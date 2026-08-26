"""Exceptions raised by the ModeraShield SDK."""


class ModerashieldError(Exception):
    """Base class for SDK errors safe to show to normal SDK users."""


class APIError(ModerashieldError):
    """An API response could not be completed successfully."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(APIError):
    """The API key was missing, invalid, inactive, or unauthorized."""


class BadRequestError(APIError):
    """The API rejected the moderation request."""


class NotFoundError(APIError):
    """The requested moderation job does not exist or is not accessible."""


class ServerError(APIError):
    """The ModeraShield service returned a 5xx response."""


class ModerashieldTimeoutError(ModerashieldError):
    """The moderation job did not reach a terminal state before the timeout."""


class NetworkError(ModerashieldError):
    """The SDK could not connect to the ModeraShield API."""


class MalformedResponseError(APIError):
    """The API returned JSON that does not match the documented API contract."""
