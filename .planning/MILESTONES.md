# Milestones

## v1.0-alpha Pre-Production Launch (Shipped: 2026-03-12)

**Phases completed:** 9 phases, 31 plans
**Timeline:** 2026-03-10 → 2026-03-12 (3 days)
**Commits:** 92
**Files changed:** 699 (+99,806 / -4,227 lines)
**Requirements:** 39/39 satisfied

**Key accomplishments:**
- Auto-workspace creation on sign-up + guided onboarding checklist — new users never see a blank screen (ONBD-01..05, BUG-01, BUG-02, WS-01, WS-02)
- Multi-provider BYOK registry (Anthropic, OpenAI, Kimi, GLM, Gemini, custom OpenAI-compat) + per-session model selector with localStorage persistence (AIPR-01..05, CHAT-01..03)
- Remote MCP server management with Bearer + OAuth2 auth, connection status badges, and PilotSpaceAgent hot-loading (MCP-01..06)
- Related issues via semantic similarity suggestions + manual linking + AI dismissal persistence (RELISS-01..04)
- Workspace role skills with AI generation, admin approval gate, role inheritance, and personal skill override (WRSKL-01..04)
- Skill action buttons on issue page bound to skills/MCP tools with AI approval policy enforcement (SKBTN-01..04)
- Plugin marketplace: versioned official plugins (skill + MCP + action buttons), one-click install, update notifications, workspace seeding (SKRG-01..05)
- Skill template catalog: unified skill_templates + user_skills tables, browsable catalog with filter chips, AI-personalized skill generation from templates (P20-01..10)
- Tech debt closure: OIDC E2E verified, MCP approval wiring fixed, xfail audit tests passing, key rotation with dual-key fallback (DEBT-01..04)

**Known gaps (tech debt):**
- Phase 016 VERIFICATION.md never generated (process gap — requirements functionally satisfied)
- OAuth2 MCP server UI: backend support exists but no "Authorize" button in frontend
- SeedPluginsService fire-and-forget asyncio.create_task shares request-scoped session
- ai_chat.py at 700-line limit
- Dead schemas/mcp_server.py file (superseded by inline schemas)

---

## v1.0 Enterprise (Shipped: 2026-03-09)

**Phases completed:** 11 phases, 46 plans
**Timeline:** 2026-01-20 → 2026-03-09 (48 days)
**Lines of code:** ~782K (Python + TypeScript)
**Requirements:** 30/30 satisfied

**Key accomplishments:**
- Shipped full SAML 2.0 + OIDC SSO with role-claim mapping, custom RBAC (per-resource permission grants), SCIM 2.0 directory sync, and force-SSO enforcement (AUTH-01 through AUTH-07)
- Delivered immutable audit log covering every user and AI action: cursor-paged API, JSON/CSV streaming export, configurable retention via pg_cron, and a compliance-ready admin UI (AUDIT-01 through AUDIT-06)
- Verified complete cross-workspace data isolation (PostgreSQL RLS), workspace-level BYOK encryption (AES-256-GCM), per-workspace API rate limiting (429 enforcement), and storage quota enforcement on all write paths (TENANT-01 through TENANT-04)
- Built configurable AI governance: per-role approval policy engine, human approval queue, full AI audit trail with model/cost/rationale, AI artifact rollback, BYOK enforcement, and cost dashboard by feature (AIGOV-01 through AIGOV-07)
- Produced enterprise deployment package: Docker Compose, Kubernetes Helm chart, two-tier health endpoints, structured JSON logs, backup/restore CLI, and zero-downtime upgrade CI simulation (OPS-01 through OPS-06)
- Closed 6 audit-gap phases: RateLimitMiddleware module-level wiring, storage quota on 5 write paths, SSO slug/UUID fix, login audit events, 10 CRUD DI factory audit wiring, SAML RLS context gap

**Known gaps (tech debt):**
- OIDC login flow browser-verification pending (AUTH-02)
- 2 MCP servers use static approval level instead of DB-backed check (AIGOV-01)

---
