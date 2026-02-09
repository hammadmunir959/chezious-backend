"""Chat endpoint with SSE streaming"""

from fastapi import APIRouter, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
import json

from app.db.session import get_session
from app.services.chat_service import ChatService
from app.schemas.chat import ChatRequest
from app.core.rate_limiter import limiter, get_rate_limit_string
from app.core.logging import get_logger, LogContext
from app.utils.ids import generate_request_id


router = APIRouter(tags=["Chat"])

logger = get_logger(__name__)


@router.post("/chat")
@limiter.limit(get_rate_limit_string())
async def chat(
    request: Request,
    chat_request: ChatRequest,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    """
    Send a message and receive a streaming response.

    Returns Server-Sent Events (SSE) stream with tokens.
    """
    request_id = generate_request_id()
    service = ChatService(session)

    # Determine user_id (header preferred)
    user_id = x_user_id

    # Determine session_id (validate if provided, create if missing/invalid)
    # This logic is now encapsulated in the service layer
    session_id = await service.resolve_session(
        chat_request.session_id, 
        user_id
    )

    with LogContext(
        request_id=request_id,
        session_id=str(session_id),
    ):
        logger.info(f"Chat request received: {len(chat_request.message)} chars")

        async def event_generator():
            """Generate SSE events from chat response."""
            try:
                # 1. Yield session ID immediately so client can track context
                yield {
                    "event": "session_created",
                    "data": json.dumps({"session_id": str(session_id)}),
                }

                # 2. Stream tokens
                async for token in service.handle_chat(
                    user_message=chat_request.message,
                    session_id=session_id,
                    user_id=user_id,
                ):
                    yield {
                        "event": "token",
                        "data": json.dumps({"token": token}),
                    }

                # 3. Done event
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "status": "complete", 
                        "session_id": str(session_id)
                    }),
                }

            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}),
                }

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
        )
