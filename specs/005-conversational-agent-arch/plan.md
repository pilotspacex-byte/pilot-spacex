# Implementation Plan: Conversational Agent Architecture Migration

**Branch**: `005-conversational-agent-arch` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-conversational-agent-arch/spec.md`
**Source**: Remediation Plan v1.3.0 (131 tasks across 6 phases)

## Summary

Migrate PilotSpace AI implementation from a **siloed agent architecture** (13 independent agents, 9 frontend stores) to a **centralized conversational agent architecture** with:
- **PilotSpaceAgent**: Main orchestrator using Claude Agent SDK
- **3 Subagents**: PRReviewSubagent, AIContextSubagent, DocGeneratorSubagent
- **8 Skills**: extract-issues, enhance-issue, recommend-assignee, find-duplicates, decompose-tasks, generate-diagram, improve-writing, summarize
- **Unified PilotSpaceStore**: Consolidating 8 siloed stores (GhostTextStore remains independent)
- **ChatView UI**: 25 components already created in Phase 4.2

Technical approach: SDK-native integration with skill files in `.claude/skills/`, SSE streaming via `/api/v1/ai/chat`, human-in-the-loop approval per DD-003.

## Technical Context

**Language/Version**: Python 3.12 (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), React 18, MobX, Claude Agent SDK (>=1.0,<2.0)
**Storage**: PostgreSQL 16+ with pgvector, Redis (sessions/cache), Supabase (Auth, Storage, Queues)
**Testing**: pytest (backend), Vitest (frontend), Playwright (E2E)
**Target Platform**: Web (Supabase hosted), Docker Compose (dev)
**Project Type**: Web application (frontend + backend)
**Performance Goals**: GhostText <2s p95, Skills <10s for simple, First token <3s p95, 100 concurrent users
**Constraints**: SSE streaming required, BYOK model (Anthropic required, OpenAI for embeddings), No local LLM
**Scale/Scope**: 131 migration tasks, 6 phases, MVP (Phases 1-5: 90 tasks), Phase 6: 41 polish tasks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|------|--------|----------|
| **I. AI-Human Collaboration First** | ✅ PASS | FR-014-017 implement human-in-the-loop approval per DD-003; canUseTool callback for SDK permission handling |
| **II. Note-First Approach** | ✅ PASS | FR-022-025 integrate ChatView with NoteCanvas; context awareness includes note_id, selected_text |
| **II.A Ghost Text** | ✅ PASS | FR-005 maintains GhostText independent fast path (<2s); not impacted by migration |
| **II.B Margin Annotations** | ✅ PASS | Skills can produce margin annotations via structured output |
| **II.C Issue Extraction** | ✅ PASS | FR-003 includes extract-issues skill; DD-048 confidence tagging (RECOMMENDED/DEFAULT/CURRENT/ALTERNATIVE) |
| **III. Documentation-Third** | ✅ PASS | DocGeneratorSubagent creates documentation from codebase analysis |
| **IV. Task-Centric** | ✅ PASS | FR-010-013 implement task tracking via TaskPanel; SDK Task tool for decomposition |
| **V. Collaboration** | ✅ PASS | Session persistence (FR-018-021) enables multi-session knowledge building |
| **VI. Agile Integration** | ✅ PASS | Skills support story points, assignee recommendations via expertise mapping |
| **VII. Notation & Standards** | ✅ PASS | FR-003 includes generate-diagram skill for Mermaid output |
| **Technology Standards** | ✅ PASS | FastAPI + SQLAlchemy 2.0, React 18 + MobX, PostgreSQL 16 + pgvector, Supabase Auth + RLS |
| **Quality Gates** | ✅ PASS | E2E tests (P5-001-006), performance benchmarks (P5-007-010), documentation (P5-011-015) |

**Constitution Version**: 1.2.1 | **Check Date**: 2026-01-27

## Project Structure

### Documentation (this feature)

```text
specs/005-conversational-agent-arch/
├── plan.md              # This file
├── research.md          # Phase 0 output: SDK integration patterns, skill format research
├── data-model.md        # Phase 1 output: Session, Message, Task, ApprovalRequest entities
├── quickstart.md        # Phase 1 output: Developer setup guide
├── contracts/           # Phase 1 output: API contracts, SSE event schemas
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/pilot_space/
│   ├── ai/
│   │   ├── sdk/                           # Phase 1: SDK integration layer
│   │   │   ├── config.py                  # ClaudeAgentOptions factory
│   │   │   ├── session_handler.py         # Session capture, resume, fork
│   │   │   ├── permission_handler.py      # canUseTool callback
│   │   │   └── hooks.py                   # PreToolUse, PostToolUse hooks
│   │   ├── agents/
│   │   │   ├── pilotspace_agent.py        # Phase 3: Main orchestrator
│   │   │   └── subagents/                 # Phase 3: Refactored agents
│   │   │       ├── pr_review_subagent.py
│   │   │       ├── ai_context_subagent.py
│   │   │       └── doc_generator_subagent.py
│   │   └── skills/                        # Phase 2: Legacy skill handlers (deprecated)
│   ├── api/v1/routers/
│   │   └── ai_chat.py                     # Phase 3: Unified /ai/chat endpoint
│   └── .claude/
│       ├── CLAUDE.md                      # Project instructions for SDK
│       ├── rules/                         # Path-specific rules
│       └── skills/                        # Phase 2: 8 skill SKILL.md files
│           ├── extract-issues/
│           ├── enhance-issue/
│           ├── recommend-assignee/
│           ├── find-duplicates/
│           ├── decompose-tasks/
│           ├── generate-diagram/
│           ├── improve-writing/
│           └── summarize/
└── tests/
    ├── e2e/                               # Phase 5: E2E tests
    └── integration/                       # Phase 5: Integration tests

