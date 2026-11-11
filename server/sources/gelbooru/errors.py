"""Errors raised by the Gelbooru integration."""


class GelbooruApiError(RuntimeError):
    """Raised when a Gelbooru API request fails or returns an unusable response."""


class GelbooruNotConfiguredError(RuntimeError):
    """Raised when Gelbooru API credentials are not configured."""


class GelbooruPostUnavailableError(ValueError):
    """Raised when a Gelbooru post has no downloadable original file."""
