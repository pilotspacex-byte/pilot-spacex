# Milestones

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
