# Feature Specification: AI Context Tab - Full Implementation

**Feature Branch**: `005-conversation-fix`
**Created**: 2026-02-02
**Status**: Draft
**Input**: Implement the full AI Context tab from the design prototype (`design-system/prototype/issue-detail-full.html`) into the issue detail page. The prototype defines 6 major sections: (1) Header+Actions with Copy All/Regenerate, (2) Context Summary Card with stats, (3) Related Context with issues/documents, (4) Codebase Context with file tree/code snippets/git refs, (5) AI Tasks with dependency graph/checklist/prompts, (6) Enhance Context Chat.

---

## Clarifications

### Session 2026-02-02

- Q: Should AI Context be a tab in the main content area (replacing sidebar) or remain as a sidebar Sheet? → A: Tab in main content area — AI Context becomes a tab alongside Description, Related, Graph, Activity. AIContextSidebar is deprecated. Full content width (800px) enables rich display of file trees, code snippets, and task graphs.
- Q: Where does the rich structured data (related issues with relations, documents with types, file trees, code snippets, git refs) come from? → A: AI-generated via SSE — extend existing SSE stream to return structured JSON sections. AI analyzes the issue and generates all context as structured data during streaming. No new REST endpoints needed for MVP.
- Q: Should all 6 prototype sections be implemented at once or phased? → A: Two phases. Phase 1: Header+Actions, Summary Card, Related Context, AI Tasks (checklist + prompts). Phase 2: Codebase Context (file tree, code snippets, git refs), Task Dependency Graph (canvas), Enhance Context Chat.
- Q: What format should "Copy All Context" generate for pasting into Claude Code? → A: Structured markdown with headers for each section (Summary, Related Issues, Documents, Files, Tasks, Acceptance Criteria). Clean, readable, universal. Matches prototype's generateFullContext() pattern.
- Q: How should the SSE contract handle streaming structured data for multiple sections? → A: Section-based SSE events — each section streams as its own event type (context_summary, related_issues, related_docs, ai_tasks, ai_prompts). Sections render independently as they arrive. Per-section error fallback without blocking other sections.

---

## Summary

The AI Context tab provides developers with a comprehensive, AI-generated view of all context relevant to an issue — related issues, documents, codebase files, implementation tasks, and ready-to-use prompts for Claude Code. This enables developers to quickly understand an issue's full context and start implementation with all necessary information pre-assembled.

Currently, the issue detail page has a basic `AIContextSidebar` (Sheet component) with streaming phases, a Claude Code prompt card, and simple `RelatedItemsList` components. The prototype envisions a much richer experience with:
- Structured sections for related issues (with relation types), documents (with doc types), codebase files (with file tree and code snippets), git references, task dependency graphs, interactive checklists, copyable prompts, and an embedded chat for context enhancement.

This feature enhances the existing AI Context implementation to match the full prototype design. The AIContextSidebar (Sheet component) is deprecated and replaced by a dedicated tab in the main content area, providing full 800px width for rich content display.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View AI Context Summary (Priority: P1)

A developer opens an issue and clicks the AI Context tab to get a quick overview of all relevant context. They see a summary card with the issue description and stats showing how many related items exist.

**Independent Test**: Open any issue, click AI Context tab, verify summary card shows issue title, description, and correct counts for related issues/documents/files/tasks.

**Acceptance Scenarios**:

1. **Given** a user views the AI Context tab, **When** context has been generated, **Then** they see a summary card with issue identifier, title, brief description, and stats (related issues count, documents count, files count, tasks count).

2. **Given** context has not been generated yet, **When** the user opens the AI Context tab, **Then** they see a prompt to generate context with a "Generate Context" button.

3. **Given** the user clicks "Copy All Context", **When** the copy completes, **Then** the full context is copied to clipboard as structured markdown and the button shows brief "Copied!" feedback.

4. **Given** the user clicks "Regenerate", **When** the regeneration starts, **Then** existing context is cleared and new context streams in with phase progress indicators.

---

### User Story 2 - Browse Related Context (Priority: P1)

A developer explores related issues and documents to understand dependencies and background for the current issue.

**Independent Test**: Open an issue with related items, click AI Context tab, verify related issues show relation type badges and documents show type badges.

**Acceptance Scenarios**:

1. **Given** the AI Context tab is showing results, **When** the user views the Related Context section, **Then** related issues display with relation type badge (BLOCKS/RELATES/BLOCKED BY), issue identifier, status pill, title, and summary.

2. **Given** related documents exist, **When** the user views documents subsection, **Then** each document shows type badge (NOTE/ADR/SPEC), title, and summary.

3. **Given** the user clicks the section copy button, **When** the copy completes, **Then** the Related Context section is copied as markdown.

---

### User Story 3 - Explore Codebase Context (Priority: P2)

A developer reviews the relevant code files, key code sections, and git references to understand the technical landscape before starting work.

