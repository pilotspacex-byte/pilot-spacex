# Tasks: Conversational Agent Architecture Migration

**Source**: `/specs/005-conversational-agent-arch/`
**Required**: plan.md ✅, spec.md ✅
**Optional**: research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

---

## Phase 1: Setup

Project initialization and SDK integration layer.

- [ ] T001 Create SDK configuration module at `backend/src/pilot_space/ai/sdk/__init__.py`
- [ ] T002 [P] Create `ClaudeAgentOptions` factory in `backend/src/pilot_space/ai/sdk/config.py`
- [ ] T003 [P] Create session handler in `backend/src/pilot_space/ai/sdk/session_handler.py`
- [ ] T004 [P] Create permission handler with `canUseTool` callback in `backend/src/pilot_space/ai/sdk/permission_handler.py`
- [ ] T005 Create `PreToolUse` hook integration in `backend/src/pilot_space/ai/sdk/hooks.py`
- [ ] T006 Update dependency injection in `backend/src/pilot_space/dependencies.py` for SDK configuration

---

## Phase 2: Foundational

Core infrastructure required before user story work.

### Database Models

- [ ] T007 Create Session model in `backend/src/pilot_space/infrastructure/database/models/ai_session.py`
- [ ] T008 [P] Create Message model in `backend/src/pilot_space/infrastructure/database/models/ai_message.py`
- [ ] T009 [P] Create ToolCall model in `backend/src/pilot_space/infrastructure/database/models/ai_tool_call.py`
- [ ] T010 [P] Create Task model in `backend/src/pilot_space/infrastructure/database/models/ai_task.py`
- [ ] T011 [P] Create ApprovalRequest model in `backend/src/pilot_space/infrastructure/database/models/ai_approval_request.py`
- [ ] T012 Create Alembic migration for AI tables in `backend/alembic/versions/005_001_create_ai_tables.py`

### SDK Memory System

- [ ] T013 Create `.claude/CLAUDE.md` with project instructions at `backend/.claude/CLAUDE.md`
- [ ] T014 [P] Create `.claude/rules/issues.md` with issue patterns at `backend/.claude/rules/issues.md`
- [ ] T015 [P] Create `.claude/rules/notes.md` with note patterns at `backend/.claude/rules/notes.md`
- [ ] T016 [P] Create `.claude/rules/ai-confidence.md` with DD-048 rules at `backend/.claude/rules/ai-confidence.md`

### Skills Migration (8 skills)

- [ ] T017 Create extract-issues skill at `backend/.claude/skills/extract-issues/SKILL.md`
- [ ] T018 [P] Create enhance-issue skill at `backend/.claude/skills/enhance-issue/SKILL.md`
- [ ] T019 [P] Create recommend-assignee skill at `backend/.claude/skills/recommend-assignee/SKILL.md`
- [ ] T020 [P] Create find-duplicates skill at `backend/.claude/skills/find-duplicates/SKILL.md`
- [ ] T021 [P] Create decompose-tasks skill at `backend/.claude/skills/decompose-tasks/SKILL.md`
- [ ] T022 [P] Create generate-diagram skill at `backend/.claude/skills/generate-diagram/SKILL.md`
- [ ] T023 [P] Create improve-writing skill at `backend/.claude/skills/improve-writing/SKILL.md`
- [ ] T024 [P] Create summarize skill at `backend/.claude/skills/summarize/SKILL.md`
- [ ] T025 Create skill registry with filesystem discovery in `backend/src/pilot_space/ai/sdk/skill_registry.py`
- [ ] T026 Create skill validation utility in `backend/src/pilot_space/ai/sdk/skill_validator.py`

### Backend Agent Architecture

- [ ] T027 Create PilotSpaceAgent class in `backend/src/pilot_space/ai/agents/pilotspace_agent.py`
- [ ] T028 Implement intent parser (`_parse_intent`) in PilotSpaceAgent for `\skill`, `@agent`, natural language
- [ ] T029 Implement skill executor (`_execute_skill`) in PilotSpaceAgent
- [ ] T030 Implement subagent spawner (`_spawn_subagent`) in PilotSpaceAgent
- [ ] T031 Implement task planner (`_plan_tasks`) in PilotSpaceAgent

### Subagents

- [ ] T032 Create subagents directory at `backend/src/pilot_space/ai/agents/subagents/__init__.py`
- [ ] T033 [P] Refactor PRReviewAgent as subagent in `backend/src/pilot_space/ai/agents/subagents/pr_review_subagent.py`
- [ ] T034 [P] Refactor AIContextAgent as subagent in `backend/src/pilot_space/ai/agents/subagents/ai_context_subagent.py`
- [ ] T035 [P] Refactor DocGeneratorAgent as subagent in `backend/src/pilot_space/ai/agents/subagents/doc_generator_subagent.py`

