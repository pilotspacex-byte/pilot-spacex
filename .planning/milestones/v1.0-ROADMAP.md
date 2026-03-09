# Roadmap: Pilot Space — Enterprise Milestone

## Overview

The MVP is working: note canvas, issue management, cycles, AI PR review, and notifications are all live. This milestone closes the gap between "working product" and "enterprise-ready." Five phases take the platform from email/password-only auth to a fully auditable, governance-controlled, tenant-isolated system that can be self-hosted by a 50-500 developer engineering organization and handed to a compliance officer without embarrassment.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Identity & Access** - SSO, custom RBAC, session control, and SCIM provisioning so enterprise teams can use their existing identity provider (completed 2026-03-07)
- [x] **Phase 2: Compliance & Audit** - Immutable audit log covering every user and AI action, with export and retention controls (completed 2026-03-08)
- [x] **Phase 3: Multi-Tenant Isolation** - Verified data isolation, workspace encryption, rate limiting, and operator dashboard (completed 2026-03-08)
- [ ] **Phase 4: AI Governance** - Configurable approval policies, AI audit trail, rollback, strict BYOK enforcement, and cost visibility
- [x] **Phase 5: Operational Readiness** - Docker Compose guide, Helm chart, health checks, structured logging, backup tooling, and migration path (completed 2026-03-08)
- [x] **Phase 6: Wire Rate Limiting + SCIM Token** - Register RateLimitMiddleware and add SCIM token generation endpoint to close AUTH-07 and TENANT-03 rate limiting gaps (Gap Closure) (completed 2026-03-09)
- [x] **Phase 7: Wire Storage Quota Enforcement** - Call _check_storage_quota/_update_storage_usage on write paths to complete TENANT-03 storage quota gap (Gap Closure) (completed 2026-03-09)
- [x] **Phase 8: Fix SSO Integration** - Normalize backend SSO endpoints to workspace_slug, complete SAML JWT issuance, add frontend saml_provisioned handler (Gap Closure) (completed 2026-03-09)
- [x] **Phase 9: Login Audit Events** - Write user.login audit events in SAML and password auth paths (Gap Closure) (completed 2026-03-09)
- [x] **Phase 10: Wire Audit Trail** - Wire audit_log_repository into 10 DI service factories, fix SAML audit RLS context, and pass session_factory to PermissionAwareHookExecutor to fully satisfy AUDIT-01, AUDIT-02, and AIGOV-03 (Gap Closure) (completed 2026-03-09)
- [x] **Phase 11: Fix Rate Limiting Architecture** - Move RateLimitMiddleware registration to module level with lazy Redis accessor so TENANT-03 rate limiting is active at runtime (Gap Closure) (completed 2026-03-09)

## Phase Details

### Phase 1: Identity & Access
**Goal**: Enterprise admins can replace email/password auth with their corporate identity provider, define granular roles, and manage sessions — the security foundation everything else builds on
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07
**Success Criteria** (what must be TRUE):
  1. Admin can configure SAML 2.0 or OIDC SSO and have users log in successfully via their identity provider (Okta, Azure AD, or Google Workspace) without touching Pilot Space credentials
  2. Admin can force SSO-only mode — email/password login is blocked at the workspace level
  3. Users logging in via SSO receive the workspace role mapped from their identity provider claims (no manual role assignment required)
  4. Admin can create a custom role with specific per-resource permission grants and assign it to workspace members
  5. Admin can view all active sessions and force-terminate any individual session or all sessions for a user
  6. Admin can connect a SCIM 2.0 endpoint so new users are auto-provisioned and removed users are auto-deprovisioned
**Plans**: 9 plans

