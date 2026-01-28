"""ONNX-based tag enrichment fallback when Danbooru lookup fails."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Iterable, Tuple, Dict, List
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import cv2

from ml.config import onnx_model
from sources.onnxmodel.preprocess import preprocess_image
from utils.file_storage import generate_file_path
from models.file import File as FileModel, TagSource, Rating
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

# Mapping from ONNX rating tag names to Rating enum
RATING_TAG_MAP: Dict[str, Rating] = {
    "general": Rating.SAFE,
    "sensitive": Rating.SENSITIVE,
    "questionable": Rating.QUESTIONABLE,
    "explicit": Rating.EXPLICIT,
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
    Get or create a Tag and associate it with the given file (if not already),
    using optimistic inserts and handling unique conflicts via IntegrityError.
    """
    # First, try to insert the Tag optimistically and handle existing rows
    tag: Tag | None = None
    try:
        async with db.begin_nested():
            tag = Tag(name=tag_name, category=category)
            db.add(tag)
    except IntegrityError:
        # Tag with this name already exists; load it instead
        tag = await db.scalar(select(Tag).where(Tag.name == tag_name))
        if tag is None:
            # If we still can't find it, re-raise so the caller can handle
            raise

    # Next, try to insert the FileTag association and ignore duplicates
    try:
        async with db.begin_nested():
            assoc = FileTag(
                file_sha256_hash=file.sha256_hash,
                tag_id=tag.id,
            )
            db.add(assoc)
    except IntegrityError:
        # Association already exists; safe to ignore
        return


