"""Thumbnail generation utilities for BijutsuBase."""
from __future__ import annotations

import io

from PIL import Image


def generate_thumbnail(content: bytes) -> bytes:
    """
    Generate a thumbnail from image content.
    
    Resizes the image to fit within 250x250 pixels while maintaining aspect ratio.
    The output is converted to WebP format with quality=85.
    
    Args:
        content: Image file content as bytes (any PIL-supported format)
        
    Returns:
        Thumbnail image as bytes in WebP format
        
    Raises:
        IOError: If the file cannot be opened as an image
        ValueError: If the file is not a valid image
    """
    # Open the image from bytes
    with Image.open(io.BytesIO(content)) as img:
        # Calculate new dimensions to fit within 250x250 while maintaining aspect ratio
        width, height = img.size
        max_dimension = 250
        
        # If image is already small enough, return original content
        if width <= max_dimension and height <= max_dimension:
            return content
        
        if width > height:
            new_width = max_dimension
            new_height = int((height / width) * max_dimension)
        elif height > width:
            new_height = max_dimension
            new_width = int((width / height) * max_dimension)
        else:
            new_width = max_dimension
            new_height = max_dimension
        
        # Resize the image using high-quality Lanczos resampling
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to BytesIO buffer as WebP with quality=85
        buffer = io.BytesIO()
        img_resized.save(buffer, format="WEBP", quality=85)
        
        # Return the bytes
        return buffer.getvalue()

