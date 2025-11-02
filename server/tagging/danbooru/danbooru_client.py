"""Danbooru API client for retrieving post information."""

from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field


class DanbooruPost(BaseModel):
    """Pydantic model representing a Danbooru post response."""

    # Required integer fields
    id: int
    uploader_id: int
    approver_id: int

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
    file_ext: str

    # Required boolean
    has_children: bool

    # Optional/nullable fields
    rating: Optional[str] = None  # Values: g, s, q, e
    parent_id: Optional[int] = None


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
    ):
        """
        Initialize the Danbooru client.

        Args:
            base_url: The base URL for the Danbooru instance (default: production)
            username: Optional username for authentication
            api_key: Optional API key for authentication

        Raises:
            ValueError: If only one of username or api_key is provided
        """
        self.base_url = base_url.rstrip("/")

        # Validate that both username and api_key are provided together
        if (username is None) != (api_key is None):
            raise ValueError("Both username and api_key must be provided together, or both must be None")

        self.username = username
        self.api_key = api_key
        self._cache: dict = {}

    def _get_cached(self, method_name: str, *args) -> Optional[Any]:
        """
        Retrieve a cached value for a method call.

        Args:
            method_name: Name of the method being called
            *args: Arguments passed to the method

        Returns:
            Cached value if found, None otherwise
        """
        cache_key = (method_name, *args)
        return self._cache.get(cache_key)

    def _set_cached(self, method_name: str, *args, value: Any) -> None:
        """
        Store a value in the cache for a method call.

        Args:
            method_name: Name of the method being called
            *args: Arguments passed to the method
            value: The value to cache
        """
        cache_key = (method_name, *args)
        self._cache[cache_key] = value

    def get_post(self, md5: str) -> list[DanbooruPost]:
        """
        Retrieve posts by MD5 hash.

        Args:
            md5: The MD5 hash of the file to search for

        Returns:
            A list of DanbooruPost objects matching the MD5 (typically 0 or 1 result)

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code
            httpx.RequestError: If there's a network error
        """
        # Check cache first
        cached_result = self._get_cached("get_post", md5)
        if cached_result is not None:
            return cached_result

        url = f"{self.base_url}/posts.json"
        params = {"md5": md5}

        # Set up authentication if credentials are provided
        auth = None
        if self.username and self.api_key:
            auth = (self.username, self.api_key)

        # Make the API request
        with httpx.Client() as client:
            response = client.get(url, params=params, auth=auth)
            response.raise_for_status()

            # Parse the JSON response as a list of DanbooruPost objects
            data = response.json()
            result = [DanbooruPost(**post) for post in data]

            # Cache the result before returning
            self._set_cached("get_post", md5, value=result)
            return result

