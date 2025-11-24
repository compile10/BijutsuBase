"""Utilities for interacting with Danbooru data."""

def map_danbooru_category_int_to_str(category_int: int) -> str:
    """Map Danbooru category integer to internal category string.
    
    Args:
        category_int: The integer category from Danbooru API.
        
    Returns:
        The corresponding string category for BijutsuBase.
    """
    if category_int == 1:
        return "artist"
    elif category_int == 3:
        return "copyright"
    elif category_int == 4:
        return "character"
    elif category_int == 5:
        return "meta"
    else:
        # 0 is general, but also default to general for unknown values
        return "general"

