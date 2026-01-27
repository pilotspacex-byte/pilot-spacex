# Feature Specification: Conversational Agent Architecture Migration

**Feature Branch**: `005-conversational-agent-arch`
**Created**: 2026-01-27
**Status**: Draft
**Input**: User description: "PilotSpace Conversational Agent Architecture migration from siloed agents to centralized PilotSpaceAgent with Claude Agent SDK integration"

---

## Clarifications

### Session 2026-01-27

- Q: When a user invokes a skill while another skill or subagent is already in progress, what should the system do? → A: Queue the request and show "queued" notification to user

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Natural Language AI Interaction (Priority: P1)

A user working in the note canvas types a message in the chat panel to ask the AI for help with their notes. The AI understands the context (current note, selected text) and responds conversationally, executing tasks or providing information as needed.

**Why this priority**: This is the foundational interaction model - everything else depends on having a working conversational interface between users and the AI.

**Independent Test**: Can be fully tested by opening a note, typing "help me improve this paragraph" in the chat, and receiving a contextual AI response that demonstrates the AI understands the current document.

**Acceptance Scenarios**:

1. **Given** a user has a note open in the canvas with text content, **When** they type "summarize this note" in the ChatView, **Then** the AI returns a summary of the note's content within 10 seconds.

2. **Given** a user has selected a text block in the note, **When** they type "extract issues from the selection" in the ChatView, **Then** the AI analyzes only the selected text and returns potential issues with confidence scores.

3. **Given** a user asks a follow-up question about a previous AI response, **When** they type the follow-up, **Then** the AI maintains conversation context and responds appropriately.

---

### User Story 2 - Skill Invocation via Backslash Commands (Priority: P1)

A user invokes a specific AI skill directly by typing a backslash command (e.g., `\extract-issues`) in the chat or editor. The system presents a searchable menu of available skills and executes the selected skill with the current context.

**Why this priority**: Skills are the primary way users will interact with specific AI capabilities - this is essential for the note-first workflow.

