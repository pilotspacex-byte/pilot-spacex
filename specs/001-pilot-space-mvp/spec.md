# Feature Specification: Pilot Space MVP

**Feature Branch**: `001-pilot-space-mvp`
**Created**: 2026-01-20
**Updated**: 2026-01-23
**Status**: Draft → Synced with docs v3.2 (Design Decisions Consolidated)
**Scope**: MVP (P0 + P1 Features Only - 6 User Stories)
**Input**: User description: "Based on documents then make specify for Pilot Space - AI-Augmented SDLC Platform"
**Sync**: This specification incorporates all features from DD-001 to DD-085 and PS-001 to PS-017 (complete sync)

**Changes v3.3 (2026-01-23)**:
- Refactored to MVP scope only (P0 + P1 features)
- Moved P2 features to `specs/002-pilot-space-phase2/`
- Moved P3 features to `specs/003-pilot-space-phase3/`
- MVP contains 6 user stories: US-01, US-02, US-03, US-04, US-12, US-18

**Changes v3.2**:
- Synced with DESIGN_DECISIONS.md v3.2 (85 decisions total)
- Added DD-059 to DD-070 (Infrastructure, Security, API, Architecture clarifications)
- Added DD-071 to DD-085 (User Story implementation clarifications)
- Added Ghost Text Word Boundary Handling (DD-067)

**Changes v3.1**:
- Added 15 Frontend Architecture Decisions clarifications (State Management, SSE, Virtualization, Testing, Accessibility)
- State: MobX for UI-only state, TanStack Query for all server data
- Virtualization: @tanstack/react-virtual for 1000+ block notes
- SSE: Separate EventSource per AI operation with cookie auth
- Testing: Integration (Vitest + jsdom) + E2E (Playwright) + MSW + axe-core

**Changes v3.0**:
- Migrated to Supabase platform (Auth, Storage, Queues, Database)
- Replaced Keycloak with Supabase Auth (GoTrue) - FR-060 to FR-062 updated
- Replaced Celery + RabbitMQ with Supabase Queues (pgmq + pg_cron) - FR-095 to FR-101 added
- Replaced S3/MinIO with Supabase Storage - FR-102 to FR-109 added
- Added database enhancements (pgvector, HNSW) - FR-110 to FR-116 added
- Added Row-Level Security (RLS) requirements - FR-117 to FR-123 added
- DD-005 (no real-time collaboration) maintained for MVP

## Core Philosophy: Note-First, Not Ticket-First

Pilot Space is a **collaborative thinking space with AI expert agents**. Unlike traditional issue trackers that force users to fill forms, Pilot Space starts with collaborative thinking—users write rough ideas, AI agents help clarify ambiguous concepts, and **explicit root issues emerge from implicit requests**.

> **"Think first, clarify with AI experts, structure later"**

### The Note-First Value Chain

```
1. WRITE              2. CLARIFY                 3. EXTRACT               4. STRUCTURE
───────────           ────────────               ──────────               ────────────
Rough ideas      →    AI asks probing       →    Root issues        →    Actionable
(implicit)            questions                  surface (explicit)       work items
```

### Implicit → Explicit Extraction

The core innovation is **extracting explicit root issues from implicit user requests**:

| User Says (Implicit) | AI Extracts (Explicit Root Issues) |
|----------------------|-----------------------------------|
| "We need to change auth" | Security vulnerability, compliance requirement, architecture debt, migration plan |
| "This page is slow" | N+1 query, missing index, unoptimized component, bundle size issue |
| "Users are confused" | Missing onboarding, unclear UX flow, inadequate error messages |

### Comparison with Traditional Tools

| Traditional PM Tools | Pilot Space |
|---------------------|-------------|
| Start with forms → Fill fields → Submit | Start with notes → AI clarifies → Root issues extracted |
| Structure imposed upfront | Structure emerges from clarified thinking |
| Vague request → Vague ticket | Vague request → AI probes → Explicit issues |
| Dashboard as home | **Note Canvas as home** |
| AI bolt-on (autocomplete) | AI embedded (expert clarification partner) |

**Reference**: See DD-013 (Note-First Collaborative Workspace) in DESIGN_DECISIONS.md

---

## MVP Scope Definition

### TRUE MVP (P0 + P1) - 6 User Stories

| Priority | User Story | Description |
|----------|------------|-------------|
| P0 | US-01 | Note-First Collaborative Writing |
| P1 | US-02 | AI Issue Creation |
| P1 | US-03 | AI PR Review |
| P1 | US-04 | Sprint Planning |
| P1 | US-12 | AI Context |
| P1 | US-18 | GitHub Integration |

### Future Phases

- **Phase 2 (P2)**: US-05, US-06, US-07, US-08, US-09, US-13, US-14, US-15, US-17 → See `specs/002-pilot-space-phase2/`
- **Phase 3 (P3)**: US-10, US-11, US-16 → See `specs/003-pilot-space-phase3/`

---

## Clarifications

### Session 2026-01-20

- Q: What authentication/authorization model for the API layer? → A: Supabase Auth (GoTrue) with Row-Level Security (RLS) for authorization. JWT tokens, OAuth2 social providers, SAML 2.0 SSO for enterprise.
- Q: What is the availability SLA and recovery time objective? → A: 99.5% uptime (~3.6 hours/month), 4-hour RTO
- Q: How to handle GitHub API rate limits for PR reviews? → A: Queue with exponential backoff + user notification when delayed
- Q: How to handle concurrent page edit conflicts? → A: Last-write-wins with conflict notification to overwritten user
- Q: What are the API response latency targets? → A: p95 < 500ms reads, p95 < 1s writes

### Session 2026-01-21

- Q: What compliance/regulatory requirements for MVP? → A: None for MVP; GDPR, SOC2, data residency deferred to Phase 3 (Enterprise)
- Q: What observability requirements for MVP? → A: Standard application logs only; structured logging, metrics, and tracing deferred to Phase 2
- Q: What accessibility conformance level? → A: WCAG 2.1 Level AA (keyboard navigation + screen reader support)
- Q: What data import capability for MVP? → A: Import for restore-from-backup only (same format as export); migration tools deferred
- Q: What AI usage tracking for BYOK users? → A: None in MVP; users monitor costs via their LLM provider dashboards

### Session 2026-01-22 (Supabase Integration)

