# Homepage Module

_For project overview, see main `README.md` and `frontend/README.md`_

## Purpose

Primary landing page after workspace selection. Phase 88 (2026-04-24)
replaced the v2 two-panel dashboard (DailyBrief + ChatView sidebar) with a
calm chat-first **Launchpad**: greeting → composer → red-flag strip →
suggested-prompt chips → continue-card. The v2 dashboard files
(`HomepageHub`, `DailyBrief`, `BriefEntries`, `DevObjectIndicators`,
`DigestInsights`, `IssueDetailSheet`, `my-projects-section`,
`NoteContextBadge`, `SDLCSuggestionCards`, `SprintSparkline`,
`StaleLogicAlert`) and their tests were removed in the same release.

**Entry**: Login → `/` → resolve workspace → `/{workspaceSlug}` →
`<Launchpad workspaceId workspaceSlug />`.

```
Launchpad (max-w-720, single column)
├── HomepageGreeting        — h1 "Good {morning|afternoon|evening}, {Name}."
├── HomeComposer            — navigation-submit ChatInput → /chat?prefill=&mode=
├── RedFlagStrip            — 0–3 calm banners (stale | sprint | digest)
├── SuggestedPromptsRow     — locked 4 chips → composer.setDraft
└── ContinueCard            — link to last chat session (renders null when none)
```

The legacy hooks `useIssueDevObjects`, `useActiveCycleMetrics`, and
`useStaleIssueDetection` remain on disk (no longer barrel-exported) pending
a Phase 89+ cleanup. Backend endpoints (`/homepage/digest`,
`/homepage/activity`) are NOT removed this phase.

---

## Two-Panel Layout

```
+-------------------------------+-------------------+
|  DailyBrief (left)            |  ChatView (right)  |
|  - Greeting                   |  (desktop only,    |
|  - OnboardingBanner           |   hidden on mobile) |
|  - Recent Notes               |  from @/features/ai |
|  - Working On                 |                    |
|  - AI Insights                |                    |
|  - Projects                   |                    |
+-------------------------------+-------------------+
Desktop: 2-column flex layout
Mobile: DailyBrief only (ChatView hidden)
```

---

## Component Hierarchy

```
WorkspaceHomePage (wrapper)
└── HomepageHub (~80 lines, 2-column orchestrator)
    ├── DailyBrief (~507 lines, prose-style document)
    │   ├── Greeting (user display name)
    │   ├── OnboardingBanner (onboardingStore.openModal)
    │   ├── Recent Notes section
    │   ├── Working On section
    │   ├── AI Insights section
    │   └── Projects section
    └── ChatView (from @/features/ai, desktop only)
```

---

## State Management

No MobX store. HomepageUIStore was removed. DailyBrief reads from existing stores:

- `authStore.userDisplayName` (greeting)
- `workspaceStore.currentWorkspace` (workspace context)
- `onboardingStore.openModal()` (banner interaction)

All data fetching via TanStack Query (`useHomepageActivity` infinite query).

---

## API Endpoints

**Activity**: `GET /api/v1/workspaces/{id}/homepage/activity?cursor=` -> `HomepageActivityResponse`

---

## File Structure

```
frontend/src/features/homepage/
├── index.ts
├── types.ts              (ActivityCard types, ActivityMeta, HomepageActivityResponse)
├── constants.ts          (ITEMS_PER_PAGE, ACTIVITY_STALE_TIME, DAY_GROUP_LABELS)
├── api/homepage-api.ts
├── hooks/useHomepageActivity.ts
├── components/
│   ├── HomepageHub.tsx
│   └── DailyBrief.tsx
└── __tests__/HomepageHub.test.tsx
```

---

## Related Documentation

- **DD-013**: Note-First workflow
- **DD-065**: MobX + TanStack Query
- **US-19**: Homepage Hub feature
