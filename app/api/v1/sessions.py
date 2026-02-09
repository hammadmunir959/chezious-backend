"""Session-related endpoints"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.session_service import SessionService
from app.services.context_service import ContextService
from app.schemas.session import SessionResponse, SessionCreate
from app.schemas.chat import MessagesResponse, ChatMessage

router = APIRouter(prefix="/sessions", tags=["Sessions"])





@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: UUID = Path(..., title="Session ID", description="The unique identifier of the session"),
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    """Get session details."""
    service = SessionService(session)
    chat_session = await service.get_session(session_id)

    return SessionResponse(
        id=chat_session.id,
        user_id=chat_session.user_id,
        created_at=chat_session.created_at,
        status=chat_session.status,
        message_count=chat_session.message_count,
        user_name=chat_session.user_name,
        location=chat_session.location,
    )


@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(
    session_id: UUID = Path(..., title="Session ID", description="The unique identifier of the session to fetch messages for"),
    session: AsyncSession = Depends(get_session),
) -> MessagesResponse:
    """Get all messages for a session."""
    session_service = SessionService(session)
    context_service = ContextService(session)

    chat_session = await session_service.get_session(session_id)
    messages = await context_service.get_session_messages(session_id)

    return MessagesResponse(
        session_id=chat_session.id,
        user_id=chat_session.user_id,
        messages=[
            ChatMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID = Path(..., title="Session ID", description="The unique identifier of the session to delete"),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a session."""
    service = SessionService(session)
    await service.delete_session(session_id)
    return None