- Q: Should MVP include real-time note collaboration? → A: No, keep DD-005 (defer to post-MVP). Last-write-wins with conflict notification.
- Q: Which authentication system for MVP? → A: Supabase Auth only. Email, OAuth, SAML 2.0 SSO. No LDAP in MVP. RLS for authorization.
- Q: How should background jobs be handled? → A: Supabase Queues only (pgmq + pg_cron). No Celery/RabbitMQ. Edge Functions for workers.
- Q: Should MVP include workspace-level AI cost tracking? → A: No, keep deferred. Users monitor via provider dashboards.
- Q: Which storage system for file uploads? → A: Supabase Storage. S3-compatible, integrated with RLS, CDN, image transforms.
- Q: What infrastructure simplification target? → A: 10 services → 2-3 services (Supabase platform + FastAPI backend + Next.js frontend)
- Q: What issue state transitions are valid? → A: All forward transitions allowed; completed can reopen to started; any state can transition to cancelled. No direct unstarted→completed.
- Q: Who can restore soft-deleted items? → A: Original creator OR workspace admin/owner. Members cannot restore others' deleted content.
- Q: What format for workspace export/import? → A: JSON archive (ZIP containing structured JSON files per entity type). Human-readable, portable, no vendor lock-in.
- Q: What AI provider failover strategy? → A: Task-based routing (code review→Anthropic, ghost text→Google Gemini, docs→any) with automatic failover to next-best provider on error.
- Q: What API rate limiting strategy? → A: Tiered rate limiting: 1000 req/min for standard API endpoints, 100 req/min for AI endpoints. Per-workspace limits.
- Q: How should backend use cases be organized? → A: Command/Query separation (CQRS-lite). Separate command (write) and query (read) handlers without event sourcing. Prepares for read replicas.
- Q: How should note blocks be stored? → A: JSONB column on `notes` table (TipTap native format). Single atomic document matches ProseMirror's `getJSON()`/`setContent()`. Embeddings indexed to separate `note_block_embeddings` table via background job.
- Q: How should frontend stores be organized? → A: Feature-based MobX UI stores (IssueUIStore, NoteUIStore, GlobalUIStore) with React Context providers at layout level. TanStack Query for ALL server data (issues, notes, projects). MobX for UI-only state (selection, filters, modals). NEVER store server data in MobX.
- Q: How should AI responses be streamed? → A: SSE via FastAPI StreamingResponse. Unidirectional server→client, proxy-friendly, native FastAPI support. Client uses EventSource API.
- Q: Where should UUIDs be generated? → A: Database-generated via PostgreSQL `gen_random_uuid()` default on PK columns. Guaranteed unique, no coordination needed.
- Q: What activity log granularity? → A: Action-only (record `actor`, `action`, `entity_type`, `entity_id`, `timestamp`). No payload snapshots for MVP. Simpler, less storage.

### Session 2026-01-22 (Implementation Details)

**User Story 1 - Note-First Canvas:**
- Q: What triggers ghost text besides 500ms pause? → A: Typing pause only. No manual trigger for MVP.
- Q: How to position multiple margin annotations? → A: Vertical stack next to block, scroll if overflow.
- Q: What patterns trigger issue detection? → A: Action verbs + entities (e.g., "implement X", "fix Y", "add Z").
- Q: How to display deleted linked issue in note? → A: Strikethrough + "Deleted" badge on rainbow box. User can unlink.
- Q: What context for ghost text? → A: Current block + 3 previous blocks + 3 sections summary (semantic) + user history/typing patterns.
- Q: Max ghost text length? → A: 1-2 sentences (~50 tokens). Short, quick suggestions.
- Q: Ghost text in code blocks? → A: Code-aware suggestions using code completion model.
- Q: How to cancel ghost text? → A: Auto-cancel on any keystroke.
- Q: How to handle word boundaries in ghost text streaming? → A: Buffer chunks until whitespace/punctuation before display. Word-by-word (→) splits on whitespace only. Never display partial tokens. (DD-067)

**User Story 2 - AI Issue Creation:**
- Q: When should duplicate detection run? → A: Auto on title blur (when user finishes typing title).

**User Story 3 - AI PR Review:**
- Q: When should AI review trigger? → A: Auto on PR open via webhook. No manual trigger needed.

**User Story 4 - Sprint Planning:**
- Q: How to calculate velocity? → A: Sum of story points for issues completed in cycle.

**User Story 12 - AI Context:**
- Q: How to discover code files for context? → A: AST analysis of code references in description (e.g., parse "UserService.ts" mentions).
- Q: What patterns to detect? → A: File paths + symbols (e.g., 'src/UserService.ts', 'UserService.create()', 'class UserRepository').
- Q: How to resolve to actual files? → A: GitHub API search in linked repos for matching files/symbols.
- Q: What context to extract? → A: Function signature + docstring + import dependencies.

**User Story 18 - GitHub Integration:**
- Q: How should commit linking work? → A: Hybrid: parse on webhook + scheduled scan for missed commits.
- Q: Should PR merge auto-transition issue? → A: Yes, always auto-complete. PR merge → issue to "Completed".

**User Story 3 - PR Review Details:**
- Q: What aspects to review? → A: Architecture + Security + Quality (design patterns, vulnerabilities, code smells, test coverage).
- Q: Comment format? → A: Severity (🔴🟡🔵) + suggestion + rationale + prompt to retrace issue + AI fix prompt per issue.

**Embedding Configuration:**
- Q: When to regenerate embeddings? → A: On significant change (>20% content diff via hash comparison).
- Q: Chunk size? → A: 512 tokens with 50 token overlap.

**Issue Detection & Extraction:**
- Q: How to present detected issues? → A: Inline rainbow box around text + margin count ('3 issues detected').
- Q: What metadata to pre-fill? → A: Title + description + priority + labels (AI suggests all based on context).

**TipTap Editor Configuration:**
- Q: How to handle @mentions? → A: Typeahead with recent items first, then search as user types.
- Q: Which extensions? → A: Full suite (Core + Code + Table + Image + Mention + Math + Diagrams + Embeds).

**Security & Authentication:**
- Q: API key encryption? → A: AES-256-GCM with Supabase Vault. Keys never stored in plaintext.
- Q: Session token strategy? → A: Access token (1h) + Refresh token (7d). Rotate on refresh.
- Q: Admin RLS handling? → A: Role check in policy (`workspace_members.role IN ('admin', 'owner')`).

**Data Model & API Design:**
- Q: Issue link modeling? → A: Junction table `issue_links` with columns: from_id, to_id, link_type (blocks, relates, duplicates).
- Q: Pagination strategy? → A: Cursor-based for stable pagination with real-time updates.
- Q: List response format? → A: Envelope with meta: `{data: [...], meta: {total, cursor, hasMore}}`.
- Q: Optimistic updates? → A: TanStack Query optimistic updates with automatic rollback on error.

### Session 2026-01-22 (Ambiguity Resolution)

**Issue State Machine:**
- Q: Can cancelled issues be reopened? → A: No, cancelled is terminal state. Create new issue to reopen work.

**Duplicate Detection:**
- Q: How to handle 100% duplicate match? → A: Warn but allow. Show dialog with link to existing issue; user can proceed if intentional.

