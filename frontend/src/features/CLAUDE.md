# Frontend Features Documentation

**Generated**: 2026-02-10
**Scope**: `frontend/src/features/` (10 feature modules)
**Language(s)**: TypeScript 5.3+, React 18, Next.js 14
**Architecture**: Feature-folder pattern with colocated components, hooks, stores

---

## Quick Start

**Before implementing any feature, read in this order**:

1. **This file** — Understanding feature structure & patterns
2. **Module CLAUDE.md** — Feature-specific design (if exists)
3. **Main CLAUDE.md** — Architecture principles (state split, accessibility, etc.)
4. **Dev patterns** — `docs/dev-pattern/45-pilot-space-patterns.md`

---

## Module Overview & Index

All modules follow consistent structure: `components/`, `hooks/`, optional `pages/`, optional `editor/`, optional `stores/`, optional `services/`.

### Core Modules (6)

| Module | Purpose | Status | Files |
|--------|---------|--------|-------|
| **[notes](#notes-module)** | Block-based editor, ghost text, issue extraction | Production | 40+ |
| **[issues](#issues-module)** | Issue CRUD, AI context, activity tracking | Production | 24 components + 15 hooks |
| **[ai](#ai-module)** | Unified conversational interface, SSE streaming, approvals | Production | 25+ components |
| **[approvals](#approvals-module)** | Human-in-the-loop workflow (DD-003) | Production | 3 components |
| **[cycles](#cycles-module)** | Sprint management, burndown charts | Production | 5 components + 6 hooks |
| **[homepage](#homepage-module)** | Landing page (Note-First), activity feed, digest | Production | 28 files |

### Integration Modules (2)

| Module | Purpose | Status | Files |
|--------|---------|--------|-------|
| **[github](#github-integration-module)** | PR review, linking, OAuth | Production | 5+ components |
| **[integrations](#integrations-module)** | PR review hooks (supports future integrations) | Production | 2 hooks |

### Configuration Modules (2)

| Module | Purpose | Status | Files |
|--------|---------|--------|-------|
| **[settings](#settings-module)** | Workspace, members, AI providers, profile, skills | Production | 5 pages + 10 components |
| **[costs](#costs-module)** | AI cost tracking by agent/user/day | Production | 1 page + 5 components |

### Onboarding Module (1)

| Module | Purpose | Status | Files |
|--------|---------|--------|-------|
| **[onboarding](#onboarding-module)** | 3-step workspace setup | Production | 6 components + 3 hooks |

---

## Shared Patterns Across All Modules

### 1. Component-Hook-Store Integration

**Every feature module follows this pattern**:

```
Feature Module/
├── components/               # UI presentation (wrapped with observer() if MobX)
│   ├── component-name.tsx    # Single component, <700 lines
│   └── __tests__/            # Co-located tests
├── hooks/                    # TanStack Query + MobX reactions
│   ├── useFeatureQuery.ts    # Query hook
│   ├── useFeatureMutation.ts # Mutation hook
│   └── index.ts              # Barrel export
├── pages/                    # Next.js app router pages (optional)
├── editor/                   # TipTap extensions (notes only)
├── services/                 # Business logic (notes ghostTextService)
└── CLAUDE.md                 # Feature-specific documentation
```

### 2. State Management Rule (DD-065)

**Strict separation**: MobX for UI state. TanStack Query for server data.

```typescript
// ✅ MobX: UI state
class UIStore { @observable isModalOpen = false; }

// ✅ TanStack Query: Server data
function useNoteData(id) { return useQuery({ queryKey: ['notes', id], queryFn: () => notesApi.get(id) }); }

// ❌ Never store API data in MobX (causes infinite loops)
```

### 3. Component Wrapping Requirements

**If component uses MobX stores → wrap with `observer()`**:

```typescript
// ✅ Correct: observer() wrapper
export const IssueCard = observer(function IssueCard({ issueId }) {
  const { workspaceStore } = useStore();
  return <div>{workspaceStore.name}</div>;
});

// ❌ Wrong: Missing observer wrapper — won't re-render on store changes
```

### 4. Barrel Export Pattern

**Every module exposes via `index.ts`**:

```typescript
// features/notes/hooks/index.ts
export { useNotes, useAutoSave } from './hooks';
export type { UseNotesOptions } from './useNotes';

// Usage: import { useNotes } from '@/features/notes';
```

### 5. File Size Limit (700 lines max)

**Enforced**: Ensures testability, reviewability, IDE performance. If exceeding:
1. Extract sub-components to subfolder
2. Extract hooks to `hooks/`
3. Extract logic to `services/`

---

## Module Details

### Notes Module

**File Path**: `/frontend/src/features/notes/`

**Purpose**: Block-based editor (TipTap + 13 extensions), AI ghost text, auto-save, annotations, issue extraction.

**Philosophy**: Note-First workflow (DD-013) — users think in notes, issues emerge from refined thinking.

**Key Features**:
- **Editor**: 13 TipTap extensions (BlockId, GhostText, Annotations, IssueLinking, CodeBlocks, etc.)
- **Ghost Text**: 500ms pause trigger, 50-token max, Gemini Flash
- **Auto-Save**: 2s debounce, 3-retry exponential backoff, dirty state tracking
- **Annotations**: AI margin suggestions on 2s pause (50+ char threshold)
- **Issue Extraction**: Rainbow-bordered extraction boxes, approval-based creation (DD-003)

**State Management**:
- **MobX**: `NoteStore` (current note, dirty state, annotations)
- **TanStack Query**: `useNote()`, `useNotes()`, `useCreateNote()`, `useUpdateNote()`
- **PilotSpaceStore**: SSE content updates, approval requests

**Architecture**:
```
NoteCanvas (observer)
├── EditorToolbar (AI toggles)
├── EditorContent (TipTap + 13 extensions)
│   ├── BlockIdExtension (IDs for all blocks)
│   ├── GhostTextExtension (500ms completions)
│   ├── MarginAnnotationExtension (margin indicators)
│   ├── IssueLinkExtension ([PS-42] badges)
│   ├── CodeBlockExtension (syntax highlight)
│   ├── MentionExtension (@user references)
│   ├── SlashCommandExtension (/commands)
│   └── 6 more extensions...
└── AnnotationDetailPanel (side annotation view)
```

**Integration Points**:
- **AI Layer**: SSE content_update → `useContentUpdates()` hook
- **Issues**: Issue extraction → approval → `NoteIssueLink` (EXTRACTED)
- **Homepage**: Recent notes → activity feed

**See Detailed Documentation**: `frontend/src/features/notes/CLAUDE.md`

---

### Issues Module

**File Path**: `/frontend/src/features/issues/`

**Purpose**: Issue CRUD, detail view, properties (state/priority/labels/etc.), sub-issues, activity timeline, AI context aggregation.

**Key Features**:
- **State Machine**: Backlog → Todo → In Progress → In Review → Done (enforced)
- **State-Cycle Constraints**: In Progress/In Review require active cycle
- **Inline Editing**: Title + description with 2s debounce
- **Properties Panel**: State, priority, assignee, cycle, labels, estimate, dates
- **Activity Timeline**: Infinite scroll comments (50/page), edit history
- **Sub-Issues**: Create child issues, link to parent
- **AI Context** (T211): Aggregated context (related issues, docs, code, tasks)
- **Keyboard Shortcuts**: Cmd+S save, Escape close sidebar

**State Management**:
- **MobX**: `IssueStore` (saveStatus Map, per-field indicators)
- **TanStack Query**: `useIssueDetail()`, `useUpdateIssue()`, `useActivities()`, `useAddComment()`
- **AI Stores**: `AIContextStore` (context generation), `ExtractionStore` (if extracted from note)

**Architecture** (70/30 split):
```
IssueDetailPage
├── IssueHeader (title, AI badge, delete)
├── Main (70%)
│   ├── IssueTitle (click-to-edit)
│   ├── IssueDescriptionEditor (TipTap)
│   ├── SubIssuesList
│   ├── ActivityTimeline (infinite scroll)
│   └── Tabs: AI Context | Details | Linked PRs
└── Sidebar (30%)
    ├── "Details" → IssuePropertiesPanel
    ├── "AI Context" → AIContextTab (dynamic import, SSR=false)
    └── "Linked" → RelatedItemsList
```

**Properties Panel Features**:
- State selector (enforces state machine)
- Priority/Type dropdowns
- Assignee search (workspace members)
- Cycle selector (filters by state constraints)
- Label multiselect
- Estimate (story points)
- Dates (start_at, target_end_at)

**AI Context Features**:
- Generate aggregated context (5m cache)
- Sections: Summary, Related Issues, Docs, Tasks, Claude Code prompt
- Copy to clipboard functionality
- Regenerate option

**Integration Points**:
- **Notes**: Issue links via `NoteIssueLink`
- **GitHub**: PR linking + review comments
- **AI**: Context generation, task decomposition
- **Cycles**: State-cycle constraints, progress metrics

**See Detailed Documentation**: `frontend/src/features/issues/CLAUDE.md`

---

### AI Module

**File Path**: `/frontend/src/features/ai/`

**Purpose**: Unified conversational interface (ChatView), SSE streaming (DD-066), skill invocation (DD-087), human-in-the-loop approvals (DD-003).

**Key Features**:
- **ChatView**: 25-component tree (messages, tasks, approvals)
- **SSE Streaming**: 8+ event types (message_start, text_delta, tool_use, approval_request, etc.)
- **Skills**: Slash commands (/extract-issues, /enhance-issue, etc.)
- **Agents**: @mentions for subagents (@pr-review, @ai-context, @doc-generator)
- **Task Tracking**: Progress bars, phases, estimated time remaining
- **Approvals**: Destructive action overlay (DD-003), 24h expiry countdown
- **Context Switching**: Note/Issue/Project context indicators

**State Management**:
- **MobX**: `PilotSpaceStore` (centralized AI state, all interactions route through here)
  - `messages: ChatMessage[]`
  - `isStreaming: boolean`
  - `tasks: Map<string, TaskState>`
  - `pendingApprovals: ApprovalRequest[]`
  - `noteContext, issueContext, projectContext`
- **Independent**: `GhostTextStore` (fast-path <2.5s SLA, bypasses PilotSpaceStore)

**Architecture**:
```
ChatView (observer)
├── ChatHeader (title, status)
├── MessageList (virtualized)
│   ├── MessageGroup (role-based)
│   ├── UserMessage
│   ├── AssistantMessage
│   ├── ToolCallList
│   ├── StreamingContent (animated indicator)
│   ├── ThinkingBlock
│   └── StructuredResultCard
├── TaskPanel (collapsible)
│   ├── TaskList
│   └── TaskItem (progress bar)
├── StreamingBanner (phase indicator)
├── ApprovalOverlay (DD-003)
│   └── ApprovalDialog (non-dismissable, 24h timer)
└── ChatInput
    ├── SkillMenu (/slash commands)
    ├── AgentMenu (@mentions)
    ├── ContextIndicator (note/issue/project badges)
    └── WorkingIndicator (streaming spinner)
```

**SSE Event Flow**:
```
Backend → SSE Event → PilotSpaceStore.handleEvent() → Specific handler
message_start → Create new message
text_delta → Append to current message (render streaming)
tool_use → Add tool call card
tool_result → Update tool card + task panel
content_update → useContentUpdates() (editor modifications)
approval_request → Show ApprovalOverlay modal
task_progress → Update TaskPanel progress
message_stop → Clear streaming state
error → Toast notification
```

**Approval Flow** (DD-003):
```
AI requests approval (destructive operation)
→ ApprovalOverlay modal appears (non-dismissable)
→ Shows operation preview + risk assessment
→ 24-hour countdown timer
→ User approves/rejects
→ Backend executes or discards
→ SSE event confirms to frontend
```

**Skill Invocation**:
```
User types "/extract-issues"
→ SDK detects skill intent
→ Skill executes (calls MCP tool if needed)
→ MCP tool returns operation payload
→ Backend applies transformations
→ SSE content_update event
→ Frontend updates UI
```

**Integration Points**:
- **Notes**: Context switching, content updates
- **Issues**: AI context generation, task decomposition
- **Approvals**: Destructive action overlay
- **Settings**: Skill configuration
- **Costs**: Token tracking (per agent, per provider)

**See Detailed Documentation**: `frontend/src/features/ai/CLAUDE.md`

---

### Approvals Module

**File Path**: `/frontend/src/features/approvals/`

**Purpose**: Human-in-the-loop approval UI for AI-generated actions (DD-003).

**Approval Categories**:
- **Non-Destructive** (auto-execute, notify): Add label, transition state
- **Content Creation** (require approval, configurable): Extract issues, post comment
- **Destructive** (always require approval, non-dismissable): Delete issue, merge PR

**Key Features**:
- **Approval Queue**: 5 tabs (Pending, Approved, Rejected, Expired, All)
- **Card View**: Status badge, action type, context preview, quick actions
- **Detail Modal**: Full metadata, risk assessment, payload preview, note field
- **24-Hour Expiry**: Countdown timer, auto-expired state
- **Risk Assessment**: Color-coded risk level (green/yellow/red)

**State Management**:
- **MobX**: `ApprovalStore` (approval list, pending count, filter state)

**Architecture**:
```
ApprovalQueuePage
├── Tabs (Pending | Approved | Rejected | Expired | All)
├── ApprovalCard (card view, default)
│   ├── Status badge
│   ├── Action type badge
│   ├── Context preview (2 lines max)
│   ├── Metadata (agent, requested_by, created)
│   ├── Expiration countdown
│   └── Quick action buttons (Approve/Reject if pending)
└── ApprovalDetailModal (on card click)
    ├── Header (title, status, description)
    ├── Metadata grid
    ├── RiskAssessment (color-coded)
    ├── PayloadPreview (JSON)
    ├── Note textarea (optional)
    ├── Expiration warning
    └── Approve/Reject buttons
```

**API Integration**:
```
GET /api/v1/ai/approvals?status=pending|approved|rejected|expired
POST /api/v1/ai/approvals/{id}/resolve
  Body: { approved: boolean, note?: string, selected_issues?: number[] }
```

**Integration Points**:
- **PilotSpaceStore**: Emits `approval_request` SSE event
- **Router**: `/[workspaceSlug]/approvals`
- **Shell**: Shows pending approval badge in header

**See Detailed Documentation**: `frontend/src/features/approvals/CLAUDE.md`

---

### Cycles Module

**File Path**: `/frontend/src/features/cycles/`

**Purpose**: Sprint/cycle management with state-cycle constraints, burndown visualization, velocity tracking.

**Key Features**:
- **CRUD**: Create, update, delete, activate, complete cycles
- **State-Cycle Constraints**: Enforced at frontend + backend
  - Backlog: No cycle
  - Todo: Cycle optional
  - In Progress: Cycle required (active only)
  - In Review: Cycle required (active only)
  - Done: Removed from cycle
  - Cancelled: Removed immediately
- **Burndown Chart**: X-axis days, Y-axis remaining points, ideal vs actual line
- **Velocity Chart**: Last 5 cycles, points completed per cycle
- **Cycle Selector**: Quick assignment, validation logic

**State Management**:
- **MobX**: `CycleStore` (cycle list, active cycle, filtering)
- **TanStack Query**: `useCycle()`, `useCycles()`, `useCycleBurndown()`, `useVelocity()`

**Architecture**:
```
CycleDetailPage
├── CycleHeader (name, status badge, dates)
├── Charts section
│   ├── BurndownChart (50% width)
│   └── VelocityChart (50% width)
└── IssuesInCycle (filtered by cycle)
```

**Frontend Constraint Enforcement**:
```typescript
// When transitioning to In Progress
if (newState === 'in_progress' && !issue.cycle_id) {
  showError('In Progress issues must be assigned to a cycle');
  return;
}

// CycleSelector disables non-active cycles
<CycleSelector disabled={state === 'in_progress' && !isActiveCycle} />
```

**Integration Points**:
- **Issues**: State transitions, property panel
- **Homepage**: Activity indicators (cycle progress)
- **Velocity metrics**: Project health dashboard

**See Detailed Documentation**: `frontend/src/features/cycles/CLAUDE.md`

---

### Homepage Module

**File Path**: `/frontend/src/features/homepage/`

**Purpose**: Primary landing page (Note-First workflow, DD-013). Three zones: compact chat, activity feed, AI digest.

**Key Features** (H047):
- **Compact ChatView** (Zone 1): Collapsed 48px, expands 400px on click
- **Activity Feed** (Zone 2): Recent notes/issues grouped by time (Today, Yesterday, This Week), infinite scroll
- **AI Digest** (Zone 3): 12 suggestion categories (stale issues, missing docs, duplicates, etc.)

**State Management**:
- **MobX**: `HomepageUIStore` (chat expanded state, active zone for F6 cycling)
- **TanStack Query**: `useHomepageActivity()` (infinite query), `useWorkspaceDigest()` (5m cache)

**Architecture** (Desktop 3-col, Mobile stacked):
```
HomepageHub
├── CompactChatView (collapsed/expanded toggle)
│   ├── CompactChatInput (48px bar)
│   └── CompactChatPanel (expanded overlay)
│       ├── CompactMessageList
│       └── CompactChatInput
├── ActivityFeed (infinite scroll)
│   ├── DayGroupHeader (Today, Yesterday, etc.)
│   ├── NoteActivityCard (title, project, word count, updated)
│   └── IssueActivityCard (ID, title, state badge, priority)
└── DigestPanel (suggestions)
    ├── DigestSuggestionCard (with relevance score, dismiss)
    └── Refresh button (2s debounce)
```

**Digest Categories**:
1. Stale Issues (14+ days)
2. Missing Documentation
3. Inconsistent Status
4. Blocked Dependencies
5. Unassigned Work
6. Overdue Cycle Items
7. PR Review Pending
8. Duplicate Candidates
9. Note Refinement
10. Project Health
11. Knowledge Gaps
12. Release Readiness

**Keyboard Shortcuts**:
- `/` → Focus chat input
- `F6` → Cycle to next zone
- `Shift+F6` → Cycle to previous zone
- `Escape` → Close expanded chat

**Accessibility** (WCAG 2.2 AA):
- ARIA landmarks for 3 zones
- Keyboard navigation (Tab, Enter, Escape)
- Focus management (trap in modal)
- Reduced motion support

**Integration Points**:
- **Notes**: Activity feed, draft indicator
- **Issues**: Activity feed, state changes
- **AI Chat**: PilotSpaceStore context switching
- **Onboarding**: Show onboarding checklist until completed

**See Detailed Documentation**: `frontend/src/features/homepage/CLAUDE.md`

---

### GitHub Integration Module

**File Path**: `/frontend/src/features/github/`

**Purpose**: PR review, linking, OAuth integration (DD-004: GitHub + Slack only in MVP).

**Key Features**:
- **OAuth Flow**: User authorization → token exchange → Supabase Vault encryption
- **Repository Management**: List repos, sync toggle, webhook status
- **PR Linking**: Search by repo:PR# → link to issue → view status
- **AI PR Review**: GitHub webhook → PRReviewAgent → Comments by aspect (architecture, security, quality, docs)
- **Severity Tags**: 🔴 Critical, 🟡 Warning, 🟢 Info

**State Management**:
- **MobX**: `GitHubStore` (connection status, repos, linked PRs)
- **TanStack Query**: `useGitHubAuth()`, `useGitHubRepos()`, `usePRReview()`

**Architecture**:
```
GitHubSettingsPage
├── OAuth button (Connect/Disconnect)
├── Connection status (Connected/Error/Connecting)
├── RepositoryList
│   └── RepoRow (sync toggle, webhook status)
├── LinkedPRsSection (in issue detail sidebar)
│   └── PR search + link/unlink actions
└── PRReviewPanel (in issue detail)
    ├── Review status badge
    └── Comments by aspect (collapsible)
```

**Webhook Flow**:
```
GitHub PR opened/updated
→ Webhook to /webhooks/github
→ Queue PR for review (pgmq)
→ PRReviewAgent analyzes (Claude Opus)
→ Posts comments to GitHub
→ SSE notification to frontend
→ Badge update in UI
```

**Integration Points**:
- **Issues**: PR linking in properties panel
- **Settings**: OAuth configuration (AI Providers page)
- **Activities**: PR events in activity feed

**See Detailed Documentation**: `frontend/src/features/github/CLAUDE.md`

---

### Integrations Module

**File Path**: `/frontend/src/features/integrations/`

**Purpose**: Support for PR review integration (currently GitHub, extensible for future integrations).

**Key Features**:
- `usePRReview()`: Query PR review results
- `usePRReviewStatus()`: Real-time review status

**State Management**:
- **TanStack Query**: PR review queries

**Integration Points**:
- **GitHub**: PR review data
- **Issues**: PR review badges

---

### Settings Module

**File Path**: `/frontend/src/features/settings/`

**Purpose**: Workspace configuration, member management, AI provider setup, user profile, AI skills.

**Key Features**:
- **Workspace General**: Edit name/slug/description, delete (owner-only)
- **Member Management**: List, invite, change roles, remove (admin+)
- **AI Providers**: API keys (Anthropic, OpenAI), feature toggles (5 switches)
- **User Profile**: Display name, avatar, email
- **AI Skills**: Create/edit/regenerate/remove role-based skills (max 3 per workspace)

**Permission Model** (4-tier):
- **Owner**: Full control
- **Admin**: Manage members, settings, AI config
- **Member**: View/toggle (if keys set), edit skills
- **Guest**: Read-only

**State Management**:
- **MobX**: `AISettingsStore`, `WorkspaceStore`, `AuthStore`
- **TanStack Query**: `useWorkspaceSettings()`, `useWorkspaceMembers()`, `useWorkspaceInvitations()`

**Architecture** (5 pages):
```
SettingsPage (router root)
├── WorkspaceGeneralPage (name, slug, description, delete)
├── MembersSettingsPage (list, invite, roles, remove)
├── AISettingsPage (API keys, toggles, provider status)
├── ProfileSettingsPage (display name, email, avatar)
└── SkillsSettingsPage (max 3 skills, create/edit/regenerate)
```

**API Key Validation**:
- Anthropic: `sk-ant-*`, min 10 chars
- OpenAI: `sk-*`, min 10 chars
- All keys encrypted via Supabase Vault (AES-256-GCM)

**Integration Points**:
- **RLS**: Database-level permission enforcement
- **Supabase Vault**: API key encryption
- **AI Layer**: Feature toggles affect agent behavior

**See Detailed Documentation**: `frontend/src/features/settings/CLAUDE.md`

---

### Costs Module

**File Path**: `/frontend/src/features/costs/`

**Purpose**: AI cost tracking and analytics (provider routing insights per DD-011).

**Key Features**:
- **Cost Dashboard**: Summary cards + 2 charts + user table
- **Cost Trends**: Daily cost line chart (AreaChart)
- **Cost by Agent**: Provider distribution donut chart
- **User Cost Table**: Sortable, user attribution
- **Date Range**: Presets (Today, Last 7/30/90 days, This month)

**Provider Routing** (DD-011):
| Agent | Provider | Model | Use Case |
|-------|----------|-------|----------|
| pilot_space_agent | Anthropic | Claude Opus | Orchestration |
| ghost_text_agent | Google | Gemini Flash | Inline completions |
| pr_review_agent | Anthropic | Claude Opus | Code analysis |
| ai_context_agent | Anthropic | Claude Sonnet | Context aggregation |

**State Management**:
- **MobX**: `CostStore` (summary data, date range, loading state)

**Architecture**:
```
CostDashboardPage
├── DateRangeSelector (presets)
├── 4 Summary Cards
│   ├── Total Cost (with trend %)
│   ├── Total Requests
│   ├── Total Tokens
│   └── Avg Cost/Request
├── CostTrendsChart (daily line chart)
├── CostByAgentChart (provider donut)
└── CostTableView (user attribution, sortable)
```

**API Integration**:
```
GET /workspaces/{workspace_id}/ai/costs/summary
  Query: { start_date: YYYY-MM-DD, end_date: YYYY-MM-DD }
  Response: CostSummary (by_agent, by_user, by_day)
```

**Business Context**:
- BYOK (Bring Your Own Key) — users provide API keys
- Backend tracks tokens (prompt/completion/cached) + USD costs
- Frontend displays cost insights without storing keys
- Cost tracking per agent enables provider routing optimization

**Integration Points**:
- **AI Layer**: Token usage logging
- **Settings**: API key configuration
- **Dashboard**: Cost visibility for admins

**See Detailed Documentation**: `frontend/src/features/costs/CLAUDE.md`

---

### Onboarding Module

**File Path**: `/frontend/src/features/onboarding/`

**Purpose**: 3-step workspace setup (role selection, skill generation, completion celebration).

**Key Features**:
- **Step 1**: User role selection (developer, manager, designer, custom)
- **Step 2**: AI skill generation (generate 3 persona-specific skills)
- **Step 3**: Completion celebration + redirect to homepage

**State Management**:
- **MobX**: `OnboardingStore` (current step, selected role, skills)
- **TanStack Query**: `useOnboardingState()`, `useRoleSkillActions()`

**Architecture**:
```
OnboardingFlow
├── OnboardingChecklist (top nav, step indicators)
├── RoleSelectorStep (radio buttons)
├── SkillGenerationWizard (async generation, 3 skills)
│   ├── SkillGenerationStep (loading phases)
│   └── SkillCard (editable, regenerate option)
└── OnboardingCelebration (confetti, next steps)
```

**Integration Points**:
- **Settings**: Skills created via `/api/v1/skills` endpoint
- **Homepage**: Shown until onboarding completed
- **Auth**: Triggered on first workspace creation

---

## Common Implementation Patterns

### Pattern 1: Optimistic Updates with Rollback

**State sync on mutation**, with instant UI feedback and automatic rollback on error:

```typescript
const mutation = useMutation({
  mutationFn: (data) => issuesApi.update(issueId, data),
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: issueDetailKeys.detail(issueId) });
    const previousData = queryClient.getQueryData(issueDetailKeys.detail(issueId));
    queryClient.setQueryData(issueDetailKeys.detail(issueId), (old) => ({ ...old, ...newData }));
    return { previousData };
  },
  onError: (_, __, context) => {
    queryClient.setQueryData(issueDetailKeys.detail(issueId), context?.previousData);
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: issueDetailKeys.detail(issueId) }),
});
```

See `docs/dev-pattern/` for detailed query key factory patterns, MobX reactions, and SSE streaming examples.

---

## Pre-Submission Checklist

**Before submitting**, verify:

- [ ] File size <700 lines | MobX/TanStack split correct | No API data in MobX
- [ ] observer() wrapper on MobX components | Props documented | Tailwind styling only
- [ ] Keyboard nav functional | ARIA labels present | Focus management correct
- [ ] Dynamic imports for large components | No unnecessary re-renders
- [ ] Conventional commit with descriptive body
- [ ] Tests written for new features (>80% coverage)

---

## Troubleshooting Guide

| Issue | Cause | Fix |
|-------|-------|-----|
| Component not re-rendering on store update | Missing `observer()` wrapper | Wrap with `observer(function Component() { ... })` |
| Query not refetching after mutation | Invalidation key mismatch | Ensure `queryKey` in invalidation matches `useQuery` key exactly |
| Infinite scroll not triggering | Sentinel not visible or IntersectionObserver not set | Verify sentinel ref is appended, observer threshold correct |
| SSE connection dropping | Token expiration or network timeout | Refresh token before SSE connect, implement exponential backoff retry |
| Ghost text not triggering | Debounce not 500ms or callback missing | Check `debounceMs: 500` in config, verify `onTrigger` callback defined |
| Block IDs lost after AI edit | BlockIdExtension running before content update | Ensure BlockIdExtension is last in extension array |

---

## Learning Resources

**In this codebase**:
- Main docs: `/CLAUDE.md`, `frontend/CLAUDE.md`
- Design decisions: `docs/DESIGN_DECISIONS.md` (DD-065 state split, DD-003 approvals)
- Dev patterns: `docs/dev-pattern/45-pilot-space-patterns.md`

**External**: [MobX](https://mobx.js.org/) | [TanStack Query](https://tanstack.com/query/latest) | [React](https://react.dev/) | [Next.js](https://nextjs.org/docs) | [TipTap](https://tiptap.dev/)

---

## Generation Metadata

- **Files Analyzed**: 40+ feature files
- **Modules Documented**: 10 (notes, issues, ai, approvals, cycles, homepage, github, integrations, settings, costs, onboarding)
- **Components Cataloged**: 100+
- **Hooks Cataloged**: 50+
- **Patterns Identified**: 20+ common patterns (state split, optimistic updates, infinite scroll, SSE, etc.)
- **Coverage Gaps**: Onboarding documentation (sparse), integrations module (minimal docs)
- **Suggested Next Steps**:
  1. Create component library documentation (shadcn/ui customizations)
  2. Document test patterns & mocking strategies
  3. Create performance tuning guide
  4. Document advanced MobX patterns (reactions, computed, etc.)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-10
**Audience**: Frontend developers, new team members, feature reviewers
**Next Review**: Post-Phase 8 completion (March 2026)

