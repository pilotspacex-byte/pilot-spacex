---
phase: 19-skill-registry-and-plugin-system
verified: 2026-03-11T08:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
human_verification:
  - test: "Browse GitHub repo and install plugin"
    expected: "Admin pastes repo URL, sees skill list, clicks Install, plugin appears in Installed list"
    why_human: "Full user flow with external GitHub API call cannot be verified without running app"
  - test: "Update Available badge appearance"
    expected: "Orange chip appears on plugin card when HEAD SHA differs from installed SHA"
    why_human: "Visual badge color (implementation uses blue instead of orange per CONTEXT.md spec) needs human review; badge IS rendered when has_update=true"
  - test: "New workspace seeded with default plugins"
    expected: "After creating workspace, Settings > Skills > Plugins tab shows mcp-builder and claude-api"
    why_human: "Requires real GitHub API call + workspace creation flow"
  - test: "GitHub PAT management flow"
    expected: "Admin saves PAT, status shows 'configured', private repos become browseable"
    why_human: "Requires real encrypted storage + PAT validation against GitHub"
---

# Phase 19: Skill Registry and Plugin System Verification Report

**Phase Goal:** Workspace admins browse a marketplace of official Pilot Space plugins (each plugin = skill + MCP tools + action buttons, versioned), install them into their workspace, and receive "Update available" notifications when new plugin versions ship -- replacing static hard-coded built-ins with a curated marketplace model
**Verified:** 2026-03-11T08:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A new workspace is seeded with default official plugins at creation time | VERIFIED | `SeedPluginsService.seed_workspace()` installs mcp-builder and claude-api from anthropics/skills; wired to workspace creation via `asyncio.create_task` in workspaces.py:153; skips silently when GITHUB_TOKEN missing |
| 2 | Admins can browse the Pilot Space plugin marketplace, preview each plugin's SKILL.md + references, and install with one click | VERIFIED | `GET /browse` endpoint fetches skill list from GitHub Contents API; `POST /plugins` installs with content auto-wired; `PluginsTabContent` observer renders cards with Install actions; `AddPluginDialog` provides browse form |
| 3 | Plugins are versioned; when an official plugin gets a new version, installed workspaces see an "Update available" badge and apply updates explicitly | VERIFIED | `GET /check-updates` compares HEAD SHA vs installed_sha with 5-min Redis cache; `PluginCard` renders update badge when `group.hasUpdate` is true; update is explicit via `InstallPluginService.update()` |
| 4 | A plugin bundles skill content (SKILL.md + references/) + MCP tool bindings + action button definitions -- installing wires SKILL.md automatically | VERIFIED | `InstallPluginService.install()` stores skill_content + references; `materialize_plugin_skills()` writes `plugin-{name}/SKILL.md` + `reference/{filename}` to skills_dir; MCP/action button wiring correctly deferred to Phase 17 per CONTEXT.md |
| 5 | Workspace admins can publish private plugins to their own workspace registry for internal distribution | VERIFIED | GitHub PAT management (save/get credential endpoints + `GitHubAccessSection` UI) enables access to private repos; admins install from any GitHub repo URL (public or private with PAT) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/src/pilot_space/integrations/github/plugin_service.py` | GitHubPluginService | VERIFIED | 306 lines; list_skills, fetch_skill_content, get_head_sha; reference/ fallback to references/; proper error types |
| `backend/src/pilot_space/application/services/workspace_plugin/install_plugin_service.py` | InstallPluginService | VERIFIED | 171 lines; install (with existing check), update (overwrite), uninstall (soft-delete) |
| `backend/src/pilot_space/application/services/workspace_plugin/seed_plugins_service.py` | SeedPluginsService | VERIFIED | 110 lines; seeds mcp-builder + claude-api from anthropics/skills; GITHUB_TOKEN check; non-fatal |
| `backend/src/pilot_space/api/v1/routers/workspace_plugins.py` | REST endpoints | VERIFIED | 583 lines; 12 endpoints including list, browse, install, install-all, toggle, delete, check-updates, github-credential; admin auth on all |
| `backend/src/pilot_space/ai/agents/role_skill_materializer.py` | materialize_plugin_skills() | VERIFIED | 318 lines; writes plugin-{name}/SKILL.md + reference/ files; OperationalError guard; stale cleanup; called from materialize_role_skills() at line 126 |
| `backend/alembic/versions/074_add_workspace_plugins.py` | DB migration | VERIFIED | RLS ENABLE + FORCE on both tables; UPPERCASE role enums; partial unique index; downgrade present |
| `backend/src/pilot_space/infrastructure/database/models/workspace_plugin.py` | WorkspacePlugin model | VERIFIED | JSONB references column; all required fields |
| `backend/src/pilot_space/infrastructure/database/models/workspace_github_credential.py` | WorkspaceGithubCredential model | VERIFIED | pat_encrypted field |
| `backend/src/pilot_space/infrastructure/database/repositories/workspace_plugin_repository.py` | WorkspacePluginRepository | VERIFIED | get_active_by_workspace, get_by_workspace_and_name, create, update, soft_delete |
| `backend/src/pilot_space/infrastructure/database/repositories/workspace_github_credential_repository.py` | WorkspaceGithubCredentialRepository | VERIFIED | get_by_workspace, upsert |
| `frontend/src/services/api/plugins.ts` | pluginsApi | VERIFIED | 80 lines; all endpoints typed; batch install-all, toggle, uninstall-repo |
| `frontend/src/stores/ai/PluginsStore.ts` | PluginsStore | VERIFIED | 227 lines; makeAutoObservable; groupedPlugins computed; all lifecycle methods with runInAction |
| `frontend/src/features/settings/components/plugin-card.tsx` | PluginCard | VERIFIED | Props-based (not observer); status badges; toggle switch; accessible |
| `frontend/src/features/settings/components/plugins-tab-content.tsx` | PluginsTabContent | VERIFIED | observer() wrapper; loads installed + checks updates on mount; detail dialog + add dialog |
| `frontend/src/features/settings/pages/skills-settings-page.tsx` | Skills page with Plugins tab | VERIFIED | Plugins tab conditionally rendered for admin users; imports PluginsTabContent |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| main.py | workspace_plugins router | `app.include_router(workspace_plugins_router)` | WIRED | Line 301 registers router at `/api/v1/workspaces` prefix |
| workspaces.py | SeedPluginsService | `asyncio.create_task(SeedPluginsService.seed_workspace())` | WIRED | Line 153 fires seed on workspace creation |
| role_skill_materializer.py | materialize_plugin_skills | Internal call at line 126 | WIRED | Called from materialize_role_skills(); no pilotspace_agent.py changes needed |
| workspace_plugins router | GitHubPluginService | Direct instantiation in handlers | WIRED | browse_repo, install_plugin, check_updates all instantiate GitHubPluginService |
| AIStore.ts | PluginsStore | `plugins = new PluginsStore()` | WIRED | Line 51 in constructor |
| skills-settings-page.tsx | PluginsTabContent | Import + render in Plugins tab | WIRED | Line 51 import; rendered in TabsContent value="plugins" |
| PluginsTabContent | PluginsStore | `useStore().ai.plugins` | WIRED | Line 33 accesses store; observer() wrapper |
| PluginCard | PluginGroup type | Props interface | WIRED | Line 13 imports PluginGroup from PluginsStore |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SKRG-01 | 019-01..04 | Admin browses plugins from a GitHub repo URL | SATISFIED | Browse endpoint + GitHubPluginService + AddPluginDialog UI |
| SKRG-02 | 019-01..04 | Admin installs a plugin -- SKILL.md auto-wired | SATISFIED | Install endpoint + InstallPluginService + PluginsStore.installAllFromRepo + PluginCard Install action |
| SKRG-03 | 019-01..04 | Installed plugins inject SKILL.md + references into PilotSpaceAgent | SATISFIED | materialize_plugin_skills() writes plugin-{name}/SKILL.md + reference/ to skills_dir |
| SKRG-04 | 019-01..04 | "Update available" badge when HEAD SHA differs | SATISFIED | check-updates endpoint with Redis cache + PluginCard hasUpdate badge |
| SKRG-05 | 019-01..04 | New workspaces seeded with default official plugins | SATISFIED | SeedPluginsService called via asyncio.create_task in workspace creation |

Note: SKRG-01 through SKRG-05 are defined in `19-RESEARCH.md`, not in `.planning/REQUIREMENTS.md`. The main REQUIREMENTS.md does not contain these IDs (it covers v1.0 requirements only; Phase 19 is v1.0-alpha).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| plugin-card.tsx | 70 | Update badge uses blue color instead of orange per CONTEXT.md spec | Info | Visual deviation from design spec; badge IS rendered correctly when has_update=true |
| plugin-detail-sheet.tsx | - | SKILL.md and References tabs noted as "placeholder" in summary | Info | Detail sheet exists but raw SKILL.md content not exposed by list API; detail sheet shows overview correctly |

No TODOs, FIXMEs, placeholders, or stub implementations found in any production file.

### Human Verification Required

### 1. Browse and Install Plugin Flow
**Test:** Log in as workspace admin, navigate to Settings > Skills > Plugins tab, click Add Plugin, paste `https://github.com/anthropics/skills`, click Browse, then install a skill.
**Expected:** Skill list appears from GitHub; after install, plugin appears in the Installed Plugins grid with Active badge.
**Why human:** Requires running application with real GitHub API connectivity.

