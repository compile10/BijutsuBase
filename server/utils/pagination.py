"""Pagination utilities for BijutsuBase API."""
from __future__ import annotations

import json
import base64
from datetime import datetime

from fastapi import HTTPException, status


def encode_cursor(sort_value: datetime | int, sha256_hash: str) -> str:
    """
    Encode cursor for pagination.
    
    Args:
        sort_value: The value used for sorting (date_added or file_size)
        sha256_hash: The SHA256 hash of the file
        
    Returns:
        Base64-encoded JSON string containing the cursor data
    """
    cursor_data = {
        "sort_value": sort_value.isoformat() if isinstance(sort_value, datetime) else sort_value,
        "sha256": sha256_hash
    }
    json_str = json.dumps(cursor_data)
    return base64.b64encode(json_str.encode()).decode()


def decode_cursor(cursor_str: str) -> tuple[datetime | int, str]:
    """
    Decode cursor for pagination.
    
    Args:
        cursor_str: Base64-encoded JSON string containing cursor data
        
    Returns:
        Tuple of (sort_value, sha256_hash)
        
    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        json_str = base64.b64decode(cursor_str.encode()).decode()
        cursor_data = json.loads(json_str)
        sort_value = cursor_data["sort_value"]
        sha256_hash = cursor_data["sha256"]
        
        # Try to parse as datetime if it looks like an ISO format
        if isinstance(sort_value, str) and "T" in sort_value:
            sort_value = datetime.fromisoformat(sort_value)
        
        return sort_value, sha256_hash
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}"
        )

