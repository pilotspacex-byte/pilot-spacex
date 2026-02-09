# Implementation Plan: Role-Based Skills for PilotSpace Agent

**Feature**: Role-Based Skills for PilotSpace Agent
**Branch**: `011-role-based-skills`
**Created**: 2026-02-06
**Spec**: `specs/011-role-based-skills/spec.md`
**Author**: Tin Dang

---

## Summary

Enable users to configure SDLC roles per workspace (BA, PO, Developer, Tester, Architect, Tech Lead, PM, DevOps, or custom) so PilotSpace Agent adapts its behavior through role-specific skills injected via Claude Agent SDK's filesystem-based skill auto-discovery. Skills are stored in the database (source of truth) and materialized as SKILL.md files in the user's sandbox space before each agent session.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | Python 3.12+ (backend), TypeScript 5.3+ (frontend) |
| **Primary Dependencies** | FastAPI 0.110+, SQLAlchemy 2.0 async, Next.js 14+, MobX 6+, TanStack Query 5+ |
| **Storage** | PostgreSQL 16+ with RLS, Redis 7 (session cache) |
| **Testing** | pytest + pytest-asyncio (backend), Vitest + Playwright (frontend) |
| **Target Platform** | Web (frontend + backend) |
| **Performance Goals** | Skill generation <30s (AI), <5s (template). Skill file materialization <100ms. No degradation to existing agent response time. |
| **Constraints** | RLS multi-tenant isolation, 700-line file limit, skill content capped at 2000 words, max 3 roles per user-workspace |
| **Scale/Scope** | 5-100 users per workspace, 8 predefined role templates, unlimited custom roles |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (Python 3.12+, FastAPI, SQLAlchemy async, Next.js)
- [x] Database choice aligns with constitution constraints (PostgreSQL 16+ with RLS)
- [x] Auth approach follows constitution requirements (Supabase JWT + RLS per DD-061)
- [x] Architecture patterns match (CQRS-lite service, Repository, Clean Architecture per DD-064)

### Simplicity Gate

- [x] Using minimum number of projects/services (extends existing backend + frontend, no new services)
- [x] No future-proofing or speculative features (skill sharing FR-019 is MAY, not implemented)
- [x] No premature abstractions (reuses existing space manager, SDK config, onboarding patterns)

### Quality Gate