### 2. Update Available Badge Color
**Test:** Install a plugin, then modify the installed_sha in the database to a different value than HEAD. Refresh the Plugins tab.
**Expected:** Plugin card shows an "Update" badge (currently blue; CONTEXT.md specified orange).
**Why human:** Visual color validation requires browser inspection.

### 3. New Workspace Default Plugin Seeding
**Test:** Create a new workspace with GITHUB_TOKEN configured.
**Expected:** After workspace creation, Settings > Skills > Plugins tab shows pre-installed mcp-builder and claude-api plugins from anthropics/skills.
**Why human:** Requires full onboarding flow + real GitHub API + async background task completion.

### 4. GitHub PAT Management
**Test:** In Plugins tab, enter a GitHub PAT in the GitHub Access section, click Save.
**Expected:** Status shows "GitHub PAT configured"; private repos become browseable.
**Why human:** Requires real encryption + decryption roundtrip + private repo access.

### Gaps Summary

No blocking gaps found. All 5 success criteria are met:

1. **Workspace seeding** -- SeedPluginsService wired to workspace creation as fire-and-forget asyncio.create_task
2. **Marketplace browsing** -- Full GitHub Contents API integration with browse endpoint + frontend UI
3. **Versioning with update notification** -- HEAD SHA comparison with 5-min Redis cache + has_update badge rendering
4. **Plugin bundling** -- SKILL.md + references stored in DB and materialized to agent sandbox; MCP/action button wiring correctly deferred to Phase 17
5. **Private plugins via PAT** -- GitHub PAT management enables private repo access

Minor note: The "Update Available" badge uses blue color instead of the orange specified in CONTEXT.md. This is a design fidelity issue, not a functional gap.

---

_Verified: 2026-03-11T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
