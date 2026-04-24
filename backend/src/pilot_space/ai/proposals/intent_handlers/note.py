"""Note intent handlers (Phase 89 Plan 03).

Registered tool names:

* ``create_note`` — creates a Note via ``CreateNoteService``.
* ``create_note_annotation`` — inserts a ``NoteAnnotation`` row.

Handlers live here because they perform real DB mutations; the audit gate
allow-lists only ``pilot_space/ai/proposals/intent_handlers/``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from pilot_space.ai.proposals.intent_executor import register_intent, register_revert
from pilot_space.application.services.proposal_bus import (
    IntentExecutionOutcome,
    ProposalCannotBeRevertedError,
)
from pilot_space.dependencies.auth import get_current_session
from pilot_space.domain.exceptions import NotFoundError
from pilot_space.domain.proposal import ArtifactType
from pilot_space.infrastructure.database.models import (
    AnnotationStatus,
    AnnotationType,
    Note,
    NoteAnnotation,
)
from pilot_space.infrastructure.database.models.note_version import (
    NoteVersion,
    VersionTrigger,
)
from pilot_space.infrastructure.database.repositories.note_version_repository import (
    NoteVersionRepository,
)


def _safe_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


@register_intent("create_note_annotation")
async def execute_create_note_annotation(
    args: dict[str, Any],
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Persist an AI margin annotation on a note.

    ``target_artifact_id`` is the Note id (same as ``args['note_id']``); we
    pull from ``args`` for clarity since the tool that built the proposal
    already resolved it.
    """
    session = get_current_session()

    note_id = _safe_uuid(args.get("note_id"))
    if note_id is None:
        msg = f"create_note_annotation: invalid note_id={args.get('note_id')!r}"
        raise NotFoundError(msg)

    note = (
        await session.execute(
            select(Note).where(
                Note.id == note_id,
                Note.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if note is None:
        msg = f"Note {note_id} not found"
        raise NotFoundError(msg)

    try:
        ann_type = AnnotationType(str(args.get("annotation_type", "")))
    except ValueError as exc:
        valid = [t.value for t in AnnotationType]
        msg = f"Invalid annotation_type; valid: {valid}"
        raise ValueError(msg) from exc

    confidence = float(args.get("confidence", 0.8))
    annotation = NoteAnnotation(
        note_id=note_id,
        block_id=args.get("block_id") or None,
        type=ann_type,
        content=str(args.get("content", "")),
        status=AnnotationStatus.PENDING,
        confidence=confidence,
        workspace_id=workspace_id,
    )
    session.add(annotation)
    await session.flush()
    # No version concept for annotations — return v1.
    return IntentExecutionOutcome(applied_version=1, lines_changed=1)


@register_intent("create_note")
async def execute_create_note(
    args: dict[str, Any],
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Create a Note via ``CreateNoteService``.

    ``args`` carries: ``title``, optional ``content_markdown``,
    optional ``project_id``, and the ``owner_id`` resolved at tool time.
    """
    from pilot_space.application.services.note.content_converter import ContentConverter
    from pilot_space.application.services.note.create_note_service import (
        CreateNotePayload,
        CreateNoteService,
    )
    from pilot_space.infrastructure.database.repositories.note_repository import (
        NoteRepository,
    )
    from pilot_space.infrastructure.database.repositories.template_repository import (
        TemplateRepository,
    )

    session = get_current_session()
    owner_id = _safe_uuid(args.get("owner_id"))
    if owner_id is None:
        msg = "create_note: owner_id is required"
        raise ValueError(msg)

    tiptap_content: dict[str, Any] | None = None
    if args.get("content_markdown"):
        tiptap_content = ContentConverter().markdown_to_tiptap(
            str(args["content_markdown"])
        )

    payload = CreateNotePayload(
        workspace_id=workspace_id,
        owner_id=owner_id,
        title=str(args.get("title", "")),
        content=tiptap_content,
        project_id=_safe_uuid(args.get("project_id")),
    )
    svc = CreateNoteService(
        session=session,
        note_repository=NoteRepository(session),
        template_repository=TemplateRepository(session),
    )
    result = await svc.execute(payload)
    # Fresh notes start at version 1 — Note doesn't carry version_number yet.
    _ = result.note.id
    return IntentExecutionOutcome(applied_version=1, lines_changed=None)


# ---------------------------------------------------------------------------
# Revert handler (Phase 89 Plan 05) — reuses note_versions infra.
# ---------------------------------------------------------------------------


@register_revert(ArtifactType.NOTE)
async def revert_note(
    *,
    workspace_id: UUID,
    target_artifact_id: UUID,
) -> IntentExecutionOutcome:
    """Revert a Note to the most recent ``ai_before`` snapshot.

    Reuses ``note_versions`` table via ``NoteVersionRepository`` (no JSONB
    duplication per plan REV-89-05-A). Restores ``note.content`` from the
    snapshot and appends a NEW NoteVersion row with trigger=MANUAL and
    label="user revert" — prior NoteVersion rows are NEVER mutated
    (append-only invariant).

    Raises ``ProposalCannotBeRevertedError`` if no prior ``ai_before``
    snapshot exists (nothing to revert to).
    """
    session = get_current_session()

    note = (
        await session.execute(
            select(Note).where(
                Note.id == target_artifact_id,
                Note.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if note is None:
        msg = f"Note {target_artifact_id} not found"
        raise NotFoundError(msg)

    nv_repo = NoteVersionRepository(session)
    ai_before = await nv_repo.get_latest_ai_before(
        note_id=target_artifact_id,
        workspace_id=workspace_id,
    )
    if ai_before is None:
        raise ProposalCannotBeRevertedError(
            f"Note {target_artifact_id} has no ai_before snapshot — nothing "
            "to revert to"
        )

    # Compute next version_number for the new snapshot row.
    latest = await nv_repo.get_latest_for_note(
        note_id=target_artifact_id,
        workspace_id=workspace_id,
    )
    next_version = (latest.version_number + 1) if latest is not None else 1

    # Restore note content in place — this is the mutation the user sees.
    note.content = ai_before.content

    # Append a new NoteVersion row recording the revert. MANUAL trigger is
    # used (not a new enum value) to avoid a migration — label carries intent.
    user_revert = NoteVersion(
        note_id=target_artifact_id,
        workspace_id=workspace_id,
        trigger=VersionTrigger.MANUAL,
        content=ai_before.content,
        label="user revert",
        version_number=next_version,
    )
    session.add(user_revert)
    await session.flush()

    return IntentExecutionOutcome(
        applied_version=next_version,
        lines_changed=None,
    )