**Real-time Updates:**
- Q: How do users see other users' changes without co-editing? → A: Supabase Realtime for state change notifications. DD-005 (no co-editing) preserved.

**Code Parsing:**
- Q: Which languages for AI Context code discovery? → A: AST for Python, TypeScript/JavaScript, Go, Java, Rust. Regex fallback for others.

**Cycle Management:**
- Q: How should cycle rollover work? → A: Manual selection. Modal lists incomplete issues; user picks rollover vs backlog.

**AI Confidence Display:**
- Q: What confidence tiers to display? → A: Three tiers per DD-048 and US-02 AS-6: Recommended (≥80%), Default (50-79%), Alternative (<50%). Percentage shown on hover.

### Session 2026-01-22 (Architecture Patterns)

**Backend Architecture:**
- Q: CQRS handler structure? → A: Service Classes with Payloads (CQRS-lite). One class per service (CreateIssueService, GetIssueService) with execute(payload) method.
- Q: AI agent structure? → A: Claude Agent SDK for orchestration with state machines.
- Q: Repository pattern? → A: Generic + Specific. BaseRepository[T] with CRUD, domain-specific extensions (IssueRepository.find_duplicates()).
- Q: API versioning? → A: URL path (/api/v1/issues).
- Q: Error format? → A: RFC 7807 Problem Details ({type, title, status, detail, instance}).
- Q: DI pattern? → A: dependency-injector library with full container and providers.

**Infrastructure:**
- Q: Database migrations? → A: Alembic autogenerate with manual review before commit.
- Q: Configuration management? → A: Pydantic Settings with .env files. Type-safe validation.
- Q: Logging structure? → A: Structlog JSON with correlation IDs for observability.

**Frontend Architecture:**
- Q: Feature module structure? → A: Feature folders (features/issues/, features/notes/) with colocated components, hooks, stores, api.
- Q: TipTap extension organization? → A: Extension per feature (GhostTextExtension, MarginAnnotationExtension).
- Q: Error handling? → A: Inline errors only. Show errors in triggering component.
- Q: Auth flow? → A: Supabase JS Client SDK handles tokens, refresh, session automatically.
- Q: File uploads? → A: Direct to Supabase Storage with signed URL. Backend validates metadata.

### Session 2026-01-22 (Frontend Architecture Decisions)

**State Management & Data Flow:**
- Q: What is TanStack Query vs MobX responsibility split? → A: MobX UI-only. TanStack Query handles ALL server data (fetching, caching, mutations, optimistic updates). MobX only for ephemeral UI state (selection, toggles, local form drafts, temporary filters). No MobX store subscribes to TanStack Query - use `useQuery` hooks directly.
- Q: How to merge Supabase Realtime updates with TanStack Query cache? → A: Optimistic merge. Parse Realtime payload, directly update cache with `queryClient.setQueryData()`. Last-write-wins (MVP). Skip Realtime update if local mutation pending for that entity.

**TipTap/ProseMirror Editor:**
- Q: How to cancel ghost text request when user continues typing? → A: AbortController. Each request creates new AbortController, signal passed to fetch(). Previous controller aborted on new keystroke or unmount.
- Q: Which virtualization for TipTap Note Canvas with 1000+ blocks? → A: @tanstack/react-virtual. TipTap NodeView wraps virtualized container. Block heights measured via ResizeObserver, cached in store. Scroll position preserved.
- Q: How to handle Tab key conflicts between ghost text and code block? → A: Context-aware priority. Tab accepts ghost text ONLY when visible. Inside code block, Tab inserts indent. Priority order: 1) code block context, 2) ghost text visible, 3) default behavior.
- Q: How to detect content changes for embedding refresh? → A: Block-level tracking via TipTap transaction. Track added/modified/deleted blocks in onUpdate. >20% blocks changed OR title/heading changed → trigger embedding refresh. Debounce 5s before queue.
- Q: How to position margin annotations relative to blocks? → A: CSS Anchor Positioning API (Chrome 125+). Fallback to absolute positioning with calculated offsets for Safari/Firefox. Block has `anchor-name: --block-{id}`, annotation uses `position-anchor`.

**Performance & Bundle Optimization:**
- Q: Which components to dynamically import vs bundle statically? → A: Heavy components only. Dynamic import (`next/dynamic`): Sigma.js, Mermaid, AI Panel. Static: TipTap, Command Palette. Threshold: >50KB gzipped = dynamic candidate.
- Q: Module barrel conventions to avoid bundle size issues? → A: Feature-level only. One barrel per feature (`@/features/issues/index.ts`). No component-level barrels. Named exports only, no `export *`.

**SSE & AI Streaming:**
- Q: One SSE stream per AI feature or multiplexed? → A: Separate streams + cookie auth. Each AI operation gets own EventSource. HttpOnly cookie for session. EventSource created on operation start, closed on completion/abort.
- Q: How to display AI streaming errors? → A: Context-specific display. Ghost text: inline muted "AI unavailable" with 3s fade. AI Panel: panel error state with retry button. PR review: toast + notification center. Network errors: retry with exponential backoff (3 attempts).
- Q: How to handle SSE auth for long-running streams? → A: Cookie-based auth with heartbeat. Access token in HttpOnly cookie (1h expiry). Server sends heartbeat every 30s. Client reconnects with token refresh if no heartbeat for 45s. Max 3 reconnect attempts with exponential backoff (1s, 2s, 4s).
- Q: How to detect dead SSE connections? → A: Server heartbeat + client timeout. Server sends SSE comment (`: heartbeat\n\n`) every 30s. Client closes connection if no data/heartbeat received for 45s. Triggers reconnect with fresh token.

**Accessibility & Focus:**
- Q: How to handle focus when switching between Note Canvas, Sidebar, and Command Palette? → A: Explicit escape pattern. Tab stays in editor (cycles blocks or accepts ghost text). Escape exits to sidebar focus. F6 cycles major regions: Sidebar → Canvas → AI Panel. Modal focus trapped, restored on close.
- Q: How to respect prefers-reduced-motion? → A: CSS media query. All animations in CSS with `@media (prefers-reduced-motion: reduce)` fallback. Tailwind `motion-safe:` and `motion-reduce:` variants. JS animations check `window.matchMedia()` before triggering.

**Testing Architecture:**
- Q: How to test TipTap editor, SSE streaming, and accessibility? → A: Integration + E2E with MSW and axe-core. Unit tests for pure functions/hooks (Vitest). Integration: TipTap with real editor in jsdom. E2E: Playwright for critical user flows. SSE: MSW handlers for streaming. Accessibility: axe-core in CI + manual screen reader testing.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Note-First Collaborative Writing (Priority: P0)

A developer or product manager captures rough ideas in the note canvas, **clarifies ambiguous concepts with AI expert agents**, and **extracts explicit root issues from implicit requests** through collaborative refinement.

