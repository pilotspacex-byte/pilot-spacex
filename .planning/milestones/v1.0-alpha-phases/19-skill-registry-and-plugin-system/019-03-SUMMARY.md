---
phase: 19-skill-registry-and-plugin-system
plan: 03
subsystem: api
tags: [fastapi, httpx, github-api, plugin-system, redis-cache, skill-materializer]

requires:
  - phase: 019-skill-registry-and-plugin-system
    provides: "WorkspacePlugin + WorkspaceGithubCredential models, migration 074, repositories"
provides:
  - "GitHubPluginService for browsing/fetching skills from GitHub repos"
  - "InstallPluginService for install/update/uninstall plugin lifecycle"
  - "SeedPluginsService for seeding new workspaces with default plugins"
  - "7 REST endpoints for plugin CRUD, browse, update check, credential"
  - "materialize_plugin_skills() for agent sandbox injection"
  - "Workspace creation seeding hook via asyncio.create_task"
affects: [019-04]

tech-stack:
  added: []
  patterns: [github-contents-api, redis-sha-cache, plugin-skill-materializer, fire-and-forget-seed]

key-files:
  created:
    - backend/src/pilot_space/integrations/github/plugin_service.py
    - backend/src/pilot_space/api/v1/schemas/workspace_plugin.py
    - backend/src/pilot_space/application/services/workspace_plugin/__init__.py
    - backend/src/pilot_space/application/services/workspace_plugin/install_plugin_service.py
    - backend/src/pilot_space/application/services/workspace_plugin/seed_plugins_service.py
    - backend/src/pilot_space/api/v1/routers/workspace_plugins.py
    - backend/tests/unit/integrations/test_github_plugin_service.py
  modified:
    - backend/src/pilot_space/ai/agents/role_skill_materializer.py
    - backend/src/pilot_space/main.py
    - backend/src/pilot_space/api/v1/routers/workspaces.py

key-decisions:
  - "GitHubPluginService tries reference/ then references/ for compatibility with both conventions"
  - "materialize_plugin_skills called from inside materialize_role_skills -- no pilotspace_agent.py changes needed"
  - "Router uses direct instantiation pattern (not DI) -- follows SCIM/related-issues convention"
  - "Workspace seeding uses asyncio.create_task fire-and-forget -- non-blocking, non-fatal"
  - "Plugin install sets is_active=True immediately -- SKILL.md auto-wired per CONTEXT.md"
  - "MCP tools and action buttons stored but NOT wired -- deferred to Phase 17"

patterns-established:
  - "GitHub Contents API integration: httpx-based service with mock transport testing"
  - "Plugin skill materializer: plugin-{name}/ prefix convention with reference/ subdirectory"
  - "Redis SHA cache: 5-min TTL per (workspace, repo) for update check deduplication"

requirements-completed: [SKRG-01, SKRG-02, SKRG-03, SKRG-04, SKRG-05]

duration: 15min
completed: 2026-03-10
---

# Phase 19 Plan 03: Backend Services and REST API Summary

**GitHubPluginService + InstallPluginService + SeedPluginsService + 7-endpoint REST router + plugin skill materializer wiring**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-10T15:09:35Z
- **Completed:** 2026-03-10T15:25:18Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- GitHubPluginService with httpx async client for list_skills, fetch_skill_content, get_head_sha
- InstallPluginService for install (auto-wire), update (overwrite), and uninstall (soft-delete)
- SeedPluginsService seeds mcp-builder + claude-api from anthropics/skills on workspace creation
- 7 REST endpoints on /workspaces/{id}/plugins with admin auth, Redis cache, PAT management
- materialize_plugin_skills() integrated into role_skill_materializer.py (318 lines, well under 700)
- pilotspace_agent.py unchanged at 698 lines -- no modifications needed
- 30 unit tests covering all services, endpoints, and error paths

## Task Commits

Each task was committed atomically:

1. **Task 1: GitHubPluginService + Pydantic schemas** - `b53c9a3e` (feat)
2. **Task 2: InstallPluginService + SeedPluginsService + materializer** - `0433e036` (feat)
3. **Task 3: REST router + workspace creation seeding hook** - `e8571d99` (feat)

## Files Created/Modified
- `backend/src/pilot_space/integrations/github/plugin_service.py` - GitHubPluginService, parse_github_url, SkillContent/SkillMeta dataclasses, PluginRepoError/PluginRateLimitError
- `backend/src/pilot_space/api/v1/schemas/workspace_plugin.py` - Pydantic v2 schemas for all plugin endpoints
- `backend/src/pilot_space/application/services/workspace_plugin/install_plugin_service.py` - Install, update, uninstall lifecycle
- `backend/src/pilot_space/application/services/workspace_plugin/seed_plugins_service.py` - Default plugin seeding with GITHUB_TOKEN
- `backend/src/pilot_space/api/v1/routers/workspace_plugins.py` - 7 REST endpoints with admin auth
- `backend/src/pilot_space/ai/agents/role_skill_materializer.py` - Extended with materialize_plugin_skills + cleanup
- `backend/src/pilot_space/main.py` - Router registration
- `backend/src/pilot_space/api/v1/routers/workspaces.py` - Seeding hook in create_workspace

## Decisions Made
- GitHubPluginService tries `reference/` then `references/` for subdirectory fallback (anthropics/skills uses singular)
- materialize_plugin_skills called internally from materialize_role_skills -- pilotspace_agent.py stays untouched at 698 lines
- Router uses direct instantiation (not DI container) -- consistent with SCIM, related-issues, workspace-role-skills patterns
- SeedPluginsService skips silently when GITHUB_TOKEN missing (log + return, no exception)
- Plugin install sets is_active=True immediately (auto-wire SKILL.md per CONTEXT.md decision)
- MCP tool bindings and action button definitions stored in plugin record but NOT wired (Phase 17 prerequisite)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit ruff-format reformatted files on first commit attempt -- resolved by re-staging formatted files
- Router tests required FastAPI dependency overrides for WorkspaceId, DbSession, CurrentUserId -- used standard override pattern

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend complete -- plugins can be browsed, installed, version-checked, materialized, and seeded
- Ready for Plan 04 (frontend UI: settings page, plugin cards, store)
- Migration 074 must be applied (`alembic upgrade head`) before using endpoints against real DB

---
*Phase: 19-skill-registry-and-plugin-system*
*Completed: 2026-03-10*
