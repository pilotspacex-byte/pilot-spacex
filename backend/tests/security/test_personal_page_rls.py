"""Tests for personal page RLS workspace scope (migration 083).

Verifies that the notes_personal_page_policy enforces workspace_id membership,
preventing users from accessing personal pages in workspaces they have been
removed from.

Reference: alembic/versions/083_fix_personal_page_rls_workspace_scope.py
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.models.workspace_member import WorkspaceMember
from pilot_space.infrastructure.database.rls import set_rls_context

from .conftest import SecurityTestContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_DB_URL = os.environ.get("DATABASE_URL", "sqlite")
_requires_postgres = pytest.mark.skipif(
    "sqlite" in _DB_URL,
    reason="RLS tests require PostgreSQL. Set DATABASE_URL.",
)


async def _create_personal_page(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    owner_id: uuid.UUID,
    title: str = "My Personal Page",
) -> Note:
    """Create a personal page (project_id=NULL, owner_id set)."""
    note = Note(
        id=uuid.uuid4(),
        title=title,
        workspace_id=workspace_id,
        owner_id=owner_id,
        project_id=None,
        content={"type": "doc", "content": []},
    )
    session.add(note)
    await session.flush()
    return note


@_requires_postgres
class TestPersonalPageWorkspaceScope:
    """Tests that personal page RLS enforces workspace membership.

    The old policy only checked owner_id. A user removed from workspace B
    could still see personal pages they created there. The new policy adds
    a workspace_members subquery to block access after membership removal.
    """

    @pytest.mark.asyncio
    async def test_owner_sees_personal_page_in_active_workspace(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Owner should see their personal page in a workspace they belong to."""
        page = await _create_personal_page(
            db_session,
            workspace_id=populated_db.workspace_a.id,
            owner_id=populated_db.owner.id,
            title="Owner Personal Page",
        )
        await db_session.commit()

        await set_rls_context(
            db_session,
            user_id=populated_db.owner.id,
            workspace_id=populated_db.workspace_a.id,
        )

        result = await db_session.execute(
            select(Note).where(
                Note.id == page.id,
                Note.project_id.is_(None),
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1
        assert rows[0].id == page.id

    @pytest.mark.asyncio
    async def test_removed_member_cannot_access_personal_page(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """User removed from workspace must not see their personal pages there.

        This is the core scenario migration 083 fixes. Previously, the policy
        only checked owner_id — so even after membership soft-delete, the user
        could still read/write their old personal pages.
        """
        # Setup: member creates a personal page in workspace A
        page = await _create_personal_page(
            db_session,
            workspace_id=populated_db.workspace_a.id,
            owner_id=populated_db.member.id,
            title="Member Personal Page",
        )
        await db_session.commit()

        # Soft-delete the member's workspace membership (simulates removal)
        result = await db_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.user_id == populated_db.member.id,
                WorkspaceMember.workspace_id == populated_db.workspace_a.id,
            )
        )
        membership = result.scalar_one()
        membership.is_deleted = True
        await db_session.commit()

        # Act: member queries their personal page after removal
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        result = await db_session.execute(
            select(Note).where(
                Note.id == page.id,
                Note.project_id.is_(None),
            )
        )
        rows = result.scalars().all()

        # Assert: RLS blocks access because membership is soft-deleted
        assert len(rows) == 0, "Removed member should NOT see personal pages in former workspace"

    @pytest.mark.asyncio
    async def test_other_user_cannot_see_personal_page(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Personal pages are private — other workspace members cannot see them."""
        await _create_personal_page(
            db_session,
            workspace_id=populated_db.workspace_a.id,
            owner_id=populated_db.owner.id,
            title="Owner Private Page",
        )
        await db_session.commit()

        # Act: member (different user) queries personal pages
        await set_rls_context(
            db_session,
            user_id=populated_db.member.id,
            workspace_id=populated_db.workspace_a.id,
        )

        result = await db_session.execute(
            select(Note).where(
                Note.project_id.is_(None),
                Note.owner_id == populated_db.owner.id,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 0, "Other members should NOT see someone else's personal pages"

    @pytest.mark.asyncio
    async def test_outsider_cannot_access_personal_page(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """User not in the workspace should have zero access to personal pages."""
        await _create_personal_page(
            db_session,
            workspace_id=populated_db.workspace_a.id,
            owner_id=populated_db.owner.id,
            title="Owner Page in A",
        )
        await db_session.commit()

        # Act: outsider (only in workspace B) queries workspace A
        await set_rls_context(
            db_session,
            user_id=populated_db.outsider.id,
            workspace_id=populated_db.workspace_a.id,
        )

        result = await db_session.execute(select(Note).where(Note.project_id.is_(None)))
        rows = result.scalars().all()
        assert len(rows) == 0, (
            "Outsider should have zero access to personal pages in other workspace"
        )

    @pytest.mark.asyncio
    async def test_cross_workspace_personal_page_isolation(
        self,
        db_session: AsyncSession,
        populated_db: SecurityTestContext,
    ) -> None:
        """Personal pages in workspace B must not leak into workspace A queries."""
        # Owner is member of workspace A, outsider is member of workspace B
        await _create_personal_page(
            db_session,
            workspace_id=populated_db.workspace_b.id,
            owner_id=populated_db.outsider.id,
            title="Outsider Page in B",
        )
        await db_session.commit()

        # Act: owner queries from workspace A context
        await set_rls_context(
            db_session,
            user_id=populated_db.owner.id,
            workspace_id=populated_db.workspace_a.id,
        )

        result = await db_session.execute(select(Note).where(Note.project_id.is_(None)))
        rows = result.scalars().all()
        assert len(rows) == 0, (
            "Personal pages from workspace B should not be visible in workspace A"
        )
