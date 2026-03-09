# Pilot Space

## What This Is

Pilot Space is an AI-augmented SDLC platform built on a "Note-First" paradigm — users think and write in a collaborative note canvas, and issues, tasks, and documentation emerge naturally from refined thoughts rather than being filled into forms. It is designed for enterprise software development teams (50-500 developers) who need AI assistance they can trust: transparent, controllable, and self-hosted.

The platform replaces traditional ticket-first tools (Jira, Linear) with an AI-native alternative where human judgment always remains in control — every AI action is visible, auditable, and subject to configurable approval policies.

## Core Value

Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## Requirements

### Validated

<!-- Pre-enterprise MVP (feat/mvp-clean) -->
- ✓ Note canvas as primary interface with TipTap rich editor — existing
- ✓ Ghost text AI autocomplete (Tab/arrow to accept) — existing
- ✓ Issue extraction from notes with ExtractionReviewPanel (human-in-the-loop) — existing
- ✓ Issue management: states, priorities, assignees, labels, custom fields — existing
- ✓ Cycles (sprints) with analytics and release notes tab — existing
- ✓ GitHub PR integration with AI code review — existing
- ✓ AI PR review: architecture + code quality + security findings — existing
- ✓ CI status badges on linked PRs — existing
- ✓ Knowledge graph auto-population from issues and notes (background job) — existing
- ✓ Notification system: backend pipeline + polling + priority display — existing
- ✓ Cmd+K global command palette (notes + issues search) — existing
- ✓ Basic workspace RBAC (Owner/Admin/Member/Guest roles) — existing
- ✓ Supabase Auth + RLS multi-tenant isolation at DB level — existing
- ✓ BYOK: workspace-level API key management for AI providers — existing
- ✓ Slash command menu in editor (AI extract issues, formatting) — existing
- ✓ Activity log on issues (including AI_REVIEW activity type) — existing

<!-- v1.0 Enterprise milestone — shipped 2026-03-09 -->
- ✓ SSO integration: SAML 2.0 and OIDC (Okta, Azure AD, Google Workspace) — v1.0
- ✓ Fine-grained RBAC: custom roles with per-resource permission grants — v1.0
- ✓ Session management: force logout, session listing, IP-based policies — v1.0
- ✓ Directory sync: SCIM 2.0 provisioning/deprovisioning — v1.0
- ✓ Immutable audit log: every user and AI action with actor, timestamp, payload — v1.0
- ✓ Audit log export: JSON and CSV, filterable by actor/action/resource/date — v1.0
- ✓ Data retention policies: configurable per workspace, auto-purge via pg_cron — v1.0
- ✓ SOC 2 Type II evidence: access logs, change logs, AI action logs — v1.0
- ✓ Workspace-level encryption key management (BYOK, AES-256-GCM) — v1.0
- ✓ Complete data isolation: cross-workspace RLS policies verified — v1.0
- ✓ Tenant-scoped API rate limiting and storage quota enforcement — v1.0
- ✓ Admin dashboard: workspace health, usage, member activity — v1.0
- ✓ AI action policy engine: per-role approval thresholds — v1.0
- ✓ Comprehensive AI audit trail: input, output, model, cost, rationale — v1.0
- ✓ Human approval gates: configurable by action type — v1.0
- ✓ AI action rollback: admins can undo AI-created artifacts — v1.0
- ✓ BYOK enforcement: AI features disabled if no valid key (no env fallback) — v1.0
- ✓ AI cost tracking: per-workspace token usage dashboard by model and feature — v1.0
- ✓ Enterprise deployment: Docker Compose + Kubernetes Helm chart — v1.0
- ✓ Health check endpoints and structured JSON logs (trace_id, actor, action) — v1.0
- ✓ Backup/restore CLI: pg_dump + Storage + AES-256-GCM encryption — v1.0
- ✓ Zero-downtime migration path from earlier versions — v1.0

### Active

<!-- Next milestone: post-beta customer hardening -->