- [x] Test strategy defined with coverage target (>80%)
- [x] Type checking enforced (pyright strict + TypeScript strict)
- [x] File size limits respected (700 lines max)
- [x] Linting configured (ruff + eslint)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement | Technical Approach | Components |
|-------|-------------|-------------------|------------|
| FR-001 | Role selection in onboarding | Add `role_setup` step to onboarding JSONB `steps` field. Frontend role selector component in onboarding flow. | OnboardingModel, RoleSelectorComponent, OnboardingRouter |
| FR-002 | Multiple roles per workspace (max 3) | `user_role_skills` table with composite PK (user_id, workspace_id, role_type). `is_primary` boolean. Check constraint max 3. | UserRoleSkill model, RoleSkillRepository |
| FR-003 | AI-generated skill description | New `GenerateRoleSkillService` calls PilotSpaceAgent with role template + experience input. Returns SKILL.md-format text. | GenerateRoleSkillService, RoleSkillRouter |
| FR-004 | Three skill generation paths | Frontend UI state: "default" loads template, "describe" sends to AI endpoint, "examples" renders static examples. | SkillGenerationWizard component |
| FR-005 | Store per user-workspace | `user_role_skills` table scoped by (user_id, workspace_id). RLS policy enforces isolation. | UserRoleSkill model, migration 024 |
| FR-006 | Inject skill into agent session | Before `_stream_with_space`, write SKILL.md files from DB to space `.claude/skills/role-{name}/`. SDK auto-discovers. | PilotSpaceAgent._materialize_role_skills(), SpaceManager |
| FR-007 | Merge multiple role skills | Materialize all user's role skills as separate SKILL.md files. Primary role skill listed first. SDK loads all from directory. | PilotSpaceAgent._materialize_role_skills() |
| FR-008 | Fallback to generic behavior | If no role skills in DB, no role skill files materialized. Agent uses existing system skills only. | PilotSpaceAgent (no change needed — absent files = no injection) |
| FR-009 | Skills tab in settings | New route `/{slug}/settings/skills` with SkillsSettingsPage. API calls to role-skills endpoints. | SkillsSettingsPage, settings layout nav update |
| FR-010 | Immediate skill updates | DB write on save → next `_stream_with_space` call re-materializes from DB. No cache to invalidate. | RoleSkillService, PilotSpaceAgent |
| FR-011 | Default role in profile | Add `default_sdlc_role` column to `users` table. Expose via profile update endpoint. | User model extension, ProfileRouter |
| FR-012 | Owner role hints on invite | Add `suggested_sdlc_role` column to `workspace_invitations`. Pass through invitation create API. | WorkspaceInvitation model extension, InvitationRouter |
| FR-013 | 2000-word skill cap | Frontend word counter + backend Pydantic validator on `skill_content` field. | Pydantic schema validation, SkillEditor component |
| FR-014 | DB + filesystem storage | DB is source of truth. `_materialize_role_skills()` writes `.claude/skills/role-{name}/SKILL.md` to sandbox space on every agent session start. | RoleSkillRepository, PilotSpaceAgent |
| FR-015 | Preserve experience description | `experience_description` column in `user_role_skills` table. Used as input for AI regeneration. | UserRoleSkill model |
| FR-016 | Live preview | Frontend renders preview from skill markdown. No backend needed. | SkillEditor component with markdown preview |
| FR-017 | Template update notifications | `role_templates` table has `version` field. Compare with `user_role_skills.template_version`. | RoleTemplate model, notification logic in GET endpoint |
| FR-018 | Max 3 roles per workspace | DB check constraint + service validation before insert. | RoleSkillService, DB constraint |
| FR-019 | Share skills (MAY) | Deferred — not implemented in this phase. | N/A |
| FR-020 | Guest restriction | Service-level check: `workspace_member.role != 'guest'`. | RoleSkillService authorization check |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Data Entities |
|------------|-------------------|--------------------|--------------  |
| US1: Role Selection (Onboarding) | OnboardingService (extend steps), RoleSkillService | RoleSelectorStep, OnboardingChecklist (extend) | WorkspaceOnboarding (extend steps), RoleTemplate |
| US2: AI Skill Generation | GenerateRoleSkillService, RoleSkillRouter | SkillGenerationWizard, SkillPreview | UserRoleSkill |
| US3: Agent Injection | PilotSpaceAgent._materialize_role_skills() | (none — transparent) | UserRoleSkill (read) |
| US4: Default Role (Profile) | ProfileService (extend), UsersRouter | ProfileSettingsPage (extend) | User (extend) |
| US5: Owner Role Hints | InvitationService (extend), InvitationRouter | InviteDialog (extend) | WorkspaceInvitation (extend) |
| US6: Skills Settings Tab | RoleSkillRouter (CRUD), RoleSkillService | SkillsSettingsPage, SkillEditor, RoleCard | UserRoleSkill, RoleTemplate |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| How to inject role skills into SDK? | (A) System prompt concatenation in PilotSpaceAgent, (B) Write SKILL.md files to sandbox `.claude/skills/` for SDK auto-discovery, (C) Custom MCP tool serving skill content | **(B) Filesystem materialization** | SDK already auto-discovers `.claude/skills/` via `setting_sources=["project"]` (configure_sdk_for_space). Reuses existing mechanism. No agent code changes for loading. FR-006. |
| Where to store skill content? | (A) DB only — generate SKILL.md on each request, (B) Filesystem only, (C) DB (source of truth) + filesystem (materialized) | **(C) DB + materialized filesystem** | DB provides queryable, RLS-protected storage (FR-005). Filesystem needed for SDK consumption (FR-014). Materialization is <100ms per skill. |
| How to handle multiple role skills? | (A) Merge into single SKILL.md, (B) Separate SKILL.md per role — SDK loads all, (C) Primary-only injection | **(B) Separate files** | SDK already loads all skills from `.claude/skills/`. Each role gets `role-{name}/SKILL.md`. Primary role file includes a "primary" tag so agent knows precedence. FR-007. |
| Where to add role selection in onboarding? | (A) New separate onboarding step, (B) Inline in invite_members step, (C) Post-onboarding prompt | **(A) New step** | Clean separation. Existing steps are atomic (ai_providers, invite_members, first_note). Adding `role_setup` as step 4 follows the pattern. FR-001. |
| AI generation: which model? | (A) Claude Sonnet (orchestrator default), (B) Claude Haiku (fast), (C) Gemini Flash (cheapest) | **(A) Claude Sonnet** | Skill descriptions require nuanced writing quality. Sonnet provides good quality at reasonable cost. One-shot `query()` pattern, no multi-turn needed. FR-003. |
| Role template storage? | (A) Hardcoded in Python code, (B) DB seed table, (C) YAML files in repo | **(B) DB seed table** | Enables FR-017 (template versioning/updates). Admin-mutable for future customization. Seeded via migration. |
| SkillRegistry revival? | (A) Revive SkillRegistry class for dynamic loading, (B) Keep current None dep — use filesystem | **(B) Keep filesystem** | SkillRegistry was deliberately removed in 005-conversational-agent-arch. Skills auto-discovered by SDK from space directory. No need to resurrect. |

