# Phase 19: Skill Registry and Plugin System - Research

**Researched:** 2026-03-10
**Domain:** GitHub-sourced plugin marketplace, Claude Agent SDK skill injection, encrypted PAT storage
**Confidence:** HIGH

## Summary

Phase 19 builds a GitHub-sourced plugin marketplace on top of the existing skill/MCP infrastructure from Phases 14 and 16. Plugins follow the `anthropics/skills` convention: each skill lives in `skills/{name}/SKILL.md` with an optional `reference/` subdirectory containing markdown files. Plugin versioning uses Git commit SHAs (HEAD of the source repo's default branch). The install flow fetches repo contents via GitHub REST API, stores SKILL.md content + references as JSONB in a new `workspace_plugins` table, and injects them into the agent sandbox via the existing `role_skill_materializer.py` pattern (extended to handle `plugin-` prefix directories).

Private repo access uses a per-workspace GitHub PAT encrypted with the existing `encrypt_api_key()` / `decrypt_api_key()` Fernet helpers — the same pattern used for MCP bearer tokens and BYOK API keys. The 5-minute update-check cache uses the existing Redis client (`infrastructure/cache/redis.py`). The settings UI is an extension of the existing `skills-settings-page.tsx` with a **Plugins** section, using the same `MCPServersStore` MobX pattern.

**Primary recommendation:** New `GitHubPluginService` (httpx-based, same client pattern as `integrations/github/client.py`) handles all GitHub API calls. New `WorkspacePlugin` DB model + migration `074_*` stores installed plugins. Plugin skill injection added to `role_skill_materializer.py` (new helper `materialize_plugin_skills`). Frontend: new `PluginsStore` added to `AIStore` alongside `MCPServersStore`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Plugin browser UI: card grid with icon + name + tagline + status badge (Installed / Update Available / Not installed)
- Status badge drives one-click Install/Update from card
- Plugin preview: single scrollable page — Overview | SKILL.md | References tabs
- Location: Settings → Skills page extended with a **Plugins** section/tab — NOT a separate nav item
- Plugins come from GitHub repos following `skills/{skill-name}/SKILL.md` + `skills/{skill-name}/references/` convention
- Admin pastes GitHub repo URL → Pilot Space fetches `skills/` directory listing → admin selects which to install
- SKILL.md content auto-wired immediately on install
- MCP registration and action button definitions require admin confirmation before wiring
- When GitHub unreachable: block marketplace with clear error, no cached/stale data fallback
- References stored as JSONB column `references: [{filename: string, content: string}]` on installed plugin record — no separate table
- Version = Git commit SHA recorded at install time
- "Update available" = current HEAD SHA differs from installed SHA
- Update check on-demand when admin opens Plugins page, cached 5 minutes
- Update always overwrites with upstream content, no diff/warning
- Private repos use per-workspace GitHub PAT encrypted with existing `encrypt_api_key()` pattern
- PAT stored once in Settings → Plugins "GitHub Access" section
- New workspaces seeded with default official plugins at creation using system-level GitHub token
- No manual setup for seeded plugins

### Claude's Discretion

- Exact DB table/column names for the plugin install record
- Caching mechanism for the 5-minute update check results
- GitHub API rate limit handling (retry/backoff strategy)
- Exact badge/chip visual styling (follow existing codebase patterns)
- Error message copy for GitHub connectivity failures

### Deferred Ideas (OUT OF SCOPE)

- Community plugin publishing (submitting to a Pilot Space-hosted registry)
- Org-level shared plugin registry
- Built-in SKILL.md editor / create plugin without GitHub
- Plugin analytics
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SKRG-01 | Workspace admin browses plugins from a GitHub repo URL (public or private) | GitHub Contents API `GET /repos/{owner}/{repo}/contents/skills` returns directory listing; `marketplace.json` in `.claude-plugin/` optional metadata |
| SKRG-02 | Admin installs a plugin — SKILL.md content auto-wired, MCP/actions require confirmation | `role_skill_materializer.py` pattern for file materialization; existing admin confirmation pattern from AI governance |
| SKRG-03 | Installed plugins inject SKILL.md + references into PilotSpaceAgent at init time | Existing `materialize_role_skills` pattern; new `materialize_plugin_skills` function using same `skills_dir` |
| SKRG-04 | "Update available" badge appears when HEAD SHA differs from installed SHA | GitHub Commits API `GET /repos/{owner}/{repo}/commits/{branch}`; Redis TTL cache (5 min) |
| SKRG-05 | New workspaces seeded with default official plugins automatically | Post-`create_workspace` hook using system GITHUB_TOKEN env var; list from config |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | already installed | GitHub API calls (async) | Already used in `workspace_mcp_servers.py` for status checks |
| cryptography/Fernet | already installed | GitHub PAT encryption | Existing `encrypt_api_key()` / `decrypt_api_key()` helpers |
| redis.asyncio | already installed | 5-minute update check cache | Existing `RedisClient` in `infrastructure/cache/redis.py` |
| SQLAlchemy (JSONB) | already installed | References storage | `postgresql.JSONB` already used elsewhere in codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | check if installed | GitHub API retry with exponential backoff | AI layer already uses resilience pattern — check if tenacity is already a dep |
| orjson | already installed | JSON serialization for cache | Already used in `redis.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Redis cache | In-process dict TTL | Redis is workspace-shared; dict resets on process restart |
| httpx | aiohttp | httpx already in project, consistent with MCP server status checks |

**No new package installs required.** All dependencies are already in the project.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/src/pilot_space/
├── integrations/github/
│   ├── plugin_service.py        # NEW: GitHubPluginService — fetch skills/, SKILL.md, refs, HEAD SHA
├── infrastructure/database/models/
│   ├── workspace_plugin.py      # NEW: WorkspacePlugin model (JSONB references column)
├── infrastructure/database/repositories/
│   ├── workspace_plugin_repository.py  # NEW: CRUD + get_by_workspace_and_name
├── application/services/workspace_plugin/
│   ├── __init__.py
│   ├── install_plugin_service.py    # NEW: install + update flow
│   ├── seed_plugins_service.py      # NEW: new workspace seeding
├── api/v1/routers/
│   ├── workspace_plugins.py     # NEW: REST endpoints for plugin CRUD + update check
├── api/v1/schemas/
│   ├── workspace_plugin.py      # NEW: Pydantic schemas
└── ai/agents/
    └── role_skill_materializer.py  # EXTEND: add materialize_plugin_skills()

alembic/versions/
└── 074_add_workspace_plugins.py  # NEW: migration

frontend/src/
├── stores/ai/
│   └── PluginsStore.ts          # NEW: mirrors MCPServersStore pattern
├── stores/ai/AIStore.ts         # EXTEND: add plugins: PluginsStore
├── services/api/
│   └── plugins.ts               # NEW: API client for plugins endpoints
├── features/settings/
│   ├── pages/skills-settings-page.tsx  # EXTEND: add Plugins section
│   ├── components/
│   │   ├── plugin-card.tsx          # NEW: card grid item
│   │   ├── plugin-detail-sheet.tsx  # NEW: slide-over with 3 tabs
│   │   ├── add-repo-form.tsx        # NEW: URL + PAT input
│   │   └── github-access-section.tsx # NEW: PAT management
```

### Pattern 1: GitHubPluginService — GitHub API Client

**What:** Stateless service taking an optional PAT; wraps GitHub REST API calls for plugin discovery and version checking.

**When to use:** Called from router handlers and seed service.

```python
# Source: based on integrations/github/client.py pattern
class GitHubPluginService:
    """Fetch plugin metadata from GitHub repos.

    Uses system GITHUB_TOKEN for public repos and official seeding.
    Uses workspace PAT (decrypted) for private repos.
    """

    GITHUB_API = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, token: str | None = None) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=self.GITHUB_API,
            headers=headers,
            timeout=15.0,
        )

    async def list_skills(self, owner: str, repo: str) -> list[SkillMeta]:
        """GET /repos/{owner}/{repo}/contents/skills — returns subdirectory names."""
        ...

    async def fetch_skill_content(self, owner: str, repo: str, skill_name: str) -> SkillContent:
        """Fetch SKILL.md + all files in reference/ for a skill.

        Returns SkillContent(skill_md: str, references: list[Reference])
        """
        ...

    async def get_head_sha(self, owner: str, repo: str) -> str:
        """GET /repos/{owner}/{repo}/commits/{branch} — returns sha field."""
        ...
```

**CRITICAL NOTE:** `anthropics/skills` uses `reference/` (singular), NOT `references/`. The CONTEXT.md says `references/` — the actual repo uses `reference/`. The service must handle BOTH directory names when scanning.

### Pattern 2: WorkspacePlugin DB Model

**What:** One row per installed plugin per workspace. Stores SKILL.md + references as JSONB to avoid a separate table.

```python
# Source: follows WorkspaceRoleSkill and WorkspaceMcpServer patterns
class WorkspacePlugin(WorkspaceScopedModel):
    __tablename__ = "workspace_plugins"

    repo_url: Mapped[str]          # e.g. "https://github.com/anthropics/skills"
    repo_owner: Mapped[str]        # parsed from URL: "anthropics"
    repo_name: Mapped[str]         # parsed from URL: "skills"
    skill_name: Mapped[str]        # directory name: "mcp-builder"
    display_name: Mapped[str]      # from SKILL.md frontmatter `name` or dir name
    description: Mapped[str | None]  # from SKILL.md frontmatter `description`
    skill_content: Mapped[str]     # full SKILL.md text
    references: Mapped[list[dict]] # JSONB: [{filename: str, content: str}]
    installed_sha: Mapped[str]     # Git SHA at install time
    is_active: Mapped[bool]        # True after SKILL.md wired; False until confirmed
    github_pat_encrypted: Mapped[str | None]  # NULL for public repos
    installed_by: Mapped[uuid | None]  # FK users.id SET NULL

    # Partial unique index: (workspace_id, repo_owner, repo_name, skill_name)
    # WHERE is_deleted = false
```

**Column notes:**
- `references` uses `postgresql.JSONB` — stores list of `{filename, content}` dicts
- `installed_sha` is `String(40)` (Git SHA is always 40 hex chars)
- Partial unique index prevents duplicate installs without blocking reinstall after uninstall

### Pattern 3: Plugin Skill Materialization

**What:** Extend `role_skill_materializer.py` with `materialize_plugin_skills()` — writes plugin SKILL.md files to sandbox using `plugin-{skill_name}` directory prefix.

```python
# Source: role_skill_materializer.py (existing pattern — extend, not replace)
_PLUGIN_SKILL_PREFIX = "plugin-"

async def materialize_plugin_skills(
    db_session: AsyncSession,
    workspace_id: UUID,
    skills_dir: Path,
) -> int:
    """Write installed plugin skills to .claude/skills/ as plugin-{name}/SKILL.md.

    Also writes reference/ files alongside SKILL.md.
    Workspace-scoped: all members in workspace get all active plugins.
    """
    from pilot_space.infrastructure.database.repositories.workspace_plugin_repository import (
        WorkspacePluginRepository,
    )
    repo = WorkspacePluginRepository(db_session)
    plugins = await repo.get_active_by_workspace(workspace_id)

    expected_dirs: set[str] = set()
    for plugin in plugins:
        dir_name = f"{_PLUGIN_SKILL_PREFIX}{plugin.skill_name}"
        expected_dirs.add(dir_name)
        plugin_dir = skills_dir / dir_name
        await asyncio.to_thread(_write_plugin_files, plugin_dir, plugin)

    await asyncio.to_thread(_cleanup_stale_plugin_skills, skills_dir, expected_dirs)
    return len(plugins)
```

**Where to call it:** Add call in `PilotSpaceAgent.stream()` alongside `materialize_role_skills` — same `skills_dir` path.

### Pattern 4: Update Check Cache

**What:** Store GitHub HEAD SHA per `(workspace_id, repo_owner, repo_name)` in Redis with 5-minute TTL. On Plugins page open, check cache first; if miss, hit GitHub API and cache result.

```python
def plugin_update_check_key(workspace_id: str, owner: str, repo: str) -> str:
    return f"plugin:head_sha:{workspace_id}:{owner}:{repo}"

# TTL: 300 seconds (5 minutes)
PLUGIN_SHA_CACHE_TTL = 300
```

**Cache miss behavior:** Fetch GitHub HEAD SHA → compare with `installed_sha` on each plugin record → return `has_update: bool` per plugin → cache the HEAD SHA for 5 min.

### Pattern 5: GitHub PAT Storage

**What:** Per-workspace GitHub PAT encrypted with `encrypt_api_key()`. Stored on a new `WorkspaceGithubCredential` record OR as a workspace-level field. Given single PAT per workspace, store on a new simple model.

```python
# Simpler: one table for workspace GitHub credential
class WorkspaceGithubCredential(WorkspaceScopedModel):
    __tablename__ = "workspace_github_credentials"
    pat_encrypted: Mapped[str]     # Fernet-encrypted PAT
    created_by: Mapped[uuid | None]
```

**Encrypt on save:** `pat_encrypted = encrypt_api_key(raw_pat)`
**Decrypt on use:** `raw_pat = decrypt_api_key(record.pat_encrypted)`

### Pattern 6: Repo URL Parsing

**What:** Parse `https://github.com/{owner}/{repo}` to extract `owner` and `repo`.

```python
import re
_GITHUB_URL_RE = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)

def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub repo URL. Returns (owner, repo)."""
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url!r}")
    return m.group("owner"), m.group("repo")
```

### Pattern 7: New Workspace Seeding

**What:** After `create_workspace` succeeds, call `SeedPluginsService` with a system GitHub token. Non-blocking: failures logged, not surfaced to the user.

```python
# In workspaces router, after workspace creation:
asyncio.create_task(
    seed_plugins_service.seed_workspace(workspace_id=new_workspace.id)
)
```

`SeedPluginsService` uses `os.getenv("GITHUB_TOKEN")` (system token). If missing, seeding is skipped. Pre-configured list of default skills: `[("anthropics", "skills", ["mcp-builder", "claude-api"])]` — or read from config.

### Pattern 8: Frontend PluginsStore

**What:** MobX observable store following `MCPServersStore` pattern exactly.

```typescript
// Source: stores/ai/MCPServersStore.ts pattern
export class PluginsStore {
  installedPlugins: InstalledPlugin[] = [];
  availablePlugins: AvailablePlugin[] = [];   // after fetching repo
  isLoading = false;
  isSaving = false;
  isCheckingUpdates = false;
  error: string | null = null;
  repoError: string | null = null;  // GitHub unreachable error

  constructor() { makeAutoObservable(this); }

  async fetchRepo(workspaceId: string, repoUrl: string): Promise<void> { ... }
  async installPlugin(workspaceId: string, pluginId: string): Promise<void> { ... }
  async updatePlugin(workspaceId: string, pluginId: string): Promise<void> { ... }
  async uninstallPlugin(workspaceId: string, pluginId: string): Promise<void> { ... }
  async checkUpdates(workspaceId: string): Promise<void> { ... }
}
```

Add to `AIStore`:
```typescript
plugins: PluginsStore;  // alongside mcpServers
```

### Anti-Patterns to Avoid

- **Caching stale plugin data when GitHub is unreachable:** CONTEXT.md is explicit — block with error, no fallback to cached content for the browse/install flow. Only the update-check SHA result is cached.
- **Using `references/` directory name exclusively:** The actual `anthropics/skills` repo uses `reference/` (singular). Handle both to be safe.
- **Blocking event loop in file I/O:** Follow existing `asyncio.to_thread(_write_...)` pattern from `role_skill_materializer.py`.
- **Using `"/"` for FastAPI root routes:** Use `""` — see FastAPI routing gotcha in CLAUDE.md.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret encryption | Custom AES impl | `encrypt_api_key()` / `decrypt_api_key()` | Already tested, Fernet handles IV + HMAC |
| HTTP retry/backoff | Custom retry loop | `tenacity` or existing `ResilientExecutor` | Edge cases with jitter, max retries, status codes |
| GitHub API auth | Custom header builder | Extend `GitHubClient` or create `GitHubPluginService` with same pattern | Existing client already handles rate limit errors, auth headers |
| Redis TTL cache | In-memory dict | `RedisClient.set()` with `ttl=300` | Process-restart safe, workspace-shared across workers |
| RLS policies | Custom ORM filtering | Standard migration pattern (see `073_add_workspace_role_skills.py`) | Already proven pattern; skipping breaks multi-tenant isolation |

**Key insight:** Every infrastructure piece needed (encryption, HTTP client, Redis cache, RLS migrations, skill file materialization) already exists and is tested. This phase is 90% wiring.

---

## Common Pitfalls

### Pitfall 1: `reference/` vs `references/` Directory Name
**What goes wrong:** CONTEXT.md says `references/` (plural) but `anthropics/skills` actual repo uses `reference/` (singular). Code that only looks for `references/` will find zero reference files in the official repo.
**Why it happens:** Convention drift between the CONTEXT.md discussion and the actual repo.
**How to avoid:** Fetch any subdirectory whose name starts with `ref` and contains `.md` files, or explicitly try both `reference/` and `references/`.
**Warning signs:** Plugin installs with empty references array.

### Pitfall 2: GitHub API Rate Limiting Without Auth
**What goes wrong:** Unauthenticated GitHub API calls are rate-limited to 60/hour. Fetching `skills/` listing + SKILL.md + reference files for multiple plugins can hit this quickly.
**Why it happens:** Not passing a token for public repo access.
**How to avoid:** Always pass `GITHUB_TOKEN` system token (even for public repos) to get 5000/hour. Fall back gracefully with `GitHubRateLimitError` from existing exceptions.
**Warning signs:** 403 responses with `X-RateLimit-Remaining: 0`.

### Pitfall 3: JSONB Column on SQLite Test DB
**What goes wrong:** Tests using `sqlite+aiosqlite:///:memory:` will fail with `JSONB` column type — SQLite has no JSONB.
**Why it happens:** Default test DB is SQLite (see `CLAUDE.md` gotcha #5).
**How to avoid:** Follow `WorkspaceRoleSkillRepository` pattern — use `OperationalError` guard in materializer. In tests, use `JSON` type fallback or set `TEST_DATABASE_URL`. Use `postgresql.JSONB` in model but handle `OperationalError` in materializer.
**Warning signs:** `sqlalchemy.exc.OperationalError: near "JSON"` in unit tests.

### Pitfall 4: 700-Line File Limit
**What goes wrong:** `pilotspace_agent.py` and `role_skill_materializer.py` are flagged as near the limit per `STATE.md`.
**Why it happens:** Adding `materialize_plugin_skills` to the materializer grows the file.
**How to avoid:** If `role_skill_materializer.py` would exceed 700 lines, split plugin materialization into `plugin_skill_materializer.py` and call from the same agent init location.
**Warning signs:** Pre-commit hook fails with file size violation.

### Pitfall 5: `encrypt_api_key()` Takes One Argument
**What goes wrong:** STATE.md decision from Phase 14 explicitly notes: "`encrypt_api_key()` takes one argument (no master_secret) — uses global EncryptionService singleton; plan interface doc was incorrect"
**Why it happens:** Confusion with workspace envelope encryption (which is different — uses Fernet with master key).
**How to avoid:** Call `encrypt_api_key(raw_pat)` — single argument. Do NOT pass a master_secret.
**Warning signs:** TypeError at runtime.

### Pitfall 6: Plugin Seeding Blocking Workspace Creation
**What goes wrong:** Seeding hits GitHub API synchronously in the workspace creation request, adding 1-3s latency and potentially failing the whole request.
**Why it happens:** Forgetting to background-task the seeding step.
**How to avoid:** Use `asyncio.create_task()` — same pattern as KG population (`memory_worker.py`). Seed failures must be non-fatal (log only).
**Warning signs:** Workspace creation endpoint timeout in tests.

### Pitfall 7: DI Wiring for New Service
**What goes wrong:** New `WorkspacePluginRepository` or `GitHubPluginService` used via `@inject` in a router file not listed in `container.py` wiring_config.modules — silently gets default values.
**Why it happens:** DI gotcha documented in `CLAUDE.md`.
**How to avoid:** Instantiate plugin services directly in router handlers (SCIM/related-issues pattern) rather than via DI, or add new module to `wiring_config.modules`.
**Warning signs:** Repository returns empty results without error.

---

## Code Examples

### GitHub Contents API — List `skills/` Directory

```python
# Source: https://api.github.com/repos/anthropics/skills/contents/skills
# GET /repos/{owner}/{repo}/contents/skills
# Returns: JSON array of objects with {name, type, sha, download_url, ...}
# Filter: items where type == "dir" are skill subdirectories

async def list_skills(self, owner: str, repo: str) -> list[str]:
    """Returns list of skill directory names under skills/."""
    resp = await self._client.get(f"/repos/{owner}/{repo}/contents/skills")
    if resp.status_code == 404:
        raise PluginRepoError(f"No skills/ directory found in {owner}/{repo}")
    if resp.status_code == 403:
        raise GitHubRateLimitError("Rate limit exceeded or auth required")
    resp.raise_for_status()
    items = resp.json()
    return [item["name"] for item in items if item["type"] == "dir"]
```

### GitHub Commits API — Get HEAD SHA

```python
# GET /repos/{owner}/{repo}/commits/{branch}
# Returns: JSON object with top-level "sha" field
# Confirmed SHA for anthropics/skills main: b0cbd3df1533b396d281a6886d5132f623393a9c

async def get_head_sha(self, owner: str, repo: str, branch: str = "main") -> str:
    resp = await self._client.get(f"/repos/{owner}/{repo}/commits/{branch}")
    resp.raise_for_status()
    return resp.json()["sha"]
```

### GitHub Contents API — Fetch File Content

```python
# GET /repos/{owner}/{repo}/contents/skills/{skill_name}/SKILL.md
# Returns: JSON with "content" field (base64-encoded) and "encoding": "base64"
import base64

async def fetch_skill_md(self, owner: str, repo: str, skill_name: str) -> str:
    path = f"skills/{skill_name}/SKILL.md"
    resp = await self._client.get(f"/repos/{owner}/{repo}/contents/{path}")
    if resp.status_code == 404:
        raise PluginRepoError(f"SKILL.md not found for skill {skill_name!r}")
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["content"]).decode("utf-8")
```

### Existing `encrypt_api_key` Pattern (Confirmed)

```python
# Source: infrastructure/encryption.py
# encrypt_api_key takes ONE argument — no master_secret param
from pilot_space.infrastructure.encryption import encrypt_api_key, decrypt_api_key

# Store PAT
pat_encrypted = encrypt_api_key(raw_pat)          # returns Fernet ciphertext str

# Retrieve PAT
raw_pat = decrypt_api_key(record.pat_encrypted)   # raises EncryptionError on failure
```

### Redis Cache — 5-Minute SHA Cache

```python
# Source: infrastructure/cache/redis.py + types.py
# RedisClient.set() supports ttl parameter

PLUGIN_SHA_CACHE_TTL = 300  # 5 minutes

async def get_cached_head_sha(
    redis: RedisClient,
    workspace_id: str,
    owner: str,
    repo: str,
) -> str | None:
    key = f"plugin:head_sha:{workspace_id}:{owner}:{repo}"
    result = await redis.get(key)
    return result if isinstance(result, str) else None

async def cache_head_sha(
    redis: RedisClient,
    workspace_id: str,
    owner: str,
    repo: str,
    sha: str,
) -> None:
    key = f"plugin:head_sha:{workspace_id}:{owner}:{repo}"
    await redis.set(key, sha, ttl=PLUGIN_SHA_CACHE_TTL)
```

### Migration Template (migration `074_*`)

```python
# Source: alembic/versions/073_add_workspace_role_skills.py pattern
# Next migration: 074_add_workspace_plugins

revision: str = "074_add_workspace_plugins"
down_revision: str = "073_add_workspace_role_skills"

def upgrade() -> None:
    op.create_table(
        "workspace_plugins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, ...),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(...), ...),
        sa.Column("repo_url", sa.String(512), nullable=False),
        sa.Column("repo_owner", sa.String(128), nullable=False),
        sa.Column("repo_name", sa.String(128), nullable=False),
        sa.Column("skill_name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("skill_content", sa.Text(), nullable=False),
        sa.Column("references", postgresql.JSONB(), nullable=False, server_default="'[]'::jsonb"),
        sa.Column("installed_sha", sa.String(40), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=text("true"), nullable=False),
        sa.Column("github_pat_encrypted", sa.String(1024), nullable=True),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # ... timestamps, is_deleted, etc.
    )
    # Partial unique index
    op.execute(text(
        "CREATE UNIQUE INDEX uq_workspace_plugins_workspace_skill "
        "ON workspace_plugins (workspace_id, repo_owner, repo_name, skill_name) "
        "WHERE is_deleted = false"
    ))
    # RLS (same UPPERCASE roles, same service_role bypass pattern)
    ...
```

**IMPORTANT:** Optionally, store the GitHub PAT in a separate `workspace_github_credentials` table (one PAT per workspace, not per plugin). This avoids storing the encrypted PAT redundantly on every plugin record. Recommended: separate table, since PAT is workspace-level not plugin-level.

### SKILL.md Frontmatter Structure (Confirmed from anthropics/skills)

```yaml
---
name: claude-api
description: >
  Use this skill when code imports Anthropic SDKs or user requests Claude API usage.
  Excludes general programming, ML/data science, non-Anthropic AI SDKs.
license: See LICENSE.txt for complete terms
---
```

Fields: `name`, `description`, `license`. No `version`, no `tags`. The `mcp-builder` skill has the same minimal frontmatter.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hard-coded skill files in sandbox | GitHub-sourced plugins fetched at install time | Phase 19 | Dynamic plugin lifecycle without code deployment |
| Role skills only (WRSKL-01..04) | Role skills + installable plugins both materialized | Phase 19 | Two parallel materialization flows in agent init |
| No versioning for skills | Git SHA versioning per installed plugin | Phase 19 | Enables update detection |

**Key structure corrections from direct API inspection:**
- `anthropics/skills` uses `reference/` (singular), not `references/` (plural)
- SKILL.md frontmatter has only 3 fields: `name`, `description`, `license`
- The `.claude-plugin/marketplace.json` groups skills into named "plugins" — this is the official plugin manifest format but Pilot Space does NOT need to implement marketplace.json parsing for MVP (user provides GitHub URL + selects skills directly)
- HEAD SHA API: `GET /repos/{owner}/{repo}/commits/main` returns top-level `sha` string

---

## Open Questions

1. **GitHub PAT storage location — per-plugin vs per-workspace**
   - What we know: CONTEXT.md says "PAT stored once per workspace"; one record makes more sense architecturally
   - What's unclear: whether a second table `workspace_github_credentials` or a field on `workspaces` table is cleaner
   - Recommendation: New `workspace_github_credentials` table (one row per workspace) — consistent with `workspace_mcp_servers` and `workspace_encryption_keys` pattern of dedicated credential tables

2. **Default seeding list — hardcoded vs config file**
   - What we know: CONTEXT.md says "pre-configured list from anthropics/skills"; seeding uses system GITHUB_TOKEN
   - What's unclear: whether the default plugin list should be in code or a config file
   - Recommendation: Hardcode in `seed_plugins_service.py` as a module-level constant `DEFAULT_PLUGINS: list[tuple[str, str, list[str]]]` — small enough that a config file adds unnecessary complexity for MVP

3. **`reference/` vs `references/` handling**
   - What we know: `anthropics/skills` uses `reference/` (confirmed via GitHub API). CONTEXT.md says `references/` based on the original discussion.
   - Recommendation: Planner should note that `GitHubPluginService.fetch_skill_content()` MUST try both directory names. Document this in the install service with a comment.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), vitest (frontend) |
| Config file | `backend/pyproject.toml` (pytest section), `frontend/vitest.config.ts` |
| Quick run command | `cd backend && uv run pytest tests/unit/api/test_workspace_plugins_router.py -x` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKRG-01 | `GET /workspaces/{id}/plugins/browse` returns skill list from GitHub | unit (mock httpx) | `pytest tests/unit/api/test_workspace_plugins_router.py::test_browse_repo -x` | Wave 0 |
| SKRG-02 | `POST /workspaces/{id}/plugins/install` creates WorkspacePlugin record + materializes SKILL.md | unit | `pytest tests/unit/services/test_install_plugin_service.py -x` | Wave 0 |
| SKRG-03 | `materialize_plugin_skills()` writes `plugin-{name}/SKILL.md` + reference files to skills_dir | unit | `pytest tests/unit/agents/test_plugin_skill_materializer.py -x` | Wave 0 |
| SKRG-04 | Update check endpoint returns `has_update=true` when HEAD SHA differs; cached 5 min | unit | `pytest tests/unit/api/test_workspace_plugins_router.py::test_update_check -x` | Wave 0 |
| SKRG-05 | `SeedPluginsService.seed_workspace()` installs default plugins; skips on missing GITHUB_TOKEN | unit | `pytest tests/unit/services/test_seed_plugins_service.py -x` | Wave 0 |
| SKRG-01 | `PluginsStore.fetchRepo()` populates `availablePlugins` + clears on error | unit (vitest) | `pnpm test stores/ai/PluginsStore.test.ts` | Wave 0 |
| SKRG-04 | Plugin card shows orange "Update available" chip when `has_update=true` | unit (vitest) | `pnpm test features/settings/components/plugin-card.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/ -x -q`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/api/test_workspace_plugins_router.py` — covers SKRG-01, SKRG-04
- [ ] `backend/tests/unit/services/test_install_plugin_service.py` — covers SKRG-02
- [ ] `backend/tests/unit/agents/test_plugin_skill_materializer.py` — covers SKRG-03
- [ ] `backend/tests/unit/services/test_seed_plugins_service.py` — covers SKRG-05
- [ ] `frontend/src/stores/ai/__tests__/PluginsStore.test.ts` — covers SKRG-01 frontend
- [ ] `frontend/src/features/settings/components/__tests__/plugin-card.test.tsx` — covers SKRG-04 frontend

---

## Sources

### Primary (HIGH confidence)
- GitHub REST API (live): `https://api.github.com/repos/anthropics/skills/contents/skills` — confirmed directory structure with 17 skills
- GitHub REST API (live): `https://api.github.com/repos/anthropics/skills/contents/skills/mcp-builder` — confirmed `reference/` (singular) subdirectory
- GitHub REST API (live): `https://api.github.com/repos/anthropics/skills/contents/.claude-plugin/marketplace.json` — confirmed marketplace.json format
- `backend/src/pilot_space/ai/agents/role_skill_materializer.py` — materialization pattern, `asyncio.to_thread`, prefix convention
- `backend/src/pilot_space/infrastructure/encryption.py` — `encrypt_api_key()` signature confirmed (single arg)
- `backend/src/pilot_space/infrastructure/cache/redis.py` + `types.py` — Redis TTL cache pattern
- `backend/src/pilot_space/infrastructure/database/models/workspace_mcp_server.py` — Fernet-encrypted field pattern
- `backend/alembic/versions/073_add_workspace_role_skills.py` — migration template, RLS policies, partial unique index
- `frontend/src/stores/ai/MCPServersStore.ts` — MobX store pattern to mirror
- `frontend/src/stores/ai/AIStore.ts` — confirmed `mcpServers: MCPServersStore` wiring location
- `frontend/src/features/settings/pages/skills-settings-page.tsx` — confirmed extension point for Plugins section

### Secondary (MEDIUM confidence)
- GitHub REST API reference: https://docs.github.com/en/rest/repos/contents — file content API returns base64-encoded content field
- GitHub rate limits: 60/hr unauthenticated, 5000/hr authenticated — confirmed via GitHub docs

### Tertiary (LOW confidence)
- `reference/` vs `references/` — only one skill (`mcp-builder`) was inspected for subdirectory structure. Other skills with subdirectories (e.g., `claude-api` has language subdirs but no `reference/`) may vary. Confirm before finalizing GitHubPluginService.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in project, confirmed via source code
- Architecture: HIGH — patterns directly lifted from existing Phase 14/16 implementations
- GitHub API behavior: HIGH — directly verified against live anthropics/skills API
- Pitfalls: HIGH — confirmed from STATE.md decision log and existing code inspection

**Research date:** 2026-03-10
**Valid until:** 2026-04-09 (30 days — GitHub API and anthropics/skills structure are stable)