**Independent Test**: Open an issue, generate AI context, verify file tree shows with badges and code snippets display with syntax highlighting.

**Acceptance Scenarios**:

1. **Given** codebase context has been generated, **When** the user views the file tree, **Then** files are organized in a tree structure with folder hierarchy and badges (Modified/New/Reference).

2. **Given** code snippets exist, **When** the user views them, **Then** each shows file:line reference, dark-themed code block, and a copy button.

3. **Given** git references exist, **When** the user views them, **Then** PRs, commits, and branches show with type icons and metadata.

---

### User Story 4 - Use AI Tasks & Prompts (Priority: P1)

A developer uses the AI-generated implementation plan to understand task dependencies, track progress, and copy ready-to-use prompts into Claude Code.

**Independent Test**: Open an issue, view AI Tasks section, verify task checklist is interactive and prompt blocks are copyable.

**Acceptance Scenarios**:

1. **Given** the implementation checklist is displayed, **When** the user clicks a task checkbox, **Then** the task toggles between completed and incomplete states.

2. **Given** ready-to-use prompts exist, **When** the user clicks "Copy" on a prompt block, **Then** the prompt text is copied to clipboard with brief "Copied!" feedback.

3. *[Phase 2]* **Given** AI tasks have been generated, **When** the user views the task dependency graph, **Then** a visual DAG shows task nodes with directional arrows for dependencies.

---

### User Story 5 - Enhance Context via Chat (Priority: P3)

A developer wants more context about a specific area. They use the embedded chat to ask the AI to expand on technical requirements, add code snippets, or include API contract details.

**Independent Test**: Type a message in the context chat, verify AI responds with relevant additions.

**Acceptance Scenarios**:

1. **Given** the user is viewing the AI Context tab, **When** they type in the chat input and submit, **Then** their message appears in the chat and an AI response streams in.

2. **Given** the AI responds with new context, **When** the response completes, **Then** the relevant section of the AI Context updates to include the new information.

---

## Functional Requirements *(mandatory)*

### FR-1: AI Context Tab Layout

- AI Context renders as a tab within the issue detail main content area (alongside Description, Related, Graph, Activity tabs)
- Tab displays AI sparkle icon with "AI Context" label
- Tab has distinct styling (ai-muted background, ai-border) when inactive, ai fill when active

### FR-2: Context Header & Actions

- Header shows "Full Context for AI Implementation" title with AI icon
- "Copy All Context" button generates structured markdown with `#` headers per section (Summary, Related Issues, Related Documents, Relevant Files, Implementation Tasks, Acceptance Criteria) and copies to clipboard. Format matches prototype's `generateFullContext()` pattern — clean, human-readable, optimized for pasting into Claude Code.
- "Regenerate" button clears cached context and re-generates via SSE stream
- Both buttons show loading/success feedback states

### FR-3: Context Summary Card

- Gradient card (ai-muted to lighter shade) with document icon
- Displays issue identifier and title as heading
- Brief AI-generated summary paragraph
- Stats row showing counts: Related Issues, Documents, Files, Tasks

### FR-4: Related Context Section

- Section header with link icon, title "Related Context", and section copy button
- **Related Issues subsection**: Each item shows relation badge (BLOCKS/RELATES/BLOCKED BY), issue ID (mono font), status pill, title, and summary
- **Related Documents subsection**: Each item shows type badge (NOTE/ADR/SPEC), title, and summary
- Items have hover states and are clickable for navigation

### FR-5: AI Tasks Section (Phase 1: Checklist + Prompts)

- Section header with checkmark icon, title "AI Tasks", and section copy button
- **Implementation Checklist**: Interactive task items with checkboxes, titles, estimates, and dependency info
- **Ready-to-Use Prompts**: Collapsible prompt blocks with task-specific instructions and copy buttons

---

## Phase 2 Functional Requirements

*These requirements are deferred to a follow-up branch. Documented here for completeness.*

### FR-6: Codebase Context Section [Phase 2]

- Section header with code icon, title "Codebase Context", and section copy button
- **File Tree subsection**: Hierarchical folder/file display with indentation, folder/file icons, and badges (Modified/New/Reference)
- **Code Snippets subsection**: Dark-themed code blocks with file:line reference header and individual copy buttons
- **Git References subsection**: PR/commit/branch items with type-colored icons, title, and metadata

### FR-7: Task Dependency Graph [Phase 2]

- Canvas-based directed graph showing task nodes with dependency arrows
- Integrated into AI Tasks section as visual overview above checklist

### FR-8: Enhance Context Chat [Phase 2]

- Embedded at bottom of AI Context tab with chat icon header
- AI-muted background styling (distinct from main content)
- Message history display with AI/user avatars
- Text input with send button
- AI can suggest context additions (code snippets, API details, testing strategies)

---

## Success Criteria *(mandatory)*