**Independent Test**: Can be fully tested by typing `\` in the chat input, selecting "extract-issues" from the menu, and seeing structured issue extraction results.

**Acceptance Scenarios**:

1. **Given** a user is in the ChatView input, **When** they type `\`, **Then** a searchable command menu appears showing all 8 available skills with descriptions.

2. **Given** the skill menu is open, **When** the user types "extract", **Then** the menu filters to show "extract-issues" skill.

3. **Given** a user selects `\extract-issues` with note content available, **When** the skill executes, **Then** issues are extracted with titles, descriptions, labels, priority, and confidence tags (RECOMMENDED/DEFAULT/ALTERNATIVE per DD-048).

4. **Given** a skill is executing, **When** results stream in, **Then** the user sees incremental output with progress indication.

---

### User Story 3 - Subagent Delegation via At-Mentions (Priority: P1)

A user invokes a specialized subagent by mentioning it with `@` (e.g., `@pr-review`) in the chat. The system spawns the subagent for complex, multi-turn tasks that require specialized tools and extended processing.

**Why this priority**: Subagents handle complex tasks (PR review, context aggregation, doc generation) that can't be done with simple skills - critical for developer workflows.

**Independent Test**: Can be fully tested by typing `@pr-review` with a PR URL, and receiving a comprehensive code review with security, quality, and performance feedback.

**Acceptance Scenarios**:

1. **Given** a user types `@` in the ChatView input, **When** the at-mention is detected, **Then** a menu shows the 3 available subagents (pr-review, ai-context, doc-generator).

2. **Given** a user mentions `@pr-review` with a GitHub PR URL, **When** the subagent is spawned, **Then** the user sees task creation and progress updates in the TaskPanel.

3. **Given** a subagent is processing, **When** it generates output, **Then** the output streams to the MessageList in real-time.

4. **Given** a subagent encounters an error, **When** the error occurs, **Then** the user sees a clear error message with suggested actions.

---

### User Story 4 - Human-in-the-Loop Approval for Critical Actions (Priority: P1)

When the AI attempts to perform a critical action (creating issues, modifying files, bulk operations), the user is presented with an approval dialog showing exactly what will happen. The user can approve, reject, or modify the action before it executes.

**Why this priority**: Human oversight of AI actions is non-negotiable per DD-003 - this protects users from unintended consequences of AI decisions.

**Independent Test**: Can be fully tested by asking the AI to create an issue, seeing the approval dialog with issue details, and verifying that approval/rejection controls execution.

**Acceptance Scenarios**:

1. **Given** the AI wants to create an issue, **When** the action is classified as critical, **Then** an ApprovalDialog appears showing issue title, description, labels, and consequences.

2. **Given** an approval request is displayed, **When** the user clicks "Approve", **Then** the action executes and confirmation appears.

3. **Given** an approval request is displayed, **When** the user clicks "Reject", **Then** the action is cancelled and the AI is informed of the rejection.

4. **Given** an approval request is displayed, **When** the user modifies the proposed content (e.g., changes issue title), **Then** the modified version is used when approved.

5. **Given** an approval request has an expiry timer (24h), **When** the timer expires, **Then** the request is automatically rejected with notification.

---

### User Story 5 - Task Progress Tracking (Priority: P2)

When the AI performs multi-step operations, users see a real-time task panel showing active tasks, their progress, dependencies, and completion status.

**Why this priority**: Transparency into AI operations builds trust and helps users understand what's happening during complex operations.

**Independent Test**: Can be fully tested by invoking a multi-step operation and verifying the TaskPanel shows tasks with correct status transitions.

**Acceptance Scenarios**:

1. **Given** a complex AI operation begins, **When** tasks are created, **Then** the TaskPanel shows task cards with subject, status, and progress indicators.

2. **Given** multiple tasks exist, **When** some complete and others are in progress, **Then** the panel shows correct counts (e.g., "2 active, 3 completed").

3. **Given** tasks have dependencies, **When** a blocking task completes, **Then** dependent tasks transition from "blocked" to "in_progress".

4. **Given** a task is selected, **When** user clicks to expand, **Then** detailed description and any output are shown.

---

### User Story 6 - Session Persistence and Resumption (Priority: P2)

Users can close and reopen conversations without losing context. The AI remembers previous exchanges, file changes discussed, and can continue where they left off.

**Why this priority**: Session continuity enables multi-session workflows and prevents users from having to repeat context.

**Independent Test**: Can be fully tested by having a conversation, closing the browser, reopening, and seeing the AI correctly reference previous context.

**Acceptance Scenarios**:

1. **Given** a user has an active conversation, **When** they navigate away and return, **Then** the conversation history is preserved and visible.

2. **Given** a saved session exists, **When** the user sends a new message, **Then** the AI resumes with full context from the previous session.

3. **Given** a session, **When** the user explicitly clears it (`/clear`), **Then** a new session starts with fresh context.

4. **Given** a session is approaching context limits, **When** automatic compaction triggers, **Then** essential context is preserved and user is notified.

---

### User Story 7 - GhostText Independent Fast Path (Priority: P2)

While typing in the editor, users see inline completion suggestions (ghost text) that appear within 2 seconds. This operates independently of the main conversational agent for responsiveness.

**Why this priority**: GhostText is the most frequent AI interaction and must remain fast (<2s) regardless of other AI operations.

**Independent Test**: Can be fully tested by typing in the editor and verifying ghost text appears within 2 seconds without impacting or being impacted by ChatView operations.

**Acceptance Scenarios**:

1. **Given** a user is typing in the editor, **When** they pause, **Then** ghost text suggestions appear within 2 seconds.

2. **Given** the main ChatView is processing a complex request, **When** the user types in the editor, **Then** ghost text still appears within 2 seconds (independent path).

3. **Given** ghost text is displayed, **When** the user presses Tab, **Then** the suggestion is accepted and inserted.

4. **Given** ghost text is displayed, **When** the user continues typing, **Then** the ghost text updates or dismisses appropriately.

---

### User Story 8 - Unified Context Awareness (Priority: P2)

The AI automatically understands the user's current context (which note is open, what's selected, which project/issue is active) without requiring explicit specification.

**Why this priority**: Context awareness enables natural interactions where users don't have to constantly tell the AI what they're working on.

**Independent Test**: Can be fully tested by opening different notes/issues and verifying the AI's responses reflect the correct current context.

**Acceptance Scenarios**:

1. **Given** a user has Note A open, **When** they ask "summarize this", **Then** the AI summarizes Note A's content.

2. **Given** a user has text selected in the editor, **When** they ask "improve this", **Then** the AI operates on the selected text only.

3. **Given** a user is viewing Issue #123, **When** they invoke `@ai-context`, **Then** the subagent aggregates context specific to Issue #123.

4. **Given** context changes (user opens different note), **When** the user asks a new question, **Then** the AI uses the new context.

---

### Edge Cases

- **Concurrent skill invocation**: When a user invokes a skill while another skill or subagent is in progress, the system queues the request and shows a "queued" notification to the user. Queued requests execute in FIFO order after the current operation completes.
- **API rate limits during streaming**: System pauses stream, displays rate limit notification with retry countdown, and automatically resumes when limit resets.
- **Network disconnection during approval flow**: Pending approval is preserved server-side; user sees reconnection prompt and can resume approval decision after reconnecting.
- **Concurrent sessions in multiple tabs**: Each tab maintains independent session; no cross-tab synchronization in MVP (per DD-005 no real-time collaboration).
- **Subagent exceeds turn limit**: Subagent gracefully terminates with partial results and explanation; user can restart or continue manually.
- **Failed tool execution mid-task**: Task marked as failed with error details; user offered retry or skip options; dependent tasks blocked until resolved.
- **Invalid API key during session**: Stream terminates with authentication error; user redirected to settings to update API key; session preserved for resumption after key update.

---

## Requirements *(mandatory)*

### Functional Requirements

**Core Agent System**

- **FR-001**: System MUST provide a unified PilotSpaceAgent that orchestrates all conversational AI interactions
- **FR-002**: System MUST route user inputs appropriately: `\skill` commands to SkillExecutor, `@agent` mentions to SubagentSpawner, natural language to intent parser
- **FR-003**: System MUST support 8 skills: extract-issues, enhance-issue, recommend-assignee, find-duplicates, decompose-tasks, generate-diagram, improve-writing, summarize
- **FR-004**: System MUST support 3 subagents: PRReviewSubagent, AIContextSubagent, DocGeneratorSubagent
- **FR-005**: GhostTextAgent MUST operate independently with less than 2 second latency target, bypassing the main conversational agent
- **FR-005a**: System MUST queue concurrent skill/subagent requests and display "queued" notification; queued requests execute in FIFO order after current operation completes

**Skill System**

- **FR-006**: Skills MUST be defined as SKILL.md files in `.claude/skills/` directory following SDK format
- **FR-007**: System MUST load skill metadata (name, description) at startup for the command menu
- **FR-008**: System MUST load skill instructions only when the skill is invoked (progressive loading)
- **FR-009**: Skills MUST return structured output with confidence tags per DD-048 (RECOMMENDED/DEFAULT/CURRENT/ALTERNATIVE)

**Subagent System**

- **FR-010**: Subagents MUST be spawned via the SDK's Task tool with defined AgentDefinition
- **FR-011**: Subagents MUST have restricted tool access appropriate to their purpose
- **FR-012**: Subagent progress MUST be tracked and reported to the TaskPanel
- **FR-013**: Subagents MUST stream output incrementally to the user

**Human-in-the-Loop**

- **FR-014**: Critical actions (issue creation, file modification, bulk operations) MUST require human approval per DD-003
- **FR-015**: Approval requests MUST include action description, consequences, and 24h expiry timer
- **FR-016**: System MUST support approve, reject, and modify responses to approval requests
- **FR-017**: System MUST implement `canUseTool` callback for SDK permission handling

**Session Management**

- **FR-018**: System MUST capture and persist SDK session IDs for resumption
- **FR-019**: System MUST support session resumption via the SDK's `resume` parameter
- **FR-020**: System MUST support session forking for exploring alternatives
- **FR-021**: System MUST support automatic context compaction when approaching limits

**Frontend Integration**

- **FR-022**: System MUST provide unified PilotSpaceStore replacing 9 siloed stores
- **FR-023**: ChatView MUST display messages, streaming content, tool calls, tasks, and approval requests
- **FR-024**: ChatInput MUST support `\skill` and `@agent` trigger detection with searchable menus
- **FR-025**: System MUST use SSE streaming for real-time updates from backend to frontend

**API**

- **FR-026**: System MUST provide unified `/api/v1/ai/chat` endpoint for all conversational interactions
- **FR-027**: Endpoint MUST accept message content, context (note_id, issue_id, project_id, selected_text), and optional session_id
- **FR-028**: Endpoint MUST return SSE stream with defined event types (message_start, text_delta, tool_use, approval_request, task_progress, message_stop)

### Key Entities

- **Message**: A single exchange in the conversation (user or assistant), with content, role, timestamp, and optional tool calls
- **Task**: A tracked unit of work with subject, description, status (pending/in_progress/completed), dependencies, and owner
- **ApprovalRequest**: A pending action requiring human confirmation, with action type, description, consequences, affected entities, urgency, and expiry
- **Skill**: A lightweight AI capability defined by SKILL.md with name, description, and execution workflow
- **Subagent**: A specialized agent (PRReview, AIContext, DocGenerator) with defined tools, model, and prompt
- **Session**: A persistent conversation context with session_id enabling resumption and forking
- **Context**: The current working state (active note, selected text, issue, project) passed to the AI

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Performance**

- **SC-001**: GhostText suggestions appear within 2 seconds for 95% of requests
- **SC-002**: Skill execution (simple skills like summarize, improve-writing) completes within 10 seconds for 95% of requests
- **SC-003**: First streaming token from conversational responses appears within 3 seconds for 95% of requests
- **SC-004**: System supports 100 concurrent users without performance degradation

**User Experience**

- **SC-005**: Users can complete skill invocation (type `\`, select skill, see results) in under 30 seconds
- **SC-006**: Approval dialog response time (user decision to action execution) is under 1 second
- **SC-007**: Session resumption restores full context with no visible delay to user
- **SC-008**: 90% of users successfully invoke a skill on first attempt (no training required)

**Reliability**

- **SC-009**: Conversation context is preserved across browser refresh with 100% accuracy
- **SC-010**: Network disconnection during streaming allows reconnection and continuation without data loss
- **SC-011**: Failed tool executions provide clear error messages and recovery options
- **SC-012**: System gracefully handles API rate limits with user notification and retry guidance

**Migration Completeness**

- **SC-013**: All 13 current backend agents are migrated to the new architecture (1 orchestrator + 3 subagents + 8 skills + 1 independent GhostText)
- **SC-014**: All 9 frontend stores are consolidated into unified PilotSpaceStore (8 migrated, GhostTextStore remains independent)
- **SC-015**: E2E tests pass for all 8 user stories defined in this specification
- **SC-016**: Zero regression in existing AI features during and after migration

---

## Assumptions

1. **Claude Agent SDK Availability**: The Claude Agent SDK (v1.0+) is available and supports all documented features (skills, tools, hooks, sessions, sandbox)
2. **BYOK Model**: Users provide their own Anthropic API keys (required) and optionally OpenAI (for embeddings) and Google (for Gemini)
3. **Supabase Infrastructure**: Supabase platform provides Auth, Storage, Queues, and Database with RLS enforcement
4. **SSE Support**: The target deployment environment supports Server-Sent Events for streaming responses
5. **Sandbox Provisioning**: Infrastructure supports per-user/workspace sandbox directories for isolated skill/config storage
6. **Existing UI Components**: shadcn/ui component library and existing ChatView components (created in Phase 4.2) are available for integration
7. **MobX State Management**: Frontend uses MobX for state management (not Zustand) per project constitution

---

## Dependencies

1. **docs/architect/pilotspace-agent-architecture.md** (v1.5.0) - Target architecture specification
2. **docs/architect/agent-architecture-remediation-plan.md** (v1.3.0) - 131-task migration plan across 6 phases
3. **DD-003** - Critical-only approval model for AI actions
4. **DD-011** - Provider routing rules (Claude for code, OpenAI for embeddings)
5. **DD-048** - AI confidence tagging system (RECOMMENDED/DEFAULT/CURRENT/ALTERNATIVE)
6. **Claude Agent SDK Documentation** - SDK integration patterns and API contracts
7. **frontend/src/features/ai/ChatView/** - Existing ChatView components (25 files from Phase 4.2)

---

## Out of Scope

1. Real-time collaboration (multiple users editing same note simultaneously) - per DD-005
2. Local LLM support - Anthropic required, no offline mode
3. Custom skill creation UI - skills are managed via filesystem only in MVP
4. Multi-workspace conversations - sessions are scoped to single workspace
5. Voice input/output - text-only interface for MVP
6. Mobile native apps - web-responsive only
7. Third-party integrations beyond GitHub + Slack - per DD-004

---

## References

- [Remediation Plan v1.3.0](../../docs/architect/agent-architecture-remediation-plan.md)
- [Target Architecture v1.5.0](../../docs/architect/pilotspace-agent-architecture.md)
- [Design Decisions](../../docs/DESIGN_DECISIONS.md) - DD-003, DD-011, DD-048
- [Feature Story Mapping](../../docs/architect/feature-story-mapping.md)
