"""Thumbnail generation utilities for BijutsuBase."""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageSequence

# Thumbnail configuration
MAX_THUMBNAIL_DIMENSION = 350
MAX_VIDEO_DURATION_SECONDS = 180  # 3 minutes


def _calculate_thumbnail_dimensions(width: int, height: int) -> tuple[int, int]:
    """
    Calculate new dimensions to fit within MAX_THUMBNAIL_DIMENSION while maintaining aspect ratio.
    
    Args:
        width: Original width in pixels
        height: Original height in pixels
        
    Returns:
        Tuple of (new_width, new_height) in pixels
    """
    if width > height:
        new_width = MAX_THUMBNAIL_DIMENSION
        new_height = int((height / width) * MAX_THUMBNAIL_DIMENSION)
    elif height > width:
        new_height = MAX_THUMBNAIL_DIMENSION
        new_width = int((width / height) * MAX_THUMBNAIL_DIMENSION)
    else:
        new_width = MAX_THUMBNAIL_DIMENSION
        new_height = MAX_THUMBNAIL_DIMENSION
    
    return new_width, new_height


def generate_thumbnail(path: Path) -> bytes:
    """
    Generate a thumbnail from image file on disk.
    
    Resizes the image to fit within MAX_THUMBNAIL_DIMENSION while maintaining aspect ratio.
    The output is converted to WebP format with quality=85.
    Supports animated images (WebP, GIF, etc.).
    
    Args:
        path: Path to image file on disk (any PIL-supported format)
        
    Returns:
        Thumbnail image as bytes in WebP format
        
    Raises:
        IOError: If the file cannot be opened as an image
        ValueError: If the file is not a valid image
    """
    # Open the image from disk
    with Image.open(path) as img:
        # Calculate new dimensions to fit within MAX_THUMBNAIL_DIMENSION while maintaining aspect ratio
        width, height = img.size
        
        # Check if image is animated
        is_animated = getattr(img, "is_animated", False)
        
        if is_animated:
            frames = []
            durations = []
            
            # Calculate new dimensions
            new_width, new_height = _calculate_thumbnail_dimensions(width, height)
            should_resize = width > MAX_THUMBNAIL_DIMENSION or height > MAX_THUMBNAIL_DIMENSION
            
            # Iterate over frames
            for frame in ImageSequence.Iterator(img):
                durations.append(frame.info.get("duration", 100))
                
                if should_resize:
                    # Resize frame (must convert to RGBA to preserve transparency during resize)
                    f = frame.convert("RGBA").resize((new_width, new_height), Image.Resampling.LANCZOS)
                    frames.append(f)
                else:
                    # Copy frame to ensure we keep it
                    frames.append(frame.copy())
            
            if not frames:
                raise ValueError("No frames extracted from animated image")
                
            # Save as animated WebP
            buffer = io.BytesIO()
            frames[0].save(
                buffer,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                quality=85
            )
            return buffer.getvalue()
            
        # If image is already small enough, just convert to WebP
        if width <= MAX_THUMBNAIL_DIMENSION and height <= MAX_THUMBNAIL_DIMENSION:
            buffer = io.BytesIO()
            img.save(buffer, format="WEBP", quality=85)
            return buffer.getvalue()
        
        # Calculate new dimensions
        new_width, new_height = _calculate_thumbnail_dimensions(width, height)
        
        # Resize the image using high-quality Lanczos resampling
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to BytesIO buffer as WebP with quality=85
        buffer = io.BytesIO()
        img_resized.save(buffer, format="WEBP", quality=85)
        
        # Return the bytes
        return buffer.getvalue()


def generate_video_thumbnail(path: Path) -> bytes:
    """
    Generate an animated thumbnail from video file on disk.
    
    Resizes the video to fit within MAX_THUMBNAIL_DIMENSION while maintaining aspect ratio.
    Trims video to MAX_VIDEO_DURATION_SECONDS if longer. Preserves original frame rate.
    The output is converted to animated WebP format with quality=85.
    
    Args:
        path: Path to video file on disk
        
    Returns:
        Animated WebP thumbnail as bytes
        
    Raises:
        IOError: If the file cannot be opened as a video
        ValueError: If the file is not a valid video or processing fails
    """
    # Open video with OpenCV
    cap = cv2.VideoCapture(str(path))
    
    if not cap.isOpened():
        raise IOError("Could not open video file")
    
    try:
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Calculate new dimensions to fit within MAX_THUMBNAIL_DIMENSION
        new_width, new_height = _calculate_thumbnail_dimensions(width, height)
        
        # Determine how many frames to extract
        max_frames = int(min(duration, MAX_VIDEO_DURATION_SECONDS) * fps)
        
        # Extract and resize frames
        frames = []
        frame_idx = 0
        
        while frame_idx < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize frame
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Convert BGR to RGB (OpenCV uses BGR, PIL uses RGB)
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_frame = Image.fromarray(rgb_frame)
            frames.append(pil_frame)
            
            frame_idx += 1
        
        if not frames:
            raise ValueError("No frames could be extracted from video")
        
        # Save as animated WebP
        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),  # Duration per frame in milliseconds
            quality=85,
            method=6  # Higher quality encoding
        )
        
        return buffer.getvalue()
        
    finally:
        # Release video capture
        cap.release()
