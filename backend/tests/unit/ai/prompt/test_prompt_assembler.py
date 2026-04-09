"""Unit tests for the 6-layer prompt assembler."""

from __future__ import annotations

import pytest

from pilot_space.ai.prompt.layer_loaders import clear_caches
from pilot_space.ai.prompt.models import PromptLayerConfig
from pilot_space.ai.prompt.prompt_assembler import assemble_system_prompt


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Clear template caches before each test."""
    clear_caches()


class TestPackageReExport:
    """Tests that the package __init__.py re-exports work."""

    @pytest.mark.asyncio
    async def test_import_via_package(self) -> None:
        from pilot_space.ai.prompt import assemble_system_prompt as pkg_fn

        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await pkg_fn(config)
        assert "PilotSpace AI" in result.prompt


class TestMinimalAssembly:
    """Tests for minimal prompt assembly (layers 1+2 only)."""

    @pytest.mark.asyncio
    async def test_loads_identity_and_safety(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        assert "PilotSpace AI" in result.prompt
        assert "Safety reasoning" in result.prompt
        assert "identity" in result.layers_loaded
        assert "safety_tools_style" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_general_intent_for_hello(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        # "hello" matches no patterns → GENERAL → no rules loaded
        assert result.rules_loaded == []
        # Should have "Available Rule Domains" section
        assert "Available Rule Domains" in result.prompt

    @pytest.mark.asyncio
    async def test_estimated_tokens_reasonable(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        assert result.estimated_tokens > 0
        assert result.estimated_tokens == len(result.prompt) // 4


class TestIdentityFallback:
    """Tests for layer 1 fallback when template file is missing."""

    @pytest.mark.asyncio
    async def test_fallback_identity_when_template_missing(self) -> None:
        from unittest.mock import AsyncMock, patch

        from pilot_space.ai.prompt.prompt_assembler import _FALLBACK_IDENTITY

        with patch(
            "pilot_space.ai.prompt.prompt_assembler.load_static_layer",
            new_callable=AsyncMock,
        ) as mock_load:
            # layer1 missing, layer2 present
            mock_load.side_effect = lambda f: "" if "layer1" in f else "## Safety reasoning\ntest"
            config = PromptLayerConfig(user_message="hello")
            result = await assemble_system_prompt(config)

        assert _FALLBACK_IDENTITY in result.prompt
        assert "identity:fallback" in result.layers_loaded


class TestRoleLayer:
    """Tests for layer 3 (role adaptation)."""

    @pytest.mark.asyncio
    async def test_with_developer_role(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)

        assert "Your User's Role" in result.prompt
        assert "role:developer" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_missing_role_skips_layer(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="nonexistent_role_xyz",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)

        assert "Your User's Role" not in result.prompt
        assert not any(layer.startswith("role:") for layer in result.layers_loaded)

    @pytest.mark.asyncio
    async def test_no_role_skips_layer(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        assert "Your User's Role" not in result.prompt


class TestWorkspaceLayer:
    """Tests for layer 4 (workspace context)."""

    @pytest.mark.asyncio
    async def test_with_workspace_name(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            workspace_name="my-team",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)

        assert "Workspace: my-team" in result.prompt
        assert "workspace" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_with_project_names(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            project_names=["alpha", "beta"],
            user_message="hello",
        )
        result = await assemble_system_prompt(config)

        assert "Active projects: alpha, beta" in result.prompt

    @pytest.mark.asyncio
    async def test_no_workspace_skips_layer(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        assert "Workspace Context" not in result.prompt
        assert "workspace" not in result.layers_loaded


class TestIntentRulesLayer:
    """Tests for layer 5 (intent-based rules)."""

    @pytest.mark.asyncio
    async def test_issue_message_loads_issues_rule(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="create an issue for the login bug",
        )
        result = await assemble_system_prompt(config)

        assert "issues.md" in result.rules_loaded
        assert "Operational Rules" in result.prompt

    @pytest.mark.asyncio
    async def test_pm_blocks_loads_multiple_rules(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="write a decision record",
        )
        result = await assemble_system_prompt(config)

        assert "pm_blocks.md" in result.rules_loaded
        assert "notes.md" in result.rules_loaded

    @pytest.mark.asyncio
    async def test_note_writing_loads_notes_rule(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="draft a document about API design",
        )
        result = await assemble_system_prompt(config)

        assert "notes.md" in result.rules_loaded

    @pytest.mark.asyncio
    async def test_multi_intent_loads_all_relevant_rules(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="write content and create an issue for the bug",
        )
        result = await assemble_system_prompt(config)

        # Should load rules for both note_writing and issue_mgmt
        loaded = set(result.rules_loaded)
        assert len(loaded) >= 2

    @pytest.mark.asyncio
    async def test_unloaded_rules_have_summaries(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="draft a document",
        )
        result = await assemble_system_prompt(config)

        # notes.md loaded, so issues.md and pm_blocks.md summaries shown
        assert "Available Rule Domains" in result.prompt
        assert "issues.md" in result.prompt


class TestSessionLayer:
    """Tests for layer 6 (session state)."""

    @pytest.mark.asyncio
    async def test_memory_entries(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            memory_entries=[
                {"source_type": "note", "content": "Auth uses JWT tokens"},
                {"source_type": "issue", "content": "Login bug reported"},
            ],
        )
        result = await assemble_system_prompt(config)

        assert "Workspace Memory Context" in result.prompt
        assert "[note] Auth uses JWT tokens" in result.prompt
        assert "[issue] Login bug reported" in result.prompt
        assert "session" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_conversation_summary(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            conversation_summary="Discussed API design for auth module.",
        )
        result = await assemble_system_prompt(config)

        assert "Conversation Summary" in result.prompt
        assert "Discussed API design" in result.prompt

    @pytest.mark.asyncio
    async def test_pending_approvals(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            pending_approvals=3,
        )
        result = await assemble_system_prompt(config)

        assert "3 pending approvals awaiting your response" in result.prompt

    @pytest.mark.asyncio
    async def test_pending_approval_singular(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            pending_approvals=1,
        )
        result = await assemble_system_prompt(config)

        assert "1 pending approval awaiting your response" in result.prompt

    @pytest.mark.asyncio
    async def test_budget_warning(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            budget_warning="90% of token budget used",
        )
        result = await assemble_system_prompt(config)

        assert "Budget: 90% of token budget used" in result.prompt

    @pytest.mark.asyncio
    async def test_no_session_state_skips_layer(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)

        assert "session" not in result.layers_loaded


class TestSkillsLayer:
    """Tests for skills layer (between workspace and session)."""

    @pytest.mark.asyncio
    async def test_with_user_skills(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            user_skills=[
                {"name": "Python Expert", "description": "Advanced Python development"},
                {
                    "name": "TDD Coach",
                    "description": "Test-driven development practices",
                },
            ],
        )
        result = await assemble_system_prompt(config)

        assert "Your Skills" in result.prompt
        assert "Python Expert" in result.prompt
        assert "Advanced Python development" in result.prompt
        assert "TDD Coach" in result.prompt
        assert "Test-driven development practices" in result.prompt
        assert "skills" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_no_skills_skips_layer(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            user_skills=[],
        )
        result = await assemble_system_prompt(config)

        assert "Your Skills" not in result.prompt
        assert "skills" not in result.layers_loaded

    @pytest.mark.asyncio
    async def test_skill_without_description(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            user_skills=[
                {"name": "No Desc Skill", "description": ""},
            ],
        )
        result = await assemble_system_prompt(config)

        assert "No Desc Skill" in result.prompt
        # Should appear without colon-description suffix
        assert "No Desc Skill**:" not in result.prompt
        assert "skills" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_skills_section_ordering(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            workspace_name="my-team",
            user_message="hello",
            user_skills=[{"name": "Skill A", "description": "Desc A"}],
            memory_entries=[{"source_type": "note", "content": "Some memory"}],
        )
        result = await assemble_system_prompt(config)

        workspace_pos = result.prompt.find("Workspace Context")
        skills_pos = result.prompt.find("Your Skills")
        memory_pos = result.prompt.find("Workspace Memory Context")

        # Skills must appear after workspace context and before session/memory
        assert workspace_pos < skills_pos < memory_pos


class TestFullAssembly:
    """Tests for backward-compatible full assembly."""

    @pytest.mark.asyncio
    async def test_all_layers_loaded(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            workspace_name="pilot-team",
            project_names=["pilot-space"],
            user_message="create an issue for the auth bug",
            has_note_context=True,
            memory_entries=[{"source_type": "note", "content": "Auth spec"}],
            pending_approvals=2,
            budget_warning="80% used",
            conversation_summary="Prior discussion about auth.",
            user_skills=[
                {"name": "Python Expert", "description": "Advanced Python development"},
            ],
        )
        result = await assemble_system_prompt(config)

        assert "PilotSpace AI" in result.prompt
        assert "Safety reasoning" in result.prompt
        assert "Your User's Role" in result.prompt
        assert "Workspace: pilot-team" in result.prompt
        assert "Operational Rules" in result.prompt
        assert "Workspace Memory Context" in result.prompt
        assert "Conversation Summary" in result.prompt
        assert "pending approval" in result.prompt
        assert "Budget: 80% used" in result.prompt
        assert "Your Skills" in result.prompt

        assert "identity" in result.layers_loaded
        assert "safety_tools_style" in result.layers_loaded
        assert "role:developer" in result.layers_loaded
        assert "workspace" in result.layers_loaded
        assert "session" in result.layers_loaded
        assert "skills" in result.layers_loaded
        assert len(result.rules_loaded) > 0
        assert result.estimated_tokens > 0


class TestMentionContextLayer:
    """Tests for mention context layer injection (Phase 04)."""

    @pytest.mark.asyncio
    async def test_with_mention_context_includes_resolution_rule(self) -> None:
        """FR-04-1: Agent receives entity resolution instruction when @[ tokens present."""
        config = PromptLayerConfig(
            user_message="tell me about @[Note:abc-123]",
            has_mention_context=True,
        )
        result = await assemble_system_prompt(config)
        assert "Entity Reference Resolution" in result.prompt
        assert "mention_resolution" in result.layers_loaded

    @pytest.mark.asyncio
    async def test_without_mention_context_skips_rule(self) -> None:
        """FR-04-1 inverse: No mention instruction when no @[ tokens."""
        config = PromptLayerConfig(
            user_message="tell me about this project",
            has_mention_context=False,
        )
        result = await assemble_system_prompt(config)
        assert "Entity Reference Resolution" not in result.prompt
        assert "mention_resolution" not in result.layers_loaded

    @pytest.mark.asyncio
    async def test_mention_context_includes_mcp_tool_names(self) -> None:
        """FR-04-1/FR-04-2: Prompt references correct MCP tools per entity type."""
        config = PromptLayerConfig(
            user_message="summarize @[Project:ghi-789]",
            has_mention_context=True,
        )
        result = await assemble_system_prompt(config)
        assert "mcp__pilot-notes-query__search_notes" in result.prompt
        assert "mcp__pilot-issues__get_issue" in result.prompt
        assert "mcp__pilot-projects__get_project_context" in result.prompt

    @pytest.mark.asyncio
    async def test_mention_context_includes_graceful_skip_language(self) -> None:
        """FR-04-3: Prompt instructs agent to skip inaccessible entities gracefully."""
        config = PromptLayerConfig(
            user_message="check @[Issue:def-456]",
            has_mention_context=True,
        )
        result = await assemble_system_prompt(config)
        prompt_lower = result.prompt.lower()
        # Must contain skip/continue language for inaccessible entities
        assert "skip" in prompt_lower, "Prompt must instruct agent to skip inaccessible entities"
        assert "continue" in prompt_lower, "Prompt must instruct agent to continue after skipping"
        # Should mention the error condition
        assert any(term in prompt_lower for term in ["not found", "inaccessible", "error"]), (
            "Prompt must reference entity-not-found or inaccessible scenario"
        )

    @pytest.mark.asyncio
    async def test_standing_instruction_always_present(self) -> None:
        """FR-04-4: Standing 'never expose raw tokens' instruction is always present."""
        config = PromptLayerConfig(user_message="hello", has_mention_context=False)
        result = await assemble_system_prompt(config)
        assert "Never expose raw" in result.prompt
