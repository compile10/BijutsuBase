"""Rating utility functions for BijutsuBase."""
from __future__ import annotations

from models.file import Rating


def get_allowed_ratings(max_rating: str | None) -> list[Rating] | None:
    """
    Get list of allowed Rating enum values up to and including max_rating.
    
    Returns a list of Rating enums from SAFE up to and including the specified
    max_rating. For example, if max_rating is "questionable", returns
    [Rating.SAFE, Rating.SENSITIVE, Rating.QUESTIONABLE].
    
    Args:
        max_rating: Maximum rating level as a string (safe, sensitive, questionable, explicit).
                   Case-insensitive. None returns None.
    
    Returns:
        List of Rating enums from SAFE to max_rating (inclusive), or None if max_rating
        is None or invalid.
    
    Example:
        >>> get_allowed_ratings("sensitive")
        [Rating.SAFE, Rating.SENSITIVE]
        >>> get_allowed_ratings("explicit")
        [Rating.SAFE, Rating.SENSITIVE, Rating.QUESTIONABLE, Rating.EXPLICIT]
        >>> get_allowed_ratings(None)
        None
    """
    if not max_rating:
        return None
    
    try:
        max_rating_enum = Rating(max_rating.lower())
    except ValueError:
        return None
    
    rating_order = [Rating.SAFE, Rating.SENSITIVE, Rating.QUESTIONABLE, Rating.EXPLICIT]
    max_index = rating_order.index(max_rating_enum)
    return rating_order[:max_index + 1]
