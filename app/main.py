"""CheziousBot - FastAPI Application Entry Point"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import ChatBotException
from app.core.rate_limiter import limiter
from app.core.middleware import RequestLoggingMiddleware, ResilienceMiddleware
from app.db.engine import init_db, close_db
from app.api import v1_router

# Initialize Logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events (startup & shutdown)."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Startup
    await init_db()
    logger.info("Database initialized successfully")
    
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

# 1. Configuration & Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ResilienceMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 2. Routers
app.include_router(v1_router)

# 3. Exception Handlers
@app.exception_handler(ChatBotException)
async def chatbot_exception_handler(request: Request, exc: ChatBotException):
    logger.warning(f"ChatBotException: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,  # Simplified: Use property if available or default
        content=exc.to_dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": exc.detail}}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}
    )


@app.get("/")
async def root():
    """Root endpoint for API status."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)

