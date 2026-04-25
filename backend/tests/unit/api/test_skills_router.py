"""Unit tests for skill discovery and GET /api/v1/skills endpoint."""

from __future__ import annotations

import contextlib
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pilot_space.ai.skills.skill_discovery import SkillInfo, discover_skills
from pilot_space.api.v1.routers import skills as skills_router_module
from pilot_space.api.v1.routers.skills import SkillListResponse, _to_response

if TYPE_CHECKING:
    from collections.abc import Iterator

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


# ---------------------------------------------------------------------------
# HTTP endpoint tests — list / detail / file streaming + path traversal
# ---------------------------------------------------------------------------


def _seed_skill(
    skills_root: Path,
    slug: str,
    *,
    name: str | None = None,
    description: str = "Test skill",
    body: str = "# Body\n\nContent.\n",
    trigger: str | None = None,
) -> Path:
    skill_dir = skills_root / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter_lines = [f"name: {name or slug}", f"description: {description}"]
    if trigger:
        frontmatter_lines.append(f"trigger: {trigger}")
    fm = "\n".join(frontmatter_lines)
    (skill_dir / "SKILL.md").write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    return skill_dir


@pytest.fixture
def skills_test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient with system_templates_dir overridden to a synthetic tree.

    Layout under tmp_path/templates/skills:
      skill-a/
        SKILL.md           (valid, with body "# Skill A\n")
        architecture.md    ("# Arch\n")
        subdir/nested.py   ("print('hi')\n")
        escape -> ../secret-inside-templates.md  (relative symlink targeting templates dir)
      skill-b/
        SKILL.md           (trigger: scheduled — non-invocable)
      secret-inside-templates.md   (sibling to skill-* — used by symlink test)

    Plus a peer dir outside templates (tmp_path/outside) with a secret file.
    """
    templates_dir = tmp_path / "templates"
    skills_dir = templates_dir / "skills"
    skills_dir.mkdir(parents=True)

    # Sentinel files for traversal targets.
    (skills_dir / "secret-inside-templates.md").write_text("STOLEN", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret-outside.txt").write_text("STOLEN-OUTSIDE", encoding="utf-8")

    skill_a = _seed_skill(skills_dir, "skill-a", body="# Skill A\n\nDocs.\n")
    (skill_a / "architecture.md").write_text("# Arch\n", encoding="utf-8")
    subdir = skill_a / "subdir"
    subdir.mkdir()
    (subdir / "nested.py").write_text("print('hi')\n", encoding="utf-8")
    # Symlink resolving OUTSIDE skill-a (target sits in skills/, not in skill-a/).
    # Some sandboxes disable symlink creation; the symlink test will skip then.
    with contextlib.suppress(OSError, NotImplementedError):
        (skill_a / "escape").symlink_to(Path("..") / "secret-inside-templates.md")

    _seed_skill(skills_dir, "skill-b", trigger="scheduled")

    # Override settings.
    settings = skills_router_module.get_settings()
    monkeypatch.setattr(settings, "system_templates_dir", templates_dir)

    app = FastAPI()
    app.include_router(skills_router_module.router, prefix="/api/v1")
    with TestClient(app) as client:
        yield client


class TestListEndpointPhase91Fields:
    def test_list_skills_returns_extended_fields(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills")

        assert resp.status_code == 200
        data = resp.json()
        skills = data["skills"]
        # skill-a only — skill-b is non-invocable.
        slugs = {s["slug"] for s in skills}
        assert "skill-a" in slugs
        assert "skill-b" not in slugs

        skill_a = next(s for s in skills if s["slug"] == "skill-a")
        assert skill_a["slug"] == "skill-a"
        assert "architecture.md" in skill_a["reference_files"]
        assert "subdir/nested.py" in skill_a["reference_files"]
        assert "SKILL.md" not in skill_a["reference_files"]
        assert skill_a["updated_at"] is not None  # ISO datetime string


class TestDetailEndpoint:
    def test_returns_body_and_ref_metadata(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/skill-a")

        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "skill-a"
        assert data["body"].lstrip().startswith("# Skill A")
        ref_paths = {r["path"] for r in data["reference_files"]}
        assert "architecture.md" in ref_paths
        arch = next(r for r in data["reference_files"] if r["path"] == "architecture.md")
        assert arch["size_bytes"] > 0
        assert arch["mime_type"] in {"text/markdown", "text/plain"}

    def test_unknown_slug_returns_404(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/nonexistent")
        assert resp.status_code == 404

    def test_non_invocable_slug_returns_404(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/skill-b")
        assert resp.status_code == 404


class TestFileStreamEndpoint:
    def test_serves_file_with_mime(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/skill-a/files/architecture.md")

        assert resp.status_code == 200
        assert resp.text == "# Arch\n"
        # mimetypes returns text/markdown on most platforms; accept text/plain fallback.
        assert resp.headers["content-type"].split(";")[0] in {"text/markdown", "text/plain"}

    def test_serves_nested_file(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/skill-a/files/subdir/nested.py")
        assert resp.status_code == 200
        assert "print" in resp.text

    def test_unknown_skill_returns_404(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/nope/files/anything.md")
        assert resp.status_code == 404

    def test_unknown_file_returns_404(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/skill-a/files/missing.md")
        assert resp.status_code == 404

    def test_skill_md_is_not_streamed(self, skills_test_client: TestClient) -> None:
        # SKILL.md is exposed via the detail endpoint only.
        resp = skills_test_client.get("/api/v1/skills/skill-a/files/SKILL.md")
        assert resp.status_code == 404


class TestPathTraversal:
    """T-91-01 mitigation suite — every vector MUST return non-200, non-500."""

    def test_path_traversal_dotdot(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get(
            "/api/v1/skills/skill-a/files/../secret-inside-templates.md"
        )
        # FastAPI may normalize ../ before dispatch; accept either 403 (guard
        # rejects) or 404 (route did not match). Both are SAFE.
        assert resp.status_code in {403, 404}
        assert resp.status_code != 200
        assert "STOLEN" not in resp.text

    def test_path_traversal_double_dotdot(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get(
            "/api/v1/skills/skill-a/files/../../etc/passwd"
        )
        assert resp.status_code in {403, 404}
        assert resp.status_code != 200

    def test_path_traversal_absolute_path(self, skills_test_client: TestClient) -> None:
        # Double slash → /etc/passwd as the file_path.
        resp = skills_test_client.get(
            "/api/v1/skills/skill-a/files//etc/passwd"
        )
        assert resp.status_code in {403, 404}
        assert resp.status_code != 200

    def test_path_traversal_subdir_escape(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get(
            "/api/v1/skills/skill-a/files/subdir/../../secret-inside-templates.md"
        )
        assert resp.status_code in {403, 404}
        assert "STOLEN" not in resp.text

    def test_path_traversal_url_encoded(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get(
            "/api/v1/skills/skill-a/files/%2e%2e/secret-inside-templates.md"
        )
        # FastAPI/Starlette decodes; the resolve+is_relative_to guard catches it.
        assert resp.status_code in {403, 404}
        assert "STOLEN" not in resp.text

    def test_path_traversal_symlink_outside(
        self, skills_test_client: TestClient, tmp_path: Path
    ) -> None:
        # If symlink creation failed in the fixture (sandboxed FS), skip.
        symlink = tmp_path / "templates" / "skills" / "skill-a" / "escape"
        if not symlink.is_symlink():
            pytest.skip("Symlink creation not supported in this environment")
        resp = skills_test_client.get("/api/v1/skills/skill-a/files/escape")
        assert resp.status_code in {403, 404}
        assert "STOLEN" not in resp.text

    def test_path_traversal_slug_escape(self, skills_test_client: TestClient) -> None:
        # `slug == "../outside"` — guarded by the slug containment check.
        resp = skills_test_client.get("/api/v1/skills/..%2Foutside/files/secret-outside.txt")
        assert resp.status_code in {403, 404}
        assert "STOLEN-OUTSIDE" not in resp.text

    def test_path_traversal_slug_escape_detail(self, skills_test_client: TestClient) -> None:
        resp = skills_test_client.get("/api/v1/skills/..%2Foutside")
        assert resp.status_code == 404
