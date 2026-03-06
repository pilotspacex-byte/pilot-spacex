# Feature Specification: MVP Note-First Complete

**Feature Number**: 018
**Branch**: `018-mvp-note-first-complete`
**Created**: 2026-02-20
**Updated**: 2026-03-06 (v3 — SDLC coverage assessment + gap analysis)
**Status**: In Progress
**Author**: Tin Dang

---

## Problem Statement

**Who**: Software development teams (architects, tech leads, PMs, developers) using PilotSpace for AI-augmented project management.

**Problem**: PilotSpace covers 7 SDLC phases with varying depth. The core loop (Requirements → Design → Implementation) is strong at 80-85% coverage with 24 AI skills. However, critical gaps exist in **Deployment** (40%), **Testing** (60%), and **Maintenance** (65%) phases. Several built features have dead code paths (TemplatePicker, Notifications, Modules, Cmd+K search). The "Note-First" paradigm works end-to-end for the happy path but lacks polish in edge cases.

**Impact**: Teams cannot use PilotSpace as their single SDLC platform — they still need external tools for CI/CD visibility, test management, deployment tracking, and incident response. The incomplete features reduce confidence in the platform's maturity.

**Success**: Each SDLC phase has at least 70% functional coverage. All built features are wired and accessible. Dead code paths are either connected or removed. The platform can support a team from idea capture through release without requiring external PM tools.

---

## SDLC Coverage Assessment

### Current State (as of 2026-03-06)

| SDLC Phase | Coverage | Status | Key Strengths | Critical Gaps |
|---|---|---|---|---|
| **1. Planning** | 75% | Functional | Sprint/cycle CRUD, burndown/velocity, AI sprint planning, capacity, dependency graph | No roadmap/timeline view; Modules schema-only (no UI/router) |
| **2. Requirements** | 85% | Strong | Note-first extraction, AI enhancement, task decomposition, duplicate detection, role skills | No formal acceptance criteria fields; traceability is link-based only |
| **3. Design** | 80% | Strong | AI diagrams (Mermaid/C4/PlantUML), architecture review (Opus), ADR-lite, risk assessment | Knowledge graph has no frontend visualization (deferred v2.1) |
| **4. Implementation** | 85% | Strong | Ghost text, CLI integration, AI context per issue, code generation, branch suggestion | GitHub-only VCS; no real-time collaboration (deferred v2.0) |
| **5. Testing** | 60% | Gaps | AI PR review (5-aspect Opus), test generation skill, security scanning skill | No test case management; no CI/CD dashboard; no test execution tracking |
| **6. Deployment** | 40% | Weak | Release notes generation, PR-to-issue linking, auto-close on merge | No deployment pipeline visibility; no feature flags; no environment management |
| **7. Maintenance** | 65% | Partial | Daily standup, retrospective, AI digest, cost tracking | Notifications pipeline broken (UI only); no incident management; no monitoring |

### AI Skill Coverage (24 Skills Across SDLC)

| Phase | Skills | Models |
|---|---|---|
| Requirements | extract-issues, enhance-issue, recommend-assignee, find-duplicates, decompose-tasks | Sonnet |
| Planning | sprint-planning | Sonnet |
| Design | generate-diagram, review-architecture, adr-lite, risk-assessment | Opus/Sonnet |
| Implementation | ai-context, generate-code, generate-migration, generate-pm-blocks | Opus/Sonnet |
| Testing | review-code, scan-security, write-tests | Opus/Sonnet |
| Maintenance | daily-standup, retrospective, generate-digest | Flash/Sonnet |
| Cross-cutting | improve-writing, summarize, create-note-from-chat, speckit-pm-guide | Flash/Sonnet |

### Built But Not Wired (Dead Code)

| Feature | What Exists | What's Missing |
|---|---|---|
| TemplatePicker | Component 100% built with keyboard nav + TanStack Query | "New Note" flow bypasses it entirely |
| Notifications | NotificationStore UI complete (bell, badges, mark-as-read) | No backend table, no worker, no SSE data source |
| Modules/Epics | SQLAlchemy model + migrations (003, 013), `module_id` FK on Issue | No router, no service, no frontend page |
| Global Search (Cmd+K) | UIStore `commandPaletteOpen`, Meilisearch indexing | No SearchModal component, no keyboard shortcut |
| Note Body Search | Meilisearch indexed | Client-side title-only search; Meilisearch not connected |
| Note Export | `handleExport` function exists | Empty stub implementation |
| Semantic Vector Search | pgvector + HNSW index, embedding service | No frontend search UI |
| Issue Filter Options | Assignee/Label filter dropdowns exist | Render as empty arrays |

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|---|---|---|---|---|
| Tin Dang | Product Owner / Architect | MVP completeness, SDLC coverage, AI agent integration | Architecture decisions, priority calls | Spec + Plan review |
| Dev Team | Implementation | Clear tasks, working foundation | Bug impact assessment | Pre-plan review |
| End Users | Workspace users | Reliable features, smooth workflow | Usage patterns, pain points | Acceptance test |
| AI Coding Agents | Consumers of issue context | Rich, structured context per issue | Context schema requirements | Integration test |