**Why this priority**: This is the core differentiator of Pilot Space. The note-first approach fundamentally changes how teams work—starting with thinking, clarifying with AI, and extracting explicit issues from vague requests. All other features build on this foundation.

**The Note-First Flow**:
1. **Write** — User captures rough, implicit ideas ("We need to change auth")
2. **Clarify** — AI asks probing questions via margin annotations ("What's driving this? Security? Scale?")
3. **Discuss** — User and AI refine understanding in threaded discussion
4. **Extract** — AI identifies explicit root issues (Security vuln, compliance, migration plan)
5. **Structure** — Explicit issues created with proper metadata, linked to source

**Reference**: DD-013 (Note-First Collaborative Workspace), DD-014-054 (UI Clarifications)

**Acceptance Scenarios**:

*Core Canvas Experience:*
1. **Given** a user opens Pilot Space, **When** the app loads, **Then** the note canvas is the default home view (not a dashboard)
2. **Given** a user is typing in the note canvas, **When** they pause for 500ms, **Then** AI ghost text suggestions appear inline as faded text
3. **Given** ghost text is displayed, **When** the user presses Tab, **Then** the entire suggestion is accepted; pressing → accepts word-by-word

*AI Clarification Flow (Implicit → Explicit):*
4. **Given** a user writes an ambiguous statement, **When** AI detects implicit intent, **Then** margin annotations appear asking clarifying questions (e.g., "What's driving this change?")
5. **Given** a margin annotation asks a question, **When** the user clicks "Discuss", **Then** a threaded AI discussion opens for that block
6. **Given** user answers clarifying questions, **When** the discussion progresses, **Then** AI identifies explicit root issues from the implicit request
7. **Given** AI identifies root issues, **When** presenting them, **Then** AI categorizes as: 🔴 Explicit (what user said), 🟡 Implicit (what user meant), 🟢 Related (what user will also need)

*Issue Extraction:*
8. **Given** a user is writing, **When** AI detects actionable content, **Then** margin annotations appear with count of detected items
9. **Given** margin annotations exist, **When** the user clicks "Review", **Then** rainbow-bordered boxes wrap source text inline showing proposed issues
10. **Given** a proposed issue is displayed, **When** the user reviews it, **Then** they can edit title/description before accepting or skip to next
11. **Given** an issue is accepted, **When** created, **Then** the issue links back to the source note (bidirectional sync)
12. **Given** a linked issue changes state, **When** the user views the note, **Then** a sync indicator badge shows the state change

*Selection & AI Actions:*
13. **Given** a user wants AI help on selected text, **When** they select text, **Then** a toolbar appears with AI actions: Improve, Simplify, Expand, Ask, Extract
14. **Given** a user invokes /ask, **When** the command executes, **Then** a threaded AI discussion opens for that block

*Performance & Navigation:*
15. **Given** a note has 1000+ blocks, **When** the user scrolls, **Then** virtualized rendering maintains smooth 60fps performance
16. **Given** a note has multiple headings, **When** the user views the note, **Then** an auto-generated table of contents appears with click-to-scroll navigation
17. **Given** a user is editing a note, **When** they pause typing for 1-2 seconds, **Then** content saves automatically with a subtle "Saved" indicator
18. **Given** a user makes edits (including AI changes), **When** they press Cmd+Z, **Then** the extended undo stack reverts the most recent change (text, AI, or block move)
19. **Given** a user clicks a margin annotation, **When** the annotation links to a content block, **Then** the linked block highlights with smooth scroll animation
20. **Given** a note is frequently accessed, **When** the user clicks "Pin", **Then** the note appears at the top of the sidebar
21. **Given** the user needs more annotation space, **When** they drag the margin edge, **Then** the margin panel resizes between 150px and 350px
22. **Given** a new note opens, **When** viewing the header, **Then** the user sees created date, last edited, author, word count, and AI-estimated reading time

*AI Annotation Types:*
23. **Given** a user writes text, **When** MarginAnnotationAgent analyzes it, **Then** it generates one of three annotation types: `suggestion` (text improvement), `warning` (ambiguity/missing context), or `issue_candidate` (actionable items with action verbs + entities pattern)
24. **Given** an annotation is generated, **When** it appears in the margin, **Then** it shows type-specific icon (💡 suggestion, ⚠️ warning, 🎯 issue_candidate) and appropriate action buttons

---

### User Story 2 - Create and Manage Issues with AI Assistance (Priority: P1)

A software development team member needs to quickly capture bugs, features, or tasks while AI assists with enhancing the quality and consistency of issue data.

**Why this priority**: Issue management is the fundamental building block of the entire platform. Without reliable issue tracking, no other features provide value. AI-enhanced issue creation differentiates Pilot Space from competitors.

**Independent Test**: Can be fully tested by creating issues with AI suggestions and verifying labels, priorities, and duplicate detection work correctly. Delivers immediate value to any development team.

**Acceptance Scenarios**:

1. **Given** a user is creating a new issue, **When** they type a brief title, **Then** AI suggests an enhanced, searchable title within 2 seconds
2. **Given** a user has entered a description, **When** they request AI enhancement, **Then** AI expands the description with acceptance criteria and technical notes
3. **Given** issue content is entered, **When** the user views suggestions, **Then** AI recommends relevant labels, priority level, and potential assignees based on expertise
4. **Given** a new issue is being created, **When** similar issues exist, **Then** the system flags potential duplicates with similarity score above 70%
5. **Given** AI makes suggestions, **When** the user reviews them, **Then** they can accept, modify, or reject each suggestion independently
6. **Given** AI suggests labels or priorities, **When** displaying confidence, **Then** contextual tags appear (Recommended, Default, Alternative) with percentage on hover
7. **Given** multiple issues are selected, **When** the user invokes AI bulk action, **Then** AI can summarize or extract common themes from the selection
8. **Given** a user right-clicks on an issue, **When** the context menu opens, **Then** an AI section shows contextual suggestions (e.g., "Find related issues", "Suggest assignee")

---

### User Story 3 - Receive AI Code Review on Pull Requests (Priority: P1)

A developer or tech lead receives automated architecture and code review feedback when pull requests are created, ensuring quality and consistency across the codebase.

**Why this priority**: Code review is a critical differentiator and core value proposition. AI-powered PR review directly addresses the bottleneck of manual reviews and maintains architectural standards.

**Independent Test**: Can be tested by creating a PR in a linked GitHub repository and verifying AI review comments appear with actionable feedback on architecture, security, and quality.

**Acceptance Scenarios**:

