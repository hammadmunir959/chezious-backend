"""User-related endpoints"""

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.session_service import SessionService
from app.services.user_service import UserService
from app.schemas.user import (
    UserSessionsResponse,
    UserSessionSummary,
    UserWithSessions,
    UserCreate,
    UserUpdate,
    UserResponse,
)

router = APIRouter(prefix="/users")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Create a new user."""
    service = UserService(session)
    user = await service.create_user(
        request.user_id,
        request.name,
        request.city,
    )

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        city=user.city,
        created_at=user.created_at,
        session_count=user.session_count,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Get a single user by ID."""
    service = UserService(session)
    user = await service.get_user(user_id)

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        city=user.city,
        created_at=user.created_at,
        session_count=user.session_count,
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Update a user's profile."""
    service = UserService(session)
    user = await service.update_user(
        user_id,
        request.name,
        request.city,
    )

    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        city=user.city,
        created_at=user.created_at,
        session_count=user.session_count,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a user and all their sessions."""
    service = UserService(session)
    await service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/", response_model=list[UserWithSessions])
async def get_users_with_sessions(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[UserWithSessions]:
    """Get all users with their active sessions."""
    service = UserService(session)
    return await service.get_users_with_sessions(limit, offset)


@router.get("/{user_id}/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    min_messages: int = 1, # Default to 1 to skip empty sessions
    session: AsyncSession = Depends(get_session),
) -> UserSessionsResponse:
    """Get all sessions for a user."""
    service = SessionService(session)
    sessions = await service.get_user_sessions(
        user_id=user_id, 
        limit=limit, 
        offset=offset, 
        min_messages=min_messages
    )

    return UserSessionsResponse(
        user_id=user_id,
        sessions=[
            UserSessionSummary(
                id=s.id,
                created_at=s.created_at,
                status=s.status,
                message_count=s.message_count,
            )
            for s in sessions
        ],
        session_count=len(sessions),
    )


