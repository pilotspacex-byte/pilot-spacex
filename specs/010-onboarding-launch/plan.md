# Implementation Plan: Onboarding Launch Page

**Feature**: Onboarding Launch Page
**Branch**: `010-onboarding-launch`
**Created**: 2026-02-05
**Spec**: `specs/010-onboarding-launch/spec.md`
**Author**: Tin Dang

---

## Summary

Guided onboarding flow that walks workspace owners/admins through 3 steps: Anthropic API key configuration with validation, team member invitation, and a guided first-note experience with AI features. The technical approach uses a workspace-scoped onboarding state stored in PostgreSQL (visible to owners/admins only) with a frontend checklist component, a separate backend validation endpoint for Anthropic keys, and a template-based guided note ("Planning authentication for our app"). Regular members see a simplified welcome banner.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | TypeScript 5.3+ / Next.js 14+ (App Router) + React 18, Python 3.12+ / FastAPI |
| **Primary Dependencies** | MobX 6+, TanStack Query 5+, shadcn/ui, TailwindCSS 3.4+, SQLAlchemy 2.0, Pydantic v2 |
| **Storage** | PostgreSQL 16+ (workspace_onboarding table) |
| **Testing** | Vitest (frontend unit), Playwright (E2E), pytest + pytest-asyncio (backend) |
| **Target Platform** | Web browser (desktop-first, responsive) |
| **Project Type** | Web (frontend + backend) |
| **Performance Goals** | <200ms P95 for onboarding state API, <500ms for key validation response (excluding provider latency) |
| **Constraints** | RLS multi-tenant isolation, BYOK key encryption via Supabase Vault (DD-060), 700-line file limit |
| **Scale/Scope** | 1 onboarding state per workspace, 1 provider validation (Anthropic only), 1 guided note template |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (Next.js 14+, FastAPI, SQLAlchemy 2.0)
- [x] Database choice aligns (PostgreSQL 16+ with RLS)
- [x] Auth approach follows (Supabase Auth + RLS per DD-061)
- [x] Architecture patterns match (CQRS-lite service pattern per DD-064, feature folders per DD-065)

### Simplicity Gate

- [x] Minimum services: 1 backend service (OnboardingService), 1 frontend store (OnboardingStore), reuse existing WorkspaceService and InvitationService
- [x] No future-proofing — only the 4 defined steps, no plugin system for onboarding steps
- [x] No premature abstractions — single onboarding flow, not a generic wizard framework

### Quality Gate

