"""Errors raised by the Danbooru integration."""


class DanbooruApiError(RuntimeError):
    """Raised when a Danbooru API request fails or returns an unusable response."""


class DanbooruPostUnavailableError(ValueError):
    """Raised when a Danbooru post has no downloadable original file."""