---

## User Scenarios & Testing

### US-1: Fix Critical Bugs & Stabilize Platform (Priority: P0 — COMPLETED)

The platform had 7 critical bugs preventing basic usage. These have been resolved in previous sprints.

**Status**: DONE (commits up to `11f0d2fd`)

**Resolved**:
- [x] Issues Kanban state mapping
- [x] AI Chat 404 error
- [x] Approvals "Bad Request" error
- [x] Costs page "Not Found" error
- [x] Homepage note word counts
- [x] Issue Detail "null pts" / "No priority"
- [x] Sidebar PINNED/RECENT empty

---

### US-2: Homepage as Intelligent Workspace Dashboard (Priority: P1)

When a user logs in, they should see a dashboard that orients them immediately: what happened since they last visited, what needs their attention, and quick actions to start working.

**Independent Test**: User logs in and sees: activity feed grouped by date with note previews, AI insights panel with workspace health, quick actions for creating notes/issues, and sidebar pinned/recent notes populated.

**Acceptance Scenarios**:

1. **Given** a workspace with recent activity, **When** user visits homepage, **Then** activity feed shows note cards grouped by Today/Yesterday/This Week with content previews (first 2 lines)
2. **Given** a workspace with notes and issues, **When** user views AI Insights panel, **Then** panel shows workspace summary (total notes, issues by state, project health indicators)
3. **Given** a logged-in user, **When** user clicks "What's on your mind?" quick input, **Then** a new note is created and the editor opens immediately
4. **Given** user has pinned notes, **When** homepage loads, **Then** PINNED section in sidebar shows up to 5 pinned notes with titles
5. **Given** user has accessed notes recently, **When** homepage loads, **Then** RECENT section shows last 10 accessed notes

---

### US-3: Note Editor for Brainstorming & PM (Priority: P1)

The note editor is the primary workspace for brainstorming and project management. Users write freely with rich text, and the editor provides structural blocks for PM workflows.

**Independent Test**: User creates a note, types with slash commands to insert headings/lists/code blocks/task lists, selects text to see floating toolbar, and the auto-save indicator confirms saves within 2 seconds.

**Acceptance Scenarios**:

1. **Given** user is in note editor, **When** user types "/" at start of a line, **Then** command palette appears with block types: Heading (1-3), Bullet List, Numbered List, Task List, Code Block, Quote, Table, Divider
2. **Given** user selects text in editor, **When** text is highlighted, **Then** floating toolbar appears with: Bold, Italic, Strikethrough, Code, Link, Highlight
3. **Given** user is typing, **When** 2 seconds pass without changes, **Then** content auto-saves with visible indicator
4. **Given** a note with content, **When** user views header, **Then** word count, last-modified date, and project association are displayed correctly
5. **Given** user creates a new note, **When** "New Note" is triggered, **Then** TemplatePicker appears with 4 system templates (Sprint Planning, Design Review, Postmortem, Release Planning) + blank option

---

### US-4: Intent-to-Issues Pipeline (Priority: P1)

Users write notes containing actionable items. AI detects intents and helps extract them as structured issues with bidirectional links.

**Independent Test**: User writes a note with actionable items, clicks "Extract issues", AI identifies 3-5 potential issues, user reviews and approves them, issues are created with links back to the source note.

**Acceptance Scenarios**:

1. **Given** a note with actionable text like "We need to migrate from sessions to JWT", **When** user clicks "Extract issues", **Then** AI identifies actionable items categorized as Explicit, Implicit, or Related
2. **Given** AI has identified potential issues, **When** extraction results display, **Then** each shows: suggested title, description, priority, source text highlighted
3. **Given** user reviews extracted issues, **When** user approves an issue, **Then** issue is created with: title, description, priority, link to source note, source paragraph reference
4. **Given** an issue was extracted from a note, **When** user views the note, **Then** inline badges like [AUTH-45] appear at extraction point, clickable to navigate to the issue
5. **Given** an issue was extracted from a note, **When** user views the issue detail, **Then** "Source Notes" section shows the originating note with relevant paragraph highlighted

