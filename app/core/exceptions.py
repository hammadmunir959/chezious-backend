"""Custom exception hierarchy for CheziousBot"""

from typing import Any


class ChatBotException(Exception):
    """Base exception for all chatbot errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationException(ChatBotException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class SessionNotFoundException(ChatBotException):
    """Raised when a session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session with ID '{session_id}' not found",
            code="SESSION_NOT_FOUND",
            details={"session_id": session_id},
        )


class UserNotFoundException(ChatBotException):
    """Raised when a user is not found."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User with ID '{user_id}' not found",
            code="USER_NOT_FOUND",
            details={"user_id": user_id},
        )


class UserAlreadyExistsException(ChatBotException):
    """Raised when a user already exists."""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User with ID '{user_id}' already exists",
            code="USER_ALREADY_EXISTS",
            details={"user_id": user_id},
        )


class GroqAPIException(ChatBotException):
    """Raised when Groq API call fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="GROQ_API_ERROR", details=details)


class DatabaseException(ChatBotException):
    """Raised when database operation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="DATABASE_ERROR", details=details)


class RateLimitException(ChatBotException):
    """Raised when rate limit is exceeded."""

    def __init__(self, user_id: str | None = None):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
            details={"user_id": user_id} if user_id else {},
        )


class ConfigurationException(ChatBotException):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="CONFIGURATION_ERROR", details=details)


class ServiceUnavailableException(ChatBotException):
    """Raised when an external service is unavailable."""

    def __init__(self, service: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=f"Service '{service}' is currently unavailable",
            code="SERVICE_UNAVAILABLE",
            details={"service": service, **(details or {})},
        )
