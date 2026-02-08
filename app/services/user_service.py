"""User service for managing user operations"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.session import ChatSession
from app.schemas.user import UserWithSessions, UserSessionSummary
from app.core.exceptions import UserNotFoundException, UserAlreadyExistsException
from app.core.logging import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(
        self, user_id: str, name: str | None = None, city: str | None = None
    ) -> User:
        """
        Create a new user. Raises exception if user already exists.

        Args:
            user_id: The username/user_id string
            name: Optional display name for the user
            city: Optional city/location for the user

        Returns:
            User instance

        Raises:
            UserAlreadyExistsException: If user already exists
        """
        # Check if user exists
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        if result.scalar_one_or_none():
            raise UserAlreadyExistsException(user_id)

        # Create new user
        user = User(user_id=user_id, name=name, city=city)
        self.db.add(user)
        await self.db.flush()

        logger.info(f"Created new user: {user_id}")
        return user

    async def update_user(
        self, user_id: str, name: str | None = None, city: str | None = None
    ) -> User:
        """
        Update an existing user's profile.

        Args:
            user_id: The username/user_id string
            name: Optional new display name
            city: Optional new city/location

        Returns:
            Updated User instance

        Raises:
            UserNotFoundException: If user doesn't exist
        """
        user = await self.get_user(user_id)

        if name is not None:
            user.name = name
        if city is not None:
            user.city = city

        await self.db.flush()
        logger.info(f"Updated user: {user_id}")
        return user

    async def get_or_create_user(
        self, user_id: str, name: str | None = None, city: str | None = None
    ) -> User:
        """
        Get existing user or create a new one.
        
        Args:
            user_id: The username/user_id string
            name: Optional display name for the user
            city: Optional city/location for the user

        Returns:
            User instance
        """
        # Try to get existing user
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            logger.debug(f"Found existing user: {user_id}")
            # Update name if provided and different
            if name and user.name != name:
                user.name = name
            # Update city if provided and different
            if city and user.city != city:
                user.city = city
            if name or city:
                await self.db.flush()
            return user

        # Create new user
        user = User(user_id=user_id, name=name, city=city)
        self.db.add(user)
        await self.db.flush()

        logger.info(f"Created new user: {user_id}")
        return user

    async def get_user(self, user_id: str) -> User:
        """
        Get a user by ID.

        Args:
            user_id: The username/user_id string

        Returns:
            User instance

        Raises:
            UserNotFoundException: If user doesn't exist
        """
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundException(user_id)

        return user

    async def increment_session_count(self, user_id: str) -> None:
        """Increment the user's session count."""
        user = await self.get_user(user_id)
        user.increment_session_count()
        await self.db.flush()

    async def get_users_with_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[UserWithSessions]:
        """
        Get all users with their active sessions.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of UserWithSessions instances
        """
        # Fetch users with their visible sessions eagerly
        # We want sessions that are (active AND message_count > 0)
        # However, typically filters on joinedloads are complex. 
        # A simpler way is to fetch all and filter in python, OR use select options.
        # But for 'visible' sessions vs 'all' sessions, it might be cleaner to 
        # keep using separate queries or a joined query with filtering.
        
        # Given "optimize the db also" and "n+1", let's load users AND their sessions in one go.
        # But we need to filter the sessions.
        # SQLAlchemy's `contains_eager` or simply loading all and filtering in memory if dataset is small.
        # Let's try to do it efficiently.
        
        from sqlalchemy.orm import selectinload
        
        # Use selectinload to fetch sessions efficiently (avoids N+1)
        # We can't easily filter the related collection on load with selectinload in a standard way
        # without more complex query construction.
        # Alternatively, we can just load all sessions and filter in Python, assuming 
        # archived/empty sessions aren't massive in number compared to active ones.
        
        stmt = (
            select(User)
            .options(selectinload(User.sessions))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        users_with_sessions = []
        for user in users:
            # Filter sessions in memory
            visible_sessions = [
                s for s in user.sessions 
                if s.status == "active" and s.message_count > 0
            ]
            
            # Sort sessions by created_at desc
            visible_sessions.sort(key=lambda x: x.created_at, reverse=True)
            
            session_summaries = [
                UserSessionSummary(
                    id=s.id,
                    created_at=s.created_at,
                    status=s.status,
                    message_count=s.message_count,
                )
                for s in visible_sessions
            ]

            users_with_sessions.append(
                UserWithSessions(
                    user_id=user.user_id,
                    name=user.name,
                    city=user.city,
                    created_at=user.created_at,
                    session_count=len(session_summaries),
                    sessions=session_summaries,
                )
            )

        return users_with_sessions

    async def delete_user(self, user_id: str) -> None:
        """
        Delete a user and all their sessions.

        Args:
            user_id: The user's ID

        Raises:
            UserNotFoundException: If user doesn't exist
        """
        # Ensure user exists
        user = await self.get_user(user_id)

        # Delete user (cascade will handle sessions and messages)
        await self.db.delete(user)
        await self.db.flush()
        
        logger.info(f"Deleted user {user_id}")
