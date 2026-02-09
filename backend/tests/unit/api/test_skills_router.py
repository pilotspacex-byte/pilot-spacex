"""Unit tests for skill discovery and GET /api/v1/skills endpoint."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pilot_space.ai.skills.skill_discovery import SkillInfo, discover_skills
from pilot_space.api.v1.routers.skills import SkillListResponse, _to_response

# ---------------------------------------------------------------------------
# discover_skills tests
# ---------------------------------------------------------------------------


class TestDiscoverSkills:
    """Tests for the filesystem-based skill discovery."""

    def test_discovers_user_invocable_skills(self, tmp_path: Path) -> None:
        """Skills without a trigger (or with trigger != scheduled/intent_detection) are returned."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                name: my-skill
                description: A test skill
                ---

                # My Skill
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 1
        assert result[0].name == "my-skill"
        assert result[0].description == "A test skill"

    def test_filters_scheduled_skills(self, tmp_path: Path) -> None:
        """Skills with trigger: scheduled are excluded."""
        skill_dir = tmp_path / "cron-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                name: cron-skill
                description: A scheduled skill
                trigger: scheduled
                ---

                # Cron Skill
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 0

    def test_filters_intent_detection_skills(self, tmp_path: Path) -> None:
        """Skills with trigger: intent_detection are excluded."""
        skill_dir = tmp_path / "auto-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                name: auto-skill
                description: An auto-detected skill
                trigger: intent_detection
                ---

                # Auto Skill
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 0

    def test_missing_frontmatter_skipped(self, tmp_path: Path) -> None:
        """SKILL.md without frontmatter is gracefully skipped."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No frontmatter here", encoding="utf-8")

        result = discover_skills(tmp_path)

        assert len(result) == 0

    def test_non_existent_directory_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty list without error."""
        result = discover_skills(tmp_path / "does-not-exist")

        assert result == []

    def test_merges_ui_metadata_for_known_skills(self, tmp_path: Path) -> None:
        """Known skills get category/icon/examples from skill_metadata."""
        skill_dir = tmp_path / "extract-issues"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                name: extract-issues
                description: Extract potential issues from note content
                ---

                # Extract Issues
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 1
        skill = result[0]
        assert skill.category == "issues"
        assert skill.icon == "ListTodo"
        assert len(skill.examples) > 0

    def test_unknown_skill_gets_defaults(self, tmp_path: Path) -> None:
        """Unknown skills get default category/icon/examples."""
        skill_dir = tmp_path / "brand-new-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                name: brand-new-skill
                description: A brand new skill
                ---

                # Brand New
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 1
        skill = result[0]
        assert skill.category == "general"
        assert skill.icon == "Sparkles"
        assert skill.examples == []

    def test_discovers_multiple_skills_sorted(self, tmp_path: Path) -> None:
        """Multiple skills are returned sorted by directory name."""
        for name in ["zzz-skill", "aaa-skill"]:
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {name}\n---\n# {name}\n",
                encoding="utf-8",
            )

        result = discover_skills(tmp_path)

        assert len(result) == 2
        assert result[0].name == "aaa-skill"
        assert result[1].name == "zzz-skill"

    def test_name_fallback_to_directory_name(self, tmp_path: Path) -> None:
        """When name is missing from frontmatter, directory name is used."""
        skill_dir = tmp_path / "dir-name-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            dedent("""\
                ---
                description: No name field
                ---

                # Skill
            """),
            encoding="utf-8",
        )

        result = discover_skills(tmp_path)

        assert len(result) == 1
        assert result[0].name == "dir-name-skill"


# ---------------------------------------------------------------------------
# _to_response / SkillListResponse tests
# ---------------------------------------------------------------------------


class TestSkillResponse:
    """Tests for response serialization."""

    def test_to_response_maps_all_fields(self) -> None:
        info = SkillInfo(
            name="test-skill",
            description="Test",
            category="issues",
            icon="ListTodo",
            examples=["example 1"],
        )
        resp = _to_response(info)

        assert resp.name == "test-skill"
        assert resp.description == "Test"
        assert resp.category == "issues"
        assert resp.icon == "ListTodo"
        assert resp.examples == ["example 1"]

    def test_skill_list_response_serialization(self) -> None:
        info = SkillInfo(name="s1", description="d1", category="c1", icon="i1", examples=[])
        resp = SkillListResponse(skills=[_to_response(info)])
        data = resp.model_dump()

        assert len(data["skills"]) == 1
        assert data["skills"][0]["name"] == "s1"


# ---------------------------------------------------------------------------
# Integration test with actual templates directory
# ---------------------------------------------------------------------------


class TestActualSkillsDirectory:
    """Integration test against the real skills templates directory."""

    def test_discovers_real_skills(self) -> None:
        """Verify discover_skills works with actual templates/skills/ directory."""
        skills_dir = (
            Path(__file__).resolve().parents[3]
            / "src"
            / "pilot_space"
            / "ai"
            / "templates"
            / "skills"
        )
        if not skills_dir.is_dir():
            pytest.skip("Skills directory not found in expected location")

        result = discover_skills(skills_dir)

        # We know there are 11 skill dirs, but 2 are non-invocable
        # (generate-digest: scheduled, create-note-from-chat: intent_detection)
        assert len(result) >= 8
        names = {s.name for s in result}
        assert "extract-issues" in names
        assert "improve-writing" in names
        assert "summarize" in names
        # Non-invocable should be filtered out
        assert "generate-digest" not in names
        assert "create-note-from-chat" not in names
