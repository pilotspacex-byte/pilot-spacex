# Pilot Space

## What This Is

Pilot Space is an AI-augmented SDLC platform built on a "Note-First" paradigm — users think and write in a collaborative note canvas, and issues, tasks, and documentation emerge naturally from refined thoughts rather than being filled into forms. It is designed for enterprise software development teams (50-500 developers) who need AI assistance they can trust: transparent, controllable, and self-hosted.

The platform replaces traditional ticket-first tools (Jira, Linear) with an AI-native alternative where human judgment always remains in control — every AI action is visible, auditable, and subject to configurable approval policies.

## Core Value

Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## Requirements

### Validated

<!-- Inferred from existing codebase (feat/mvp-clean branch) -->

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
- ✓ SelectionToolbar: Bold, Italic, Strikethrough, Code, Highlight — existing
- ✓ Basic workspace RBAC (Owner/Admin/Member/Guest roles) — existing
- ✓ Supabase Auth + RLS multi-tenant isolation at DB level — existing
- ✓ BYOK: workspace-level API key management for AI providers — existing
- ✓ Slash command menu in editor (AI extract issues, formatting) — existing
- ✓ Activity log on issues (including AI_REVIEW activity type) — existing

### Active

<!-- Enterprise milestone: first enterprise customer live in production -->

**Identity & Access**
- [ ] SSO integration: SAML 2.0 and OIDC (Okta, Azure AD, Google Workspace)
- [ ] Fine-grained RBAC: custom roles with per-resource permission grants
- [ ] Session management: force logout, session listing, IP-based policies
- [ ] Directory sync: SCIM 2.0 provisioning/deprovisioning

**Compliance & Audit**
- [ ] Immutable audit log: every user and AI action with actor, timestamp, payload
- [ ] Audit log export: JSON and CSV, filterable by actor/action/resource/date
- [ ] Data retention policies: configurable per workspace, auto-purge enforcement
- [ ] SOC 2 Type II evidence collection: access logs, change logs, AI action logs

**Multi-Tenant Isolation**
- [ ] Workspace-level encryption key management (bring your own key)
- [ ] Complete data isolation verification: cross-workspace query prevention
- [ ] Tenant-scoped API rate limiting and quota management
- [ ] Admin dashboard: workspace health, usage, member activity

**AI Governance**
- [ ] AI action policy engine: per-role approval thresholds (auto-run vs. require approval)
- [ ] Comprehensive AI audit trail: every AI action logged with input, output, model, cost, rationale
- [ ] Human approval gates: configurable by action type (create issue, post review, generate doc)
- [ ] AI action replay/rollback: admins can undo AI-created artifacts
- [ ] BYOK enforcement: AI features disabled if no valid key configured
- [ ] AI cost tracking: per-workspace token usage dashboard

**Operational Readiness**
- [ ] Enterprise deployment guide: Docker Compose + Kubernetes Helm chart
- [ ] Health check endpoints and structured logging (JSON) for observability
- [ ] Backup/restore tooling for PostgreSQL data and Supabase storage
- [ ] Zero-downtime migration path from earlier versions

### Out of Scope

- Real-time collaborative editing (Y.js) — Phase 3+, requires significant infra investment
- Offline editing — Infrastructure complexity, not enterprise-critical
- Mobile-specific features — Desktop-first for developer workflows
- Jira/Asana bidirectional sync — Complexity vs. value; enterprises will migrate, not sync
- Built-in LLM hosting (Ollama) — BYOK is sufficient; hosting LLMs adds ops burden
- AI Studio custom agent builder — Built-in agents are sufficient for this milestone
- GitLab integration — Prioritize GitHub first; GitLab in subsequent milestone

## Context

The codebase is a Python/FastAPI backend with Next.js 15 App Router frontend on the `feat/mvp-clean` branch. The MVP-018 "Note-First Complete" spec has been substantially implemented: the note canvas, issue management, cycles, AI PR review, notifications, and command palette are all working.

The primary gap between current state and enterprise readiness is in:
1. **Identity** — no SSO; only email/password via Supabase Auth
2. **Audit** — no immutable audit log; only per-issue activity log exists
3. **AI governance** — approval policies are hardcoded (DD-003), not configurable per workspace/role
4. **Compliance packaging** — no evidence export, no data retention controls
5. **Operational** — no Helm chart, no backup tooling, no structured logging

Target customer: large software engineering organization (50-500 developers), likely evaluating against Jira + GitHub Copilot. Decision criteria: data sovereignty (self-hosted), AI transparency (audit trail), compliance readiness (SOC 2 evidence), and migration friction (low).

## Constraints

- **Tech Stack**: FastAPI + SQLAlchemy async + Next.js 15 App Router + MobX + shadcn/ui — no substitutions
- **Auth**: Supabase Auth is the foundation; SSO must integrate through it (PKCE flow)
- **Database**: PostgreSQL + RLS is the multi-tenant boundary — must not bypass with service role in user flows
- **AI**: BYOK only — never route user data through Pilot Space-controlled AI keys
- **File size**: Backend files max 700 lines (pre-commit enforced); splits required for large modules
- **Deployment**: Self-hosted primary — all enterprise features must work without external managed services

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Note-First paradigm over ticket-first | Differentiator vs. Jira/Linear; thinking before structure | — Pending (market validation) |
| BYOK for all AI features | No AI cost pass-through; enterprise data stays on their infra | ✓ Good |
| Supabase Auth + RLS for multi-tenancy | DB-level isolation; proven; no custom JWT | ✓ Good |
| pgmq for async job queue | Native PostgreSQL; avoids Redis/Kafka dependency | ✓ Good |
| SSO via Supabase Auth PKCE | Avoids building custom SAML parser; Supabase handles provider handshake | — Pending |
| AI approval policies per-role | Enterprise admins need control granularity; hardcoded thresholds insufficient | — Pending |

---
*Last updated: 2026-03-07 after project initialization (enterprise milestone planning)*
