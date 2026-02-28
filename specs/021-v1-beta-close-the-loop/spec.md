# Milestone Specification: v1.0-beta — Team-Ready AI Workspace

**Feature Number**: 021
**Branch**: `021-v1-beta`
**Created**: 2026-02-28
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: A software team of 5-10 members evaluating Pilot Space as their AI-augmented SDLC platform.

**Problem**: Pilot Space has a powerful backend (48 routers, 24 AI skills, 9 MCP servers) and a functional frontend — but the product is not yet viable for daily team use. A new user arriving today faces five blockers:

1. **Can't find anything.** No global search. Notes search is title-only (client-side). 100+ notes and issues become unnavigable. Meilisearch is deployed but has no frontend surface.
2. **Starts from blank every time.** `TemplatePicker` is fully built (4 SDLC templates, keyboard navigation, TanStack Query integration) but never rendered. "New Note" drops straight into a blank editor. Users never see Sprint Planning, Design Review, Postmortem, or Release Planning templates.
3. **Collaboration is silent.** `NotificationStore` has a full UI (bell icon, priority badges, mark-as-read) but zero data sources. `addNotification()` is called by no code path. Supabase Realtime subscriptions were removed. A teammate commenting on an issue produces no signal.
4. **Can't organize work beyond projects.** No Modules/Epics UI. The `module` SQLAlchemy model exists (with status, target_date, lead). Issues have a `module_id` FK. But there is no router, no service, no frontend page. Teams managing multiple features have no grouping mechanism between "project" (too coarse) and "issue" (too granular).
5. **Can't get work out.** Note export is a stub (`// to be implemented`). Share copies an authenticated internal URL. Users cannot produce Markdown, PDF, or public links. Work created in Pilot Space is trapped in Pilot Space.

