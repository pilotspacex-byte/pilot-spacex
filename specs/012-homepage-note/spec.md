# Feature Specification: Homepage Hub (US-19)

**Feature Branch**: `012-homepage-note`
**Created**: 2026-02-06
**Status**: Draft
**Priority**: P1 (MVP Enhancement)
**Scope**: Replace static welcome page with productive Homepage Hub
**Parent Spec**: `specs/001-pilot-space-mvp/spec.md` (extends US-01 Note-First workflow)
**Design Decisions**: DD-013 (Note-First Workspace), DD-065 (MobX UI + TanStack Query), DD-066 (SSE Streaming), DD-086 (Centralized Agent)

---

## Problem Statement

The current homepage (`/[workspaceSlug]`) displays a static welcome screen with a compass icon, a greeting ("What would you like to work on?"), and a single "Create a note" CTA with display-only template cards. This page provides no productivity value -- users must navigate away before doing any real work.

**Current flow**: Land on welcome page -> Click "Create a note" -> Navigate to Notes List -> Click "New Note" -> Start writing.

**Pain points**:
- 3 navigation steps before productive work begins
- No visibility into recent work or workspace activity
- No AI assistance until inside a note editor
- No quick capture mechanism for fleeting ideas
- No workspace health overview or AI-driven suggestions

---

## Solution: Homepage Hub

Replace the static welcome page with a three-zone productive homepage:

```
+--------------------------------------------------------------+
|  SIDEBAR  |        HOMEPAGE HUB                               |
|           | +-------------------------------------------+     |
|           | |  ZONE 1: Compact ChatView                 |     |
|           | |  (expand-on-focus input bar)               |     |
|           | |  Quick note capture + AI clarification     |     |
|           | +-------------------------------------------+     |
|           |                                                   |
|           | +-------------------------+ +-------------------+ |
|           | | ZONE 2: Recent Activity | | ZONE 3: AI Digest | |
|           | | Notes & Issues cards    | | Project insights  | |
|           | | Grouped by day          | | Hourly refresh    | |
|           | | With AI annotations     | | Quick actions     | |
|           | +-------------------------+ +-------------------+ |
+--------------------------------------------------------------+
```

### Zone 1: Compact ChatView (Top)
An expand-on-focus input bar for quick AI conversations. Users can:
- Capture a quick idea in natural language
- Clarify thinking with PilotSpaceAgent in 2-5 message exchanges
- Receive a "Create Note" suggestion when ideas are ready for full editing
- Navigate to the full Note Editor with conversation context seeded as initial content AND linked as chat history

### Zone 2: Recent Activity Feed (Bottom-Left)
Cards showing recent notes and in-progress issues, grouped by day (Today, Yesterday, This Week):
- **Note cards**: title, project, topic tags, word count, last AI annotation summary, updated timestamp
- **Issue cards**: identifier (PS-123), title, project, state badge, priority indicator, assignee avatar, last activity summary
- Each card shows the most recent AI annotation as a subtle inline preview
- Click navigates to the full entity view

### Zone 3: AI Digest Panel (Bottom-Right)
AI-generated workspace insights refreshed hourly by background job:
- Actionable suggestions with quick-action buttons or navigation links
- Workspace-wide analysis ranked by relevance to the current user
- Categorized suggestion types (see AI Digest Categories below)

### Constitution Compliance Note (Principle II)

Constitution Principle II states: "Note canvas MUST be the default home view for capturing rough ideas." The Homepage Hub satisfies this principle in spirit by serving as the **gateway into Note-First workflow**:

1. **Compact ChatView** (Zone 1) provides AI-assisted idea capture — the first step of the Note-First flow ("Rough Ideas → AI Clarification"). Ideas captured here flow directly into full Note Canvas via the chat-to-note creation path.
2. **Recent Activity Feed** (Zone 2) surfaces notes with AI annotations, encouraging users to return to in-progress notes for continued refinement.
3. The homepage does **not** replace the Note Canvas (US-01) — it provides a faster on-ramp to it. The full Note Editor remains the primary workspace for extended writing and issue extraction.

This is an intentional evolution: the static welcome page provided zero Note-First value, while the Homepage Hub makes AI-assisted thinking the immediate entry point on every session. The Note Canvas remains accessible via sidebar navigation and is the destination of all chat-to-note flows.

---

## User Story 19 - Homepage Hub (Priority: P1)