Plans:
- [ ] 01-01-PLAN.md — DB migration 064 (custom_roles, workspace_sessions tables) + test scaffolds for all AUTH requirements
- [ ] 01-02-PLAN.md — SAML 2.0 backend: SamlAuthProvider + SsoService + auth_sso.py router (AUTH-01)
- [ ] 01-03-PLAN.md — Custom RBAC backend: check_permission(), CustomRoleRepository, RbacService + custom_roles router (AUTH-05)
- [ ] 01-04-PLAN.md — Session management backend: recording middleware, force-terminate service + sessions router (AUTH-06)
- [ ] 01-05-PLAN.md — Role claim mapping + SSO enforcement tests: map_claims_to_role, /claim-role endpoint, AUTH-02/03/04 tests
- [ ] 01-06-PLAN.md — SCIM 2.0 backend: ScimService + /api/v1/scim/v2/ router + SCIM token generation (AUTH-07)
- [ ] 01-07-PLAN.md — SSO and RBAC settings pages: SsoSettingsPage, RolesSettingsPage + TanStack Query hooks (AUTH-01/02/04/05)
- [ ] 01-08-PLAN.md — Security settings page: sessions table + SCIM directory sync UI (AUTH-06/07)
- [ ] 01-09-PLAN.md — SSO login flow wire-up: login page SSO button, OIDC post-login claims, MemberRoleBadge (AUTH-01/02/03/04)

### Phase 2: Compliance & Audit
**Goal**: Every user and AI action leaves an immutable, queryable, exportable record that a compliance officer can use as evidence
**Depends on**: Phase 1
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06
**Success Criteria** (what must be TRUE):
  1. Every create/update/delete on any resource (including AI-generated ones) appears in the audit log with actor identity, timestamp, resource type, and a diff of what changed
  2. Every AI action appears in the audit log with the input sent, output received, model name, token cost, and AI rationale
  3. Admin can filter the audit log by actor, action type, resource type, and date range and see only matching entries
  4. Admin can export filtered audit log results as JSON or CSV and open the file in a spreadsheet tool
  5. Admin can set a retention window (e.g., 90 days) and confirm that entries older than the window are purged on schedule
  6. No user — including a workspace owner — can modify or delete any audit log entry via the API or admin UI
**Plans**: 5 plans

Plans:
- [ ] 02-01-PLAN.md — AuditLog model + migration 065 (table, trigger, RLS, pg_cron) + test scaffolds (AUDIT-01 through AUDIT-06)
- [ ] 02-02-PLAN.md — AuditLogRepository + service instrumentation: issues, notes, cycles, members, settings, custom roles (AUDIT-01)
- [ ] 02-03-PLAN.md — AI hook upgrade: AuditLogHook writes DB rows with full AI action metadata (AUDIT-02)
- [ ] 02-04-PLAN.md — Audit API: GET list (filtered, cursor-paged), GET export (streaming CSV/JSON), PATCH retention, immutability tests (AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06)
- [ ] 02-05-PLAN.md — Audit settings page: filter UI, read-only table, row expansion, export buttons, settings nav entry + human verification (AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06)

### Phase 3: Multi-Tenant Isolation
**Goal**: Workspace data is verifiably isolated at every layer, operators can configure encryption and quotas, and the self-hosted operator has a dashboard to monitor workspace health
**Depends on**: Phase 2
**Requirements**: TENANT-01, TENANT-02, TENANT-03, TENANT-04
**Success Criteria** (what must be TRUE):
  1. An authenticated user from workspace A cannot retrieve any data belonging to workspace B through any API endpoint, even when providing crafted workspace IDs
  2. Admin can upload a workspace-level encryption key and confirm that stored data is encrypted with their key (bring-your-own-key model)
  3. Admin can set per-workspace API rate limits and storage quotas, and requests exceeding those limits receive a 429 with a meaningful error
  4. Super-admin (self-hosted operator) can open an admin dashboard and see workspace health metrics, member activity, and usage stats across all workspaces
**Plans**: 8 plans

Plans:
- [x] 03-01-PLAN.md — Migration 066 (RLS enum case fix) + Phase 3 test scaffolds for all TENANT requirements (TENANT-01) (completed 2026-03-08)
- [ ] 03-02-PLAN.md — Workspace encryption backend: model + migration 067 + helpers + 4 API endpoints (TENANT-02)
- [ ] 03-03-PLAN.md — Per-workspace rate limits + storage quota enforcement + GET/PATCH quota API (TENANT-03)
- [ ] 03-04-PLAN.md — Super-admin operator dashboard backend: get_super_admin dependency + admin_router (TENANT-04)
- [ ] 03-05-PLAN.md — Encryption settings UI: EncryptionSettingsPage + TanStack Query hooks + nav entry (TENANT-02)
- [ ] 03-06-PLAN.md — Usage settings UI: UsageSettingsPage with quota bars + owner edit controls (TENANT-03)
- [ ] 03-07-PLAN.md — Admin dashboard frontend: (admin) route group + token form + workspace health table (TENANT-04)
- [ ] 03-08-PLAN.md — Gap closure: implement 3 RLS isolation integration tests replacing xfail stubs (TENANT-01)

