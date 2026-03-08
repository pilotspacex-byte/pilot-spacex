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
- [ ] **Phase 3: Multi-Tenant Isolation** - Verified data isolation, workspace encryption, rate limiting, and operator dashboard
- [ ] **Phase 4: AI Governance** - Configurable approval policies, AI audit trail, rollback, strict BYOK enforcement, and cost visibility
- [ ] **Phase 5: Operational Readiness** - Docker Compose guide, Helm chart, health checks, structured logging, backup tooling, and migration path

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
**Plans**: 7 plans

Plans:
- [ ] 03-01-PLAN.md — Migration 066 (RLS enum case fix) + Phase 3 test scaffolds for all TENANT requirements (TENANT-01)
- [ ] 03-02-PLAN.md — Workspace encryption backend: model + migration 067 + helpers + 4 API endpoints (TENANT-02)
- [ ] 03-03-PLAN.md — Per-workspace rate limits + storage quota enforcement + GET/PATCH quota API (TENANT-03)
- [ ] 03-04-PLAN.md — Super-admin operator dashboard backend: get_super_admin dependency + admin_router (TENANT-04)
- [ ] 03-05-PLAN.md — Encryption settings UI: EncryptionSettingsPage + TanStack Query hooks + nav entry (TENANT-02)
- [ ] 03-06-PLAN.md — Usage settings UI: UsageSettingsPage with quota bars + owner edit controls (TENANT-03)
- [ ] 03-07-PLAN.md — Admin dashboard frontend: (admin) route group + token form + workspace health table (TENANT-04)

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
**Plans**: TBD

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
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5
(Note: Phase 4 depends on Phase 1 only, so it can begin once Phase 1 is complete. The sequence above assumes sequential execution for simplicity; Phase 4 may be parallelized with Phases 2-3 if needed.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Identity & Access | 9/9 | Complete   | 2026-03-07 |
| 2. Compliance & Audit | 5/5 | Complete   | 2026-03-08 |
| 3. Multi-Tenant Isolation | 2/7 | In Progress|  |
| 4. AI Governance | 0/TBD | Not started | - |
| 5. Operational Readiness | 0/TBD | Not started | - |

---
*Roadmap created: 2026-03-07*
*Coverage: 30/30 v1 requirements mapped*
*Phase 1 planned: 2026-03-07 — 9 plans across 5 waves*
*Phase 2 planned: 2026-03-08 — 5 plans across 4 waves*
*Phase 3 planned: 2026-03-08 — 7 plans across 3 waves*
