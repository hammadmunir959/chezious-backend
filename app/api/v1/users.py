"""User-related endpoints"""

from fastapi import APIRouter, Depends, status, Response, Query, Path
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

router = APIRouter(prefix="/users", tags=["Users"])


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
    user_id: str = Path(..., title="User ID", description="The unique identifier of the user"),
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


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    request: UserUpdate,
    user_id: str = Path(..., title="User ID", description="The unique identifier of the user to update"),
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
    user_id: str = Path(..., title="User ID", description="The unique identifier of the user to delete"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a user and all their sessions."""
    service = UserService(session)
    await service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/", response_model=list[UserWithSessions])
async def get_users_with_sessions(
    limit: int = Query(50, ge=1, le=100, description="Max number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    session: AsyncSession = Depends(get_session),
) -> list[UserWithSessions]:
    """Get all users with their active sessions."""
    service = UserService(session)
    return await service.get_users_with_sessions(limit, offset)


@router.get("/{user_id}/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(
    user_id: str = Path(..., title="User ID", description="The ID of the user to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100, description="Max number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    min_messages: int = Query(1, ge=0, description="Minimum messages required to include a session"),
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


