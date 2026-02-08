"""User-related schemas"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Request to create a new user."""

    user_id: str = Field(..., min_length=1, max_length=50)
    name: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)


class UserUpdate(BaseModel):
    """Request to update a user's profile."""

    name: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)


class UserResponse(BaseModel):
    """Response for user operations."""

    user_id: str
    name: str | None = None
    city: str | None = None
    created_at: datetime
    session_count: int = 0

class UserSessionSummary(BaseModel):
    """Summary of a user's session."""

    id: UUID
    created_at: datetime
    status: str
    message_count: int


class UserSessionsResponse(BaseModel):
    """Response for getting user sessions."""

    user_id: str
    sessions: list[UserSessionSummary]
    session_count: int


class UserWithSessions(BaseModel):
    """User with their sessions."""

    user_id: str
    name: str | None = None
    city: str | None = None
    created_at: datetime
    session_count: int
    sessions: list[UserSessionSummary]
