"""File information utilities for BijutsuBase."""
from __future__ import annotations

import json
import subprocess
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
    
    Uses ffprobe to read video metadata from file.
    
    Args:
        path: Path to video file on disk
        
    Returns:
        Tuple of (width, height) in pixels
        
    Raises:
        IOError: If the file cannot be opened as a video
        ValueError: If the file is not a valid video or ffprobe is not available
    """
    try:
        # Use ffprobe to get video dimensions from file
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            str(path)  # Read from file path
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Unable to determine video dimensions: {stderr.decode('utf-8', errors='ignore')}")
        
        data = json.loads(stdout.decode('utf-8'))
        
        if "streams" not in data or len(data["streams"]) == 0:
            raise ValueError("No video stream found")
        
        stream = data["streams"][0]
        width = stream.get("width")
        height = stream.get("height")
        
        if not width or not height:
            raise ValueError("Unable to determine video dimensions")
        
        return (int(width), int(height))
    except FileNotFoundError:
        raise ValueError("ffprobe is not installed or not in PATH")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid video format or corrupted data: {str(e)}")

