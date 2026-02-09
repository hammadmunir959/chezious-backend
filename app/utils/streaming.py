"""SSE (Server-Sent Events) streaming utilities"""


from typing import AsyncGenerator
from sse_starlette.sse import EventSourceResponse


async def create_sse_response(
    generator: AsyncGenerator[str, None],
    media_type: str = "text/event-stream",
) -> EventSourceResponse:
    """Create an SSE response from an async generator."""

    async def event_generator():
        async for token in generator:
            yield {"data": token}
        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator(), media_type=media_type)



