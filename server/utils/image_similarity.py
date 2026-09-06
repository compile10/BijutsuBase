"""Geometric verification for visually related images."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from utils.file_storage import generate_file_path

if TYPE_CHECKING:
    from models.file import File

logger = logging.getLogger(__name__)

MAX_IMAGE_DIMENSION = 1600
LOWE_RATIO = 0.72
MIN_GOOD_MATCHES = 10
MIN_INLIERS = 8
MIN_INLIER_RATIO = 0.45
MIN_INLIER_COVERAGE = 0.03
RANSAC_REPROJECTION_THRESHOLD = 5.0


@dataclass(frozen=True)
class VisualMatch:
    """Result of geometrically verifying a pair of images."""

    matched: bool
    good_matches: int = 0
    inliers: int = 0
    inlier_ratio: float = 0.0
    coverage_a: float = 0.0
    coverage_b: float = 0.0

    @property
    def rank(self) -> tuple[int, float, float]:
        """Sort key for choosing the strongest verified candidate."""
        return self.inliers, self.inlier_ratio, min(self.coverage_a, self.coverage_b)


def _load_grayscale(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Unable to read image at {path}")

    height, width = image.shape
    longest_side = max(height, width)
    if longest_side <= MAX_IMAGE_DIMENSION:
        return image

    scale = MAX_IMAGE_DIMENSION / longest_side
    resized_width = max(1, round(width * scale))
    resized_height = max(1, round(height * scale))
    return cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )


def _ratio_matches(
    descriptors_a: np.ndarray,
    descriptors_b: np.ndarray,
) -> list[cv2.DMatch]:
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    forward_pairs = matcher.knnMatch(descriptors_a, descriptors_b, k=2)
    reverse_pairs = matcher.knnMatch(descriptors_b, descriptors_a, k=2)

    forward = [
        pair[0]
        for pair in forward_pairs
        if len(pair) == 2 and pair[0].distance < LOWE_RATIO * pair[1].distance
    ]
    reverse = {
        (pair[0].trainIdx, pair[0].queryIdx)
        for pair in reverse_pairs
        if len(pair) == 2 and pair[0].distance < LOWE_RATIO * pair[1].distance
    }
    return [match for match in forward if (match.queryIdx, match.trainIdx) in reverse]


def _point_coverage(points: np.ndarray, image: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    hull = cv2.convexHull(points.reshape(-1, 1, 2))
    image_area = image.shape[0] * image.shape[1]
    return float(cv2.contourArea(hull)) / image_area


def verify_image_similarity(path_a: Path, path_b: Path) -> VisualMatch:
    """Verify that two images share geometrically consistent local content."""
    image_a = _load_grayscale(path_a)
    image_b = _load_grayscale(path_b)

    detector = cv2.SIFT_create(nfeatures=2500)
    keypoints_a, descriptors_a = detector.detectAndCompute(image_a, None)
    keypoints_b, descriptors_b = detector.detectAndCompute(image_b, None)
    if descriptors_a is None or descriptors_b is None:
        return VisualMatch(matched=False)

    good_matches = _ratio_matches(descriptors_a, descriptors_b)
    if len(good_matches) < MIN_GOOD_MATCHES:
        return VisualMatch(matched=False, good_matches=len(good_matches))

    points_a = np.float32(
        [keypoints_a[match.queryIdx].pt for match in good_matches]
    )
    points_b = np.float32(
        [keypoints_b[match.trainIdx].pt for match in good_matches]
    )
    _, inlier_mask = cv2.findHomography(
        points_a,
        points_b,
        cv2.RANSAC,
        RANSAC_REPROJECTION_THRESHOLD,
    )
    if inlier_mask is None:
        return VisualMatch(matched=False, good_matches=len(good_matches))

    inlier_selector = inlier_mask.ravel().astype(bool)
    inliers = int(inlier_selector.sum())
    inlier_ratio = inliers / len(good_matches)
    coverage_a = _point_coverage(points_a[inlier_selector], image_a)
    coverage_b = _point_coverage(points_b[inlier_selector], image_b)
    matched = (
        inliers >= MIN_INLIERS
        and inlier_ratio >= MIN_INLIER_RATIO
        and coverage_a >= MIN_INLIER_COVERAGE
        and coverage_b >= MIN_INLIER_COVERAGE
    )
    return VisualMatch(
        matched=matched,
        good_matches=len(good_matches),
        inliers=inliers,
        inlier_ratio=inlier_ratio,
        coverage_a=coverage_a,
        coverage_b=coverage_b,
    )


def verify_file_similarity(
    file_a: "File", file_b: "File", *, strict: bool = False,
) -> VisualMatch:
    """Verify stored files; strict rebuilds abort on unreadable images."""
    path_a = generate_file_path(file_a.sha256_hash, file_a.file_ext)
    path_b = generate_file_path(file_b.sha256_hash, file_b.file_ext)
    try:
        return verify_image_similarity(path_a, path_b)
    except (OSError, ValueError, cv2.error) as exc:
        if strict:
            raise
        logger.warning(
            "Failed to verify visual similarity between %s and %s: %s",
            file_a.sha256_hash,
            file_b.sha256_hash,
            exc,
        )
        return VisualMatch(matched=False)