**What IS working** (verified 2026-02-28):
- All core pages load without errors (Homepage, Notes, Issues, Chat, Approvals, Costs, Settings)
- Note editor with 20+ TipTap extensions, `[[wiki linking]]`, inline issue badges, ghost text, PM blocks
- AI chat with thinking visualization, tool call cards, file attachments, Google Drive integration
- Issue extraction from notes with auto-approve and NoteIssueLink bidirectional tracking
- GitHub integration (webhooks, PR linking, auto-transition)
- AuthCore JWT microservice + frontend bridge
- 24 AI skills executable via `\` trigger in chat
- Homepage AI digest with daily briefing and standup generator
- Settings pages functional (Members, AI Providers, Skills, Integrations)

**Success**: A team of 5 can use Pilot Space daily for one sprint cycle: create notes from templates, organize issues into modules, find content via Cmd+K, receive notifications when teammates act, export meeting notes as Markdown, and discover AI skills through the command palette.

---

## Milestone Pillars

### Pillar 1 — Find Anything

| Story | Readiness | Effort | User Value |
|-------|-----------|--------|------------|
| S1: Global Search (Cmd+K) | Backend Meilisearch ready; UIStore state ready; no SearchModal component | Medium | Critical — users can't find their own content |
| S2: Command Palette (Cmd+P) | UIStore state ready; shadcn cmdk available; no CommandPalette component | Medium | High — 24 skills + 18 routes with no keyboard access |
| S3: Keyboard Shortcut Guide (?) | No component | Small | Low — polish, teaches discoverability |

### Pillar 2 — Organize at Scale

| Story | Readiness | Effort | User Value |
|-------|-----------|--------|------------|
| S4: Modules/Epics | Backend model + migration exist; no router/service/UI | Large | High — teams can't group work into features |
| S5: Template Picker Active | Component 100% built; never mounted in "New Note" flow | Small | Critical — dead code, 1 line to activate |
| S6: Template Editor | No editor page; "Create Template" is a no-op stub | Medium | Medium — custom templates for team patterns |

### Pillar 3 — Stay Informed

| Story | Readiness | Effort | User Value |
|-------|-----------|--------|------------|
| S7: Notification Pipeline | Frontend UI 60% built; backend queue exists; no worker/table/SSE | Large | High — collaboration is currently silent |
| S8: Team Activity Feed | Homepage shows personal view only; no teammate attribution | Medium | Medium — no awareness of team changes |
| S9: Issue Filter Wiring | FilterBar component exists; assignee/label options default to [] | Small | Medium — two filter types are silently broken |

### Pillar 4 — Complete the Workflow

| Story | Readiness | Effort | User Value |
|-------|-----------|--------|------------|
| S10: Note Export (Markdown + PDF) | Export handler is empty stub | Medium | Medium-High — work is trapped in the platform |
| S11: AI Skill Discoverability | Skills only via `\` in chat; no visual menu outside chat input | Medium | Medium-High — 24 skills invisible to new users |
| S12: Full-text Note Search | Client-side title/topic only; Meilisearch not connected | Small | Medium — users can't search note content |

### Out of Scope (Deferred)

| Feature | Why Deferred |
|---------|-------------|
| Slack Integration (002 US-09) | 10+ days effort, external OAuth dependency, low team readiness (10% built) |
| Knowledge Graph (002 US-14) | 14+ days effort, zero frontend infrastructure, needs graph library |
| Real-time Collaboration / CRDT (016) | Requires Supabase Realtime load-test gate; architectural decision pending |
| Note Versioning (017) | Depends on 016 CRDT |
| Semantic Search (003 US-10) | pgvector exists but not needed for beta — Meilisearch full-text is sufficient |

---

## User Stories

### S1: Global Search Modal (Pillar 1 — Critical)

A user presses Cmd+K to open a search modal. Before typing, they see recent items. As they type, Meilisearch returns results across notes, issues, and projects with content type badges and text previews. Tab previews a result. Enter navigates to it.

**Existing infrastructure**: Meilisearch client (`infrastructure/search/meilisearch.py`) with workspace-scoped search. `UIStore.searchModalOpen` state. Notes and issues are indexed.

**What to build**: `SearchModal` component, Meilisearch API client in frontend, unified search endpoint (`GET /workspaces/{id}/search`), Cmd+K global keybinding.

**Acceptance Scenarios**:

1. **Given** user presses Cmd+K, **When** modal opens, **Then** recent items appear grouped by type (Notes, Issues, Projects).
2. **Given** user types a query, **When** results display, **Then** content type filters appear (All, Notes, Issues, Projects) with match count badges.
3. **Given** results exist, **When** user presses Tab on a result, **Then** a preview panel shows content snippet without navigating.
4. **Given** results exist, **When** user presses Enter, **Then** user navigates to the selected item and modal closes.
5. **Given** Meilisearch is unreachable, **When** modal opens, **Then** a fallback message appears and local title/topic search activates.

---

### S2: Command Palette (Pillar 1 — High)

User presses Cmd+P to open a command palette. Commands are categorized: Navigation (go to Notes, Issues, Projects), AI Skills (24 skills with descriptions), Editor Actions (bold, heading, etc.), Settings. Fuzzy search filters instantly. Each command shows its keyboard shortcut if one exists.

**Existing infrastructure**: `UIStore.commandPaletteOpen` state. shadcn `command.tsx` (cmdk wrapper). 24 skill definitions in `ai/templates/skills/`.

**What to build**: `CommandPalette` component, command registry (static list of navigation + skills + actions), Cmd+P global keybinding, context-aware ordering (note editor → show editor commands first).

**Acceptance Scenarios**:

1. **Given** user presses Cmd+P, **When** palette opens, **Then** commands are grouped by: Navigation, AI Skills, Editor Actions, Settings.
2. **Given** palette is open and user types "extract", **When** results filter, **Then** "Extract Issues from Note" appears with description and shortcut hint.
3. **Given** user selects an AI skill command, **When** Enter is pressed, **Then** the chat input opens with `\skill-name` pre-filled and palette closes.
4. **Given** user selects a navigation command (e.g., "Go to Issues"), **When** Enter is pressed, **Then** user navigates to `/issues` and palette closes.

---

### S3: Keyboard Shortcut Guide (Pillar 1 — Low)

User presses `?` outside a text input to see all available shortcuts grouped by category.

**Acceptance Scenarios**:

1. **Given** user presses `?` outside text input, **When** overlay opens, **Then** shortcuts grouped by: Navigation, Editor, AI, Search.
2. **Given** user is in a text input, **When** `?` is pressed, **Then** character types normally.

---

### S4: Modules/Epics (Pillar 2 — High)

A PM or tech lead creates modules (epics) to group related issues. Each module shows aggregated progress (% issues done), issue count, target date, and lead. Issues can be assigned to modules from the issue detail page.

**Existing infrastructure**: `Module` SQLAlchemy model with status enum, target_date, lead_id, sort_order. `module_id` FK on Issue with index. Migration `003` + `013`.

**What to build**:
- **Backend**: ModuleRepository, module service (CRUD + progress calculation), modules router (`/workspaces/{id}/modules`), Pydantic schemas
- **Frontend**: `/modules` route, module list page (cards with progress bars), module detail page (filtered issue list), module selector in issue detail properties, module-to-project assignment

**Acceptance Scenarios**:

1. **Given** a user creates a module with name, description, and target date, **When** saved, **Then** the module appears in the modules list with 0% progress.
2. **Given** a module exists, **When** issues are assigned to it, **Then** module progress reflects % of done issues (story points if available, count as fallback).
3. **Given** a module has a target date, **When** the date passes with incomplete issues, **Then** an overdue badge appears.
4. **Given** issue detail is open, **When** user clicks the Module property, **Then** a searchable dropdown shows available modules.
5. **Given** modules list, **When** user views it, **Then** each card shows: name, lead avatar, issue count, progress bar, target date.

---

### S5: Activate Template Picker (Pillar 2 — Critical)

The `TemplatePicker` component is 100% built — 4 SDLC system templates (Sprint Planning, Design Review, Postmortem, Release Planning), keyboard navigation, TanStack Query integration. It is never rendered. The "New Note" flow skips it entirely.

**What to build**: Mount `TemplatePicker` in the "New Note" flow. When user clicks "New Note" (sidebar or notes page), show the template picker first. Offer "Blank note" as the first option.

**Acceptance Scenarios**:

1. **Given** user clicks "New Note" in sidebar, **When** the action triggers, **Then** `TemplatePicker` modal opens showing Blank + 4 SDLC templates.
2. **Given** TemplatePicker is open, **When** user selects "Sprint Planning", **Then** a new note is created pre-filled with the Sprint Planning template structure.
3. **Given** TemplatePicker is open, **When** user selects "Blank", **Then** a new empty note is created (current behavior preserved).
4. **Given** TemplatePicker is open, **When** user presses Escape, **Then** modal closes without creating a note.

---

### S6: Template Editor (Pillar 2 — Medium)

Workspace admins can create and edit custom templates. The "Create Template" card in TemplatePicker currently has an empty stub (`// Navigate to template editor — future feature`).

