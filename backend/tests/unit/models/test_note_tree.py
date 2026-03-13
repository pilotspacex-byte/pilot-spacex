"""Unit tests for Note tree hierarchy columns.

Covers:
- NoteFactory produces valid Note with tree defaults (parent_id=None, depth=0, position=0)
- Note model accepts depth values 0, 1, 2 (valid range)
- Note model allows parent_id != id (no self-reference at model level via constraint name)
- Note with project_id=None represents a personal page (owner_id NOT NULL)
- Note with project_id set represents a project page
- Note model has CheckConstraint named "chk_notes_depth_range"
- Note model has CheckConstraint named "chk_notes_no_self_parent"
- Note model has indexes: ix_notes_parent_id, ix_notes_parent_position, ix_notes_depth, ix_notes_owner_workspace

SQLAlchemy mapped_column(default=...) sets the PYTHON-side default only when the
ORM flushes a new row — NOT on __init__. For default assertions before flush we
check the column `default.arg` or `server_default.arg` directly on the column spec.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Index

from pilot_space.infrastructure.database.models.note import Note
from tests.factories import NoteFactory

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _get_table_args() -> tuple:
    """Return the __table_args__ tuple for Note, unwrapping if it's a dict."""
    args = Note.__table_args__
    if isinstance(args, dict):
        return ()
    return args


def _find_check_constraint(name: str) -> CheckConstraint | None:
    """Find a CheckConstraint by name in Note.__table_args__."""
    for item in _get_table_args():
        if isinstance(item, CheckConstraint) and item.name == name:
            return item
    return None


def _find_index(name: str) -> Index | None:
    """Find an Index by name in Note.__table_args__."""
    for item in _get_table_args():
        if isinstance(item, Index) and item.name == name:
            return item
    return None


# ---------------------------------------------------------------------------
# Test 1: NoteFactory defaults for tree columns
# ---------------------------------------------------------------------------


def test_note_factory_tree_defaults() -> None:
    """NoteFactory produces a Note with parent_id=None, depth=0, position=0."""
    note = NoteFactory()

    assert note.parent_id is None, "parent_id should default to None"
    assert note.depth == 0, "depth should default to 0"
    assert note.position == 0, "position should default to 0"


# ---------------------------------------------------------------------------
# Test 2: Valid depth values 0, 1, 2 (model-level construction)
# ---------------------------------------------------------------------------


def test_note_accepts_depth_zero() -> None:
    """Note with depth=0 (root) can be constructed."""
    note = NoteFactory(depth=0)
    assert note.depth == 0


def test_note_accepts_depth_one() -> None:
    """Note with depth=1 (first child) can be constructed."""
    parent_id = uuid.uuid4()
    note = NoteFactory(depth=1, parent_id=parent_id)
    assert note.depth == 1


def test_note_accepts_depth_two() -> None:
    """Note with depth=2 (grandchild) can be constructed."""
    parent_id = uuid.uuid4()
    note = NoteFactory(depth=2, parent_id=parent_id)
    assert note.depth == 2


# ---------------------------------------------------------------------------
# Test 3: No self-reference at model level — parent_id != id is valid
# ---------------------------------------------------------------------------


def test_note_with_different_parent_id_is_valid() -> None:
    """Note with parent_id != id is valid (guard is at DB constraint level)."""
    parent_id = uuid.uuid4()
    note = NoteFactory(parent_id=parent_id)
    assert note.parent_id == parent_id
    assert note.parent_id != note.id


# ---------------------------------------------------------------------------
# Test 4: Personal page — project_id=None, owner_id NOT NULL
# ---------------------------------------------------------------------------


def test_note_personal_page_has_no_project_id() -> None:
    """Note with project_id=None represents a personal (user) page.

    owner_id must be set (not None) for personal pages.
    """
    owner_id = uuid.uuid4()
    note = NoteFactory(owner_id=owner_id, project_id=None)

    assert note.project_id is None, "Personal page has no project_id"
    assert note.owner_id is not None, "Personal page must have owner_id"
    assert note.owner_id == owner_id


# ---------------------------------------------------------------------------
# Test 5: Project page — project_id set
# ---------------------------------------------------------------------------


def test_note_project_page_has_project_id() -> None:
    """Note with project_id set represents a project page."""
    project_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    note = NoteFactory(owner_id=owner_id, project_id=project_id)

    assert note.project_id == project_id
    assert note.owner_id == owner_id


# ---------------------------------------------------------------------------
# Test 6: CheckConstraint "chk_notes_depth_range" exists in __table_args__
# ---------------------------------------------------------------------------


def test_note_has_check_constraint_depth_range() -> None:
    """Note model has CheckConstraint named 'chk_notes_depth_range'."""
    constraint = _find_check_constraint("chk_notes_depth_range")
    assert constraint is not None, (
        "Note.__table_args__ must contain CheckConstraint(name='chk_notes_depth_range')"
    )


# ---------------------------------------------------------------------------
# Test 7: CheckConstraint "chk_notes_no_self_parent" exists in __table_args__
# ---------------------------------------------------------------------------


def test_note_has_check_constraint_no_self_parent() -> None:
    """Note model has CheckConstraint named 'chk_notes_no_self_parent'."""
    constraint = _find_check_constraint("chk_notes_no_self_parent")
    assert constraint is not None, (
        "Note.__table_args__ must contain CheckConstraint(name='chk_notes_no_self_parent')"
    )


# ---------------------------------------------------------------------------
# Test 8: Required indexes exist in __table_args__
# ---------------------------------------------------------------------------


def test_note_has_index_parent_id() -> None:
    """Note model has Index named 'ix_notes_parent_id'."""
    index = _find_index("ix_notes_parent_id")
    assert index is not None, "Note.__table_args__ must contain Index('ix_notes_parent_id')"


def test_note_has_index_parent_position() -> None:
    """Note model has composite Index named 'ix_notes_parent_position'."""
    index = _find_index("ix_notes_parent_position")
    assert index is not None, "Note.__table_args__ must contain Index('ix_notes_parent_position')"


def test_note_has_index_depth() -> None:
    """Note model has Index named 'ix_notes_depth'."""
    index = _find_index("ix_notes_depth")
    assert index is not None, "Note.__table_args__ must contain Index('ix_notes_depth')"


def test_note_has_index_owner_workspace() -> None:
    """Note model has composite Index named 'ix_notes_owner_workspace'."""
    index = _find_index("ix_notes_owner_workspace")
    assert index is not None, "Note.__table_args__ must contain Index('ix_notes_owner_workspace')"
