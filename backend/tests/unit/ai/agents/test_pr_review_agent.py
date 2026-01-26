"""Unit tests for PRReviewAgent.

Tests migration to Claude Agent SDK patterns:
- StreamingSDKBaseAgent integration
- Input validation
- Large PR handling
- Streaming output
- Structured output parsing
- Cost tracking
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from anthropic.types import Message, TextBlock, Usage

from pilot_space.ai.agents.pr_review_agent import (
    MAX_FILES_FULL_REVIEW,
    MAX_LINES_FULL_REVIEW,
    PRIORITY_FILE_PATTERNS,
    PRReviewAgent,
    PRReviewInput,
    PRReviewOutput,
    ReviewCategory,
    ReviewComment,
    ReviewSeverity,
    _filter_priority_files,
    _is_priority_file,
    _should_partial_review,
)
from pilot_space.ai.agents.sdk_base import AgentContext


@pytest.fixture
def workspace_id() -> UUID:
    """Fixture for workspace ID."""
    return uuid4()


@pytest.fixture
def user_id() -> UUID:
    """Fixture for user ID."""
    return uuid4()


@pytest.fixture
def agent_context(workspace_id: UUID, user_id: UUID) -> AgentContext:
    """Fixture for agent execution context."""
    return AgentContext(
        workspace_id=workspace_id,
        user_id=user_id,
        operation_id=uuid4(),
    )


@pytest.fixture
def mock_tool_registry() -> Mock:
    """Mock ToolRegistry."""
    return Mock()


@pytest.fixture
def mock_provider_selector() -> Mock:
    """Mock ProviderSelector."""
    return Mock()


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    """Mock CostTracker."""
    mock = AsyncMock()
    mock.track = AsyncMock(return_value=Mock(cost_usd=0.50))
    return mock


@pytest.fixture
def mock_resilient_executor() -> Mock:
    """Mock ResilientExecutor."""
    return Mock()


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    """Mock SecureKeyStorage."""
    mock = AsyncMock()
    mock.get_api_key = AsyncMock(return_value="test-api-key")
    return mock


@pytest.fixture
def pr_review_agent(
    mock_tool_registry: Mock,
    mock_provider_selector: Mock,
    mock_cost_tracker: AsyncMock,
    mock_resilient_executor: Mock,
    mock_key_storage: AsyncMock,
) -> PRReviewAgent:
    """Fixture for PRReviewAgent instance."""
    return PRReviewAgent(
        tool_registry=mock_tool_registry,
        provider_selector=mock_provider_selector,
        cost_tracker=mock_cost_tracker,
        resilient_executor=mock_resilient_executor,
        key_storage=mock_key_storage,
    )


@pytest.fixture
def basic_pr_input() -> PRReviewInput:
    """Fixture for basic PR review input."""
    return PRReviewInput(
        pr_number=123,
        pr_title="Add user authentication",
        pr_description="Implements OAuth2 authentication flow",
        diff="""diff --git a/auth.py b/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/auth.py
@@ -0,0 +1,10 @@
+def authenticate(username, password):
+    # Simple authentication
+    if username == "admin":
+        return True
+    return False
""",
        file_contents={"auth.py": "def authenticate(username, password):\n    pass\n"},
        changed_files=["auth.py"],
        project_context={"tech_stack": "Python 3.12, FastAPI"},
    )


@pytest.fixture
def large_pr_input() -> PRReviewInput:
    """Fixture for large PR that triggers partial review."""
    # Create diff with >5000 lines
    diff_lines = ["+ line content\n"] * (MAX_LINES_FULL_REVIEW + 100)
    diff = "".join(diff_lines)

    # Create >50 files with mixed priority
    changed_files = [
        "auth/login.py",
        "auth/oauth.py",
        "security/crypto.py",
        "api/routes/users.py",
        "models/user.py",
        *[f"utils/helper_{i}.py" for i in range(60)],
    ]

    return PRReviewInput(
        pr_number=456,
        pr_title="Large refactoring",
        pr_description="Major system refactoring",
        diff=diff,
        file_contents={f: f"# content of {f}\n" for f in changed_files},
        changed_files=changed_files,
    )


class TestPriorityFileFiltering:
    """Tests for priority file pattern matching."""

    @pytest.mark.parametrize(
        ("file_path", "expected"),
        [
            ("auth/login.py", True),
            ("security/crypto.py", True),
            ("api/routes/users.py", True),
            ("models/user.py", True),
            ("routes/api.py", True),
            ("routers/main.py", True),
            ("middleware/cors.py", True),
            ("services/auth_service.py", True),
            ("domain/entities.py", True),
            ("utils/helpers.py", False),
            ("tests/test_auth.py", False),
            ("README.md", False),
        ],
    )
    def test_is_priority_file(self, file_path: str, expected: bool) -> None:
        """Test priority file pattern matching."""
        assert _is_priority_file(file_path) == expected

    def test_filter_priority_files(self) -> None:
        """Test partitioning files into priority and non-priority."""
        files = [
            "auth/login.py",
            "utils/helpers.py",
            "security/crypto.py",
            "tests/test_auth.py",
            "api/routes.py",
            "README.md",
        ]

        priority, other = _filter_priority_files(files)

        assert set(priority) == {
            "auth/login.py",
            "security/crypto.py",
            "api/routes.py",
        }
        assert set(other) == {
            "utils/helpers.py",
            "tests/test_auth.py",
            "README.md",
        }


class TestPartialReviewDetection:
    """Tests for large PR detection."""

    def test_should_partial_review_by_lines(self) -> None:
        """Test partial review triggered by line count."""
        diff_lines = ["+ line\n"] * (MAX_LINES_FULL_REVIEW + 1)
        diff = "".join(diff_lines)

        input_data = PRReviewInput(
            pr_number=1,
            pr_title="Large PR",
            pr_description="",
            diff=diff,
            changed_files=["file.py"],
        )

        assert _should_partial_review(input_data) is True

    def test_should_partial_review_by_files(self) -> None:
        """Test partial review triggered by file count."""
        changed_files = [f"file_{i}.py" for i in range(MAX_FILES_FULL_REVIEW + 1)]

        input_data = PRReviewInput(
            pr_number=1,
            pr_title="Many files",
            pr_description="",
            diff="+ content\n",
            changed_files=changed_files,
        )

        assert _should_partial_review(input_data) is True

    def test_no_partial_review_small_pr(self, basic_pr_input: PRReviewInput) -> None:
        """Test small PR doesn't trigger partial review."""
        assert _should_partial_review(basic_pr_input) is False