1. **Given** a GitHub repository is linked to a project, **When** a PR is opened, **Then** AI automatically reviews the code within 5 minutes
2. **Given** AI completes a review, **When** issues are found, **Then** comments are posted inline on the PR with specific line references
3. **Given** a PR with code changes, **When** AI reviews it, **Then** the review covers architecture compliance, security vulnerabilities, code quality, and performance concerns
4. **Given** AI review identifies a critical issue, **When** the review is posted, **Then** the issue is clearly marked with severity (Critical/Warning/Suggestion)
5. **Given** a PR author reviews AI feedback, **When** they want more context, **Then** each comment includes rationale and relevant documentation links
6. **Given** a PR exceeds size limits (>5000 lines or >50 files), **When** AI review is triggered, **Then** the system reviews priority files only with a summary note indicating partial review and recommendations

**PR Size Limits**: Maximum 5000 lines changed, 50 files maximum. PRs exceeding limits receive partial review with priority on critical paths (security, core logic, public APIs).

---

### User Story 4 - Plan and Track Sprints (Priority: P1)

A tech lead or product manager creates sprint cycles, assigns work, and tracks progress through a visual board with status tracking.

**Why this priority**: Sprint/cycle management is essential for agile teams. This provides the core scrum board functionality that replaces tools like Jira.

**Independent Test**: Can be tested by creating a cycle, adding issues, moving them through states, and verifying sprint metrics display correctly.

**Acceptance Scenarios**:

1. **Given** a user is a project admin, **When** they create a new cycle, **Then** they can set start date, end date, and sprint goals
2. **Given** a cycle exists, **When** a user adds issues to it, **Then** issues appear on the sprint board organized by state
3. **Given** issues are in a cycle, **When** a user drags an issue to a new column, **Then** the issue state updates immediately
4. **Given** a cycle is active, **When** a user views the cycle, **Then** they see completion percentage, velocity, and burndown metrics
5. **Given** a cycle ends, **When** incomplete issues exist, **Then** the user can roll them over to the next cycle or return to backlog

---

### User Story 12 - AI Context for Issues (Priority: P1)

A developer opens an issue and views comprehensive AI-aggregated context (related docs, code files, dependencies) with actionable tasks optimized for AI-assisted implementation with Claude Code.

**Why this priority**: AI Context directly addresses the pain of context-switching and information gathering. Developers get everything they need to start implementation in one view.

**Reference**: PS-017 (AI Context for Issues), DD-055 (AI Context Architecture), DD-056 (AI Context Update Strategy)

**Acceptance Scenarios**:

1. **Given** a user opens an issue, **When** they click the "AI Context" tab, **Then** they see aggregated context within 5 seconds
2. **Given** AI Context is displayed, **When** viewing related context, **Then** they see linked issues (blocks, relates, blocked by), related documents, and relevant code files
3. **Given** code files are listed, **When** viewing details, **Then** they see file paths with key functions/classes extracted (AST-aware)
4. **Given** AI Context is complete, **When** viewing tasks, **Then** they see AI-generated implementation checklist with dependencies
5. **Given** tasks are displayed, **When** viewing a task, **Then** they see ready-to-use prompts optimized for Claude Code
6. **Given** the user wants more context, **When** they use the chat input, **Then** they can refine context through conversation
7. **Given** linked data changes, **When** viewing AI Context, **Then** a badge shows "Updates available" with regenerate option
8. **Given** completed context, **When** clicking "Copy All Context", **Then** markdown export is copied to clipboard
9. **Given** task dependencies exist, **When** viewing tasks, **Then** they see a visual dependency graph
10. **Given** AI Context includes files, **When** files contain `.env` or credentials, **Then** they are automatically excluded

---

### User Story 18 - Link and Track GitHub Repositories (Priority: P1)

A development team links their GitHub repositories to projects, enabling automatic tracking of commits, pull requests, and branch activity with bidirectional status updates.

**Why this priority**: GitHub integration is essential for developer workflows. Linking PRs to issues, tracking commits, and automatic status updates are core capabilities expected by development teams.

**Reference**: PS-011 (GitHub Integration), DD-004 (MVP Integration Scope)

**Acceptance Scenarios**:

1. **Given** a project admin is in project settings, **When** they navigate to Integrations, **Then** they see GitHub connection option with OAuth flow
2. **Given** GitHub OAuth is completed, **When** connection succeeds, **Then** the user can select repositories to link to the project
3. **Given** a repository is linked, **When** a commit mentions an issue ID (e.g., "fixes PROJ-123"), **Then** the commit is linked to that issue within 5 minutes
4. **Given** a commit is linked to an issue, **When** viewing the issue, **Then** the user sees the commit in the activity timeline with message, author, and link to GitHub
5. **Given** a PR is opened that references an issue, **When** the PR is created, **Then** the PR is linked to the issue and visible in the issue detail
6. **Given** a linked PR changes status (merged, closed), **When** the webhook is received, **Then** the issue state can auto-transition based on project settings
7. **Given** a user views an issue with linked PRs, **When** clicking on a PR link, **Then** they navigate directly to GitHub PR page
8. **Given** a project has branch naming conventions, **When** creating an issue, **Then** the user can copy a suggested branch name (e.g., `feature/PROJ-123-issue-title`)
9. **Given** GitHub API rate limit is hit, **When** syncing, **Then** the system queues operations with exponential backoff and notifies the user of delays
10. **Given** a linked repository is disconnected, **When** the admin removes the link, **Then** existing commit/PR links are preserved but no new syncing occurs

---

### Edge Cases

- What happens when AI provider API key is invalid or expired? System should gracefully disable AI features with clear error message and allow manual operations.
- What happens when GitHub/Slack integration fails mid-sync? Operations should be idempotent with retry capability and sync state preserved.
- What happens when GitHub API rate limit is hit during PR review? System queues review via Supabase Queues with exponential backoff (initial 1 min, max 30 min) and notifies user of delay via in-app notification and optional Slack message.
- What happens when a user tries to access a project they don't have permission for? RLS policy denies access; return clear access denied message without revealing project existence.
- What happens when duplicate detection finds 100% match? Present clear warning but allow user to proceed if intentional.
- What happens when AI suggestion confidence is below 50%? Show suggestion with uncertainty indicator, requiring explicit user confirmation.
- What happens during workspace deletion? All data (issues, pages, integrations) must be soft-deleted with 30-day recovery window. RLS policies ensure cascading isolation.
- What happens when two users edit the same page simultaneously? Last-write-wins (DD-005); overwritten user receives in-app notification with link to view/restore their version from activity log.
- What happens when AI fails during content generation? Non-blocking error displays as margin annotation with retry and dismiss options; user can continue working manually.
- What happens when a note has 5000+ blocks and user scrolls rapidly? Virtual scroll only renders visible blocks plus buffer; scroll position preserved on content changes.
- What happens when Supabase Edge Function times out during AI processing? Job marked as failed in queue, retry with exponential backoff. After 3 failures, notify user via in-app notification.
- What happens when Supabase Storage upload fails mid-transfer? Resumable upload (tus protocol) allows retry from last successful chunk.

