"""ONNX-based tag enrichment fallback when Danbooru lookup fails."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Iterable, Tuple, Dict, List

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ml.config import onnx_model
from tagging.onnxmodel.preprocess import preprocess_image
from utils.file_storage import generate_file_path
from models.file import File as FileModel, TagSource
from models.tag import Tag, TagCategory, FileTag

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
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
        tags = [
            (str(row["name"]).strip(), WD_TO_ENUM.get(int(row["category"]), TagCategory.GENERAL))
            for _, row in df.iterrows()
            if pd.notna(row.get("name")) and pd.notna(row.get("category"))
        ]
        return tags
    except Exception as e:
        logger.error("Failed to read tag list CSV at %s: %s", csv_path, e)
        return []


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