frontend/
├── src/
│   ├── stores/ai/
│   │   ├── PilotSpaceStore.ts             # Phase 4: Unified store
│   │   └── types/                         # Phase 4: Type definitions
│   │       ├── conversation.ts
│   │       ├── skills.ts
│   │       └── events.ts
│   └── features/ai/ChatView/              # Phase 4.2: ✅ COMPLETED (25 files)
│       ├── ChatView.tsx
│       ├── ChatHeader.tsx
│       ├── MessageList/
│       ├── TaskPanel/
│       ├── ApprovalOverlay/
│       └── ChatInput/
└── tests/
    └── e2e/                               # Phase 5: Playwright tests
```

**Structure Decision**: Web application structure with frontend/ and backend/ directories. Backend follows CQRS-lite pattern with service classes. Frontend uses feature-based organization with MobX stores.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | N/A | N/A |

No constitution violations detected. All gates pass.

## Implementation Phases

### Phase 1: Foundation & SDK Integration Layer (P1-001 to P1-012)

**Priority**: Critical (blocks all subsequent phases)
**Tasks**: 12

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P1-001 | Create `sdk/config.py` with `ClaudeAgentOptions` factory | Returns configured options with `setting_sources=["project"]`, sandbox settings |
| P1-002 | Implement `session_handler.py` with session capture | Captures `session_id`, supports `resume`, `fork_session` |
| P1-003 | Implement `permission_handler.py` with `canUseTool` callback | Maps to existing ApprovalService, handles `AskUserQuestion` |
| P1-004 | Create `hooks.py` with `PreToolUse` approval interceptor | Integrates with existing `ACTION_CLASSIFICATIONS` |
| P1-005 | Update `dependencies.py` to provide SDK configuration | Injects `ClaudeAgentOptions` via dependency injection |
| P1-006 | Create `.claude/CLAUDE.md` with project instructions | Includes note-first workflow, confidence tagging, approval rules |
| P1-007 | Create `.claude/rules/issues.md` with issue patterns | Path-specific rules for issue-related files |
| P1-008 | Create `.claude/rules/notes.md` with note patterns | Path-specific rules for note-related files |
| P1-009 | Create `.claude/rules/ai-confidence.md` with DD-048 rules | Defines RECOMMENDED/DEFAULT/CURRENT/ALTERNATIVE tags |
| P1-010 | Design sandbox directory structure per user/workspace | `/sandbox/{user_id}/{workspace_id}/` with isolated `.claude/` |
| P1-011 | Implement sandbox provisioning on workspace creation | Creates directory structure, copies base skills |
| P1-012 | Create base skills mount (read-only) | `/opt/pilotspace/base-skills/` with default skills |

### Phase 2: Skill Migration (P2-001 to P2-011)

**Priority**: High
**Dependencies**: Phase 1 complete
**Tasks**: 11

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P2-001 | Create `extract-issues/SKILL.md` from IssueExtractorAgent | YAML frontmatter; workflow steps; JSON schema with DD-048 confidence |
| P2-002 | Create `enhance-issue/SKILL.md` from IssueEnhancerAgent | Single prompt for labels, priority, acceptance criteria |
| P2-003 | Create `recommend-assignee/SKILL.md` from AssigneeRecommenderAgent | Expertise matching workflow; structured output |
| P2-004 | Create `find-duplicates/SKILL.md` from DuplicateDetectorAgent | Vector search integration; similarity thresholds |
| P2-005 | Create `decompose-tasks/SKILL.md` from TaskDecomposerAgent | Dependency modeling; subtask schema |
| P2-006 | Create `generate-diagram/SKILL.md` from DiagramGeneratorAgent | Mermaid syntax; diagram types |
| P2-007 | Create `improve-writing/SKILL.md` (new) | Style guide reference; clarity improvements |
| P2-008 | Create `summarize/SKILL.md` (new) | Multi-format summary output |
| P2-009 | Update skill registry to use filesystem discovery | Loads from `.claude/skills/` per SDK pattern |
| P2-010 | Create skill validation utility | Validates SKILL.md format, frontmatter |
| P2-011 | Add skill invocation tests | E2E tests for each skill |

### Phase 3: Backend Consolidation (P3-001 to P3-015)

**Priority**: High
**Dependencies**: Phase 2 complete
**Tasks**: 15

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P3-001 | Create `PilotSpaceAgent` class | Implements SDK `query()` loop; skill/subagent routing |
| P3-002 | Implement intent parsing (`_parse_intent`) | Detects `\skill`, `@agent`, natural language |
| P3-003 | Implement skill execution (`_execute_skill`) | Invokes SDK `Skill` tool; streams result |
| P3-004 | Implement subagent spawning (`_spawn_subagent`) | Uses SDK `Task` tool; tracks progress |
| P3-005 | Implement task planning (`_plan_tasks`) | Decomposes complex requests into task list |
| P3-006 | Refactor PRReviewAgent as subagent | Adapts to `AgentDefinition` format |
| P3-007 | Refactor AIContextAgent as subagent | Adapts to `AgentDefinition` format |
| P3-008 | Refactor DocGeneratorAgent as subagent | Adapts to `AgentDefinition` format |
| P3-009 | Create `/api/v1/ai/chat` unified endpoint | Handles all conversational interactions |
| P3-010 | Add context extraction middleware | Extracts note/issue/project context |
| P3-011 | Implement SSE event transformation | Maps SDK messages to frontend format |
| P3-012 | Deprecate old endpoints (not remove yet) | Add deprecation headers; log usage |
| P3-013 | Update `SDKOrchestrator` to use PilotSpaceAgent | Delegates conversational requests |
| P3-014 | Remove migrated agents from registry | GhostText stays; others removed |
| P3-015 | Update agent registration in `container.py` | Registers PilotSpaceAgent + 3 subagents |

### Phase 4: Frontend Architecture (P4-001 to P4-032)

**Priority**: High
**Dependencies**: Phase 3 API endpoints ready
**Tasks**: 32 (8 completed in P4.2)

**Completed (Phase 4.2):**
- P4-009 to P4-016: ChatView component tree (25 files, ~4,000 lines) ✅

**Remaining:**

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P4-001 | Create `PilotSpaceStore` class | Implements interface from architecture doc |
| P4-002 | Implement conversation state | Messages, streaming content, session ID |
| P4-003 | Implement task state | Task map, active/completed computed |
| P4-004 | Implement approval state | Pending approvals, approve/reject actions |
| P4-005 | Implement context state | Note/issue/project context |
| P4-006 | Implement actions | sendMessage, setContext, abort, clear |
| P4-007 | Add SSE streaming integration | Uses existing SSEClient |
| P4-008 | Add skill/agent definitions | Static definitions for UI menus |
| P4-017 | Update AIStore to include PilotSpaceStore | Add as property alongside existing stores |
| P4-018 | Create migration path for IssueExtractionStore | Redirect to PilotSpaceStore for new features |
| P4-019 | Create migration path for ConversationStore | Redirect to PilotSpaceStore for new features |
| P4-020 | Deprecate siloed stores (not remove yet) | Add deprecation warnings; log usage |
| P4-021 | Add ChatView sidebar to NoteCanvas | Toggleable panel; preserves GhostText |
| P4-022 | Implement `\skill` detection in editor | Triggers SkillMenu on `\` keystroke |
| P4-023 | Implement `@agent` detection in editor | Triggers AgentMenu on `@` keystroke |
| P4-024 | Connect selection context to PilotSpaceStore | Updates noteContext on selection |
| P4-025 | Wire ChatInput to PilotSpaceStore.sendMessage | Enter/submit triggers API call |
| P4-026 | Implement SSE event handlers in PilotSpaceStore | All 8 event types handled correctly |
| P4-027 | Wire MessageList to store.messages | Auto-scroll, streaming content display |
| P4-028 | Wire TaskPanel to store.tasks | Real-time progress updates |
| P4-029 | Wire ApprovalOverlay to store.pendingApprovals | Approval queue, approve/reject actions |
| P4-030 | Implement skill invocation flow | `\skill` → sendMessage with skill context |
| P4-031 | Implement agent mention flow | `@agent` → sendMessage with agent context |
| P4-032 | Add error boundary and retry logic | Graceful error handling, reconnection |

### Phase 5: Integration & Testing (P5-001 to P5-020)

**Priority**: High
**Dependencies**: Phases 1-4 complete
**Tasks**: 20

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P5-001 | E2E test: Skill invocation via ChatView | User triggers `\extract-issues`, sees results |
| P5-002 | E2E test: Subagent invocation via ChatView | User triggers `@pr-review`, sees streaming output |
| P5-003 | E2E test: Approval flow | User extracts issues, approves subset, issues created |
| P5-004 | E2E test: Session resumption | User closes/reopens chat, context preserved |
| P5-005 | E2E test: Task tracking | User sees task list, progress updates |
| P5-006 | E2E test: Error recovery | Network failure → reconnect → resume |
| P5-007 | Benchmark GhostText latency | <2s p95 maintained |
| P5-008 | Benchmark skill invocation latency | <10s for simple skills |
| P5-009 | Benchmark subagent streaming | First token <5s, continuous stream |
| P5-010 | Load test concurrent sessions | 100 concurrent users, no degradation |
| P5-011 | Update architecture documentation | Reflects implemented state |
| P5-012 | Create skill development guide | How to create custom skills |
| P5-013 | Create subagent development guide | How to add new subagents |
| P5-014 | Update API documentation | New /ai/chat endpoint documented |
| P5-015 | Create ChatView integration guide | How to extend ChatView components |
| P5-016 | Remove deprecated agent files | After migration verified |
| P5-017 | Remove deprecated store files | After migration verified |
| P5-018 | Remove deprecated API endpoints | After traffic migrated |
| P5-019 | Clean up unused dependencies | Remove packages no longer needed |
| P5-020 | Final architecture audit | Verify all components align with target architecture |

### Phase 6: Polish & Refinement (P6-001 to P6-041)

**Priority**: Medium (post-MVP enhancements)
**Dependencies**: Phase 5 complete
**Tasks**: 41

Categories:
- **UI/UX Refinement** (P6-001 to P6-006): Loading skeletons, empty states, reactions, copy, regenerate, branching
- **Animations** (P6-007 to P6-012): Message entrance, streaming cursor, panel transitions
- **Error States** (P6-013 to P6-018): Offline UI, rate limits, session expired, API key missing
- **Accessibility** (P6-019 to P6-024): Screen reader, focus management, keyboard shortcuts, contrast
- **Theming** (P6-025 to P6-029): Dark mode, mobile responsive, tablet layout
- **Performance** (P6-030 to P6-035): Virtualization, lazy loading, pagination, caching
- **Advanced Features** (P6-036 to P6-041): Search, export, templates, model selector, analytics, sharing

## Critical Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CRITICAL PATH                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Phase 1 (Foundation)           Phase 3 (Backend)           Phase 4 (FE)    │
│  ┌───────────────────┐         ┌───────────────────┐       ┌─────────────┐  │
│  │ P1-001: SDK Config│────────▶│ P3-001: PilotSpace│──────▶│ P4-001:     │  │
│  │ P1-002: Sessions  │         │         Agent     │       │ PilotSpace  │  │
│  │ P1-003: Permissions│        │ P3-009: /ai/chat  │──┐    │ Store       │  │
│  └───────────────────┘         └───────────────────┘  │    └──────┬──────┘  │
│                                                        │           │         │
│  Phase 2 (Skills)                                      │           ▼         │
│  ┌───────────────────┐                                │    ┌─────────────┐  │
│  │ P2-001: Skills    │─────────────────────────────────┼───▶│ P4-025-032: │  │
│  │ P2-009: Registry  │                                │    │ Integration │  │
│  └───────────────────┘                                │    └──────┬──────┘  │
│                                                        │           │         │
│                                                        │           ▼         │
│                                                        │    ┌─────────────┐  │
│                                                        └───▶│ P5-001-006: │  │
│                                                             │ E2E Tests   │  │
│                                                             └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Next Priority Tasks (in order):**
1. **P1-001**: Create `sdk/config.py` with `ClaudeAgentOptions` factory
2. **P2-001**: Create `extract-issues/SKILL.md` (skill file format)
3. **P3-001**: Create `PilotSpaceAgent` class (main orchestrator)
4. **P3-009**: Create `/api/v1/ai/chat` unified endpoint
5. **P4-001**: Create `PilotSpaceStore` class (frontend state)
6. **P4-025**: Wire ChatInput to PilotSpaceStore.sendMessage

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SDK integration complexity | Medium | High | Start with single skill migration; validate pattern before scaling |
| Session state corruption | Medium | High | Implement checkpointing early; automatic recovery |
| Frontend performance regression | Low | Medium | Incremental migration; feature flags for rollback |
| Breaking changes during migration | Medium | Medium | Maintain backward compatibility; deprecate before remove |

## Success Criteria

| Phase | Criteria |
|-------|----------|
| **Phase 1** | SDK configuration working; CLAUDE.md loaded; sandbox provisioned |
| **Phase 2** | All 8 skills migrated; skill invocation via SDK working |
| **Phase 3** | PilotSpaceAgent streaming; /ai/chat endpoint live; subagents invokable |
| **Phase 4** | ChatView component complete; PilotSpaceStore integrated; skill/agent menus working |
| **Phase 5** | All E2E tests passing; performance benchmarks met; documentation updated |
| **Phase 6** | Animations smooth; accessibility audit passed; mobile responsive; dark mode consistent |

## References

- [Feature Specification](./spec.md)
- [Remediation Plan v1.3.0](../../docs/architect/agent-architecture-remediation-plan.md)
- [Target Architecture v1.5.0](../../docs/architect/pilotspace-agent-architecture.md)
- [Constitution v1.2.1](../../.specify/memory/constitution.md)
- [Dev Patterns](../../docs/dev-pattern/45-pilot-space-patterns.md)