---

## Requirements *(mandatory)*

### Functional Requirements

**Core Project Management**
- **FR-001**: System MUST allow users to create workspaces containing multiple projects
- **FR-002**: System MUST allow users to create, read, update, and delete issues with title, description, state, priority, and assignees
- **FR-003**: System MUST support customizable issue states with groupings (unstarted, started, completed, cancelled). Valid transitions: all forward moves allowed (unstarted→started→completed); completed can reopen to started; any state can transition to cancelled; no direct unstarted→completed skip.
- **FR-004**: System MUST allow creating cycles (sprints) with start/end dates and associating issues
- **FR-005**: System MUST display cycle progress metrics including completion percentage and issue counts by state
- **FR-006**: System MUST define module (epic) data model for grouping related issues *(Note: Data model foundation only - full Module/Epic feature in Phase 2 US-05)*
- **FR-007**: System MUST provide a rich text editor for notes with autosave *(Note: Documentation pages feature in Phase 2 US-06; MVP uses same TipTap editor for notes)*
- **FR-008**: System MUST support views with filtering by state, priority, assignee, label, and date range
- **FR-009**: System MUST support board, list, and calendar layout views for issues
- **FR-010**: System MUST allow creating and applying labels to issues for categorization

**Note-First Canvas (Home Interface)**
- **FR-011**: System MUST display the note canvas as the default home view on application launch
- **FR-012**: System MUST provide a block-based rich text editor for notes using TipTap/ProseMirror
- **FR-013**: System MUST display AI ghost text suggestions after 500ms typing pause *(Uses Template model for ghost text context patterns)*
- **FR-014**: System MUST support Tab key to accept full ghost text, Right Arrow for word-by-word acceptance
- **FR-015**: System MUST display margin annotations linked to specific content blocks
- **FR-016**: System MUST automatically detect actionable items in notes and suggest issue extraction
- **FR-017**: System MUST wrap extracted issues in rainbow-bordered boxes inline with source text
- **FR-018**: System MUST maintain bidirectional sync between notes and extracted issues
- **FR-019**: System MUST support threaded AI discussions per content block with persistence
- **FR-020**: System MUST provide version history panel with AI reasoning for AI-made changes
- **FR-021**: System MUST support @ mentions for notes, issues, projects, and AI agents

**AI Features (BYOK)**
- **FR-022**: System MUST allow workspace admins to configure API keys for supported LLM providers (OpenAI, Anthropic, Google Gemini, Azure OpenAI)
- **FR-023**: System MUST provide AI-enhanced issue creation with title improvement, description expansion, and metadata suggestions
- **FR-024**: System MUST detect potential duplicate issues during creation with configurable similarity threshold
- **FR-025**: System MUST provide AI task decomposition that generates subtasks from feature descriptions *(Note: Data model foundation only - full TaskDecomposerAgent in Phase 2 US-05)*
- **FR-026**: System MUST provide AI code review on linked GitHub pull requests covering architecture, security, quality, and performance
- **FR-027**: System MUST post AI review comments directly to GitHub PRs with inline line references
- **FR-028**: System MUST provide AI documentation generation from code analysis or feature descriptions *(Note: Data model foundation only - full DocumentGeneratorAgent in Phase 2 US-06)*
- **FR-029**: System MUST generate diagrams from natural language descriptions in Mermaid format *(Note: Data model foundation only - full DiagramGeneratorAgent in Phase 2 US-06)*
- **FR-030**: System MUST track AI-generated content origin including model, prompt hash, and generation timestamp for audit purposes *(Note: Data model foundation only - full AI provenance UI in Phase 2)*
- **FR-031**: System MUST clearly label all AI-generated content with visual indicators *(Note: Data model foundation only - full AI content labeling UI in Phase 2)*
- **FR-032**: System MUST require human approval for AI actions that create, modify, or delete data

**AI Agent Scope (MVP)**

| Agent | MVP | SDK Mode | Provider |
|-------|-----|----------|----------|
| **GhostTextAgent** | ✅ | Direct SDK | Google Gemini Flash |
| **MarginAnnotationAgent** | ✅ | Claude SDK `query()` | Anthropic Claude |
| **PRReviewAgent** | ✅ | Claude SDK (agentic) | Anthropic Claude |
| **AIContextAgent** | ✅ | Claude SDK (agentic) | Anthropic Claude |
| **IssueExtractorAgent** | ✅ | Claude SDK `query()` | Anthropic Claude |
| **DuplicateDetectorAgent** | ✅ | pgvector + Claude | Hybrid |
| **AssigneeRecommenderAgent** | ✅ | Claude SDK `query()` | Anthropic Haiku |

*Note: 7 MVP agents listed above. MarginAnnotationAgent generates clarifying questions and suggestions for note blocks.*

*Deferred Agents (Phase 2)*: TaskDecomposerAgent, DiagramGeneratorAgent (FR-029), DocumentGeneratorAgent (FR-028), PatternMatcherAgent. AI content labeling (FR-031) UI components also deferred to Phase 2.

*Reference: DD-002 (BYOK Architecture), DD-058 (Agent SDK Modes), AI_CAPABILITIES.md*

**AI Context for Issues**
- **FR-033**: System MUST aggregate related context (linked issues, documents, code files) when viewing an issue
- **FR-034**: System MUST generate AI implementation checklists with task dependencies for issues
- **FR-035**: System MUST provide ready-to-use prompts optimized for Claude Code per task
- **FR-036**: System MUST support conversation-based context refinement in AI Context view
- **FR-037**: System MUST provide "Copy All Context" export to markdown clipboard
- **FR-038**: System MUST exclude sensitive files (.env, credentials) from AI Context automatically
- **FR-039**: System MUST show "Updates available" badge when linked data changes

**GitHub Integration**
- **FR-050**: System MUST support GitHub integration via OAuth for repository linking
- **FR-051**: System MUST track commits that reference issue IDs and link them to issues
- **FR-052**: System MUST link pull requests to issues and update issue state on PR events
- **FR-093**: System MUST provide suggested branch names based on issue ID and title (e.g., `feature/PROJ-123-issue-title`) with copy-to-clipboard action

<!--
FR Numbering Notes:
- FR-040 to FR-049: Reserved for Slack Integration (Phase 2 US-09)
- FR-053 to FR-056: Reserved for Advanced GitHub Features (Phase 2 US-08)
See specs/002-pilot-space-phase2/spec.md for these requirements.
-->