- [x] Test strategy: >80% coverage, Vitest unit + Playwright E2E
- [x] Type checking: pyright (backend), TypeScript strict (frontend)
- [x] File size: 700 lines max
- [x] Linting: ruff (backend), eslint (frontend)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement (from spec) | Technical Approach | Components |
|-------|------------------------|-------------------|------------|
| FR-001 | Display onboarding checklist (owner/admin only) on workspace home | OnboardingChecklist component renders based on workspace onboarding state from TanStack Query + user role check | `OnboardingChecklist`, `useOnboardingState` hook, `GET /api/v1/workspaces/{id}/onboarding` |
| FR-002 | Persist onboarding state per workspace | `workspace_onboarding` table with RLS, accessed via OnboardingService | `WorkspaceOnboarding` model, `OnboardingRepository`, `OnboardingService` |
| FR-003 | Dismiss onboarding checklist | PATCH endpoint sets `dismissed_at`, MobX UIStore tracks collapsed state | `PATCH /api/v1/workspaces/{id}/onboarding`, `UIStore.onboardingCollapsed` |
| FR-004 | Navigate to AI Providers from checklist | Next.js router.push to `/[workspaceSlug]/settings/ai-providers` with `?onboarding=true` query param for contextual guidance | `OnboardingChecklist` click handler |
| FR-005 | Validate Anthropic API key | Separate backend endpoint proxies lightweight auth check to Anthropic API (GET /v1/models) with 10s timeout | `POST /api/v1/workspaces/{id}/ai-providers/validate`, `AIProviderKeyValidator` |
| FR-006 | Display Anthropic provider status | TanStack Query on AI Providers page, status derived from validation response | Existing `ProviderStatusCard` component (enhanced) |
| FR-007 | Show feature unlock summary | Frontend mapping of Anthropic key → feature capabilities (ghost text, code review, annotations, issue extraction, doc gen) | `FeatureUnlockSummary` component (static mapping, no backend) |
| FR-008 | Invitation dialog from onboarding | Reuse existing `InviteMemberDialog` component, opened from checklist step | Existing `InviteMemberDialog` + onboarding trigger |
| FR-009 | Handle existing vs new user invitations | Reuse existing `WorkspaceService.invite_member()` logic (already handles both cases) | Existing backend — no changes needed |
| FR-010 | Prevent duplicate invitations | Reuse existing 409 conflict handling in invitation endpoint | Existing backend — no changes needed |
| FR-011 | Create guided note with template | OnboardingService creates a Note with `is_guided_template=true` flag and pre-populated TipTap JSON content | `OnboardingService.create_guided_note()`, `POST /api/v1/workspaces/{id}/onboarding/guided-note` |
| FR-012 | Contextual tooltips in guided note (only when AI key configured) | Frontend tooltip overlay component activated when note has `is_guided_template` flag AND Anthropic key is valid | `GuidedNoteTooltips` component, conditional rendering in NoteEditor |
| FR-013 | Subtle celebration on completion | Animated checkmark + "All set!" text, auto-collapse after 3s, respects prefers-reduced-motion | `OnboardingCelebration` component |
| FR-014 | "What's Next?" section | Static component with links, rendered at bottom of guided note | `WhatsNextSection` component |
| FR-015 | Soft warning banner in editor when AI keys not configured | Banner in note editor with direct link to AI Providers settings | `AIKeyRequiredBanner` component (reusable) |
| FR-016 | Welcome banner for non-admin members | Simplified banner component for regular members joining workspace | `WelcomeBanner` component |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Data Entities |
|------------|-------------------|--------------------|--------------  |
| US1: Guided Workspace Setup | OnboardingService, OnboardingRepository, onboarding router | OnboardingChecklist, OnboardingStore, useOnboardingState | WorkspaceOnboarding |
| US2: Anthropic Key Validation | AIProviderKeyValidator, onboarding router extension | Existing ProviderStatusCard (enhanced), FeatureUnlockSummary | (uses existing AIProvider model) |
| US3: Team Member Invitation | (reuse existing WorkspaceService) | (reuse InviteMemberDialog, add onboarding trigger) | (uses existing WorkspaceMember, Invitation) |
| US4: Guided First Note | OnboardingService.create_guided_note(), onboarding router extension | GuidedNoteTooltips, WhatsNextSection, OnboardingCelebration | (uses existing Note model with guided flag) |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| Where to store onboarding state? | A) localStorage, B) PostgreSQL table, C) Redis | B) PostgreSQL table | FR-002 requires persistence across sessions/devices. RLS enforcement per DD-061. localStorage doesn't survive device switches. Redis is ephemeral. |
| How to validate AI provider keys? | A) Frontend-only format check, B) Backend proxy to provider API (separate endpoint), C) Validate-on-save (combined endpoint) | B) Separate validate endpoint | FR-005 requires actual authentication verification. Separate endpoint allows validate-before-commit UX. Frontend-only misses revoked keys. |
| How to implement guided note? | A) Special note type in DB, B) Regular note with metadata flag, C) Frontend-only overlay | B) Regular note with `is_guided_template` metadata | Reuses existing Note infrastructure. Flag enables conditional tooltip rendering. No new entity type needed. Aligns with DD-013 Note-First approach. |
| Onboarding checklist UI pattern? | A) Full-page wizard (multi-step modal), B) Embedded checklist card on home page, C) Sidebar panel | B) Embedded checklist card | Less disruptive than modal wizard. User stays on home page and can explore freely. Sidebar would compete with main nav. Matches Craft/Linear onboarding patterns. |
| How to track step completion? | A) Boolean per step in JSON column, B) Separate rows per step, C) Bitmask | A) JSON column with step statuses | Simple, flexible, no join needed. 3 steps don't justify separate rows. PostgreSQL JSONB supports efficient queries. |
| Which providers require keys during onboarding? | A) Anthropic only, B) Anthropic + OpenAI, C) All three (Anthropic + OpenAI + Google) | A) Anthropic only | Simplest onboarding. Anthropic powers all core AI features. OpenAI (embeddings) and Google (ghost text latency) are optional enhancements. |
| Who sees the onboarding checklist? | A) All workspace members, B) Owner/Admin only | B) Owner/Admin only | Setup tasks (AI keys, invitations) require admin permissions. Regular members see a simpler welcome banner (FR-016). |

---

## Data Model

### WorkspaceOnboarding