A developer, tech lead, or PM opens Pilot Space and immediately sees a productive hub where they can capture quick ideas with AI assistance, review recent work with AI annotations, and act on AI-generated workspace insights -- all without navigating away from the homepage.

**Why this priority**: The homepage is the first screen every user sees on every session. A productive homepage reduces time-to-first-action from ~15 seconds (3 navigation clicks) to ~2 seconds (start typing). It reinforces the Note-First philosophy by making AI-assisted thinking the default entry point.

**Relationship to US-01**: US-01 defines the full Note Canvas editor experience. US-19 provides the quick-capture entry point that leads into US-01. The Compact ChatView is a lightweight version of the ChatView already used in the Note Editor (65/35 split).

---

## Acceptance Scenarios

### Zone 1: Compact ChatView

**AS-01**: **Given** a user opens the homepage, **When** the page loads, **Then** a compact input bar is visible at the top with placeholder text "What's on your mind? Start typing to chat with PilotSpace AI..." and the input is not auto-focused (user must click/tab to focus).

**AS-02**: **Given** the compact input bar is idle, **When** the user clicks or tabs into it, **Then** the bar expands upward into a compact chat panel (max height 400px) with the input at the bottom and a message area above, using a 200ms ease-out animation.

**AS-03**: **Given** the chat panel is expanded, **When** the user types a message and presses Enter, **Then** PilotSpaceAgent responds via SSE streaming with the same event types as the full ChatView (text_delta, tool_use, etc.).

**AS-04**: **Given** the user has exchanged 2+ messages with the AI, **When** the conversation contains substantive content (AI detects actionable ideas), **Then** the AI suggests "Would you like me to create a note from this conversation?" as an inline suggestion card.

**AS-05**: **Given** the AI suggests creating a note, **When** the user accepts, **Then** a new note is created with:
- Title extracted from conversation themes
- Content blocks pre-filled from key points in the conversation (AI-structured)
- A linked chat session reference for traceability
- The user is navigated to the full Note Editor (`/[workspaceSlug]/notes/[noteId]`)

**AS-06**: **Given** the user accepts note creation, **When** viewing the new note in the editor, **Then** a "Created from homepage chat" badge appears in the note header with a link to view the source conversation.

**AS-07**: **Given** the chat panel is expanded, **When** the user clicks outside the panel or presses Escape, **Then** the panel collapses back to the compact input bar (200ms ease-in), preserving the conversation state for the current session.

**AS-08**: **Given** the chat panel has an active conversation, **When** the user navigates away and returns to the homepage within the same browser session, **Then** the conversation is restored (session persistence via PilotSpaceStore).

**AS-09**: **Given** the chat panel is expanded on mobile (<768px), **When** the panel expands, **Then** it renders as a bottom sheet (full-width, 60% viewport height) with swipe-down to dismiss.

### Zone 2: Recent Activity Feed

**AS-10**: **Given** a user views the homepage, **When** the page loads, **Then** the Recent Activity section displays cards grouped by day: "Today", "Yesterday", "This Week", with a maximum of 20 cards initially loaded.

**AS-11**: **Given** recent activity cards are displayed, **When** viewing a note card, **Then** it shows: note title, project name badge, topic tags (max 3), word count, the most recent AI annotation as a one-line preview (truncated at 80 chars), and relative timestamp ("2h ago").

**AS-12**: **Given** recent activity cards are displayed, **When** viewing an issue card, **Then** it shows: issue identifier (PS-123), title, project name badge, state color badge, priority indicator bar, assignee avatar, last activity summary (e.g., "State changed to In Review"), and relative timestamp.

**AS-13**: **Given** a card has an AI annotation, **When** the user hovers over the annotation preview, **Then** a tooltip shows the full annotation text with its type icon (suggestion, warning, issue_candidate).

**AS-14**: **Given** a user clicks a note card, **When** navigating, **Then** the user is taken to the Note Editor (`/[workspaceSlug]/notes/[noteId]`).

**AS-15**: **Given** a user clicks an issue card, **When** navigating, **Then** the user is taken to the Issue Detail page (`/[workspaceSlug]/issues/[issueId]`).

**AS-16**: **Given** more than 20 recent items exist, **When** the user scrolls to the bottom of the activity feed, **Then** additional cards load via infinite scroll (cursor-based pagination).

