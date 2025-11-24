from typing import Optional
from pydantic import BaseModel

class DanbooruPost(BaseModel):
    """Pydantic model representing a Danbooru post response."""

    # Required integer fields
    id: int

    # Required tag strings
    tag_string_general: str
    tag_string_artist: str
    tag_string_copyright: str
    tag_string_character: str
    tag_string_meta: str

    # Required file/media fields
    source: str
    md5: str
    file_url: str
    large_file_url: str
    preview_file_url: str

    # Required boolean
    has_children: bool

    # Optional/nullable fields
    rating: Optional[str] = None  # Values: g, s, q, e
    parent_id: Optional[int] = None
    pixiv_id: Optional[int] = None


class DanbooruTag(BaseModel):
    """Pydantic model representing a Danbooru tag response."""

    id: int
    name: str
    category: int
    post_count: int
    is_deprecated: bool