1. **Context completeness**: AI Context tab displays all 6 sections from the prototype with correct data
2. **Copy reliability**: "Copy All Context" produces valid markdown that can be pasted into Claude Code
3. **Interactive tasks**: Checkboxes, copy buttons, and expand/collapse all function correctly
4. **Streaming feedback**: Context generation shows real-time progress through phases
5. **Performance**: AI Context tab renders within 500ms when cached context exists
6. **Accessibility**: All interactive elements are keyboard-navigable with visible focus indicators

---

## Key Entities *(mandatory when data is involved)*

### AIContextResult (extended from current)
- **Summary**: issue_identifier, title, summary_text, stats (related_count, docs_count, files_count, tasks_count)
- **Related Issues**: Array of { relation_type, issue_id, identifier, title, summary, status, state_group }
- **Related Documents**: Array of { doc_type (NOTE/ADR/SPEC), title, summary, url? }
- **Codebase Files**: Array of { path, badge (modified/new/reference), is_folder }
- **Code Snippets**: Array of { file_path, line_range, language, code }
- **Git References**: Array of { type (pr/commit/branch), title, meta, url? }
- **Tasks**: Array of { id, title, estimate, dependencies: id[], completed }
- **Prompts**: Array of { task_id, title, content }

### AIContextPhase (existing)
- name, status (pending/in_progress/complete), content?

### SSE Event Contract (new)
- **`context_summary`**: `{ issue_identifier, title, summary_text, stats: { related_count, docs_count, files_count, tasks_count } }`
- **`related_issues`**: `{ items: [{ relation_type, issue_id, identifier, title, summary, status, state_group }] }`
- **`related_docs`**: `{ items: [{ doc_type, title, summary, url? }] }`
- **`ai_tasks`**: `{ items: [{ id, title, estimate, dependencies: id[], completed }] }`
- **`ai_prompts`**: `{ items: [{ task_id, title, content }] }`
- **`context_error`**: `{ section: string, message: string }` — Per-section error, other sections continue
- **`context_complete`**: `{}` — All sections finished streaming
- Each section renders independently as its event arrives. Partial failures show per-section error states.

---

## Scope & Boundaries

### In Scope — Phase 1 (this branch)
- Tab integration into issue detail page (replacing AIContextSidebar)
- Context Header with Copy All / Regenerate actions
- Context Summary Card with stats
- Related Context section (issues with relation types, documents with doc types)
- AI Tasks section (implementation checklist with checkboxes, ready-to-use prompts with copy)
- MobX store enhancements (AIContextStore) for structured JSON data shapes
- Copy-to-clipboard for all sections and full context markdown export
- Unit tests for new components (>80% coverage)

### In Scope — Phase 2 (follow-up branch)
- Codebase Context section (file tree, code snippets with syntax highlighting, git references)
- Task Dependency Graph (canvas-based DAG visualization)
- Enhance Context Chat (embedded ConversationPanel within AI Context tab)

### Out of Scope
- Backend API changes for AI context generation (uses existing SSE endpoint)
- Real codebase analysis (git integration for file trees/code snippets — AI-generated data)
- Persistent task completion state (checkboxes are session-local)
- Real-time context updates from external changes
- New REST endpoints for related issues/documents (AI generates all data via SSE)

---

## Assumptions

1. The existing AIContextStore SSE endpoint is extended to return structured JSON sections (related issues, documents, files, code snippets, git refs, tasks, prompts) during streaming. No new REST endpoints are created — all data is AI-generated via SSE.
2. Task dependency graph can be rendered with HTML Canvas without requiring a third-party graphing library.
3. The AI Context tab replaces the current sidebar-based approach (AIContextSidebar becomes deprecated).
4. Code snippets use static syntax highlighting (no LSP integration).
5. Git references are AI-generated suggestions, not live GitHub API queries.

---

## Dependencies

- **Existing components**: AIContextPanel, AIContextStreaming, ClaudeCodePromptCard, RelatedItemsList, ConversationPanel
- **Existing stores**: AIContextStore, ConversationStore
- **Design system**: shadcn/ui (Tabs, Card, Badge, Button, ScrollArea, Separator)
- **Canvas API**: For task dependency graph rendering

---

## Risks

1. **Data shape mismatch**: Backend SSE may not return all fields needed for the rich UI. **Mitigation**: Define clear contract, use fallback empty states for missing data.
2. **Canvas rendering complexity**: Task dependency graph requires custom canvas drawing. **Mitigation**: Keep graph simple (max 10 nodes), provide fallback list view.
3. **Bundle size**: Adding canvas graph + code display could increase JS bundle. **Mitigation**: Lazy load the AI Context tab content.
4. **Chat integration complexity**: Embedding ConversationPanel within AI Context tab requires careful state management. **Mitigation**: Reuse existing ConversationPanel component with context-specific props.
