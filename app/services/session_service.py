"""Session service for managing chat sessions"""

from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.session import ChatSession, SessionStatus
from app.models.user import User
from app.core.exceptions import SessionNotFoundException, UserNotFoundException
from app.core.logging import get_logger
from app.services.user_service import UserService

logger = get_logger(__name__)


class SessionService:
    """Service layer for chat session operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)

    async def create_session(
        self, 
        user_id: str, 
        session_id: Optional[UUID] = None,
        user_name: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ChatSession:
        """
        Create a new chat session.
        
        If session_id is provided, it attempts to use that ID (useful for idempotent creation).
        If user_name/location are not provided, it attempts to inherit them from the User profile.
        
        Args:
            user_id: ID of the owner
            session_id: Optional specific UUID for the session
            user_name: Contextual display name
            location: Contextual location
            
        Returns:
            The created ChatSession persisted in the DB.
        """
        # Ensure user exists and get their profile data
        user = await self.user_service.get_or_create_user(user_id)
        
        # Fallback to user profile if specific context isn't provided
        final_user_name = user_name or user.name
        final_location = location or user.city

        # Prepare arguments (filter out None to let defaults work if needed)
        session_kwargs = {
            "user_id": user_id,
            "user_name": final_user_name,
            "location": final_location,
        }
        if session_id:
            session_kwargs["id"] = session_id

        chat_session = ChatSession(**session_kwargs)
        
        self.db.add(chat_session)
        await self.db.flush()
        
        # Update user stats
        await self.user_service.increment_session_count(user_id)
        
        logger.info(f"Session created: {chat_session.id} (User: {user_id})")
        return chat_session

    async def get_session(self, session_id: UUID) -> ChatSession:
        """
        Retrieve a session by ID.
        
        Raises:
            SessionNotFoundException: If session does not exist.
        """
        chat_session = await self.db.get(ChatSession, session_id)
        
        if not chat_session:
            raise SessionNotFoundException(str(session_id))

        return chat_session

    async def get_user_sessions(
        self, 
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        min_messages: int = 0
    ) -> List[ChatSession]:
        """
        Retrieve active sessions for a specific user.
        
        Args:
            min_messages: Filter out empty sessions with fewer than N messages.
        """
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.status == SessionStatus.ACTIVE,
                ChatSession.message_count >= min_messages
            )
            .order_by(ChatSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_session(
        self, user_id: str, session_id: UUID
    ) -> ChatSession:
        """
        Retrieve a specific session owned by a specific user.
        
        Raises:
            SessionNotFoundException: If session missing or belongs to another user.
        """
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        )
        result = await self.db.execute(stmt)
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            raise SessionNotFoundException(str(session_id))

        return chat_session

    async def delete_session(self, session_id: UUID) -> None:
        """
        Delete a session.
        """
        chat_session = await self.get_session(session_id)
        await self.db.delete(chat_session)
        await self.db.flush()
        logger.info(f"Session deleted: {session_id}")

    async def increment_message_count(self, session_id: UUID) -> None:
        """Atomic increment of message count for a session."""
        chat_session = await self.get_session(session_id)
        chat_session.increment_message_count()
        await self.db.flush()
