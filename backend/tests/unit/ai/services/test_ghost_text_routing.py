"""Unit tests for GhostText block-type routing and note context injection.

Tests that block_type parameter routes to the correct prompt builder and system prompt,
note_title/linked_issues are injected into system prompts, and backward compatibility
is maintained when block_type is omitted.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from anthropic.types import TextBlock

from pilot_space.ai.prompts.ghost_text import (
    GHOST_TEXT_CODE_SYSTEM_PROMPT,
    GHOST_TEXT_HEADING_SYSTEM_PROMPT,
    GHOST_TEXT_LIST_SYSTEM_PROMPT,
)
from pilot_space.ai.services.ghost_text import (
    _SYSTEM_PROMPT,
    GhostTextService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID: UUID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_ID: UUID = uuid4()
TEST_API_KEY = "sk-ant-test-routing-key"  # pragma: allowlist secret


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get.return_value = None
    redis.set.return_value = True
    return redis


@pytest.fixture
def mock_executor() -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def mock_provider_selector() -> MagicMock:
    selector = MagicMock()
    selector.select.return_value = ("anthropic", "claude-3-5-haiku-20241022")
    return selector


@pytest.fixture
def mock_client_pool() -> MagicMock:
    pool = MagicMock()
    mock_client = AsyncMock()
    pool.get_client.return_value = mock_client
    return pool


@pytest.fixture
def mock_key_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.get_api_key.return_value = TEST_API_KEY
    # Set db=None so _resolve_workspace_provider skips the DB settings lookup
    storage.db = None
    # _resolve_workspace_provider calls get_key_info first, then get_api_key
    mock_key_info = MagicMock()
    mock_key_info.base_url = None
    mock_key_info.model_name = None
    storage.get_key_info.return_value = mock_key_info
    storage.get_all_key_infos.return_value = []
    return storage


@pytest.fixture
def mock_cost_tracker() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    mock_redis: AsyncMock,
    mock_executor: MagicMock,
    mock_provider_selector: MagicMock,
    mock_client_pool: MagicMock,
    mock_key_storage: AsyncMock,
    mock_cost_tracker: AsyncMock,
) -> GhostTextService:
    return GhostTextService(
        redis=mock_redis,
        resilient_executor=mock_executor,
        provider_selector=mock_provider_selector,
        client_pool=mock_client_pool,
        key_storage=mock_key_storage,
        cost_tracker=mock_cost_tracker,
    )


def _anthropic_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    msg.stop_reason = stop_reason
    msg.usage = MagicMock()
    msg.usage.input_tokens = 10
    msg.usage.output_tokens = 5
    return msg


def _make_forwarding_executor(
    mock_client: AsyncMock,
    mock_executor: MagicMock,
    response_text: str = "completion",
) -> None:
    """Configure executor to forward the operation lambda and capture client calls."""
    mock_client.messages.create = AsyncMock(return_value=_anthropic_response(response_text))

    async def forward_operation(
        provider: str,
        operation: Any,
        timeout_sec: float | None = None,
        retry_config: Any = None,
    ) -> Any:
        return await operation()

    mock_executor.execute = AsyncMock(side_effect=forward_operation)


# ---------------------------------------------------------------------------
# _resolve_system_prompt
# ---------------------------------------------------------------------------


class TestResolveSystemPrompt:
    def test_paragraph_uses_default_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt("paragraph")
        assert result == _SYSTEM_PROMPT

    def test_none_uses_default_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt(None)
        assert result == _SYSTEM_PROMPT

    def test_code_block_uses_code_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt("codeBlock")
        assert result == GHOST_TEXT_CODE_SYSTEM_PROMPT

    def test_heading_uses_heading_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt("heading")
        assert result == GHOST_TEXT_HEADING_SYSTEM_PROMPT

    def test_bullet_list_uses_list_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt("bulletList")
        assert result == GHOST_TEXT_LIST_SYSTEM_PROMPT

    def test_unknown_type_falls_back_to_default(self) -> None:
        result = GhostTextService._resolve_system_prompt("taskList")
        assert result == _SYSTEM_PROMPT

    def test_note_title_appended(self) -> None:
        result = GhostTextService._resolve_system_prompt("paragraph", note_title="Sprint Planning")
        assert "<note_title>Sprint Planning</note_title>" in result

    def test_linked_issues_appended(self) -> None:
        result = GhostTextService._resolve_system_prompt(
            "paragraph", linked_issues=["PS-42", "PS-51"]
        )
        assert "PS-42" in result
        assert "PS-51" in result

    def test_note_context_appended_to_code_prompt(self) -> None:
        result = GhostTextService._resolve_system_prompt(
            "codeBlock", note_title="Auth Module", linked_issues=["PS-10"]
        )
        assert result.startswith(GHOST_TEXT_CODE_SYSTEM_PROMPT)
        assert "Auth Module" in result
        assert "PS-10" in result

    def test_no_context_when_both_none(self) -> None:
        result = GhostTextService._resolve_system_prompt("paragraph", None, None)
        assert result == _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# _resolve_user_prompt
# ---------------------------------------------------------------------------


class TestResolveUserPrompt:
    def test_paragraph_uses_default_build_prompt(self) -> None:
        result = GhostTextService._resolve_user_prompt("some context", "prefix text", "paragraph")
        assert "Context: some context" in result
        assert "Complete: prefix text" in result

    def test_none_type_uses_default_build_prompt(self) -> None:
        result = GhostTextService._resolve_user_prompt("ctx", "pre", None)
        assert "Complete: pre" in result

    def test_code_block_uses_code_prompt(self) -> None:
        result = GhostTextService._resolve_user_prompt("fn main()", "let x = ", "codeBlock")
        assert "technical" in result.lower() or "Complete" in result or "complete" in result.lower()
        assert "let x =" in result

    def test_heading_uses_heading_prompt(self) -> None:
        result = GhostTextService._resolve_user_prompt("intro text", "## Getting St", "heading")
        assert "heading" in result.lower() or "complete" in result.lower()
        assert "## Getting St" in result

    def test_bullet_list_uses_list_prompt(self) -> None:
        result = GhostTextService._resolve_user_prompt(
            "- item 1\n- item 2", "- item ", "bulletList"
        )
        assert "list" in result.lower() or "complete" in result.lower()
        assert "- item" in result

    def test_unknown_type_falls_back_to_default(self) -> None:
        result = GhostTextService._resolve_user_prompt("ctx", "pre", "image")
        assert "Complete: pre" in result


# ---------------------------------------------------------------------------
# generate_completion — block-type routing integration
# ---------------------------------------------------------------------------


class TestBlockTypeRouting:
    @pytest.mark.asyncio
    async def test_code_block_sends_code_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="fn main()",
            prefix="let x = ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            block_type="codeBlock",
        )

        call_kwargs: dict[str, Any] = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == GHOST_TEXT_CODE_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_heading_sends_heading_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="intro",
            prefix="## Getting St",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            block_type="heading",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == GHOST_TEXT_HEADING_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_bullet_list_sends_list_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="- item 1",
            prefix="- item ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            block_type="bulletList",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == GHOST_TEXT_LIST_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_paragraph_sends_default_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="some text",
            prefix="continue ",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            block_type="paragraph",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == _SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_unknown_block_type_falls_back_to_default(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="text",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            block_type="taskItem",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# generate_completion — note context injection
# ---------------------------------------------------------------------------


class TestNoteContextInjection:
    @pytest.mark.asyncio
    async def test_note_title_in_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            note_title="Sprint 42 Planning",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Sprint 42 Planning" in call_kwargs["system"]

    @pytest.mark.asyncio
    async def test_linked_issues_in_system_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
            linked_issues=["PS-42", "PS-51"],
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "PS-42" in call_kwargs["system"]
        assert "PS-51" in call_kwargs["system"]

    @pytest.mark.asyncio
    async def test_context_appended_to_all_block_types(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        """Note context should be appended regardless of block type."""
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client

        for block_type in ["paragraph", "codeBlock", "heading", "bulletList"]:
            _make_forwarding_executor(mock_client, mock_executor)

            await service.generate_completion(
                context="ctx",
                prefix="pre",
                workspace_id=WORKSPACE_ID,
                user_id=TEST_USER_ID,
                block_type=block_type,
                note_title="Test Note",
            )

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert "Test Note" in call_kwargs["system"], (
                f"note_title missing for block_type={block_type}"
            )


# ---------------------------------------------------------------------------
# Backward compatibility — no block_type parameter
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_no_block_type_uses_default_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        """Omitting block_type should produce identical behavior to the original service."""
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="some context",
            prefix="prefix text",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == _SYSTEM_PROMPT

        # User prompt should use the default _build_prompt format
        user_msg = call_kwargs["messages"][0]["content"]
        assert "Context: some context" in user_msg
        assert "Complete: prefix text" in user_msg

    @pytest.mark.asyncio
    async def test_no_note_context_keeps_clean_prompt(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
        mock_client_pool: MagicMock,
    ) -> None:
        mock_client = AsyncMock()
        mock_client_pool.get_client.return_value = mock_client
        _make_forwarding_executor(mock_client, mock_executor)

        await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Additional context" not in call_kwargs["system"]

    @pytest.mark.asyncio
    async def test_returns_valid_response_structure(
        self,
        service: GhostTextService,
        mock_executor: MagicMock,
    ) -> None:
        mock_executor.execute = AsyncMock(return_value=_anthropic_response("hello world"))

        result = await service.generate_completion(
            context="ctx",
            prefix="pre",
            workspace_id=WORKSPACE_ID,
            user_id=TEST_USER_ID,
        )

        assert "suggestion" in result
        assert "confidence" in result
        assert "cached" in result
        assert result["suggestion"] == "hello world"


# ---------------------------------------------------------------------------
# Skill loading — daily-standup SKILL.md
# ---------------------------------------------------------------------------


class TestDailyStandupSkillFile:
    """Verify the daily-standup skill file can be discovered and loaded."""

    def test_skill_file_exists(self) -> None:
        from pathlib import Path

        skill_dir = Path(__file__).resolve().parents[4] / (
            "src/pilot_space/ai/templates/skills/daily-standup"
        )
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.is_file(), f"SKILL.md not found at {skill_file}"

    def test_skill_file_has_frontmatter(self) -> None:
        from pathlib import Path

        skill_file = (
            Path(__file__).resolve().parents[4]
            / "src/pilot_space/ai/templates/skills/daily-standup/SKILL.md"
        )
        content = skill_file.read_text()
        assert content.startswith("---")
        assert "name: daily-standup" in content
        assert "description:" in content

    def test_skill_file_references_mcp_tools(self) -> None:
        from pathlib import Path

        skill_file = (
            Path(__file__).resolve().parents[4]
            / "src/pilot_space/ai/templates/skills/daily-standup/SKILL.md"
        )
        content = skill_file.read_text()
        assert "list_issues" in content
        assert "get_issue" in content

    def test_skill_file_has_three_sections(self) -> None:
        from pathlib import Path

        skill_file = (
            Path(__file__).resolve().parents[4]
            / "src/pilot_space/ai/templates/skills/daily-standup/SKILL.md"
        )
        content = skill_file.read_text()
        assert "Yesterday" in content
        assert "Today" in content
        assert "Blockers" in content