**AS-17**: **Given** a new note or issue is created/updated in the workspace, **When** the user is on the homepage, **Then** the activity feed updates in real-time via Supabase Realtime broadcast without page refresh.

### Zone 3: AI Digest Panel

**AS-18**: **Given** a user views the homepage, **When** the AI Digest panel loads, **Then** it shows the most recent digest generation timestamp ("Last updated 45 min ago") and a manual "Refresh" button.

**AS-19**: **Given** the AI Digest has generated suggestions, **When** viewing the panel, **Then** suggestions are displayed as cards grouped by category with an icon, title, description (1-2 lines), affected entity link, and action button.

**AS-20**: **Given** a digest suggestion has a quick action (e.g., "Create Issue"), **When** the user clicks the action button, **Then** the action executes inline (e.g., opens issue creation modal pre-filled with AI suggestion) without navigating away from the homepage.

**AS-21**: **Given** a digest suggestion requires navigation (e.g., "Review PR #42"), **When** the user clicks the action button, **Then** the user navigates to the relevant entity page.

**AS-22**: **Given** a user dismisses a digest suggestion, **When** clicking the dismiss icon, **Then** the suggestion is removed from the panel and will not reappear in future digest generations for that entity.

**AS-23**: **Given** no AI providers are configured for the workspace, **When** loading the AI Digest panel, **Then** a helpful empty state is shown: "Configure an AI provider in Settings to enable workspace insights" with a link to Settings > AI Providers.

**AS-24**: **Given** the background digest job runs hourly, **When** generating suggestions, **Then** the job analyzes workspace-wide data (all projects, issues, notes, integrations) and ranks suggestions by relevance to the current user (assigned items, created items, frequently accessed projects).

**AS-25**: **Given** the digest has been generated, **When** the user clicks "Refresh", **Then** a new digest generation is triggered on-demand (not waiting for the hourly schedule), showing a loading skeleton during generation.

### Cross-Zone Interactions

**AS-26**: **Given** the homepage has all three zones, **When** the Compact ChatView expands, **Then** Zones 2 and 3 remain visible below (the page scrolls if needed) -- the chat panel does not overlay the activity feed.

**AS-27**: **Given** the user is on the homepage, **When** they press `/` (slash), **Then** focus moves to the Compact ChatView input bar (keyboard shortcut for quick access).

**AS-28**: **Given** the homepage is viewed on tablet (768-1023px), **When** the layout renders, **Then** Zone 2 and Zone 3 stack vertically (full-width each) instead of side-by-side.

---

## AI Digest Categories

The background AI Digest job generates suggestions in these categories:

| Category | Icon | Description | Quick Action | Examples |
|----------|------|-------------|--------------|----------|
| **Stale Issues** | `Clock` | Issues not updated for >7 days in active cycle | Navigate to issue | "PS-42 hasn't been updated in 9 days. Is it still in progress?" |
| **Missing Documentation** | `FileWarning` | Issues marked Done without linked docs/notes | Create note | "PS-38 was completed but has no linked documentation" |
| **Inconsistent Status** | `AlertTriangle` | Issues with mismatched state vs activity | Navigate to issue | "PS-55 is 'In Progress' but last commit was 12 days ago" |
| **Blocked Dependencies** | `GitBranch` | Issues blocked by other issues not progressing | Navigate to blocker | "PS-60 is blocked by PS-45 which hasn't moved in 5 days" |
| **Unassigned Work** | `UserPlus` | High/urgent priority issues without assignee | Assign (modal) | "3 high-priority issues in Sprint 4 have no assignee" |
| **Overdue Cycle Items** | `CalendarClock` | Active cycle ending within 2 days with incomplete items | Navigate to cycle | "Sprint 4 ends in 2 days with 5 incomplete items" |
| **PR Review Pending** | `GitPullRequest` | Open PRs without AI review for >4 hours | Trigger review | "PR #87 has been open for 6 hours without review" |
| **Duplicate Candidates** | `Copy` | Newly created issues with >70% similarity to existing | Navigate to comparison | "PS-72 may be a duplicate of PS-31 (82% match)" |
| **Note Refinement** | `Sparkles` | Notes with unresolved AI annotations or unextracted issues | Navigate to note | "Your 'Auth Refactor' note has 4 unreviewed AI suggestions" |
| **Project Health** | `Activity` | Weekly project velocity trends and anomalies | Navigate to project | "Project Alpha velocity dropped 40% this sprint" |
| **Knowledge Gaps** | `BookOpen` | Topics referenced in issues without linked documentation | Create note | "5 issues reference 'payment gateway' but no docs exist" |
| **Release Readiness** | `Package` | Cycle completion analysis with risk assessment | Navigate to cycle | "Sprint 4 is 72% complete -- 2 critical items remain" |

