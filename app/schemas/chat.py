"""Chat-related schemas"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.config import settings


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    session_id: UUID | None = None

    message: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_message_length,
    )


class ChatMessage(BaseModel):
    """A single chat message."""

    id: UUID
    role: str
    content: str
    created_at: datetime


class MessagesResponse(BaseModel):
    """Response for getting session messages."""

    session_id: UUID
    user_id: str
    messages: list[ChatMessage]
