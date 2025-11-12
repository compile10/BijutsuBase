"""ONNX-based tag enrichment fallback when Danbooru lookup fails."""
from __future__ import annotations

import asyncio
import csv
import logging
from pathlib import Path
from typing import Iterable, Tuple, Dict, List

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ml.config import onnx_model
from tagging.onnxmodel.preprocess import preprocess_image
from utils.file_storage import generate_file_path
from models.file import File as FileModel
from models.tag import Tag, TagCategory, FileTag, TagSource

logger = logging.getLogger(__name__)

# Confidence thresholds per category (as specified)
THRESHOLDS: Dict[TagCategory, float] = {
    TagCategory.CHARACTER: 0.80,
    # Artist and Copyright are currently unsupported by the ONNX model
    TagCategory.ARTIST: 0.75,
    TagCategory.COPYRIGHT: 0.55,
    TagCategory.GENERAL: 0.35,
    TagCategory.META: 0.35,
}

# Mapping from WD tagger numeric category to our TagCategory
WD_TO_ENUM: Dict[int, TagCategory] = {
    0: TagCategory.GENERAL,
    1: TagCategory.ARTIST,
    3: TagCategory.COPYRIGHT,
    4: TagCategory.CHARACTER,
    9: TagCategory.META,
}


def _read_tag_list_csv(csv_path: Path) -> List[Tuple[str, TagCategory]]:
    """
    Read tag metadata from selected_tags.csv in the same order as model outputs.
    
    Returns a list of (name, TagCategory) in file order.
    """
    tags: List[Tuple[str, TagCategory]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        # Prefer DictReader (standard WD format: name, category, count)
        reader = csv.DictReader(f)
        # If DictReader failed to detect header (None), fall back to plain reader
        if reader.fieldnames is None:
            f.seek(0)
            plain = csv.reader(f)
            # Skip header if present by checking first row content
            first = next(plain, None)
            if first is None:
                return tags
            # Heuristically detect header
            if first and len(first) >= 2 and first[0].lower() == "name":
                pass  # header consumed
            else:
                # treat first as data row
                try:
                    name = str(first[0]).strip()
                    cat_num = int(first[1])
                    tags.append((name, WD_TO_ENUM.get(cat_num, TagCategory.GENERAL)))
                except Exception:
                    # Ignore malformed line
                    pass
            for row in plain:
                if not row or len(row) < 2:
                    continue
                try:
                    name = str(row[0]).strip()
                    cat_num = int(row[1])
                    tags.append((name, WD_TO_ENUM.get(cat_num, TagCategory.GENERAL)))
                except Exception:
                    continue
            return tags

        # DictReader path
        for row in reader:
            try:
                name = str(row["name"]).strip()
                cat_num = int(row["category"])
            except Exception:
                # If columns differ, try positional fallback
                try:
                    name = str(row.get(None, [])[0]).strip()  # type: ignore[index]
                    cat_num = int(row.get(None, [])[1])  # type: ignore[index]
                except Exception:
                    continue
            tags.append((name, WD_TO_ENUM.get(cat_num, TagCategory.GENERAL)))
    return tags


async def _associate_tag(
    db: AsyncSession,
    file: FileModel,
    tag_name: str,
    category: TagCategory,
) -> None:
    """
    Get or create a Tag and associate it with the given file (if not already).
    """
    # Get or create Tag
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(name=tag_name, category=category)
        db.add(tag)
        await db.flush()  # to get tag.id

    # Ensure association exists
    assoc_result = await db.execute(
        select(FileTag).where(
            FileTag.file_sha256_hash == file.sha256_hash,
            FileTag.tag_id == tag.id,
        )
    )
    if assoc_result.scalar_one_or_none() is None:
        db.add(
            FileTag(
                file_sha256_hash=file.sha256_hash,
                tag_id=tag.id,
            )
        )


async def enrich_file_with_onnx(
    file: FileModel,
    db: AsyncSession,
) -> AsyncSession:
    """
    Enrich the file with tags predicted by the ONNX model.
    
    This is intended as a fallback when Danbooru metadata is unavailable.
    """
    # Only process images
    # TODO: ADD VIDEO SUPPORT
    if not (file.file_type or "").startswith("image/"):
        logger.debug("Skipping ONNX enrichment for non-image file %s", file.sha256_hash)
        return db

    # Resolve original image path
    image_path = generate_file_path(file.sha256_hash, file.file_ext)
    if not Path(image_path).exists():
        logger.warning("Original image file not found for %s at %s", file.sha256_hash, image_path)
        return db

    # Preprocess image for model
    input_tensor = await asyncio.to_thread(preprocess_image, image_path)

    # Run inference
    outputs = await onnx_model.infer_async(input_tensor)
    # Use the first output tensor by convention
    if not outputs:
        logger.warning("ONNX inference returned no outputs for %s", file.sha256_hash)
        return db
    probs = next(iter(outputs.values()))
    # Shape expected: (1, N) or (N,)
    scores = np.asarray(probs).squeeze().astype(np.float32)

    # Load tag list in model order
    tag_list_path = onnx_model.tag_list_path
    tags = _read_tag_list_csv(tag_list_path)
    if not tags:
        logger.warning("Tag list CSV empty or unreadable at %s", tag_list_path)
        return db

    # Sanity check: ensure alignment length
    num = min(len(tags), int(scores.shape[-1]))

    # Iterate predictions and associate tags above thresholds
    for idx in range(num):
        name, category = tags[idx]
        score = float(scores[idx])
        threshold = THRESHOLDS.get(category, 0.35)
        if score >= threshold:
            await _associate_tag(db, file, name, category)

    file.tag_source = TagSource.ONNX

    return db