**Existing infrastructure**: Template CRUD API (`note_templates.py` router), `Template` model with content as TipTap JSON, templates API client in frontend.

**What to build**: Template editor page (reuse note editor with save-as-template action), settings/templates management page for the workspace library.

**Acceptance Scenarios**:

1. **Given** an admin clicks "Create Template" in TemplatePicker, **When** the editor opens, **Then** a note editor appears with a "Save as Template" action instead of normal save.
2. **Given** a template is saved, **When** user opens TemplatePicker, **Then** the custom template appears in the "Custom Templates" section.
3. **Given** settings/templates page, **When** admin views it, **Then** all system + custom templates are listed with edit/delete actions (system templates read-only).

---

### S7: Notification Pipeline (Pillar 3 — High)

When a teammate comments on an issue, assigns a task, approves a PR, or mentions a user, a notification appears in the bell icon within 5 seconds. Notifications are persisted, prioritized (Urgent/Important/FYI), and dismissable.

**Existing infrastructure**: `NotificationStore` with full UI (bell icon, priority badges, mark-as-read, clear-all). `QueueName.NOTIFICATIONS` queue. `enqueue_notification()` method on queue client. Frontend notification-panel.tsx rendered in sidebar.

**What to build**:
- **Backend**: `notifications` table + migration + RLS, notification types enum, notification worker consuming from queue, `enqueue_notification()` calls at event sources (comment creation, issue assignment, PR review, @mention detection), notification API endpoint (list, mark-read, dismiss), SSE channel for real-time push
- **Frontend**: Connect `NotificationStore` to API on mount, subscribe to SSE for real-time delivery, notification settings page (per-type enable/disable)