---

## Functional Requirements

### Homepage Layout

- **FR-200**: System MUST replace the static welcome page with the Homepage Hub as the default view for `/[workspaceSlug]`
- **FR-201**: System MUST render three zones: Compact ChatView (top), Recent Activity Feed (bottom-left), AI Digest Panel (bottom-right)
- **FR-202**: System MUST maintain the existing sidebar navigation unchanged (Home, Notes, Issues, Projects)
- **FR-203**: System MUST use responsive layout: side-by-side Zones 2+3 on desktop (>=1024px), stacked on tablet/mobile (<1024px)

### Compact ChatView

- **FR-204**: System MUST display a compact input bar that expands into a chat panel on focus
- **FR-205**: System MUST stream PilotSpaceAgent responses via SSE with the same event types as the full ChatView
- **FR-206**: System MUST detect substantive conversation content and suggest note creation after 2+ message exchanges
- **FR-207**: System MUST create notes with AI-structured content from conversation AND link to source chat session
- **FR-208**: System MUST preserve conversation state within the browser session (PilotSpaceStore)
- **FR-209**: System MUST collapse the chat panel on outside click or Escape, preserving state
- **FR-210**: System MUST render the chat panel as a bottom sheet on mobile (<768px)

### Recent Activity Feed

- **FR-211**: System MUST display recent notes and issues grouped by day (Today, Yesterday, This Week)
- **FR-212**: System MUST show note cards with: title, project badge, topic tags, word count, latest AI annotation preview, relative timestamp
- **FR-213**: System MUST show issue cards with: identifier, title, project badge, state badge, priority indicator, assignee avatar, last activity summary, relative timestamp
- **FR-214**: System MUST support infinite scroll with cursor-based pagination (20 items per page)
- **FR-215**: System MUST update the activity feed in real-time via Supabase Realtime
- **FR-216**: System MUST link note cards to Note Editor and issue cards to Issue Detail page

### AI Digest Panel

- **FR-217**: System MUST generate workspace digest suggestions via hourly background job (pg_cron)
- **FR-218**: System MUST rank suggestions by relevance to the current user (assignments, creations, access frequency)
- **FR-219**: System MUST support quick actions (inline) for simple operations and navigation for complex ones
- **FR-220**: System MUST allow dismissing suggestions (persisted, excluded from future digests for that entity)
- **FR-221**: System MUST support on-demand digest refresh via manual trigger
- **FR-222**: System MUST display empty state when no AI provider is configured
- **FR-223**: System MUST categorize suggestions with icons and group by category
- **FR-224**: System MUST analyze: stale issues, missing docs, inconsistent status, blocked deps, unassigned work, overdue cycles, pending PR reviews, duplicate candidates, note refinement, project health, knowledge gaps, release readiness

### Keyboard & Accessibility

- **FR-225**: System MUST support `/` keyboard shortcut to focus Compact ChatView input from homepage
- **FR-226**: System MUST ensure all three zones are keyboard navigable with F6 cycling between zones
- **FR-227**: System MUST provide ARIA landmarks for each zone (role="region" with aria-label)
- **FR-228**: System MUST support screen readers with descriptive labels for all card metadata
- **FR-229**: System MUST respect `prefers-reduced-motion` for expand/collapse animations

---

## Data Model Extensions

### New Entity: `workspace_digests`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `workspace_id` | UUID (FK) | Parent workspace |
| `generated_at` | DateTime | Generation timestamp |
| `generated_by` | String(20) | "scheduled" or "manual" |
| `suggestions` | JSONB | Array of digest suggestion objects |
| `model_used` | String(50) | AI model identifier |
| `token_usage` | JSONB | `{input_tokens, output_tokens, cost_usd}` |
| `created_at` | DateTime | Record creation |

### New Entity: `digest_dismissals`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Unique identifier |
| `workspace_id` | UUID (FK) | Parent workspace |
| `user_id` | UUID (FK) | User who dismissed |
| `suggestion_category` | String(30) | Category (e.g., "stale_issues") |
| `entity_id` | UUID | Dismissed entity reference |
| `entity_type` | String(20) | "issue", "note", "cycle", "pr" |
| `dismissed_at` | DateTime | Dismissal timestamp |

