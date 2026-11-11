"""Danbooru API client for retrieving post information."""

import logging
from typing import Optional

import httpx
from pydantic import ValidationError

from api.serializers.danbooru import DanbooruPost, DanbooruTag
from .errors import DanbooruApiError

logger = logging.getLogger(__name__)


class DanbooruClient:
    """Client for interacting with the Danbooru API.
       Many booru sites use the same API, so this client can be used for any booru site 
      that uses the Danbooru API standard.
    """

    def __init__(
        self,
        base_url: str = "https://danbooru.donmai.us",
        username: Optional[str] = None,
        api_key: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        """
        Initialize the Danbooru client.

        Args:
            base_url: The base URL for the Danbooru instance (default: production)
            username: Optional username for authentication
            api_key: Optional API key for authentication
            transport: Optional httpx transport, used to stub requests in tests

        Raises:
            ValueError: If only one of username or api_key is provided
        """
        self.base_url = base_url.rstrip("/")

        # Validate that both username and api_key are provided together
        if (username is None) != (api_key is None):
            raise ValueError("Both username and api_key must be provided together, or both must be None")

        self.username = username
        self.api_key = api_key
        self.transport = transport

        # Shared headers for API requests
        self.headers = {
            "User-Agent": "BijutsuBase/0.1.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

    async def get_post(self, md5: str) -> list[DanbooruPost]:
        """
        Retrieve posts by MD5 hash.

        Args:
            md5: The MD5 hash of the file to search for

        Returns:
            A list of DanbooruPost objects matching the MD5 (typically 0 or 1 result)

        Raises:
            DanbooruApiError: If the request fails or the response is malformed
        """
        auth = None
        if self.username and self.api_key:
            auth = (self.username, self.api_key)

        try:
            async with httpx.AsyncClient(transport=self.transport) as client:
                response = await client.get(
                    f"{self.base_url}/posts.json",
                    params={"md5": md5},
                    auth=auth,
                    headers=self.headers,
                )
        except httpx.RequestError as error:
            raise DanbooruApiError(f"Failed to reach Danbooru: {error}") from error

        if response.status_code == 404:
            logger.debug(f"File with MD5 {md5} not found on Danbooru")
            return []
        if not response.is_success:
            raise DanbooruApiError(f"Danbooru returned {response.status_code} for MD5 {md5}")

        try:
            data = response.json()
        except ValueError:
            # Maintenance and challenge pages are served as HTML with a 200
            raise DanbooruApiError(f"Danbooru returned invalid JSON for MD5 {md5}") from None

        # A single match is returned as an object, multiple or none as a list
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise DanbooruApiError(f"Unexpected Danbooru response type: {type(data).__name__}")

        try:
            return [DanbooruPost.model_validate(post) for post in data]
        except ValidationError as error:
            raise DanbooruApiError(f"Danbooru returned an invalid post for MD5 {md5}") from error

    async def search_tags(self, query: str, limit: int = 20) -> list[DanbooruTag]:
        """
        Search for tags by name/pattern.

        Args:
            query: The tag name or pattern to search for
            limit: Maximum number of results to return

        Returns:
            A list of DanbooruTag objects matching the query.
        """
        url = f"{self.base_url}/tags.json"
        params = {
            "search[name_matches]": f"{query}*",
            "search[order]": "count",
            "search[hide_empty]": "yes",
            "limit": limit,
        }

        # Set up authentication if credentials are provided
        auth = None
        if self.username and self.api_key:
            auth = (self.username, self.api_key)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, auth=auth, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return [DanbooruTag(**tag) for tag in data]
        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Error searching Danbooru tags: {e}")
            return []
