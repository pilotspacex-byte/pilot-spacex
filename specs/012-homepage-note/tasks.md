# Tasks: Homepage Hub (US-19)

**Source**: `specs/012-homepage-note/`
**Required**: plan.md, spec.md
**Generated**: 2026-02-06
**User Story**: US-19 (P1 MVP Enhancement) | **Total Tasks**: 65

**Branch**: `012-homepage-note`
**Dependency**: MVP infrastructure (T001-T067 from `specs/001-pilot-space-mvp/tasks.md`) must be complete.

---

## Task Format

```
- [ ] [ID] [P?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies within group) |
| `→` | Depends on preceding task(s) |

---

## Phase 0: Database Schema & Migrations

Database tables, models, and RLS policies for digest storage and chat-to-note linking.

### Alembic Migrations

- [ ] H001 Create migration for `workspace_digests` table in `backend/alembic/versions/xxx_add_workspace_digests.py` with columns: id (UUID PK, gen_random_uuid), workspace_id (FK workspaces, CASCADE), generated_at (timestamptz, server_default now), generated_by (varchar(20), default 'scheduled'), suggestions (JSONB, default '[]'), model_used (varchar(50), nullable), token_usage (JSONB, nullable), created_at (timestamptz). Index on (workspace_id, generated_at).
- [ ] H002 [P] Create migration for `digest_dismissals` table in `backend/alembic/versions/xxx_add_digest_dismissals.py` with columns: id (UUID PK), workspace_id (FK workspaces, CASCADE), user_id (FK users, CASCADE), suggestion_category (varchar(30)), entity_id (UUID), entity_type (varchar(20)), dismissed_at (timestamptz, server_default now). Index on (workspace_id, user_id, entity_id).
- [ ] H064 [P] Create migration for `chat_sessions` table in `backend/alembic/versions/xxx_add_chat_sessions.py` with columns: id (UUID PK, gen_random_uuid), workspace_id (FK workspaces, CASCADE), user_id (FK users, CASCADE), agent_type (varchar(30)), context_type (varchar(20)), context_entity_id (UUID nullable), title (varchar(255) nullable), message_count (integer, default 0), expires_at (timestamptz), created_at (timestamptz, server_default now), updated_at (timestamptz, server_default now). Index on (workspace_id, user_id, context_type).
- [ ] H003 Create migration to add `source_chat_session_id` column (UUID, FK chat_sessions, nullable) to `notes` table in `backend/alembic/versions/xxx_add_notes_source_chat.py` → depends on H064

### RLS Policies

- [ ] H004 Create RLS policies for `workspace_digests`, `digest_dismissals`, and `chat_sessions` in migration: workspace members can SELECT their workspace's digests; users can INSERT/SELECT/DELETE their own dismissals; users can SELECT/INSERT/UPDATE their own chat sessions; service role can INSERT digests → depends on H001, H002, H064

### SQLAlchemy Models

- [ ] H005 Create WorkspaceDigest SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/workspace_digest.py` inheriting WorkspaceScopedModel with fields: generated_at (DateTime tz), generated_by (String 20), suggestions (JSONB list), model_used (String 50 nullable), token_usage (JSONB nullable) → depends on H001
- [ ] H006 [P] Create DigestDismissal SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/digest_dismissal.py` inheriting WorkspaceScopedModel with fields: user_id (FK), suggestion_category (String 30), entity_id (UUID), entity_type (String 20), dismissed_at (DateTime tz) → depends on H002
- [ ] H065 [P] Create ChatSession SQLAlchemy model in `backend/src/pilot_space/infrastructure/database/models/chat_session.py` inheriting WorkspaceScopedModel with fields: user_id (FK users), agent_type (String 30), context_type (String 20), context_entity_id (UUID nullable), title (String 255 nullable), message_count (Integer default 0), expires_at (DateTime tz), updated_at (DateTime tz) → depends on H064
- [ ] H007 [P] Add `source_chat_session_id` mapped column to existing Note model in `backend/src/pilot_space/infrastructure/database/models/note.py` (UUID FK, nullable) with relationship to ChatSession → depends on H003, H065

**Checkpoint**: Database schema ready. Run `alembic upgrade head` to verify.

---

## Phase 1: Backend API Layer

Homepage router, schemas, services, and repositories.

### Pydantic Schemas

- [ ] H008 Create homepage Pydantic schemas in `backend/src/pilot_space/api/v1/schemas/homepage.py`: ActivityCardNote (type, id, title, project, topics, word_count, latest_annotation, updated_at, is_pinned), ActivityCardIssue (type, id, identifier, title, project, state, priority, assignee, last_activity, updated_at), HomepageActivityResponse (data: {today, yesterday, this_week}, meta: {total, cursor, has_more}), DigestSuggestion (id, category, icon, title, description, entity_id, entity_type, entity_identifier, project_id, project_name, action_type, action_label, action_route, relevance_score, generated_at), DigestResponse (data: {generated_at, generated_by, suggestions, suggestion_count}), DigestDismissPayload (suggestion_id, entity_id, entity_type, category), DigestRefreshResponse (data: {status, estimated_seconds}), CreateNoteFromChatPayload (chat_session_id, title, project_id optional)

### Repositories

- [ ] H009 Create HomepageRepository in `backend/src/pilot_space/infrastructure/database/repositories/homepage_repository.py` with methods: get_recent_notes_with_annotations(workspace_id, since, limit) returns notes LEFT JOIN latest annotation via lateral subquery; get_recent_issues_with_activity(workspace_id, since, limit) returns issues LEFT JOIN latest activity via lateral subquery → depends on H005, H006
- [ ] H010 [P] Create DigestRepository in `backend/src/pilot_space/infrastructure/database/repositories/digest_repository.py` with methods: get_latest_digest(workspace_id), save_digest(digest), get_user_dismissals(workspace_id, user_id), add_dismissal(dismissal), check_recent_digest_exists(workspace_id, minutes=30) → depends on H005, H006

### Application Services (CQRS-lite)

- [ ] H011 Create GetActivityService in `backend/src/pilot_space/application/services/homepage/get_activity_service.py` with GetActivityPayload (workspace_id, user_id, cursor, limit) and GetActivityResult (today, yesterday, this_week, total, cursor, has_more). Logic: query notes + issues updated in last 7 days, union and sort by updated_at DESC, group into day buckets using Python datetime, apply cursor pagination → depends on H008, H009
- [ ] H012 [P] Create GetDigestService in `backend/src/pilot_space/application/services/homepage/get_digest_service.py` with GetDigestPayload (workspace_id, user_id) and GetDigestResult. Logic: fetch latest workspace_digest, fetch user dismissals, filter out dismissed suggestions, rank remaining by relevance to user (is_assignee +0.3, is_creator +0.2, access_frequency +0.1), return sorted → depends on H008, H010
- [ ] H013 [P] Create DismissSuggestionService in `backend/src/pilot_space/application/services/homepage/dismiss_suggestion_service.py` with DismissSuggestionPayload and void result. Logic: insert DigestDismissal record → depends on H010
- [ ] H014 [P] Create CreateNoteFromChatService in `backend/src/pilot_space/application/services/note/create_note_from_chat_service.py` with CreateNoteFromChatPayload (chat_session_id, title, project_id, workspace_id, user_id) and CreateNoteFromChatResult (note_id, title, block_count, source_chat_session_id). Logic: fetch chat session messages, call Claude Sonnet one-shot to extract key points, structure as TipTap JSON blocks (heading + paragraphs), create note via existing NoteRepository with source_chat_session_id set → depends on H007, H008

### API Router

- [ ] H015 Create homepage router in `backend/src/pilot_space/api/v1/routers/homepage.py` with 4 endpoints: GET /activity (calls GetActivityService), GET /digest (calls GetDigestService), POST /digest/refresh (enqueues digest job, returns status), POST /digest/dismiss (calls DismissSuggestionService, returns 204). Mount under `/api/v1/workspaces/{workspace_id}/homepage/`. All endpoints require JWT auth + workspace membership check. → depends on H011, H012, H013
- [ ] H016 Add POST /from-chat endpoint to existing notes router in `backend/src/pilot_space/api/v1/routers/notes.py`. Calls CreateNoteFromChatService, returns NoteResponse with 201 status. → depends on H014
- [ ] H017 Register homepage router in `backend/src/pilot_space/api/v1/__init__.py` router aggregator → depends on H015
- [ ] H018 Wire homepage services and repositories to DI container in `backend/src/pilot_space/container.py` → depends on H009, H010, H011, H012, H013, H014

**Checkpoint**: Backend API functional. Test with `curl` against dev server for all 5 endpoints.

---

## Phase 2: AI Digest Background Job

Hourly workspace analysis via pgmq + pg_cron.

### AI Skill

- [ ] H019 Create `generate-digest` skill in `backend/src/pilot_space/ai/templates/skills/generate-digest/SKILL.md` with YAML frontmatter (name, description, trigger: scheduled, model: claude-sonnet, timeout: 60s) and prompt template for workspace analysis covering 12 categories: stale_issues, missing_docs, inconsistent_status, blocked_deps, unassigned_work, overdue_cycles, pr_review_pending, duplicate_candidates, note_refinement, project_health, knowledge_gaps, release_readiness. Output format: JSON array of DigestSuggestion objects.
- [ ] H020 [P] Create `create-note-from-chat` skill in `backend/src/pilot_space/ai/templates/skills/create-note-from-chat/SKILL.md` with YAML frontmatter (name, description, trigger: intent_detection, model: claude-sonnet) and prompt template for extracting key themes and structuring conversation into TipTap-compatible content blocks.

### Digest Job Handler

- [ ] H021 Create DigestContextBuilder in `backend/src/pilot_space/application/services/homepage/digest_context_builder.py` with method build_context(workspace_id) that runs SQL aggregate queries: stale issues (state IN started, updated_at < 7d), done issues without note links, issues with inconsistent state vs activity, blocked dependency chains, unassigned high/urgent issues, active cycle progress, open PRs without review, recent high-similarity issue pairs, notes with undismissed annotations, cycle velocity trends. Returns structured dict <4000 tokens. → depends on H009
- [ ] H022 Create DigestJobHandler in `backend/src/pilot_space/infrastructure/queue/handlers/digest_handler.py` with handle(payload: DigestJobPayload) method. Logic: 1) check deduplication (skip if digest <30min old), 2) call DigestContextBuilder, 3) invoke Claude Sonnet via one-shot query with generate-digest skill prompt, 4) parse JSON response into DigestSuggestion[], 5) store in workspace_digests via DigestRepository, 6) broadcast via Supabase Realtime channel `workspace:{workspace_id}` event `digest_updated`. Timeout: 60s. Retry: 3 attempts, exponential backoff (2s, 4s, 8s). → depends on H019, H021, H010
- [ ] H023 Register DigestJobHandler in queue worker dispatcher for `ai_low` queue operations with `operation: 'generate_digest'` → depends on H022

### pg_cron Schedule

- [ ] H024 Create migration for pg_cron schedule in `backend/alembic/versions/xxx_add_digest_cron.py`: schedule `generate-workspace-digests` job at `0 * * * *` (hourly) that queries active workspaces with valid AI configurations and enqueues `generate_digest` jobs to `ai_low` queue with random jitter (0-300s delay via `pg_sleep(random() * 300)`) to prevent thundering herd → depends on H022

**Checkpoint**: Digest job generates suggestions hourly. Verify via `/admin/jobs` queue monitoring.

---

## Phase 3: Frontend - Feature Module & Activity Feed (Zone 2)

Feature folder setup, API client, types, and the Recent Activity Feed.

### Feature Module Setup

- [ ] H025 Create frontend feature module structure at `frontend/src/features/homepage/` with directories: components/, hooks/, stores/, api/, __tests__/ and barrel export index.ts
- [ ] H026 Create TypeScript types in `frontend/src/features/homepage/types.ts`: ActivityCardNote, ActivityCardIssue, ActivityCard (union), DayGroup, DigestSuggestion, DigestCategory (enum of 12 categories), DigestResponse, HomepageActivityResponse → depends on H025
- [ ] H027 [P] Create constants in `frontend/src/features/homepage/constants.ts`: ITEMS_PER_PAGE=20, ACTIVITY_STALE_TIME=30000, DIGEST_STALE_TIME=300000, MAX_ANNOTATION_PREVIEW_LENGTH=80, CHAT_MAX_HEIGHT=400, DAY_GROUP_LABELS, DIGEST_CATEGORY_ICONS (maps category to lucide-react icon name) → depends on H025
- [ ] H028 [P] Create homepage API client in `frontend/src/features/homepage/api/homepage-api.ts` with functions: getActivity(workspaceId, cursor?), getDigest(workspaceId), refreshDigest(workspaceId), dismissSuggestion(workspaceId, payload), createNoteFromChat(workspaceId, payload). Uses existing API client with typed responses. → depends on H026

### MobX Store

- [ ] H043 Create HomepageUIStore in `frontend/src/features/homepage/stores/HomepageUIStore.ts`: MobX store with makeAutoObservable. Observables: chatExpanded (boolean, default false), activeZone ('chat' | 'activity' | 'digest', default 'activity'). Actions: expandChat(), collapseChat(), setActiveZone(zone), toggleChat(). Computed: isChatActive. No server data (TanStack Query handles that). Register in RootStore or provide via React Context at homepage level. → depends on H025

### Activity Feed Components

- [ ] H029 Create NoteActivityCard component in `frontend/src/features/homepage/components/ActivityFeed/NoteActivityCard.tsx`: interactive Card (shadcn/ui), FileText icon + title (line-clamp-1), project badge (colored pill), topic tags (max 3, muted pills), word count, AI annotation preview line (truncated 80 chars, --ai-muted bg, --ai text, text-sm), relative timestamp (formatDistanceToNow), hover: translateY(-2px) + shadow-warm-md, click: navigate to /[workspaceSlug]/notes/[noteId]. Tooltip on annotation hover showing full text + type icon. → depends on H026
- [ ] H030 [P] Create IssueActivityCard component in `frontend/src/features/homepage/components/ActivityFeed/IssueActivityCard.tsx`: interactive Card, state dot (colored circle per state color), identifier (PS-123) + title, project badge, state badge (colored pill), priority indicator (4px left border in priority color), assignee avatar (24px), last activity summary (1 line), relative timestamp, hover: translateY(-2px) + shadow, click: navigate to /[workspaceSlug]/issues/[issueId]. → depends on H026
- [ ] H031 [P] Create ActivityDayGroup component in `frontend/src/features/homepage/components/ActivityFeed/ActivityDayGroup.tsx`: renders day header (text-sm, --foreground-muted, uppercase, font-semibold) with separator line (1px --border-subtle), then maps over cards rendering NoteActivityCard or IssueActivityCard based on type. → depends on H029, H030
- [ ] H032 [P] Create ActivityCardSkeleton component in `frontend/src/features/homepage/components/ActivityFeed/ActivityCardSkeleton.tsx`: loading skeleton matching card dimensions (160px note, 140px issue) with diagonal shimmer animation. → depends on H025
- [ ] H033 Create ActivityFeed component in `frontend/src/features/homepage/components/ActivityFeed/ActivityFeed.tsx`: uses useHomepageActivity hook, renders ActivityDayGroup for each day bucket (Today, Yesterday, This Week), shows ActivityCardSkeleton during loading, empty state ("Your workspace is quiet. Start a note to get going!") when no data, infinite scroll via IntersectionObserver at bottom triggering fetchNextPage. → depends on H031, H032, H034

### Activity Feed Hook

- [ ] H034 Create useHomepageActivity hook in `frontend/src/features/homepage/hooks/useHomepageActivity.ts`: useInfiniteQuery with queryKey ['homepage', 'activity', workspaceId], calls homepageApi.getActivity, getNextPageParam from meta.cursor, staleTime 30s. Also subscribes to Supabase Realtime channel `workspace:{workspaceId}` for `note_updated` and `issue_updated` broadcast events, calling queryClient.invalidateQueries on receive. Cleanup subscription on unmount. → depends on H028

**Checkpoint**: Activity feed renders with day-grouped cards and real-time updates.

---

## Phase 4: Frontend - Compact ChatView (Zone 1)

Expand-on-focus chat widget reusing PilotSpaceStore.

### Compact ChatView Components

- [ ] H035 Create CompactChatInput component in `frontend/src/features/homepage/components/CompactChatView/CompactChatInput.tsx`: 48px height bar with --background-subtle bg, 14px border-radius, PilotSpace AI avatar (24px) on left with pulsing dot (motion-safe:animate-pulse), rounded-full input with placeholder "What's on your mind?", keyboard hint badge [/] in muted text on right. Accepts onFocus callback. Disabled state when no AI provider (shows "Configure AI provider in Settings" link). → depends on H025
- [ ] H036 Create CompactMessageList component in `frontend/src/features/homepage/components/CompactChatView/CompactMessageList.tsx`: scrollable message container (max-height from parent), renders user messages (right-aligned, --background-subtle bubble) and AI messages (left-aligned, white/dark bubble, AI avatar 24px). Reuses StreamingContent from `features/ai/ChatView/MessageList/` for SSE rendering. Auto-scrolls to bottom on new messages unless user scrolled up. 16px padding. → depends on H025
- [ ] H037 [P] Create NoteCreationSuggestion component in `frontend/src/features/homepage/components/CompactChatView/NoteCreationSuggestion.tsx`: SuggestionCard variant with title "Create a note from this conversation", AI-suggested note title, optional project selector dropdown, "Create Note" primary button + "Not now" ghost button. On accept: calls homepageApi.createNoteFromChat, on success navigates to /[workspaceSlug]/notes/[noteId] via router.push. Shows loading state during creation. → depends on H028
- [ ] H038 Create CompactChatPanel component in `frontend/src/features/homepage/components/CompactChatView/CompactChatPanel.tsx`: --card bg, shadow-warm-md, rounded-lg, max-height 400px. Header: "PilotSpace AI" label + ChevronDown minimize button. Contains CompactMessageList + NoteCreationSuggestion (when AI suggests). Bottom: auto-expanding textarea input (Enter to send, Shift+Enter newline), send button (primary when text, disabled when streaming), stop button during streaming. Animation: 200ms ease-out expand, 200ms ease-in collapse with motion-safe variant. → depends on H036, H037
- [ ] H039 Create CompactChatView component in `frontend/src/features/homepage/components/CompactChatView/CompactChatView.tsx`: coordinator component managing collapsed/expanded state via HomepageUIStore. Collapsed: renders CompactChatInput. Expanded: renders CompactChatPanel. Integrates PilotSpaceStore with context_type 'homepage' session. On mount: start or resume homepage session. On Escape or outside click (useClickOutside): collapse preserving state. On mobile (<768px): expanded renders as bottom sheet (full-width, 60vh, backdrop overlay 40% black, swipe-down dismiss via touch events). → depends on H035, H038, H043

### Chat Integration Hook

- [ ] H040 Create useCompactChat hook in `frontend/src/features/homepage/hooks/useCompactChat.ts`: manages PilotSpaceStore session lifecycle for homepage context. On mount: calls store.startSession({ contextType: 'homepage' }). On unmount: calls store.pauseSession() (not destroy). Exposes: sendMessage(text), messages, isStreaming, hasNoteCreationSuggestion (derived from AI response containing note creation intent). Session persists across expand/collapse cycles within browser session. → depends on H025

**Checkpoint**: Compact ChatView expands, sends messages via SSE, collapses preserving state.

---

## Phase 5: Frontend - AI Digest Panel (Zone 3)

AI insights panel with actionable suggestion cards.

### Digest Hooks

- [ ] H041 Create useWorkspaceDigest hook in `frontend/src/features/homepage/hooks/useWorkspaceDigest.ts`: useQuery with queryKey ['homepage', 'digest', workspaceId], calls homepageApi.getDigest, staleTime 5min, refetchOnWindowFocus true. Subscribe to Supabase Realtime `workspace:{workspaceId}` for `digest_updated` broadcast event to invalidate query. → depends on H028
- [ ] H042 [P] Create useDigestDismiss hook in `frontend/src/features/homepage/hooks/useDigestDismiss.ts`: useMutation calling homepageApi.dismissSuggestion with optimistic update (remove suggestion from cache via queryClient.setQueryData, rollback on error via onError with previous snapshot). → depends on H028

### Digest Panel Components

- [ ] H063 Create DigestEmptyState component in `frontend/src/features/homepage/components/DigestPanel/DigestEmptyState.tsx`: simple SVG illustration, text "Configure an AI provider in Settings to enable workspace insights", ghost link button to /[workspaceSlug]/settings/ai-providers. Centered, padded, muted text. → depends on H025
- [ ] H044 Create DigestSuggestionCard component in `frontend/src/features/homepage/components/DigestPanel/DigestSuggestionCard.tsx`: --background-subtle bg, rounded (10px), category icon (lucide-react, --foreground-muted), title (font-medium, 1 line), description (text-sm, --foreground-muted, line-clamp-2), project name label. Action button: ghost variant for navigate actions (calls router.push), outline variant for quick actions (create issue opens modal pre-filled, assign opens popover, trigger review calls endpoint). Dismiss button: ghost icon X top-right, calls onDismiss. → depends on H026, H027
- [ ] H045 [P] Create DigestCategoryGroup component in `frontend/src/features/homepage/components/DigestPanel/DigestCategoryGroup.tsx`: groups suggestions by category, renders category header (icon + label) then list of DigestSuggestionCards. Collapsible with ChevronDown toggle if >3 suggestions in category. → depends on H044
- [ ] H046 Create DigestPanel component in `frontend/src/features/homepage/components/DigestPanel/DigestPanel.tsx`: coordinator component. Checks AI provider configured via workspace settings. If not: render DigestEmptyState. If loading: render Skeleton cards. Header: "AI Insights" label + relative timestamp ("Updated 45 min ago" via formatDistanceToNow) + Refresh button (ghost, RefreshCw icon). On refresh click: call homepageApi.refreshDigest, set loading state, invalidate digest query on completion. Groups suggestions by category via DigestCategoryGroup. → depends on H041, H042, H063, H045

**Checkpoint**: Digest panel renders suggestion cards, dismiss works with optimistic update, refresh triggers regeneration.

---

## Phase 6: Homepage Layout & Accessibility

Main layout coordinator, keyboard navigation, and ARIA compliance. (HomepageUIStore moved to Phase 3.)

### Homepage Layout

- [ ] H047 Create HomepageHub component in `frontend/src/features/homepage/components/HomepageHub.tsx`: observer() wrapped, 3-zone layout. Zone 1 (top): CompactChatView, max-w-[720px] mx-auto. Zone 2+3 (bottom): flex-col lg:flex-row gap-6, Zone 2 flex-[3] min-w-0, Zone 3 flex-[2] min-w-0. Outer: flex flex-col gap-6 p-6 max-w-[1400px] mx-auto. Each zone wrapped in section with role="region" aria-label. Integrates HomepageUIStore and ref forwarding for F6 zone cycling. → depends on H033, H039, H046, H043

### Page Route

- [ ] H048 Replace existing homepage page component at `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx` with HomepageHub. Preserve OnboardingChecklist integration (show if onboarding incomplete). Remove static welcome screen (compass icon, greeting, template cards). → depends on H047

### Keyboard Navigation

- [ ] H049 Add `/` global shortcut handler in HomepageHub: on keydown, if key is '/' and target is not text input (input, textarea, [contenteditable]), preventDefault and focus compactChatInputRef. Only active on homepage route. → depends on H047
- [ ] H050 [P] Add F6 zone cycling handler in HomepageHub: on keydown F6, preventDefault, cycle activeZone through ['chat', 'activity', 'digest'], focus the corresponding zone ref. Each zone section has tabIndex={-1} for programmatic focus. → depends on H047

### Accessibility

- [ ] H051 Add ARIA landmarks to all zone sections: role="region" with aria-label="Quick capture - Chat with PilotSpace AI" (Zone 1), "Recent activity - Notes and issues" (Zone 2), "AI workspace insights" (Zone 3). Add role="article" with descriptive aria-label to each card (NoteActivityCard, IssueActivityCard, DigestSuggestionCard). Add aria-live="polite" to chat message list for screen reader announcements. → depends on H047
- [ ] H052 [P] Add prefers-reduced-motion support: wrap all expand/collapse animations in motion-safe: Tailwind variant, add CSS `@media (prefers-reduced-motion: reduce)` fallback in CompactChatPanel and card hover transitions. Verify pulsing AI dot uses motion-safe:animate-pulse. → depends on H047

**Checkpoint**: Full homepage renders with 3 zones, keyboard navigation works, screen reader compatible.

---

## Phase 7: Testing

Backend and frontend tests achieving >80% coverage.

### Backend Unit Tests

- [ ] H053 Create test file `backend/tests/unit/services/homepage/test_get_activity_service.py` with tests: day grouping logic (today/yesterday/this_week boundaries), cursor pagination (forward, empty next page), empty workspace returns empty buckets, annotation preview truncation at 80 chars, mixed note+issue sorting by updated_at DESC, workspace scoping (RLS simulation) → depends on H011
- [ ] H054 [P] Create test file `backend/tests/unit/services/homepage/test_get_digest_service.py` with tests: digest retrieval returns latest, dismissal filtering removes matching suggestions, relevance ranking (assignee > creator > other), empty digest when no AI provider, stale digest still returned with timestamp → depends on H012
- [ ] H055 [P] Create test file `backend/tests/unit/services/homepage/test_dismiss_suggestion_service.py` with tests: creates dismissal record, duplicate dismissal is idempotent → depends on H013
- [ ] H056 [P] Create test file `backend/tests/unit/services/note/test_create_note_from_chat_service.py` with tests: creates note with source_chat_session_id, content structured as TipTap blocks, missing chat session returns 404, empty conversation returns error → depends on H014
- [ ] H057 [P] Create test file `backend/tests/unit/queue/test_digest_handler.py` with tests: context builder produces <4000 token context, deduplication skips if digest <30min old, AI response parsed into DigestSuggestion list, timeout handled gracefully (job marked failed), Supabase Realtime broadcast called on success → depends on H022

### Backend Integration Tests

- [ ] H058 Create test file `backend/tests/integration/test_homepage_router.py` with tests: GET /activity returns grouped data with 200, GET /activity with cursor paginates, GET /digest returns latest digest with 200, POST /digest/refresh returns 200 with status, POST /digest/dismiss returns 204, POST /notes/from-chat returns 201 with note, auth required (401 without token), workspace isolation (403 for non-member) → depends on H015, H016

### Frontend Unit Tests

- [ ] H059 Create test file `frontend/src/features/homepage/__tests__/HomepageHub.test.tsx` with tests: renders 3 zone sections with ARIA landmarks, responsive layout stacks on tablet (mock matchMedia), F6 cycles zone focus, '/' shortcut focuses chat input, '/' ignored when in text input → depends on H047
- [ ] H060 [P] Create test file `frontend/src/features/homepage/__tests__/CompactChatView.test.tsx` with tests: renders collapsed input bar initially, expands on focus/click, collapses on Escape, collapses on outside click, sends message on Enter (mock PilotSpaceStore), shows NoteCreationSuggestion when AI suggests, note creation navigates to editor, preserves messages after collapse/expand cycle, disabled state when no AI provider → depends on H039
- [ ] H061 [P] Create test file `frontend/src/features/homepage/__tests__/ActivityFeed.test.tsx` with tests: renders day group headers (Today/Yesterday/This Week), renders NoteActivityCard with metadata, renders IssueActivityCard with state/priority, empty state message shown when no data, infinite scroll triggers fetchNextPage (mock IntersectionObserver), annotation tooltip on hover → depends on H033
- [ ] H062 [P] Create test file `frontend/src/features/homepage/__tests__/DigestPanel.test.tsx` with tests: renders suggestion cards grouped by category, dismiss removes card optimistically, dismiss rollback on API error, refresh button triggers loading state, empty state when no AI provider, timestamp shows relative time, category collapse/expand toggle, quick action button calls correct handler → depends on H046

**Checkpoint**: All tests pass. Run `uv run pytest --cov=. && pnpm test` to verify >80% coverage.

---

## Dependency Graph

```
H001 ─┬─ H004 ─── H005 ─┬─ H009 ─┬─ H011 ─┬─ H015 ─── H017 ─── H018
H002 ─┘   │         │     │        │         │
H064 ─┬───┘         │     │        │         │
      │              │     │        │         │