class TestPRReviewAgent:
    """Tests for PRReviewAgent class."""

    def test_agent_name(self, pr_review_agent: PRReviewAgent) -> None:
        """Test agent has correct name."""
        assert pr_review_agent.AGENT_NAME == "pr_review"

    def test_default_model(self, pr_review_agent: PRReviewAgent) -> None:
        """Test agent uses Claude Opus."""
        assert pr_review_agent.DEFAULT_MODEL == "claude-opus-4-5-20251101"

    def test_get_model(self, pr_review_agent: PRReviewAgent) -> None:
        """Test get_model returns correct provider and model."""
        provider, model = pr_review_agent.get_model()

        assert provider == "anthropic"
        assert model == "claude-opus-4-5-20251101"

    @pytest.mark.asyncio
    async def test_prepare_review_input_small_pr(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
    ) -> None:
        """Test _prepare_review_input for small PR."""
        prompt, partial, files_reviewed, files_skipped = (
            await pr_review_agent._prepare_review_input(basic_pr_input)
        )

        assert partial is False
        assert files_reviewed == 1
        assert files_skipped == 0
        assert "Pull Request #123" in prompt
        assert "Add user authentication" in prompt
        assert "auth.py" in prompt

    @pytest.mark.asyncio
    async def test_prepare_review_input_large_pr(
        self,
        pr_review_agent: PRReviewAgent,
        large_pr_input: PRReviewInput,
    ) -> None:
        """Test _prepare_review_input for large PR."""
        prompt, partial, files_reviewed, files_skipped = (
            await pr_review_agent._prepare_review_input(large_pr_input)
        )

        assert partial is True
        assert files_reviewed <= MAX_FILES_FULL_REVIEW
        assert files_skipped > 0
        assert "Partial Review Notice" in prompt


class TestPRReviewExecution:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_validates_pr_number(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
    ) -> None:
        """Test execute validates PR number."""
        basic_pr_input.pr_number = 0

        with pytest.raises(ValueError, match="PR number must be positive"):
            await pr_review_agent.execute(basic_pr_input, agent_context)

    @pytest.mark.asyncio
    async def test_execute_validates_pr_title(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
    ) -> None:
        """Test execute validates PR title."""
        basic_pr_input.pr_title = ""

        with pytest.raises(ValueError, match="PR title is required"):
            await pr_review_agent.execute(basic_pr_input, agent_context)

    @pytest.mark.asyncio
    async def test_execute_validates_diff(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
    ) -> None:
        """Test execute validates diff."""
        basic_pr_input.diff = ""

        with pytest.raises(ValueError, match="PR diff is required"):
            await pr_review_agent.execute(basic_pr_input, agent_context)

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
        mock_cost_tracker: AsyncMock,
    ) -> None:
        """Test successful execute with structured output."""
        # Mock Anthropic client
        with patch("pilot_space.ai.agents.pr_review_agent.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_message = Message(
                id="msg_123",
                type="message",
                role="assistant",
                content=[
                    TextBlock(
                        type="text",
                        text='{"summary": "Good PR", "approval_recommendation": "approve", "comments": []}',
                    )
                ],
                model="claude-opus-4-5-20251101",
                stop_reason="end_turn",
                usage=Usage(input_tokens=1000, output_tokens=500),
            )
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            # Execute
            result = await pr_review_agent.execute(basic_pr_input, agent_context)

            # Verify result
            assert isinstance(result, PRReviewOutput)
            assert result.summary == "Good PR"
            assert result.approval_recommendation == "approve"
            assert len(result.comments) == 0

            # Verify API calls
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["model"] == "claude-opus-4-5-20251101"
            assert call_kwargs["max_tokens"] == 8192

            # Verify cost tracking
            mock_cost_tracker.track.assert_awaited_once()
            track_kwargs = mock_cost_tracker.track.call_args.kwargs
            assert track_kwargs["workspace_id"] == agent_context.workspace_id
            assert track_kwargs["user_id"] == agent_context.user_id
            assert track_kwargs["agent_name"] == "pr_review"
            assert track_kwargs["input_tokens"] == 1000
            assert track_kwargs["output_tokens"] == 500


