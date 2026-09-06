"""Perceptual hashing utilities for visual similarity detection."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import imagehash
from PIL import Image, ImageOps
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from models.file import File

# pHash is only a recall-oriented candidate signal. Multiple center-crop views
# make it crop-aware; OpenCV makes the acceptance decision.
CANDIDATE_THRESHOLD = 10
MAX_CANDIDATES = 50
CENTER_CROP_RETENTIONS = (0.8, 0.5)


@dataclass(frozen=True)
class PerceptualHashes:
    """Whole-image and center-crop pHashes as 64-character bit strings."""

    full: str
    center_80: str
    center_50: str

    def values(self) -> tuple[str, str, str]:
        return self.full, self.center_80, self.center_50


def _hash_image(image: Image.Image) -> str:
    return format(int(str(imagehash.phash(image)), 16), "064b")


def _center_crop(image: Image.Image, retained_fraction: float) -> Image.Image:
    width, height = image.size
    margin_x = round(width * (1 - retained_fraction) / 2)
    margin_y = round(height * (1 - retained_fraction) / 2)
    return image.crop((margin_x, margin_y, width - margin_x, height - margin_y))


def compute_phashes(image_path: Path) -> PerceptualHashes:
    """Compute whole-image and center-crop perceptual hashes."""
    with Image.open(image_path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        center_80 = _center_crop(image, CENTER_CROP_RETENTIONS[0])
        center_50 = _center_crop(image, CENTER_CROP_RETENTIONS[1])
        return PerceptualHashes(
            full=_hash_image(image),
            center_80=_hash_image(center_80),
            center_50=_hash_image(center_50),
        )


def compute_phash(image_path: Path) -> str:
    """
    Compute perceptual hash for an image.
    
    Uses the pHash algorithm from imagehash library which produces a 64-bit hash
    that is resistant to minor image modifications like resizing, slight color changes,
    and compression artifacts.
    
    Args:
        image_path: Path to image file on disk
        
    Returns:
        64-character bit string for PostgreSQL BIT(64) storage
        
    Raises:
        IOError: If the file cannot be opened as an image
        ValueError: If the file is not a valid image
    """
    return compute_phashes(image_path).full


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Compute hamming distance between two pHash values.
    
    Hamming distance is the number of bit positions where the two hashes differ.
    Lower distance means more similar images.
    
    Args:
        hash1: First perceptual hash as a 64-character bit string
        hash2: Second perceptual hash as a 64-character bit string
        
    Returns:
        Hamming distance (0 = identical, higher = more different)
    """
    return (int(hash1, 2) ^ int(hash2, 2)).bit_count()


def minimum_hamming_distance(
    hashes1: PerceptualHashes,
    hashes2: PerceptualHashes,
) -> int:
    """Return the closest distance between any two crop-aware hash views."""
    return min(
        hamming_distance(hash1, hash2)
        for hash1 in hashes1.values()
        for hash2 in hashes2.values()
    )


async def find_similar_files(
    phash: str,
    db: AsyncSession,
    phash_center_80: str | None = None,
    phash_center_50: str | None = None,
    threshold: int = CANDIDATE_THRESHOLD,
    exclude_hash: str | None = None,
    limit: int = MAX_CANDIDATES,
    before_hash: str | None = None,
) -> list[tuple["File", int]]:
    """
    Find files with similar perceptual hashes.
    
    Uses PostgreSQL's bit_count function to efficiently compute hamming distance
    in SQL and filter results by threshold.
    
    Args:
        phash: 64-character perceptual hash bit string to compare against
        db: Database session
        phash_center_80: pHash of the centered view retaining 80% of the image
        phash_center_50: pHash of the centered view retaining 50% of the image
        threshold: Maximum hamming distance for candidate retrieval
        exclude_hash: Optional SHA256 hash to exclude from results (e.g., the file being compared)
        limit: Maximum number of candidates to return for OpenCV verification
        before_hash: Only consider lower SHA256 hashes during an ordered library rebuild
        
    Returns:
        List of tuples (File, hamming_distance) sorted by distance (closest first)
    """
    from models.file import File
    from models.family import FileFamily
    
    query_hashes = [phash]
    if phash_center_80 is not None:
        query_hashes.append(phash_center_80)
    if phash_center_50 is not None:
        query_hashes.append(phash_center_50)

    stored_hashes = [File.phash, File.phash_center_80, File.phash_center_50]
    distances = [
        func.coalesce(
            func.bit_count(stored_hash.op('#')(cast(query_hash, BIT(64)))),
            65,
        )
        for stored_hash in stored_hashes
        for query_hash in query_hashes
    ]
    hamming_expr = func.least(*distances)
    
    query = (
        select(File, hamming_expr.label('distance'))
        .where(File.phash.isnot(None))
        .where(hamming_expr <= threshold)
        .options(
            selectinload(File.tags),
            selectinload(File.family_as_child).selectinload(FileFamily.parent),
            selectinload(File.family_as_parent).selectinload(FileFamily.children),
        )
        .order_by(hamming_expr.asc(), File.sha256_hash.asc())
        .limit(limit)
    )
    
    # Exclude the file being compared if specified
    if exclude_hash:
        query = query.where(File.sha256_hash != exclude_hash)
    if before_hash is not None:
        query = query.where(File.sha256_hash < before_hash)
    
    result = await db.execute(query)
    rows = result.all()
    
    return [(row[0], row[1]) for row in rows]
