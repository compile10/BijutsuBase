from typing import Literal

from pydantic import BaseModel, HttpUrl


class TwitterMedia(BaseModel):
    """A single downloadable media item attached to a Twitter/X post."""

    # 1-based position, matching the /photo/<n> and /video/<n> post URLs
    index: int
    type: Literal["photo", "video", "animated_gif"]
    # Highest quality download URL (orig photo or highest bitrate MP4)
    url: str
    thumbnail_url: str
    width: int | None = None
    height: int | None = None


class TwitterPost(BaseModel):
    """A Twitter/X post and its media, resolved from a post URL."""

    id: str
    url: str
    author_screen_name: str
    author_name: str
    text: str
    media: list[TwitterMedia]


class TwitterResolveRequest(BaseModel):
    url: HttpUrl