### Digest Suggestion Object (JSONB)

```json
{
  "id": "uuid",
  "category": "stale_issues",
  "icon": "Clock",
  "title": "Stale issue in Sprint 4",
  "description": "PS-42 hasn't been updated in 9 days",
  "entity_id": "uuid",
  "entity_type": "issue",
  "entity_identifier": "PS-42",
  "project_id": "uuid",
  "project_name": "Project Alpha",
  "action_type": "navigate",
  "action_label": "View Issue",
  "action_route": "/workspace/issues/uuid",
  "relevance_score": 0.85,
  "generated_at": "2026-02-06T10:00:00Z"
}
```

### Extended Entity: `notes` (add field)

| Column | Type | Description |
|--------|------|-------------|
| `source_chat_session_id` | UUID (FK, nullable) | Chat session that generated this note (homepage quick capture) |

### New Entity: `chat_sessions`

New table required for chat session persistence (does not exist in current codebase — verified):

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Session identifier |
| `workspace_id` | UUID (FK) | Parent workspace |
| `user_id` | UUID (FK) | Session owner |
| `agent_type` | String(30) | "pilot_space", "ghost_text", "homepage_chat" |
| `context_type` | String(20) | "homepage", "note_editor", "issue_detail", "standalone" |
| `context_entity_id` | UUID (nullable) | Linked entity (note_id, issue_id) |
| `title` | String(255, nullable) | Auto-generated or user-set session title |
| `message_count` | Integer | Count of messages |
| `expires_at` | DateTime | TTL (24h from last activity) |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last activity timestamp |

---

## API Endpoints

### Homepage Data

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v1/workspaces/{id}/homepage/activity` | Recent notes + issues for activity feed | JWT + RLS |
| `GET` | `/api/v1/workspaces/{id}/homepage/digest` | Latest AI digest suggestions | JWT + RLS |
| `POST` | `/api/v1/workspaces/{id}/homepage/digest/refresh` | Trigger on-demand digest generation | JWT + RLS |
| `POST` | `/api/v1/workspaces/{id}/homepage/digest/dismiss` | Dismiss a digest suggestion | JWT + RLS |

### Activity Feed Endpoint

```
GET /api/v1/workspaces/{workspace_id}/homepage/activity
  ?cursor={string}       # Pagination cursor
  &limit={int}           # Items per page (default 20, max 50)

Response:
{
  "data": {
    "today": [ActivityCard, ...],
    "yesterday": [ActivityCard, ...],
    "this_week": [ActivityCard, ...]
  },
  "meta": {
    "total": 47,
    "cursor": "eyJ0IjoiMjAyNi0wMi0wNVQxMDowMDowMFoifQ",
    "has_more": true
  }
}

ActivityCard (Note):
{
  "type": "note",
  "id": "uuid",
  "title": "Auth Refactor Notes",
  "project": {"id": "uuid", "name": "Project Alpha", "identifier": "PA"},
  "topics": ["security", "architecture"],
  "word_count": 1250,
  "latest_annotation": {
    "type": "suggestion",
    "content": "Consider adding rate limiting to the new auth flow",
    "confidence": 0.82
  },
  "updated_at": "2026-02-06T09:30:00Z",
  "is_pinned": false
}

ActivityCard (Issue):
{
  "type": "issue",
  "id": "uuid",
  "identifier": "PS-42",
  "title": "Implement JWT refresh token rotation",
  "project": {"id": "uuid", "name": "Pilot Space", "identifier": "PS"},
  "state": {"name": "In Progress", "color": "#D9853F", "group": "started"},
  "priority": "high",
  "assignee": {"id": "uuid", "name": "Tin", "avatar_url": "..."},
  "last_activity": "State changed to In Progress",
  "updated_at": "2026-02-06T08:15:00Z"
}
```

### Digest Endpoints

```
GET /api/v1/workspaces/{workspace_id}/homepage/digest

Response:
{
  "data": {
    "generated_at": "2026-02-06T10:00:00Z",
    "generated_by": "scheduled",
    "suggestions": [DigestSuggestion, ...],
    "suggestion_count": 8
  }
}

POST /api/v1/workspaces/{workspace_id}/homepage/digest/refresh

