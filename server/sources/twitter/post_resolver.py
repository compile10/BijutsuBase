"""Resolve Twitter/X post URLs to their highest quality media URLs.

Uses the unauthenticated syndication endpoint that powers embedded tweets, so
no account cookies or API keys are needed. Posts that require login (protected
accounts, some age-restricted media) are reported as unavailable.
"""

import math
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from api.serializers.twitter import TwitterMedia, TwitterPost

TWITTER_POST_HOSTS = frozenset(
    {
        "twitter.com",
        "www.twitter.com",
        "mobile.twitter.com",
        "x.com",
        "www.x.com",
        "mobile.x.com",
    }
)
TWITTER_IMAGE_HOST = "pbs.twimg.com"
SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"

# Post IDs are 64-bit snowflakes, so at most 20 digits
_POST_PATH_PATTERN = re.compile(r"^/(?:i/web|i|[A-Za-z0-9_]+)/status(?:es)?/(\d{1,20})(?:/|$)")
_BASE36_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class TwitterPostUnavailableError(ValueError):
    """Raised when a post does not exist, is private, or has no media."""


class TwitterApiError(RuntimeError):
    """Raised when the syndication API returns an invalid or unsuccessful response."""


def get_twitter_post_id(url: str) -> str | None:
    """Return the post ID when ``url`` is a Twitter/X post URL."""
    parsed = urlparse(url)
    if parsed.hostname is None or parsed.hostname.lower() not in TWITTER_POST_HOSTS:
        return None

    match = _POST_PATH_PATTERN.match(parsed.path)
    if match is None:
        return None

    return match.group(1)


def to_twimg_size_url(media_url: str, size: str) -> str:
    """Rewrite a pbs.twimg.com image URL to request a specific named size.

    Handles the legacy ``<id>.jpg:large`` form, the extension form
    ``<id>.jpg`` and the query form ``<id>?format=jpg&name=small``. The format
    is preserved because requesting a different one (e.g. png for a jpg upload)
    returns 404. Non-twimg URLs are returned unchanged.
    """
    parsed = urlparse(media_url)
    if parsed.hostname != TWITTER_IMAGE_HOST:
        return media_url

    path = parsed.path.split(":", 1)[0]
    query = parse_qs(parsed.query)
    image_format = query.get("format", [None])[0]

    directory, _, filename = path.rpartition("/")
    stem, dot, extension = filename.rpartition(".")
    if dot:
        filename = stem
        image_format = image_format or extension

    if image_format is None:
        return media_url

    new_query = urlencode({"format": image_format, "name": size})
    return f"https://{TWITTER_IMAGE_HOST}{directory}/{filename}?{new_query}"


def _syndication_token(post_id: str) -> str:
    """Port of the embed widget token: ((id / 1e15) * PI).toString(36) without 0s and dots.

    The endpoint does not currently validate it, but the embed widget always
    sends one, so we do too.
    """
    value = (int(post_id) / 1e15) * math.pi
    integer_part = int(value)
    fraction = value - integer_part

    digits = ""
    while integer_part:
        integer_part, remainder = divmod(integer_part, 36)
        digits = _BASE36_DIGITS[remainder] + digits

    for _ in range(11):
        fraction *= 36
        digit = int(fraction)
        digits += _BASE36_DIGITS[digit]
        fraction -= digit

    return digits.replace("0", "")


def _best_video_url(media: dict[str, Any]) -> str | None:
    video_info = media.get("video_info")
    variants = video_info.get("variants") if isinstance(video_info, dict) else None
    if not isinstance(variants, list):
        return None

    mp4_variants = [
        variant
        for variant in variants
        if isinstance(variant, dict)
        and variant.get("content_type") == "video/mp4"
        and isinstance(variant.get("url"), str)
    ]
    if not mp4_variants:
        return None

    best = max(
        mp4_variants,
        key=lambda variant: variant["bitrate"] if isinstance(variant.get("bitrate"), int) else 0,
    )
    return best["url"]


