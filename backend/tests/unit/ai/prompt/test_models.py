"""Unit tests for prompt assembly models."""

from __future__ import annotations

from pilot_space.ai.prompt.models import (
    AssembledPrompt,
    PromptLayerConfig,
)


class TestPromptLayerConfig:
    """Tests for PromptLayerConfig model."""

    def test_minimal_config(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.base_prompt == ""
        assert cfg.role_type is None
        assert cfg.workspace_name is None
        assert cfg.project_names is None
        assert cfg.user_message == ""
        assert cfg.has_mention_context is False

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
            has_mention_context=True,
            user_skills=[{"name": "Code Review", "description": "Reviews PRs"}],
            feature_toggles={"memory": True, "skills": False},
        )
        assert cfg.role_type == "developer"
        assert cfg.project_names == ["proj-a", "proj-b"]
        assert cfg.has_mention_context is True
        assert len(cfg.user_skills) == 1
        assert cfg.feature_toggles["memory"] is True

    def test_base_prompt_defaults_to_empty(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.base_prompt == ""

    def test_user_skills_default_factory(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.user_skills == []

    def test_feature_toggles_default_factory(self) -> None:
        cfg = PromptLayerConfig()
        assert cfg.feature_toggles == {}


class TestAssembledPrompt:
    """Tests for AssembledPrompt model."""

    def test_defaults(self) -> None:
        ap = AssembledPrompt(prompt="hello")
        assert ap.prompt == "hello"
        assert ap.layers_loaded == []
        assert ap.estimated_tokens == 0
        assert ap.static_prefix == ""
        assert ap.dynamic_suffix == ""

    def test_with_metadata(self) -> None:
        ap = AssembledPrompt(
            prompt="full prompt",
            layers_loaded=["identity", "safety"],
            estimated_tokens=500,
            static_prefix="static content",
            dynamic_suffix="dynamic content",
        )
        assert len(ap.layers_loaded) == 2
        assert ap.estimated_tokens == 500
        assert ap.static_prefix == "static content"
        assert ap.dynamic_suffix == "dynamic content"

    def test_combined_prompt_field(self) -> None:
        ap = AssembledPrompt(
            prompt="static\n\ndynamic",
            static_prefix="static",
            dynamic_suffix="dynamic",
        )
        assert ap.prompt == "static\n\ndynamic"
