---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Completed 14-03-PLAN.md - MCP server API router and agent hot-load wiring
last_updated: "2026-03-10T02:53:55.619Z"
last_activity: "2026-03-09 — 13-03 complete: generalized ProviderStatusCard, CustomProviderForm, AISettingsStore.loadModels (AIPR-01, AIPR-02, AIPR-05)"
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 11
  completed_plans: 10
  percent: 23
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** v1.0-alpha — Pre-Production Launch

## Current Position

Phase: Phase 13 — AI Provider Registry + Model Selection (in progress)
Plan: 3/?
Status: 13-03 complete — generalized ProviderStatusCard, CustomProviderForm, AISettingsStore.loadModels
Last activity: 2026-03-09 — 13-03 complete: generalized ProviderStatusCard, CustomProviderForm, AISettingsStore.loadModels (AIPR-01, AIPR-02, AIPR-05)

Progress: [██░░░░░░░░] 23%

## Milestone: v1.0-alpha

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 12. Onboarding & First-Run UX | No blank screen on sign-up; guided onboarding | ONBD-01..05, BUG-01, BUG-02, WS-01, WS-02 | Not started |
| 13. AI Provider Registry + Model Selection | Multi-provider BYOK + per-session model picker | AIPR-01..05, CHAT-01..03 | Not started |
| 14. Remote MCP Server Management | Register/auth/status + PilotSpaceAgent hot-load | MCP-01..06 | Not started |
| 15. Related Issues | Semantic suggestions + manual linking | RELISS-01..04 | Not started |
| 16. Workspace Role Skills | Admin-generated role skills + inheritance | WRSKL-01..04 | Not started |
| 17. Skill Action Buttons | Custom issue-page buttons bound to skills/MCP | SKBTN-01..04 | Not started |
| 18. Tech Debt Closure | OIDC E2E, MCP approval, xfail tests, key rotation | DEBT-01..04 | Not started |

## Performance Metrics

**Velocity (v1.0 history):**
- Total plans completed: 46
- Average duration: ~27 min
- Total execution time: ~20.7 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 Identity & Access | 6/9 | ~165 min | ~27 min |
| 02 Compliance & Audit | 5/5 | ~144 min | ~29 min |
| 03 Multi-Tenant Isolation | 8/8 | ~111 min | ~14 min |
| 04 AI Governance | 10/10 | ~355 min | ~36 min |
| 05 Operational Readiness | 7/7 | ~56 min | ~8 min |
| 06 Wire Rate Limiting | 1/1 | 12 min | 12 min |
| 07 Wire Storage Quota | 2/2 | 28 min | 14 min |
| 08 Fix SSO Integration | 1/1 | 11 min | 11 min |
| 09 Login Audit Events | 1/1 | 7 min | 7 min |
| 10 Wire Audit Trail | 1/1 | 90 min | 90 min |
| 11 Fix Rate Limiting | 1/1 | 45 min | 45 min |