- [ ] OIDC login flow browser-verified end-to-end (AUTH-02 human verification pending)
- [ ] MCP servers `issue_relation_server` + `note_content_server` wired to `check_approval_from_db()` (10 tools, AIGOV-01 partial)
- [ ] xfail API test fixtures: missing async HTTP `client` fixture in audit API tests (Phase 02 tech debt)
- [ ] Key rotation re-encryption: `test_key_rotation_re_encrypts_existing_content` is xfail stub (Phase 03 tech debt)
- [ ] Live environment smoke tests: Docker Compose full stack + Helm chart install on real cluster

### Out of Scope

- Real-time collaborative editing (Y.js) — significant infra investment, not enterprise-critical yet
- Offline editing — infrastructure complexity vs. value
- Mobile-specific features — desktop-first for developer workflows
- Jira/Asana bidirectional sync — enterprises will migrate, not sync
- Built-in LLM hosting (Ollama) — BYOK is sufficient
- AI Studio custom agent builder — built-in agents sufficient for current scale
- GitLab integration — GitHub-first; GitLab in subsequent milestone

## Context

Shipped v1.0 Enterprise on 2026-03-09. Codebase: ~782K lines (Python + TypeScript) across 11 completed phases and 46 plans.

**Tech stack:** FastAPI + SQLAlchemy async + Next.js 15 App Router + MobX + TanStack Query + shadcn/ui + Supabase Auth + PostgreSQL 16 (pgvector, pgmq, RLS) + Redis + Meilisearch.

**Current state:** All 30 enterprise requirements satisfied. Platform is self-hostable (Docker Compose or Helm), auditable (immutable log, CSV/JSON export), and enterprise-auth ready (SAML 2.0, OIDC, SCIM 2.0). Two known tech-debt items pending for next milestone.

**Known issues / tech debt:**
- OIDC E2E browser flow not verified (role claim application in frontend confirmed, but no browser test)
- 2 of 6 MCP servers bypass DB approval policy (10 tools use static level)
- 2 xfail audit API tests blocked by missing async HTTP client fixture
- Key rotation re-encryption deferred (xfail stub)

## Constraints

- **Tech Stack**: FastAPI + SQLAlchemy async + Next.js 15 App Router + MobX + shadcn/ui — no substitutions
- **Auth**: Supabase Auth is the foundation; SSO integrates through PKCE/SAML flows
- **Database**: PostgreSQL + RLS is the multi-tenant boundary — service role only for admin operations
- **AI**: BYOK only — no env fallback, no Pilot Space-controlled AI keys
- **File size**: Backend files max 700 lines (pre-commit enforced)
- **Deployment**: Self-hosted primary — all enterprise features work without external managed services

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Note-First paradigm over ticket-first | Differentiator vs. Jira/Linear; thinking before structure | — Pending (market validation) |
| BYOK for all AI features | No AI cost pass-through; enterprise data stays on their infra | ✓ Good |
| Supabase Auth + RLS for multi-tenancy | DB-level isolation; proven; no custom JWT | ✓ Good |
| pgmq for async job queue | Native PostgreSQL; avoids Redis/Kafka dependency | ✓ Good |
| SSO via Supabase Auth PKCE (SAML) | Custom SAML callback + `generate_link` + `verifyOtp` — Supabase handles JWT issuance | ✓ Good |
| AI approval policies per-role | Per-role DB policy rows; four-tier priority (ALWAYS_REQUIRE → owner → DB → fallback) | ✓ Good |
| `audit_log_repository` as `providers.Factory` | Immutable audit rows need fresh AsyncSession per request; Singleton shares session across concurrent requests | ✓ Good |
| RateLimitMiddleware at module level with lazy `_resolve_redis()` | Starlette freezes middleware stack at lifespan start; module-level registration needed | ✓ Good |
| `AuditLog` uses `Base+TimestampMixin+WorkspaceScopedMixin` (not `WorkspaceScopedModel`) | Exclude `SoftDeleteMixin` — audit records are immutable and must not support soft-delete | ✓ Good |

---
*Last updated: 2026-03-09 after v1.0 Enterprise milestone*