### Phase 4: AI Governance
**Goal**: Admins can configure exactly which AI actions run automatically and which require human approval, with a complete traceable record of every AI decision and the ability to undo any AI-created artifact
**Depends on**: Phase 1
**Requirements**: AIGOV-01, AIGOV-02, AIGOV-03, AIGOV-04, AIGOV-05, AIGOV-06, AIGOV-07
**Success Criteria** (what must be TRUE):
  1. Admin can configure a policy per action type (e.g., "create issue" = auto-run for Admin, require approval for Member) and the AI respects those thresholds at runtime
  2. When an AI action requires approval, it is queued and an authorized reviewer sees a pending approval request before the action executes
  3. Admin can open an AI audit trail and see every AI action with its full input, output, rationale, model, cost, and approval chain
  4. Admin can select any AI-created or AI-modified artifact and roll it back to its pre-AI state
  5. If no valid BYOK API key is configured for a workspace, all AI features are disabled with a clear message — no fallback to platform-controlled keys occurs
  6. Admin can view a cost dashboard showing token usage broken down by model, feature, and time period for their workspace
  7. Users can click any AI-generated suggestion, extracted issue, or review comment and read the AI's stated rationale for it
**Plans**: 10 plans

Plans:
- [ ] 04-01-PLAN.md — Migrations 068/069 (workspace_ai_policy table + operation_type column) + WorkspaceAIPolicy model + Phase 4 test scaffolds (AIGOV-01/02/03/04/05/06)
- [ ] 04-02-PLAN.md — Service layer: async ApprovalService (role-aware policy lookup) + WorkspaceAIPolicyRepository + CostTracker Factory fix + BYOK enforcement + AINotConfiguredError (AIGOV-01/05/06)
- [ ] 04-03-PLAN.md — Audit repository + router: actor_type filter on list_filtered() + list_for_export() + audit GET endpoints (AIGOV-03)
- [ ] 04-04-PLAN.md — API layer: ai_governance.py router (policy CRUD + AI status + rollback) + ai_costs.py group_by=operation_type (AIGOV-01/02/04/05/06)
- [ ] 04-05-PLAN.md — Frontend: Approvals page + sidebar badge + AI Governance settings page policy matrix (AIGOV-01/02)
- [ ] 04-06-PLAN.md — Frontend: Audit settings actor_type filter + AI row expansion + cost dashboard By Feature tab (AIGOV-03/06)
- [ ] 04-07-PLAN.md — Frontend: Rationale popovers (ExtractionReviewPanel + PR review) + AiNotConfiguredBanner + disabled AI controls (AIGOV-05/07)
- [ ] 04-08-PLAN.md — Full quality gates + human verification checkpoint for all 7 AIGOV requirements (AIGOV-01/02/03/04/05/06/07)
- [x] 04-09-PLAN.md — Gap closure: wire ApprovalService.check_approval_required() into MCP server pipeline (AIGOV-01)
- [x] 04-10-PLAN.md — Gap closure: implement _dispatch_rollback() for issue/note + frontend rollback button (AIGOV-04)

### Phase 5: Operational Readiness
**Goal**: A new enterprise customer can deploy, monitor, back up, and upgrade Pilot Space without help from Pilot Space engineers — the platform operates as a self-contained system
**Depends on**: Phase 3
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06
**Success Criteria** (what must be TRUE):
  1. A developer following the Docker Compose guide can bring up a complete Pilot Space stack (backend, frontend, Supabase, Redis, Meilisearch) on a fresh Linux machine using a single `docker compose up` command
  2. A developer following the Helm chart guide can deploy Pilot Space on a Kubernetes cluster and have all services healthy within documented time
  3. All services expose a `/health` (or equivalent) endpoint returning structured JSON that monitoring tools (Prometheus, Datadog) can consume without custom parsing
  4. All application log lines are structured JSON with level, timestamp, trace_id, actor, and action fields — no unstructured string logs in production paths
  5. Admin can run a CLI backup command that produces a portable archive of all workspace data (PostgreSQL + Supabase Storage) and a restore command that applies it to a fresh instance
  6. An existing deployment running the prior MVP version can be upgraded to the enterprise release with zero downtime using documented migration steps