**Access Control**
- **FR-057**: System MUST support four role levels: Owner, Admin, Member, Guest
- **FR-058**: System MUST restrict workspace management to Owner and Admin roles
- **FR-059**: System MUST restrict guest users to viewing and commenting on assigned issues only
- **FR-060**: System MUST authenticate users via Supabase Auth (GoTrue) supporting email/password, magic links, OAuth2 social providers (GitHub, Google, Microsoft), and SAML 2.0 SSO
  > **Note**: SAML 2.0 SSO is provided natively by Supabase Auth. Configuration via Supabase Dashboard (managed) or `config.toml` (self-hosted). No application code required.
- **FR-061**: System MUST issue JWT tokens with automatic refresh (access: 1 hour, refresh: 7 days) via Supabase Auth
- **FR-062**: System MUST enforce authorization via Row-Level Security (RLS) policies at database level

**Data Management**
- **FR-063**: System MUST use soft deletion for all user content with restoration capability. Restoration permitted by original creator OR workspace admin/owner only.
- **FR-064**: System MUST maintain activity logs for all issue, note, and page changes
- **FR-065**: System MUST support data export for workspace backup in JSON archive format (ZIP containing structured JSON files per entity type)
- **FR-094**: System MUST support data import from JSON archive backup files for restore purposes (same format as export)

<!--
FR Numbering Notes:
- FR-066 to FR-070: Reserved for Notification System (Phase 2 US-07)
- FR-071 to FR-078: Reserved for Semantic Search (Phase 3 US-10)
- FR-079 to FR-085: Reserved for Knowledge Graph (Phase 2 US-14)
- FR-086 to FR-092: Reserved for Templates & Automation (Phase 2 US-15)
See specs/002-pilot-space-phase2/spec.md and specs/003-pilot-space-phase3/spec.md for these requirements.
-->

**Background Jobs (Supabase Queues)**
- **FR-095**: System MUST use Postgres-native message queue (pgmq) for background job processing
- **FR-096**: System MUST schedule recurring jobs using pg_cron extension
- **FR-097**: System MUST process background jobs with guaranteed delivery and exactly-once semantics within visibility window
- **FR-098**: System MUST retry failed jobs with exponential backoff (max 3 retries, delays: 2s, 4s, 8s)
- **FR-099**: System MUST clean up completed jobs older than 7 days automatically via pg_cron
- **FR-100**: System MUST expose job monitoring via /admin/jobs endpoint showing queue depth and job status
- **FR-101**: System MUST process AI operations (PR review, embeddings) via Supabase Edge Functions

**Supabase Storage**
- **FR-102**: System MUST store uploaded files in Supabase Storage with S3-compatible API
- **FR-103**: System MUST enforce storage access control via Row-Level Security (RLS) policies
- **FR-104**: System MUST support resumable uploads using tus protocol for files >5MB
- **FR-105**: System MUST provide on-the-fly image transformations (resize, crop, format conversion) via Supabase Image Transformation
- **FR-106**: System MUST serve files via CDN for optimal performance
- **FR-107**: System MUST support public and private buckets with policy-based access control
- **FR-108**: System MUST limit file upload size to 50MB per file (configurable per workspace)
- **FR-109**: System MAY scan uploaded files for malware using ClamAV integration (post-MVP enhancement for enterprise deployments)

**Database & Vector Search (Supabase)**
- **FR-110**: System MUST use PostgreSQL 16+ as the primary database via Supabase
- **FR-111**: System MUST use pgvector extension with HNSW indexing for semantic search (m=16, ef_construction=64)
- **FR-112**: System MUST store embeddings in 3072-dimensional vectors (OpenAI text-embedding-3-large)
- **FR-113**: System MUST perform hybrid search combining vector similarity + full-text + filters
- **FR-114**: System MUST index embeddings asynchronously via background jobs
- **FR-115**: System MUST use connection pooling (PgBouncer) to handle 1000+ concurrent connections
- **FR-116**: System MUST enable point-in-time recovery (PITR) with 7-day retention

**Row-Level Security (RLS)**
- **FR-117**: System MUST enforce all data authorization via PostgreSQL RLS policies
- **FR-118**: System MUST enable RLS on all user data tables
- **FR-119**: System MUST use `auth.uid()` function to identify current user in RLS policies
- **FR-120**: System MUST implement policy-based access control for workspace membership
- **FR-121**: System MUST audit RLS policy changes via database triggers
- **FR-122**: System MUST use service role key only in trusted backend services (FastAPI)
- **FR-123**: System MUST use anon key for client-side Supabase SDK (with RLS enforcement)

### Non-Functional Requirements

**Availability & Recovery**
- **NFR-001**: System MUST maintain 99.5% uptime (~3.6 hours maximum unplanned downtime per month)
- **NFR-002**: System MUST support Recovery Time Objective (RTO) of 4 hours for full service restoration
- **NFR-003**: System MUST perform automated daily backups with 30-day retention
- **NFR-004**: System MUST deploy in single-region with automated failover within availability zones

**Performance**
- **NFR-005**: API read operations (GET) MUST respond within 500ms at p95
- **NFR-006**: API write operations (POST/PUT/DELETE) MUST respond within 1 second at p95
- **NFR-007**: System MUST use connection pooling for database operations
- **NFR-019**: System MUST enforce tiered rate limiting: 1000 req/min for standard API endpoints, 100 req/min for AI endpoints, per workspace

**Accessibility**
- **NFR-008**: System MUST conform to WCAG 2.1 Level AA accessibility guidelines
- **NFR-009**: All interactive elements MUST be keyboard accessible with visible focus indicators
- **NFR-010**: System MUST support screen readers with appropriate ARIA labels and landmarks

**Deployment & Infrastructure (Supabase)**
- **NFR-011**: System MUST deploy backend as containerized FastAPI service
- **NFR-012**: System MUST deploy frontend as Next.js application (Vercel or self-hosted)
- **NFR-013**: System MUST use Supabase managed service OR self-hosted Supabase platform
- **NFR-014**: System MUST reduce infrastructure services from 10+ to 2-3 services (Supabase + FastAPI + Next.js)
- **NFR-015**: System MUST provide Docker Compose for local development with Supabase CLI
- **NFR-016**: System MUST support environment-based configuration (dev, staging, production)
- **NFR-017**: System MUST implement health check endpoints for all services (/health)
- **NFR-018**: System MUST use managed PostgreSQL connection pooling (no separate PgBouncer container)

### Key Entities

