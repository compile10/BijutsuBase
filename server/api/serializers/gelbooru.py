from typing import Optional
from pydantic import BaseModel


class GelbooruPost(BaseModel):
    """Pydantic model representing a Gelbooru post response."""

    id: int

    # Space-separated, HTML-escaped tag names without category information
    tags: str = ""

    md5: Optional[str] = None
    source: Optional[str] = None
    file_url: Optional[str] = None

    # Values: general, sensitive, questionable, explicit - defaults to explicit
    rating: str = "explicit"


class GelbooruTag(BaseModel):
    """Pydantic model for the tag-endpoint fields needed to categorize post tags."""

    name: str
    # Integer using the Danbooru category numbering (0 general, 1 artist,
    # 3 copyright, 4 character, 5 metadata) plus 6 for deprecated tags
    type: int = 0
