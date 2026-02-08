"""CheziousBot - FastAPI Application Entry Point"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.api import v1_router
from app.core.config import settings
from app.core.exceptions import ChatBotException
from app.core.logging import setup_logging, get_logger
from app.core.rate_limiter import limiter
from app.db.engine import init_db, close_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered chatbot for Cheezious pizza brand",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from app.core.middleware import RequestLoggingMiddleware

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include API router
app.include_router(v1_router)


# Exception handlers
@app.exception_handler(ChatBotException)
async def chatbot_exception_handler(
    request: Request, exc: ChatBotException
) -> JSONResponse:
    """Handle ChatBotException and return structured error response."""
    # Map error codes to appropriate HTTP status codes
    status_map = {
        "SESSION_NOT_FOUND": 404,
        "USER_NOT_FOUND": 404,
        "USER_ALREADY_EXISTS": 409,
        "VALIDATION_ERROR": 400,
        "RATE_LIMIT_EXCEEDED": 429,
        "DATABASE_ERROR": 503,
        "GROQ_API_ERROR": 503,
        "SERVICE_UNAVAILABLE": 503,
        "CONFIGURATION_ERROR": 500,
    }
    status_code = status_map.get(exc.code, 400)
    logger.warning(f"ChatBotException: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )

 
@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI HTTPException with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


# Mount static files (UI) - must be last to not override API routes
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
 