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

<!-- v1.0-alpha Pre-Production Launch — shipped 2026-03-12 -->
- ✓ Auto-workspace creation on sign-up + guided onboarding checklist — v1.0-alpha
- ✓ Bug fixes: skill wizard UUID resolution + empty page redirect — v1.0-alpha
- ✓ Workspace switcher: name + member count + last-visited path — v1.0-alpha
- ✓ Multi-provider BYOK registry (Anthropic, OpenAI, Kimi, GLM, Gemini, custom) — v1.0-alpha
- ✓ Per-session AI model selector with localStorage persistence — v1.0-alpha
- ✓ Remote MCP server management with Bearer + OAuth2 auth — v1.0-alpha
- ✓ PilotSpaceAgent hot-loads registered MCP servers per workspace — v1.0-alpha
- ✓ Related issues: semantic similarity suggestions + manual linking + dismissal — v1.0-alpha
- ✓ Workspace role skills: AI generation, admin approval, role inheritance — v1.0-alpha
- ✓ Skill action buttons on issue page bound to skills/MCP tools — v1.0-alpha
- ✓ Plugin marketplace: versioned official plugins, one-click install, update notifications — v1.0-alpha
- ✓ Skill template catalog: browsable templates + AI personalization — v1.0-alpha
- ✓ Tech debt closure: OIDC E2E, MCP approval wiring, key rotation — v1.0-alpha

<!-- v1.0.0-alpha2 Notion-Style Restructure — shipped 2026-03-12 -->
- ✓ Nested page tree within projects (max 3 levels, adjacency list) — v1.0.0-alpha2
- ✓ Personal pages owned by user, independent of projects — v1.0.0-alpha2
- ✓ Migration: existing notes → project or personal pages — v1.0.0-alpha2
- ✓ Project-centric sidebar tree with expand/collapse + inline creation — v1.0.0-alpha2
- ✓ Personal pages under "Notes" nav — v1.0.0-alpha2
- ✓ Breadcrumb navigation in page header — v1.0.0-alpha2
- ✓ Embedded issue views (Board/List/Table/Priority) in project hub — v1.0.0-alpha2
- ✓ Page emoji icons with picker — v1.0.0-alpha2
- ✓ Visual design refresh (Notion-like typography, spacing, colors) — v1.0.0-alpha2
- ✓ Desktop + tablet responsive layout — v1.0.0-alpha2
- ✓ Drag-and-drop tree reordering with depth limit enforcement — v1.0.0-alpha2

### Active

(No active requirements — next milestone not yet defined)

### Out of Scope

- Real-time collaborative editing (Y.js) — significant infra investment, not enterprise-critical yet
- Offline editing — infrastructure complexity vs. value
- Mobile-specific features — desktop-first for developer workflows
- Jira/Asana bidirectional sync — enterprises will migrate, not sync
- Built-in LLM hosting (Ollama) — BYOK is sufficient
- AI Studio custom agent builder — built-in agents sufficient for current scale
- GitLab integration — GitHub-first; GitLab in subsequent milestone
- Unlimited nesting depth — 3 levels covers 95% of use cases
- Real-time collaborative tree editing — requires CRDT; enormous complexity vs. value
- Page-level permissions (per-page ACL) — breaks simple workspace RBAC model
- Synced blocks / transclusion — TipTap doesn't natively support

## Context

Shipped v1.0.0-alpha2 Notion-Style Restructure on 2026-03-12. Restructured data hierarchy from flat notes to Notion-style project-centric nested page trees with embedded issue views, visual design refresh, and tablet-responsive layout. Total codebase across 29 completed phases and 92 plans over three milestones.

**Tech stack:** FastAPI + SQLAlchemy async + Next.js 15 App Router + MobX + TanStack Query + shadcn/ui + Supabase Auth + PostgreSQL 16 (pgvector, pgmq, RLS) + Redis + Meilisearch.

**Current state:** All 86 requirements satisfied across v1.0 (30), v1.0-alpha (39), and v1.0.0-alpha2 (17). Platform features: Notion-style project page trees (3-level), sidebar tree navigation with drag-and-drop, embedded issue views (Board/List/Table/Priority), emoji page icons, Notion-like visual design, tablet-responsive layout, plus all prior enterprise features (SSO, RBAC, audit, BYOK AI, MCP, plugins).

**Known tech debt (minor):**
- Two test assertions in test_related_issues.py use stale field names (pass vacuously over empty lists)
- AgentListItem/AgentListResponse dead code in _chat_schemas.py (pre-existing)
- AISettingsStore.validateKey vs api-key-form.tsx validation duplication

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
| Plugin marketplace model | Versioned skill + MCP + action buttons as installable unit; replaces static built-ins | ✓ Good |
| Skill templates decoupled from roles | Unified skill_templates + user_skills tables; users pick templates, AI personalizes | ✓ Good |
| Multi-provider registry with custom OpenAI-compat | PROVIDER_DISPLAY_NAMES lookup + model_validator; trivially extensible | ✓ Good |
| Remote MCP hot-loading per workspace | _load_remote_mcp_servers in PilotSpaceAgent; no restart required | ✓ Good |
| Notion-style page tree over flat notes | Users organize knowledge hierarchically within projects; 3-level max keeps complexity manageable | ✓ Good |
| Two ownership: project pages + user pages | Replaces workspace-level notes; clearer ownership semantics | ✓ Good |
| Desktop + tablet responsive first | Mobile deferred; developer workflows are desktop/tablet primary | ✓ Good |
| Adjacency list on existing notes table | parent_id + depth + position avoids new table; CHECK constraint enforces depth 0-2 | ✓ Good |
| Gap-based positioning (ROW_NUMBER * 1000) | Enables reordering without renumbering; auto-resequence on gap exhaustion | ✓ Good |
| @dnd-kit for tree drag-and-drop | Already in codebase from BoardView; DndContext + useSortable for tree reorder/re-parent | ✓ Good |
| System font stack over DM Sans | Zero web font overhead for body text; Fraunces preserved for display headings | ✓ Good |
| Three-mode responsive (mobile/tablet/desktop) | Tablet gets icon-rail sidebar (not overlay drawer); desktop unchanged | ✓ Good |

---
*Last updated: 2026-03-12 after v1.0.0-alpha2 milestone shipped*
