"""Unit tests for homepage router (H058).

Tests route registration, HTTP methods, schema validation, and
response model configuration for all homepage endpoints.

References:
- specs/012-homepage-note/spec.md API Endpoints section
- US-19: Homepage Hub feature
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status
from pydantic import ValidationError

from pilot_space.api.v1.routers.homepage import notes_from_chat_router, router
from pilot_space.api.v1.schemas.homepage import (
    ActivityCardIssue,
    ActivityCardNote,
    ActivityGroupedData,
    ActivityMeta,
    AnnotationPreview,
    AssigneeBrief,
    CreateNoteFromChatData,
    CreateNoteFromChatPayload,
    CreateNoteFromChatResponse,
    DigestData,
    DigestDismissPayload,
    DigestRefreshData,
    DigestRefreshResponse,
    DigestResponse,
    DigestSuggestion,
    HomepageActivityResponse,
    ProjectBrief,
    StateBrief,
)

# ---------------------------------------------------------------------------
# Route registration helpers
# ---------------------------------------------------------------------------


def _get_routes(target_router):
    """Extract (method, path) tuples from a FastAPI router.

    FastAPI routers store the full path including prefix.
    """
    results = []
    for route in target_router.routes:
        methods = getattr(route, "methods", set())
        path = getattr(route, "path", "")
        for m in methods:
            results.append((m, path))
    return results


# Path constants — prefix is baked into route paths by FastAPI
_HP = "/workspaces/{workspace_id}/homepage"
_NP = "/workspaces/{workspace_id}/notes"


# ---------------------------------------------------------------------------
# Route registration tests
# ---------------------------------------------------------------------------


class TestHomepageRouterRegistration:
    """Verify all homepage router routes are registered."""

    def test_get_activity_registered(self) -> None:
        routes = _get_routes(router)
        assert ("GET", f"{_HP}/activity") in routes

    def test_get_digest_registered(self) -> None:
        routes = _get_routes(router)
        assert ("GET", f"{_HP}/digest") in routes

    def test_post_digest_refresh_registered(self) -> None:
        routes = _get_routes(router)
        assert ("POST", f"{_HP}/digest/refresh") in routes

    def test_post_digest_dismiss_registered(self) -> None:
        routes = _get_routes(router)
        assert ("POST", f"{_HP}/digest/dismiss") in routes

    def test_homepage_router_route_count(self) -> None:
        """Exactly 4 homepage routes expected."""
        routes = _get_routes(router)
        assert len(routes) == 4

    def test_notes_from_chat_registered(self) -> None:
        routes = _get_routes(notes_from_chat_router)
        assert ("POST", f"{_NP}/from-chat") in routes

    def test_router_prefix(self) -> None:
        assert router.prefix == "/workspaces/{workspace_id}/homepage"

    def test_notes_from_chat_router_prefix(self) -> None:
        assert notes_from_chat_router.prefix == "/workspaces/{workspace_id}/notes"


# ---------------------------------------------------------------------------
# Response model tests (dismiss endpoint returns 204 NO_CONTENT)
# ---------------------------------------------------------------------------


class TestHomepageRouterResponseModels:
    """Verify response_model is set on endpoints."""

    def test_get_activity_response_model(self) -> None:
        for route in router.routes:
            if getattr(route, "path", "").endswith("/activity") and "GET" in getattr(
                route, "methods", set()
            ):
                assert route.response_model is HomepageActivityResponse
                return
        pytest.fail("GET /activity route not found")

    def test_get_digest_response_model(self) -> None:
        for route in router.routes:
            if getattr(route, "path", "").endswith("/digest") and "GET" in getattr(
                route, "methods", set()
            ):
                assert route.response_model is DigestResponse
                return
        pytest.fail("GET /digest route not found")

    def test_post_refresh_response_model(self) -> None:
        for route in router.routes:
            if getattr(route, "path", "").endswith("/digest/refresh") and "POST" in getattr(
                route, "methods", set()
            ):
                assert route.response_model is DigestRefreshResponse
                return
        pytest.fail("POST /digest/refresh route not found")

    def test_dismiss_returns_204(self) -> None:
        for route in router.routes:
            if getattr(route, "path", "").endswith("/digest/dismiss") and "POST" in getattr(
                route, "methods", set()
            ):
                assert route.status_code == status.HTTP_204_NO_CONTENT
                return
        pytest.fail("POST /digest/dismiss route not found")

    def test_from_chat_returns_201(self) -> None:
        for route in notes_from_chat_router.routes:
            if getattr(route, "path", "").endswith("/from-chat") and "POST" in getattr(
                route, "methods", set()
            ):
                assert route.status_code == status.HTTP_201_CREATED
                return
        pytest.fail("POST /from-chat route not found")


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestHomepageSchemas:
    """Validate Pydantic schema construction and field defaults."""

    def test_activity_card_note_defaults(self) -> None:
        card = ActivityCardNote(
            id=uuid.uuid4(),
            title="Test note",
            word_count=42,
            updated_at=datetime.now(tz=UTC),
        )
        assert card.type == "note"
        assert card.is_pinned is False
        assert card.project is None
        assert card.latest_annotation is None
        assert card.topics == []

    def test_activity_card_issue_full(self) -> None:
        pid = uuid.uuid4()
        aid = uuid.uuid4()
        card = ActivityCardIssue(
            id=uuid.uuid4(),
            identifier="PS-42",
            title="Fix login bug",
            priority="high",
            updated_at=datetime.now(tz=UTC),
            project=ProjectBrief(id=pid, name="Core", identifier="PS"),
            state=StateBrief(name="In Progress", color="#D9853F", group="started"),
            assignee=AssigneeBrief(id=aid, name="Alice", avatar_url=None),
            last_activity="Assigned to Alice",
        )
        assert card.type == "issue"
        assert card.project is not None
        assert card.project.identifier == "PS"
        assert card.state is not None
        assert card.state.group == "started"
        assert card.assignee is not None
        assert card.assignee.name == "Alice"

    def test_digest_suggestion_defaults(self) -> None:
        s = DigestSuggestion(
            id=uuid.uuid4(),
            category="stale_issues",
            title="Review stale issues",
            description="3 issues have not been updated in 7+ days",
        )
        assert s.entity_id is None
        assert s.entity_type is None
        assert s.entity_identifier is None
        assert s.project_id is None
        assert s.project_name is None
        assert s.action_type is None
        assert s.action_label is None
        assert s.action_url is None
        assert s.relevance_score == 0.5

    def test_digest_suggestion_all_fields(self) -> None:
        eid = uuid.uuid4()
        pid = uuid.uuid4()
        s = DigestSuggestion(
            id=uuid.uuid4(),
            category="stale_issues",
            title="Review stale issues",
            description="3 issues have not been updated in 7+ days",
            entity_id=eid,
            entity_type="issue",
            entity_identifier="PS-42",
            project_id=pid,
            project_name="Core",
            action_type="navigate",
            action_label="View Issue",
            action_url="/workspace/core/issues/PS-42",
            relevance_score=0.9,
        )
        assert s.entity_identifier == "PS-42"
        assert s.project_id == pid
        assert s.project_name == "Core"
        assert s.action_type == "navigate"
        assert s.action_label == "View Issue"

    def test_digest_dismiss_payload_validation(self) -> None:
        p = DigestDismissPayload(
            suggestion_id=uuid.uuid4(),
            entity_id=None,
            entity_type=None,
            category="stale_issues",
        )
        assert p.entity_id is None
        assert p.entity_type is None

    def test_digest_dismiss_payload_with_entity(self) -> None:
        eid = uuid.uuid4()
        p = DigestDismissPayload(
            suggestion_id=uuid.uuid4(),
            entity_id=eid,
            entity_type="issue",
            category="stale_issues",
        )
        assert p.entity_id == eid
        assert p.entity_type == "issue"

    def test_activity_grouped_data_defaults(self) -> None:
        data = ActivityGroupedData()
        assert data.today == []
        assert data.yesterday == []
        assert data.this_week == []

    def test_activity_meta_defaults(self) -> None:
        meta = ActivityMeta(total=0)
        assert meta.cursor is None
        assert meta.has_more is False

    def test_digest_data_response(self) -> None:
        resp = DigestResponse(
            data=DigestData(
                generated_at=datetime.now(tz=UTC),
                generated_by="scheduled",
                suggestions=[],
                suggestion_count=0,
            )
        )
        assert resp.data.suggestion_count == 0
        assert resp.data.generated_by == "scheduled"

    def test_digest_refresh_response(self) -> None:
        resp = DigestRefreshResponse(
            data=DigestRefreshData(
                status="generating",
                estimated_seconds=15,
            )
        )
        assert resp.data.status == "generating"
        assert resp.data.estimated_seconds == 15

    def test_create_note_from_chat_payload(self) -> None:
        p = CreateNoteFromChatPayload(
            chat_session_id=uuid.uuid4(),
            title="My note",
        )
        assert p.project_id is None
        assert len(p.title) > 0

    def test_create_note_from_chat_response(self) -> None:
        nid = uuid.uuid4()
        sid = uuid.uuid4()
        resp = CreateNoteFromChatResponse(
            data=CreateNoteFromChatData(
                note_id=nid,
                title="My note",
                source_chat_session_id=sid,
            )
        )
        assert resp.data.note_id == nid
        assert resp.data.source_chat_session_id == sid

    def test_annotation_preview_validation(self) -> None:
        a = AnnotationPreview(type="suggestion", content="test", confidence=0.8)
        assert a.confidence == 0.8

    def test_annotation_preview_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            AnnotationPreview(type="suggestion", content="test", confidence=1.5)

    def test_digest_suggestion_relevance_bounds(self) -> None:
        with pytest.raises(ValidationError):
            DigestSuggestion(
                id=uuid.uuid4(),
                category="stale_issues",
                title="Test",
                description="Test",
                relevance_score=-0.1,
            )
