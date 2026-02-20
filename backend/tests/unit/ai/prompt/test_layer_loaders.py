"""Unit tests for prompt layer loaders."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pilot_space.ai.prompt.layer_loaders import (
    _PROMPT_LAYERS_DIR,
    _ROLE_TEMPLATES_DIR,
    _RULES_DIR,
    clear_caches,
    load_role_template,
    load_rule_file,
    load_static_layer,
)


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Clear caches before each test."""
    clear_caches()


class TestLoadStaticLayer:
    """Tests for load_static_layer."""

    @pytest.mark.asyncio
    async def test_loads_existing_file(self) -> None:
        content = await load_static_layer("layer1_identity.md")
        assert "PilotSpace AI" in content
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_caches_result(self) -> None:
        first = await load_static_layer("layer1_identity.md")
        second = await load_static_layer("layer1_identity.md")
        assert first is second  # same object from cache

    @pytest.mark.asyncio
    async def test_missing_file_returns_empty(self) -> None:
        result = await load_static_layer("nonexistent.md")
        assert result == ""

    @pytest.mark.asyncio
    async def test_layer2_exists(self) -> None:
        content = await load_static_layer("layer2_safety_tools_style.md")
        assert "Safety reasoning" in content


class TestLoadRoleTemplate:
    """Tests for load_role_template."""

    @pytest.mark.asyncio
    async def test_loads_developer_template(self) -> None:
        content = await load_role_template("developer")
        assert content is not None
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_strips_yaml_frontmatter(self) -> None:
        content = await load_role_template("developer")
        assert content is not None
        assert not content.startswith("---")

    @pytest.mark.asyncio
    async def test_caches_result(self) -> None:
        first = await load_role_template("developer")
        second = await load_role_template("developer")
        assert first is second

    @pytest.mark.asyncio
    async def test_missing_role_returns_none(self) -> None:
        result = await load_role_template("nonexistent_role")
        assert result is None


class TestLoadRuleFile:
    """Tests for load_rule_file."""

    @pytest.mark.asyncio
    async def test_loads_existing_rule(self) -> None:
        content = await load_rule_file("issues.md")
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_caches_result(self) -> None:
        first = await load_rule_file("issues.md")
        second = await load_rule_file("issues.md")
        assert first is second

    @pytest.mark.asyncio
    async def test_missing_rule_returns_empty(self) -> None:
        result = await load_rule_file("nonexistent_rule.md")
        assert result == ""

    @pytest.mark.asyncio
    async def test_truncation_at_4000_chars(self, tmp_path: Path) -> None:
        """Verify files exceeding 4000 chars are truncated."""
        long_content = "x" * 5000
        rule_file = tmp_path / "long_rule.md"
        rule_file.write_text(long_content)

        with patch("pilot_space.ai.prompt.layer_loaders._RULES_DIR", tmp_path):
            clear_caches()
            result = await load_rule_file("long_rule.md")

        assert len(result) < 5000
        assert result.endswith("... (truncated)")
        # 4000 chars + "\n... (truncated)" = 4016 chars
        assert len(result) == 4000 + len("\n... (truncated)")


class TestClearCaches:
    """Tests for clear_caches."""

    @pytest.mark.asyncio
    async def test_clears_all_caches(self) -> None:
        await load_static_layer("layer1_identity.md")
        await load_rule_file("issues.md")

        clear_caches()

        # After clearing, next load should hit disk again
        # We verify by checking the function still works (no stale state)
        content = await load_static_layer("layer1_identity.md")
        assert "PilotSpace AI" in content


class TestPathConstants:
    """Tests for path constant correctness."""

    def test_prompt_layers_dir_exists(self) -> None:
        assert _PROMPT_LAYERS_DIR.is_dir()

    def test_role_templates_dir_exists(self) -> None:
        assert _ROLE_TEMPLATES_DIR.is_dir()

    def test_rules_dir_exists(self) -> None:
        assert _RULES_DIR.is_dir()
