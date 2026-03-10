"""Tests for GitHubPluginService — SKRG-01 browse + SKRG-04 version check.

Tests use httpx mock transport to avoid real GitHub API calls.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.asyncio


def _mock_transport(responses: dict[str, tuple[int, dict | list]]) -> httpx.MockTransport:
    """Create a mock transport that returns predefined responses by URL path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in responses:
            status_code, body = responses[path]
            return httpx.Response(status_code, json=body)
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


class TestParseGithubUrl:
    """Tests for parse_github_url utility."""

    def test_parse_standard_url(self) -> None:
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url("https://github.com/anthropics/skills")
        assert owner == "anthropics"
        assert repo == "skills"

    def test_parse_url_with_git_suffix(self) -> None:
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url("https://github.com/acme/my-repo.git")
        assert owner == "acme"
        assert repo == "my-repo"

    def test_parse_url_with_trailing_slash(self) -> None:
        from pilot_space.integrations.github.plugin_service import parse_github_url

        owner, repo = parse_github_url("https://github.com/acme/repo/")
        assert owner == "acme"
        assert repo == "repo"

    def test_parse_invalid_url_raises(self) -> None:
        from pilot_space.integrations.github.plugin_service import parse_github_url

        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("https://gitlab.com/user/repo")


class TestListSkills:
    """Tests for GitHubPluginService.list_skills."""

    async def test_returns_directory_names(self) -> None:
        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        transport = _mock_transport(
            {
                "/repos/anthropics/skills/contents/skills": (
                    200,
                    [
                        {"name": "mcp-builder", "type": "dir"},
                        {"name": "claude-api", "type": "dir"},
                        {"name": "README.md", "type": "file"},
                    ],
                )
            }
        )
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        result = await svc.list_skills("anthropics", "skills")
        assert result == ["mcp-builder", "claude-api"]
        await svc._client.aclose()

    async def test_raises_plugin_repo_error_on_404(self) -> None:
        from pilot_space.integrations.github.plugin_service import (
            GitHubPluginService,
            PluginRepoError,
        )

        transport = _mock_transport(
            {"/repos/bad/repo/contents/skills": (404, {"message": "Not Found"})}
        )
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        with pytest.raises(PluginRepoError):
            await svc.list_skills("bad", "repo")
        await svc._client.aclose()

    async def test_raises_rate_limit_error_on_403(self) -> None:
        from pilot_space.integrations.github.plugin_service import (
            GitHubPluginService,
            PluginRateLimitError,
        )

        transport = _mock_transport(
            {"/repos/org/repo/contents/skills": (403, {"message": "rate limit exceeded"})}
        )
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        with pytest.raises(PluginRateLimitError):
            await svc.list_skills("org", "repo")
        await svc._client.aclose()


class TestFetchSkillContent:
    """Tests for GitHubPluginService.fetch_skill_content."""

    async def test_fetches_skill_md_and_references(self) -> None:
        import base64

        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        skill_md = "---\nname: test-skill\ndescription: A test\n---\n# Test"
        encoded = base64.b64encode(skill_md.encode()).decode()
        ref_content = "# Reference doc"
        ref_encoded = base64.b64encode(ref_content.encode()).decode()

        transport = _mock_transport(
            {
                "/repos/org/repo/contents/skills/test-skill/SKILL.md": (
                    200,
                    {"content": encoded, "encoding": "base64"},
                ),
                "/repos/org/repo/contents/skills/test-skill/reference": (
                    200,
                    [{"name": "guide.md", "type": "file"}],
                ),
                "/repos/org/repo/contents/skills/test-skill/reference/guide.md": (
                    200,
                    {"content": ref_encoded, "encoding": "base64"},
                ),
            }
        )
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        result = await svc.fetch_skill_content("org", "repo", "test-skill")
        assert result.skill_md == skill_md
        assert len(result.references) == 1
        assert result.references[0]["filename"] == "guide.md"
        assert result.references[0]["content"] == ref_content
        await svc._client.aclose()

    async def test_tries_references_fallback_directory(self) -> None:
        """When reference/ returns 404, tries references/ as fallback."""
        import base64

        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        skill_md = "---\nname: fb\n---\n# Fallback"
        encoded = base64.b64encode(skill_md.encode()).decode()
        ref_content = "# Ref"
        ref_encoded = base64.b64encode(ref_content.encode()).decode()

        transport = _mock_transport(
            {
                "/repos/org/repo/contents/skills/fb/SKILL.md": (
                    200,
                    {"content": encoded, "encoding": "base64"},
                ),
                # reference/ returns 404, references/ returns data
                "/repos/org/repo/contents/skills/fb/references": (
                    200,
                    [{"name": "doc.md", "type": "file"}],
                ),
                "/repos/org/repo/contents/skills/fb/references/doc.md": (
                    200,
                    {"content": ref_encoded, "encoding": "base64"},
                ),
            }
        )
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        result = await svc.fetch_skill_content("org", "repo", "fb")
        assert result.skill_md == skill_md
        assert len(result.references) == 1
        await svc._client.aclose()


class TestGetHeadSha:
    """Tests for GitHubPluginService.get_head_sha."""

    async def test_returns_sha_string(self) -> None:
        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        sha = "a" * 40
        transport = _mock_transport({"/repos/org/repo/commits/main": (200, {"sha": sha})})
        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        result = await svc.get_head_sha("org", "repo")
        assert result == sha
        assert len(result) == 40
        await svc._client.aclose()


class TestAuthorizationHeader:
    """Verify token is passed in Authorization header."""

    async def test_token_passed_in_header(self) -> None:
        from pilot_space.integrations.github.plugin_service import GitHubPluginService

        captured_headers: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json=[])

        svc = GitHubPluginService.__new__(GitHubPluginService)
        svc._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer test-token-123",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        await svc.list_skills("org", "repo")
        assert captured_headers.get("authorization") == "Bearer test-token-123"
        await svc._client.aclose()


class TestSchemas:
    """Tests for workspace_plugin Pydantic schemas."""

    def test_workspace_plugin_response_schema(self) -> None:
        from pilot_space.api.v1.schemas.workspace_plugin import WorkspacePluginResponse

        resp = WorkspacePluginResponse(
            id="00000000-0000-0000-0000-000000000001",
            workspace_id="00000000-0000-0000-0000-000000000002",
            repo_url="https://github.com/anthropics/skills",
            skill_name="mcp-builder",
            display_name="MCP Builder",
            description="Build MCP servers",
            installed_sha="a" * 40,
            is_active=True,
            has_update=False,
        )
        assert resp.skill_name == "mcp-builder"

    def test_workspace_plugin_install_request(self) -> None:
        from pilot_space.api.v1.schemas.workspace_plugin import WorkspacePluginInstallRequest

        req = WorkspacePluginInstallRequest(
            repo_url="https://github.com/anthropics/skills",
            skill_name="claude-api",
        )
        assert req.repo_url == "https://github.com/anthropics/skills"

    def test_skill_list_item(self) -> None:
        from pilot_space.api.v1.schemas.workspace_plugin import SkillListItem

        item = SkillListItem(
            skill_name="claude-api",
            display_name="Claude API",
            description="Use Claude APIs",
        )
        assert item.skill_name == "claude-api"

    def test_github_credential_response(self) -> None:
        from pilot_space.api.v1.schemas.workspace_plugin import WorkspaceGithubCredentialResponse

        resp = WorkspaceGithubCredentialResponse(has_pat=True)
        assert resp.has_pat is True
