"""Unit tests for NoteRepository topic-tree methods.

Covers ``list_topic_children``, ``list_topic_ancestors``, and ``move_topic``
on the topic-level hierarchy (``parent_topic_id`` / ``topic_depth``).

These tests use the rolling-back ``db_session`` fixture from conftest.py
because the moved-row + descendant updates are exercised inside the
session's outer transaction (move_topic opens a savepoint via
``begin_nested``). The cycle / max-depth / cross-workspace failure cases
also assert that the source row's pre-state is preserved when the
repository raises ValueError.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from pilot_space.infrastructure.database.models import (
    Note,
    User,
    Workspace,
)
from pilot_space.infrastructure.database.repositories.note_repository import (
    NoteRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(
        id=uuid4(),
        name="Topic Tree WS",
        slug="topic-tree-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def other_workspace(db_session: AsyncSession) -> Workspace:
    """Create a SECOND workspace to verify cross-workspace move rejection."""
    ws = Workspace(
        id=uuid4(),
        name="Other WS",
        slug="other-ws",
        owner_id=uuid4(),
    )
    db_session.add(ws)
    await db_session.flush()
    return ws


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a user for tests."""
    u = User(
        id=uuid4(),
        email="topic-tree@example.com",
        full_name="Topic Tree User",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _make_note(
    db_session: AsyncSession,
    workspace_id: UUID,
    owner_id: UUID,
    *,
    title: str = "Topic",
    parent_topic_id: UUID | None = None,
    topic_depth: int = 0,
) -> Note:
    note = Note(
        id=uuid4(),
        workspace_id=workspace_id,
        owner_id=owner_id,
        title=title,
        content={},
        parent_topic_id=parent_topic_id,
        topic_depth=topic_depth,
    )
    db_session.add(note)
    await db_session.flush()
    return note


# ── list_topic_children ─────────────────────────────────────────────────────


async def test_list_topic_children_returns_only_direct_children(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    parent = await _make_note(db_session, workspace.id, user.id, title="Parent")
    child_1 = await _make_note(
        db_session,
        workspace.id,
        user.id,
        title="Child 1",
        parent_topic_id=parent.id,
        topic_depth=1,
    )
    child_2 = await _make_note(
        db_session,
        workspace.id,
        user.id,
        title="Child 2",
        parent_topic_id=parent.id,
        topic_depth=1,
    )
    # Grandchild: not a DIRECT child of parent → should not appear.
    await _make_note(
        db_session,
        workspace.id,
        user.id,
        title="Grandchild",
        parent_topic_id=child_1.id,
        topic_depth=2,
    )

    rows, total = await repo.list_topic_children(workspace.id, parent.id)
    ids = {n.id for n in rows}
    assert ids == {child_1.id, child_2.id}
    assert total == 2


async def test_list_topic_children_with_parent_topic_id_none_returns_roots(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    root_a = await _make_note(db_session, workspace.id, user.id, title="Root A")
    root_b = await _make_note(db_session, workspace.id, user.id, title="Root B")
    # A non-root child must NOT appear at the root listing.
    await _make_note(
        db_session,
        workspace.id,
        user.id,
        title="Child of A",
        parent_topic_id=root_a.id,
        topic_depth=1,
    )

    rows, total = await repo.list_topic_children(workspace.id, None)
    ids = {n.id for n in rows}
    assert ids == {root_a.id, root_b.id}
    assert total == 2


async def test_list_topic_children_paginates(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    parent = await _make_note(db_session, workspace.id, user.id, title="Parent")
    for i in range(5):
        await _make_note(
            db_session,
            workspace.id,
            user.id,
            title=f"Child {i}",
            parent_topic_id=parent.id,
            topic_depth=1,
        )

    page_1, total = await repo.list_topic_children(
        workspace.id, parent.id, page=1, page_size=2
    )
    page_2, _ = await repo.list_topic_children(
        workspace.id, parent.id, page=2, page_size=2
    )
    page_3, _ = await repo.list_topic_children(
        workspace.id, parent.id, page=3, page_size=2
    )

    assert total == 5
    assert len(page_1) == 2
    assert len(page_2) == 2
    assert len(page_3) == 1
    # No overlap between pages.
    seen = {n.id for n in page_1} | {n.id for n in page_2} | {n.id for n in page_3}
    assert len(seen) == 5


# ── list_topic_ancestors ────────────────────────────────────────────────────


async def test_list_topic_ancestors_root_only_returns_self(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    root = await _make_note(db_session, workspace.id, user.id, title="Root")

    chain = await repo.list_topic_ancestors(root.id)
    assert [n.id for n in chain] == [root.id]


async def test_list_topic_ancestors_returns_root_to_leaf_order(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    root = await _make_note(db_session, workspace.id, user.id, title="Root")
    a = await _make_note(
        db_session, workspace.id, user.id, title="A",
        parent_topic_id=root.id, topic_depth=1,
    )
    b = await _make_note(
        db_session, workspace.id, user.id, title="B",
        parent_topic_id=a.id, topic_depth=2,
    )
    c = await _make_note(
        db_session, workspace.id, user.id, title="C",
        parent_topic_id=b.id, topic_depth=3,
    )

    chain = await repo.list_topic_ancestors(c.id)
    assert [n.id for n in chain] == [root.id, a.id, b.id, c.id]


async def test_list_topic_ancestors_caps_at_six(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """Defense-in-depth: walk truncates at TOPIC_MAX_DEPTH+1 = 6 hops.

    Even if a manually-injected too-deep chain exists, the walk must not
    loop forever; result length is bounded.
    """
    repo = NoteRepository(db_session)
    # Build 8 stacked nodes with topic_depth ignoring the invariant
    # (this simulates a corrupted DB, defense-in-depth path).
    prev_id: UUID | None = None
    nodes: list[Note] = []
    for i in range(8):
        n = await _make_note(
            db_session,
            workspace.id,
            user.id,
            title=f"Lvl {i}",
            parent_topic_id=prev_id,
            topic_depth=i,
        )
        nodes.append(n)
        prev_id = n.id

    chain = await repo.list_topic_ancestors(nodes[-1].id)
    assert len(chain) <= 6


# ── move_topic — happy path ─────────────────────────────────────────────────


async def test_move_topic_to_root_sets_parent_null_depth_zero(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    parent = await _make_note(db_session, workspace.id, user.id, title="Parent")
    child = await _make_note(
        db_session, workspace.id, user.id, title="Child",
        parent_topic_id=parent.id, topic_depth=1,
    )

    moved = await repo.move_topic(child.id, None)
    assert moved.parent_topic_id is None
    assert moved.topic_depth == 0


async def test_move_topic_to_parent_sets_depth_one_more_than_parent(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    new_parent = await _make_note(
        db_session, workspace.id, user.id, title="NP", topic_depth=2
    )
    floating = await _make_note(
        db_session, workspace.id, user.id, title="Floater"
    )

    moved = await repo.move_topic(floating.id, new_parent.id)
    assert moved.parent_topic_id == new_parent.id
    assert moved.topic_depth == 3  # parent.topic_depth (2) + 1


async def test_move_topic_recomputes_descendant_depths(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """Moving a subtree shifts every descendant's topic_depth by the delta."""
    repo = NoteRepository(db_session)
    # Tree: root -> a -> b
    root = await _make_note(db_session, workspace.id, user.id, title="Root")
    a = await _make_note(
        db_session, workspace.id, user.id, title="A",
        parent_topic_id=root.id, topic_depth=1,
    )
    b = await _make_note(
        db_session, workspace.id, user.id, title="B",
        parent_topic_id=a.id, topic_depth=2,
    )
    # Separate destination at depth 2.
    dest = await _make_note(
        db_session, workspace.id, user.id, title="Dest", topic_depth=2,
    )

    # Move A under Dest → A becomes depth 3, B becomes depth 4.
    moved_a = await repo.move_topic(a.id, dest.id)
    assert moved_a.parent_topic_id == dest.id
    assert moved_a.topic_depth == 3

    refreshed_b = await db_session.get(Note, b.id)
    assert refreshed_b is not None
    assert refreshed_b.topic_depth == 4
    # B's parent_topic_id is unchanged — only A's parent moved.
    assert refreshed_b.parent_topic_id == a.id


# ── move_topic — rejections ─────────────────────────────────────────────────


async def test_move_topic_rejects_self_cycle(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    n = await _make_note(db_session, workspace.id, user.id, title="N")
    with pytest.raises(ValueError, match="topic_cycle"):
        await repo.move_topic(n.id, n.id)


async def test_move_topic_rejects_cycle_into_descendant(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """Moving a node under one of its descendants creates a cycle → reject."""
    repo = NoteRepository(db_session)
    root = await _make_note(db_session, workspace.id, user.id, title="Root")
    child = await _make_note(
        db_session, workspace.id, user.id, title="Child",
        parent_topic_id=root.id, topic_depth=1,
    )
    grand = await _make_note(
        db_session, workspace.id, user.id, title="Grand",
        parent_topic_id=child.id, topic_depth=2,
    )

    with pytest.raises(ValueError, match="topic_cycle"):
        await repo.move_topic(root.id, grand.id)


async def test_move_topic_rejects_max_depth_exceeded(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """Moving a 4-deep subtree under a depth-2 parent → resulting depth 6 > 5."""
    repo = NoteRepository(db_session)
    # Subtree of height 4: A(0) -> B(1) -> C(2) -> D(3)
    a = await _make_note(db_session, workspace.id, user.id, title="A")
    b = await _make_note(
        db_session, workspace.id, user.id, title="B",
        parent_topic_id=a.id, topic_depth=1,
    )
    c = await _make_note(
        db_session, workspace.id, user.id, title="C",
        parent_topic_id=b.id, topic_depth=2,
    )
    await _make_note(
        db_session, workspace.id, user.id, title="D",
        parent_topic_id=c.id, topic_depth=3,
    )
    # Destination at depth 2 → A would become 3, B 4, C 5, D 6 (>5).
    dest = await _make_note(
        db_session, workspace.id, user.id, title="Dest", topic_depth=2,
    )

    with pytest.raises(ValueError, match="topic_max_depth"):
        await repo.move_topic(a.id, dest.id)


async def test_move_topic_rejects_cross_workspace(
    db_session: AsyncSession,
    workspace: Workspace,
    other_workspace: Workspace,
    user: User,
) -> None:
    repo = NoteRepository(db_session)
    source = await _make_note(db_session, workspace.id, user.id, title="Source")
    foreign_parent = await _make_note(
        db_session, other_workspace.id, user.id, title="Foreign Parent"
    )

    with pytest.raises(ValueError, match="cross_workspace_move"):
        await repo.move_topic(source.id, foreign_parent.id)


async def test_move_topic_rejects_missing_parent(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    n = await _make_note(db_session, workspace.id, user.id, title="N")
    with pytest.raises(ValueError, match="parent_not_found"):
        await repo.move_topic(n.id, uuid4())


async def test_move_topic_rejects_missing_topic(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    repo = NoteRepository(db_session)
    with pytest.raises(ValueError, match="topic_not_found"):
        await repo.move_topic(uuid4(), None)


async def test_move_topic_savepoint_rolls_back_partial_update(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """A mid-flight UPDATE failure inside the begin_nested savepoint rolls
    back the source row's already-applied parent_topic_id + topic_depth
    write so the caller observes the pre-move state.

    This is the real test for the savepoint atomicity guarantee: the
    upfront validations all pass, the moved-row UPDATE lands first, then
    a forced RuntimeError on the descendant UPDATE must unwind both
    writes together via the begin_nested rollback. The outer transaction
    stays healthy so the post-failure SELECT can proceed.
    """
    repo = NoteRepository(db_session)
    # Tree: root -> a -> b. Move A under a separate Dest at depth 0.
    root = await _make_note(db_session, workspace.id, user.id, title="Root")
    a = await _make_note(
        db_session, workspace.id, user.id, title="A",
        parent_topic_id=root.id, topic_depth=1,
    )
    await _make_note(
        db_session, workspace.id, user.id, title="B",
        parent_topic_id=a.id, topic_depth=2,
    )
    dest = await _make_note(
        db_session, workspace.id, user.id, title="Dest", topic_depth=0,
    )

    # Capture identifiers BEFORE forcing a session error, so post-failure
    # attribute access on `a` does not trigger an autoload at a bad moment.
    a_id = a.id
    pre_parent_id = a.parent_topic_id
    pre_depth = a.topic_depth

    # Patch the session's execute so the FIRST UPDATE inside the savepoint
    # (moved row) succeeds and the SECOND UPDATE (descendant B) raises.
    # Using a non-DB exception (RuntimeError) keeps the outer connection
    # healthy — IntegrityError would taint the connection past the savepoint
    # rollback in async SQLAlchemy + SQLite.
    real_execute = db_session.execute
    update_call_count = {"n": 0}

    async def fake_execute(stmt, *args, **kwargs):  # type: ignore[no-untyped-def]
        if getattr(stmt, "is_dml", False):
            update_call_count["n"] += 1
            if update_call_count["n"] >= 2:
                raise RuntimeError("forced mid-update failure")
        return await real_execute(stmt, *args, **kwargs)

    db_session.execute = fake_execute  # type: ignore[method-assign]
    try:
        with pytest.raises(RuntimeError, match="forced mid-update failure"):
            await repo.move_topic(a.id, dest.id)
    finally:
        # Restore so post-test introspection uses the real method.
        db_session.execute = real_execute  # type: ignore[method-assign]

    # Savepoint should have rolled BOTH the moved row's UPDATE and any
    # partial descendant UPDATE back to the pre-call state. Issue an
    # explicit SELECT (bypass the identity map cache and any lazy-load
    # path on detached attributes that triggers post-error).
    from sqlalchemy import select as sa_select

    result = await db_session.execute(
        sa_select(Note.parent_topic_id, Note.topic_depth).where(Note.id == a_id)
    )
    row = result.one()
    assert row.parent_topic_id == pre_parent_id, (
        "savepoint failed to roll back source row's parent_topic_id"
    )
    assert row.topic_depth == pre_depth, (
        "savepoint failed to roll back source row's topic_depth"
    )


async def test_move_topic_rolls_back_on_failure(
    db_session: AsyncSession, workspace: Workspace, user: User
) -> None:
    """Failed move (max-depth) leaves source row's parent_topic_id + topic_depth unchanged."""
    repo = NoteRepository(db_session)
    # Subtree: A(0) -> B(1) -> C(2) -> D(3) — height 4 from A.
    a = await _make_note(db_session, workspace.id, user.id, title="A")
    b = await _make_note(
        db_session, workspace.id, user.id, title="B",
        parent_topic_id=a.id, topic_depth=1,
    )
    c = await _make_note(
        db_session, workspace.id, user.id, title="C",
        parent_topic_id=b.id, topic_depth=2,
    )
    d = await _make_note(
        db_session, workspace.id, user.id, title="D",
        parent_topic_id=c.id, topic_depth=3,
    )
    dest = await _make_note(
        db_session, workspace.id, user.id, title="Dest", topic_depth=2,
    )

    # Snapshot pre-state.
    pre_parent_id = a.parent_topic_id
    pre_depth = a.topic_depth
    pre_d_depth = d.topic_depth

    with pytest.raises(ValueError, match="topic_max_depth"):
        await repo.move_topic(a.id, dest.id)

    # The validation rejects BEFORE any UPDATE issues, so source + descendants
    # are bit-for-bit unchanged.
    refreshed_a = await db_session.get(Note, a.id)
    refreshed_d = await db_session.get(Note, d.id)
    assert refreshed_a is not None
    assert refreshed_d is not None
    assert refreshed_a.parent_topic_id == pre_parent_id
    assert refreshed_a.topic_depth == pre_depth
    assert refreshed_d.topic_depth == pre_d_depth
