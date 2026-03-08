---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: Completed 04-ai-governance-06-PLAN.md
last_updated: "2026-03-08T10:39:34.789Z"
last_activity: 2026-03-08 — Completed plan 03-04 (super-admin operator dashboard backend)
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 30
  completed_plans: 28
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-07)

**Core value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control.
**Current focus:** Phase 1 — Identity & Access

## Current Position

Phase: 3 of 5 (Multi-Tenant Isolation) — IN PROGRESS
Plan: 1 of 7 in current phase (03-01 complete)
Status: Plan 03-04 complete — ready for 03-05
Last activity: 2026-03-08 — Completed plan 03-04 (super-admin operator dashboard backend)

Progress: [███████░░░] 71%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: ~27 min
- Total execution time: ~2.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 Identity & Access | 6/9 | ~165 min | ~27 min |

**Recent Trend:**
- Last 5 plans: 01-02 (SSO), 01-03 (RBAC), 01-04 (Audit Log), 01-05 (Session Mgmt), 01-06 (SCIM 2.0)
- Trend: consistent 25-35 min/plan

*Updated after each plan completion*
| Phase 01-identity-and-access P03 | 45 | 2 tasks | 14 files |
| Phase 01-identity-and-access P05 | 28 | 2 tasks | 5 files |
| Phase 01-identity-and-access P07 | 35 | 2 tasks | 11 files |
| Phase 01-identity-and-access P08 | 12 | 1 task | 7 files |
| Phase 01-identity-and-access P09 | 7 | 2 tasks | 9 files |
| Phase 02-compliance-and-audit P01 | 27 | 2 tasks | 12 files |
| Phase 02-compliance-and-audit P02 | 90 | 2 tasks | 14 files |
| Phase 02-compliance-and-audit P03 | 10 | 1 task | 5 files |
| Phase 02-compliance-and-audit P04 | 10 | 2 tasks | 6 files |
| Phase 02-compliance-and-audit P05 | 7 | 2 tasks | 6 files |
| Phase 03-multi-tenant-isolation P01 | 11 | 2 tasks | 6 files |
| Phase 03-multi-tenant-isolation P02 | 20 | 2 tasks | 11 files |
| Phase 03-multi-tenant-isolation PP03 | 35 | 2 tasks | 7 files |
| Phase 03-multi-tenant-isolation P04 | 9 | 2 tasks | 6 files |
| Phase 03-multi-tenant-isolation P05 | 3 | 2 tasks | 5 files |
| Phase 03-multi-tenant-isolation P06 | 4 | 2 tasks | 5 files |
| Phase 03-multi-tenant-isolation P07 | 18 | 2 tasks | 5 files |
| Phase 03-multi-tenant-isolation P08 | 1 | 1 tasks | 1 files |
| Phase 04-ai-governance P01 | 7 | 2 tasks | 13 files |
| Phase 04-ai-governance P02 | 11 | 2 tasks | 12 files |
| Phase 04-ai-governance P03 | 7 | 2 tasks | 5 files |
| Phase 04-ai-governance P04 | 8 | 2 tasks | 8 files |
| Phase 04-ai-governance P05 | 25 | 2 tasks | 10 files |
| Phase 04-ai-governance P06 | 18 | 2 tasks | 4 files |

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
- [Phase 01-identity-and-access]: map_claims_to_role is @staticmethod — pure claim mapping logic, no DB access, easily unit testable
- [Phase 01-identity-and-access]: owner role cap in SSO mapping is silent (log + downgrade to admin) — prevents accidental privilege escalation via IdP misconfiguration
- [Phase 01-identity-and-access]: GET /auth/sso/check-login for pre-login enforcement check — idempotent, called before credentials are submitted
- [Phase 01-identity-and-access]: SsoSettingsPage uses plain React component (not observer()) — no MobX observables; TanStack Query covers all data needs
- [Phase 01-identity-and-access]: 409 conflict errors in useCreateRole/useUpdateRole bubble to callers for inline error display rather than toast
- [Phase 01-identity-and-access]: SecuritySettingsPage is plain React (no observer()) — no MobX observables; TanStack Query handles all data needs
- [Phase 01-identity-and-access]: Token reveal uses separate Dialog (not AlertDialog) — allows more content for copy UX
- [Phase 01-identity-and-access]: Terminate-all shown as inline "All" button per row — avoids extra expand/collapse complexity (YAGNI)
- [Phase 01-identity-and-access]: SSO button visible only when workspace_id is in URL query param — avoids showing SSO for non-SSO workspaces
- [Phase 01-identity-and-access]: Claims role application in auth callback is non-fatal — unmapped claims default to member on backend (graceful degradation)
- [Phase 01-identity-and-access]: MemberRoleBadge: data-testid role-badge-{role} for built-in, role-badge-custom for custom roles; unified component for all member list views
- [Phase 02-compliance-and-audit]: AuditLog uses Base+TimestampMixin+WorkspaceScopedMixin (not WorkspaceScopedModel) to exclude SoftDeleteMixin — audit records are immutable
- [Phase 02-compliance-and-audit]: pg_cron bypass via app.audit_purge session variable — BEFORE trigger checks current_setting, purge function sets/resets it around DELETE
- [Phase 02-compliance-and-audit]: Migration dollar-quoting: DO $outer$ with single-quoted cron command — nested $$ inside DO $$ causes PostgreSQL SyntaxError
- [Phase 02-compliance-and-audit]: AuditLogRepository is standalone (not extending BaseRepository) — avoids inheriting soft-delete methods on immutable records
- [Phase 02-compliance-and-audit]: Cursor pagination uses base64(JSON{ts,id}) keyset for O(1) page seeks on (created_at DESC, id DESC) index
- [Phase 02-compliance-and-audit]: All service audit writes non-fatal (try/except) — audit failures never interrupt primary write paths; write_audit_nonfatal() helper reduces boilerplate
- [Phase 02-compliance-and-audit]: delete_note_service.py drops Activity tracking — Activity.issue_id is a non-nullable FK; notes structurally incompatible with Activity model
- [Phase 02-compliance-and-audit]: AuditLogHook dual-mode injection: audit_repo for request-scoped use, session_factory for SDK lifecycle callbacks — keeps unit tests simple while enabling out-of-request writes
- [Phase 02-compliance-and-audit]: Private state captured as local closure vars to satisfy SLF001 ruff rule — avoids hook_self._xxx access from nested closures
- [Phase 02-compliance-and-audit]: list_for_export added to AuditLogRepository — full chronological export without cursor pagination for streaming CSV/JSON export
- [Phase 02-compliance-and-audit]: audit_router prefix /api/v1 not /api/v1/workspaces — routes already include /workspaces/{slug}/audit path, avoids double-prefix
- [Phase 02-compliance-and-audit]: Retention PATCH requires settings:manage (OWNER only) — data retention config is higher-privilege than settings:read (ADMIN+OWNER)
- [Phase 02-compliance-and-audit]: Streaming generators use Sequence[object] not list[object] — list is invariant in Python typing, Sequence is covariant, prevents pyright error on AuditLog assignment
- [Phase 02-compliance-and-audit]: AuditSettingsPage is plain React (no observer()) — consistent with all settings pages; TanStack Query handles data
- [Phase 02-compliance-and-audit]: useExportAuditLog returns triggerExport function not useMutation — export is imperative browser file download, not a server state mutation
- [Phase 02-compliance-and-audit]: Radix Select does not support empty string as value — used '_all_' sentinel for All options in action and resource_type selects
- [Phase 02-compliance-and-audit]: async streaming in AuditLogRepository uses plain async iteration (no yield_per) — yield_per incompatible with async SQLAlchemy streaming patterns
- [Phase 03-multi-tenant-isolation]: Migration 066 downgrade() is a no-op — RLS policies always required UPPERCASE; reverting to lowercase would break isolation
- [Phase 03-multi-tenant-isolation]: Isolation tests use pytestmark skipif(sqlite in DB_URL) at module level — cleaner than per-test decorators, matches PostgreSQL-only RLS pattern
- [Phase 03-multi-tenant-isolation]: test_isolation.py uses existing populated_db fixture — already provisions workspace_a and workspace_b with outsider cross-membership
- [Phase 03-multi-tenant-isolation]: Workspace encryption is opt-in: get_workspace_content_key() returns None for unconfigured workspaces; callers check before encrypting/decrypting
- [Phase 03-multi-tenant-isolation]: workspace_encryption_keys RLS intentionally omits user SELECT policy — encrypted key must never reach client via any API path
- [Phase 03-multi-tenant-isolation]: workspace_encryption router mounted at /api/v1/workspaces with full {workspace_slug}/encryption/* paths — FastAPI does not support path params in include_router prefix
- [Phase Phase 03-multi-tenant-isolation]: RateLimitMiddleware uses async_sessionmaker (not DI container) for DB fallback — avoids wiring complexity in middleware context, same SCIM pattern
- [Phase Phase 03-multi-tenant-isolation]: Workspace quota router extracted to workspace_quota.py — keeps both workspaces.py and workspace_quota.py under 700-line limit
- [Phase Phase 03-multi-tenant-isolation]: PATCH /settings/quota uses RedisDep for cache invalidation — consistent with ghost_text and issues_ai_context patterns
- [Phase 03-multi-tenant-isolation]: Admin router uses class-based _AdminSessionFactory (not global) — avoids PLW0603, maintains test patchability via patch()
- [Phase 03-multi-tenant-isolation]: HTTPBearer(auto_error=False) on admin routes — returns 401 with WWW-Authenticate header, not 403 (RFC 6750 compliant)
- [Phase 03-multi-tenant-isolation]: PILOT_SPACE_SUPER_ADMIN_TOKEN is SecretStr — masks in repr/logs/model_dump without custom filter; None disables super-admin access
- [Phase 03-multi-tenant-isolation]: EncryptionSettingsPage is plain React (no observer()) — consistent with all settings pages; TanStack Query handles all data
- [Phase 03-multi-tenant-isolation]: Non-owner members see read-only status card; Configure Key card hidden (not disabled) — cleaner UX, avoids confusion
- [Phase 03-multi-tenant-isolation]: Encryption verify result shown inline below input (not toast) — allows user to see result while key is still in the field
- [Phase 03-multi-tenant-isolation]: UsageSettingsPage is plain React (no observer()) — TanStack Query handles all quota data, consistent with all settings pages pattern
- [Phase 03-multi-tenant-isolation]: Storage bar color at 80%+/100% via CSS slot class override on Progress indicator — avoids custom progress component, stays within shadcn/ui primitives
- [Phase 03-multi-tenant-isolation]: AdminLayout is a plain div wrapper — root layout already provides html/body; nesting html inside html would produce invalid HTML
- [Phase 03-multi-tenant-isolation]: AdminDashboardPage is plain React (no observer()) — no MobX; consistent with all settings pages pattern
- [Phase 03-multi-tenant-isolation]: Admin token passed as explicit hook parameter — token state change triggers query key change and re-fetch automatically
- [Phase 03-multi-tenant-isolation]: flush() not commit() for test data — visible in same transaction, rolls back after test
- [Phase 03-multi-tenant-isolation]: Three primary isolation tests use module-level pytestmark skipif (not xfail) — clean skip signaling on SQLite
- [Phase 04-ai-governance]: Migration 069 uses ADD COLUMN IF NOT EXISTS — operation_type was already present in dev DB from outside alembic; idempotent migration avoids DuplicateColumn error
- [Phase 04-ai-governance]: workspace_ai_policy RLS: OWNER+ADMIN read (settings visible to admins), OWNER-only write (policy changes require owner authority)
- [Phase 04-ai-governance]: xfail stubs use empty bodies (not pass) per ruff PIE790 — async functions with only docstrings are valid Python and pass trivially as xpass
- [Phase 04-ai-governance]: async ApprovalService with four-tier priority: ALWAYS_REQUIRE → OWNER shortcut → DB policy row → level fallback
- [Phase 04-ai-governance]: AINotConfiguredError in ai/exceptions.py with 503 http_status — workspace calls raise immediately, no env fallback
- [Phase 04-ai-governance]: cost_tracker changed from providers.Callable(lambda:None) to providers.Factory(CostTracker) — must be positioned before referencing services in container class body
- [Phase 04-ai-governance]: actor_type=None default in list_filtered/list_for_export — preserves backward compatibility while enabling AI-specific audit filtering (AIGOV-03)
- [Phase 04-ai-governance]: Scoped test engine fixture creates only audit_log table — avoids SQLite failures from PostgreSQL-specific server_defaults in chat_attachments table
- [Phase 04-ai-governance]: ai_governance.py uses _resolve_workspace + check_permission (audit.py pattern) — verify_workspace_admin from ai_approvals.py uses WorkspaceId header context incompatible with slug-based routing
- [Phase 04-ai-governance]: ai_governance.py uses _resolve_workspace + check_permission (audit.py pattern) not verify_workspace_admin from ai_approvals.py
- [Phase 04-ai-governance]: Rollback dispatch stubs 501 pending 04-05 — plan referenced non-existent monolithic IssueService/NoteService; CQRS split services need payload mapping
- [Phase 04-ai-governance]: group_by query param uses Query(pattern=...) regex for 422 validation — by_feature field declared as None default on CostSummaryResponse
- [Phase 04-ai-governance]: useResolveApproval delegates to approvalsApi.approve/reject (not raw apiClient) — existing service maps backend flat format to PendingApproval interface
- [Phase 04-ai-governance]: Sidebar Approvals item uses badgeKey indirection — static nav constant, dynamic badge injection via badgeValues map at render time in observer Sidebar
- [Phase 04-ai-governance]: AI policy matrix optimistic updates: onMutate flips cell immediately, onError rolls back — avoids loading spinner flicker on Switch toggles
- [Phase 04-ai-governance]: AuditFilters.actor_type added as optional — backward-compatible; absence omits filter from API query
- [Phase 04-ai-governance]: By Feature tab uses lazy useQuery (enabled: activeTab === 'by_feature') — avoids unnecessary API fetch on dashboard mount
- [Phase 04-ai-governance]: Horizontal BarChart for By Feature tab (not PieChart) — ranked list reads better for 5-10 operation_type labels with long names

### Pending Todos

- POST /workspaces/{slug}/settings/scim-token admin endpoint not yet implemented (ScimService.generate_scim_token exists, router endpoint missing)

### Blockers/Concerns

- CONCERNS: Several files at/near 700-line limit (dependencies.py, pilotspace_agent.py, ai_chat.py) — new Phase 1-4 code will need to be added to new modules, not extended from these files
- CONCERNS: RLS enum case mismatch (UPPERCASE in policies vs lowercase in some migrations) — must be resolved before Phase 3 isolation verification
- CONCERNS: CostTracker/ApprovalService singletons with session=None silently drop cost/approval records — must be fixed in Phase 4 before AI governance wiring
- CONCERNS: BYOK env fallback exposes platform key — blocking requirement for AIGOV-05
- CONCERNS: SessionRecordingMiddleware deprovisioned check adds 1 DB query per authenticated workspace request — consider Redis caching if latency becomes an issue

## Session Continuity

Last session: 2026-03-08T10:39:34.787Z
Stopped at: Completed 04-ai-governance-06-PLAN.md
Resume file: None
