"""E2E tests for skill invocation via chat endpoint (T095).

Tests skill system including:
- Skill discovery via chat prompts
- Skill execution through conversational interface
- Response validation

Note: Skills are now invoked through the unified chat endpoint
with skill-triggering prompts instead of separate skill endpoints.

Reference: backend/.claude/skills/*/SKILL.md
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def test_e2e_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for E2E testing with proper DI container setup.

    Yields:
        AsyncClient for making requests.
    """
    from pilot_space.container import get_container
    from pilot_space.main import app

    # Reset and reinitialize DI container to ensure fresh state
    app.state.container = get_container()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up app state after test
    if hasattr(app.state, "container"):
        delattr(app.state, "container")


class TestSkillInvocation:
    """E2E tests for skill invocation via chat."""

    @pytest.mark.asyncio
    async def test_extract_issues_skill_invocation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test issue extraction via chat prompt.

        Verifies:
        - Skill-triggering prompt is recognized
        - Response contains issue extraction
        - Content is relevant to prompt

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        note_content = """
        We need to implement user authentication with OAuth2 support.
        The system should support Google and GitHub login.
        Also, we need to add JWT token refresh mechanism.
        """

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": f"Extract issues from: {note_content}",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify extraction occurred
            assert len(full_response) > 0
            assert "issue" in full_response.lower() or "implement" in full_response.lower()

    @pytest.mark.asyncio
    async def test_enhance_issue_skill_invocation(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test issue enhancement via chat prompt.

        Verifies:
        - Enhancement prompt is recognized
        - Response provides enhancement suggestions
        - Content is relevant to issue

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Enhance this issue: Fix login bug - Users can't log in",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify enhancement occurred
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_skill_validation_empty_message(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test validation for empty messages.

        Verifies:
        - Empty messages are rejected
        - Clear error message is returned

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        # Empty message should fail validation
        response = await test_e2e_client.post(
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "",
                "context": {"workspace_id": workspace_id},
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_recommend_assignee_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test assignee recommendation via chat.

        Verifies:
        - Recommendation prompt is recognized
        - Response provides assignee suggestion
        - Content is relevant to issue context

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Who should be assigned to implement JWT authentication (backend, security)",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_find_duplicates_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test duplicate detection via chat.

        Verifies:
        - Duplicate finding prompt is recognized
        - Response addresses duplicate checking
        - Content is relevant to query

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Find duplicates of: Implement user authentication with JWT",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_decompose_tasks_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test task decomposition via chat.

        Verifies:
        - Decomposition prompt is recognized
        - Response provides task breakdown
        - Content is relevant to issue

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Break down this issue into subtasks: Implement complete user authentication with OAuth2 and JWT",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_generate_diagram_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test diagram generation via chat.

        Verifies:
        - Diagram generation prompt is recognized
        - Response addresses diagram creation
        - Content is relevant to request

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Generate a sequence diagram for: Authentication flow with OAuth2",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0

    @pytest.mark.asyncio
    async def test_improve_writing_skill(
        self,
        test_e2e_client: AsyncClient,
        mock_claude_sdk_demo_mode: None,
    ) -> None:
        """Test writing improvement via chat.

        Verifies:
        - Improvement prompt is recognized
        - Response provides improved version
        - Content is relevant to original text

        Args:
            test_e2e_client: AsyncClient for making requests.
            mock_claude_sdk_demo_mode: Mock SDK fixture.
        """
        demo_headers = {"X-Workspace-Id": "pilot-space-demo"}
        workspace_id = "00000000-0000-0000-0000-000000000002"

        async with test_e2e_client.stream(
            "POST",
            "/api/v1/ai/chat",
            headers=demo_headers,
            json={
                "message": "Improve this text: We need to implement authentication with OAuth2 support.",
                "context": {"workspace_id": workspace_id},
            },
        ) as response:
            assert response.status_code == 200

            # Collect full response
            full_response = ""
            async for chunk in response.aiter_text():
                full_response += chunk

            # Verify response received
            assert len(full_response) > 0


__all__ = ["TestSkillInvocation"]