**Acceptance Scenarios**:

1. **Given** user A comments on an issue assigned to user B, **When** the comment is saved, **Then** user B's notification bell shows a count badge within 5 seconds.
2. **Given** a notification exists, **When** user views the notification panel, **Then** it shows: title, description, priority badge (Urgent/Important/FYI), timestamp, and link to source.
3. **Given** unread notifications, **When** user clicks one, **Then** it navigates to the source and marks as read.
4. **Given** notification settings, **When** user disables "Comment" notifications, **Then** future comment events do not produce notifications for that user.

---

### S8: Team Activity Feed (Pillar 3 — Medium)

The homepage shows only the current user's personal notes and issues. Add a "Team Activity" section showing recent actions by teammates: issue state changes, note edits, comments, PR reviews — with author attribution.

**Existing infrastructure**: Homepage `DailyBrief` component. Activity model in backend. Homepage API returns `activity` data.

**What to build**: Extend homepage API to include team-member-attributed activity. Add "Team Activity" section to DailyBrief with author avatar, action verb, and target entity link.

**Acceptance Scenarios**:

1. **Given** a teammate moved PS-42 to "In Review" 1 hour ago, **When** user views homepage, **Then** Team Activity shows "Alice moved PS-42 to In Review — 1h ago" with Alice's avatar.
2. **Given** no team activity in the last 24h, **When** user views homepage, **Then** the Team Activity section is hidden (not shown as empty).
3. **Given** 20+ activities, **When** viewing, **Then** the feed shows the 10 most recent with a "View all" link.

---

### S9: Wire Issue Filter Options (Pillar 3 — Small)

The `FilterBar` component supports Assignee and Label filters, but `IssueViewsRoot` passes no options — both default to empty arrays. Users see State, Priority, and Type filters but Assignee and Label dropdowns never render.

**What to build**: Pass workspace members as `assigneeOptions` and project labels as `labelOptions` to `FilterBar` from `IssueViewsRoot`.

**Acceptance Scenarios**:

1. **Given** a workspace with 5 members, **When** user opens the Assignee filter dropdown, **Then** all 5 members appear as options with avatars.
2. **Given** issues with labels "backend" and "frontend", **When** user opens the Label filter dropdown, **Then** both labels appear as options.
3. **Given** user selects an assignee filter, **When** applied, **Then** only issues assigned to that member are shown.

---

### S10: Note Export (Pillar 4 — Medium-High)

Users can export a note as Markdown or PDF. The export button in the note header actually does something.

**Existing infrastructure**: TipTap `tiptap-markdown` extension for bidirectional Markdown conversion. Note content stored as TipTap JSON.

**What to build**: Export dropdown with Markdown (download `.md` file) and PDF (use browser print-to-PDF or html2pdf) options. Replace the empty `handleExport` stub.

**Acceptance Scenarios**:

