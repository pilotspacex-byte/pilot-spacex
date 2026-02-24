# Implementation Plan: Daily Routine — Contextual AI Chat Experience

**Feature**: Daily Routine — Contextual AI Chat Experience
**Branch**: `019-daily-routine`
**Created**: 2026-02-20
**Spec**: `specs/019-daily-routine/spec.md`
**Author**: Tin Dang

---

## Summary

Transform the generic ChatView into a context-aware AI assistant by wiring the existing backend digest system to the frontend homepage (US1), adding a standup generator skill (US2), building note health indicators with block-aware ghost text (US3), adding action buttons to annotation cards (US4), and injecting homepage context into the ChatView (US5).

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | Python 3.12+, TypeScript 5.3+ |
| **Primary Dependencies** | FastAPI 0.110+, Next.js 14+, MobX 6+, TanStack Query 5+, TipTap 2+ |
| **Storage** | PostgreSQL 16+ (WorkspaceDigest, DigestDismissal already exist) |
| **Testing** | pytest + pytest-asyncio (backend), Vitest (frontend) |
| **Target Platform** | Web (browser) |
| **Project Type** | web (frontend + backend) |
| **Performance Goals** | Digest load <1s, Ghost text <2.5s, Note health badges <2s |
| **Constraints** | RLS multi-tenant, 700-line file limit, >80% test coverage |
| **Scale/Scope** | 5-100 users per workspace |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (Python 3.12+, Next.js 14+)
- [x] Database choice aligns (PostgreSQL 16+ — reuse existing models)
- [x] Auth approach follows requirements (Supabase Auth + RLS)
- [x] Architecture patterns match (CQRS-lite services, MobX+TanStack, TipTap extensions)

### Simplicity Gate

- [x] Using minimum services — no new microservices; extends existing homepage router + AI services
- [x] No future-proofing — wiring existing backend to frontend, not building speculative features
- [x] No premature abstractions — reusing existing patterns (TanStack hooks, MobX stores, SKILL.md)

### Quality Gate

- [x] Test strategy: unit tests for services/stores/components, >80% coverage
- [x] Type checking: pyright (backend), TypeScript strict (frontend)
- [x] File size limits: 700 lines max
- [x] Linting: ruff (backend), eslint (frontend)

---

## Requirements-to-Architecture Mapping