**Plans**: 6 plans

Plans:
- [ ] 05-01-PLAN.md — Health endpoints: /health/live (liveness) + /health/ready (deep check with DB/Redis/Supabase) + tests (OPS-03)
- [ ] 05-02-PLAN.md — Structured logging: add trace_id, actor, action ContextVars to structlog + auth_middleware actor population (OPS-04)
- [ ] 05-03-PLAN.md — Docker Compose consolidation: root docker-compose.yml with all services + .env.example + deployment guide (OPS-01)
- [ ] 05-04-PLAN.md — Helm chart: convert infra/k8s/ manifests to Helm templates + values.yaml + kubernetes guide (OPS-02)
- [ ] 05-05-PLAN.md — Backup CLI: pilot backup create/restore commands + pg_dump + Storage API + AES-256-GCM + docs (OPS-05)
- [ ] 05-06-PLAN.md — Upgrade runbook + CI simulation: docs/operations/upgrade-guide.md + .github/workflows/upgrade-simulation.yml (OPS-06)

### Phase 6: Wire Rate Limiting + SCIM Token
**Goal:** Close the two runtime wiring gaps found by the milestone audit — RateLimitMiddleware never registered and SCIM token generation endpoint missing
**Depends on**: Phase 1, Phase 3 (existing code already present)
**Requirements**: AUTH-07 (gap closure), TENANT-03 (rate limiting gap closure)
**Gap Closure:** Closes integration gaps from v1.0 audit
**Plans**: 1 plan

Plans:
- [ ] 06-01-PLAN.md — Register RateLimitMiddleware in lifespan + add POST /workspaces/{slug}/settings/scim-token endpoint + unit tests for 429 wiring and token endpoint (AUTH-07, TENANT-03)

### Phase 7: Wire Storage Quota Enforcement
**Goal:** Complete TENANT-03 by calling quota helpers on all write paths so storage limits actually enforce
**Depends on**: Phase 3 (quota helpers already implemented)
**Requirements**: TENANT-03 (storage quota gap closure)
**Gap Closure:** Closes storage quota integration gap from v1.0 audit
**Plans**: 2 plans

Plans:
- [ ] 07-01-PLAN.md — Test scaffold: 7 failing stubs for 507 + X-Storage-Warning behaviors across issue/note/attachment write paths (TENANT-03)
- [ ] 07-02-PLAN.md — Wire _check_storage_quota + _update_storage_usage into workspace_issues.py, workspace_notes.py, ai_attachments.py (TENANT-03)

### Phase 8: Fix SSO Integration
**Goal:** Close the two runtime blockers in SSO — frontend hooks send `workspace_slug` while backend endpoints expect `workspace_id: UUID` (HTTP 422 on all SSO config calls), and the SAML callback issues no Supabase JWT leaving the SAML login loop incomplete
**Depends on**: Phase 1 (SSO implementations already present)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Gap Closure:** Closes integration gaps from v1.0 audit — SSO frontend 422 + SAML no JWT
**Plans**: 1 plan

Plans:
- [ ] 08-01-PLAN.md — Normalize backend SSO endpoints to accept workspace_slug + complete SAML callback JWT issuance + frontend saml_provisioned handler + tests (AUTH-01/02/03/04)

### Phase 9: Login Audit Events
**Goal:** Record every user login (SAML and password) in the audit log so AUDIT-01 coverage is complete and compliance officers have a full login activity record
**Depends on**: Phase 2 (AuditLog infrastructure), Phase 8 (SSO callbacks fixed)
**Requirements**: AUDIT-01
**Gap Closure:** Closes auth paths → audit log integration gap from v1.0 audit
**Plans**: 1 plan

Plans:
- [ ] 09-01-PLAN.md — Add write_audit_nonfatal(user.login) to SAML callback + base auth router successful login path + tests (AUDIT-01)