1. **Given** a note with rich content, **When** user clicks Export → Markdown, **Then** a `.md` file downloads with correctly formatted headings, lists, code blocks, and tables.
2. **Given** a note, **When** user clicks Export → PDF, **Then** a print-friendly view opens or a PDF downloads.
3. **Given** a note with inline issue badges, **When** exporting, **Then** badges render as `[PS-42]` text in Markdown and as styled badges in PDF.

---

### S11: AI Skill Discoverability (Pillar 4 — Medium-High)

Users discover AI skills without knowing to type `\` in chat. The slash command menu in the note editor, the command palette, and a skills browser surface all 24 skills.

**Existing infrastructure**: `SkillMenu` triggered by `\` in chat. `SlashCommandExtension` in note editor. 24 skill YAML definitions.

**What to build**: Add AI skill category to Command Palette (S2). Add an "AI Actions" section to the slash command menu in notes with skill descriptions. Add a skill browser page or section in Settings/Skills showing all available skills with descriptions and trigger commands.

**Acceptance Scenarios**:

1. **Given** user opens Command Palette (Cmd+P), **When** they browse "AI Skills" category, **Then** all 24 skills are listed with names and one-line descriptions.
2. **Given** user types `/` in note editor, **When** slash menu opens, **Then** an "AI Actions" group shows relevant skills (extract-issues, improve-writing, summarize, generate-diagram).
3. **Given** user visits Settings → Skills, **When** viewing the page, **Then** all skills are listed with descriptions, trigger commands, and whether approval is required.

---

### S12: Full-text Note Search (Pillar 4 — Small)

Note list search currently filters client-side by title and topics only. Connect it to Meilisearch for full-text content search so users can find notes by phrases in the body.

**Existing infrastructure**: Meilisearch backend with notes index. `notesApi.searchNotes()` exists. Notes list page has a search box.

**What to build**: Replace client-side `filter()` in notes page with a Meilisearch API call. Show matched content snippets in results.

**Acceptance Scenarios**:

1. **Given** a note containing "the caching strategy decision", **When** user searches "caching strategy" in notes list, **Then** the note appears in results with a content snippet highlighted.
2. **Given** empty search query, **When** viewing notes list, **Then** default sort by recent (current behavior preserved).

---

## Sprint Plan

### Sprint 1: Quick Wins + Foundation (Week 1)

| Story | Effort | Priority |
|-------|--------|----------|
| **S5**: Activate TemplatePicker | XS (mount existing component) | P0 |
| **S9**: Wire issue filter options | S (pass props) | P0 |
| **S12**: Full-text note search | S (swap client filter for Meilisearch call) | P1 |
| **S3**: Keyboard shortcut guide | S (new overlay component) | P2 |

**Theme**: Activate dead code. Fix silently broken features. Zero new architecture.

### Sprint 2: Find Anything (Week 2-3)

| Story | Effort | Priority |
|-------|--------|----------|
| **S1**: Global Search (Cmd+K) | M (new component + backend endpoint + Meilisearch client) | P0 |
| **S2**: Command Palette (Cmd+P) | M (new component + command registry) | P0 |
| **S10**: Note Export | M (Markdown export + PDF option) | P1 |

**Theme**: Keyboard-first navigation. Content discoverability. Work portability.

### Sprint 3: Organize & Communicate (Week 4-5)

| Story | Effort | Priority |
|-------|--------|----------|
| **S4**: Modules/Epics | L (full stack: router + service + repository + UI) | P0 |
| **S7**: Notification Pipeline | L (full stack: table + worker + SSE + connect frontend) | P0 |
| **S6**: Template Editor | M (editor page + settings page) | P1 |

**Theme**: Team-scale organization. Communication infrastructure.

### Sprint 4: Team Awareness + Polish (Week 6)

| Story | Effort | Priority |
|-------|--------|----------|
| **S8**: Team Activity Feed | M (extend homepage API + frontend section) | P1 |
| **S11**: AI Skill Discoverability | M (palette integration + slash menu + skill browser) | P1 |
| E2E: Full workflow smoke test | M (AuthCore + Note-First pipeline verification) | P0 |
| Performance + Accessibility audit | S | P1 |

**Theme**: Team awareness. AI adoption. Release gate.

---

## Requirements Summary

### Functional Requirements

**Pillar 1 — Find Anything**
- **FR-001**: System MUST provide a global search modal on Cmd+K with full-text search across notes, issues, and projects via Meilisearch.
- **FR-002**: System MUST provide a command palette on Cmd+P with categorized commands (Navigation, AI Skills, Editor Actions, Settings) and fuzzy search.
- **FR-003**: System MUST connect the notes list search to Meilisearch for body content search (replacing client-side title-only filter).
- **FR-004**: System MUST provide a keyboard shortcut guide overlay on `?` key press outside text inputs.

**Pillar 2 — Organize at Scale**
- **FR-005**: System MUST provide a Modules page with CRUD, progress aggregation (% done issues), target date, and lead assignment.
- **FR-006**: System MUST allow issues to be assigned to modules from the issue detail properties panel.
- **FR-007**: System MUST show TemplatePicker when creating a new note, offering Blank + system SDLC templates.
- **FR-008**: System MUST provide a template editor for admins to create and manage custom workspace templates.

**Pillar 3 — Stay Informed**
- **FR-009**: System MUST deliver notifications within 5 seconds for: comments, assignments, state changes, @mentions, PR reviews.
- **FR-010**: System MUST persist notifications with priority classification (Urgent/Important/FYI) and per-type user preferences.
- **FR-011**: System MUST display team member activity on the homepage with author attribution and action descriptions.
- **FR-012**: System MUST populate Assignee and Label filter dropdowns in the issues filter bar with workspace member and label data.

**Pillar 4 — Complete the Workflow**
- **FR-013**: System MUST export notes as Markdown files with correct formatting of headings, lists, code blocks, tables, and issue references.
- **FR-014**: System MUST provide a PDF export option for notes.
- **FR-015**: System MUST surface AI skills in the Command Palette, note editor slash menu, and Settings/Skills browser page.

---

## Key Entities

| Entity | Status | This Milestone |
|--------|--------|---------------|
| Module | Model + migration exist; no router/service | Build full CRUD stack + frontend |
| Notification | Queue name exists; no table/worker | New table + worker + SSE + API |
| Template | Full CRUD backend + frontend TemplatePicker | Activate picker; build editor page |
| Meilisearch index | Backend indexed | Connect to frontend SearchModal |

---

## Success Criteria

- **SC-001**: Global search returns relevant results within 500ms for workspaces under 10,000 items. Users can find notes by body content, not just title.
- **SC-002**: Command palette surfaces all 24 AI skills and 18 navigation routes within 2 keystrokes of opening.
- **SC-003**: 100% of "New Note" flows go through TemplatePicker. Users can create notes from 4+ system templates.
- **SC-004**: Modules display aggregated progress. Issues can be grouped into modules. Overdue modules show warning badges.
- **SC-005**: Notifications arrive within 5 seconds of triggering events. Notification bell shows accurate unread count.
- **SC-006**: Note Markdown export produces valid, well-formatted `.md` files that render correctly in GitHub, VS Code, and Obsidian.
- **SC-007**: Issue filter bar shows Assignee and Label dropdowns populated with real workspace data.
- **SC-008**: Team Activity Feed shows attributed teammate actions on the homepage.
- **SC-009**: Test coverage > 80% for all new components and services.
- **SC-010**: Full Note → Extract Issues → AI Context → Copy for Claude Code workflow completes end-to-end.

---

## Risk Register

| ID | Risk | Prob | Impact | Score | Response |
|----|------|------|--------|-------|----------|
| R-1 | Notification SSE adds WebSocket-like complexity | 3 | 4 | 12 | Mitigate: Use existing SSE infrastructure from AI chat; avoid new transport |
| R-2 | Meilisearch index stale or misconfigured in dev environments | 2 | 3 | 6 | Mitigate: SearchModal falls back to API text search if Meilisearch health check fails |
| R-3 | Modules CRUD scope creep (roadmap view, timeline, Gantt) | 3 | 3 | 9 | Accept: MVP modules only — list + detail + progress. No timeline or Gantt |
| R-4 | Notification volume overwhelms users in active workspaces | 2 | 3 | 6 | Mitigate: Default to FYI priority; users configure per-type settings; batch digest option |
| R-5 | PDF export quality varies across browsers | 3 | 2 | 6 | Accept: Use browser print-to-PDF as v1; dedicated PDF renderer deferred |
| R-6 | Template editor complexity (custom fields, conditional sections) | 2 | 3 | 6 | Accept: v1 template editor is just a note editor with save-as-template. No custom fields |

---

## Dependency Map

```
Sprint 1 (Quick Wins) ──────────────── no dependencies
  S5: Activate TemplatePicker ──── mount existing component
  S9: Wire filter options ─────── pass props
  S12: Full-text note search ──── connect Meilisearch
  S3: Shortcut guide ──────────── standalone