| FR ID | Requirement | Technical Approach | Components |
|-------|------------|-------------------|------------|
| FR-001 | Display categorized AI digest insights | TanStack Query hook calls existing `GET /homepage/digest` → render insight cards grouped by category | `useWorkspaceDigest` hook, `DigestInsights` component, `DailyBrief.tsx` |
| FR-002 | Generate contextual suggested prompts | Derive prompts from digest data in `HomepageHub` — map insight categories to actionable prompt strings | `HomepageHub.tsx`, `generateContextualPrompts()` utility |
| FR-003 | Show freshness indicator + background refresh | TanStack Query `staleTime: 60_000`, `refetchInterval: 300_000`; display `updatedAt` from digest response | `useWorkspaceDigest` hook, `DigestHeader` component |
| FR-004 | Hide empty insight categories | Conditional rendering — filter `suggestions` array where `items.length > 0` | `DigestInsights` component |
| FR-005 | Dismiss individual insights | `POST /homepage/dismiss` (already exists) → optimistic update in TanStack cache | `useWorkspaceDigest` hook, `DismissButton` in insight card |
| FR-006 | "Generate Standup" action | Button triggers `\daily-standup` skill via ChatView `sendMessage` | `StandupButton` in `DailyBrief.tsx`, `daily-standup/SKILL.md` |
| FR-007 | Standup with yesterday/today/blockers | SKILL.md prompt instructs agent to query issues by state + transition time | `daily-standup/SKILL.md` |
| FR-008 | Copy standup to clipboard | `navigator.clipboard.writeText()` on standup structured result | `StandupResult` component in ChatView |
| FR-009 | Adapt standup time window | SKILL.md prompt includes "look back to last workday" instruction; agent uses MCP issue tools | `daily-standup/SKILL.md` |
| FR-010 | Note health badges in toolbar | `useNoteHealth` hook runs lightweight analysis on note load → badges in editor toolbar | `NoteHealthBadges` component, `useNoteHealth` hook |
| FR-011 | Clickable health badges → ChatView | Badge `onClick` calls `aiStore.pilotSpace.sendMessage(preFilledPrompt)` + opens ChatView panel | `NoteHealthBadges` component |
| FR-012 | Health analysis on load + debounced refresh | Run on mount, then debounced 5s after significant edits (>50 chars changed) | `useNoteHealth` hook |
| FR-013 | Note-specific ChatView empty state prompts | `ChatView` receives `suggestedPrompts` prop derived from `useNoteHealth` data | `NoteCanvasEditor.tsx` → `ChatView` props |
| FR-014 | Inject note health into ChatView context | Add `healthContext` to `PilotSpaceStore.conversationContext` | `PilotSpaceStore.ts`, `PilotSpaceActions.ts` |
| FR-015 | Block-aware ghost text | Route to block-type-specific prompts in `GhostTextService._build_prompt()` | `ghost_text.py` (backend), `GhostTextExtension.ts` (send blockType) |
| FR-016 | Note-level context in ghost text prompt | Include note title + linked issues in ghost text system prompt | `ghost_text.py`, `GhostTextStore.ts` |
| FR-017 | `issue_candidate` → "Extract Issue" button | Add action button to annotation card; onClick sends extraction message to ChatView | `annotation-card.tsx` |
| FR-018 | `clarification` → "Ask AI" button | Add action button; onClick opens ChatView with clarification prompt | `annotation-card.tsx` |
| FR-019 | `action_item` → "Create Task" button | Add action button; onClick opens issue creation with pre-filled title | `annotation-card.tsx` |
| FR-020 | Fix annotation `noteId: ''` bug | Pass `noteId` from `NoteCanvasEditor` through extension config | `MarginAnnotationAutoTriggerExtension.ts`, `NoteCanvasEditor.tsx` |
| FR-021 | Clean context transition between pages | Clear homepage context on note enter, clear note context on homepage enter | `PilotSpaceStore.ts` (context management) |
| FR-022 | Role-based permission filtering | Digest API already uses RLS; frontend filters based on user role from `workspaceStore` | Existing RLS policies, `useWorkspaceDigest` |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Data Entities |
|------------|-------------------|--------------------|--------------  |
| US1: Daily Briefing | `homepage.py` (existing endpoints), `GetDigestService`, `DismissSuggestionService` | `DailyBrief.tsx`, `DigestInsights`, `useWorkspaceDigest`, `HomepageHub.tsx` | WorkspaceDigest (existing), DigestDismissal (existing) |
| US2: Standup Generator | `daily-standup/SKILL.md` (new) | `DailyBrief.tsx` (StandupButton), ChatView (StandupResult) | StandupSummary (ephemeral) |
| US3: Note Health + Ghost Text | `ghost_text.py` (enhance prompts), `note_health.py` (new endpoint) | `NoteHealthBadges`, `useNoteHealth`, `GhostTextExtension.ts`, `NoteCanvasEditor.tsx` | NoteHealthAnalysis (client-side) |
| US4: Annotation Actions | None (frontend-only) | `annotation-card.tsx`, `MarginAnnotationAutoTriggerExtension.ts` | None |
| US5: Homepage Context Injection | None (context assembly in frontend) | `PilotSpaceStore.ts`, `PilotSpaceActions.ts`, `HomepageHub.tsx` | None |

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| Where to compute note health? | A: New backend endpoint, B: Client-side from existing data, C: Hybrid (client fast + server enrich) | C: Hybrid | FR-010 needs <2s; client-side uses linked-issues query (fast) + annotation data. Server enrichment deferred to background. KISS: start with client-only, add endpoint if needed. |
| How to deliver contextual prompts? | A: Backend generates prompts in digest response, B: Frontend derives from digest data | B: Frontend derives | FR-002 — prompts are UI copy, not business logic. Keeping prompt generation in frontend avoids API coupling and allows instant adaptation to digest changes. |
| Ghost text block-type routing | A: Frontend sends blockType, backend routes to different prompts, B: Single prompt with block-type context injected | A: Explicit routing | FR-015 — code blocks need fundamentally different prompts (syntax awareness). Already have `build_code_ghost_text_prompt` unused. Clean separation. |
| Standup data source | A: Dedicated backend endpoint aggregating issue transitions, B: AI skill using MCP tools to query issues | B: AI skill | FR-006/FR-009 — the standup needs natural language formatting and weekend-awareness. An AI skill handles edge cases (Monday standups, holidays) gracefully. MCP tools already expose issue state transitions. |
| Annotation action dispatch | A: Annotation card directly calls AI store, B: Annotation card emits event, parent handles | A: Direct store call | FR-017/018/019 — simpler, annotations already import `useStore()`. No event bus needed. KISS. |

