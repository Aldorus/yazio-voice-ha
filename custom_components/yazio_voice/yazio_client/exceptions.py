class YazioError(Exception):
    """Generic Yazio client error."""


class YazioAuthError(YazioError):
    """Authentication or token refresh failure."""