### API Endpoint

- [ ] T036 Create unified `/api/v1/ai/chat` endpoint in `backend/src/pilot_space/api/v1/routers/ai_chat.py`
- [ ] T037 Add context extraction middleware in `backend/src/pilot_space/api/v1/middleware/ai_context.py`
- [ ] T038 Implement SSE event transformation in `backend/src/pilot_space/ai/sdk/sse_transformer.py`

### Frontend Store

- [ ] T039 Create TypeScript types in `frontend/src/stores/ai/types/conversation.ts`
- [ ] T040 [P] Create TypeScript types in `frontend/src/stores/ai/types/skills.ts`
- [ ] T041 [P] Create TypeScript types in `frontend/src/stores/ai/types/events.ts`
- [ ] T042 Create PilotSpaceStore class in `frontend/src/stores/ai/PilotSpaceStore.ts`
- [ ] T043 Implement conversation state (messages, streaming, sessionId) in PilotSpaceStore
- [ ] T044 Implement task state (tasks Map, activeTasks, completedTasks) in PilotSpaceStore
- [ ] T045 Implement approval state (pendingApprovals, approve/reject) in PilotSpaceStore
- [ ] T046 Implement context state (noteContext, issueContext) in PilotSpaceStore
- [ ] T047 Implement sendMessage action with SSE client in PilotSpaceStore
- [ ] T048 Implement SSE event handlers for 8 event types in PilotSpaceStore
- [ ] T049 Update AIStore to include PilotSpaceStore in `frontend/src/stores/ai/AIStore.ts`

**Checkpoint**: Foundation complete - user stories can start.

---

## Phase 3: User Story 1 - Natural Language AI Interaction (P1) 🎯 MVP

**Goal**: Users can type natural language messages in ChatView and receive contextual AI responses
**Verify**: Open a note, type "summarize this note" in chat, receive AI summary within 10 seconds

### Implementation

- [ ] T050 [US1] Wire ChatInput to PilotSpaceStore.sendMessage in `frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx`
- [ ] T051 [US1] Wire MessageList to store.messages in `frontend/src/features/ai/ChatView/MessageList/MessageList.tsx`
- [ ] T052 [P] [US1] Wire StreamingContent to store.streamContent in `frontend/src/features/ai/ChatView/MessageList/StreamingContent.tsx`
- [ ] T053 [US1] Connect selection context to PilotSpaceStore in `frontend/src/features/notes/editor/hooks/useSelectionContext.ts`
- [ ] T054 [US1] Add ChatView sidebar to NoteCanvas in `frontend/src/components/editor/NoteCanvas.tsx`
- [ ] T055 [US1] Implement conversation context passing in chat endpoint (note_id, selected_text)

**Checkpoint**: US1 functional - user can chat with AI about their notes.

---

## Phase 4: User Story 2 - Skill Invocation via Backslash Commands (P1)

**Goal**: Users can type `\` to see skill menu and execute skills with `\skill-name`
**Verify**: Type `\extract-issues` in ChatView, see structured issue extraction results

### Implementation

- [ ] T056 [US2] Wire SkillMenu to skill definitions in `frontend/src/features/ai/ChatView/ChatInput/SkillMenu.tsx`
- [ ] T057 [US2] Implement `\skill` detection in ChatInput in `frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx`
- [ ] T058 [US2] Implement skill invocation flow (`\skill` → sendMessage with skill context)
- [ ] T059 [US2] Wire ToolCallList to store.toolCalls in `frontend/src/features/ai/ChatView/MessageList/ToolCallList.tsx`
- [ ] T060 [US2] Implement skill execution feedback (progress, streaming output) in MessageList

**Checkpoint**: US2 functional - user can invoke skills via backslash commands.

---

## Phase 5: User Story 3 - Subagent Delegation via At-Mentions (P1)

**Goal**: Users can type `@agent-name` to spawn specialized subagents for complex tasks
**Verify**: Type `@pr-review https://github.com/org/repo/pull/123`, see comprehensive review output

### Implementation

- [ ] T061 [US3] Wire AgentMenu to agent definitions in `frontend/src/features/ai/ChatView/ChatInput/AgentMenu.tsx`
- [ ] T062 [US3] Implement `@agent` detection in ChatInput in `frontend/src/features/ai/ChatView/ChatInput/ChatInput.tsx`
- [ ] T063 [US3] Implement agent mention flow (`@agent` → sendMessage with agent context)
- [ ] T064 [US3] Wire TaskPanel to store.tasks in `frontend/src/features/ai/ChatView/TaskPanel/TaskPanel.tsx`
- [ ] T065 [US3] Implement task progress display with status transitions

