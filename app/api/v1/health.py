"""Health check endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_session
from app.schemas.common import HealthResponse
from app.utils.time import utc_now
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> HealthResponse:
    """
    Comprehensive health check.
    
    Verifies connectivity to:
    - Database
    - Groq API Client configuration
    """
    db_status = "ok"
    groq_status = "ok"

    # Check database connectivity
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Groq API configuration/client availability
    try:
        from app.llm.groq_client import get_groq_client
        if not get_groq_client().client:
            groq_status = "error"
    except Exception:
        groq_status = "error"

    is_healthy = db_status == "ok" and groq_status == "ok"
    
    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        timestamp=utc_now(),
        version=settings.app_version,
        database=db_status,
        groq=groq_status,
    )