**Purpose**: Tracks onboarding progress for a workspace. One record per workspace, created on workspace creation.
**Source**: FR-001, FR-002, FR-003, FR-013, US1

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK → workspaces.id, UNIQUE, NOT NULL | One-to-one with workspace |
| steps | JSONB | NOT NULL, default `{}` | `{"ai_providers": false, "invite_members": false, "first_note": false}` |
| guided_note_id | UUID | FK → notes.id, NULLABLE | Reference to the created guided note |
| dismissed_at | timestamp | NULLABLE | When user dismissed checklist |
| completed_at | timestamp | NULLABLE | When all steps marked complete |
| created_at | timestamp | NOT NULL, default NOW | |
| updated_at | timestamp | NOT NULL, auto-update | |

**Relationships**:
- Belongs to Workspace (1:1)
- Has one Note (guided note, optional)

**Indexes**:
- (workspace_id) — UNIQUE, lookup by workspace
- (completed_at) — filter incomplete onboardings

**RLS Policy**: `workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin'))`

---

## API Contracts

### Endpoint 1: GET /api/v1/workspaces/{workspace_id}/onboarding

**Auth**: Required (Bearer)
**Source**: FR-001, FR-002, US1

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Onboarding record ID |
| workspace_id | UUID | Workspace this belongs to |
| steps | object | `{ ai_providers: bool, invite_members: bool, first_note: bool }` |
| guided_note_id | UUID? | ID of guided note if created |
| dismissed_at | string? | ISO timestamp when dismissed |
| completed_at | string? | ISO timestamp when completed |
| completion_percentage | number | 0-100 calculated from steps |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | No valid auth token |
| 403 | FORBIDDEN | User not admin/owner of workspace |
| 404 | NOT_FOUND | Workspace or onboarding record not found |

---

### Endpoint 2: PATCH /api/v1/workspaces/{workspace_id}/onboarding

**Auth**: Required (Bearer)
**Source**: FR-002, FR-003, FR-013, US1

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| step | string | No | One of: ai_providers, invite_members, first_note |
| completed | boolean | No | Required if step provided |
| dismissed | boolean | No | Sets dismissed_at to now if true |

**Response (200)**: Same as GET response above.

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | Invalid step name or missing fields |
| 401 | UNAUTHORIZED | No valid auth token |
| 403 | FORBIDDEN | User not admin/owner of workspace |

---

### Endpoint 3: POST /api/v1/workspaces/{workspace_id}/ai-providers/validate

**Auth**: Required (Bearer)
**Source**: FR-005, FR-006, US2

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| provider | string | Yes | One of: anthropic (MVP — extensible to openai, google later) |
| api_key | string | Yes | Non-empty, starts with "sk-ant-" for Anthropic |

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| provider | string | Provider name |
| valid | boolean | Whether key authenticated successfully |
| error_message | string? | Human-readable error if invalid |
| models_available | string[] | List of models accessible with this key |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | Empty key, invalid format, or unsupported provider |
| 401 | UNAUTHORIZED | No valid auth token |
| 403 | FORBIDDEN | User not admin/owner of workspace |
| 502 | PROVIDER_ERROR | Anthropic API unreachable (timeout >10s) |

---

### Endpoint 4: POST /api/v1/workspaces/{workspace_id}/onboarding/guided-note

**Auth**: Required (Bearer)
**Source**: FR-011, US4

**Request**: None (template is server-defined)

**Response (201)**:

| Field | Type | Description |
|-------|------|-------------|
| note_id | UUID | ID of the created guided note |
| title | string | Note title |
| redirect_url | string | URL to navigate to the note editor |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 401 | UNAUTHORIZED | No valid auth token |
| 403 | FORBIDDEN | User not admin/owner |
| 409 | CONFLICT | Guided note already exists for this workspace |

---

## Project Structure

