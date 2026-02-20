# Feature Specification: Daily Routine — Contextual AI Chat Experience

**Feature Branch**: `019-daily-routine`
**Created**: 2026-02-20
**Status**: Draft
**Input**: Transform the generic ChatView into a contextually intelligent AI assistant that adapts to where the user is (homepage vs note editor) and what they need right now.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — AI-Powered Daily Briefing (Priority: P1)

A team member opens Pilot Space at the start of their workday. Instead of a generic greeting, the homepage presents a personalized briefing: stale issues needing attention, blocked dependencies, cycle risk alerts, and overdue items. The AI chat sidebar shows smart prompts tailored to their actual workspace state — not hardcoded suggestions.

**Why this priority**: The homepage is the first thing every user sees. A personalized daily briefing immediately demonstrates AI value and drives engagement. The backend digest system is already fully built — this story wires existing infrastructure to the frontend, delivering high ROI for low effort.

**Independent Test**: Can be fully tested by logging into a workspace with active issues, notes, and cycles. The homepage displays categorized AI insights and contextual prompts. Users can click a suggestion to start an AI conversation with pre-loaded context.

**Acceptance Scenarios**:

1. **Given** a workspace with 5 stale issues (no updates for 7+ days), **When** the user opens the homepage, **Then** an "Attention Needed" section displays the stale issues with last-updated timestamps and a "Review these" action prompt.
2. **Given** a workspace with an active cycle ending in 2 days and 4 unfinished issues, **When** the user opens the homepage, **Then** a "Cycle Risk" alert shows the deadline, remaining items, and a prompt like "Sprint ends Friday — prioritize these 4 items?"
3. **Given** a workspace with notes containing unlinked actionable content, **When** the user opens the homepage, **Then** an "Unlinked Notes" insight suggests extracting issues from specific notes.
4. **Given** the user clicks a contextual prompt (e.g., "Review 3 stale issues"), **When** the ChatView receives the message, **Then** the AI has the digest data pre-loaded as context and responds immediately without additional data-fetching delays.
5. **Given** a workspace with no pending issues and no recent activity, **When** the user opens the homepage, **Then** only relevant insight categories appear (empty categories are hidden, not shown as "No items").
6. **Given** the digest data was generated 2 hours ago, **When** the user opens the homepage, **Then** the system shows the cached digest with a "Last updated 2h ago" indicator and refreshes in the background.

---

### User Story 2 — Daily Standup Generator (Priority: P2)

A developer needs to prepare for their daily standup meeting. They click a "Generate Standup" button on the homepage. The AI aggregates yesterday's completed work, today's in-progress items, and any blockers into a formatted standup update they can copy to Slack or Teams.

**Why this priority**: Standup preparation is a daily friction point for every developer. Automating it saves 5-10 minutes per person per day and increases standup quality by not missing completed items.

**Independent Test**: Can be tested by having a workspace with issues that transitioned states in the last 48 hours. Clicking "Generate Standup" produces a formatted summary. The output can be copied to clipboard.

**Acceptance Scenarios**:

1. **Given** 3 issues moved to "Done" yesterday and 2 issues currently "In Progress", **When** the user clicks "Generate Standup", **Then** the AI produces a formatted update with "Yesterday: [3 items]", "Today: [2 items]", "Blockers: [none]".
2. **Given** 1 issue is in "Blocked" state with a dependency, **When** the standup is generated, **Then** the "Blockers" section includes the blocked issue with its dependency explanation.
3. **Given** the standup output is displayed, **When** the user clicks "Copy to clipboard", **Then** the formatted text is copied and a confirmation toast appears.
4. **Given** the user has no activity in the last 48 hours, **When** they click "Generate Standup", **Then** the AI responds with "No recent activity found" and suggests reviewing backlog items.

---

### User Story 3 — Note Health Indicator & Proactive Suggestions (Priority: P2)

A user opens a note they've been working on. The editor toolbar shows health badges: "3 extractable issues", "2 sections need clarity". The ChatView empty state shows note-specific suggestions instead of generic prompts. When they start typing, ghost text completions are aware of the note's block type and context.

**Why this priority**: The note editor is where users spend the most time. Proactive intelligence turns passive editing into guided workflow — surfacing next actions reduces cognitive load and drives feature adoption (extraction, improvement, linking).

**Independent Test**: Can be tested by opening a note with mixed content (requirements, bullet lists, ambiguous text). The toolbar shows health badges, ChatView shows relevant suggestions, and ghost text adapts to block type.

**Acceptance Scenarios**:

1. **Given** a note with 3 paragraphs containing actionable language ("implement X", "fix Y", "add Z"), **When** the user opens the note, **Then** a health badge shows "3 extractable issues" in the editor toolbar.
2. **Given** a note with 2 ambiguous sections (detected by annotation analysis), **When** the user opens the note, **Then** a health badge shows "2 need clarity" and clicking it opens the ChatView with a pre-filled "Improve clarity in these sections" message.
3. **Given** a note linked to issues PS-42 and PS-55, **When** the user opens the note, **Then** a health badge shows "Linked: PS-42, PS-55" with quick navigation to those issues.
4. **Given** the ChatView is empty (no conversation history for this note), **When** the user views the ChatView, **Then** suggested prompts are specific to the note content (e.g., "Extract 3 actionable items as issues", "Improve writing in section 2") instead of generic prompts.
5. **Given** the user is typing in a heading block, **When** ghost text triggers, **Then** the completion suggests structural/outline content rather than generic sentence continuation.
6. **Given** the user is typing in a code block, **When** ghost text triggers, **Then** the completion uses code-aware prompting (syntax-appropriate suggestions).

---

### User Story 4 — Annotation-to-Action Pipeline (Priority: P3)

While editing a note, the margin annotation system highlights blocks with detected issues, unclear text, or actionable items. Each annotation card has an action button that directly triggers the relevant AI operation — no need to manually type commands in the chat.

**Why this priority**: Annotations currently show information but require users to manually invoke skills via chat. Adding action buttons closes the loop from detection to action, reducing the steps from 3 (see annotation → open chat → type command) to 1 (click action).

**Independent Test**: Can be tested by editing a note until annotations appear. Clicking the action button on an `issue_candidate` annotation triggers the extract-issues flow for that specific block.

**Acceptance Scenarios**:

1. **Given** an annotation of type `issue_candidate` appears on a block, **When** the user clicks "Extract Issue" on the annotation card, **Then** the extraction flow starts for that specific block with the content pre-loaded.
2. **Given** an annotation of type `clarification` appears, **When** the user clicks "Ask AI to Clarify", **Then** the ChatView opens with a pre-filled message asking the AI to clarify the flagged section.
3. **Given** an annotation of type `action_item` appears, **When** the user clicks "Create Task", **Then** the issue creation flow starts with the action item text pre-filled as the issue title.
4. **Given** annotations are loading for a block, **When** the user hovers over the margin indicator, **Then** a loading state is shown (not an empty card).

---

### User Story 5 — Contextual Chat with Homepage Context Injection (Priority: P3)

When the user asks the AI a question on the homepage (e.g., "What should I focus on today?"), the ChatView already has the digest data, active issues, recent notes, and project progress pre-loaded. The AI responds instantly with workspace-aware answers without needing to make separate data-fetching calls.

**Why this priority**: Without context injection, every homepage AI query requires 3-5 tool calls to gather workspace state, adding 5-10 seconds of latency. Pre-loading context makes the AI feel instant and knowledgeable.

**Independent Test**: Can be tested by asking "What should I focus on today?" on the homepage and measuring response time. The AI should reference specific issues and notes without visible "searching..." tool calls.

**Acceptance Scenarios**:

1. **Given** the homepage has loaded digest data showing 3 stale issues and 2 cycle risks, **When** the user asks "What should I focus on today?", **Then** the AI references the specific stale issues and cycle risks in its response without making additional tool calls.
2. **Given** the user navigates from the homepage to a note editor, **When** the ChatView loads in the note context, **Then** the homepage context is cleared and replaced with note-specific context.
3. **Given** the homepage digest data is stale (>1 hour old), **When** the user starts a chat, **Then** the context includes the cached data with a freshness indicator, and a background refresh is triggered.

---

### Edge Cases

- What happens when the digest background job hasn't run yet (new workspace)? Display an onboarding state: "AI is analyzing your workspace. Check back in a few minutes."
- What happens when multiple users access the homepage simultaneously? Each user sees their own digest (digest is per-workspace, filtered by user role permissions).
- What happens when a note has 0 blocks (empty note)? Health indicator shows nothing; ChatView suggests "Start writing to get AI assistance."
- What happens when the annotation auto-trigger fires but the note hasn't been saved yet? Use the local editor content for analysis, not the server-persisted version.
- What happens when the user dismisses a digest insight? The dismissal persists for that digest generation cycle; the insight reappears if the next digest still flags it.
- What happens when ghost text is disabled in user settings? Block-aware routing still respects the global ghost text toggle — no ghost text appears regardless of block type.

## Requirements *(mandatory)*

### Functional Requirements

**Homepage — Daily Briefing**

- **FR-001**: System MUST display categorized AI digest insights on the homepage, grouped by: stale issues, unlinked notes, cycle risks, blocked dependencies, overdue items, and unassigned high-priority items.
- **FR-002**: System MUST generate contextual suggested prompts based on current workspace state (digest data + issue counts + cycle status). Generic prompts MUST NOT appear when contextual alternatives are available.
- **FR-003**: System MUST show a freshness indicator for digest data (e.g., "Updated 2h ago") and trigger background refresh when data is older than a configurable threshold (default: 1 hour).
- **FR-004**: System MUST hide empty insight categories rather than showing "No items" placeholders.
- **FR-005**: Users MUST be able to dismiss individual digest insights. Dismissals persist until the next digest generation cycle.

**Homepage — Standup Generator**

