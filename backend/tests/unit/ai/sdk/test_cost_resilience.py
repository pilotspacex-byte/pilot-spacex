"""Tests for SDK cost & resilience controls (Phase A: G1-G4).

Tests for:
- max_budget_usd propagation (G1)
- fallback_model configuration (G2)
- max_turns configuration (G3)
- output_format wiring (G4)
- ModelTier default properties
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

if TYPE_CHECKING:
    import pytest

from pilot_space.ai.sdk.sandbox_config import (
    ModelTier,
    SandboxSettings,
    SDKConfiguration,
    _resolve_tier,
    configure_sdk_for_space,
    resolve_model,
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
# G1: max_budget_usd
# ========================================


class TestMaxBudgetUsd:
    """Tests for per-request cost ceiling (G1)."""

    def test_max_budget_usd_included_in_sdk_params(self) -> None:
        config = _make_sdk_config(max_budget_usd=0.75)
        params = config.to_sdk_params()
        assert params["max_budget_usd"] == 0.75

    def test_max_budget_usd_omitted_when_none(self) -> None:
        config = _make_sdk_config(max_budget_usd=None)
        params = config.to_sdk_params()
        assert "max_budget_usd" not in params

    def test_sonnet_tier_default_budget(self) -> None:
        assert ModelTier.SONNET.default_budget_usd == 0.50

    def test_opus_tier_default_budget(self) -> None:
        assert ModelTier.OPUS.default_budget_usd == 2.00

    def test_haiku_tier_default_budget(self) -> None:
        assert ModelTier.HAIKU.default_budget_usd == 0.10

    def test_configure_sdk_applies_tier_default_budget(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.OPUS)
        assert config.max_budget_usd == 2.00

    def test_configure_sdk_explicit_budget_overrides_tier(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.OPUS, max_budget_usd=5.00)
        assert config.max_budget_usd == 5.00

    def test_configure_sdk_custom_model_no_default_budget(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model="custom-model-id")
        assert config.max_budget_usd is None


# ========================================
# G2: fallback_model
# ========================================


class TestFallbackModel:
    """Tests for automatic model fallback (G2)."""

    def test_fallback_model_included_in_sdk_params(self) -> None:
        config = _make_sdk_config(fallback_model="claude-haiku-4-5-20251001")
        params = config.to_sdk_params()
        assert params["fallback_model"] == "claude-haiku-4-5-20251001"

    def test_fallback_model_omitted_when_none(self) -> None:
        config = _make_sdk_config(fallback_model=None)
        params = config.to_sdk_params()
        assert "fallback_model" not in params

    def test_opus_fallback_tier_is_sonnet(self) -> None:
        assert ModelTier.OPUS.fallback_tier == ModelTier.SONNET

    def test_sonnet_fallback_tier_is_haiku(self) -> None:
        assert ModelTier.SONNET.fallback_tier == ModelTier.HAIKU

    def test_haiku_fallback_tier_is_none(self) -> None:
        assert ModelTier.HAIKU.fallback_tier is None

    def test_configure_sdk_sets_fallback_from_tier(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.OPUS)
        # Opus falls back to Sonnet's model_id
        assert config.fallback_model == ModelTier.SONNET.model_id

    def test_configure_sdk_haiku_has_no_fallback(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.HAIKU)
        assert config.fallback_model is None

    def test_configure_sdk_custom_model_no_fallback(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model="custom-model-id")
        assert config.fallback_model is None


# ========================================
# G3: max_turns
# ========================================


class TestMaxTurns:
    """Tests for conversation turn limits (G3)."""

    def test_max_turns_included_in_sdk_params(self) -> None:
        config = _make_sdk_config(max_turns=30)
        params = config.to_sdk_params()
        assert params["max_turns"] == 30

    def test_max_turns_omitted_when_none(self) -> None:
        config = _make_sdk_config(max_turns=None)
        params = config.to_sdk_params()
        assert "max_turns" not in params

    def test_sonnet_default_max_turns(self) -> None:
        assert ModelTier.SONNET.default_max_turns == 25

    def test_opus_default_max_turns(self) -> None:
        assert ModelTier.OPUS.default_max_turns == 15

    def test_haiku_default_max_turns(self) -> None:
        assert ModelTier.HAIKU.default_max_turns == 50

    def test_configure_sdk_applies_tier_default_turns(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.SONNET)
        assert config.max_turns == 25

    def test_configure_sdk_explicit_turns_overrides_tier(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.SONNET, max_turns=100)
        assert config.max_turns == 100


# ========================================
# G4: output_format
# ========================================


class TestOutputFormat:
    """Tests for structured output enforcement (G4)."""

    def test_output_format_included_in_sdk_params(self) -> None:
        schema = {"type": "object", "properties": {"title": {"type": "string"}}}
        config = _make_sdk_config(output_format=schema)
        params = config.to_sdk_params()
        assert params["output_format"] == schema

    def test_output_format_omitted_when_none(self) -> None:
        config = _make_sdk_config(output_format=None)
        params = config.to_sdk_params()
        assert "output_format" not in params

    def test_configure_sdk_passes_output_format(self) -> None:
        ctx = _make_space_context()
        schema = {"type": "object", "properties": {"issues": {"type": "array"}}}
        config = configure_sdk_for_space(ctx, output_format=schema)
        assert config.output_format == schema


# ========================================
# ModelTier: Haiku + resolve helpers
# ========================================


class TestModelTierHaiku:
    """Tests for Haiku tier (new in this phase)."""

    def test_haiku_model_id_default(self) -> None:
        assert ModelTier.HAIKU.model_id == "claude-haiku-4-5-20251001"

    def test_haiku_model_id_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PILOTSPACE_MODEL_HAIKU_DEFAULT", "claude-haiku-custom")
        assert ModelTier.HAIKU.model_id == "claude-haiku-custom"

    def test_resolve_model_haiku_string(self) -> None:
        assert resolve_model("haiku") == ModelTier.HAIKU.model_id

    def test_resolve_model_haiku_enum(self) -> None:
        assert resolve_model(ModelTier.HAIKU) == ModelTier.HAIKU.model_id


class TestResolveTier:
    """Tests for _resolve_tier helper."""

    def test_resolve_tier_from_enum(self) -> None:
        assert _resolve_tier(ModelTier.SONNET) == ModelTier.SONNET

    def test_resolve_tier_from_string(self) -> None:
        assert _resolve_tier("opus") == ModelTier.OPUS

    def test_resolve_tier_from_haiku_string(self) -> None:
        assert _resolve_tier("haiku") == ModelTier.HAIKU

    def test_resolve_tier_unknown_returns_none(self) -> None:
        assert _resolve_tier("custom-model-id") is None

    def test_resolve_tier_case_insensitive(self) -> None:
        assert _resolve_tier("SONNET") == ModelTier.SONNET


# ========================================
# Integration: Full config round-trip
# ========================================


class TestFullConfigRoundTrip:
    """Integration tests verifying all Phase A params flow through."""

    def test_all_cost_resilience_params_in_sdk_params(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            model=ModelTier.OPUS,
            max_budget_usd=3.00,
            max_turns=10,
            output_format={"type": "object"},
        )
        params = config.to_sdk_params()

        assert params["max_budget_usd"] == 3.00
        assert params["max_turns"] == 10
        assert params["output_format"] == {"type": "object"}
        assert params["fallback_model"] == ModelTier.SONNET.model_id
        assert params["model"] == ModelTier.OPUS.model_id

    def test_sonnet_tier_defaults_all_present(self) -> None:
        ctx = _make_space_context()
        config = configure_sdk_for_space(ctx, model=ModelTier.SONNET)

        assert config.max_budget_usd == 0.50
        assert config.fallback_model == ModelTier.HAIKU.model_id
        assert config.max_turns == 25
        assert config.output_format is None

    def test_existing_params_unchanged(self) -> None:
        """Verify Phase A additions don't break existing params."""
        ctx = _make_space_context()
        config = configure_sdk_for_space(
            ctx,
            model=ModelTier.SONNET,
            include_partial_messages=True,
            effort="high",
        )
        params = config.to_sdk_params()

        assert params["include_partial_messages"] is True
        assert params["effort"] == "high"
        assert params["permission_mode"] == "default"
        assert params["setting_sources"] == ["project"]