See `specs/011-role-based-skills/research.md` for detailed analysis.

---

## Data Model

See `specs/011-role-based-skills/data-model.md` for complete entity definitions.

### user_role_skills (new table)

**Purpose**: Stores personalized role skill content per user-workspace pair.
**Source**: FR-002, FR-005, FR-013, FR-015, US2, US3, US6

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| user_id | UUID | FK users.id, NOT NULL | Owner of the skill |
| workspace_id | UUID | FK workspaces.id, NOT NULL | Workspace scope |
| role_type | VARCHAR(50) | NOT NULL | Enum value or 'custom' |
| role_name | VARCHAR(100) | NOT NULL | Display name (e.g., "Senior QA Engineer") |
| skill_content | TEXT | NOT NULL, max 15000 chars (~2000 words) | SKILL.md markdown content |
| experience_description | TEXT | NULL | User's input for AI generation |
| is_primary | BOOLEAN | NOT NULL, default FALSE | Primary role flag |
| template_version | INTEGER | NULL | Version of RoleTemplate used (for update notifications) |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW | |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-update | |

**Relationships**:
- Belongs to User (N:1)
- Belongs to Workspace (N:1)
- Derived from RoleTemplate (optional reference via role_type)

**Indexes**:
- `ix_urs_user_workspace` (user_id, workspace_id) — primary query: "get all skills for user in workspace"
- `ix_urs_workspace` (workspace_id) — workspace-level queries

**Constraints**:
- UNIQUE (user_id, workspace_id, role_type) — no duplicate role types per user-workspace
- CHECK: count per (user_id, workspace_id) <= 3 — enforced at service layer (DB trigger optional)

**RLS Policy**:
- SELECT: user_id = current_user OR workspace member with admin+ role
- INSERT/UPDATE/DELETE: user_id = current_user AND workspace member with member+ role (not guest)

### role_templates (new table)

**Purpose**: Predefined SDLC role templates with default skill content.
**Source**: FR-001, FR-004, FR-017, US1

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| role_type | VARCHAR(50) | UNIQUE, NOT NULL | Enum key (e.g., 'developer', 'tester') |
| display_name | VARCHAR(100) | NOT NULL | Human-readable name |
| description | TEXT | NOT NULL | Brief role description for selection UI |
| default_skill_content | TEXT | NOT NULL | Default SKILL.md content |
| icon | VARCHAR(50) | NOT NULL | Icon identifier for frontend |
| sort_order | INTEGER | NOT NULL | Display order in selection grid |
| version | INTEGER | NOT NULL, default 1 | For template update notifications |
| created_at | TIMESTAMPTZ | NOT NULL, default NOW | |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-update | |

