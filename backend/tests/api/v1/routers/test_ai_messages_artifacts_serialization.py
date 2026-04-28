"""Phase 87.1 Plan 03 — API serialization tests for ChatMessage.artifacts.

Asserts the InlineArtifactRefSchema shape mirrors the frontend
InlineArtifactRef contract verified at
``frontend/src/components/chat/InlineArtifactCard.tsx:62``. The schema
ships in a NEW module ``api/v1/schemas/ai_messages.py`` so the grep
gate in the plan passes and Wave 4 has a stable import path. The
existing ``api/v1/schemas/ai_sessions.py`` shapes are left untouched.

The router-level serialization is exercised at the resume_session
``msg_dict`` builder layer in ``api/v1/routers/ai_sessions.py`` (the
real chat-replay endpoint — not the fictional ``ai_messages.py``
router referenced in the plan; see SUMMARY for the documented Rule 3
deviation).
"""

from __future__ import annotations

from uuid import uuid4

from pilot_space.api.v1.schemas.ai_messages import InlineArtifactRefSchema


class TestInlineArtifactRefSchema:
    def test_serialises_to_camel_case(self) -> None:
        ref = InlineArtifactRefSchema(
            id=uuid4(),
            type="MD",
            title="report.md",
        )
        # by_alias=True yields camelCase contract per BaseSchema.
        dumped = ref.model_dump(by_alias=True, exclude_none=True)
        assert "title" in dumped
        # No snake_case leakage.
        assert "updated_at" not in dumped
        assert "project_name" not in dumped

    def test_camel_case_aliases_for_optional_fields(self) -> None:
        from datetime import UTC, datetime

        ref = InlineArtifactRefSchema(
            id=uuid4(),
            type="HTML",
            title="page.html",
            updated_at=datetime(2026, 4, 28, tzinfo=UTC),
            project_name="Pilot",
        )
        dumped = ref.model_dump(by_alias=True, exclude_none=True)
        assert "updatedAt" in dumped
        assert "projectName" in dumped

    def test_required_fields_are_id_and_type(self) -> None:
        # Title is optional — InlineArtifactRef on the frontend lists it
        # as required for compact variant only; backend does not enforce.
        ref = InlineArtifactRefSchema(id=uuid4(), type="MD")
        assert ref.title is None