def _parse_media(media_details: list[dict[str, Any]]) -> list[TwitterMedia]:
    media_items: list[TwitterMedia] = []
    for media in media_details:
        media_type = media.get("type")
        preview_url = media.get("media_url_https")
        if not isinstance(preview_url, str):
            continue

        if media_type == "photo":
            download_url = to_twimg_size_url(preview_url, "orig")
        elif media_type in {"video", "animated_gif"}:
            download_url = _best_video_url(media)
        else:
            continue

        if download_url is None:
            continue

        original_info = media.get("original_info")
        if not isinstance(original_info, dict):
            original_info = {}
        width = original_info.get("width")
        height = original_info.get("height")
        media_items.append(
            TwitterMedia(
                index=len(media_items) + 1,
                type=media_type,
                url=download_url,
                thumbnail_url=to_twimg_size_url(preview_url, "small"),
                width=width if isinstance(width, int) else None,
                height=height if isinstance(height, int) else None,
            )
        )

    return media_items


def _unavailable_message(post_id: str, post: dict[str, Any]) -> str:
    """Explain a tombstone, using Twitter's own reason (e.g. age restriction) when given."""
    login_hint = "BijutsuBase reads posts without logging in, so this one can't be imported."
    tombstone = post.get("tombstone")
    text = tombstone.get("text") if isinstance(tombstone, dict) else None
    reason = text.get("text") if isinstance(text, dict) else None
    if isinstance(reason, str) and reason.strip():
        return f"Post {post_id} is unavailable: {reason.strip()} {login_hint}"

    return (
        f"Post {post_id} is unavailable. It may be age-restricted, from a protected or "
        f"suspended account, or deleted. {login_hint}"
    )


async def resolve_twitter_post(
    source_url: str,
    client: httpx.AsyncClient,
) -> TwitterPost:
    """Fetch a post's metadata and return its media at the highest available quality."""
    post_id = get_twitter_post_id(source_url)
    if post_id is None:
        raise ValueError(f"Not a Twitter/X post URL: {source_url}")

    response = await client.get(
        SYNDICATION_URL,
        params={"id": post_id, "token": _syndication_token(post_id), "lang": "en"},
    )
    if response.status_code == 404:
        raise TwitterPostUnavailableError(
            f"Post {post_id} was not found. It may have been deleted or belong to a "
            "protected account, which can't be read without logging in."
        )
    if response.status_code == 429:
        raise TwitterApiError(
            f"Twitter is rate limiting requests while resolving post {post_id}; "
            "try again in a few minutes"
        )
    if 400 <= response.status_code < 500:
        raise TwitterPostUnavailableError(
            f"Post {post_id} could not be accessed ({response.status_code})"
        )
    if response.status_code != 200:
        raise TwitterApiError(
            f"Twitter returned {response.status_code} while resolving post {post_id}"
        )

    try:
        post = response.json()
    except ValueError as error:
        raise TwitterApiError(f"Twitter returned invalid metadata for post {post_id}") from error

    if not isinstance(post, dict):
        raise TwitterApiError(f"Twitter returned invalid metadata for post {post_id}")

    # Deleted, suspended, or login-gated posts come back as tombstones
    if post.get("__typename") == "TweetTombstone" or not isinstance(post.get("user"), dict):
        raise TwitterPostUnavailableError(_unavailable_message(post_id, post))

    media_details = post.get("mediaDetails") or []
    if not isinstance(media_details, list) or not all(
        isinstance(media, dict) for media in media_details
    ):
        raise TwitterApiError(f"Twitter returned invalid media metadata for post {post_id}")

    media_items = _parse_media(media_details)
    if not media_items:
        raise TwitterPostUnavailableError(f"Post {post_id} has no downloadable media")

    user = post["user"]
    screen_name = user.get("screen_name") or "i"
    return TwitterPost(
        id=post_id,
        url=f"https://x.com/{screen_name}/status/{post_id}",
        author_screen_name=screen_name,
        author_name=user.get("name") or screen_name,
        text=post.get("text") or "",
        media=media_items,
    )