H003 ─┤── H065      │     │        │         │
      │    │         │     │        │         │
      └─── H007     H006 ─┤─ H010 ─┼─ H012 ─┤
                    │     │        │         │
                    └─────┘        ├─ H013 ──┤
                                   │         │
                    H014 ──────────┘─ H016   │
                                             │
H019 ─── H021 ─── H022 ─── H023 ─── H024    │
H020                                         │
                                             │
H025 ─┬─ H026 ─┬─ H027                      │
      │        ├─ H028 ─┬─ H029 ─┐          │
      │        │         ├─ H030 ─┤          │
      │        │         │        ├─ H031    │
      │        │         │        │   │      │
      │        │         ├─ H034 ─┘   │      │
      │        │         │        H032│      │
      │        │         │            │      │
      ├─ H043 (Store)    │        H033 ──────┤ (Zone 2)
      │        │         │                   │
      ├─ H035 ─┤         │                   │
      ├─ H036 ─┤─ H037 ──┤                   │
      │        │         │                   │
      │        H038 ─────┤                   │
      │                  │                   │
      │        H040      H039 ──────────────┤ (Zone 1)
      │                                     │
      ├─ H063 (EmptyState) H041 ─┐          │
      │                  H042 ─┤          │
      │        H044 ─── H045 ─┤          │
      │                       │          │
      │                  H046 ───────────┤ (Zone 3)
      │                                  │
      │                             H047 ─┤ (Layout)
      │                                  │
      │                             H048 ─┤ (Route)
      │                             H049 ─┤ (Keyboard)
      │                             H050 ─┤
      │                             H051 ─┤ (A11y)
      │                             H052 ─┘
      │
      └─── H053-H062 (Tests, depend on respective implementation tasks)