**Checkpoint**: US3 functional - user can invoke subagents via at-mentions.

---

## Phase 6: User Story 4 - Human-in-the-Loop Approval (P1)

**Goal**: Critical AI actions require human approval before execution
**Verify**: Ask AI to create an issue, see approval dialog, approve/reject controls execution

### Implementation

- [ ] T066 [US4] Wire ApprovalOverlay to store.pendingApprovals in `frontend/src/features/ai/ChatView/ApprovalOverlay/ApprovalOverlay.tsx`
- [ ] T067 [US4] Wire ApprovalDialog approve/reject actions in `frontend/src/features/ai/ChatView/ApprovalOverlay/ApprovalDialog.tsx`
- [ ] T068 [US4] Implement approval request API in `frontend/src/services/api/ai.ts`
- [ ] T069 [US4] Implement modify-before-approve flow in ApprovalDialog
- [ ] T070 [US4] Implement 24h expiry timer UI in ApprovalOverlay

**Checkpoint**: US4 functional - critical actions require human approval.

---

## Phase 7: User Story 5 - Task Progress Tracking (P2)

**Goal**: Users see real-time task panel with progress during AI operations
**Verify**: Invoke multi-step operation, see tasks with correct status transitions

### Implementation

- [ ] T071 [US5] Implement task cards with status badges in `frontend/src/features/ai/ChatView/TaskPanel/TaskItem.tsx`
- [ ] T072 [US5] Implement task counts (active/completed) in `frontend/src/features/ai/ChatView/TaskPanel/TaskSummary.tsx`
- [ ] T073 [US5] Implement task dependency visualization (blocked → in_progress transition)
- [ ] T074 [US5] Implement task expand/collapse with detailed output in TaskItem

**Checkpoint**: US5 functional - users see task progress in real-time.

---

## Phase 8: User Story 6 - Session Persistence and Resumption (P2)

**Goal**: Users can close/reopen conversations without losing context
**Verify**: Have conversation, close browser, reopen, AI remembers previous context

### Implementation

- [ ] T075 [US6] Implement session persistence API in `backend/src/pilot_space/api/v1/routers/ai_chat.py`
- [ ] T076 [US6] Implement session resume via SDK `resume` parameter in session_handler
- [ ] T077 [US6] Implement `/clear` command for new session in PilotSpaceStore
- [ ] T078 [US6] Implement automatic context compaction when approaching limits
- [ ] T079 [US6] Implement session restoration on page load in PilotSpaceStore

**Checkpoint**: US6 functional - conversations persist across browser sessions.

---

## Phase 9: User Story 7 - GhostText Independent Fast Path (P2)

**Goal**: GhostText maintains <2s latency independent of ChatView operations
**Verify**: Type in editor during complex ChatView operation, ghost text still appears <2s

### Implementation

- [ ] T080 [US7] Verify GhostText endpoint remains on separate path (not affected by migration)
- [ ] T081 [US7] Verify GhostTextStore remains independent from PilotSpaceStore
- [ ] T082 [US7] Add performance guard to ensure <2s p95 latency
- [ ] T083 [US7] Add AbortController for in-flight request cancellation

**Checkpoint**: US7 functional - GhostText operates independently at <2s latency.

---

## Phase 10: User Story 8 - Unified Context Awareness (P2)

**Goal**: AI automatically understands current context without explicit specification
**Verify**: Open different notes/issues, AI responses reflect correct current context

### Implementation

- [ ] T084 [US8] Implement automatic context detection from NoteCanvas in `frontend/src/features/notes/editor/hooks/useNoteContext.ts`
- [ ] T085 [US8] Implement automatic context detection from IssueView in `frontend/src/features/issues/hooks/useIssueContext.ts`
- [ ] T086 [US8] Wire context providers to PilotSpaceStore.setContext
- [ ] T087 [US8] Implement context change detection and store update

**Checkpoint**: US8 functional - AI uses correct context automatically.

---

## Phase Final: Polish

Cross-cutting concerns after all stories complete.

### Integration Testing

