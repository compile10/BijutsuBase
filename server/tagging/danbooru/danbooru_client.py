"""Danbooru API client for retrieving post information."""

import logging
from typing import Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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

    async def get_post(self, md5: str) -> list[DanbooruPost]:
        """
        Retrieve posts by MD5 hash.

        Args:
            md5: The MD5 hash of the file to search for

        Returns:
            A list of DanbooruPost objects matching the MD5 (typically 0 or 1 result).
            Returns an empty list if the file is not found or if there's an error.
            All errors are handled gracefully to allow the upload process to continue.
        """
        url = f"{self.base_url}/posts.json"
        params = {"md5": md5}

        # Set up authentication if credentials are provided
        auth = None
        if self.username and self.api_key:
            auth = (self.username, self.api_key)

        # Set up headers for API requests
        headers = {
            "User-Agent": "BijutsuBase/0.1.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }

        # Make the API request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, auth=auth, headers=headers)
                
                # Handle 404 (file not found) gracefully
                if response.status_code == 404:
                    logger.debug(f"File with MD5 {md5} not found on Danbooru")
                    result = []
                    return result
                
                # Raise for other HTTP errors
                response.raise_for_status()

                # Parse the JSON response
                # Danbooru returns a dict for single post, list for multiple/empty
                data = response.json()
                if isinstance(data, dict):
                    # Single post returned as dict - wrap in list
                    result = [DanbooruPost(**data)]
                elif isinstance(data, list):
                    # Multiple posts or empty list
                    result = [DanbooruPost(**post) for post in data]
                else:
                    # Unexpected format
                    logger.warning(f"Unexpected response format from Danbooru API: {type(data)}")
                    return []

                return result
        except httpx.HTTPStatusError as e:
            # Handle other HTTP errors gracefully (e.g., 500, 503, etc.)
            logger.warning(
                f"Danbooru API returned error {e.response.status_code} for MD5 {md5}: {e.response.text[:200]}"
            )
            # Return empty list to allow upload to proceed without Danbooru metadata
            return []
        except httpx.RequestError as e:
            # Network errors (connection errors, timeouts, etc.) - log and return empty list
            logger.error(f"Network error when querying Danbooru API for MD5 {md5}: {e}")
            # Return empty list to allow upload to proceed without Danbooru metadata
            return []