Sprint 2 (Find Anything) ───────────── no dependencies on Sprint 1
  S1: Global Search (Cmd+K) ──── new component + endpoint
  S2: Command Palette (Cmd+P) ── new component + registry
  S10: Note Export ────────────── standalone

Sprint 3 (Organize & Communicate) ──── S2 enables S11 (skills in palette)
  S4: Modules/Epics ───────────── full stack
  S7: Notification Pipeline ───── full stack
  S6: Template Editor ─────────── depends on S5 (picker active)

Sprint 4 (Polish + Release) ────────── depends on S1-S3
  S8: Team Activity Feed ──────── extends homepage
  S11: AI Skill Discoverability ── uses S2 (palette) + slash menu
  E2E + Perf audit ────────────── final gate
```

**Parallelization**: Sprint 1 and Sprint 2 can run concurrently. Sprint 3 items are independent of each other. Sprint 4 is the final gate.

---

## Relationship to Existing Specs

| Source Spec | What This Milestone Takes | What Remains |
|-------------|--------------------------|-------------|
| 002-phase2 US-05 | Modules/Epics (S4) | — |
| 002-phase2 US-13 | Command Palette + Search (S1, S2) | FAB, AI panel, block reordering |
| 002-phase2 US-15 | Activate TemplatePicker + Editor (S5, S6) | AI-generated templates, conversational filling |
| 002-phase2 US-17 | Notification Pipeline (S7) | AI-prioritized inbox, Slack forwarding |
| 002-phase2 US-06 | Note Export (S10) covers doc portability | Dedicated Documentation Pages entity |
| 002-phase2 US-07 | Task decomposition already built | Story points UI (minor) |
| 002-phase2 US-08 | Architecture diagrams already built | `onLinkToIssue` callback (minor) |
| 002-phase2 US-09 | Slack — deferred | Full Slack integration |
| 002-phase2 US-14 | Knowledge Graph — deferred | Graph visualization |
| 003-phase3 US-10 | Meilisearch search (S1, S12) | Semantic vector search UI |

---

## After This Milestone

| Version | Theme | Key Features |
|---------|-------|-------------|
| v1.1 | Editor & AI Polish | Note embeds (`/link-note`), project picker, issue gutter indicators, AI skill auto-discovery learning |
| v1.2 | Integrations | Slack integration, GitHub enhanced (PR templates), webhook configurator |
| v2.0 | Collaboration | Real-time CRDT co-editing (016), block ownership engine, density controls |
| v2.1 | Intelligence | Note versioning + diff (017), knowledge graph (002 US-14), semantic search (003 US-10) |
