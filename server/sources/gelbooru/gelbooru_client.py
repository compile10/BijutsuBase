"""Gelbooru API client for retrieving post and tag information."""

import html
import logging
import os
import re
from typing import Any, Optional

import httpx
from pydantic import ValidationError

from api.serializers.gelbooru import GelbooruPost, GelbooruTag
from .errors import GelbooruApiError, GelbooruNotConfiguredError

logger = logging.getLogger(__name__)

# The tag endpoint returns at most 100 tags per request by default
TAG_LOOKUP_BATCH_SIZE = 100

_API_KEY_PATTERN = re.compile(r"(api_key=)[^&\s\"']+")


def redact_api_key(text: str) -> str:
    """Mask Gelbooru API keys embedded in request URLs."""
    return _API_KEY_PATTERN.sub(r"\1[REDACTED]", text)


class _RedactApiKeyFilter(logging.Filter):
    """Strip Gelbooru API keys from httpx's per-request INFO logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "api_key=" in message:
            record.msg = redact_api_key(message)
            record.args = None
        return True


# Gelbooru only accepts credentials as query parameters, which httpx logs verbatim
logging.getLogger("httpx").addFilter(_RedactApiKeyFilter())


class GelbooruClient:
    """Client for the Gelbooru DAPI.

    Gelbooru rejects anonymous API requests, so every lookup raises
    `GelbooruNotConfiguredError` unless both an API key and user ID are configured
    (via arguments or the `GELBOORU_API_KEY` / `GELBOORU_USER_ID` environment
    variables).
    """

    def __init__(
        self,
        base_url: str = "https://gelbooru.com",
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        """
        Initialize the Gelbooru client.

        Args:
            base_url: The base URL for the Gelbooru instance
            api_key: API key; defaults to the `GELBOORU_API_KEY` environment variable
            user_id: User ID; defaults to the `GELBOORU_USER_ID` environment variable
            transport: Optional httpx transport, used to stub requests in tests
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("GELBOORU_API_KEY") or None
        self.user_id = user_id or os.getenv("GELBOORU_USER_ID") or None

        # A half-configured client is a deployment mistake; treat it as unconfigured
        if (self.api_key is None) != (self.user_id is None):
            logger.warning("Gelbooru lookups disabled: GELBOORU_API_KEY and GELBOORU_USER_ID must both be set")

        self.transport = transport
        self.headers = {
            "User-Agent": "BijutsuBase/0.1.0",
            "Accept": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """Whether credentials are available for API requests."""
        return self.api_key is not None and self.user_id is not None

    async def get_post(self, md5: str) -> list[GelbooruPost]:
        """
        Retrieve posts by MD5 hash.

        Args:
            md5: The MD5 hash of the file to search for

        Returns:
            A list of GelbooruPost objects matching the MD5 (typically 0 or 1 result)

        Raises:
            GelbooruNotConfiguredError: If credentials are not configured
            GelbooruApiError: If the request fails or the response is malformed
        """
        data = await self._dapi_get("post", {"tags": f"md5:{md5}"})
        try:
            return [GelbooruPost(**post) for post in _extract_items(data, "post")]
        except ValidationError as error:
            raise GelbooruApiError(f"Gelbooru returned an invalid post for MD5 {md5}") from error

    async def fetch_post_by_id(self, post_id: int) -> Optional[dict[str, Any]]:
        """
        Retrieve a single post's raw metadata by ID.

        Returns:
            The post object, or None when no post has this ID

        Raises:
            GelbooruNotConfiguredError: If credentials are not configured
            GelbooruApiError: If the request fails or the response is malformed
        """
        data = await self._dapi_get("post", {"id": post_id})
        posts = _extract_items(data, "post")
        return next((post for post in posts if str(post.get("id")) == str(post_id)), None)

    async def get_tag_types(self, tag_names: list[str]) -> dict[str, int]:
        """
        Look up the category type of each tag.

        Gelbooru posts only list tag names, so categories need a second request
        against the tag endpoint.

        Args:
            tag_names: Unescaped tag names to look up

        Returns:
            A mapping of tag name to Gelbooru tag type. Tags that Gelbooru does not
            return are omitted.

        Raises:
            GelbooruNotConfiguredError: If credentials are not configured
            GelbooruApiError: If any request fails, so callers can avoid storing tags
                with guessed categories
        """
        tag_types: dict[str, int] = {}

        for start in range(0, len(tag_names), TAG_LOOKUP_BATCH_SIZE):
            batch = tag_names[start:start + TAG_LOOKUP_BATCH_SIZE]
            data = await self._dapi_get(
                "tag",
                {"names": " ".join(batch), "limit": TAG_LOOKUP_BATCH_SIZE},
            )
            try:
                tags = [GelbooruTag(**item) for item in _extract_items(data, "tag")]
            except ValidationError as error:
                raise GelbooruApiError("Gelbooru returned an invalid tag") from error

            # Every tag on a live post exists on Gelbooru, so an empty answer means the
            # lookup failed; accepting it would store every tag as general
            if not tags:
                raise GelbooruApiError("Gelbooru tag lookup returned no tags for a non-empty request")

            for tag in tags:
                tag_types[html.unescape(tag.name)] = tag.type

        return tag_types

    async def _dapi_get(self, resource: str, params: dict[str, Any]) -> Any:
        """Issue an authenticated JSON request against a DAPI index endpoint.

        Raises:
            GelbooruNotConfiguredError: If credentials are not configured
            GelbooruApiError: If the request fails, is rejected, or returns invalid JSON
        """
        if not self.is_configured:
            raise GelbooruNotConfiguredError(
                "Gelbooru API credentials are not configured; set GELBOORU_API_KEY and GELBOORU_USER_ID"
            )

        request_params = {
            "page": "dapi",
            "s": resource,
            "q": "index",
            "json": 1,
            "api_key": self.api_key,
            "user_id": self.user_id,
            **params,
        }

        try:
            async with httpx.AsyncClient(transport=self.transport) as client:
                response = await client.get(
                    f"{self.base_url}/index.php",
                    params=request_params,
                    headers=self.headers,
                )
        except httpx.RequestError as error:
            # Chained exceptions would carry the request URL, which includes the API key
            raise GelbooruApiError(f"Failed to reach Gelbooru: {redact_api_key(str(error))}") from None

        if response.status_code in {401, 403}:
            raise GelbooruApiError(
                f"Gelbooru rejected the configured credentials ({response.status_code})"
            )
        if not response.is_success:
            raise GelbooruApiError(f"Gelbooru returned {response.status_code}")

        try:
            return response.json()
        except ValueError:
            raise GelbooruApiError("Gelbooru returned invalid JSON") from None


def _extract_items(data: Any, key: str) -> list[dict[str, Any]]:
    """Return the result list from a DAPI JSON response.

    Gelbooru omits the result key entirely when nothing matches, and may return a
    single object instead of a list.

    Raises:
        GelbooruApiError: If the response is not a DAPI envelope of result objects
    """
    if not isinstance(data, dict):
        raise GelbooruApiError(f"Unexpected Gelbooru response type: {type(data).__name__}")

    items = data.get(key)
    if items is None:
        return []
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise GelbooruApiError(f"Unexpected Gelbooru '{key}' payload")

    return items
