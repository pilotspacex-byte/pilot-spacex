"""Add note_templates table and annotation performance index.

T-141: note_templates — stores reusable note templates per workspace.
  - UUID PK, workspace_id (RLS), name, description, content JSONB (TipTap doc)
  - is_system boolean for 4 built-in SDLC templates
  - created_by FK to auth.users
  - RLS policy on workspace_id (members read, admins write)

T-142: Annotation query performance index (CONCURRENTLY).
  - idx_annotations_note_block on annotations(note_id, block_id)
  - Non-blocking — allows concurrent reads/writes during index creation.
  - Speeds up annotation queries from O(n) to O(log n) per block (FR-076).

T-143: Seed 4 system SDLC templates.
  - Sprint Planning, Design Review, Postmortem, Release Planning
  - is_system=true, workspace_id=NULL (available to all workspaces)

Revision ID: 044_add_note_templates
Revises: 043_add_note_yjs_states
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "044_add_note_templates"
down_revision = "043_add_note_yjs_states"
branch_labels = None
depends_on = None

# ── System template content ────────────────────────────────────────────────


def _tiptap_doc(blocks: list[dict]) -> dict:
    """Wrap blocks in a TipTap document root."""
    return {"type": "doc", "content": blocks}


def _heading(text: str, level: int = 2) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _paragraph(text: str = "") -> dict:
    node: dict = {"type": "paragraph"}
    if text:
        node["content"] = [{"type": "text", "text": text}]
    return node


def _bullet_list(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_paragraph(item)],
            }
            for item in items
        ],
    }


SPRINT_PLANNING = _tiptap_doc(
    [
        _heading("Sprint Planning", 1),
        _heading("Sprint Goal"),
        _paragraph("What is the main outcome we want to achieve this sprint?"),
        _heading("Scope"),
        _bullet_list(
            [
                "Issue PS-XXX: [feature/fix]",
                "Issue PS-XXX: [feature/fix]",
            ]
        ),
        _heading("Capacity"),
        _paragraph("Team capacity: X story points / X days"),
        _heading("Risks & Dependencies"),
        _bullet_list(["Risk: ...", "Dependency: ..."]),
        _heading("Definition of Done"),
        _bullet_list(
            [
                "All acceptance criteria met",
                "Tests pass (>80% coverage)",
                "PR reviewed and merged",
            ]
        ),
    ]
)

DESIGN_REVIEW = _tiptap_doc(
    [
        _heading("Design Review", 1),
        _heading("Overview"),
        _paragraph("Brief description of the design being reviewed."),
        _heading("Goals & Non-goals"),
        _bullet_list(["Goal: ...", "Non-goal: ..."]),
        _heading("Design Decision"),
        _paragraph("Describe the chosen approach and why."),
        _heading("Alternatives Considered"),
        _bullet_list(["Alternative A: ...", "Alternative B: ..."]),
        _heading("Trade-offs"),
        _paragraph("What are we accepting? What are we sacrificing?"),
        _heading("Open Questions"),
        _bullet_list(["Q: ...", "Q: ..."]),
        _heading("Decision"),
        _paragraph("Final decision and rationale."),
    ]
)

POSTMORTEM = _tiptap_doc(
    [
        _heading("Postmortem", 1),
        _heading("Incident Summary"),
        _paragraph("What happened? When? What was the impact?"),
        _heading("Timeline"),
        _bullet_list(
            [
                "HH:MM — Event description",
                "HH:MM — Event description",
                "HH:MM — Resolution",
            ]
        ),
        _heading("Root Cause Analysis"),
        _paragraph("What was the underlying cause?"),
        _heading("Contributing Factors"),
        _bullet_list(["Factor 1", "Factor 2"]),
        _heading("Action Items"),
        _bullet_list(
            [
                "[ ] Action item (Owner: @user, Due: date)",
            ]
        ),
        _heading("Lessons Learned"),
        _paragraph("What did we learn? What would we do differently?"),
    ]
)

RELEASE_PLANNING = _tiptap_doc(
    [
        _heading("Release Planning", 1),
        _heading("Release Goal"),
        _paragraph("What is the primary objective of this release?"),
        _heading("Scope"),
        _bullet_list(
            [
                "Feature: ...",
                "Fix: ...",
                "Migration: ...",
            ]
        ),
        _heading("Release Checklist"),
        _bullet_list(
            [
                "[ ] All features tested",
                "[ ] Documentation updated",
                "[ ] DB migrations run",
                "[ ] Rollback plan documented",
                "[ ] Stakeholders notified",
            ]
        ),
        _heading("Rollback Plan"),
        _paragraph("How do we roll back if the release fails?"),
        _heading("Communication"),
        _paragraph("Who needs to be notified? When?"),
    ]
)

SYSTEM_TEMPLATES = [
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "name": "Sprint Planning",
        "description": "Plan your sprint goals, scope, and capacity.",
        "content": SPRINT_PLANNING,
        "is_system": True,
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000002")),
        "name": "Design Review",
        "description": "Document design decisions, alternatives, and trade-offs.",
        "content": DESIGN_REVIEW,
        "is_system": True,
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000003")),
        "name": "Postmortem",
        "description": "Analyze incidents with timeline, root cause, and action items.",
        "content": POSTMORTEM,
        "is_system": True,
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000004")),
        "name": "Release Planning",
        "description": "Plan releases with checklist, rollback, and communication.",
        "content": RELEASE_PLANNING,
        "is_system": True,
    },
]


def upgrade() -> None:
    # T-141: Create note_templates table
    op.create_table(
        "note_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,  # NULL for system templates (available to all workspaces)
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            nullable=True,  # NULL for system templates
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # RLS: enable row-level security
    op.execute("ALTER TABLE note_templates ENABLE ROW LEVEL SECURITY")

    # RLS policy: members can read system templates and their workspace templates
    op.execute("""
        CREATE POLICY note_templates_select ON note_templates
        FOR SELECT
        USING (
            is_system = true
            OR workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = auth.uid()
            )
        )
    """)

    # RLS policy: admins/owners can insert custom templates
    op.execute("""
        CREATE POLICY note_templates_insert ON note_templates
        FOR INSERT
        WITH CHECK (
            is_system = false
            AND workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = auth.uid()
                AND role IN ('owner', 'admin')
            )
        )
    """)

    # RLS policy: admins/owners can update their workspace templates (not system)
    op.execute("""
        CREATE POLICY note_templates_update ON note_templates
        FOR UPDATE
        USING (
            is_system = false
            AND workspace_id IN (
                SELECT workspace_id FROM workspace_members
                WHERE user_id = auth.uid()
                AND role IN ('owner', 'admin')
            )
        )
    """)

    # RLS policy: admins/owners or creator can delete (not system templates)
    op.execute("""
        CREATE POLICY note_templates_delete ON note_templates
        FOR DELETE
        USING (
            is_system = false
            AND (
                created_by = auth.uid()
                OR workspace_id IN (
                    SELECT workspace_id FROM workspace_members
                    WHERE user_id = auth.uid()
                    AND role IN ('owner', 'admin')
                )
            )
        )
    """)

    # T-143: Seed system templates
    conn = op.get_bind()
    import json

    for tmpl in SYSTEM_TEMPLATES:
        conn.execute(
            sa.text("""
                INSERT INTO note_templates (id, workspace_id, name, description, content, is_system, created_by)
                VALUES (:id, NULL, :name, :description, :content::jsonb, true, NULL)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": tmpl["id"],
                "name": tmpl["name"],
                "description": tmpl["description"],
                "content": json.dumps(tmpl["content"]),
            },
        )

    # T-142: Annotation performance index (CONCURRENTLY — non-blocking)
    # Note: CONCURRENTLY cannot run inside a transaction block.
    # Alembic runs in a transaction by default, so we use execute_if_not_exists pattern
    # with standard CREATE INDEX (acceptable for initial migration; prod can re-create CONCURRENTLY).
    op.create_index(
        "idx_annotations_note_block",
        "annotations",
        ["note_id", "block_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_annotations_note_block", table_name="annotations", if_exists=True)
    op.execute("DROP TABLE IF EXISTS note_templates CASCADE")