**Relationships**: Referenced by UserRoleSkill (one-to-many via role_type)

**RLS Policy**: SELECT for all authenticated users (templates are public). No INSERT/UPDATE/DELETE via app (seed data only).

### users (extend existing)

**Source**: FR-011, US4

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| default_sdlc_role | VARCHAR(50) | NULL | Default role for new workspace joins |

### workspace_invitations (extend existing)

**Source**: FR-012, US5

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| suggested_sdlc_role | VARCHAR(50) | NULL | Owner's role hint for invitee |

### workspace_onboardings (extend existing)

**Source**: FR-001, US1

The existing `steps` JSONB field gains a new key:
```json
{"ai_providers": false, "invite_members": false, "first_note": false, "role_setup": false}
```

No schema change needed — JSONB is flexible. Service logic updated to include `role_setup` in completion percentage calculation (now 0/4 to 4/4).

---

## API Contracts

See `specs/011-role-based-skills/contracts/rest-api.md` for complete endpoint specifications.

### Summary

| Method | Path | Source | Purpose |
|--------|------|--------|---------|
| GET | `/api/v1/role-templates` | FR-001, US1 | List predefined role templates |
| GET | `/api/v1/workspaces/{id}/role-skills` | FR-009, US6 | Get user's role skills for workspace |
| POST | `/api/v1/workspaces/{id}/role-skills` | FR-002, US1/US6 | Create role skill (from template or custom) |
| PUT | `/api/v1/workspaces/{id}/role-skills/{skill_id}` | FR-009, US6 | Update role skill content |
| DELETE | `/api/v1/workspaces/{id}/role-skills/{skill_id}` | FR-009, US6 | Remove role skill |
| POST | `/api/v1/workspaces/{id}/role-skills/generate` | FR-003, US2 | AI-generate skill from experience description |
| POST | `/api/v1/workspaces/{id}/role-skills/{skill_id}/regenerate` | FR-003, US6 | Regenerate existing skill with updated input |
| PATCH | `/api/v1/users/me/profile` | FR-011, US4 | Update default role (extend existing) |
| POST | `/api/v1/workspaces/{id}/invitations` | FR-012, US5 | Create invitation with role hint (extend existing) |

---

## Project Structure

```text
specs/011-role-based-skills/
├── spec.md
├── plan.md                    # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rest-api.md
└── tasks.md                   # Created in next phase

backend/src/pilot_space/
├── infrastructure/database/models/
│   └── user_role_skill.py     # NEW: UserRoleSkill + RoleTemplate models
├── infrastructure/database/repositories/
│   └── role_skill_repository.py  # NEW: RoleSkillRepository
├── application/services/
│   └── role_skill_service.py  # NEW: RoleSkillService (CRUD + generation)
├── api/v1/
│   ├── routers/
│   │   └── role_skills.py     # NEW: Role skills endpoints
│   └── schemas/
│       └── role_skill.py      # NEW: Pydantic schemas
├── ai/agents/
│   └── pilotspace_agent.py    # MODIFY: Add _materialize_role_skills()
├── ai/templates/role_templates/  # NEW: Default skill templates (8 SKILL.md files)
│   ├── developer.md
│   ├── tester.md
│   ├── business_analyst.md
│   ├── product_owner.md
│   ├── architect.md
│   ├── tech_lead.md
│   ├── project_manager.md
│   └── devops.md

backend/alembic/versions/
└── 024_add_role_based_skills.py  # NEW: Migration

frontend/src/
├── app/(workspace)/[workspaceSlug]/settings/
│   └── skills/
│       └── page.tsx           # NEW: Skills settings route
├── features/
│   ├── settings/
│   │   └── pages/
│   │       └── skills-settings-page.tsx  # NEW: Skills management UI
│   └── onboarding/
│       └── components/
│           └── role-selector-step.tsx    # NEW: Role selection step
├── components/
│   └── role-skill/
│       ├── role-card.tsx      # NEW: Role display card
│       ├── skill-editor.tsx   # NEW: Skill content editor
│       └── skill-generation-wizard.tsx  # NEW: AI generation flow
├── services/api/
│   └── role-skills.ts         # NEW: API client
└── stores/
    └── role-skill-store.ts    # NEW: MobX store for UI state
```

