"""Common schemas for error and health responses"""

from datetime import datetime
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Error detail schema."""

    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    timestamp: datetime
    version: str | None = None
    database: str = "unknown"
    groq: str = "unknown"