```text
specs/010-onboarding-launch/
├── spec.md
├── plan.md              # This file
├── contracts/
│   └── rest-api.md      # (content inlined above)
├── quickstart.md
└── tasks.md             # Created in next phase

backend/src/pilot_space/
├── api/v1/
│   ├── routers/
│   │   └── onboarding.py          # New router (4 endpoints)
│   └── schemas/
│       └── onboarding.py          # Pydantic request/response schemas
├── application/services/
│   └── onboarding.py              # OnboardingService (CQRS-lite)
├── domain/
│   └── onboarding.py              # WorkspaceOnboarding entity
├── infrastructure/database/
│   ├── models/
│   │   └── onboarding.py          # SQLAlchemy model
│   └── repositories/
│       └── onboarding_repository.py  # OnboardingRepository
└── ai/
    └── providers/
        └── key_validator.py       # AIProviderKeyValidator

frontend/src/
├── features/onboarding/
│   ├── components/
│   │   ├── onboarding-checklist.tsx       # Main checklist card
│   │   ├── onboarding-step-item.tsx       # Individual step row
│   │   ├── onboarding-celebration.tsx     # Completion animation
│   │   ├── feature-unlock-summary.tsx     # AI features available
│   │   ├── guided-note-tooltips.tsx       # Contextual tooltips overlay
│   │   ├── whats-next-section.tsx         # Post-note-completion links
│   │   └── ai-key-required-banner.tsx     # Prompt for unconfigured keys
│   ├── hooks/
│   │   ├── useOnboardingState.ts          # TanStack Query hook
│   │   └── useOnboardingActions.ts        # Mutation hooks
│   └── index.ts                           # Feature barrel export
├── features/settings/components/
│   └── provider-status-card.tsx           # Enhanced AI provider card
└── stores/
    └── onboarding-store.ts                # MobX UI state for onboarding
```

**Structure Decision**: Follows existing feature-folder pattern (DD-065). New `features/onboarding/` directory colocates all onboarding components, hooks, and exports. Backend follows Clean Architecture layers (DD-064) with dedicated service, repository, and router.

---

## Quickstart Validation

### Scenario 1: Full Onboarding Happy Path

1. Create a new user account and workspace (as owner)
2. Land on workspace home page
3. **Verify**: Onboarding checklist visible with 3 steps, 0/3 complete
4. Click "Configure AI" step
5. Enter valid Anthropic API key, click Validate
6. **Verify**: Green checkmark, "Valid" status, feature unlock summary shows available features
7. Navigate back to home, click "Invite Members"
8. Enter a valid email, select "Member" role, click Send
9. **Verify**: Pending invitation appears in list
10. Click "Write Your First Note"
11. **Verify**: Note editor opens with guided template content ("Planning authentication for our app")
12. Type some text and pause for 500ms
13. **Verify**: Ghost text appears with tooltip explaining acceptance
14. **Verify**: Home page checklist shows 3/3, subtle animated checkmark + "All set!" auto-collapses

### Scenario 2: Dismiss and Resume

1. Create workspace, see onboarding checklist
2. Complete 1 step (AI providers)
3. Click "Skip for now"
4. **Verify**: Checklist collapses to sidebar reminder
5. Close browser, reopen workspace
6. **Verify**: Sidebar reminder visible, click to expand shows 1/3 complete

### Scenario 3: Guided Note Without AI Keys (Soft Enforce)

1. Create workspace, skip AI key configuration
2. Click "Write Your First Note" from checklist
3. **Verify**: Note editor opens with template content
4. **Verify**: Warning banner shows "Configure your Anthropic API key to unlock AI writing assistance" with direct link to settings
5. Type and pause — no ghost text appears, no AI tooltips shown
6. User can still write and explore the note normally

### Scenario 4: Regular Member Experience

1. Log in as a regular member (non-admin) of an existing workspace
2. **Verify**: No onboarding checklist visible
3. **Verify**: Simplified "Welcome" banner shown with links to key features

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | All gates pass | N/A |

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping
- [x] Every user story maps to backend + frontend components
- [x] Data model covers all spec entities with fields, relationships, indexes
- [x] API contracts cover all user-facing interactions
- [x] Research documents each decision with 2+ alternatives

### Constitution Compliance

- [x] Technology standards gate passed
- [x] Simplicity gate passed
- [x] Quality gate passed
- [x] All violations documented in Complexity Tracking (none)

### Traceability

- [x] Every technical decision references FR-NNN or constitution article
- [x] Every contract references the user story it serves
- [x] Every data entity references the spec entity it implements
- [x] Project structure matches constitution architecture patterns

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining
- [x] Performance constraints have concrete targets (<200ms onboarding API, <500ms validation)
- [x] Security documented (RLS policy on WorkspaceOnboarding, admin/owner only)
- [x] Error handling strategy defined per endpoint
- [x] File creation order: contracts -> tests -> implementation

---

## Next Phase

After this plan passes all checklists:

1. **Create supporting files** — quickstart.md (inlined above), contracts/rest-api.md (inlined above)
2. **Proceed to task breakdown** — Use `template-tasks.md` to create tasks.md
3. **Share with Tech Lead** — Plan is the technical alignment artifact
