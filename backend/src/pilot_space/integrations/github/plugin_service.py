"""GitHub Plugin Service for browsing and fetching skill plugins.

Stateless httpx-based service that wraps GitHub REST API calls for:
- Listing available skills in a repository's `skills/` directory
- Fetching SKILL.md content and reference files for a skill
- Getting HEAD commit SHA for version checking

Uses system GITHUB_TOKEN for public repos; workspace PAT for private repos.

Source: Phase 19, SKRG-01, SKRG-04
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field

import httpx

from pilot_space.infrastructure.logging import get_logger

logger = get_logger(__name__)

_GITHUB_URL_RE = re.compile(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse a GitHub repository URL into (owner, repo) tuple.

    Handles standard URLs, .git suffix, and trailing slashes.

    Args:
        url: GitHub repository URL (e.g., "https://github.com/anthropics/skills").

    Returns:
        Tuple of (owner, repo_name).

    Raises:
        ValueError: If URL does not match expected GitHub format.
    """
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url!r}")
    return m.group("owner"), m.group("repo")


class PluginRepoError(Exception):
    """Raised when a plugin repository is not found or inaccessible."""


class PluginRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""


@dataclass
class SkillContent:
    """Fetched content of a skill from a GitHub repository.

    Attributes:
        skill_md: Full text of SKILL.md.
        references: List of reference file dicts [{filename, content}].
        display_name: Parsed from SKILL.md frontmatter `name` field.
        description: Parsed from SKILL.md frontmatter `description` field.
    """

    skill_md: str
    references: list[dict[str, str]] = field(default_factory=list)
    display_name: str = ""
    description: str = ""


@dataclass
class SkillMeta:
    """Brief metadata about a skill directory in a repository.

    Attributes:
        skill_name: Directory name under skills/.
        display_name: Parsed from frontmatter or same as skill_name.
        description: Optional description from frontmatter.
    """

    skill_name: str
    display_name: str = ""
    description: str = ""