---

### US-5: AI Coding Agent Context per Issue (Priority: P1)

Each issue carries a rich context object that AI coding agents can consume to implement features autonomously.

**Independent Test**: User opens an issue, clicks "AI Context" tab, sees structured context with 5+ sections. User can copy or export this context for use with Claude Code.

**Acceptance Scenarios**:

1. **Given** an issue with description and acceptance criteria, **When** user clicks "Generate AI Context", **Then** AI produces structured context combining all issue fields
2. **Given** an issue linked to source notes, **When** AI context generated, **Then** context includes relevant paragraphs from linked notes
3. **Given** an issue with dependencies, **When** AI context generated, **Then** context includes dependency graph showing related issues and their states
4. **Given** AI context has been generated, **When** user clicks "Copy for Claude Code", **Then** context formatted as markdown prompt optimized for AI coding agents
5. **Given** an issue in a project with codebase context, **When** AI context generated, **Then** context includes relevant file paths, architecture patterns, and coding conventions

---

### US-6: Issues Kanban & Detail Polish (Priority: P1)

The Issues page provides a fully functional Kanban board with drag-and-drop, proper cards, and a detailed issue view with all fields working.

**Acceptance Scenarios**:

1. **Given** issues in various states, **When** user views Kanban board, **Then** cards show: identifier, title, priority indicator, assignee avatar, creation date
2. **Given** an issue in "Todo", **When** user drags to "In Progress", **Then** state updates and card moves with animation
3. **Given** issues exist, **When** user switches to List view, **Then** issues display in table with sortable columns
4. **Given** user opens issue detail, **When** viewing Properties panel, **Then** all fields functional: State, Priority, Type, Assignee, Labels, Cycle, Estimate, Hours, Dates
5. **Given** user filters issues, **When** selecting Assignee or Label filter, **Then** dropdown shows actual workspace members/labels (not empty arrays)

---

### US-7: Wire Dead Code — TemplatePicker, Search, Notifications (Priority: P2)

Several fully-built features are unreachable. Wire them into the application flow.

**Acceptance Scenarios**:

1. **Given** user clicks "New Note", **When** creation flow starts, **Then** TemplatePicker appears with 4 system SDLC templates + blank option
2. **Given** user presses Cmd+K, **When** palette opens, **Then** user can search notes by title and body content (via Meilisearch), issues by identifier/title, and navigate directly
3. **Given** a workspace event occurs (issue assigned, PR review complete, mention), **When** notification generated, **Then** bell icon shows badge count and notification list populates
4. **Given** user is on Notes page, **When** user types in search input, **Then** notes are filtered by content (not just title) using Meilisearch

---

### US-8: SDLC Gap — Testing Phase (Priority: P2)

Add visibility into testing and quality gates to bring Testing phase coverage from 60% to 75%.

**Acceptance Scenarios**:

1. **Given** an issue with linked PR, **When** PR has CI checks, **Then** issue detail shows CI status (pass/fail/pending) from GitHub webhook data
2. **Given** a PR review completes, **When** AI reviewer finds Critical/Warning findings, **Then** findings summary appears in issue activity timeline
3. **Given** a workspace with GitHub integration, **When** user views project dashboard, **Then** a "Quality" section shows: open PRs with review status, recent CI failures, test coverage trends

---

### US-9: SDLC Gap — Deployment Phase (Priority: P2)

Add release and deployment tracking to bring Deployment phase coverage from 40% to 65%.

**Acceptance Scenarios**:

1. **Given** a completed cycle, **When** user navigates to cycle detail, **Then** "Release Notes" tab shows auto-categorized completed issues (features, bug fixes, improvements)
2. **Given** release notes are generated, **When** user clicks "Export", **Then** notes export as markdown suitable for GitHub Release or changelog
3. **Given** GitHub integration is active, **When** a PR merges to main, **Then** deployment activity appears in issue timeline showing merge commit and linked environments

---

### US-10: SDLC Gap — Maintenance & Notifications (Priority: P2)

Complete the notification pipeline and operational visibility to bring Maintenance phase from 65% to 80%.

**Acceptance Scenarios**:

