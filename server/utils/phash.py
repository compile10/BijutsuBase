"""Perceptual hashing utilities for visual similarity detection."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import imagehash
from PIL import Image
from sqlalchemy import select, func, cast
from sqlalchemy.dialects.postgresql import BIT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from models.file import File

# Hamming distance threshold for considering images similar
# 0 = identical, 1-5 = very similar, 6-10 = similar, 11-15 = somewhat similar
SIMILARITY_THRESHOLD = 13

# Constants for 64-bit signed/unsigned conversion
_INT64_MAX = (1 << 63) - 1  # 9223372036854775807
_UINT64_OVERFLOW = 1 << 64  # 18446744073709551616


def _unsigned_to_signed_64(value: int) -> int:
    """
    Convert unsigned 64-bit integer to signed 64-bit integer.
    
    This preserves the bit pattern while making the value compatible with
    PostgreSQL's signed BIGINT type.
    """
    if value > _INT64_MAX:
        return value - _UINT64_OVERFLOW
    return value


def compute_phash(image_path: Path) -> int:
    """
    Compute perceptual hash for an image.
    
    Uses the pHash algorithm from imagehash library which produces a 64-bit hash
    that is resistant to minor image modifications like resizing, slight color changes,
    and compression artifacts.
    
    Args:
        image_path: Path to image file on disk
        
    Returns:
        64-bit perceptual hash as signed integer (for PostgreSQL BIGINT compatibility)
        
    Raises:
        IOError: If the file cannot be opened as an image
        ValueError: If the file is not a valid image
    """
    with Image.open(image_path) as img:
        phash = imagehash.phash(img)
        # Convert hex string to unsigned integer
        unsigned_hash = int(str(phash), 16)
        # Convert to signed 64-bit integer for PostgreSQL BIGINT compatibility
        # PostgreSQL BIGINT range: -9223372036854775808 to 9223372036854775807
        # pHash produces 0 to 18446744073709551615 (unsigned 64-bit)
        return _unsigned_to_signed_64(unsigned_hash)


def hamming_distance(hash1: int, hash2: int) -> int:
    """
    Compute hamming distance between two pHash values.
    
    Hamming distance is the number of bit positions where the two hashes differ.
    Lower distance means more similar images.
    
    Args:
        hash1: First perceptual hash as integer
        hash2: Second perceptual hash as integer
        
    Returns:
        Hamming distance (0 = identical, higher = more different)
    """
    return bin(hash1 ^ hash2).count('1')


async def find_similar_files(
    phash: int,
    db: AsyncSession,
    threshold: int = SIMILARITY_THRESHOLD,
    exclude_hash: str | None = None,
) -> list[tuple["File", int]]:
    """
    Find files with similar perceptual hashes.
    
    Uses PostgreSQL's bit_count function to efficiently compute hamming distance
    in SQL and filter results by threshold.
    
    Args:
        phash: Perceptual hash to compare against
        db: Database session
        threshold: Maximum hamming distance to consider similar (default: SIMILARITY_THRESHOLD)
        exclude_hash: Optional SHA256 hash to exclude from results (e.g., the file being compared)
        
    Returns:
        List of tuples (File, hamming_distance) sorted by distance (closest first)
    """
    from models.file import File
    from models.family import FileFamily
    
    # Build query to find files with similar phash
    # PostgreSQL's bit_count requires a bit string, so we cast the XOR result to bit(64)
    # XOR (# operator) computes differences, bit_count counts the 1 bits = hamming distance
    xor_result = File.phash.op('#')(phash)
    hamming_expr = func.bit_count(cast(xor_result, BIT(64)))
    
    query = (
        select(File, hamming_expr.label('distance'))
        .where(File.phash.isnot(None))
        .where(hamming_expr <= threshold)
        .options(
            selectinload(File.tags),
            selectinload(File.family_as_child).selectinload(FileFamily.parent),
            selectinload(File.family_as_parent).selectinload(FileFamily.children),
        )
        .order_by(hamming_expr.asc())
    )
    
    # Exclude the file being compared if specified
    if exclude_hash:
        query = query.where(File.sha256_hash != exclude_hash)
    
    result = await db.execute(query)
    rows = result.all()
    
    return [(row[0], row[1]) for row in rows]

