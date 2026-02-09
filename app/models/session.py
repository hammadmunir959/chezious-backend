"""Chat session model"""

from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.message import Message

from app.utils.time import utc_now

# Use Enum for database compatibility and strict validation
class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ChatSession(SQLModel, table=True):
    """
    Represents an individual chat session for a user.
    """

    __tablename__ = "chat_sessions"

    id: UUID = Field(
        default_factory=uuid4, 
        primary_key=True,
        description="Unique identifier for the session"
    )
    
    user_id: str = Field(
        foreign_key="users.user_id", 
        index=True,
        max_length=50,
        description="The ID of the user who owns this session"
    )
    
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        index=True,
        description="Current state of the session"
    )
    
    message_count: int = Field(
        default=0,
        description="Total number of messages in this session"
    )
    
    # Context fields captured at creation
    user_name: str | None = Field(
        default=None, 
        max_length=100,
        description="The user's display name at session start"
    )
    
    location: str | None = Field(
        default=None, 
        max_length=100,
        description="The user's city/location at session start"
    )
    
    # Lifecycle timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        index=True,
        description="Timestamp when the session was created"
    )
    
    last_activity_at: datetime = Field(
        default_factory=utc_now,
        index=True,
        description="Timestamp of the most recent message or interaction"
    )
    
    # Relationships
    user: "User" = Relationship(back_populates="sessions")
    messages: list["Message"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def increment_message_count(self) -> None:
        """Update message counter and refresh activity timestamp."""
        self.message_count += 1
        self.update_activity()

    def update_activity(self) -> None:
        """Refresh the last activity timestamp to current UTC time."""
        self.last_activity_at = utc_now()

    def archive(self) -> None:
        """Set session status to archived."""
        self.status = SessionStatus.ARCHIVED

    @property
    def is_active(self) -> bool:
        """Returns True if the session is in 'active' state and not expired."""
        return self.status == SessionStatus.ACTIVE and not self.is_expired