### Phase 10: Wire Audit Trail
**Goal:** Fully activate the audit log at runtime by wiring audit_log_repository into all 10 CRUD service DI factories, fixing the SAML RLS context gap, and passing session_factory to PermissionAwareHookExecutor so AI audit writes actually reach the database
**Depends on**: Phase 2 (AuditLog infrastructure), Phase 4 (AI hook infrastructure)
**Requirements**: AUDIT-01, AUDIT-02, AIGOV-03
**Gap Closure:** Closes audit DI gap (container.py), SAML RLS gap (auth_sso.py:314), and AI session_factory gap (pilotspace_agent.py) from v1.0 audit
**Plans**: 1 plan

Plans:
- [x] 10-01-PLAN.md — Add audit_log_repository injection to 10 service factories in container.py + set_rls_context() in saml_callback + session_factory in PermissionAwareHookExecutor + tests (AUDIT-01, AUDIT-02, AIGOV-03)

### Phase 11: Fix Rate Limiting Architecture
**Goal:** Make rate limiting active at runtime by moving RateLimitMiddleware registration from inside the lifespan (where the stack is already frozen) to module level with a lazy Redis accessor
**Depends on**: Phase 3 (RateLimitMiddleware implementation), Phase 6 (wiring attempt)
**Requirements**: TENANT-03
**Gap Closure:** Closes rate limiting architectural gap from v1.0 audit — middleware commented out in main.py lifespan
**Plans**: 1 plan

Plans:
- [ ] 11-01-PLAN.md — Move RateLimitMiddleware to module-level registration with lazy Redis accessor + integration test verifying 429 response during lifespan startup (TENANT-03)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11
(Note: Phase 4 depends on Phase 1 only. Phases 6–7 are gap closure phases and can run independently. Phase 8 depends on Phase 1. Phase 9 depends on Phases 2 and 8. Phase 10 depends on Phases 2 and 4. Phase 11 depends on Phase 3.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Identity & Access | 9/9 | Complete   | 2026-03-07 |
| 2. Compliance & Audit | 5/5 | Complete   | 2026-03-08 |
| 3. Multi-Tenant Isolation | 8/8 | Complete   | 2026-03-08 |
| 4. AI Governance | 10/10 | Complete | 2026-03-08 |
| 5. Operational Readiness | 7/7 | Complete   | 2026-03-09 |
| 6. Wire Rate Limiting + SCIM Token | 1/1 | Complete   | 2026-03-09 |
| 7. Wire Storage Quota Enforcement | 2/2 | Complete   | 2026-03-09 |
| 8. Fix SSO Integration | 1/1 | Complete   | 2026-03-09 |
| 9. Login Audit Events | 1/1 | Complete   | 2026-03-09 |
| 10. Wire Audit Trail | 0/1 | Complete    | 2026-03-09 |
| 11. Fix Rate Limiting Architecture | 1/1 | Complete    | 2026-03-09 |

---
*Roadmap created: 2026-03-07*
*Coverage: 30/30 v1 requirements mapped*
*Phase 1 planned: 2026-03-07 — 9 plans across 5 waves*
*Phase 2 planned: 2026-03-08 — 5 plans across 4 waves*
*Phase 3 planned: 2026-03-08 — 7 plans across 3 waves*
*Phase 3 gap closure: 2026-03-08 — 03-08-PLAN.md (TENANT-01 RLS integration tests)*
*Phase 4 planned: 2026-03-08 — 8 plans across 5 waves*
*Phase 4 gap closure: 2026-03-08 — 04-09-PLAN.md (AIGOV-01 MCP wiring) + 04-10-PLAN.md (AIGOV-04 rollback)*
*Phase 5 planned: 2026-03-08 — 6 plans across 2 waves*
*Phase 6 planned: 2026-03-09 — 1 plan (gap closure: AUTH-07 + TENANT-03)*
*Phase 7 planned: 2026-03-09 — 2 plans across 2 waves (gap closure: TENANT-03 storage quota)*
*Phase 8 planned: 2026-03-09 — 1 plan (gap closure: AUTH-01/02/03/04 SSO integration)*
*Phase 9 planned: 2026-03-09 — 1 plan (gap closure: AUDIT-01 login events)*
*Phase 10 planned: 2026-03-09 — 1 plan (gap closure: AUDIT-01 DI + SAML RLS + AUDIT-02 + AIGOV-03 session_factory)*
*Phase 11 planned: 2026-03-09 — 1 plan (gap closure: TENANT-03 rate limiting architecture)*