```

---

## Summary

| Phase | Tasks | Key Files | Parallelizable |
|-------|-------|-----------|----------------|
| Phase 0: DB Schema | H001-H007, H064-H065 | 4 migrations, 3 models, 1 model update | H001/H002/H064 parallel |
| Phase 1: Backend API | H008-H018 | 1 schema, 2 repos, 4 services, 2 routers | H011-H014 parallel |
| Phase 2: AI Digest Job | H019-H024 | 2 skills, 1 context builder, 1 handler, 1 cron | H019/H020 parallel |
| Phase 3: Activity Feed + Store | H025-H034, H043 | 6 components, 1 hook, 1 store, 2 config files | H029/H030/H032 parallel |
| Phase 4: Compact ChatView | H035-H040 | 5 components, 1 hook | H036/H037 parallel |
| Phase 5: Digest Panel | H041-H042, H044-H046, H063 | 4 components, 2 hooks | H041/H042 parallel |
| Phase 6: Layout & A11y | H047-H052 | 1 layout, 1 route, 4 enhancements | H049/H050 and H051/H052 parallel |
| Phase 7: Testing | H053-H062 | 6 backend test files, 4 frontend test files | All test files parallel |
| **Total** | **65 tasks** | **50 new files, 3 modified** | |

**Critical Path**: H001 → H005 → H009 → H011 → H015 → H017 → H018 → H025 → H043 → H039/H033/H046 → H047 → H048

**Estimated Parallel Execution**: With 2 developers (1 backend, 1 frontend), Phases 0-2 (backend) and Phases 3-5 (frontend) can run concurrently after Phase 1 schemas are available via API stubs.
