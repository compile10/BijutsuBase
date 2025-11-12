"""Image preprocessing for ONNX tagger."""
from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np


def preprocess_image(image_input: Union[str, Path, np.ndarray], target_size: int = 448) -> np.ndarray:
    """
    Load or accept an image and preprocess it for the ONNX tagger model.
    
    Steps:
    - Load image from disk using OpenCV (loads as BGR) OR accept a BGR numpy array
    - Resize to target_size x target_size using LANCZOS
    - Convert to float32 in [0, 255] range (NO normalization)
    - Add batch dimension -> (1, H, W, C)
    
    Note: The WD ConvNext tagger expects BGR format in [0, 255] range.
    
    Args:
        image_input: Path/str to the source image file OR a numpy ndarray in BGR format
        target_size: Desired square side (defaults to 448)
    
    Returns:
        Numpy array of shape (1, target_size, target_size, 3), dtype float32
        (NHWC format, BGR channels, [0, 255] range)
    """
    # If provided a numpy array, assume it's already a BGR image (H, W, C)
    if isinstance(image_input, np.ndarray):
        img = image_input
        if img.ndim != 3 or img.shape[2] != 3:
            raise ValueError("Expected BGR image with shape (H, W, 3)")
    else:
        image_path = str(Path(image_input))
        # Load image with OpenCV (loads as BGR)
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
    
    # Resize using LANCZOS interpolation
    img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
    
    # Convert to float32
    np_img = img.astype(np.float32)  # (H, W, C) in [0, 255], BGR
    
    # Add batch dimension (keep HWC format)
    batched = np.expand_dims(np_img, axis=0).astype(np.float32, copy=False)
    
    return batched


