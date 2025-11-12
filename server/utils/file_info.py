"""File information utilities for BijutsuBase."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)


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


def get_file_sha256(path: Path) -> str:
    """
    Compute the SHA-256 hash of a file on disk.
    
    Args:
        path: Path to the file on disk
    
    Returns:
        Hex-encoded SHA-256 digest string
    """
    # Use hashlib.file_digest (Python 3.11+) for efficient file hashing
    # Increase buffering to reduce syscalls on large files
    with open(path, "rb", buffering=1024 * 1024) as file_handle:
        return hashlib.file_digest(file_handle, "sha256").hexdigest()


def is_ai_generated_image(path: Path) -> bool:
    """
    Inspect EXIF UserComment to heuristically detect AI-generated images.
    Only the EXIF UserComment field (0x9286 / 37510) is examined.
    If the image cannot be read, has no EXIF, or has no UserComment,
    the function returns False.
    """
    # Common indicators found in EXIF UserComment of AI-generated images
    ai_keywords = (
        # Generators
        "stable diffusion",
        "stablediffusion",
        "dall-e",
        "dall·e",
        "midjourney",
        "novelai",
        "nai diffusion",
        # UI / tooling
        "comfyui",
        "automatic1111",
        "a1111",
        "invoke ai",
        "invokeai",
        # Common metadata/parameters
        "cfg scale",
        "sampler:",
        "sampling method",
        "steps:",
        "negative prompt",
        "model hash",
        "clip skip",
        "seed:",
        "denoising strength",
        # Model indicators
        "sdxl",
        "sd 1.5",
        "sd 2.1",
        "pony diffusion",
    )

    def _decode_user_comment(raw_value: object) -> str | None:
        """
        Decode EXIF UserComment according to EXIF spec heuristics.
        Handles common encodings and prefixes. Returns None if undecodable.
        """
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            return raw_value
        if isinstance(raw_value, bytes):
            # EXIF UserComment may start with an 8-byte charset prefix
            # e.g., ASCII\\0\\0\\0, UNICODE\\0, JIS\\0\\0\\0
            try:
                if raw_value.startswith(b"ASCII\x00\x00\x00"):
                    return raw_value[8:].decode("ascii", errors="ignore")
                if raw_value.startswith(b"UNICODE\x00"):
                    # Bytes are UCS-2/UTF-16 without BOM. Endianness varies.
                    data = raw_value[8:]
                    # Try both and select the one with the highest ASCII ratio
                    def decode_utf16_variant(enc: str) -> tuple[str, float]:
                        try:
                            s = data.decode(enc, errors="ignore")
                        except Exception:
                            return "", 0.0
                        if not s:
                            return "", 0.0
                        ascii_count = sum(1 for ch in s if ord(ch) < 128)
                        ratio = ascii_count / max(1, len(s))
                        return s, ratio
                    le_s, le_r = decode_utf16_variant("utf-16-le")
                    be_s, be_r = decode_utf16_variant("utf-16-be")
                    return le_s if le_r >= be_r else be_s
                if raw_value.startswith(b"JIS\x00\x00\x00"):
                    return raw_value[8:].decode("shift_jis", errors="ignore")
            except Exception:
                # Fall through to generic attempts below
                pass
            # Generic attempts
            for encoding in ("utf-8", "utf-16", "latin-1"):
                try:
                    return raw_value.decode(encoding, errors="ignore")
                except Exception:
                    continue
            # As a last resort, strip NULs and decode latin-1 best-effort
            try:
                return raw_value.replace(b"\x00", b"").decode("latin-1", errors="ignore")
            except Exception:
                return None
        # Unknown type
        return None

    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return False
            # EXIF UserComment tag (37510 / 0x9286). It often resides in the Exif IFD (0x8769).
            user_comment_tag = 37510  # 0x9286 UserComment
            user_comment_raw = exif.get(user_comment_tag)
            # If not present at top-level, check known sub-IFDs
            if not user_comment_raw and hasattr(exif, "get_ifd"):
                for ifd_id in (0x8769, 0xA005):  # ExifIFD, InteropIFD
                    try:
                        sub_ifd = exif.get_ifd(ifd_id)
                        if sub_ifd and user_comment_tag in sub_ifd:
                            user_comment_raw = sub_ifd[user_comment_tag]
                            break
                    except Exception:
                        # Ignore parsing errors for uncommon IFDs
                        continue
            if not user_comment_raw:
                return False
            user_comment = _decode_user_comment(user_comment_raw)
            if not user_comment:
                return False
            text = user_comment.lower()
            return any(keyword in text for keyword in ai_keywords)
    except Exception:
        # If the file is not an image or cannot be opened/read,
        # conservatively return False")
        logger.exception("Error detecting AI-generated image")
        return False

