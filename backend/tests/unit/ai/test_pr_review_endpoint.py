"""Unit tests for PR review endpoint and PRReviewSubagent configuration.

Coverage:
- Group 1: StreamPRReviewRequest defaults (Pydantic schema)
- Group 2: PRReviewSubagent class configuration (tools, inheritance, stream method)
- Group 3: SSE endpoint — no-integration error path via httpx.AsyncClient
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

# ============================================================================
# Group 1: StreamPRReviewRequest defaults
# ============================================================================


class TestStreamPRReviewRequestDefaults:
    """StreamPRReviewRequest Pydantic schema — field defaults."""

    def test_all_aspects_default_true(self) -> None:
        """All review aspect flags default to True."""
        from pilot_space.api.v1.routers.ai_pr_review import StreamPRReviewRequest

        req = StreamPRReviewRequest()

        assert req.include_architecture is True
        assert req.include_security is True
        assert req.include_performance is True

    def test_post_comments_defaults_false(self) -> None:
        """post_comments defaults to False (MVP: disabled)."""
        from pilot_space.api.v1.routers.ai_pr_review import StreamPRReviewRequest

        req = StreamPRReviewRequest()

        assert req.post_comments is False

    def test_force_refresh_defaults_false(self) -> None:
        """force_refresh defaults to False."""
        from pilot_space.api.v1.routers.ai_pr_review import StreamPRReviewRequest

        req = StreamPRReviewRequest()

        assert req.force_refresh is False

    def test_explicit_values_round_trip(self) -> None:
        """Explicit overrides are preserved."""
        from pilot_space.api.v1.routers.ai_pr_review import StreamPRReviewRequest

        req = StreamPRReviewRequest(
            include_architecture=False,
            include_security=False,
            include_performance=False,
            post_comments=True,
            force_refresh=True,
        )

        assert req.include_architecture is False
        assert req.include_security is False
        assert req.include_performance is False
        assert req.post_comments is True
        assert req.force_refresh is True


# ============================================================================
# Group 1 (cont.): PRReviewInput dataclass — pure construction tests
# ============================================================================


class TestPRReviewInputDataclass:
    """PRReviewInput is a plain dataclass — tests cover valid construction
    and required fields.  Validation of pr_number >= 1 is enforced by the
    FastAPI Path() constraint, not the dataclass itself."""

    def test_valid_input_constructs_without_error(self) -> None:
        """PRReviewInput with positive pr_number constructs cleanly."""
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewInput

        repo_id = uuid4()
        pr_input = PRReviewInput(
            repository_id=repo_id,
            pr_number=42,
        )

        assert pr_input.repository_id == repo_id
        assert pr_input.pr_number == 42
        assert pr_input.include_architecture is True
        assert pr_input.include_security is True
        assert pr_input.include_performance is True

    def test_aspect_flags_can_be_disabled(self) -> None:
        """PRReviewInput accepts False for all optional aspect flags."""
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewInput

        pr_input = PRReviewInput(
            repository_id=uuid4(),
            pr_number=1,
            include_architecture=False,
            include_security=False,
            include_performance=False,
        )

        assert pr_input.include_architecture is False
        assert pr_input.include_security is False
        assert pr_input.include_performance is False


# ============================================================================
# Group 2: Subagent configuration
# ============================================================================


class TestSubagentConfiguration:
    """PRReviewSubagent class-level structural checks."""

    def test_subagent_is_streaming_agent(self) -> None:
        """PRReviewSubagent inherits from StreamingSDKBaseAgent."""
        from pilot_space.ai.agents.agent_base import StreamingSDKBaseAgent
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

        assert issubclass(PRReviewSubagent, StreamingSDKBaseAgent)

    def test_subagent_stream_method_exists(self) -> None:
        """PRReviewSubagent exposes `stream`, not `execute_stream`."""
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

        assert hasattr(PRReviewSubagent, "stream")
        assert not hasattr(PRReviewSubagent, "execute_stream")

    def test_subagent_allowed_tools_contain_github_prefix(self) -> None:
        """Every tool in _create_agent_options.allowed_tools starts with mcp__github__."""
        from pilot_space.ai.agents.agent_base import AgentContext
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

        # Use __new__ to skip __init__; we only need to call _create_agent_options
        subagent = PRReviewSubagent.__new__(PRReviewSubagent)
        context = AgentContext(workspace_id=uuid4(), user_id=uuid4())
        options = subagent._create_agent_options(context)

        assert len(options.allowed_tools) > 0, "allowed_tools must not be empty"
        for tool in options.allowed_tools:
            assert tool.startswith("mcp__github__"), (
                f"Tool '{tool}' does not start with 'mcp__github__'"
            )

    def test_subagent_allowed_tools_covers_expected_operations(self) -> None:
        """Allowed tools include the four required GitHub operations."""
        from pilot_space.ai.agents.agent_base import AgentContext
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

        subagent = PRReviewSubagent.__new__(PRReviewSubagent)
        context = AgentContext(workspace_id=uuid4(), user_id=uuid4())
        options = subagent._create_agent_options(context)

        # search_code_in_repo removed from allowed_tools (returns empty, wastes tokens)
        expected = {
            "mcp__github__get_pr_details",
            "mcp__github__get_pr_diff",
            "mcp__github__post_pr_comment",
        }
        assert expected == set(options.allowed_tools)

    def test_subagent_default_model_is_sonnet(self) -> None:
        """PRReviewSubagent uses Sonnet as default model."""
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent
        from pilot_space.ai.sdk.config import MODEL_SONNET

        assert PRReviewSubagent.DEFAULT_MODEL == MODEL_SONNET

    def test_subagent_agent_name_set(self) -> None:
        """PRReviewSubagent.AGENT_NAME is a non-empty string."""
        from pilot_space.ai.agents.subagents.pr_review_subagent import PRReviewSubagent

        assert isinstance(PRReviewSubagent.AGENT_NAME, str)
        assert PRReviewSubagent.AGENT_NAME != ""


# ============================================================================
# Group 3: SSE endpoint — no integration path
# ============================================================================


def _build_test_app(*, bypass_auth: bool = False) -> Any:
    """Build a minimal FastAPI app wired with a mock DI container.

    Args:
        bypass_auth: If True, override auth dependencies with no-ops so tests
            that focus on business logic (not auth) can reach the route handler.
    """
    from uuid import uuid4 as _uuid4

    from fastapi import FastAPI

    from pilot_space.api.v1.routers.ai_pr_review import router
    from pilot_space.dependencies.auth import get_current_user_id
    from pilot_space.dependencies.workspace import get_current_workspace_id

    app = FastAPI()
    app.include_router(router)

    # Attach a mock container so the container guard passes
    mock_container = MagicMock()
    mock_container.provider_selector.return_value = MagicMock()
    mock_container.resilient_executor.return_value = MagicMock()
    app.state.container = mock_container

    if bypass_auth:
        _fixed_user_id = _uuid4()
        _fixed_workspace_id = _uuid4()
        app.dependency_overrides[get_current_user_id] = lambda: _fixed_user_id
        app.dependency_overrides[get_current_workspace_id] = lambda: _fixed_workspace_id

    return app


async def _collect_sse_chunks(response: Any) -> list[str]:
    """Collect all text chunks from an httpx streaming response."""
    chunks: list[str] = []
    async for chunk in response.aiter_text():
        if chunk.strip():
            chunks.append(chunk)
    return chunks


class TestStreamPRReviewEndpoint:
    """Integration-level tests for the stream_pr_review SSE endpoint."""

    async def test_no_integration_yields_error_event(self) -> None:
        """When get_active_github() returns None the endpoint yields an SSE error event."""
        from pilot_space.dependencies.auth import get_current_user_id
        from pilot_space.dependencies.workspace import get_current_workspace_id

        repo_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()

        app = _build_test_app()
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        app.dependency_overrides[get_current_workspace_id] = lambda: workspace_id

        mock_integration_repo = AsyncMock()
        mock_integration_repo.get_active_github.return_value = None

        with (
            patch(
                "pilot_space.infrastructure.database.repositories"
                ".integration_repository.IntegrationRepository.get_active_github",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "pilot_space.infrastructure.database.repositories"
                ".integration_repository.IntegrationRepository.__init__",
                return_value=None,
            ),
            patch(
                "pilot_space.infrastructure.database.repositories"
                ".integration_repository.IntegrationRepository",
                return_value=mock_integration_repo,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.stream(
                    "POST",
                    f"/ai/repos/{repo_id}/prs/1/review",
                    json={},
                ) as response:
                    chunks = await _collect_sse_chunks(response)

        full_body = "".join(chunks)
        assert "event: error" in full_body, (
            f"Expected 'event: error' in SSE response, got: {full_body!r}"
        )

    async def test_no_integration_error_event_contains_integration_not_found_type(
        self,
    ) -> None:
        """The error SSE event payload identifies the error as integration_not_found."""
        from pilot_space.dependencies.auth import get_current_user_id
        from pilot_space.dependencies.workspace import get_current_workspace_id

        repo_id = uuid4()
        workspace_id = uuid4()
        user_id = uuid4()

        app = _build_test_app()
        app.dependency_overrides[get_current_user_id] = lambda: user_id
        app.dependency_overrides[get_current_workspace_id] = lambda: workspace_id

        mock_integration_repo = AsyncMock()
        mock_integration_repo.get_active_github.return_value = None

        with patch(
            "pilot_space.infrastructure.database.repositories"
            ".integration_repository.IntegrationRepository",
            return_value=mock_integration_repo,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                async with client.stream(
                    "POST",
                    f"/ai/repos/{repo_id}/prs/1/review",
                    json={},
                ) as response:
                    chunks = await _collect_sse_chunks(response)

        full_body = "".join(chunks)
        assert "integration_not_found" in full_body, (
            f"Expected 'integration_not_found' in error payload, got: {full_body!r}"
        )

    async def test_route_requires_positive_pr_number(self) -> None:
        """FastAPI Path(ge=1) rejects pr_number=0 with 422 Unprocessable Entity.

        Auth is bypassed via dependency_overrides so path validation is
        evaluated before auth middleware raises 401.
        """
        from pilot_space.dependencies.auth import get_current_user_id
        from pilot_space.dependencies.workspace import get_current_workspace_id

        repo_id = uuid4()
        workspace_id = uuid4()

        app = _build_test_app()
        app.dependency_overrides[get_current_user_id] = uuid4
        app.dependency_overrides[get_current_workspace_id] = lambda: workspace_id

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/ai/repos/{repo_id}/prs/0/review",
                json={},
            )

        assert response.status_code == 422

    async def test_route_rejects_negative_pr_number(self) -> None:
        """FastAPI Path(ge=1) rejects negative pr_number with 422."""
        from pilot_space.dependencies.auth import get_current_user_id
        from pilot_space.dependencies.workspace import get_current_workspace_id

        repo_id = uuid4()
        workspace_id = uuid4()

        app = _build_test_app()
        app.dependency_overrides[get_current_user_id] = uuid4
        app.dependency_overrides[get_current_workspace_id] = lambda: workspace_id

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/ai/repos/{repo_id}/prs/-1/review",
                json={},
            )

        assert response.status_code == 422