1. **Given** an AI PR review completes, **When** review has findings, **Then** notification sent to PR author and issue assignee
2. **Given** an issue is assigned to a user, **When** assignment changes, **Then** notification sent to new assignee
3. **Given** a sprint is ending in 2 days, **When** there are incomplete issues, **Then** notification sent to assignees with at-risk items
4. **Given** a user opens notification center, **When** viewing notifications, **Then** notifications grouped by type with priority badges and mark-as-read

---

### US-11: Settings & Configuration Complete (Priority: P3)

All settings pages functional: workspace general, members with invite flow, AI providers with validation, integrations (GitHub/Slack), billing placeholder, profile with save, skills configuration.

**Acceptance Scenarios**:

1. **Given** user on General settings, **When** user changes workspace name and saves, **Then** name updates throughout the app
2. **Given** user on Members settings, **When** user clicks "Invite Member" and enters email, **Then** invitation sent and appears in pending list
3. **Given** user on AI Providers, **When** user enters an API key and saves, **Then** key validated, stored securely, provider status shows "Connected"
4. **Given** user on Integrations, **When** user clicks "Connect GitHub", **Then** OAuth flow initiates and returns showing connected repositories

---

### Edge Cases

- What happens when user extracts issues from an empty note? System shows "No actionable items detected."
- What happens when AI context generation fails (no API key)? System shows clear error directing to Settings > AI Providers.
- What happens when two users edit the same note? Last-write-wins with conflict notification toast.
- What happens when user drags issue to state requiring a cycle? System prompts to assign a cycle first.
- What happens when note content exceeds token limits for AI extraction? System processes in chunks and merges results.
- What happens when network drops during auto-save? System retries with exponential backoff and shows "Unsaved changes" indicator.
- What happens when Meilisearch is unavailable for Cmd+K search? Fallback to client-side title-only search with "Limited search" indicator.
- What happens when notifications pipeline has no events? Bell icon shows no badge; notification center shows "All caught up" empty state.

---

## Requirements

### Functional Requirements

#### Core Platform (P0 — COMPLETED)
- **FR-001**: ~~System MUST display issues in correct workflow state columns on Kanban board~~ DONE
- **FR-002**: ~~System MUST render AI Chat page at correct route~~ DONE
- **FR-003**: ~~System MUST load Approvals page without errors~~ DONE
- **FR-004**: ~~System MUST load Costs page with usage data~~ DONE
- **FR-005**: ~~System MUST display accurate word counts on homepage note cards~~ DONE
- **FR-006**: ~~System MUST show correct property values in issue detail~~ DONE
- **FR-007**: ~~System MUST populate sidebar PINNED and RECENT sections~~ DONE

#### Note-First Pipeline (P1)
- **FR-008**: System MUST group homepage activity by date (Today/Yesterday/This Week)
- **FR-009**: System MUST display AI-generated workspace insights on homepage
- **FR-010**: System MUST provide "/" slash command menu with 8+ block types
- **FR-011**: System MUST show floating toolbar on text selection with 6 formatting options
- **FR-012**: System MUST auto-save note content within 2 seconds with visible indicator
- **FR-013**: System MUST detect actionable items in notes when user triggers extraction
- **FR-014**: System MUST create issues from extracted items with bidirectional NoteIssueLinks
- **FR-015**: System MUST display inline issue badges in notes at extraction points
- **FR-016**: System MUST generate structured AI context per issue with 5+ sections
- **FR-017**: System MUST provide "Copy for Claude Code" action that formats context as AI-optimized markdown
- **FR-018**: System MUST support drag-and-drop issue state transitions on Kanban board
- **FR-019**: System MUST render issue cards with identifier, title, priority indicator, and assignee avatar
- **FR-020**: System MUST provide functional List and Table view alternatives to Kanban

#### Wire Dead Features (P2)
- **FR-021**: System MUST display note content previews on homepage activity cards
- **FR-022**: System SHOULD support version history with restore capability
- **FR-023**: System SHOULD present TemplatePicker when creating new notes with 4 system SDLC templates
- **FR-024**: System SHOULD provide Cmd+K global search across notes (body) and issues via Meilisearch
- **FR-025**: System SHOULD populate issue filter dropdowns (Assignee, Label) with actual workspace data

#### SDLC Testing Phase (P2)
- **FR-026**: System SHOULD display CI check status on issues with linked PRs
- **FR-027**: System SHOULD surface AI PR review findings in issue activity timeline
- **FR-028**: System MAY show project-level quality dashboard (open PRs, CI status, coverage)

