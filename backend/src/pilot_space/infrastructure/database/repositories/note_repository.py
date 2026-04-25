"""Note repository for Note data access.

Provides specialized methods for Note-related queries with eager loading support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import joinedload, selectinload

from pilot_space.infrastructure.database.models.note import Note
from pilot_space.infrastructure.database.repositories.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy import RowMapping
    from sqlalchemy.ext.asyncio import AsyncSession


# ── Topic-hierarchy invariants ───────────────────────────────────────────────
# Max depth for the topic-level hierarchy (separate from page-level max=2).
TOPIC_MAX_DEPTH: int = 5
# Hard cap on ancestor walk hops (TOPIC_MAX_DEPTH + 1 to include the node itself).
_TOPIC_ANCESTOR_HOP_CAP: int = TOPIC_MAX_DEPTH + 1


class NoteRepository(BaseRepository[Note]):
    """Repository for Note entities.

    Extends BaseRepository with note-specific queries.
    Supports eager loading of annotations and discussions.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NoteRepository.

        Args:
            session: The async database session.
        """
        super().__init__(session, Note)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        """Get all notes in a workspace.

        Args:
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.
            offset: Number of notes to skip.

        Returns:
            List of notes in the workspace.
        """
        query = select(Note).where(Note.workspace_id == workspace_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        query = query.order_by(Note.created_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_notes(
        self,
        workspace_id: UUID,
        *,
        project_ids: list[UUID] | None = None,
        is_pinned: bool | None = None,
        search: str | None = None,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[Note]:
        """List notes in a workspace with optional filters.

        All filters are composable: any combination of project_ids, is_pinned,
        and search can be provided together.

        Args:
            workspace_id: The workspace ID to scope the query.
            project_ids: If provided, only notes belonging to these projects are returned.
            is_pinned: If provided, filters by pinned status.
            search: If provided, performs case-insensitive title matching.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.
            offset: Number of notes to skip (for pagination).

        Returns:
            List of matching notes ordered by updated_at desc.
        """
        query = select(Note).where(Note.workspace_id == workspace_id)

        if project_ids:
            query = query.where(Note.project_id.in_(project_ids))
        if is_pinned is not None:
            query = query.where(Note.is_pinned == is_pinned)
        if search:
            safe_term = search.replace("%", r"\%").replace("_", r"\_")
            query = query.where(Note.title.ilike(f"%{safe_term}%"))
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        query = query.order_by(Note.updated_at.desc())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_pinned(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
    ) -> int:
        """Count pinned notes in workspace or project.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID to narrow count.

        Returns:
            Count of pinned notes.
        """
        query = (
            select(func.count())
            .select_from(Note)
            .where(
                Note.workspace_id == workspace_id,
                Note.is_pinned == True,  # noqa: E712
                Note.is_deleted == False,  # noqa: E712
            )
        )
        if project_id:
            query = query.where(Note.project_id == project_id)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_with_annotations(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with annotations eagerly loaded.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with annotations loaded, or None if not found.
        """
        query = select(Note).options(selectinload(Note.annotations)).where(Note.id == note_id)
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_discussions(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with discussions and comments eagerly loaded.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with discussions and comments loaded, or None if not found.
        """
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        query = (
            select(Note)
            .options(selectinload(Note.discussions).selectinload(ThreadedDiscussion.comments))
            .where(Note.id == note_id)
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_all_relations(
        self,
        note_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Note | None:
        """Get note with all relations eagerly loaded.

        Loads annotations, discussions with comments, owner, and template.

        Args:
            note_id: The note ID.
            include_deleted: Whether to include soft-deleted note.

        Returns:
            Note with all relations loaded, or None if not found.
        """
        from pilot_space.infrastructure.database.models.note_issue_link import (
            NoteIssueLink,
        )
        from pilot_space.infrastructure.database.models.threaded_discussion import (
            ThreadedDiscussion,
        )

        query = (
            select(Note)
            .options(
                selectinload(Note.annotations),
                selectinload(Note.discussions).selectinload(ThreadedDiscussion.comments),
                selectinload(Note.issue_links).joinedload(NoteIssueLink.issue),
                joinedload(Note.owner),
                joinedload(Note.template),
                joinedload(Note.project),
            )
            .where(Note.id == note_id)
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_pinned_notes(
        self,
        workspace_id: UUID,
        *,
        project_id: UUID | None = None,
        limit: int = 10,
    ) -> Sequence[Note]:
        """Get pinned notes in workspace or project.

        Args:
            workspace_id: The workspace ID.
            project_id: Optional project ID to narrow results.
            limit: Maximum number of notes to return.

        Returns:
            List of pinned notes.
        """
        query = select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_pinned == True,  # noqa: E712
            Note.is_deleted == False,  # noqa: E712
        )
        if project_id:
            query = query.where(Note.project_id == project_id)
        query = query.order_by(Note.updated_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_owner(
        self,
        owner_id: UUID,
        workspace_id: UUID,
        *,
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> Sequence[Note]:
        """Get all notes by a specific owner in workspace.

        Args:
            owner_id: The owner's user ID.
            workspace_id: The workspace ID.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum number of notes to return.

        Returns:
            List of notes by the owner.
        """
        query = select(Note).where(
            Note.owner_id == owner_id,
            Note.workspace_id == workspace_id,
        )
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712
        query = query.order_by(Note.created_at.desc())
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def exists_in_workspace(self, note_id: UUID, workspace_id: UUID) -> bool:
        """Check if a note exists in the given workspace without fetching content.

        Selects only the id column to avoid loading the full JSONB content column.

        Args:
            note_id: The note UUID.
            workspace_id: The workspace UUID.

        Returns:
            True if the note exists and is not deleted, False otherwise.
        """
        result = await self.session.execute(
            select(Note.id).where(
                Note.id == note_id,
                Note.workspace_id == workspace_id,
                Note.is_deleted.is_(False),
            )
        )
        return result.scalar() is not None

    async def get_children(self, parent_id: UUID) -> Sequence[Note]:
        """Get direct children of a note ordered by position ascending.

        Args:
            parent_id: The parent note ID.

        Returns:
            Ordered list of direct child notes.
        """
        query = (
            select(Note)
            .where(
                Note.parent_id == parent_id,
                Note.is_deleted == False,  # noqa: E712
            )
            .order_by(Note.position.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_siblings(
        self,
        parent_id: UUID | None,
        workspace_id: UUID,
        project_id: UUID | None,
        exclude_note_id: UUID,
        for_update: bool = False,
    ) -> Sequence[Note]:
        """Get siblings of a note (notes sharing same parent) ordered by position ASC.

        Args:
            parent_id: The shared parent ID (None for root-level siblings).
            workspace_id: The workspace ID.
            project_id: The project ID (None for personal notes).
            exclude_note_id: Note ID to exclude from results.
            for_update: If True, apply SELECT FOR UPDATE to serialize concurrent writes.
                        This is a no-op in SQLite (used in production PostgreSQL only).

        Returns:
            Ordered list of sibling notes.
        """
        query = select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_deleted == False,  # noqa: E712
            Note.id != exclude_note_id,
        )
        if parent_id is None:
            query = query.where(Note.parent_id.is_(None))
        else:
            query = query.where(Note.parent_id == parent_id)

        if project_id is None:
            query = query.where(Note.project_id.is_(None))
        else:
            query = query.where(Note.project_id == project_id)

        query = query.order_by(Note.position.asc())
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_descendants(self, note_id: UUID) -> Sequence[RowMapping]:
        """Get all descendants of a note using a recursive CTE.

        Uses PostgreSQL WITH RECURSIVE to traverse the note tree.
        Unit tests must mock this method since SQLite cannot run this CTE pattern.

        Args:
            note_id: The root note ID whose descendants to retrieve.

        Returns:
            Sequence of row mappings with id, parent_id, depth, position columns.
        """
        cte_sql = text(
            """
            WITH RECURSIVE descendants AS (
                SELECT id, parent_id, depth, position
                FROM notes
                WHERE parent_id = :root_id AND is_deleted = false
                UNION ALL
                SELECT n.id, n.parent_id, n.depth, n.position
                FROM notes n
                JOIN descendants d ON n.parent_id = d.id
                WHERE n.is_deleted = false
            )
            SELECT * FROM descendants
            """
        )
        result = await self.session.execute(cte_sql, {"root_id": str(note_id)})
        return result.mappings().all()

    # ── Topic-level hierarchy (Phase 93) ────────────────────────────────────
    # The methods below operate on `parent_topic_id` / `topic_depth`, NOT
    # `parent_id` / `depth` / `position`. The two hierarchies are orthogonal.

    async def list_topic_children(
        self,
        workspace_id: UUID,
        parent_topic_id: UUID | None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Note], int]:
        """Return (rows, total_count) for direct topic children.

        ``parent_topic_id=None`` lists root-level topics (top of the tree).
        Ordered by ``created_at DESC``. Soft-deleted rows are excluded.

        Args:
            workspace_id: workspace scoping (defense-in-depth on top of RLS).
            parent_topic_id: parent's id, or None for the workspace's roots.
            page: 1-based page number.
            page_size: page size, must be >= 1.
        """
        page = max(page, 1)
        page_size = max(page_size, 1)

        base = select(Note).where(
            Note.workspace_id == workspace_id,
            Note.is_deleted == False,  # noqa: E712
        )
        if parent_topic_id is None:
            base = base.where(Note.parent_topic_id.is_(None))
        else:
            base = base.where(Note.parent_topic_id == parent_topic_id)

        # Total count (paginate on a stable filtered set).
        count_query = (
            select(func.count()).select_from(Note).where(
                Note.workspace_id == workspace_id,
                Note.is_deleted == False,  # noqa: E712
            )
        )
        if parent_topic_id is None:
            count_query = count_query.where(Note.parent_topic_id.is_(None))
        else:
            count_query = count_query.where(Note.parent_topic_id == parent_topic_id)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Stable order: created_at DESC with id DESC tie-break so concurrent
        # inserts in the same millisecond cannot shuffle pagination boundaries.
        rows_query = (
            base.order_by(Note.created_at.desc(), Note.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows_result = await self.session.execute(rows_query)
        rows = rows_result.scalars().all()
        return rows, total

    async def list_topic_ancestors(self, note_id: UUID) -> list[Note]:
        """Walk parent_topic_id chain upward; returns root → leaf order.

        Includes the node itself as the LAST element. Length ≤ 6
        (TOPIC_MAX_DEPTH + 1). If a cycle is somehow present in the DB
        (defense-in-depth — move_topic prevents this at write time), the
        walk is truncated at the hop cap.

        Args:
            note_id: leaf note id whose ancestor chain to walk.

        Returns:
            list of Note ordered root → leaf, INCLUDING the leaf.
            Empty list if note_id does not exist or is soft-deleted.
        """
        chain: list[Note] = []
        seen: set[UUID] = set()
        current_id: UUID | None = note_id

        for _ in range(_TOPIC_ANCESTOR_HOP_CAP):
            if current_id is None or current_id in seen:
                break
            seen.add(current_id)

            result = await self.session.execute(
                select(Note).where(
                    Note.id == current_id,
                    Note.is_deleted == False,  # noqa: E712
                )
            )
            node = result.scalar_one_or_none()
            if node is None:
                break
            chain.append(node)
            current_id = node.parent_topic_id

        # chain is leaf → root; reverse to root → leaf as documented.
        chain.reverse()
        return chain

    async def move_topic(
        self,
        topic_id: UUID,
        new_parent_topic_id: UUID | None,
    ) -> Note:
        """Reparent ``topic_id`` under ``new_parent_topic_id`` (root if None).

        Atomic over the moved row + every descendant via a single savepoint
        (``begin_nested``) inside the caller's outer transaction. Uses
        Python BFS instead of a Postgres-only recursive CTE so the same code
        runs on the SQLite test DB.

        Validations (all raise ``ValueError`` with sentinel messages so the
        Phase 93-02 service layer can map them to typed domain exceptions):

          * ``"topic_not_found"`` — topic_id missing or soft-deleted
          * ``"parent_not_found"`` — new_parent_topic_id missing / deleted
          * ``"cross_workspace_move"`` — parent in a different workspace
          * ``"topic_cycle"`` — target equals topic_id or sits in its subtree
          * ``"topic_max_depth"`` — any descendant would exceed depth 5

        Returns:
            the refreshed source Note.
        """
        # ── Self-cycle short-circuit ────────────────────────────────────────
        # Match against topic_id BEFORE any DB lookups: cheaper, clearer.
        if new_parent_topic_id is not None and new_parent_topic_id == topic_id:
            raise ValueError("topic_cycle")

        # ── Load source row ─────────────────────────────────────────────────
        source_result = await self.session.execute(
            select(Note).where(
                Note.id == topic_id,
                Note.is_deleted == False,  # noqa: E712
            )
        )
        source = source_result.scalar_one_or_none()
        if source is None:
            raise ValueError("topic_not_found")

        # ── Load + validate new parent (if any) ─────────────────────────────
        if new_parent_topic_id is None:
            new_root_depth = 0
        else:
            parent_result = await self.session.execute(
                select(Note).where(
                    Note.id == new_parent_topic_id,
                    Note.is_deleted == False,  # noqa: E712
                )
            )
            parent = parent_result.scalar_one_or_none()
            if parent is None:
                raise ValueError("parent_not_found")
            if parent.workspace_id != source.workspace_id:
                raise ValueError("cross_workspace_move")

            # Cycle check: walk parent's chain upward — if topic_id appears
            # anywhere, the move would create a cycle.
            cursor: UUID | None = parent.parent_topic_id
            seen: set[UUID] = {parent.id}
            for _ in range(_TOPIC_ANCESTOR_HOP_CAP):
                if cursor is None:
                    break
                if cursor == topic_id:
                    raise ValueError("topic_cycle")
                if cursor in seen:
                    # Defensive break on pre-existing cycle.
                    break
                seen.add(cursor)
                ancestor_result = await self.session.execute(
                    select(Note.parent_topic_id).where(Note.id == cursor)
                )
                cursor = ancestor_result.scalar_one_or_none()

            new_root_depth = parent.topic_depth + 1

        # ── BFS-load source's descendants ──────────────────────────────────
        # Frontier-by-frontier load; cap at TOPIC_MAX_DEPTH iterations since
        # max subtree height is bounded.
        # Map: descendant_id -> (parent_id, current_depth)
        descendants: dict[UUID, tuple[UUID, int]] = {}
        frontier: list[UUID] = [topic_id]
        for _ in range(TOPIC_MAX_DEPTH + 1):  # +1 = guard against pre-existing depth violations
            if not frontier:
                break
            child_result = await self.session.execute(
                select(Note.id, Note.parent_topic_id, Note.topic_depth).where(
                    Note.parent_topic_id.in_(frontier),
                    Note.is_deleted == False,  # noqa: E712
                )
            )
            next_frontier: list[UUID] = []
            for row in child_result.all():
                child_id, child_parent_id, child_depth = row
                # parent_topic_id is non-null because we filtered by .in_(frontier).
                descendants[child_id] = (child_parent_id, child_depth)
                next_frontier.append(child_id)
            frontier = next_frontier

        # ── Compute new depths via BFS from source ─────────────────────────
        new_depths: dict[UUID, int] = {topic_id: new_root_depth}
        queue: list[UUID] = [topic_id]
        while queue:
            current = queue.pop(0)
            current_new_depth = new_depths[current]
            for desc_id, (desc_parent_id, _desc_old_depth) in descendants.items():
                if desc_parent_id == current and desc_id not in new_depths:
                    new_depths[desc_id] = current_new_depth + 1
                    queue.append(desc_id)

        # ── Reject if any new depth exceeds the invariant ──────────────────
        if any(d > TOPIC_MAX_DEPTH for d in new_depths.values()):
            raise ValueError("topic_max_depth")

        # ── Apply updates atomically ───────────────────────────────────────
        # Single savepoint so depth + parent updates roll back together if
        # any UPDATE raises mid-flight. Caller controls the outer commit.
        async with self.session.begin_nested():
            await self.session.execute(
                update(Note)
                .where(Note.id == topic_id)
                .values(
                    parent_topic_id=new_parent_topic_id,
                    topic_depth=new_root_depth,
                )
            )
            for desc_id, new_depth in new_depths.items():
                if desc_id == topic_id:
                    continue
                await self.session.execute(
                    update(Note)
                    .where(Note.id == desc_id)
                    .values(topic_depth=new_depth)
                )

        await self.session.flush()
        await self.session.refresh(source)
        return source

    async def search_full_text(
        self,
        workspace_id: UUID,
        search_term: str,
        *,
        project_ids: list[UUID] | None = None,
        include_deleted: bool = False,
        limit: int = 20,
    ) -> Sequence[Note]:
        """Full-text search on notes using PostgreSQL ts_vector.

        Searches title using the full-text index.

        Args:
            workspace_id: The workspace ID.
            search_term: Text to search for.
            project_ids: Optional list of project IDs to narrow search.
            include_deleted: Whether to include soft-deleted notes.
            limit: Maximum results to return.

        Returns:
            List of matching notes ordered by relevance.
        """
        from sqlalchemy import text as sql_text

        query = select(Note).where(Note.workspace_id == workspace_id)
        if project_ids:
            query = query.where(Note.project_id.in_(project_ids))
        if not include_deleted:
            query = query.where(Note.is_deleted == False)  # noqa: E712

        # Use PostgreSQL full-text search
        ts_query = sql_text("to_tsvector('english', title) @@ plainto_tsquery('english', :term)")
        query = query.where(ts_query.bindparams(term=search_term))
        query = query.order_by(Note.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