---

## Data Model

### Existing Entities (no changes needed)

**WorkspaceDigest** — `backend/src/pilot_space/infrastructure/database/models/workspace_digest.py`
Already stores categorized suggestions as JSONB. `GetDigestService` already queries and filters.

**DigestDismissal** — `backend/src/pilot_space/infrastructure/database/models/digest_dismissal.py`
Already tracks per-user dismissals scoped to digest generation cycle.

### New Entity: NoteHealthAnalysis (client-side only)

**Purpose**: Transient analysis result computed in the browser. Not persisted to database.
**Source**: FR-010, FR-012, US3

| Field | Type | Source |
|-------|------|--------|
| noteId | string | Route param |
| extractableCount | number | Count of blocks matching actionable patterns |
| clarityIssueCount | number | Count of annotation results with type `clarification` |
| linkedIssues | Array<{id, identifier}> | From note-issue-links API |
| suggestedPrompts | string[] | Derived from above counts |
| computedAt | Date | Timestamp of last analysis |

No database migration needed.

---

## API Contracts

### Existing Endpoints (already implemented — no backend changes)

| Endpoint | Method | Router | Service |
|----------|--------|--------|---------|
| `/api/v1/workspaces/{id}/homepage/activity` | GET | `homepage.py:get_activity` | `GetActivityService` |
| `/api/v1/workspaces/{id}/homepage/digest` | GET | `homepage.py:get_digest` | `GetDigestService` |
| `/api/v1/workspaces/{id}/homepage/digest/refresh` | POST | `homepage.py:refresh_digest` | Triggers digest job |
| `/api/v1/workspaces/{id}/homepage/dismiss` | POST | `homepage.py:dismiss_suggestion` | `DismissSuggestionService` |

### Enhanced Endpoint: Ghost Text

**`POST /api/v1/ai/ghost-text`** (existing, enhanced)

Added field in request:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| block_type | string | No | One of: paragraph, heading, bulletList, codeBlock, blockquote. Default: paragraph |
| note_title | string | No | Max 255 chars |
| linked_issues | string[] | No | Issue identifiers for context |

No new endpoints needed. Backend already has all digest APIs.

---

## Project Structure

```text
specs/019-daily-routine/
├── spec.md
├── plan.md              # This file
├── tasks.md
└── checklists/
    └── requirements.md

# Backend changes (existing files — modify, don't create)
backend/src/pilot_space/
├── ai/
│   ├── services/ghost_text.py                    # Enhance: block-type routing
│   ├── prompts/ghost_text.py                     # Enhance: block-type prompts
│   └── templates/skills/
│       └── daily-standup/SKILL.md                # NEW: standup skill
├── api/v1/routers/
│   └── ghost_text.py                             # Enhance: accept block_type param
└── (no other backend changes — digest APIs already exist)

# Frontend changes
frontend/src/
├── features/
│   ├── homepage/
│   │   ├── components/
│   │   │   ├── DailyBrief.tsx                    # Enhance: wire digest, add standup button
│   │   │   └── DigestInsights.tsx                # NEW: render digest insight cards
│   │   └── hooks/
│   │       └── useWorkspaceDigest.ts             # NEW: TanStack Query hook for digest
│   ├── notes/
│   │   ├── components/
│   │   │   └── annotation-card.tsx               # Enhance: add action buttons
│   │   └── editor/extensions/
│   │       ├── GhostTextExtension.ts             # Enhance: send blockType
│   │       └── MarginAnnotationAutoTriggerExtension.ts  # FIX: pass noteId
│   └── ai/
│       └── ChatView/
│           └── constants.ts                      # Enhance: add daily-standup skill
├── components/editor/
│   ├── NoteCanvasEditor.tsx                      # Enhance: pass noteId to annotation ext, add health badges
│   └── NoteHealthBadges.tsx                      # NEW: health badge component
├── hooks/
│   └── useNoteHealth.ts                          # NEW: note health analysis hook
└── stores/ai/
    ├── PilotSpaceStore.ts                        # Enhance: context management methods
    ├── PilotSpaceActions.ts                      # Enhance: homepageContext injection
    └── GhostTextStore.ts                         # Enhance: pass blockType + note context
```