*Updated after each plan completion*
| Phase 12-onboarding-first-run-ux P01 | 25 | 3 tasks | 4 files |
| Phase 13-ai-provider-registry-model-selection P02 | 26 | 2 tasks | 5 files |
| Phase 13-ai-provider-registry-model-selection P04 | 30 | 2 tasks | 6 files |
| Phase 14-remote-mcp-server-management P01 | 18 | 2 tasks | 6 files |
| Phase 14-remote-mcp-server-management P02 | 18 | 2 tasks | 4 files |
| Phase 14-remote-mcp-server-management P03 | 12 | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- SSO via Supabase Auth PKCE — avoids building custom SAML parser; Supabase handles provider handshake (pending validation)
- AI approval policies per-role — hardcoded DD-003 thresholds must become configurable per workspace/role (Phase 4)
- BYOK enforcement — env fallback to ANTHROPIC_API_KEY must be removed in Phase 4 (currently violates billing model)
- WorkspaceSession uses own-rows RLS (user_id = current_user) rather than workspace isolation — sessions are private; admins use service_role for force-terminate (01-01)
- custom_roles RLS uses workspace_members subquery join — same pattern as graph_nodes, isolates per workspace without per-user policy rows (01-01)
- is_active added to workspace_members not via soft_delete — SCIM deactivation must be reversible without touching is_deleted semantics (01-01)
- Test scaffolds use xfail(strict=False) not skip — xfail runs the test body and reports XFAIL/XPASS, giving better visibility when implementation begins (01-01)
- ScimService uses factory function pattern not DI container — avoids complex wiring for a service needing custom per-request auth context (01-06)
- SCIM routes bypass JWT middleware via is_public_route() — SCIM uses workspace bearer token, not Supabase JWT (01-06)
- Deprovision = is_active=False on WorkspaceMember — data preserved; deprovisioned check in SessionRecordingMiddleware fails open on DB error (01-06)
- SessionRecordingMiddleware uses lazy-init for redis/session_factory from app.state.container — enables add_middleware at module load time before lifespan (01-04)
- Sessions router instantiates SessionService directly (SCIM pattern) — avoids @inject DI wiring for a service with external client dependencies (01-04)
- WorkspaceSessionRepository.get_session_by_id not get_by_id — avoids BaseRepository.get_by_id signature override incompatibility (01-04)
- [Phase 01-identity-and-access]: Custom role precedence: custom_role_id set → use custom permissions; NULL → fall back to built-in WorkspaceRole
- [Phase 01-identity-and-access]: WorkspaceRole enum UPPERCASE vs BUILTIN_ROLE_PERMISSIONS lowercase — normalized via .lower() in check_permission
- [Phase 02-compliance-and-audit]: AuditLog uses Base+TimestampMixin+WorkspaceScopedMixin (not WorkspaceScopedModel) to exclude SoftDeleteMixin — audit records are immutable
- [Phase 02-compliance-and-audit]: pg_cron bypass via app.audit_purge session variable — BEFORE trigger checks current_setting, purge function sets/resets it around DELETE
- [Phase 03-multi-tenant-isolation]: Migration 066 downgrade() is a no-op — RLS policies always required UPPERCASE; reverting to lowercase would break isolation
- [Phase 04-ai-governance]: async ApprovalService with four-tier priority: ALWAYS_REQUIRE → OWNER shortcut → DB policy row → level fallback
- [Phase 04-ai-governance]: AINotConfiguredError in ai/exceptions.py with 503 http_status — workspace calls raise immediately, no env fallback
- [Phase 10-wire-audit-trail]: audit_log_repository is providers.Factory (not Singleton) — audit writes need fresh AsyncSession per request
- [Phase 11-fix-rate-limiting-architecture]: RateLimitMiddleware lazy _resolve_redis(request) reads container.redis_client().client on first dispatch
- [Phase 12-onboarding-first-run-ux]: WorkspaceContext is authoritative workspaceId source — WorkspaceGuard resolves workspace from API before rendering, UUID always available via context
- [Phase 12-onboarding-first-run-ux]: Auto-create workspace uses email prefix + 4-char random suffix slug; retries once on 409, falls back to manual form on double failure
- [Phase 12-onboarding-first-run-ux]: supabase.auth.getUser() used directly in app/page.tsx (not via AuthProvider) to avoid expanding AuthProvider interface
- [Phase 12-onboarding-first-run-ux]: ApiKeySetupStep renders inline (no navigation) — removes context switch from onboarding flow; onNavigateToSettings fallback available for users who need full settings
- [Phase 12-onboarding-first-run-ux]: STEP_SETTINGS_PATH map in OnboardingChecklist — avoids threading workspaceSlug through OnboardingStepItem just for href construction; checklist owns the href composition
- [Phase 12-onboarding-first-run-ux]: vitest.config.ts env stubs for NEXT_PUBLIC_SUPABASE_URL — all unit tests were blocked without the var; stubs avoid requiring a live Supabase in CI
- [Phase 12-onboarding-first-run-ux]: saveLastWorkspacePath filters /settings/ paths — workspace switch lands on last non-settings page, not inside another workspace's settings
- [Phase 12-onboarding-first-run-ux]: getLastWorkspacePath returns null on failure; callers use ?? to fall back to workspace root without branching on empty string
- [Phase 12-onboarding-first-run-ux]: Pathname tracking in WorkspaceSlugLayout useEffect (client-side, co-located with workspace context) rather than middleware
- [Phase 13-ai-provider-registry-model-selection]: module-level imports in model_listing.py for AIConfigurationRepository and decrypt_api_key — enables unittest.mock.patch with simple module path; lazy imports don't create module attributes for patching
- [Phase 13-ai-provider-registry-model-selection]: ModelListingService uses its own _google_model_listing_lock — avoids importing _google_api_lock private attr from router (reportPrivateUsage)
- [Phase 13-ai-provider-registry-model-selection]: Anthropic model listing returns hardcoded fallback — models.list() requires beta header not in stable SDK; is_selectable=True since key is valid
- [Phase 13-ai-provider-registry-model-selection]: base_url required for custom provider via model_validator(mode=after) on AIConfigurationCreate — raises ValidationError before reaching DB
- [Phase 13-ai-provider-registry-model-selection]: PROVIDER_DISPLAY_NAMES lookup table keyed by string — avoids switch statement, trivially extensible for future providers
- [Phase 13-ai-provider-registry-model-selection]: BUILT_IN_PROVIDERS const array in ai-settings-page — 5 provider cards rendered via map(), no per-provider JSX duplication
- [Phase 13-ai-provider-registry-model-selection]: ProviderModelItem exported from AISettingsStore — plan 04 model picker imports from single canonical location
- [Phase 13-ai-provider-registry-model-selection]: loadModels() uses apiClient.get directly (not aiApi) — models endpoint is a different resource class than workspace AI settings
- [Phase 13-ai-provider-registry-model-selection]: resolve_model_override uses lazy imports to avoid circular dependency with AIConfigurationRepository
- [Phase 13-ai-provider-registry-model-selection]: self._resolved_model set on agent instance in stream() before _get_api_key — no signature change to _get_api_key needed
- [Phase 13-ai-provider-registry-model-selection]: Model override fallback is always None on any error — BYOK invariant preserved for workspace requests
- [Phase 13-ai-provider-registry-model-selection]: ModelSelector returns null when availableModels is empty — no layout shift in ChatHeader when no providers configured
- [Phase 13-ai-provider-registry-model-selection]: Per-workspace localStorage key chat_model_{workspaceId} — model selection scoped to workspace, not global session
- [Phase 13-ai-provider-registry-model-selection]: model_override is undefined (not null) when no model selected — field omitted from JSON body, no breaking change for workspaces without selection
- [Phase 14-remote-mcp-server-management]: xfail stubs with function-local imports: prevents import failure from breaking whole test file when implementation modules are absent (14-01)
- [Phase 14-remote-mcp-server-management]: it.todo() for frontend Wave 0 stubs: Vitest pending state communicates intent-to-implement better than it.skip() (14-01)
- [Phase 14-remote-mcp-server-management]: WorkspaceMcpServerRepository uses get_by_workspace_and_id not get_by_id override — avoids pyright incompatible method override (entity_id vs server_id parameter name)
- [Phase 14-remote-mcp-server-management]: WorkspaceMcpServerUpdate schema added in 14-02 — Plan 03 PATCH endpoint needs it; added proactively to avoid deviation in Plan 03
- [Phase 14-remote-mcp-server-management]: encrypt_api_key() takes one argument (no master_secret) - uses global EncryptionService singleton; plan interface doc was incorrect
- [Phase 14-remote-mcp-server-management]: MCP server Pydantic schemas inline in router file - avoids separate schema file, stays under 700-line limit
- [Phase 14-remote-mcp-server-management]: _load_remote_mcp_servers uses pyright ignore[reportUnusedFunction] + caller type: ignore[reportPrivateUsage] - underscore prefix is intentional shared-internal convention

### Pending Todos

None.

### Blockers/Concerns

- CONCERNS: Several files at/near 700-line limit (dependencies.py, pilotspace_agent.py, ai_chat.py) — new Phase 12-18 code must go into new modules, not extend these files
- CONCERNS: Phase 17 (Skill Action Buttons) depends on both Phase 14 (MCP tools available) AND Phase 16 (workspace role skills available) — do not plan Phase 17 before both are complete
- CONCERNS: DEBT-02 (MCP approval wiring) requires Phase 14 MCP servers to exist — schedule Phase 18 after Phase 14

## Session Continuity

Last session: 2026-03-10T02:53:55.617Z
Stopped at: Completed 14-03-PLAN.md - MCP server API router and agent hot-load wiring
Resume file: None
Next action: Phase 13 in progress. Plans 13-01, 13-02, 13-03 complete. Continue with 13-04 (model picker chat UI).