**Structure Decision**: Follows existing Clean Architecture layers (model → repository → service → router). New files placed alongside existing patterns. Single router for role-skills endpoints. Single service for CQRS-lite operations. Frontend follows feature-folder pattern with shared components.

---

## Quickstart Validation

See `specs/011-role-based-skills/quickstart.md` for full scenarios.

### Scenario 1: Happy Path — Onboarding Role Setup

1. Create a new workspace (or use fresh test workspace)
2. Navigate to workspace home — onboarding checklist visible
3. Complete AI providers step, then click "Set Up Your Role"
4. Select "Developer" from role grid → click "Continue"
5. Choose "Describe your expertise": "Full-stack TypeScript developer, 5 years. Focus on React, Node.js, and PostgreSQL."
6. Wait for AI generation (<30s) → preview skill content
7. Click "Save & Continue"
8. **Verify**: Skills tab in settings shows "Developer" role card with generated skill text

### Scenario 2: Agent Behavior Change

1. Configure "Tester" role with default template skill
2. Open AI Chat, start new session
3. Send: "Review this note about adding a payment feature"
4. **Verify**: Agent response emphasizes test scenarios, edge cases, acceptance criteria — not implementation details

### Scenario 3: Skills Settings CRUD

1. Navigate to Settings → Skills tab
2. Click "Edit" on existing skill → modify text → save
3. Click "Add Role" → select "Architect" → generate skill
4. Click "Remove" on secondary role → confirm
5. **Verify**: Changes reflected in next agent interaction

### Scenario 4: Multi-Workspace Independence

1. Configure "Developer" role in Workspace A
2. Configure "Tester" role in Workspace B
3. Chat with agent in Workspace A → developer-focused responses
4. Switch to Workspace B → chat with agent → tester-focused responses
5. **Verify**: No cross-contamination between workspace role skills

---

## Complexity Tracking

No constitution violations. All gates pass.

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping (FR-001 through FR-020)
- [x] Every user story maps to backend + frontend components
- [x] Data model covers all spec entities with fields, relationships, indexes
- [x] API contracts cover all user-facing interactions (9 endpoints)
- [x] Research documents each decision with 2+ alternatives (7 decisions)

### Constitution Compliance

- [x] Technology standards gate passed
- [x] Simplicity gate passed
- [x] Quality gate passed
- [x] All violations documented in Complexity Tracking (none)

### Traceability

- [x] Every technical decision references FR-NNN or constitution article
- [x] Every contract references the user story it serves
- [x] Every data entity references the spec entity it implements
- [x] Project structure matches constitution architecture patterns (Clean Architecture 5-layer)

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining
- [x] Performance constraints have concrete targets (<30s generation, <100ms materialization)
- [x] Security documented (RLS policies, guest restriction FR-020, workspace isolation)
- [x] Error handling strategy defined per endpoint (see contracts/rest-api.md)
- [x] File creation order specified (migration → models → repository → service → router → frontend)

---

## Next Phase

After this plan passes all checklists:

1. **Create supporting files** — research.md, data-model.md, contracts/rest-api.md, quickstart.md
2. **Proceed to task breakdown** — Use `template-tasks.md` to create tasks.md
3. **Share with Tech Lead** — Plan is the technical alignment artifact