class GitHubPluginService:
    """Fetch plugin metadata from GitHub repos.

    Uses system GITHUB_TOKEN for public repos and official seeding.
    Uses workspace PAT (decrypted) for private repos.
    """

    GITHUB_API = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, token: str | None = None) -> None:
        """Initialize the service with an optional auth token.

        Falls back to GITHUB_TOKEN environment variable if no token provided.

        Args:
            token: GitHub PAT for authentication. Uses GITHUB_TOKEN env var as fallback.
        """
        effective_token = token or os.getenv("GITHUB_TOKEN")
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }
        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"
        self._client = httpx.AsyncClient(
            base_url=self.GITHUB_API,
            headers=headers,
            timeout=15.0,
        )

    async def list_skills(self, owner: str, repo: str) -> list[str]:
        """List available skill directory names in a repository.

        Fetches the `skills/` directory listing and returns names of
        subdirectories (type == "dir").

        Args:
            owner: GitHub owner/organization.
            repo: Repository name.

        Returns:
            List of skill directory names.

        Raises:
            PluginRepoError: If no skills/ directory found (404).
            PluginRateLimitError: If rate limited (403).
        """
        resp = await self._client.get(f"/repos/{owner}/{repo}/contents/skills")
        if resp.status_code == 404:
            raise PluginRepoError(f"No skills/ directory found in {owner}/{repo}")
        if resp.status_code == 403:
            raise PluginRateLimitError(f"Rate limit exceeded or auth required for {owner}/{repo}")
        resp.raise_for_status()
        items = resp.json()
        return [item["name"] for item in items if item["type"] == "dir"]

    async def fetch_skill_content(self, owner: str, repo: str, skill_name: str) -> SkillContent:
        """Fetch SKILL.md and reference files for a skill.

        Tries `reference/` first, then `references/` as fallback for the
        reference files subdirectory (anthropics/skills uses singular).

        Args:
            owner: GitHub owner/organization.
            repo: Repository name.
            skill_name: Name of the skill directory under skills/.

        Returns:
            SkillContent with markdown text and reference file list.

        Raises:
            PluginRepoError: If SKILL.md not found.
        """
        # Fetch SKILL.md
        path = f"skills/{skill_name}/SKILL.md"
        resp = await self._client.get(f"/repos/{owner}/{repo}/contents/{path}")
        if resp.status_code == 404:
            raise PluginRepoError(f"SKILL.md not found for skill {skill_name!r}")
        resp.raise_for_status()
        data = resp.json()
        skill_md = base64.b64decode(data["content"]).decode("utf-8")

        # Parse frontmatter for display_name and description
        display_name, description = _parse_frontmatter(skill_md, skill_name)

        # Fetch reference files — try reference/ then references/
        references = await self._fetch_references(owner, repo, skill_name)

        return SkillContent(
            skill_md=skill_md,
            references=references,
            display_name=display_name,
            description=description,
        )

    async def _fetch_references(
        self, owner: str, repo: str, skill_name: str
    ) -> list[dict[str, str]]:
        """Fetch reference files from reference/ or references/ directory.

        Tries singular first, then plural as fallback.

        Args:
            owner: GitHub owner/organization.
            repo: Repository name.
            skill_name: Skill directory name.

        Returns:
            List of {filename, content} dicts.
        """
        for ref_dir in ("reference", "references"):
            ref_path = f"skills/{skill_name}/{ref_dir}"
            resp = await self._client.get(f"/repos/{owner}/{repo}/contents/{ref_path}")
            if resp.status_code == 404:
                continue
            if resp.status_code != 200:
                continue

            items = resp.json()
            if not isinstance(items, list):
                continue

            references: list[dict[str, str]] = []
            for item in items:
                if item.get("type") != "file":
                    continue
                file_resp = await self._client.get(
                    f"/repos/{owner}/{repo}/contents/{ref_path}/{item['name']}"
                )
                if file_resp.status_code == 200:
                    file_data = file_resp.json()
                    content = base64.b64decode(file_data["content"]).decode("utf-8")
                    references.append({"filename": item["name"], "content": content})
            return references

        return []

    async def get_head_sha(self, owner: str, repo: str, branch: str = "main") -> str:
        """Get the HEAD commit SHA for a branch.

        Args:
            owner: GitHub owner/organization.
            repo: Repository name.
            branch: Branch name (defaults to "main").

        Returns:
            40-character hex SHA string.

        Raises:
            httpx.HTTPStatusError: If the API call fails.
        """
        resp = await self._client.get(f"/repos/{owner}/{repo}/commits/{branch}")
        resp.raise_for_status()
        return resp.json()["sha"]

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()


def _parse_frontmatter(skill_md: str, fallback_name: str) -> tuple[str, str]:
    """Extract name and description from YAML frontmatter.

    Args:
        skill_md: Full SKILL.md text.
        fallback_name: Used as display_name if frontmatter has no `name` field.

    Returns:
        Tuple of (display_name, description).
    """
    display_name = fallback_name
    description = ""

    if not skill_md.startswith("---"):
        return display_name, description

    parts = skill_md.split("---", 2)
    if len(parts) < 3:
        return display_name, description

    frontmatter = parts[1]
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if line.startswith("name:"):
            display_name = line[len("name:") :].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            desc_val = line[len("description:") :].strip()
            if desc_val.startswith(">"):
                # Multi-line YAML description — take remaining lines
                desc_lines = []
                in_desc = False
                for fl_line in frontmatter.splitlines():
                    fl_line_stripped = fl_line.strip()
                    if fl_line_stripped.startswith("description:"):
                        in_desc = True
                        continue
                    if in_desc:
                        if fl_line_stripped and not fl_line_stripped.endswith(":"):
                            desc_lines.append(fl_line_stripped)
                        else:
                            break
                description = " ".join(desc_lines)
            else:
                description = desc_val.strip('"').strip("'")

    return display_name, description


__all__ = [
    "GitHubPluginService",
    "PluginRateLimitError",
    "PluginRepoError",
    "SkillContent",
    "SkillMeta",
    "parse_github_url",
]