- **Workspace**: Container for all projects, members, and settings within an organization. Has name, slug, and owner.
- **Project**: Unit of work organization within a workspace. Contains issues, cycles, modules, pages, notes. Has identifier prefix for issue numbering.
- **Note**: Primary collaborative document for thought-first workflow. Contains blocks of content, AI margin annotations, threaded discussions, and extracted issues. Has title, content blocks, and version history with AI reasoning.
- **Issue**: Core work item with title, description, state, priority, assignees, labels, and links. Belongs to one project, optionally to cycle and module. May link to source note block.
- **AIContext**: Aggregated context for an issue including related issues, documents, code files, and AI-generated implementation tasks with Claude Code prompts.
- **Cycle**: Time-boxed sprint with start/end dates. Contains issues for the sprint period. Has velocity and burndown metrics.
- **Module**: Epic/feature grouping for issues. Tracks progress across multiple issues toward a larger goal. *(Note: Data model foundation only - full Module/Epic feature in Phase 2 US-05)*
- **Page**: Rich text documentation with hierarchical organization. Supports Mermaid diagrams inline. *(Note: Data model foundation only - full Pages feature in Phase 2 US-06)*
- **User**: Authenticated person with email, name, and workspace memberships with roles. Identity managed by Supabase Auth; local record stores workspace-specific preferences and role mappings.
- **Label**: Categorization tag with name and color. Applied to issues for filtering.
- **Activity**: Audit log entry recording changes to issues, notes, and pages with actor, timestamp, and change details.
- **Integration**: Connection to external service (GitHub) with credentials and configuration.
- **AIConfiguration**: Workspace-level settings for LLM providers including encrypted API keys and preferences.
- **Template**: Reusable note template with placeholder patterns for AI ghost text context. Contains structure, default content, and AI prompt hints. *(Note: Data model foundation only - full Template feature in Phase 2 US-15)*

## Assumptions

1. Users have existing LLM provider accounts and API keys (BYOK model)
2. Teams are familiar with agile/scrum methodologies and terminology
3. GitHub repositories to be integrated are accessible via OAuth to team members
4. Internet connectivity is required for AI features (cloud LLM providers)
5. Modern web browser (Chrome, Firefox, Safari, Edge - latest 2 versions)
6. English is the primary language for AI features in MVP
7. Team sizes range from 5-100 members per workspace in MVP
8. Issue volumes up to 50,000 per workspace in MVP
9. Real-time collaboration on pages is NOT required in MVP (DD-005: standard editing with autosave, last-write-wins)
10. No compliance certifications (GDPR, SOC2) required for MVP; deferred to Phase 3 Enterprise
11. Standard application logs sufficient for MVP; advanced observability (metrics, tracing) deferred to Phase 2
12. No AI usage tracking in MVP; users monitor LLM costs via their provider dashboards directly
13. Supabase managed service or self-hosted Supabase platform available for deployment
14. No LDAP authentication required in MVP; SAML 2.0 SSO covers enterprise needs
15. Background job processing completes within 10 minutes; longer AI workflows handled via streaming responses

## Success Criteria *(mandatory)*

### Measurable Outcomes

**User Efficiency**
- **SC-001**: Users can create a fully detailed issue (with AI-enhanced title, description, labels, priority) in under 2 minutes
- **SC-002**: AI code review completes and posts comments within 5 minutes of PR creation
- **SC-003**: 80% of AI-suggested labels are accepted by users without modification
- **SC-004**: Sprint planning time reduces by 30% compared to manual planning baseline (baseline: average planning session duration before AI assistance, measured via time tracking in first 2 sprints)

**System Performance**
- **SC-005**: Page load time under 3 seconds on standard broadband connection
- **SC-006**: System supports 100 concurrent users per workspace without degradation
- **SC-007**: Issue state changes reflect in UI within 1 second

**Adoption & Satisfaction**
- **SC-008**: 70% of workspace members use AI features at least weekly
- **SC-009**: User satisfaction score above 4.0/5.0 for AI assistance quality
- **SC-010**: GitHub integration successfully links 95% of PRs mentioning issue IDs

**Data Integrity**
- **SC-011**: Zero data loss for user content during normal operations
- **SC-012**: Soft-deleted content recoverable for 30 days
- **SC-013**: Activity logs capture 100% of issue and page modifications

**Infrastructure (Supabase)**
- **SC-014**: Infrastructure reduced to 2-3 services (from 10+)
- **SC-015**: Local development setup time under 5 minutes (`supabase start` + backend + frontend)
- **SC-016**: RLS policies enforce 100% of authorization decisions at database level
- **SC-017**: Background job retry success rate above 95% after 3 attempts

---

## Related Documentation

### Phase Documentation

| Phase | Document | Scope |
|-------|----------|-------|
| MVP (This) | [spec.md](./spec.md), [plan.md](./plan.md) | P0 + P1 features (6 user stories) |
| Phase 2 | [spec.md](../002-pilot-space-phase2/spec.md), [plan.md](../002-pilot-space-phase2/plan.md) | P2 features (9 user stories) |
| Phase 3 | [spec.md](../003-pilot-space-phase3/spec.md), [plan.md](../003-pilot-space-phase3/plan.md) | P3 features (3 user stories) |

### SDLC Documentation Suite

Complete lifecycle documentation is available in the [sdlc/](./sdlc/README.md) directory:

| Phase | Document | Purpose |
|-------|----------|---------|
| Requirements | [PRD](./sdlc/01-requirements/PRD.md) | Business objectives, personas, scope |
| Requirements | [RTM](./sdlc/01-requirements/requirements-traceability.md) | Traceability matrix |
| Requirements | [Acceptance Criteria](./sdlc/01-requirements/acceptance-criteria-catalog.md) | MVP testable scenarios |
| Requirements | [NFRs](./sdlc/01-requirements/nfr-specification.md) | Quality attributes |
| Architecture | [C4 Diagrams](./sdlc/02-architecture/c4-diagrams.md) | System context, containers, components |
| API | [Developer Guide](./sdlc/03-api/api-developer-guide.md) | REST API integration |
| AI | [Agent Reference](./sdlc/04-ai-agents/AI_AGENT_REFERENCE.md) | MVP AI agents catalog |
| Development | [Contributing](./sdlc/05-development/CONTRIBUTING.md) | Git workflow, code standards |
| Development | [Testing](./sdlc/05-development/testing-strategy.md) | Test pyramid, coverage |
| Development | [Local Setup](./sdlc/05-development/local-development.md) | Docker, environment |
| Operations | [Deployment](./sdlc/06-operations/deployment-guide.md) | Production deployment |
| Operations | [Incident Response](./sdlc/06-operations/incident-response.md) | SEV1-4 runbooks |
| User Guide | [Getting Started](./sdlc/07-user-guide/getting-started.md) | End-user onboarding |
| Governance | [Documentation](./sdlc/08-governance/documentation-governance.md) | Doc-as-code practices |

### Other References

- [Implementation Plan](./plan.md) - Architecture decisions and project structure
- [Data Model](./data-model.md) - Entity definitions and relationships
- [UI Design Spec](./ui-design-spec.md) - Interface specifications
- [Design Decisions](../../docs/DESIGN_DECISIONS.md) - 85 architectural decision records
- [Architecture Docs](../../docs/architect/README.md) - Technical architecture index