Response:
{
  "data": {
    "status": "generating",
    "estimated_seconds": 15
  }
}
# SSE stream follows for generation progress

POST /api/v1/workspaces/{workspace_id}/homepage/digest/dismiss

Body:
{
  "suggestion_id": "uuid",
  "entity_id": "uuid",
  "entity_type": "issue",
  "category": "stale_issues"
}

Response: 204 No Content
```

### Chat-to-Note Endpoint

```
POST /api/v1/workspaces/{workspace_id}/notes/from-chat

Body:
{
  "chat_session_id": "uuid",
  "title": "AI-suggested title",
  "project_id": "uuid"  // optional
}

Response:
{
  "data": {
    "note_id": "uuid",
    "title": "Auth Refactor Strategy",
    "block_count": 5,
    "source_chat_session_id": "uuid"
  }
}
```

---

## AI Agent Integration

### Compact ChatView

The Compact ChatView reuses the existing `PilotSpaceStore` and SSE infrastructure. The key difference is a new `context_type: "homepage"` that instructs the agent to:

1. Keep responses concise (1-3 paragraphs, not lengthy analyses)
2. After 2+ substantive exchanges, proactively suggest note creation
3. When creating a note, use the `create_note_from_chat` skill to:
   - Extract key themes as note title
   - Structure conversation points as content blocks
   - Preserve block IDs for future annotation linking

**New Skill**: `create-note-from-chat`
```yaml
name: create-note-from-chat
description: Creates a structured note from a homepage chat conversation
trigger: intent_detection  # AI triggers when it detects sufficient substance
output: Note with structured content blocks and linked chat session
mcp_tool: create_note_from_chat
```

### AI Digest Background Job

**Job**: `generate_workspace_digest`
**Schedule**: Hourly via pg_cron
**Queue**: LOW priority (non-interactive)
**Agent**: PilotSpaceAgent with `digest` skill
**Model**: Claude Sonnet (cost-optimized for analysis)
**Timeout**: 60 seconds

**Input Context**:
1. All issues updated in last 7 days (state, assignee, activity)
2. All notes updated in last 7 days (annotations, extraction status)
3. Active cycles with progress metrics
4. Open PRs with review status
5. Issue links and dependency graph
6. User activity patterns (for relevance ranking)

**Output**: Array of `DigestSuggestion` objects ranked by relevance score

**New Skill**: `generate-digest`
```yaml
name: generate-digest
description: Analyzes workspace state and generates actionable insights
trigger: scheduled  # Hourly pg_cron job
output: Array of categorized suggestions with relevance scores
```

---

## Component Architecture

### New Components

```
frontend/src/features/homepage/
  components/
    HomepageHub.tsx              # Main layout coordinator
    CompactChatView/
      CompactChatView.tsx        # Expand-on-focus chat widget
      CompactChatInput.tsx       # Input bar (collapsed state)
      CompactChatPanel.tsx       # Expanded chat panel
      CompactMessageList.tsx     # Lightweight message renderer
      NoteCreationSuggestion.tsx # Inline suggestion card
    ActivityFeed/
      ActivityFeed.tsx           # Day-grouped card list
      ActivityDayGroup.tsx       # "Today", "Yesterday" group header
      NoteActivityCard.tsx       # Note card with AI annotation
      IssueActivityCard.tsx      # Issue card with state/priority
      ActivityCardSkeleton.tsx   # Loading skeleton
    DigestPanel/
      DigestPanel.tsx            # AI insights panel
      DigestSuggestionCard.tsx   # Individual suggestion card
      DigestCategoryGroup.tsx    # Category grouping
      DigestEmptyState.tsx       # No AI provider configured
      DigestRefreshButton.tsx    # Manual refresh trigger (integrated into DigestPanel header)
  hooks/
    useHomepageActivity.ts       # TanStack Query for activity feed
    useWorkspaceDigest.ts        # TanStack Query for digest
    useDigestDismiss.ts          # Mutation for dismissals
    useCompactChat.ts            # Chat panel expand/collapse state
  stores/
    HomepageUIStore.ts           # MobX: panel state, focus, keyboard
  __tests__/
    HomepageHub.test.tsx
    CompactChatView.test.tsx
    ActivityFeed.test.tsx
    DigestPanel.test.tsx
