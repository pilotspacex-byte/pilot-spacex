"""Tests for SDK advanced features (Phase C: G5-G7).

Tests for:
- enable_file_checkpointing (G5)
- betas configuration (G6)
- system_prompt append mode with cache_control (G7)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from pilot_space.ai.sdk.sandbox_config import (
    ModelTier,
    SandboxSettings,
    SDKConfiguration,
    configure_sdk_for_space,
)

# ========================================
# Helpers
# ========================================


def _make_sdk_config(**overrides: Any) -> SDKConfiguration:
    """Create SDKConfiguration with sensible test defaults."""
    defaults: dict[str, Any] = {
        "cwd": "/tmp/test",
        "setting_sources": ["project"],
        "sandbox": SandboxSettings(),
        "permission_mode": "default",
        "env": {},
        "allowed_tools": ["Read", "Write"],
    }
    defaults.update(overrides)
    return SDKConfiguration(**defaults)


def _make_space_context() -> MagicMock:
    """Create mock SpaceContext for configure_sdk_for_space()."""
    ctx = MagicMock()
    ctx.path = Path("/sandbox/user1/workspace1")
    ctx.to_sdk_env.return_value = {"PILOTSPACE_USER_ID": "user1"}
    ctx.hooks_file = Path("/sandbox/user1/workspace1/.claude/hooks.json")
    return ctx


# ========================================
# G5: enable_file_checkpointing
# ========================================


class TestFileCheckpointing:
    """Tests for file checkpointing configuration."""

    def test_checkpointing_included_when_enabled(self) -> None:
        config = _make_sdk_config(enable_file_checkpointing=True)
        params = config.to_sdk_params()
        assert params["enable_file_checkpointing"] is True

    def test_checkpointing_omitted_when_disabled(self) -> None:
        config = _make_sdk_config(enable_file_checkpointing=False)
        params = config.to_sdk_params()
        assert "enable_file_checkpointing" not in params

    def test_checkpointing_default_false(self) -> None:
        config = _make_sdk_config()
        assert config.enable_file_checkpointing is False

    def test_configure_sdk_passes_checkpointing(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            enable_file_checkpointing=True,
        )
        assert config.enable_file_checkpointing is True
        params = config.to_sdk_params()
        assert params["enable_file_checkpointing"] is True

    def test_configure_sdk_default_no_checkpointing(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx)
        assert config.enable_file_checkpointing is False


# ========================================
# G6: betas
# ========================================


class TestBetasConfiguration:
    """Tests for SDK beta features configuration."""

    def test_betas_included_when_set(self) -> None:
        config = _make_sdk_config(betas=["context-1m-2025-08-07"])
        params = config.to_sdk_params()
        assert params["betas"] == ["context-1m-2025-08-07"]

    def test_betas_omitted_when_empty(self) -> None:
        config = _make_sdk_config(betas=[])
        params = config.to_sdk_params()
        assert "betas" not in params

    def test_betas_default_empty(self) -> None:
        config = _make_sdk_config()
        assert config.betas == []

    def test_multiple_betas(self) -> None:
        betas = ["context-1m-2025-08-07", "another-beta"]
        config = _make_sdk_config(betas=betas)
        params = config.to_sdk_params()
        assert params["betas"] == betas

    def test_configure_sdk_passes_betas(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            betas=["context-1m-2025-08-07"],
        )
        assert config.betas == ["context-1m-2025-08-07"]

    def test_configure_sdk_default_no_betas(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx)
        assert config.betas == []

    def test_configure_sdk_none_betas_becomes_empty(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, betas=None)
        assert config.betas == []


# ========================================
# G7: system_prompt with cache_control
# ========================================


class TestSystemPromptCaching:
    """Tests for SDK-native system prompt caching."""

    def test_system_prompt_included_when_set(self) -> None:
        config = _make_sdk_config(system_prompt_base="You are a helpful assistant.")
        params = config.to_sdk_params()
        assert params["system_prompt"] == {
            "content": "You are a helpful assistant.",
            "cache_control": "ephemeral",
        }

    def test_system_prompt_omitted_when_none(self) -> None:
        config = _make_sdk_config(system_prompt_base=None)
        params = config.to_sdk_params()
        assert "system_prompt" not in params

    def test_system_prompt_default_none(self) -> None:
        config = _make_sdk_config()
        assert config.system_prompt_base is None

    def test_system_prompt_cache_control_is_ephemeral(self) -> None:
        config = _make_sdk_config(system_prompt_base="PilotSpace agent prompt")
        params = config.to_sdk_params()
        assert params["system_prompt"]["cache_control"] == "ephemeral"

    def test_configure_sdk_passes_system_prompt(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            system_prompt_base="You are PilotSpace Agent.",
        )
        assert config.system_prompt_base == "You are PilotSpace Agent."

    def test_configure_sdk_default_no_system_prompt(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx)
        assert config.system_prompt_base is None


# ========================================
# Integration: All Phase C params together
# ========================================


class TestPhaseCIntegration:
    """Integration tests for all Phase C features together."""

    def test_all_phase_c_params_in_sdk_params(self) -> None:
        config = _make_sdk_config(
            enable_file_checkpointing=True,
            betas=["context-1m-2025-08-07"],
            system_prompt_base="PilotSpace base prompt",
        )
        params = config.to_sdk_params()
        assert params["enable_file_checkpointing"] is True
        assert params["betas"] == ["context-1m-2025-08-07"]
        assert params["system_prompt"]["content"] == "PilotSpace base prompt"

    def test_phase_c_with_phase_a_params(self) -> None:
        """Verify Phase C additions don't break Phase A params."""
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            model=ModelTier.OPUS,
            enable_file_checkpointing=True,
            betas=["context-1m-2025-08-07"],
            system_prompt_base="Opus agent",
            max_budget_usd=3.0,
        )
        params = config.to_sdk_params()
        # Phase A
        assert params["max_budget_usd"] == 3.0
        assert params["fallback_model"] == ModelTier.SONNET.model_id
        assert params["max_turns"] == 15
        # Phase C
        assert params["enable_file_checkpointing"] is True
        assert params["betas"] == ["context-1m-2025-08-07"]
        assert params["system_prompt"]["content"] == "Opus agent"

    def test_existing_params_unchanged_with_phase_c(self) -> None:
        """Verify Phase C additions don't break existing params."""
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            model=ModelTier.SONNET,
            include_partial_messages=True,
            effort="high",
            enable_file_checkpointing=True,
        )
        params = config.to_sdk_params()
        assert params["include_partial_messages"] is True
        assert params["effort"] == "high"
        assert params["permission_mode"] == "default"
