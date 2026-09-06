"""Automatic family creation based on verified visual similarity."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.image_similarity import VisualMatch, verify_file_similarity
from utils.parent_determination import determine_parent

if TYPE_CHECKING:
    from models.family import FileFamily
    from models.file import File

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _VerifiedCandidate:
    file: "File"
    phash_distance: int
    visual_match: VisualMatch

    @property
    def rank(self) -> tuple[int, float, float, int]:
        return (*self.visual_match.rank, -self.phash_distance)


def _candidate_family(file: "File") -> "FileFamily | None":
    if file.family_as_parent is not None:
        return file.family_as_parent
    if file.parent_family_id is not None:
        return file.family_as_child
    return None


async def handle_similar_files(
    new_file: "File",
    similar_files: list[tuple["File", int]],
    db: AsyncSession,
    *,
    commit: bool = True,
    strict: bool = False,
) -> None:
    """Verify pHash candidates and safely create or extend one family.

    A family is only extended when the new file matches its canonical parent.
    Multiple family matches are considered ambiguous and never auto-merged.
    When no family exists, only the strongest standalone match is used to start
    a two-file family, preventing transitive similarity chains.

    Rebuilds use commit=False to own the transaction and strict=True to propagate
    image verification errors instead of treating them as non-matches.
    """
    if not similar_files:
        return

    standalone_matches: list[_VerifiedCandidate] = []
    family_matches: dict[object, tuple["FileFamily", _VerifiedCandidate]] = {}
    evaluated_families: set[object] = set()

    for candidate, phash_distance in similar_files:
        family = _candidate_family(candidate)
        comparison_file = (
            candidate
            if family is None or candidate.family_as_parent is family
            else family.parent
        )
        family_key: object = family.id if family is not None else candidate.sha256_hash

        if family is not None:
            if family_key in evaluated_families:
                continue
            evaluated_families.add(family_key)

        visual_match = await asyncio.to_thread(
            verify_file_similarity,
            new_file,
            comparison_file,
            strict=strict,
        )
        logger.info(
            "Visual verification %s -> %s: matched=%s, pHash=%s, "
            "good_matches=%s, inliers=%s, inlier_ratio=%.3f",
            new_file.sha256_hash,
            comparison_file.sha256_hash,
            visual_match.matched,
            phash_distance,
            visual_match.good_matches,
            visual_match.inliers,
            visual_match.inlier_ratio,
        )
        if not visual_match.matched:
            continue

        verified = _VerifiedCandidate(candidate, phash_distance, visual_match)
        if family is None:
            standalone_matches.append(verified)
        else:
            family_matches[family_key] = (family, verified)

    if len(family_matches) > 1:
        logger.warning(
            "Skipping automatic family assignment for %s: matched %s family parents",
            new_file.sha256_hash,
            len(family_matches),
        )
        return

    if family_matches:
        family, _ = next(iter(family_matches.values()))
        await _add_to_existing_family(new_file, family, db)
        if commit:
            await db.commit()
        return

    if not standalone_matches:
        return

    best_match = max(standalone_matches, key=lambda match: match.rank)
    await _create_new_family(new_file, best_match.file, db)
    if commit:
        await db.commit()


async def _create_new_family(
    new_file: "File",
    similar_file: "File",
    db: AsyncSession,
) -> None:
    """Create a two-file family from a geometrically verified match."""
    from models.family import FileFamily

    parent = determine_parent(similar_file, new_file)
    child = new_file if parent.sha256_hash == similar_file.sha256_hash else similar_file

    family = FileFamily(parent_sha256_hash=parent.sha256_hash)
    db.add(family)
    await db.flush()
    child.parent_family_id = family.id

    logger.info(
        "Created family %s with parent %s and child %s",
        family.id,
        parent.sha256_hash,
        child.sha256_hash,
    )


async def _add_to_existing_family(
    new_file: "File",
    family: "FileFamily",
    db: AsyncSession,
) -> None:
    """Add a verified file to a family and select the preferred parent."""
    from models.file import File

    result = await db.execute(
        select(File)
        .options(selectinload(File.tags))
        .where(File.sha256_hash == family.parent_sha256_hash)
    )
    current_parent = result.scalar_one()
    best_parent = determine_parent(current_parent, new_file)

    if best_parent.sha256_hash == new_file.sha256_hash:
        current_parent.parent_family_id = family.id
        family.parent_sha256_hash = new_file.sha256_hash
        logger.info(
            "Replaced parent %s with %s in family %s",
            current_parent.sha256_hash,
            new_file.sha256_hash,
            family.id,
        )
        return

    new_file.parent_family_id = family.id
    logger.info("Added %s to family %s", new_file.sha256_hash, family.id)