- **FR-006**: System MUST provide a "Generate Standup" action on the homepage that produces a formatted daily standup summary.
- **FR-007**: The standup MUST include three sections: "Yesterday" (issues completed in last 24h), "Today" (issues currently in-progress), and "Blockers" (blocked issues with dependency context).
- **FR-008**: Users MUST be able to copy the standup output to clipboard with a single click.
- **FR-009**: The standup MUST adapt its time window to the user's last active session (e.g., Monday standups cover Friday-Monday).

**Note Editor — Health Indicator**

- **FR-010**: System MUST display health badges in the note editor toolbar showing: count of extractable issues, count of sections needing clarity, and linked issue identifiers.
- **FR-011**: Health badges MUST be clickable — clicking opens the ChatView with a pre-filled message for the relevant action (e.g., clicking "3 extractable" sends "Extract issues from this note").
- **FR-012**: Health analysis MUST run on note load and refresh after significant edits (debounced, not on every keystroke).

**Note Editor — Contextual Chat**

- **FR-013**: ChatView empty state MUST show note-specific suggested prompts derived from the health analysis (not generic hardcoded prompts).
- **FR-014**: System MUST inject the current note's health data and linked entities into the ChatView context so the AI can reference them without additional tool calls.

**Note Editor — Block-Aware Ghost Text**

- **FR-015**: Ghost text completions MUST adapt to block type: heading blocks receive outline/structure suggestions, bullet lists receive pattern-continuation suggestions, code blocks receive syntax-aware completions.
- **FR-016**: Ghost text MUST include note-level context (title, linked issues, project) in the completion prompt — not just the immediate cursor position.

**Note Editor — Annotation Actions**

- **FR-017**: Annotation cards of type `issue_candidate` MUST include an "Extract Issue" action button that triggers the extraction flow for the annotated block.
- **FR-018**: Annotation cards of type `clarification` MUST include an "Ask AI" action button that opens ChatView with a pre-filled clarification request.
- **FR-019**: Annotation cards of type `action_item` MUST include a "Create Task" action button that opens the issue creation flow with the action item text pre-filled.
- **FR-020**: The annotation auto-trigger MUST correctly identify the current note (fix: the note identity must be passed through the extension configuration, not hardcoded as empty).

**Cross-Cutting**

- **FR-021**: Context switching between homepage and note editor MUST cleanly transition the ChatView context (homepage context cleared when entering a note, note context cleared when returning to homepage).
- **FR-022**: All AI-generated suggestions (digest insights, health badges, contextual prompts) MUST respect workspace role permissions — users only see data they have access to.

### Key Entities

- **WorkspaceDigest**: Per-workspace AI analysis containing categorized suggestions (stale issues, unlinked notes, cycle risks, blocked dependencies, overdue items). Generated by background job, stored as structured data. Has freshness timestamp and generation cycle identifier.
- **NoteHealthAnalysis**: Per-note analysis result containing: extractable issue count, clarity issue count, linked entity list. Computed on note load and cached per-session. Drives health badges and contextual prompts.
- **DigestInsightDismissal**: Tracks which digest insights a user has dismissed, scoped to the digest generation cycle. Resets when a new digest is generated.
- **StandupSummary**: Ephemeral output from the standup generator skill. Contains three sections (yesterday/today/blockers) with issue references. Not persisted — generated on demand.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 80% of daily active users interact with at least one AI digest insight within their first 2 minutes on the homepage (baseline: 0% — currently no digest insights shown).
- **SC-002**: Users asking "What should I focus on today?" on the homepage receive a workspace-aware response within 3 seconds (no visible tool-call delays).
- **SC-003**: Daily standup generation completes in under 5 seconds and covers 100% of issues that transitioned state in the relevant time window.
- **SC-004**: Note health badges appear within 2 seconds of opening a note, correctly identifying at least 80% of extractable actionable items (measured against manual review).
- **SC-005**: Annotation-to-action click-through reduces the steps to invoke an AI skill from 3 (view annotation → open chat → type command) to 1 (click action button).
- **SC-006**: Ghost text acceptance rate improves by 20% when using block-aware prompting compared to generic positional completion (A/B measurable).
- **SC-007**: Contextual suggested prompts on the homepage have a 3x higher click-through rate than the current hardcoded prompts (A/B measurable).

## Assumptions

- The existing `DigestJobHandler` backend generates correct and complete digest data. This spec does not require changes to the digest generation logic — only frontend consumption and API endpoint creation.
- Ghost text latency budget (2.5s total) is sufficient to include block-type routing and note-level context in the prompt without degrading user experience.
- The note health analysis can be computed client-side from existing annotation data and linked entity queries, without requiring a new dedicated backend endpoint (though a lightweight endpoint may optimize performance).
- The standup generator time window logic ("yesterday" means last workday, accounting for weekends) is handled by the AI skill prompt, not by complex date arithmetic in the backend.
- Workspace digest data is shared across all workspace members (not per-user), with role-based filtering applied at display time.
