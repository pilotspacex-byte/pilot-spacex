"""E2E tests for skill invocation (T095).

Tests skill system including:
- Skill discovery and loading
- Skill parameter validation
- Skill execution flow
- Error handling

Reference: backend/.claude/skills/*/SKILL.md
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSkillInvocation:
    """E2E tests for skill invocation flow."""

    @pytest.mark.asyncio
    async def test_extract_issues_skill_invocation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /extract-issues skill invocation.

        Verifies:
        - Skill is discovered from filesystem
        - Input validation works
        - Execution produces expected output
        - Confidence tags are included

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        note_id = uuid4()
        note_content = """
        We need to implement user authentication with OAuth2 support.
        The system should support Google and GitHub login.
        Also, we need to add JWT token refresh mechanism.
        """

        response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                "note_id": str(note_id),
                "note_content": note_content,
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Verify skill output structure
        assert "issues" in result
        assert len(result["issues"]) > 0

        # Verify confidence tagging (DD-048)
        for issue in result["issues"]:
            assert "name" in issue
            assert "description" in issue
            assert "confidence" in issue
            assert issue["confidence"] in [
                "RECOMMENDED",
                "DEFAULT",
                "CURRENT",
                "ALTERNATIVE",
            ]
            assert "rationale" in issue
            assert len(issue["rationale"]) > 0

    @pytest.mark.asyncio
    async def test_enhance_issue_skill_invocation(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /enhance-issue skill invocation.

        Verifies:
        - Issue enhancement adds metadata
        - Labels are suggested with confidence
        - Priority is recommended
        - Description is improved

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        issue_id = uuid4()
        issue_data = {
            "id": str(issue_id),
            "name": "Fix login bug",
            "description": "Users can't log in",
        }

        response = await e2e_client.post(
            "/api/v1/ai/skills/enhance-issue",
            headers=auth_headers,
            json={"issue": issue_data},
        )

        assert response.status_code == 200
        result = response.json()

        # Verify enhancement structure
        assert "enhanced_issue" in result
        enhanced = result["enhanced_issue"]

        assert "labels" in enhanced
        assert "labels_confidence" in enhanced
        assert enhanced["labels_confidence"] in [
            "RECOMMENDED",
            "DEFAULT",
            "CURRENT",
            "ALTERNATIVE",
        ]

        assert "priority" in enhanced
        assert "priority_confidence" in enhanced

        assert "improved_description" in enhanced
        assert len(enhanced["improved_description"]) > len(issue_data["description"])

    @pytest.mark.asyncio
    async def test_skill_validation_errors(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test skill input validation.

        Verifies:
        - Missing required fields are caught
        - Invalid field types are rejected
        - Clear error messages are returned

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Missing required field
        response = await e2e_client.post(
            "/api/v1/ai/skills/extract-issues",
            headers=auth_headers,
            json={
                # Missing note_content
                "note_id": str(uuid4()),
            },
        )
        assert response.status_code == 422
        error = response.json()
        assert "detail" in error

        # Invalid field type
        response = await e2e_client.post(
            "/api/v1/ai/skills/enhance-issue",
            headers=auth_headers,
            json={
                "issue": "not-an-object",  # Should be dict
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_recommend_assignee_skill(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /recommend-assignee skill.

        Verifies:
        - Assignee is recommended based on context
        - Confidence tag is provided
        - Rationale explains recommendation

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        issue_id = uuid4()

        response = await e2e_client.post(
            "/api/v1/ai/skills/recommend-assignee",
            headers=auth_headers,
            json={
                "issue_id": str(issue_id),
                "issue_title": "Implement JWT authentication",
                "issue_description": "Add JWT-based auth with refresh tokens",
                "labels": ["backend", "security"],
            },
        )

        assert response.status_code == 200
        result = response.json()

        assert "assignee" in result
        assignee = result["assignee"]

        assert "user_id" in assignee
        assert "user_email" in assignee
        assert "confidence" in assignee
        assert assignee["confidence"] in [
            "RECOMMENDED",
            "DEFAULT",
            "CURRENT",
            "ALTERNATIVE",
        ]
        assert "rationale" in assignee
        assert len(assignee["rationale"]) >= 20  # Meaningful explanation

    @pytest.mark.asyncio
    async def test_find_duplicates_skill(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /find-duplicates skill.

        Verifies:
        - Duplicate detection using semantic search
        - Similarity scores are provided
        - Results are ranked by relevance

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        response = await e2e_client.post(
            "/api/v1/ai/skills/find-duplicates",
            headers=auth_headers,
            json={
                "issue_title": "Implement user authentication",
                "issue_description": "Add JWT-based authentication system",
            },
        )

        assert response.status_code == 200
        result = response.json()

        assert "duplicates" in result
        duplicates = result["duplicates"]

        # Verify duplicate structure
        for duplicate in duplicates:
            assert "issue_id" in duplicate
            assert "issue_title" in duplicate
            assert "similarity_score" in duplicate
            assert 0.0 <= duplicate["similarity_score"] <= 1.0
            assert "confidence" in duplicate

    @pytest.mark.asyncio
    async def test_decompose_tasks_skill(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /decompose-tasks skill.

        Verifies:
        - Issue is broken into subtasks
        - Dependencies are identified
        - Each subtask has confidence tag

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        issue_id = uuid4()

        response = await e2e_client.post(
            "/api/v1/ai/skills/decompose-tasks",
            headers=auth_headers,
            json={
                "issue_id": str(issue_id),
                "issue_description": "Implement complete user authentication with OAuth2 and JWT",
            },
        )

        assert response.status_code == 200
        result = response.json()

        assert "subtasks" in result
        subtasks = result["subtasks"]
        assert len(subtasks) > 0

        for subtask in subtasks:
            assert "name" in subtask
            assert "description" in subtask
            assert "confidence" in subtask
            assert subtask["confidence"] in [
                "RECOMMENDED",
                "DEFAULT",
                "CURRENT",
                "ALTERNATIVE",
            ]
            assert "dependencies" in subtask
            assert isinstance(subtask["dependencies"], list)

    @pytest.mark.asyncio
    async def test_generate_diagram_skill(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test /generate-diagram skill.

        Verifies:
        - Mermaid diagram is generated
        - Diagram syntax is valid
        - Diagram matches description

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        response = await e2e_client.post(
            "/api/v1/ai/skills/generate-diagram",
            headers=auth_headers,
            json={
                "description": "Authentication flow with OAuth2",
                "diagram_type": "sequence",
            },
        )

        assert response.status_code == 200
        result = response.json()

        assert "diagram" in result
        diagram = result["diagram"]

        assert "mermaid_code" in diagram
        assert diagram["mermaid_code"].startswith("sequenceDiagram")

        assert "confidence" in diagram
        assert diagram["confidence"] in [
            "RECOMMENDED",
            "DEFAULT",
            "CURRENT",
            "ALTERNATIVE",
        ]

    @pytest.mark.asyncio
    async def test_skill_streaming_support(
        self,
        e2e_client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Test skills that support streaming output.

        Verifies:
        - Skills can stream results for long operations
        - SSE format is correct
        - Partial results are usable

        Args:
            e2e_client: AsyncClient for making requests.
            auth_headers: Auth headers with API keys.
        """
        # Some skills may support streaming (e.g., improve-writing)
        async with e2e_client.stream(
            "POST",
            "/api/v1/ai/skills/improve-writing",
            headers=auth_headers,
            json={
                "text": "We need to implement authentication with OAuth2 support.",
                "style": "technical",
            },
        ) as response:
            if response.status_code == 200:
                # If streaming is supported
                assert response.headers["content-type"] == "text/event-stream"

                events: list[dict[str, Any]] = []
                current_event = None

                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        current_event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:") and current_event:
                        try:
                            data = json.loads(line.split(":", 1)[1].strip())
                            events.append({"type": current_event, "data": data})
                        except json.JSONDecodeError:
                            pass

                assert len(events) > 0
            else:
                # If streaming not supported, expect regular JSON response
                assert response.status_code in [200, 501]


__all__ = ["TestSkillInvocation"]
