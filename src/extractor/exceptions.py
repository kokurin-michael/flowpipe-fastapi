class UrlError(ValueError):
    """Raised when the provided URL is not a supported YouTube single-video URL."""


class CookiesFileError(ValueError):
    """Raised when cookies file is missing, invalid, or unreadable."""
