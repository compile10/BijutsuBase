"""Recompute all image pHashes and replace every family using the v2 matcher.

Run after Alembic migrations, with the API and all media writers stopped.
By default the full rebuild is rehearsed and rolled back; --apply commits it.
Manual families are replaced too. Media files, tags, and pools are not modified.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import delete, func, inspect, select, text, update
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.config import AsyncSessionLocal, engine
from models.family import FileFamily
from models.file import File
from utils.file_storage import generate_file_path
from utils.phash import compute_phashes, find_similar_files
from utils.similarity_family import handle_similar_files

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MigrationSummary:
    images_rehashed: int
    images_processed: int
    families_removed: int
    families_created: int
    children_linked: int
    applied: bool


async def _require_bit64_schema(db: AsyncSession) -> None:
    connection = await db.connection()
    columns = await connection.run_sync(
        lambda sync_connection: inspect(sync_connection).get_columns("files")
    )
    column_types = {column["name"]: column["type"] for column in columns}
    for name in ("phash", "phash_center_80", "phash_center_50"):
        column_type = column_types.get(name)
        if not isinstance(column_type, BIT) or column_type.length != 64:
            raise RuntimeError("Run 'uv run alembic upgrade head' before rebuilding families.")


async def _recompute_hashes(db: AsyncSession, batch_size: int) -> int:
    processed = 0
    last_hash: str | None = None
    while True:
        query = (
            select(File.sha256_hash, File.file_ext)
            .where(File.file_type.like("image/%"))
            .order_by(File.sha256_hash)
            .limit(batch_size)
        )
        if last_hash is not None:
            query = query.where(File.sha256_hash > last_hash)
        rows = (await db.execute(query)).all()
        if not rows:
            return processed

        for sha256_hash, file_ext in rows:
            path = generate_file_path(sha256_hash, file_ext)
            try:
                hashes = await asyncio.to_thread(compute_phashes, path)
            except (OSError, ValueError) as exc:
                raise RuntimeError(f"Could not recompute hashes for {sha256_hash}: {path}") from exc
            await db.execute(
                update(File)
                .where(File.sha256_hash == sha256_hash)
                .values(
                    phash=hashes.full,
                    phash_center_80=hashes.center_80,
                    phash_center_50=hashes.center_50,
                )
            )
            processed += 1
        last_hash = rows[-1].sha256_hash
        logger.info("Recomputed hashes for %s images", processed)


async def _rebuild_families(db: AsyncSession, batch_size: int) -> int:
    processed = 0
    last_hash: str | None = None
    while True:
        query = (
            select(File.sha256_hash)
            .where(File.file_type.like("image/%"))
            .order_by(File.sha256_hash)
            .limit(batch_size)
        )
        if last_hash is not None:
            query = query.where(File.sha256_hash > last_hash)
        hashes = (await db.scalars(query)).all()
        if not hashes:
            return processed

        for sha256_hash in hashes:
            file = (
                await db.scalars(
                    select(File)
                    .options(selectinload(File.tags))
                    .where(File.sha256_hash == sha256_hash)
                )
            ).one()
            if file.phash is None or file.phash_center_80 is None or file.phash_center_50 is None:
                raise RuntimeError(f"Missing recomputed hashes for {sha256_hash}")

            # Lower SHA-256 keys provide deterministic, single-pass assignment.
            candidates = await find_similar_files(
                phash=file.phash,
                phash_center_80=file.phash_center_80,
                phash_center_50=file.phash_center_50,
                db=db,
                exclude_hash=sha256_hash,
                before_hash=sha256_hash,
            )
            await handle_similar_files(file, candidates, db, commit=False, strict=True)
            await db.flush()
            # Foreign-key updates must not leave cached family relationships stale.
            db.expunge_all()
            processed += 1
        last_hash = hashes[-1]
        logger.info("Ran v2 autofamily for %s images", processed)


async def v2_autofamily_migration(
    batch_size: int = 100, *, apply: bool = False,
) -> MigrationSummary:
    """Rebuild atomically; errors and dry runs preserve the original DB state."""
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            await _require_bit64_schema(db)
            # Fail immediately if another writer is active; keep the replay stable.
            await db.execute(text(
                "LOCK TABLE files, file_families, file_tags, tags "
                "IN SHARE ROW EXCLUSIVE MODE NOWAIT"
            ))
            families_removed = await db.scalar(select(func.count()).select_from(FileFamily))
            logger.warning(
                "Resetting all pHashes and %s families (including manual families); apply=%s",
                families_removed, apply,
            )
            await db.execute(
                update(File).values(
                    phash=None, phash_center_80=None, phash_center_50=None,
                    parent_family_id=None,
                )
            )
            await db.execute(delete(FileFamily))

            images_rehashed = await _recompute_hashes(db, batch_size)
            images_processed = await _rebuild_families(db, batch_size)
            families_created = await db.scalar(select(func.count()).select_from(FileFamily))
            children_linked = await db.scalar(
                select(func.count()).select_from(File).where(File.parent_family_id.isnot(None))
            )
            summary = MigrationSummary(
                images_rehashed=images_rehashed,
                images_processed=images_processed,
                families_removed=families_removed,
                families_created=families_created,
                children_linked=children_linked,
                applied=apply,
            )
            if not apply:
                await db.rollback()

    logger.info("%s: %s", "Committed rebuild" if apply else "Dry run rolled back", summary)
    return summary


async def async_main(batch_size: int, apply: bool) -> None:
    try:
        await v2_autofamily_migration(batch_size, apply=apply)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=100)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Commit the replacement of all hashes and families.")
    mode.add_argument("--dry-run", action="store_true", help="Rehearse the full rebuild and roll back (default).")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    logging.basicConfig(level=logging.INFO)
    engine.echo = False
    try:
        asyncio.run(async_main(args.batch_size, args.apply))
    except Exception:
        logger.exception("Rebuild failed; its hash and family changes were rolled back.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
