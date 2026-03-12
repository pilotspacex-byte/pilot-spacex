# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0-alpha — Pre-Production Launch

**Shipped:** 2026-03-12
**Phases:** 12 (9 original + 3 gap closure) | **Plans:** 37 | **Commits:** 116

### What Was Built
- Complete onboarding flow: auto-workspace + checklist + inline BYOK setup (Phase 12)
- Multi-provider BYOK registry with 6 built-in + custom providers + per-session model selector (Phase 13)
- Remote MCP server management with Bearer/OAuth2 auth + PilotSpaceAgent hot-loading (Phase 14)
- Related issues via semantic similarity + manual linking + AI suggestion dismissal (Phase 15)
- Workspace role skills with AI generation + admin approval gate + role inheritance (Phase 16)
- Skill action buttons on issue page bound to skills/MCP tools (Phase 17)
- Tech debt closure: OIDC E2E, MCP approval wiring, key rotation with dual-key fallback (Phase 18)
- Plugin marketplace: versioned plugins (skill + MCP + action buttons), install/update/seed (Phase 19)
- Skill template catalog: unified tables, browsable catalog with filter chips, AI personalization (Phase 20)

### What Worked
- Wave-based parallel execution: independent plans ran in parallel, reducing wall-clock time
- xfail/it.todo Wave 0 pattern: test stubs written before implementation gave clear contracts
- Consistent DI patterns: new services followed existing factory/direct-instantiation conventions
- TanStack Query + MobX separation: server state vs UI state cleanly split across all new features
- 3-day execution for 9 phases (31 plans) — high velocity maintained throughout

### What Was Inefficient
- Phase 016 missing VERIFICATION.md: process gap discovered only at audit — verification should be mandatory → **Fixed in Phase 21**
- Audit found 4 documentation gaps (frontmatter, traceability, roadmap checkboxes) — doc consistency checks should run per-phase → **Fixed in Phase 21**
- SeedPluginsService fire-and-forget asyncio.create_task shares request-scoped session — known race condition → **Fixed in Phase 22** (independent DB session)
- OAuth2 MCP UI button missing — backend/frontend feature gap not caught until audit → **Fixed in Phase 22** (Authorize button + callback handling)

### Patterns Established
- Plugin format: SKILL.md + references/ + MCP bindings + action buttons as installable unit
- Skill template catalog: skill_templates (admin-managed) + user_skills (personal, AI-personalized)
- Observer/plain split: observer() for data-fetching containers, plain components for props-driven leaves
- Source badge color coding: blue=built-in, green=workspace, purple=custom
- OperationalError guard for graceful migration fallback (new table primary, legacy fallback)

### Key Lessons
1. VERIFICATION.md should be generated as part of phase execution, not deferred to milestone audit — gap closure proved the cost of deferral
2. Doc consistency (frontmatter, traceability, roadmap checkboxes) should be checked per-phase, not per-milestone
3. Fire-and-forget background tasks must not share request-scoped sessions — use `get_db_session()` for independent sessions
4. Backend + frontend feature gaps (like OAuth2 UI) need explicit cross-layer checklist in plans
5. Milestone audit → gap closure → re-audit cycle is effective — 7/7 gaps closed, audit passed on second run

### Cost Observations
- Model mix: ~70% sonnet (execution), ~30% opus (planning, auditing)
- Sessions: ~15 across 3 days
- Notable: Wave-based parallelization cut execution time significantly — parallel plan execution is a strong efficiency multiplier

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 Enterprise | ~200 | 11 | Established Clean Architecture, RLS, DI patterns |
| v1.0-alpha | 116 | 12 | Wave parallelization, plugin model, template catalog, audit-gap-closure cycle |

### Cumulative Quality

| Milestone | Plans | Requirements | Files Changed |
|-----------|-------|-------------|---------------|
| v1.0 | 46 | 30/30 | ~500 |
| v1.0-alpha | 37 | 39/39 + 7 gap items | 738 |

### Top Lessons (Verified Across Milestones)

1. xfail stubs + TDD-first (Wave 0) produces cleaner interfaces than implementation-first
2. OperationalError guards enable safe incremental migration without feature flags
3. Observer/plain component split prevents MobX+TipTap flushSync issues in React 19
4. Documentation gaps compound — check per-phase, not per-milestone
5. Audit → gap closure → re-audit is a reliable quality gate for milestone completion