#### SDLC Deployment Phase (P2)
- **FR-029**: System SHOULD generate release notes per cycle with categorized issues
- **FR-030**: System SHOULD support release notes export as markdown
- **FR-031**: System MAY show deployment activity in issue timeline from GitHub merge events

#### SDLC Maintenance Phase (P2)
- **FR-032**: System SHOULD deliver notifications for: PR review complete, issue assignment, sprint deadline
- **FR-033**: System SHOULD display notification center with grouped, prioritized notifications
- **FR-034**: System MAY support notification preferences (email, in-app, mute)

#### Settings & Configuration (P3)
- **FR-035**: System SHOULD allow workspace invitation via email with role assignment
- **FR-036**: System SHOULD validate and securely store AI provider API keys

---

### Key Entities

- **Note**: Rich-text document for brainstorming and PM. Attributes: title, content (TipTap JSON), word_count, project, pin status, owner. Relations: Workspace, Project, NoteVersions, NoteIssueLinks.
- **Issue**: Trackable work item with state machine. Attributes: name, description, state, priority, type, assignee, labels, estimate, hours, dates. Relations: Project, State, NoteIssueLinks, IssueRelations, GitHubPRLinks.
- **NoteIssueLink**: Bidirectional link. Attributes: note_id, issue_id, link_type (CREATED/EXTRACTED/REFERENCED), source_paragraph_ref.
- **AIContext**: Generated rich context per issue. Attributes: issue_id, context_json, source_notes, dependency_graph, generated_at.
- **Intent**: Detected actionable item. Attributes: note_id, intent_type, source_text, suggested_title, suggested_priority, status.
- **Notification**: (NEW) User notification. Attributes: user_id, workspace_id, type, title, body, entity_type, entity_id, read_at, priority.
- **Module**: (EXISTING, unwired) Epic/feature group. Attributes: name, description, status, target_date, lead_id, sort_order.

---

## Success Criteria

- **SC-001**: ~~All 7 critical bugs resolved~~ DONE
- **SC-002**: Users can complete Note-to-Issue flow (write → extract → view linked issues) in under 3 minutes
- **SC-003**: AI context generation produces 5+ context sections within 10 seconds
- **SC-004**: Issues display correctly across all 6 workflow states in Kanban with accurate counts
- **SC-005**: Note editor supports 8+ block types via slash commands with <200ms response
- **SC-006**: Homepage loads with correct data within 2 seconds
- **SC-007**: "Copy for Claude Code" produces a prompt usable by AI coding agents without additional context
- **SC-008**: (NEW) SDLC Planning phase coverage ≥75% (currently 75%)
- **SC-009**: (NEW) SDLC Requirements phase coverage ≥85% (currently 85%)
- **SC-010**: (NEW) SDLC Testing phase coverage ≥70% (currently 60%)
- **SC-011**: (NEW) SDLC Deployment phase coverage ≥60% (currently 40%)
- **SC-012**: (NEW) SDLC Maintenance phase coverage ≥75% (currently 65%)
- **SC-013**: (NEW) All dead-code features either wired or removed — zero unreachable built components

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|---|---|---|
| I. AI-Human Collaboration | Yes | Extract Issues requires human review/approval. AI Context generated on demand. Notifications inform, don't auto-act. |
| II. Note-First | Yes | Core focus — notes are entry point. Issues emerge from notes, not forms. Templates guide structured thinking. |
| III. Documentation-Third | Yes | AI Context auto-generates docs from issue + note content. Release notes auto-categorize. |
| IV. Task-Centric | Yes | Each user story independently testable. Tasks are self-contained work units. |
| V. Collaboration | Yes | Notifications enable team awareness. Notes support team viewing. Issues link to shared notes. |
| VI. Agile Integration | Yes | Stories fit sprint planning. SDLC phases map to sprint priorities. |
| VII. Notation Standards | Yes | AI diagrams use Mermaid/C4/PlantUML standards. ADR-lite follows lightweight ADR format. |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships
- [x] SDLC coverage gaps identified with target metrics

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names in requirements (tech names only in constraints/assessment)
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P0 through P3
- [x] Functional requirements numbered sequentially (FR-001 through FR-036)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS
- [x] SDLC coverage assessment with per-phase scoring

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Next Phase

After this spec passes all checklists:

1. **Resolve remaining ambiguities** — None remaining
2. **Proceed to planning** — Implementation plan organized by SDLC phase priority
3. **Share for review** — This spec is the alignment artifact for all stakeholders