```

### Reused Components

| Component | Source | Usage |
|-----------|--------|-------|
| `PilotSpaceStore` | `stores/ai/PilotSpaceStore.ts` | Chat state management |
| `StreamingContent` | `features/ai/ChatView/MessageList/` | SSE message rendering |
| `SuggestionCard` | `features/ai/ChatView/MessageList/` | Note creation prompt |
| `NoteGridCard` (adapted) | `app/(workspace)/[workspaceSlug]/notes/page.tsx` | Activity feed note cards |
| `Card`, `Badge`, `Button` | `components/ui/` (shadcn/ui) | Base primitives |
| `Skeleton` | `components/ui/skeleton` | Loading states |

---

## UI Design Specifications

### Layout Grid

```
Desktop (>=1024px):
+--------------------------------------------------+
| Zone 1: Compact ChatView                          |
| max-width: 720px, centered, h: 48px collapsed     |
+--------------------------------------------------+
|                        |                          |
| Zone 2: Activity Feed  | Zone 3: AI Digest Panel  |
| flex: 3 (60%)          | flex: 2 (40%)            |
| min-w: 380px           | min-w: 300px             |
|                        |                          |
+------------------------+--------------------------+

Tablet (<1024px):
+--------------------------------------------------+
| Zone 1: Compact ChatView (full-width)             |
+--------------------------------------------------+
| Zone 2: Activity Feed (full-width)                |
+--------------------------------------------------+
| Zone 3: AI Digest Panel (full-width)              |
+--------------------------------------------------+

Mobile (<768px):
+--------------------------------------------------+
| Zone 1: Compact ChatView (bottom sheet on expand) |
+--------------------------------------------------+
| Zone 2: Activity Feed (full-width, scrollable)    |
+--------------------------------------------------+
| Zone 3: AI Digest Panel (collapsed, expandable)   |
+--------------------------------------------------+
```

### Compact ChatView Design

**Collapsed State (48px height)**:
- Background: `--background-subtle` with 1px `--border-subtle` bottom
- Icon: PilotSpace AI avatar (24px) on left, pulsing dot when AI available
- Input: Rounded-full, placeholder "What's on your mind?", `--foreground-muted`
- Right: Keyboard hint badge `[/]` in muted text
- Border-radius: 14px (`rounded-lg`)

**Expanded State (max 400px height)**:
- Background: `--card` with `shadow-warm-md`
- Header: "PilotSpace AI" label + minimize button (ChevronDown icon)
- Message area: Scrollable, 16px padding, auto-scroll to bottom
- User messages: Right-aligned, `--background-subtle` bubble
- AI messages: Left-aligned, white/dark bubble, AI avatar (24px)
- Input: Same as full ChatView input (auto-expanding textarea, Enter to send)
- Animation: 200ms ease-out expand, 200ms ease-in collapse

### Activity Card Design

**Note Card (160px height)**:
```
+------------------------------------------+
| [FileText icon] Auth Refactor Notes   2h |
| [PA badge] security, architecture        |
| 1,250 words                              |
| ---------------------------------------- |
| AI: "Consider adding rate limiting..."   |
+------------------------------------------+
```

- Border-radius: 10px (`rounded`)
- Border: 1px `--border-subtle`
- Hover: translateY(-2px), `shadow-warm-md`, cursor pointer
- AI annotation line: `--ai-muted` background, `--ai` text color, `text-sm`

**Issue Card (140px height)**:
```
+------------------------------------------+
| [state-dot] PS-42  In Progress     [!] H |
| Implement JWT refresh token rotation     |
| [PS badge]                    [avatar] T |
| State changed to In Review          3h   |
+------------------------------------------+
```

- State dot: colored circle matching state (e.g., `#D9853F` for In Progress)
- Priority bar: 4px left border in priority color
- Assignee: 24px avatar, right-aligned

### AI Digest Card Design

```
+------------------------------------------+
| [Clock icon] Stale Issue                 |
| PS-42 hasn't been updated in 9 days      |
| Project Alpha                            |
| [View Issue]                    [x]      |
+------------------------------------------+
```

- Background: `--background-subtle`
- Icon: Category-specific, `--foreground-muted` color
- Action button: `ghost` variant, `--primary` text
- Dismiss: `ghost` icon button, `--foreground-muted`
- Border-radius: 10px
- Spacing between cards: 8px

### Day Group Header

```
TODAY
─────────────────────────────────
```

- Text: `text-sm`, `--foreground-muted`, uppercase, `font-semibold`
- Separator: 1px `--border-subtle`, full-width below text
- Margin: 16px top, 8px bottom