**Structure Decision**: Follows existing feature-folder pattern. New components colocated with their domain (homepage, notes, editor). No new directories except `homepage/hooks/`.

---

## Quickstart Validation

### Scenario 1: Homepage Daily Briefing

1. Seed workspace with: 5 issues (3 stale >7 days, 1 blocked, 1 overdue), 2 notes with actionable content
2. Trigger digest generation: `POST /homepage/digest/refresh`
3. Open homepage in browser
4. **Verify**: DigestInsights section shows categorized cards: "3 Stale Issues", "1 Blocked", "1 Overdue". No empty categories shown. Freshness indicator displays "Updated just now".
5. Dismiss the "Stale Issues" card
6. **Verify**: Card disappears. Page refresh still hides dismissed card.
7. Click contextual prompt "Review 3 stale issues"
8. **Verify**: ChatView opens, AI responds with stale issue details without visible tool calls.

### Scenario 2: Daily Standup

1. Have 2 issues moved to "Done" yesterday, 3 "In Progress" today, 1 "Blocked"
2. Click "Generate Standup" on homepage
3. **Verify**: ChatView shows formatted standup with Yesterday (2), Today (3), Blockers (1)
4. Click "Copy to clipboard"
5. **Verify**: Paste produces clean text output. Toast confirmation shown.

### Scenario 3: Note Health + Contextual Chat

1. Open a note with 3 actionable paragraphs ("implement auth", "fix login bug", "add tests") and 1 linked issue PS-42
2. **Verify**: Editor toolbar shows badges: "3 extractable", "Linked: PS-42"
3. Click "3 extractable" badge
4. **Verify**: ChatView opens with pre-filled "Extract issues from this note"
5. Check ChatView empty state (clear conversation first)
6. **Verify**: Suggested prompts are note-specific, not generic

### Scenario 4: Annotation Actions

1. Edit a note until margin annotations appear (type 50+ chars, wait 2s)
2. **Verify**: Annotation card for `issue_candidate` shows "Extract Issue" button
3. Click "Extract Issue"
4. **Verify**: ChatView opens with extraction flow for that specific block

### Scenario 5: Block-Aware Ghost Text

1. Open a note, place cursor in a heading block, type "Project "
2. **Verify**: Ghost text suggests structural content (e.g., "Overview" or "Architecture")
3. Place cursor in a code block, type `function `
4. **Verify**: Ghost text suggests syntax-appropriate completion

---

## Complexity Tracking

No constitution violations. All gates pass.

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping (FR-001 through FR-022)
- [x] Every user story maps to backend + frontend components
- [x] Data model covers all spec entities (WorkspaceDigest existing, NoteHealthAnalysis client-side)
- [x] API contracts cover all user-facing interactions (existing digest endpoints, enhanced ghost text)
- [x] Research documents each decision with 2+ alternatives

### Constitution Compliance

- [x] Technology standards gate passed
- [x] Simplicity gate passed
- [x] Quality gate passed
- [x] All violations documented in Complexity Tracking (none)

### Traceability

- [x] Every technical decision references FR-NNN
- [x] Every contract references the user story it serves
- [x] Every data entity references the spec entity it implements
- [x] Project structure matches constitution architecture patterns

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining
- [x] Performance constraints have concrete targets (<1s digest, <2.5s ghost text, <2s health badges)
- [x] Security documented (RLS filtering, workspace-scoped digest, role-based permissions)
- [x] Error handling strategy: TanStack Query error/retry for digest, graceful degradation for health analysis
- [x] File creation order specified in project structure
