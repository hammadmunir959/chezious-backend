"""User service for managing user operations"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.session import ChatSession, SessionStatus
from app.schemas.user import UserWithSessions, UserSessionSummary
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserService:
    """Service layer for handling User domain logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self, user_id: str, name: Optional[str] = None, city: Optional[str] = None
    ) -> User:
        """
        Create a new user. 
        
        Strictly enforces that the user must not already exist.
        
        Raises:
            UserAlreadyExistsException: If a user with the given ID already exists.
        """
        if await self._user_exists(user_id):
            raise UserAlreadyExistsException(user_id)

        user = User(user_id=user_id, name=name, city=city)
        self.db.add(user)
        # We flush to get the ID/defaults but commit is handled by caller/middleware
        await self.db.flush()
        
        logger.info(f"User created: {user_id}")
        return user

    async def get_user(self, user_id: str) -> User:
        """
        Retrieve a user by ID.
        
        Raises:
            UserNotFoundException: If the user does not exist.
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user

    async def update_user(
        self, user_id: str, name: Optional[str] = None, city: Optional[str] = None
    ) -> User:
        """
        Update an existing user's profile fields.
        
        Only updates fields that are explicitly provided (not None).
        """
        user = await self.get_user(user_id)

        if name is not None:
            user.name = name
        if city is not None:
            user.city = city
        
        await self.db.flush()
        logger.info(f"User updated: {user_id}")
        return user

    async def get_or_create_user(
        self, user_id: str, name: Optional[str] = None, city: Optional[str] = None
    ) -> User:
        """
        Retrieve an existing user, updating their profile if new info is provided,
        OR create a new user if one does not exist.
        
        This is an idempotent operation safe for repeated calls.
        """
        user = await self.db.get(User, user_id)

        if user:
            # User exists, optionally update their details
            updated = False
            if name is not None and user.name != name:
                user.name = name
                updated = True
            if city is not None and user.city != city:
                user.city = city
                updated = True
            
            if updated:
                await self.db.flush()
                logger.debug(f"User refreshed: {user_id}")
            return user

        # User does not exist, create new
        return await self.create_user(user_id, name, city)

    async def delete_user(self, user_id: str) -> None:
        """
        Delete a user and cascadingly remove their sessions/messages.
        """
        user = await self.get_user(user_id)
        await self.db.delete(user)
        await self.db.flush()
        logger.info(f"User deleted: {user_id}")

    async def increment_session_count(self, user_id: str) -> None:
        """Atomic increment of user session count."""
        user = await self.get_user(user_id)
        user.increment_session_count()
        await self.db.flush()

    async def get_users_with_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> List[UserWithSessions]:
        """
        Retrieve users along with a summary of their ACTIVE sessions.
        
        Optimized to fetch users and sessions in a single query round-trip.
        """
        # Eager load sessions to avoid N+1 query problem
        stmt = (
            select(User)
            .options(selectinload(User.sessions))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return [self._map_user_with_sessions(user) for user in users]

    # --- Private Helper Methods ---

    async def _user_exists(self, user_id: str) -> bool:
        """Check if a user ID occupies a row in the database."""
        result = await self.db.execute(select(User.user_id).where(User.user_id == user_id))
        return result.first() is not None

    def _map_user_with_sessions(self, user: User) -> UserWithSessions:
        """Transform a User ORM object into a Schema response object."""
        # In-memory filtering for active sessions
        # Note: For very large datasets, this filtering should move to the SQL query
        active_sessions = [
            s for s in user.sessions 
            if s.status == SessionStatus.ACTIVE and s.message_count > 0
        ]
        
        # Sort by newest first
        active_sessions.sort(key=lambda x: x.created_at, reverse=True)
        
        session_summaries = [
            UserSessionSummary(
                id=s.id,
                created_at=s.created_at,
                status=s.status,
                message_count=s.message_count,
            )
            for s in active_sessions
        ]

        return UserWithSessions(
            user_id=user.user_id,
            name=user.name,
            city=user.city,
            created_at=user.created_at,
            session_count=len(session_summaries),
            sessions=session_summaries,
        )