---

## Background Job Specification

### `generate_workspace_digest` Job

**Schedule**: `0 * * * *` (every hour, on the hour)
**Queue**: `ai_low` (LOW priority)
**Max Runtime**: 60 seconds
**Retry**: 3 attempts, exponential backoff (2s, 4s, 8s)

**Job Payload**:
```json
{
  "workspace_id": "uuid",
  "trigger": "scheduled",
  "categories": ["all"]
}
```

**Processing Steps**:
1. Query workspace data (issues, notes, cycles, PRs) from last 7 days
2. Build analysis context (<4000 tokens to stay within budget)
3. Send to Claude Sonnet with `generate-digest` skill prompt
4. Parse structured output into `DigestSuggestion[]`
5. Filter out dismissed suggestions per user
6. Score relevance per user based on: ownership, assignment, access frequency
7. Store in `workspace_digests` table
8. Broadcast via Supabase Realtime to connected homepage clients

**Cost Budget**: ~1000 input tokens + ~500 output tokens per run = ~$0.005/run = ~$3.60/month per workspace

---

## Edge Cases

- **No recent activity**: Show empty state with illustration and "Your workspace is quiet. Start a note to get going!" message with CTA.
- **AI provider not configured**: Compact ChatView shows disabled input with "Configure AI provider in Settings" link. Digest panel shows empty state (AS-23).
- **Chat-to-note creation fails**: Show error toast, preserve conversation in chat panel, allow retry.
- **Digest job timeout**: Show stale digest with "Last updated X hours ago" and retry button. No error banner.
- **High-volume workspace (50K+ issues)**: Digest job samples recent data (last 7 days, max 500 entities) to stay within token budget.
- **User has no assigned items**: Digest still shows workspace-wide suggestions but ranked lower for relevance.
- **Concurrent digest refresh**: Queue deduplication prevents multiple simultaneous digest generations per workspace.
- **Mobile keyboard overlap**: Chat panel adjusts height when mobile keyboard appears (viewport resize handling).

---

## Non-Functional Requirements

- **NFR-030**: Homepage MUST load within 2 seconds (activity feed + digest combined)
- **NFR-031**: Compact ChatView MUST respond to first token within 2 seconds
- **NFR-032**: Activity feed MUST support 1000+ items with virtualized scroll rendering
- **NFR-033**: AI Digest generation MUST complete within 60 seconds
- **NFR-034**: Homepage MUST meet WCAG 2.1 Level AA (keyboard nav, screen readers, reduced motion)

---

## Success Criteria

- **SC-020**: Time-to-first-action reduces from ~15 seconds to <3 seconds (measured: time from page load to first user input)
- **SC-021**: 60% of users engage with Compact ChatView at least weekly
- **SC-022**: 40% of notes created via homepage chat-to-note flow (vs direct "New Note")
- **SC-023**: AI Digest suggestions have >50% action rate (clicked/actioned, not dismissed)
- **SC-024**: Homepage bounce rate (navigate away within 5s without interaction) <20%

---

## Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| PilotSpaceStore (DD-086) | Exists | Reuse for Compact ChatView |
| SSE streaming infrastructure | Exists | Reuse for chat streaming |
| Supabase Realtime | Exists | Reuse for activity feed updates |
| pg_cron scheduling | Exists | Use for hourly digest job |
| ChatView components | Exists | Adapt for compact variant |
| Note/Issue card patterns | Exists | Adapt for activity feed |
| `chat_sessions` table | Needs formalization | Required for chat-to-note linking |
| `workspace_digests` table | New | Required for digest storage |
| `digest_dismissals` table | New | Required for dismissal tracking |
| `generate-digest` skill | New | Required for AI digest generation |
| `create-note-from-chat` skill | New | Required for chat-to-note flow |

---

## Related Documentation

- [MVP Specification](../001-pilot-space-mvp/spec.md) - Parent spec (US-01 Note-First Canvas)
- [UI Design Spec](../001-pilot-space-mvp/ui-design-spec.md) - Design system reference
- [Data Model](../001-pilot-space-mvp/data-model.md) - Entity definitions
- [Agent Architecture](../../docs/architect/pilotspace-agent-architecture.md) - PilotSpaceAgent design
- [Design Decisions](../../docs/DESIGN_DECISIONS.md) - DD-013, DD-065, DD-066, DD-086
