"""Unit tests for IssueExtractionService.

Tests cover:
- TipTap JSON text extraction
- LLM response parsing
- Confidence tag mapping
- Full extraction flow with mocked LLM
- Empty/invalid content handling
- Error resilience

Feature 009: Intent-to-Issues extraction pipeline.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pilot_space.application.services.extraction.extract_issues_service import (
    ExtractIssuesPayload,
    IssueExtractionService,
    _confidence_tag,
    _extract_text_from_tiptap,
    _parse_extraction_response,
)

# ---------------------------------------------------------------------------
# Unit tests: _confidence_tag
# ---------------------------------------------------------------------------


class TestConfidenceTag:
    """Tests for confidence tag mapping."""

    def test_explicit_threshold(self) -> None:
        assert _confidence_tag(0.7) == "explicit"
        assert _confidence_tag(0.85) == "explicit"
        assert _confidence_tag(1.0) == "explicit"

    def test_implicit_threshold(self) -> None:
        assert _confidence_tag(0.5) == "implicit"
        assert _confidence_tag(0.69) == "implicit"

    def test_related_threshold(self) -> None:
        assert _confidence_tag(0.3) == "related"
        assert _confidence_tag(0.0) == "related"
        assert _confidence_tag(0.49) == "related"


# ---------------------------------------------------------------------------
# Unit tests: _extract_text_from_tiptap
# ---------------------------------------------------------------------------


class TestExtractTextFromTiptap:
    """Tests for TipTap JSON text extraction."""

    def test_simple_paragraph(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"id": "block-1"},
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }
        result = _extract_text_from_tiptap(content)
        assert "Hello world" in result
        assert "block-1" in result

    def test_multiple_blocks(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"id": "h1", "level": 1},
                    "content": [{"type": "text", "text": "Title"}],
                },
                {
                    "type": "paragraph",
                    "attrs": {"id": "p1"},
                    "content": [{"type": "text", "text": "Body text"}],
                },
            ],
        }
        result = _extract_text_from_tiptap(content)
        assert "Title" in result
        assert "Body text" in result
        assert "h1" in result
        assert "p1" in result

    def test_empty_content(self) -> None:
        content = {"type": "doc", "content": []}
        result = _extract_text_from_tiptap(content)
        assert result == ""

    def test_max_chars_limit(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "A" * 10000}],
                }
            ],
        }
        result = _extract_text_from_tiptap(content, max_chars=100)
        assert len(result) <= 100

    def test_nested_list_items(self) -> None:
        content = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "attrs": {"id": "li1"},
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 1"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = _extract_text_from_tiptap(content)
        assert "Item 1" in result


# ---------------------------------------------------------------------------
# Unit tests: _parse_extraction_response
# ---------------------------------------------------------------------------


class TestParseExtractionResponse:
    """Tests for LLM response parsing."""

    def test_valid_json_array(self) -> None:
        raw = json.dumps(
            [
                {"title": "Fix bug", "description": "Fix the login bug", "priority": 1},
                {"title": "Add tests", "description": "Add unit tests", "priority": 2},
            ]
        )
        result = _parse_extraction_response(raw)
        assert len(result) == 2
        assert result[0]["title"] == "Fix bug"

    def test_markdown_fenced_json(self) -> None:
        raw = '```json\n[{"title": "Task 1"}]\n```'
        result = _parse_extraction_response(raw)
        assert len(result) == 1
        assert result[0]["title"] == "Task 1"

    def test_invalid_json(self) -> None:
        raw = "This is not JSON"
        result = _parse_extraction_response(raw)
        assert result == []

    def test_non_list_json(self) -> None:
        raw = json.dumps({"title": "Single item"})
        result = _parse_extraction_response(raw)
        assert result == []

    def test_empty_array(self) -> None:
        raw = "[]"
        result = _parse_extraction_response(raw)
        assert result == []


# ---------------------------------------------------------------------------
# Integration tests: IssueExtractionService.extract
# ---------------------------------------------------------------------------


class TestIssueExtractionService:
    """Tests for the full extraction service."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session: AsyncMock) -> IssueExtractionService:
        return IssueExtractionService(session=mock_session)

    @pytest.fixture
    def sample_payload(self) -> ExtractIssuesPayload:
        return ExtractIssuesPayload(
            workspace_id=uuid4(),
            note_id="note-123",
            note_title="Sprint Planning Notes",
            note_content={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "attrs": {"id": "block-1"},
                        "content": [
                            {"type": "text", "text": "TODO: Fix the login page bug"},
                        ],
                    },
                    {
                        "type": "paragraph",
                        "attrs": {"id": "block-2"},
                        "content": [
                            {"type": "text", "text": "We should add rate limiting to the API"},
                        ],
                    },
                ],
            },
            max_issues=5,
        )

    @pytest.mark.asyncio
    async def test_extract_empty_content(self, service: IssueExtractionService) -> None:
        """Empty note content returns empty result."""
        payload = ExtractIssuesPayload(
            workspace_id=uuid4(),
            note_id="note-empty",
            note_title="Empty",
            note_content={"type": "doc", "content": []},
        )
        result = await service.extract(payload)
        assert result.total_count == 0
        assert result.issues == []
        assert result.model == "noop"

    @pytest.mark.asyncio
    async def test_extract_no_api_key(
        self, service: IssueExtractionService, sample_payload: ExtractIssuesPayload
    ) -> None:
        """No API key returns empty result gracefully."""
        with patch.object(service, "_resolve_api_key", return_value=None):
            result = await service.extract(sample_payload)
            assert result.total_count == 0
            assert result.model == "noop"

    @pytest.mark.asyncio
    async def test_extract_success(
        self, service: IssueExtractionService, sample_payload: ExtractIssuesPayload
    ) -> None:
        """Successful extraction returns parsed issues."""
        llm_response = json.dumps(
            [
                {
                    "title": "Fix login page bug",
                    "description": "Fix the bug on the login page",
                    "priority": 1,
                    "labels": ["bug", "frontend"],
                    "confidence_score": 0.95,
                    "source_block_ids": ["block-1"],
                    "rationale": "Explicitly mentioned as TODO",
                },
                {
                    "title": "Add API rate limiting",
                    "description": "Implement rate limiting for API endpoints",
                    "priority": 2,
                    "labels": ["enhancement", "backend"],
                    "confidence_score": 0.72,
                    "source_block_ids": ["block-2"],
                    "rationale": "Mentioned as should-do",
                },
            ]
        )

        with (
            patch.object(service, "_resolve_api_key", return_value="sk-test-key"),
            patch(
                "pilot_space.application.services.extraction.extract_issues_service.ResilientExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(return_value=llm_response)
            mock_executor_cls.return_value = mock_executor

            result = await service.extract(sample_payload)

            assert result.total_count == 2
            assert result.recommended_count == 2  # Both >= 0.7
            assert result.model != "noop"

            issue1 = result.issues[0]
            assert issue1.title == "Fix login page bug"
            assert issue1.priority == 1
            assert issue1.confidence_tag == "explicit"
            assert "bug" in issue1.labels

            issue2 = result.issues[1]
            assert issue2.title == "Add API rate limiting"
            assert issue2.confidence_tag == "explicit"

    @pytest.mark.asyncio
    async def test_extract_max_issues_respected(self, service: IssueExtractionService) -> None:
        """max_issues limit is enforced on results."""
        payload = ExtractIssuesPayload(
            workspace_id=uuid4(),
            note_id="note-many",
            note_title="Many items",
            note_content={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Lots of tasks here"}],
                    }
                ],
            },
            max_issues=2,
        )

        # LLM returns more than max_issues
        llm_response = json.dumps(
            [
                {
                    "title": f"Issue {i}",
                    "description": f"Desc {i}",
                    "priority": 2,
                    "labels": [],
                    "confidence_score": 0.8,
                    "source_block_ids": [],
                    "rationale": "",
                }
                for i in range(5)
            ]
        )

        with (
            patch.object(service, "_resolve_api_key", return_value="sk-test-key"),
            patch(
                "pilot_space.application.services.extraction.extract_issues_service.ResilientExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(return_value=llm_response)
            mock_executor_cls.return_value = mock_executor

            result = await service.extract(payload)
            assert result.total_count <= 2

    @pytest.mark.asyncio
    async def test_extract_llm_error_graceful(
        self, service: IssueExtractionService, sample_payload: ExtractIssuesPayload
    ) -> None:
        """LLM errors are handled gracefully, returning empty."""
        with (
            patch.object(service, "_resolve_api_key", return_value="sk-test-key"),
            patch(
                "pilot_space.application.services.extraction.extract_issues_service.ResilientExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(side_effect=Exception("LLM error"))
            mock_executor_cls.return_value = mock_executor

            result = await service.extract(sample_payload)
            assert result.total_count == 0
            assert result.model == "noop"

    @pytest.mark.asyncio
    async def test_extract_confidence_clamping(
        self, service: IssueExtractionService, sample_payload: ExtractIssuesPayload
    ) -> None:
        """Confidence scores are clamped to 0-1 range."""
        llm_response = json.dumps(
            [
                {
                    "title": "Over confident",
                    "description": "Desc",
                    "priority": 2,
                    "labels": [],
                    "confidence_score": 1.5,
                    "source_block_ids": [],
                    "rationale": "",
                },
                {
                    "title": "Under confident",
                    "description": "Desc",
                    "priority": -1,
                    "labels": [],
                    "confidence_score": -0.5,
                    "source_block_ids": [],
                    "rationale": "",
                },
            ]
        )

        with (
            patch.object(service, "_resolve_api_key", return_value="sk-test-key"),
            patch(
                "pilot_space.application.services.extraction.extract_issues_service.ResilientExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(return_value=llm_response)
            mock_executor_cls.return_value = mock_executor

            result = await service.extract(sample_payload)
            assert result.issues[0].confidence_score == 1.0
            assert result.issues[1].confidence_score == 0.0
            # Priority clamped too
            assert result.issues[1].priority == 0  # -1 clamped to 0

    @pytest.mark.asyncio
    async def test_extract_with_selected_text(self, service: IssueExtractionService) -> None:
        """Selected text is passed to the prompt."""
        payload = ExtractIssuesPayload(
            workspace_id=uuid4(),
            note_id="note-sel",
            note_title="Notes",
            note_content={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Some context"}],
                    }
                ],
            },
            selected_text="Fix the authentication flow",
        )

        llm_response = json.dumps(
            [
                {
                    "title": "Fix authentication flow",
                    "description": "Fix auth",
                    "priority": 1,
                    "labels": ["auth"],
                    "confidence_score": 0.9,
                    "source_block_ids": [],
                    "rationale": "User selected",
                }
            ]
        )

        with (
            patch.object(service, "_resolve_api_key", return_value="sk-test-key"),
            patch(
                "pilot_space.application.services.extraction.extract_issues_service.ResilientExecutor"
            ) as mock_executor_cls,
        ):
            mock_executor = MagicMock()
            mock_executor.execute = AsyncMock(return_value=llm_response)
            mock_executor_cls.return_value = mock_executor

            result = await service.extract(payload)
            assert result.total_count == 1
            assert result.issues[0].title == "Fix authentication flow"
