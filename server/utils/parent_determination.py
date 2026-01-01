"""
Utility for determining which file should be the parent in a relationship.
"""
from typing import Optional, Set

from models.file import File


def determine_parent(file_a: File, file_b: File) -> File:
    """
    Determine which of two files should be the parent based on specific rules.

    Rules (in order of consideration):
    1. Most recent active revision (Newer is better, unless exceptions apply).
    2. Highest resolution.
    3. Uncensored > Censored.
    4. Highest quality (filesize).
    5. Most lossless file format (png > jpg).
    
    Note: Requires 'tags' relationship to be loaded on the File objects for censorship checks.

    Returns:
        The File object that should be the parent.
    """
    # 0. Identify Newer and Older
    # If date_added is same, pick arbitrary (e.g. hash) to be stable
    if file_a.date_added > file_b.date_added:
        newer, older = file_a, file_b
    elif file_b.date_added > file_a.date_added:
        newer, older = file_b, file_a
    else:
        # Same date, use sha256 as tie breaker for stability
        if file_a.sha256_hash > file_b.sha256_hash:
            newer, older = file_a, file_b
        else:
            newer, older = file_b, file_a

    # Resolution Helpers
    def get_area(f: File) -> int:
        return (f.width or 0) * (f.height or 0)

    area_newer = get_area(newer)
    area_older = get_area(older)

    # 1. Resolution Check (Exception to Rule 1)
    # If Newer is significantly smaller (e.g. < 95%), Older wins (Bad revision exception)
    # If Newer is significantly larger, Newer wins (Good revision/Better res)
    # If similar (within 5%), proceed to next checks
    if area_newer < area_older * 0.95:
        return older
    if area_newer > area_older * 1.05:
        return newer

    # Resolution is similar. Proceed to next checks.

    # 2. Censorship Check
    def get_tag_names(f: File) -> Set[str]:
        try:
            return {t.name for t in f.tags}
        except (AttributeError, KeyError):
            # If tags not loaded or None, assume empty
            return set()

    tags_newer = get_tag_names(newer)
    tags_older = get_tag_names(older)

    newer_uncensored = "uncensored" in tags_newer
    older_uncensored = "uncensored" in tags_older

    # Preference for Uncensored
    if newer_uncensored and not older_uncensored:
        return newer
    if older_uncensored and not newer_uncensored:
        return older

    newer_censored = "censored" in tags_newer
    older_censored = "censored" in tags_older

    # Preference against Censored
    if newer_censored and not older_censored:
        return older
    if older_censored and not newer_censored:
        return newer

    # 3. Format Check (PNG > JPG)
    # "Most lossless file format"
    def is_lossless(f: File) -> bool:
        return f.file_ext.lower() in ('png', 'flac', 'wav')

    def is_lossy(f: File) -> bool:
        return f.file_ext.lower() in ('jpg', 'jpeg', 'webm', 'mp4')

    newer_lossless = is_lossless(newer)
    older_lossless = is_lossless(older)
    newer_lossy = is_lossy(newer)
    older_lossy = is_lossy(older)

    if newer_lossless and older_lossy:
        return newer
    if older_lossless and newer_lossy:
        return older

    # 4. Quality (Filesize)
    # "Larger filesize tends to mean higher quality"
    # Only use if not contradicted by resolution (already checked)
    if newer.file_size > older.file_size:
        return newer
    if older.file_size > newer.file_size:
        return older

    # 5. Default to Newer (Revision)
    return newer

