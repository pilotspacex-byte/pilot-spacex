"""User repository for user data access.

Provides specialized methods for user-related queries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from pilot_space.infrastructure.database.models.user import User
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(BaseRepository[User]):
    """Repository for User entities.

    Extends BaseRepository with user-specific queries.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize UserRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, User)

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> User | None:
        """Get user by email address.

        Args:
            email: The user's email address.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            The user if found, None otherwise.
        """
        query = select(User).where(User.email == email)
        if not include_deleted:
            query = query.where(User.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_emails(
        self,
        emails: list[str],
        *,
        include_deleted: bool = False,
    ) -> Sequence[User]:
        """Get multiple users by email addresses.

        Args:
            emails: List of email addresses.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            List of matching users.
        """
        if not emails:
            return []
        query = select(User).where(User.email.in_(emails))
        if not include_deleted:
            query = query.where(User.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalars().all()

    async def email_exists(
        self,
        email: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check if email address is already in use.

        Args:
            email: The email address to check.
            exclude_id: User ID to exclude from check (for updates).

        Returns:
            True if email exists, False otherwise.
        """
        query = select(User).where(
            User.email == email,
            User.is_deleted == False,  # noqa: E712
        )
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def search_users(
        self,
        search_term: str,
        *,
        limit: int = 20,
        include_deleted: bool = False,
    ) -> Sequence[User]:
        """Search users by email or full name.

        Args:
            search_term: Text to search for.
            limit: Maximum results to return.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            List of matching users.
        """
        return await self.search(
            search_term,
            ["email", "full_name"],
            include_deleted=include_deleted,
            limit=limit,
        )

    async def get_or_create(
        self,
        email: str,
        *,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one.

        Args:
            email: The user's email address.
            full_name: Optional display name.
            avatar_url: Optional profile image URL.

        Returns:
            Tuple of (user, created) where created is True if new user.
        """
        existing = await self.get_by_email(email, include_deleted=True)
        if existing:
            if existing.is_deleted:
                # Restore soft-deleted user
                await self.restore(existing)
            return existing, False

        user = User(
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )
        await self.create(user)
        return user, True