class TestPRReviewStreaming:
    """Tests for stream() method."""

    @pytest.mark.asyncio
    async def test_stream_validates_input(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
    ) -> None:
        """Test stream validates input."""
        basic_pr_input.pr_number = 0

        chunks: list[str] = []
        async for chunk in pr_review_agent.stream(basic_pr_input, agent_context):
            chunks.append(chunk)

        output = "".join(chunks)
        assert "error" in output.lower()
        assert "positive" in output.lower()

    @pytest.mark.asyncio
    async def test_stream_success(
        self,
        pr_review_agent: PRReviewAgent,
        basic_pr_input: PRReviewInput,
        agent_context: AgentContext,
    ) -> None:
        """Test successful streaming."""
        # Mock Anthropic streaming
        with patch("pilot_space.ai.agents.pr_review_agent.Anthropic") as mock_anthropic:
            mock_client = MagicMock()

            # Create mock stream manager
            class MockStreamManager:
                def __enter__(self) -> MockStreamManager:
                    return self

                def __exit__(self, *args: object) -> None:
                    pass

                @property
                def text_stream(self) -> list[str]:
                    return ["chunk1", "chunk2", "chunk3"]

            mock_client.messages.stream.return_value = MockStreamManager()
            mock_anthropic.return_value = mock_client

            # Stream
            chunks: list[str] = []
            async for chunk in pr_review_agent.stream(basic_pr_input, agent_context):
                chunks.append(chunk)

            # Verify output
            assert chunks == ["chunk1", "chunk2", "chunk3"]


class TestReviewDataStructures:
    """Tests for review data structures."""

    def test_review_severity_values(self) -> None:
        """Test ReviewSeverity enum values."""
        assert ReviewSeverity.CRITICAL == "critical"
        assert ReviewSeverity.WARNING == "warning"
        assert ReviewSeverity.SUGGESTION == "suggestion"
        assert ReviewSeverity.INFO == "info"

    def test_review_category_values(self) -> None:
        """Test ReviewCategory enum values."""
        assert ReviewCategory.ARCHITECTURE == "architecture"
        assert ReviewCategory.SECURITY == "security"
        assert ReviewCategory.QUALITY == "quality"
        assert ReviewCategory.PERFORMANCE == "performance"
        assert ReviewCategory.DOCUMENTATION == "documentation"

    def test_review_comment_creation(self) -> None:
        """Test ReviewComment dataclass."""
        comment = ReviewComment(
            file_path="auth.py",
            line_number=42,
            severity=ReviewSeverity.CRITICAL,
            category=ReviewCategory.SECURITY,
            message="SQL injection vulnerability",
            suggestion="Use parameterized queries",
        )

        assert comment.file_path == "auth.py"
        assert comment.line_number == 42
        assert comment.severity == ReviewSeverity.CRITICAL
        assert comment.category == ReviewCategory.SECURITY
        assert comment.message == "SQL injection vulnerability"
        assert comment.suggestion == "Use parameterized queries"

    def test_pr_review_output_post_init(self) -> None:
        """Test PRReviewOutput calculates counts correctly."""
        comments = [
            ReviewComment(
                file_path="a.py",
                line_number=1,
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                message="Issue 1",
            ),
            ReviewComment(
                file_path="b.py",
                line_number=2,
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                message="Issue 2",
            ),
            ReviewComment(
                file_path="c.py",
                line_number=3,
                severity=ReviewSeverity.WARNING,
                category=ReviewCategory.QUALITY,
                message="Issue 3",
            ),
            ReviewComment(
                file_path="d.py",
                line_number=4,
                severity=ReviewSeverity.SUGGESTION,
                category=ReviewCategory.PERFORMANCE,
                message="Issue 4",
            ),
        ]

        output = PRReviewOutput(
            summary="Review complete",
            comments=comments,
            approval_recommendation="request_changes",
        )

        assert output.critical_count == 2
        assert output.warning_count == 1
        assert output.suggestion_count == 1
        assert output.info_count == 0
        assert output.categories_summary["security"] == 2
        assert output.categories_summary["quality"] == 1
        assert output.categories_summary["performance"] == 1


class TestPriorityFilePatterns:
    """Tests for PRIORITY_FILE_PATTERNS constant."""

    def test_priority_patterns_coverage(self) -> None:
        """Test priority patterns cover expected directories."""
        expected_patterns = {
            "auth/",
            "security/",
            "api/",
            "models/",
            "routes/",
            "routers/",
            "middleware/",
            "services/",
            "domain/",
        }

        assert set(PRIORITY_FILE_PATTERNS) == expected_patterns
