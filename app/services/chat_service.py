"""Chat service for orchestrating chat interactions"""

from uuid import UUID
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationException, SessionNotFoundException, UserNotFoundException
from app.core.logging import get_logger
from app.services.session_service import SessionService
from app.services.context_service import ContextService
from app.services.user_service import UserService
from app.llm.groq_client import get_groq_client

logger = get_logger(__name__)


class ChatService:
    """Service for chat orchestration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_service = SessionService(db)
        self.context_service = ContextService(db)
        self.user_service = UserService(db)

    def validate_message(self, content: str) -> str:
        """
        Validate user message.

        Args:
            content: Message content

        Returns:
            Validated content

        Raises:
            ValidationException: If validation fails
        """
        content = content.strip()

        if not content:
            raise ValidationException("Message cannot be empty")

        if len(content) > settings.max_message_length:
            raise ValidationException(
                f"Message exceeds maximum length of {settings.max_message_length} characters",
                details={
                    "max_length": settings.max_message_length,
                    "provided_length": len(content),
                },
            )

        return content

    async def resolve_session(self, session_id: UUID | None, user_id: str | None) -> UUID:
        """
        Resolve the session ID to use for the chat.
        
        - Checks if provided session_id exists and is valid for the user.
        - Creates a new session if ID is missing, invalid, or unauthorized.
        """
        if session_id:
            try:
                existing_session = await self.session_service.get_session(session_id)
                
                # Check ownership if user_id is provided
                if user_id and existing_session.user_id != user_id:
                    logger.warning(
                        f"Session {session_id} belongs to user {existing_session.user_id}, "
                        f"not {user_id}. Creating new session."
                    )
                    session_id = None
                else:
                    logger.info(f"Resuming existing session {session_id}")
                    return session_id
            except SessionNotFoundException:
                logger.warning(f"Provided session {session_id} not found. Creating new session.")
                session_id = None

        # Create new session if execution reaches here
        if not user_id:
            raise ValidationException("user_id is required to create a new session")
        
        new_session = await self.session_service.create_session(user_id=user_id)
        logger.info(f"Auto-created session {new_session.id} for user {user_id}")
        return new_session.id

    async def handle_chat(
        self,
        user_message: str,
        session_id: UUID,  # Now expects a valid, resolved ID
        user_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Handle a chat request with streaming response.
        Assumes session_id is valid and exists (resolved via resolve_session).
        """
        # 1. Validate input
        user_message = self.validate_message(user_message)
        logger.info(f"Processing chat for session {session_id}")
        
        # 2. Re-verify session exists (should be cached/fast)
        try:
            chat_session = await self.session_service.get_session(session_id)
        except SessionNotFoundException:
            # Should not happen if resolve_session was called, but safety net:
             raise ValidationException("Session not found after resolution")
             
        logger.debug(f"Session verified: {chat_session.id}")
        
        # 3. Save user message...

        # 3. Save user message
        await self.context_service.save_message(
            session_id, "user", user_message
        )
        await self.session_service.increment_message_count(session_id)
        
        # Get user context from session (preferred) or fetch from user profile
        user_name = chat_session.user_name
        location = chat_session.location
        
        # Fall back to user profile if session doesn't have context
        if not user_name or not location:
            current_user_id = user_id or chat_session.user_id
            if current_user_id:
                try:
                    user = await self.user_service.get_user(current_user_id)
                    user_name = user_name or user.name
                    location = location or user.city
                except UserNotFoundException:
                    logger.debug(f"User {current_user_id} not found, proceeding without full context")
                except Exception as e:
                    logger.error(f"Unexpected error fetching user {current_user_id}: {e}")
        
        # 4. Commit the session NOW before streaming
        await self.db.commit()

        # 5. Get context messages
        context_messages = await self.context_service.get_context_messages(
            session_id
        )

        # 6. Build LLM messages (without current message since it's in context)
        llm_messages = self.context_service.build_messages_for_llm(
            context_messages[:-1],  # Exclude the just-saved message
            user_message,
            user_name=user_name,
            location=location,
        )

        # 7. Stream response from Groq
        full_response: list[str] = []
        async for token in get_groq_client().stream_chat(llm_messages):
            full_response.append(token)
            yield token

        # 8. Save assistant response (session will be committed by dependency)
        assistant_content = "".join(full_response)
        await self.context_service.save_message(
            session_id, "assistant", assistant_content
        )
        await self.session_service.increment_message_count(session_id)

        logger.info(
            f"Chat completed for session {session_id}",
            extra={"response_length": len(assistant_content)},
        )

    async def get_response(
        self,
        session_id: UUID,
        user_message: str,
    ) -> str:
        """
        Get a complete (non-streaming) response.

        Args:
            session_id: The session UUID
            user_message: The user's message

        Returns:
            Complete response text
        """
        tokens: list[str] = []
        async for token in self.handle_chat(session_id, user_message):
            tokens.append(token)
        return "".join(tokens)
