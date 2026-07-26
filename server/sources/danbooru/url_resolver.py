"""Resolve Danbooru post page URLs to their original media URLs."""

from urllib.parse import urlparse

import httpx

DANBOORU_POST_HOSTS = frozenset(
    {
        "danbooru.donmai.us",
        "www.danbooru.donmai.us",
    }
)


class DanbooruPostUnavailableError(ValueError):
    """Raised when a Danbooru post has no downloadable original file."""


class DanbooruApiError(RuntimeError):
    """Raised when Danbooru returns an invalid or unsuccessful API response."""


def get_danbooru_post_id(url: str) -> int | None:
    """Return the post ID when ``url`` is a canonical Danbooru post URL."""
    parsed = urlparse(url)
    if parsed.hostname is None or parsed.hostname.lower() not in DANBOORU_POST_HOSTS:
        return None

    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) != 2 or path_parts[0] != "posts" or not path_parts[1].isdigit():
        return None

    return int(path_parts[1])


async def resolve_danbooru_post_url(
    source_url: str,
    client: httpx.AsyncClient,
) -> str:
    """Resolve a Danbooru post page to its original file URL.

    Non-Danbooru URLs are returned unchanged. Query parameters on Danbooru post
    URLs are intentionally ignored because they only describe page navigation or
    search context.
    """
    post_id = get_danbooru_post_id(source_url)
    if post_id is None:
        return source_url

    response = await client.get(f"https://danbooru.donmai.us/posts/{post_id}.json")
    if response.status_code == 404:
        raise DanbooruPostUnavailableError(f"Danbooru post {post_id} was not found")
    if 400 <= response.status_code < 500:
        raise DanbooruPostUnavailableError(
            f"Danbooru post {post_id} could not be accessed ({response.status_code})"
        )
    if response.status_code != 200:
        raise DanbooruApiError(
            f"Danbooru returned {response.status_code} while resolving post {post_id}"
        )

    try:
        post = response.json()
    except ValueError as error:
        raise DanbooruApiError(
            f"Danbooru returned invalid metadata for post {post_id}"
        ) from error

    if not isinstance(post, dict):
        raise DanbooruApiError(
            f"Danbooru returned invalid metadata for post {post_id}"
        )

    file_url = post.get("file_url")
    if not isinstance(file_url, str) or not file_url.strip():
        raise DanbooruPostUnavailableError(
            f"Danbooru post {post_id} does not have an accessible original file"
        )

    parsed_file_url = urlparse(file_url)
    if parsed_file_url.scheme not in {"http", "https"} or not parsed_file_url.netloc:
        raise DanbooruApiError(
            f"Danbooru returned an invalid file URL for post {post_id}"
        )

    return file_url
