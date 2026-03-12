# Phase 19: Skill Registry and Plugin System - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Workspace admins browse and install plugins sourced from GitHub repositories. Each plugin follows the Claude Code skills convention (`skills/{name}/SKILL.md` + `skills/{name}/references/`). Installing a plugin wires the skill content into the workspace's AI agent and optionally registers MCP tools and action buttons. New workspaces are seeded with default plugins at creation. Official and private plugins share the same GitHub-sourced install flow.

This phase does NOT include: building a hosted Pilot Space plugin registry/CDN, community plugin publishing, or a built-in markdown plugin editor.

</domain>

<decisions>
## Implementation Decisions

### Plugin Browser UI
- Card grid layout: icon + name + tagline + status badge (Installed / Update Available / Not installed)
- Status badge drives one-click Install/Update action from the card
- Plugin preview: single scrollable page (description → SKILL.md rendered markdown → References tab)
- Plugin detail has tabs: **Overview | SKILL.md | References**
- Location: Settings → Skills page extended with a **Plugins** section/tab — NOT a separate nav item

### GitHub-Sourced Plugin Model
- Plugins come from GitHub repos following Claude Code skills convention: `skills/{skill-name}/SKILL.md` + `skills/{skill-name}/references/`
- Researcher MUST investigate the exact file structure of `anthropics/skills` (https://github.com/anthropics/skills) to confirm conventions
- Install flow:
  1. Admin pastes GitHub repo URL (e.g. `https://github.com/anthropics/skills`)
  2. Pilot Space fetches repo's `skills/` directory listing via GitHub API
  3. Admin sees list of available skills in the repo — selects which to install
  4. SKILL.md content is **auto-wired** immediately on install
  5. MCP registration and action button definitions from plugin **require admin confirmation** before wiring
- When GitHub is unreachable: block the marketplace with a clear error message (no cached/stale data fallback)

### References Storage
- References stored as **JSONB column** `references: [{filename: string, content: string}]` on the installed plugin DB record
- No separate PluginReference table
- References injected as Claude Agent SDK sandbox skills at agent init time — researcher MUST investigate Claude Agent SDK `skills` parameter for correct injection pattern

### Version Management
- Version = **Git commit SHA** recorded at install time (no semver, no tags required)
- "Update available" = current HEAD SHA of the source repo differs from the installed SHA
- Surfaced as: badge on the Settings → Plugins nav area + orange "Update available" chip on the plugin card
- Admin clicks Update → always overwrites with upstream content (no diff, no warning about local customizations)
- Update check: **on-demand** when admin opens the Plugins page, results cached 5 minutes to avoid GitHub rate limits

### Private Plugin Authoring
- Same install flow as public plugins — admin provides a **private GitHub repo URL**
- GitHub PAT stored per-workspace: encrypted with AES-256-GCM using existing `encrypt_api_key()` pattern (same as BYOK API keys)
- PAT stored once in Settings → Plugins "GitHub Access" section; used for all private plugin installs in that workspace
- Private plugins are **workspace-isolated** — no cross-workspace sharing

### New Workspace Seeding
- New workspaces are seeded with default official plugins at creation time
- Seeding = auto-installing a pre-configured list of plugins from `anthropics/skills` (or similar official repo) using a system-level GitHub token
- No manual setup required

### Claude's Discretion
- Exact DB table/column names for the plugin install record
- Caching mechanism for the 5-minute update check results
- GitHub API rate limit handling (retry/backoff strategy)
- Exact badge/chip visual styling (follow existing codebase patterns)
- Error message copy for GitHub connectivity failures

</decisions>

<specifics>
## Specific Ideas

- Reference model: follow `anthropics/skills` repo layout exactly (https://github.com/anthropics/skills) — researcher to confirm exact structure
- Install UX should feel like Claude Code's Skills panel: browse → click → install in one motion
- "Add plugin" = paste GitHub repo URL, then pick skills from the list — same whether public or private
- Claude Agent SDK sandbox skills pattern must be used for injecting SKILL.md + references at agent init

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `encrypt_api_key()` / `decrypt_api_key()`: existing AES-256-GCM helpers — use for GitHub PAT storage
- `WorkspaceRoleSkill` model (Phase 16): workspace-scoped skill content with `role_type`, `skill_content`, `is_active` — installed plugins will create/update these records
- `RoleTemplate` model: `version` int field already exists — similar versioning concept
- `role_skill_materializer.py`: existing skill injection into AI agent — understand this before adding plugin skill injection
- `mcp-servers-settings-page.tsx`: existing MCP settings page — model the GitHub credential UX after this pattern
- Skills settings page at `/[workspaceSlug]/skills`: extend this page with a Plugins section
- BYOK API key settings: existing pattern for per-workspace secret storage and display

### Established Patterns
- BYOK pattern: workspace-scoped encrypted secrets — apply to GitHub PAT
- MCP server registration flow: credential input → test → save — apply to GitHub repo + PAT input
- TanStack Query: existing data fetching pattern for settings pages
- MobX stores: existing pattern for AI settings — create PluginsStore following same pattern

### Integration Points
- `role_skill_materializer.py`: agent init must load installed plugin skills (SKILL.md + references) using Claude Agent SDK `skills` parameter
- Workspace creation flow (Phase 12 onboarding): add plugin seeding step after workspace is created
- Settings layout: extend sidebar nav to show update badge on Plugins section
- GitHub API: new service needed for fetching repo directory listing, file contents, and HEAD SHA

</code_context>

<deferred>
## Deferred Ideas

- Community plugin publishing (submitting plugins to a Pilot Space-hosted registry) — separate phase
- Org-level shared plugin registry (private plugins shared across multiple workspaces) — requires org data model
- Built-in SKILL.md editor / create plugin without GitHub — future phase
- Plugin analytics (which skills are used most, performance metrics) — future phase

</deferred>

---

*Phase: 19-skill-registry-and-plugin-system*
*Context gathered: 2026-03-10*
