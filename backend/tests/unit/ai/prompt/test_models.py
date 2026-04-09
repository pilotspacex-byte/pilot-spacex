"""Unit tests for prompt assembly models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pilot_space.ai.prompt.models import (
    AssembledPrompt,
    IntentClassification,
    PromptLayerConfig,
    UserIntent,
)


class TestUserIntent:
    """Tests for UserIntent enum."""

    def test_all_intents_exist(self) -> None:
        expected = {
            "note_writing",
            "note_reading",
            "issue_mgmt",
            "pm_blocks",
            "project_mgmt",
            "comment",
            "general",
        }
        assert {i.value for i in UserIntent} == expected

    def test_intent_count(self) -> None:
        assert len(UserIntent) == 7

    def test_intent_is_string(self) -> None:
        assert UserIntent.NOTE_WRITING == "note_writing"


class TestIntentClassification:
    """Tests for IntentClassification model."""

    def test_defaults(self) -> None:
        ic = IntentClassification(primary=UserIntent.GENERAL)
        assert ic.primary == UserIntent.GENERAL
        assert ic.secondary is None
        assert ic.confidence == 1.0

    def test_with_secondary(self) -> None:
        ic = IntentClassification(
            primary=UserIntent.NOTE_WRITING,
            secondary=UserIntent.ISSUE_MGMT,
            confidence=0.85,
        )
        assert ic.secondary == UserIntent.ISSUE_MGMT
        assert ic.confidence == 0.85

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            IntentClassification(primary=UserIntent.GENERAL, confidence=1.5)
        with pytest.raises(ValidationError):
            IntentClassification(primary=UserIntent.GENERAL, confidence=-0.1)


class TestPromptLayerConfig:
    """Tests for PromptLayerConfig model."""

    def test_minimal_config(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.base_prompt == ""
        assert cfg.role_type is None
        assert cfg.workspace_name is None
        assert cfg.project_names is None
        assert cfg.user_message == ""
        assert cfg.has_note_context is False
        assert cfg.has_mention_context is False
        assert cfg.memory_entries == []
        assert cfg.pending_approvals == 0
        assert cfg.budget_warning is None
        assert cfg.conversation_summary is None

    def test_has_mention_context_explicit_true(self) -> None:
        cfg = PromptLayerConfig(has_mention_context=True)
        assert cfg.has_mention_context is True

    def test_full_config(self) -> None:
        cfg = PromptLayerConfig(
            base_prompt="base",
            role_type="developer",
            workspace_name="my-ws",
            project_names=["proj-a", "proj-b"],
            user_message="hello",
            has_note_context=True,
            memory_entries=[{"key": "val"}],
            pending_approvals=3,
            budget_warning="90% used",
            conversation_summary="discussed issues",
        )
        assert cfg.role_type == "developer"
        assert cfg.project_names == ["proj-a", "proj-b"]
        assert cfg.pending_approvals == 3

    def test_base_prompt_defaults_to_empty(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.base_prompt == ""


class TestAssembledPrompt:
    """Tests for AssembledPrompt model."""

    def test_defaults(self) -> None:
        ap = AssembledPrompt(prompt="hello")
        assert ap.prompt == "hello"
        assert ap.layers_loaded == []
        assert ap.rules_loaded == []
        assert ap.estimated_tokens == 0

    def test_with_metadata(self) -> None:
        ap = AssembledPrompt(
            prompt="full prompt",
            layers_loaded=["identity", "safety"],
            rules_loaded=["issues.md"],
            estimated_tokens=500,
        )
        assert len(ap.layers_loaded) == 2
        assert ap.estimated_tokens == 500
