"""Resolve Gelbooru post page URLs to their original media URLs."""

from urllib.parse import parse_qs, urlparse

from .errors import GelbooruApiError, GelbooruNotConfiguredError, GelbooruPostUnavailableError
from .gelbooru_client import GelbooruClient

GELBOORU_POST_HOSTS = frozenset(
    {
        "gelbooru.com",
        "www.gelbooru.com",
    }
)


def get_gelbooru_post_id(url: str) -> int | None:
    """Return the post ID when ``url`` is a Gelbooru post view URL.

    Post pages look like ``/index.php?page=post&s=view&id=123``, optionally with
    extra navigation parameters such as ``tags``.
    """
    parsed = urlparse(url)
    if parsed.hostname is None or parsed.hostname.lower() not in GELBOORU_POST_HOSTS:
        return None
    if parsed.path not in {"", "/", "/index.php"}:
        return None

    query = parse_qs(parsed.query)
    if query.get("page") != ["post"] or query.get("s") != ["view"]:
        return None

    post_ids = query.get("id")
    if post_ids is None or len(post_ids) != 1 or not (post_ids[0].isascii() and post_ids[0].isdigit()):
        return None

    return int(post_ids[0])


async def resolve_gelbooru_post_url(
    source_url: str,
    gelbooru: GelbooruClient,
) -> str:
    """Resolve a Gelbooru post page to its original file URL.

    Non-Gelbooru URLs are returned unchanged. Gelbooru rejects anonymous API
    calls, so resolving a post requires configured credentials.

    Raises:
        GelbooruNotConfiguredError: If Gelbooru credentials are not configured
        GelbooruPostUnavailableError: If the post is missing or has no original file
        GelbooruApiError: If the request fails or Gelbooru returns unusable data
    """
    post_id = get_gelbooru_post_id(source_url)
    if post_id is None:
        return source_url

    if not gelbooru.is_configured:
        raise GelbooruNotConfiguredError(
            "Gelbooru post URLs need a Gelbooru API key, which this server does not have. "
            "Set GELBOORU_API_KEY and GELBOORU_USER_ID on the server, "
            "or upload the direct image URL instead."
        )

    post = await gelbooru.fetch_post_by_id(post_id)
    if post is None:
        raise GelbooruPostUnavailableError(f"Gelbooru post {post_id} was not found")

    file_url = post.get("file_url")
    if not isinstance(file_url, str) or not file_url.strip():
        raise GelbooruPostUnavailableError(
            f"Gelbooru post {post_id} does not have an accessible original file"
        )

    parsed_file_url = urlparse(file_url)
    if parsed_file_url.scheme not in {"http", "https"} or not parsed_file_url.netloc:
        raise GelbooruApiError(
            f"Gelbooru returned an invalid file URL for post {post_id}"
        )

    return file_url
