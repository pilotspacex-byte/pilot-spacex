"""Unit tests for the static/dynamic prompt assembler."""

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
    """Tests for workspace context (dynamic suffix)."""

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


class TestSkillsLayer:
    """Tests for skills layer (dynamic suffix)."""

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
        )
        result = await assemble_system_prompt(config)

        workspace_pos = result.prompt.find("Workspace Context")
        skills_pos = result.prompt.find("Your Skills")

        # Skills must appear after workspace context in dynamic suffix
        assert workspace_pos < skills_pos


class TestFullAssembly:
    """Tests for full assembly with all dynamic layers."""

    @pytest.mark.asyncio
    async def test_all_layers_loaded(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            workspace_name="pilot-team",
            project_names=["pilot-space"],
            user_message="create an issue for the auth bug",
            user_skills=[
                {"name": "Python Expert", "description": "Advanced Python development"},
            ],
        )
        result = await assemble_system_prompt(config)

        assert "PilotSpace AI" in result.prompt
        assert "Safety reasoning" in result.prompt
        assert "Your User's Role" in result.prompt
        assert "Workspace: pilot-team" in result.prompt
        assert "Your Skills" in result.prompt

        assert result.static_prefix != ""
        assert result.dynamic_suffix != ""
        assert result.prompt.startswith(result.static_prefix)

        assert "identity" in result.layers_loaded
        assert "safety_tools_style" in result.layers_loaded
        assert "role:developer" in result.layers_loaded
        assert "workspace" in result.layers_loaded
        assert "skills" in result.layers_loaded
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


class TestStaticDynamicSplit:
    """Tests for static/dynamic prompt boundary (PROM-01)."""

    @pytest.mark.asyncio
    async def test_static_prefix_contains_identity_and_safety(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert "PilotSpace AI" in result.static_prefix
        assert "Safety reasoning" in result.static_prefix

    @pytest.mark.asyncio
    async def test_static_prefix_contains_role(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback", role_type="developer", user_message="hello"
        )
        result = await assemble_system_prompt(config)
        assert "Your User's Role" in result.static_prefix

    @pytest.mark.asyncio
    async def test_dynamic_suffix_contains_workspace(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            workspace_name="my-team",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)
        assert "Workspace: my-team" in result.dynamic_suffix
        assert "Workspace: my-team" not in result.static_prefix

    @pytest.mark.asyncio
    async def test_static_prefix_identical_across_requests(self) -> None:
        """PROM-01: Static prefix must be identical for same workspace+role."""
        config1 = PromptLayerConfig(
            role_type="developer",
            workspace_name="team-a",
            user_message="write a note",
            user_skills=[{"name": "Python", "description": "dev"}],
        )
        config2 = PromptLayerConfig(
            role_type="developer",
            workspace_name="team-b",
            user_message="create an issue",
            user_skills=[],
        )
        result1 = await assemble_system_prompt(config1)
        result2 = await assemble_system_prompt(config2)
        # Static prefix depends only on role_type, not workspace or message
        assert result1.static_prefix == result2.static_prefix

    @pytest.mark.asyncio
    async def test_combined_prompt_is_static_plus_dynamic(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            workspace_name="my-team",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)
        expected = f"{result.static_prefix}\n\n{result.dynamic_suffix}"
        assert result.prompt == expected

    @pytest.mark.asyncio
    async def test_no_dynamic_content_prompt_equals_static(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert result.dynamic_suffix == ""
        assert result.prompt == result.static_prefix


class TestLayerRemoval:
    """Tests that Layer 5 and Layer 6 content is no longer assembled (PROM-02)."""

    @pytest.mark.asyncio
    async def test_no_operational_rules_in_prompt(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="create an issue for the login bug",
        )
        result = await assemble_system_prompt(config)
        assert "Operational Rules" not in result.prompt

    @pytest.mark.asyncio
    async def test_no_rule_domains_summary(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert "Available Rule Domains" not in result.prompt

    @pytest.mark.asyncio
    async def test_no_session_layer(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert "session" not in result.layers_loaded
        assert "Workspace Memory Context" not in result.prompt
        assert "Conversation Summary" not in result.prompt
        assert "pending approval" not in result.prompt

    @pytest.mark.asyncio
    async def test_no_rules_loaded_attribute(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert not hasattr(result, "rules_loaded")


class TestEmptySectionSkipping:
    """Tests that empty layers produce no output (PROM-03)."""

    @pytest.mark.asyncio
    async def test_no_skills_no_section(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback", user_message="hello", user_skills=[]
        )
        result = await assemble_system_prompt(config)
        assert "Your Skills" not in result.prompt
        assert "skills" not in result.layers_loaded

    @pytest.mark.asyncio
    async def test_no_disabled_features_no_section(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback", user_message="hello", feature_toggles={}
        )
        result = await assemble_system_prompt(config)
        assert "Disabled Workspace Features" not in result.prompt
        assert "disabled_features" not in result.layers_loaded

    @pytest.mark.asyncio
    async def test_all_features_enabled_no_section(self) -> None:
        config = PromptLayerConfig(
            base_prompt="fallback",
            user_message="hello",
            feature_toggles={"ai_chat": True, "memory": True},
        )
        result = await assemble_system_prompt(config)
        assert "Disabled Workspace Features" not in result.prompt

    @pytest.mark.asyncio
    async def test_no_role_no_section(self) -> None:
        config = PromptLayerConfig(base_prompt="fallback", user_message="hello")
        result = await assemble_system_prompt(config)
        assert "Your User's Role" not in result.prompt


class TestTokenReduction:
    """Tests that token count meets the 40-70% reduction target (PROM-04)."""

    @pytest.mark.asyncio
    async def test_typical_request_under_2500_tokens(self) -> None:
        """Pre-milestone typical was ~5,337 tokens. Target: ~1,850 (65% reduction)."""
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            workspace_name="pilot-team",
            user_message="write a note about API design",
        )
        result = await assemble_system_prompt(config)
        # Must be well under the pre-milestone 5,337 tokens
        assert result.estimated_tokens < 2500, (
            f"Typical request should be under 2500 tokens, got {result.estimated_tokens}"
        )

    @pytest.mark.asyncio
    async def test_worst_case_under_3000_tokens(self) -> None:
        """Pre-milestone worst case was ~8,137 tokens. Target: ~2,506 (69% reduction)."""
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            workspace_name="pilot-team",
            project_names=["proj-a", "proj-b"],
            user_message="check @[Issue:abc-123]",
            has_mention_context=True,
            user_skills=[
                {"name": "Python Expert", "description": "Advanced Python development"},
                {"name": "TDD Coach", "description": "Test-driven development practices"},
            ],
            feature_toggles={"legacy_feature": False},
        )
        result = await assemble_system_prompt(config)
        assert result.estimated_tokens < 3000, (
            f"Worst case should be under 3000 tokens, got {result.estimated_tokens}"
        )

    @pytest.mark.asyncio
    async def test_reduction_percentage_from_baseline(self) -> None:
        """Verify 40%+ reduction from pre-milestone baseline analytically."""
        config = PromptLayerConfig(
            base_prompt="fallback",
            role_type="developer",
            workspace_name="pilot-team",
            user_message="hello",
        )
        result = await assemble_system_prompt(config)
        pre_milestone_typical = 5337  # Pre-milestone baseline from RESEARCH.md
        reduction_pct = (1 - result.estimated_tokens / pre_milestone_typical) * 100
        assert reduction_pct >= 40, (
            f"Expected 40%+ reduction, got {reduction_pct:.1f}% "
            f"({result.estimated_tokens} vs baseline {pre_milestone_typical})"
        )
