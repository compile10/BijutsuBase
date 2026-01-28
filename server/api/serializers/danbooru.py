from typing import Optional
from pydantic import BaseModel

class DanbooruPost(BaseModel):
    """Pydantic model representing a Danbooru post response."""

    # Required integer fields
    id: int

    # Tag strings (can be empty strings but always present)
    tag_string_general: str = ""
    tag_string_artist: str = ""
    tag_string_copyright: str = ""
    tag_string_character: str = ""
    tag_string_meta: str = ""

    # File/media fields (can be null for restricted content)
    source: Optional[str] = None
    md5: Optional[str] = None
    file_url: Optional[str] = None
    large_file_url: Optional[str] = None
    preview_file_url: Optional[str] = None

    # Boolean fields
    has_children: bool = False

    # Optional/nullable fields
    rating: str = "e"  # Values: g, s, q, e - defaults to explicit
    parent_id: Optional[int] = None
    pixiv_id: Optional[int] = None


class DanbooruTag(BaseModel):
    """Pydantic model representing a Danbooru tag response."""

    id: int
    name: str
    category: int
    post_count: int
    is_deprecated: bool