def _extract_video_frames(video_path: Path, points: Iterable[float] = (0.1, 0.5, 0.9)) -> List[np.ndarray]:
    """
    Extract BGR frames from a video at the specified fractional positions.
    Returns a list of frames as numpy arrays (BGR, HxWx3). Missing frames are skipped.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("Unable to open video file for ONNX enrichment: %s", video_path)
        return []
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            return []
        indices: List[int] = []
        for p in points:
            idx = int(max(0, min(frame_count - 1, int(frame_count * float(p)))))
            indices.append(idx)
        # Ensure uniqueness and order
        indices = sorted(set(indices))
        frames: List[np.ndarray] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok and frame is not None and frame.size > 0:
                frames.append(frame)
        return frames
    finally:
        cap.release()


async def _infer_image_scores(image_path: Path) -> Optional[np.ndarray]:
    """
    Preprocess a single image and run ONNX inference, returning a 1D probability array.
    """
    try:
        input_tensor = await asyncio.to_thread(preprocess_image, image_path)
        outputs = await onnx_model.infer_async(input_tensor)
        if not outputs:
            return None
        probs = next(iter(outputs.values()))
        scores = np.asarray(probs).squeeze().astype(np.float32)
        return scores
    except Exception as e:
        logger.warning("Failed ONNX image inference for %s: %s", image_path, e)
        return None


async def _infer_frame_scores(frames: List[np.ndarray]) -> List[np.ndarray]:
    """
    Preprocess frames and run ONNX inference for each, returning list of 1D probability arrays.
    """
    scores_list: List[np.ndarray] = []
    for frame in frames:
        try:
            input_tensor = await asyncio.to_thread(preprocess_image, frame)
            outputs = await onnx_model.infer_async(input_tensor)
            if not outputs:
                continue
            probs = next(iter(outputs.values()))
            scores = np.asarray(probs).squeeze().astype(np.float32)
            scores_list.append(scores)
        except Exception as e:
            logger.debug("Skipping a frame due to ONNX inference error: %s", e)
            continue
    return scores_list


def _combine_probs_logit_mean(probs_list: List[np.ndarray], weights: Optional[np.ndarray] = None) -> Optional[np.ndarray]:
    """
    Combine multiple probability vectors via logit-mean and return final probabilities.
    """
    if not probs_list:
        return None
    # Stack to (F, N)
    P = np.stack(probs_list, axis=0).astype(np.float32)
    # Clamp probabilities away from 0/1
    eps = 1e-6
    P = np.clip(P, eps, 1.0 - eps)
    # Logit
    logits = np.log(P / (1.0 - P))
    # Weights
    if weights is None:
        weights = np.full((logits.shape[0],), 1.0 / logits.shape[0], dtype=np.float32)
    else:
        weights = np.asarray(weights, dtype=np.float32)
        weights = weights / np.sum(weights)
        if weights.shape[0] != logits.shape[0]:
            raise ValueError("Weights length must match number of frames")
    # Weighted mean over frames
    mean_logit = np.sum(logits * weights[:, None], axis=0)
    # Sigmoid
    combined = 1.0 / (1.0 + np.exp(-mean_logit))
    return combined.astype(np.float32)


def _combine_probs_max(probs_list: List[np.ndarray]) -> Optional[np.ndarray]:
    """
    Combine multiple probability vectors by taking the maximum across frames.
    
    """
    if not probs_list:
        return None
    # Stack to (F, N) where F = frames, N = number of tags
    P = np.stack(probs_list, axis=0).astype(np.float32)
    # Take max across frames (axis=0)
    combined = np.max(P, axis=0)
    return combined.astype(np.float32)


async def enrich_file_with_onnx(
    file: FileModel,
    db: AsyncSession,
) -> AsyncSession:
    """
    Enrich the file with tags predicted by the ONNX model.
    
    This is intended as a fallback when API metadata is unavailable.
    """
    file_type = file.file_type or ""
    # Resolve original media path
    media_path = generate_file_path(file.sha256_hash, file.file_ext)
    if not Path(media_path).exists():
        logger.warning("Original media file not found for %s at %s", file.sha256_hash, media_path)
        return db

    scores: Optional[np.ndarray] = None
    if file_type.startswith("image/"):
        scores = await _infer_image_scores(media_path)
        if scores is None:
            logger.warning("ONNX inference returned no outputs for image %s", file.sha256_hash)
            return db
    elif file_type.startswith("video/"):
        frames = _extract_video_frames(media_path, points=(0.1, 0.5, 0.9))
        if not frames:
            logger.warning("No frames extracted for video %s", file.sha256_hash)
            return db
        frame_scores = await _infer_frame_scores(frames)
        if not frame_scores:
            logger.warning("ONNX inference returned no outputs for frames of %s", file.sha256_hash)
            return db
        # Use max across frames so a tag detected clearly in any frame isn't suppressed
        scores = _combine_probs_max(frame_scores)
        if scores is None:
            logger.warning("Failed to combine frame probabilities for %s", file.sha256_hash)
            return db
    else:
        logger.debug("Skipping ONNX enrichment for unsupported file type %s", file_type)
        return db

    # Load tag list in model order
    tag_list_path = onnx_model.tag_list_path
    tags = _read_tag_list_csv(tag_list_path)
    if not tags:
        logger.warning("Tag list CSV empty or unreadable at %s", tag_list_path)
        return db

    # Sanity check: ensure alignment length
    num = min(len(tags), int(scores.shape[-1]))

    # Collect rating scores to determine the best rating
    rating_scores: Dict[Rating, float] = {}
    
    # Iterate predictions and associate tags above thresholds
    for idx in range(num):
        name, category = tags[idx]
        score = float(scores[idx])
        threshold = THRESHOLDS.get(category, 0.35)
        
        # Check if this is a rating tag
        if name in RATING_TAG_MAP:
            rating_scores[RATING_TAG_MAP[name]] = score
            continue  # Skip adding rating as a tag
        
        if score >= threshold:
            await _associate_tag(db, file, name, category)
    
    # Set the file rating to the one with highest confidence
    if rating_scores:
        best_rating = max(rating_scores.items(), key=lambda x: x[1])
        file.rating = best_rating[0]
        logger.info(
            "Set rating for %s to %s (confidence: %.3f)",
            file.sha256_hash,
            best_rating[0].value,
            best_rating[1]
        )

    file.tag_source = TagSource.ONNX

    return db