- [ ] T088 [P] E2E test: Skill invocation via ChatView in `frontend/tests/e2e/ai-skill-invocation.spec.ts`
- [ ] T089 [P] E2E test: Subagent invocation via ChatView in `frontend/tests/e2e/ai-subagent-invocation.spec.ts`
- [ ] T090 [P] E2E test: Approval flow in `frontend/tests/e2e/ai-approval-flow.spec.ts`
- [ ] T091 [P] E2E test: Session resumption in `frontend/tests/e2e/ai-session-resumption.spec.ts`
- [ ] T092 [P] E2E test: Task tracking in `frontend/tests/e2e/ai-task-tracking.spec.ts`
- [ ] T093 E2E test: Error recovery in `frontend/tests/e2e/ai-error-recovery.spec.ts`

### Performance Benchmarks

- [ ] T094 Benchmark GhostText latency (<2s p95) in `backend/tests/performance/test_ghost_text_latency.py`
- [ ] T095 [P] Benchmark skill invocation latency (<10s) in `backend/tests/performance/test_skill_latency.py`
- [ ] T096 [P] Benchmark subagent streaming (first token <5s) in `backend/tests/performance/test_subagent_streaming.py`
- [ ] T097 Load test concurrent sessions (100 users) in `backend/tests/performance/test_concurrent_sessions.py`

### Cleanup

- [ ] T098 Add deprecation warnings to old stores in `frontend/src/stores/ai/`
- [ ] T099 Add deprecation headers to old API endpoints
- [ ] T100 Update SDKOrchestrator to delegate to PilotSpaceAgent
- [ ] T101 Update agent registration in `backend/src/pilot_space/container.py`
- [ ] T102 Add error boundary and retry logic in ChatView

### Documentation

- [ ] T103 [P] Update architecture documentation to reflect implemented state
- [ ] T104 [P] Create skill development guide in `docs/guides/skill-development.md`
- [ ] T105 [P] Create subagent development guide in `docs/guides/subagent-development.md`
- [ ] T106 [P] Update API documentation for /ai/chat endpoint
- [ ] T107 Create ChatView integration guide in `docs/guides/chatview-integration.md`

### Final Validation

- [ ] T108 Run quickstart.md validation
- [ ] T109 Final architecture audit against target architecture v1.5.0

---

## Dependencies

### Phase Order

```
Setup → Foundational → User Stories (US1→US2→US3→US4 P1, then US5→US6→US7→US8 P2) → Polish
```

### User Story Independence

- US1-US4 (P1): Core MVP - must complete in order (conversational → skills → subagents → approval)
- US5-US8 (P2): Can run in parallel after US1-US4 complete
- Each P2 story is independently testable

### Within Each Story

1. Backend changes before frontend integration
2. Store changes before component wiring
3. Core functionality before edge cases
4. Tests after implementation (not TDD - not requested in spec)

### Parallel Opportunities

Tasks marked `[P]` in the same phase can run concurrently:

```bash
# Example: Launch skill creation in parallel
Task T017-T024: Create all 8 skill SKILL.md files simultaneously

# Example: Launch database models in parallel
Task T008-T011: Create Message, ToolCall, Task, ApprovalRequest models

# Example: Launch subagent refactoring in parallel
Task T033-T035: Refactor PR Review, AI Context, Doc Generator subagents
```

---

## Implementation Strategy

### MVP First

1. Setup → Foundational → US1 only
2. Validate: User can chat with AI about notes
3. Deploy/demo MVP

### P1 Complete

1. Add US2 (Skills) → test → deploy
2. Add US3 (Subagents) → test → deploy
3. Add US4 (Approval) → test → deploy
4. P1 milestone complete

### P2 Incremental

1. US5 (Tasks) + US6 (Sessions) can run in parallel
2. US7 (GhostText) is mostly verification (existing feature)
3. US8 (Context) completes the experience
4. Full MVP complete

---

## Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Phase 1: Setup | 6 | 3 |
| Phase 2: Foundational | 43 | 24 |
| Phase 3: US1 - Natural Language (P1) | 6 | 1 |
| Phase 4: US2 - Skill Invocation (P1) | 5 | 0 |
| Phase 5: US3 - Subagent Delegation (P1) | 5 | 0 |
| Phase 6: US4 - Human Approval (P1) | 5 | 0 |
| Phase 7: US5 - Task Tracking (P2) | 4 | 0 |
| Phase 8: US6 - Session Persistence (P2) | 5 | 0 |
| Phase 9: US7 - GhostText Fast Path (P2) | 4 | 0 |
| Phase 10: US8 - Context Awareness (P2) | 4 | 0 |
| Phase Final: Polish | 22 | 12 |
| **Total** | **109** | **40** |

**MVP Scope**: Phases 1-6 (US1-US4) = 70 tasks
**Full Scope**: All phases = 109 tasks
