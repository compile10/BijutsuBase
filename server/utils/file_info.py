"""File information utilities for BijutsuBase."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image


def get_image_dimensions(path: Path) -> Tuple[int, int]:
    """
    Get width and height of an image file from disk.
    
    Args:
        path: Path to image file on disk
        
    Returns:
        Tuple of (width, height) in pixels
        
    Raises:
        IOError: If the file cannot be opened as an image
        ValueError: If the file is not a valid image
    """
    with Image.open(path) as img:
        return img.size  # Returns (width, height)


def get_video_dimensions(path: Path) -> Tuple[int, int]:
    """
    Get width and height of a video file from disk.
    
    Uses OpenCV to read video metadata from file.
    
    Args:
        path: Path to video file on disk
        
    Returns:
        Tuple of (width, height) in pixels
        
    Raises:
        IOError: If the file cannot be opened as a video
        ValueError: If the file is not a valid video or OpenCV is not available
    """
    try:
        import cv2
    except ImportError:
        raise ValueError("OpenCV (cv2) is not installed")
    
    cap = cv2.VideoCapture(str(path))
    
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {path}")
    
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if width == 0 or height == 0:
            raise ValueError("Unable to determine video dimensions")
        
        return (width, height)
    finally:
        cap.release()

