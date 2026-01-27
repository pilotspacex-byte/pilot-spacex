# PilotSpace Agent Architecture Remediation Plan

> **Version**: 1.3.0
> **Date**: 2026-01-27
> **Target Architecture**: pilotspace-agent-architecture.md v1.5.0
> **Author**: Principal AI Systems Architect
> **Status**: Phase 4.2 Complete ✅ | Full Roadmap Defined

## Executive Summary

This document provides a comprehensive remediation plan to migrate the current PilotSpace AI implementation from a **siloed agent architecture** to the **centralized conversational agent architecture** defined in `pilotspace-agent-architecture.md` v1.5.0.

### Current vs Target State Summary

| Dimension | Current State | Target State | Gap Severity |
|-----------|--------------|--------------|--------------|
| **Backend Agents** | 13 independent agents | PilotSpaceAgent + 3 subagents + 8 skills | 🔴 High |
| **Orchestration** | Custom SDKOrchestrator | Claude Agent SDK native | 🔴 High |
| **Frontend Stores** | 9 siloed MobX stores | Unified PilotSpaceStore | 🟡 Medium |
| **UI Components** | Feature-specific views | ChatView + ApprovalOverlay | 🟡 In Progress (P4.2 ✅) |
| **Session Management** | Per-agent sessions | Unified SDK sessions | 🟡 Medium |
| **Skill System** | None | .claude/skills/ directory | 🔴 High |
| **Tool Integration** | Custom MCP tools | SDK builtin + MCP tools | 🟢 Low |
| **Approval Flow** | Custom ApprovalService | SDK canUseTool + hooks | 🟡 Medium |

### Implementation Progress

| Phase | Status | Tasks | Completed | Progress |
|-------|--------|-------|-----------|----------|
| **Phase 1: Foundation** | ⬜ Not Started | 12 | 0 | 0% |
| **Phase 2: Skills** | ⬜ Not Started | 11 | 0 | 0% |
| **Phase 3: Backend** | ⬜ Not Started | 15 | 0 | 0% |
| **Phase 4: Frontend** | 🟡 In Progress | 32 | 8 | 25% |
| **Phase 5: Integration & Testing** | ⬜ Not Started | 20 | 0 | 0% |
| **Phase 6: Polish & Refinement** | ⬜ Not Started | 41 | 0 | 0% |
| **Total** | | **131** | **8** | **6%** |

**Phase Summary:**
- **Phases 1-5**: Core MVP (90 tasks) - Required for launch
- **Phase 6**: Post-MVP Polish (41 tasks) - Enhanced experience

**Recently Completed:**
- ✅ P4-009 to P4-016: ChatView component tree (25 files, ~4,000 lines)

### Critical Path

The following tasks are on the critical path and should be prioritized:

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

---

## Phase 1: Foundation & SDK Integration Layer

**Duration Estimate**: Sprint 1 (2 weeks)
**Dependencies**: None
**Priority**: Critical (blocks all subsequent phases)

### 1.1 Claude Agent SDK Configuration Layer

**Files to Create:**
```
backend/src/pilot_space/ai/
├── sdk/
│   ├── __init__.py
│   ├── config.py              # SDK configuration factory
│   ├── session_handler.py     # SDK session management
│   ├── permission_handler.py  # canUseTool implementation
│   └── hooks.py               # PreToolUse, PostToolUse hooks
```

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P1-001 | Create `sdk/config.py` with `ClaudeAgentOptions` factory | Returns configured options with `setting_sources=["project"]`, sandbox settings | None |
| P1-002 | Implement `session_handler.py` with session capture from `init` message | Captures `session_id`, supports `resume`, `fork_session` | P1-001 |
| P1-003 | Implement `permission_handler.py` with `canUseTool` callback | Maps to existing ApprovalService, handles `AskUserQuestion` | P1-001 |
| P1-004 | Create `hooks.py` with `PreToolUse` approval interceptor | Integrates with existing `ACTION_CLASSIFICATIONS` | P1-003 |
| P1-005 | Update `dependencies.py` to provide SDK configuration | Injects `ClaudeAgentOptions` via dependency injection | P1-001 |

**Code Pattern for P1-001:**
```python
# backend/src/pilot_space/ai/sdk/config.py
from claude_agent_sdk import ClaudeAgentOptions, SandboxSettings

def create_pilotspace_agent_options(
    user_id: str,
    workspace_id: str,
    key_storage: SecureKeyStorage,
    permission_handler: PermissionHandler,
) -> ClaudeAgentOptions:
    """Factory for PilotSpace agent configuration."""

    user_cwd = f"/sandbox/{user_id}/{workspace_id}"

    return ClaudeAgentOptions(
        cwd=user_cwd,
        setting_sources=["project", "user"],
        allowed_tools=[
            "Skill", "Task", "Read", "Write", "Edit", "Bash",
            "Glob", "Grep", "TodoWrite", "AskUserQuestion", "WebFetch",
        ],
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": PILOTSPACE_SYSTEM_PROMPT,
        },
        permission_mode="default",
        can_use_tool=permission_handler.handle_permission,
        sandbox=SandboxSettings(
            enabled=True,
            auto_allow_bash_if_sandboxed=True,
        ),
        env={
            "PILOTSPACE_USER_ID": user_id,
            "PILOTSPACE_WORKSPACE_ID": workspace_id,
        },
    )
```

### 1.2 Memory System Implementation

**Files to Create:**
```
backend/
├── .claude/
│   ├── CLAUDE.md              # Project instructions for SDK
│   └── rules/
│       ├── issues.md          # Issue formatting rules
│       ├── notes.md           # Note-first workflow rules
│       └── ai-confidence.md   # Confidence tag rules (DD-048)
```

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P1-006 | Create `.claude/CLAUDE.md` with project instructions | Includes note-first workflow, confidence tagging, approval rules | None |
| P1-007 | Create `.claude/rules/issues.md` with issue patterns | Path-specific rules for `src/api/v1/routers/issues.py` | P1-006 |
| P1-008 | Create `.claude/rules/notes.md` with note patterns | Path-specific rules for note-related files | P1-006 |
| P1-009 | Create `.claude/rules/ai-confidence.md` with DD-048 rules | Defines Recommended/Default/Current/Alternative tags | P1-006 |

### 1.3 Sandbox Infrastructure

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P1-010 | Design sandbox directory structure per user/workspace | `/sandbox/{user_id}/{workspace_id}/` with isolated `.claude/` | P1-001 |
| P1-011 | Implement sandbox provisioning on workspace creation | Creates directory structure, copies base skills | P1-010 |
| P1-012 | Create base skills mount (read-only) | `/opt/pilotspace/base-skills/` with default skills | P1-010 |

---

## Phase 2: Skill Migration

**Duration Estimate**: Sprint 2 (2 weeks)
**Dependencies**: Phase 1 complete
**Priority**: High

### 2.1 Skill Directory Structure

**Files to Create:**
```
backend/.claude/skills/
├── extract-issues/
│   ├── SKILL.md
│   └── EXAMPLES.md
├── improve-writing/
│   ├── SKILL.md
│   └── STYLE_GUIDE.md
├── summarize/
│   └── SKILL.md
├── find-duplicates/
│   ├── SKILL.md
│   └── SIMILARITY_THRESHOLDS.md
├── recommend-assignee/
│   ├── SKILL.md
│   └── EXPERTISE_MATRIX.md
├── decompose-tasks/
│   ├── SKILL.md
│   └── DEPENDENCY_PATTERNS.md
├── enhance-issue/
│   └── SKILL.md
└── generate-diagram/
    ├── SKILL.md
    └── MERMAID_TEMPLATES.md
```

### 2.2 Agent-to-Skill Migration Matrix

| Current Agent | Target Skill | Complexity | Migration Notes |
|--------------|--------------|------------|-----------------|
| `IssueExtractorAgent` | `extract-issues` | Medium | Move prompt to SKILL.md; structured JSON output |
| `IssueEnhancerAgent` | `enhance-issue` | Low | Single prompt transformation |
| `AssigneeRecommenderAgent` | `recommend-assignee` | Medium | Needs expertise data access |
| `DuplicateDetectorAgent` | `find-duplicates` | High | Requires pgvector integration |
| `TaskDecomposerAgent` | `decompose-tasks` | Medium | Structured subtask output |
| `DiagramGeneratorAgent` | `generate-diagram` | Low | Mermaid output |
| N/A (new) | `improve-writing` | Low | Text transformation |
| N/A (new) | `summarize` | Low | Content summarization |

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P2-001 | Create `extract-issues/SKILL.md` from IssueExtractorAgent | YAML frontmatter with name/description; workflow steps; JSON schema | P1-006 |
| P2-002 | Create `enhance-issue/SKILL.md` from IssueEnhancerAgent | Single prompt for labels, priority, acceptance criteria | P1-006 |
| P2-003 | Create `recommend-assignee/SKILL.md` from AssigneeRecommenderAgent | Expertise matching workflow; structured output | P1-006 |
| P2-004 | Create `find-duplicates/SKILL.md` from DuplicateDetectorAgent | Vector search integration; similarity thresholds | P1-006 |
| P2-005 | Create `decompose-tasks/SKILL.md` from TaskDecomposerAgent | Dependency modeling; subtask schema | P1-006 |
| P2-006 | Create `generate-diagram/SKILL.md` from DiagramGeneratorAgent | Mermaid syntax; diagram types | P1-006 |
| P2-007 | Create `improve-writing/SKILL.md` (new) | Style guide reference; clarity improvements | P1-006 |
| P2-008 | Create `summarize/SKILL.md` (new) | Multi-format summary output | P1-006 |

**Example SKILL.md (P2-001):**
```yaml
---
name: extract-issues
description: >
  Extract structured issues from note content. Use when the user asks to
  identify tasks, bugs, or work items from their notes or selected text.
---

# Extract Issues

## Quick Start

Analyze the provided content and identify actionable items.

## Workflow

1. Read the content or selection
2. Identify potential issues (bugs, tasks, features)
3. For each issue:
   - Generate a clear title
   - Write description with context
   - Suggest labels and priority
   - Include confidence score

## Confidence Tagging (DD-048)

Mark each issue with confidence:
- **RECOMMENDED** (>0.8): High confidence, auto-create eligible
- **DEFAULT** (0.5-0.8): Standard confidence, requires review
- **CURRENT** (use existing): Match to existing pattern
- **ALTERNATIVE** (<0.5): Present as option only

## Output Format

Return JSON with this structure:
```json
{
  "issues": [
    {
      "title": "string",
      "description": "string",
      "labels": ["string"],
      "priority": 1-5,
      "confidence_tag": "RECOMMENDED|DEFAULT|CURRENT|ALTERNATIVE",
      "confidence_score": 0.0-1.0,
      "source_block_ids": ["string"],
      "rationale": "string"
    }
  ]
}
```

See @EXAMPLES.md for annotated examples.
```

### 2.3 Skill Registry Update

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P2-009 | Update skill registry to use filesystem discovery | Loads from `.claude/skills/` per SDK pattern | P2-001 to P2-008 |
| P2-010 | Create skill validation utility | Validates SKILL.md format, frontmatter | P2-009 |
| P2-011 | Add skill invocation tests | E2E tests for each skill | P2-009 |

---

## Phase 3: Backend Consolidation

**Duration Estimate**: Sprint 3-4 (4 weeks)
**Dependencies**: Phase 2 complete
**Priority**: High

### 3.1 PilotSpaceAgent Implementation

**Files to Create:**
```
backend/src/pilot_space/ai/agents/
├── pilotspace_agent.py        # Main orchestrator (new)
├── subagents/
│   ├── __init__.py
│   ├── pr_review_subagent.py  # Refactored from pr_review_agent.py
│   ├── ai_context_subagent.py # Refactored from ai_context_agent.py
│   └── doc_generator_subagent.py # Refactored from doc_generator_agent.py
```

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P3-001 | Create `PilotSpaceAgent` class | Implements SDK `query()` loop; skill/subagent routing | P2-009 |
| P3-002 | Implement intent parsing (`_parse_intent`) | Detects `\skill`, `@agent`, natural language | P3-001 |
| P3-003 | Implement skill execution (`_execute_skill`) | Invokes SDK `Skill` tool; streams result | P3-001 |
| P3-004 | Implement subagent spawning (`_spawn_subagent`) | Uses SDK `Task` tool; tracks progress | P3-001 |
| P3-005 | Implement task planning (`_plan_tasks`) | Decomposes complex requests into task list | P3-001 |
| P3-006 | Refactor PRReviewAgent as subagent | Adapts to `AgentDefinition` format | P3-001 |
| P3-007 | Refactor AIContextAgent as subagent | Adapts to `AgentDefinition` format | P3-001 |
| P3-008 | Refactor DocGeneratorAgent as subagent | Adapts to `AgentDefinition` format | P3-001 |

**Code Pattern for P3-001:**
```python
# backend/src/pilot_space/ai/agents/pilotspace_agent.py
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

class PilotSpaceAgent:
    """Main PilotSpace conversational agent orchestrator."""

    SUBAGENTS: ClassVar[dict[str, AgentDefinition]] = {
        "pr-review": AgentDefinition(
            description="Expert code review for quality, security, and best practices",
            prompt="...",
            tools=["Read", "Grep", "Glob"],
            model="opus"
        ),
        "ai-context": AgentDefinition(
            description="Multi-turn context aggregation for issues",
            prompt="...",
            tools=["Read", "Grep", "Glob", "WebSearch"],
            model="opus"
        ),
        "doc-generator": AgentDefinition(
            description="Generate technical documentation",
            prompt="...",
            tools=["Read", "Write", "Grep"],
            model="sonnet"
        ),
    }

    async def stream(
        self,
        input_text: str,
        context: ConversationContext,
    ) -> AsyncIterator[SSEEvent]:
        """Main entry point for conversational interaction."""

        options = create_pilotspace_agent_options(
            user_id=str(context.user_id),
            workspace_id=str(context.workspace_id),
            key_storage=self._key_storage,
            permission_handler=self._permission_handler,
        )
        options.agents = self.SUBAGENTS

        session_id = await self._session_handler.get_or_resume(context)
        if session_id:
            options.resume = session_id

        async for message in query(input_text, options):
            yield self._transform_message(message)
```

### 3.2 API Endpoint Consolidation

**Current Endpoints to Consolidate:**
```
POST /api/v1/notes/{noteId}/ghost-text         → Keep (fast path)
POST /api/v1/notes/{noteId}/extract-issues     → Migrate to /api/v1/ai/chat
POST /api/v1/ai/notes/{noteId}/annotations     → Migrate to /api/v1/ai/chat
POST /api/v1/issues/{issueId}/ai-context/stream → Migrate to /api/v1/ai/chat
POST /api/v1/ai/conversation                   → Migrate to /api/v1/ai/chat
POST /api/v1/ai/repos/{repoId}/prs/{prNumber}/review → Keep (subagent invocation)
```

**New Unified Endpoint:**
```
POST /api/v1/ai/chat
Body: {
  "message": "string",
  "context": {
    "note_id": "uuid | null",
    "issue_id": "uuid | null",
    "project_id": "uuid | null",
    "selected_text": "string | null",
    "selected_block_ids": ["string"]
  },
  "session_id": "string | null"  // For resumption
}

Response: SSE stream with events:
- message_start
- content_block_start
- text_delta
- tool_use (skill/subagent invocation)
- approval_request
- task_progress
- message_stop
```

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P3-009 | Create `/api/v1/ai/chat` unified endpoint | Handles all conversational interactions | P3-001 |
| P3-010 | Add context extraction middleware | Extracts note/issue/project context | P3-009 |
| P3-011 | Implement SSE event transformation | Maps SDK messages to frontend format | P3-009 |
| P3-012 | Deprecate old endpoints (not remove yet) | Add deprecation headers; log usage | P3-009 |

### 3.3 Orchestrator Refactoring

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P3-013 | Update `SDKOrchestrator` to use PilotSpaceAgent | Delegates conversational requests | P3-001 |
| P3-014 | Remove migrated agents from registry | GhostText stays; others removed | P3-006 to P3-008 |
| P3-015 | Update agent registration in `container.py` | Registers PilotSpaceAgent + 3 subagents | P3-014 |

---

## Phase 4: Frontend Architecture

**Duration Estimate**: Sprint 5-6 (4 weeks)
**Dependencies**: Phase 3 API endpoints ready
**Priority**: High

### 4.1 Unified PilotSpaceStore

**Files to Create:**
```
frontend/src/stores/ai/
├── PilotSpaceStore.ts         # Unified store (new)
├── types/
│   ├── conversation.ts        # Message, Task, Approval types
│   ├── skills.ts              # Skill definitions
│   └── events.ts              # SSE event types
```

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies |
|----|------|---------------------|--------------|
| P4-001 | Create `PilotSpaceStore` class | Implements interface from architecture doc | P3-009 |
| P4-002 | Implement conversation state | Messages, streaming content, session ID | P4-001 |
| P4-003 | Implement task state | Task map, active/completed computed | P4-001 |
| P4-004 | Implement approval state | Pending approvals, approve/reject actions | P4-001 |
| P4-005 | Implement context state | Note/issue/project context | P4-001 |
| P4-006 | Implement actions | sendMessage, setContext, abort, clear | P4-001 |
| P4-007 | Add SSE streaming integration | Uses existing SSEClient | P4-001 |
| P4-008 | Add skill/agent definitions | Static definitions for UI menus | P4-001 |

**Code Pattern for P4-001:**
```typescript
// frontend/src/stores/ai/PilotSpaceStore.ts
import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient } from '@/lib/sse-client';

export class PilotSpaceStore {
  // Conversation
  messages: ChatMessage[] = [];
  isStreaming = false;
  streamContent = '';
  sessionId: string | null = null;
  error: string | null = null;

  // Tasks
  tasks = new Map<string, AgentTask>();
  get activeTasks() { return [...this.tasks.values()].filter(t => t.status === 'in_progress'); }
  get completedTasks() { return [...this.tasks.values()].filter(t => t.status === 'completed'); }

  // Approvals
  pendingApprovals: ApprovalRequest[] = [];
  get hasUnresolvedApprovals() { return this.pendingApprovals.length > 0; }

  // Context
  noteContext: NoteContext | null = null;
  issueContext: IssueContext | null = null;
  activeSkill: string | null = null;
  skillArgs: string | null = null;
  mentionedAgents: string[] = [];

  private client: SSEClient | null = null;

  constructor(private rootStore: AIStore) {
    makeAutoObservable(this);
  }

  async sendMessage(content: string): Promise<void> {
    // ... implementation
  }

  // ... other methods
}
```

### 4.2 ChatView Component Tree ✅ COMPLETED

> **Completed**: 2026-01-27
> **Files Created**: 25 components
> **Location**: `frontend/src/features/ai/ChatView/`

**Files Created:**
```
frontend/src/features/ai/ChatView/
├── ChatView.tsx                    # Main container ✅
├── ChatHeader.tsx                  # Title, status, task badges ✅
├── MessageList/
│   ├── MessageList.tsx            # Auto-scrolling container ✅
│   ├── MessageGroup.tsx           # Groups by role ✅
│   ├── UserMessage.tsx            # User bubbles ✅
│   ├── AssistantMessage.tsx       # AI bubbles with markdown ✅
│   ├── ToolCallList.tsx           # Tool call displays ✅
│   └── StreamingContent.tsx       # Streaming indicator ✅
├── TaskPanel/
│   ├── TaskPanel.tsx              # Collapsible panel ✅
│   ├── TaskList.tsx               # Tabbed list ✅
│   ├── TaskItem.tsx               # Task cards with status ✅
│   └── TaskSummary.tsx            # Progress bar ✅
├── ApprovalOverlay/
│   ├── ApprovalOverlay.tsx        # Floating indicator ✅
│   ├── ApprovalDialog.tsx         # Approval modal ✅
│   ├── IssuePreview.tsx           # Issue preview cards ✅
│   ├── ContentDiff.tsx            # Diff viewer ✅
│   └── GenericJSON.tsx            # JSON display ✅
├── ChatInput/
│   ├── ChatInput.tsx              # Auto-resizing textarea ✅
│   ├── ContextIndicator.tsx       # Context badges ✅
│   ├── SkillMenu.tsx              # \skill searchable menu ✅
│   └── AgentMenu.tsx              # @agent searchable menu ✅
├── types.ts                        # TypeScript definitions ✅
├── constants.ts                    # 8 skills + 3 agents ✅
├── index.ts                        # Public exports ✅
├── README.md                       # Documentation ✅
└── ChatView.example.tsx            # 8 usage examples ✅
```

**Features Delivered:**

| Feature | Implementation |
|---------|---------------|
| **Messages** | User/assistant bubbles with avatars, markdown, auto-scroll |
| **Streaming** | Animated cursor, incremental content display |
| **Tool Calls** | Collapsible displays with status indicators |
| **Skills** | 8 skills with `\skill-name` trigger and Command menu |
| **Agents** | 3 agents with `@agent-name` trigger and Command menu |
| **Tasks** | Real-time progress panel with tabs and progress bar |
| **Approvals** | Floating indicator, queue with specialized previews (DD-003) |
| **Context** | Note/issue/project badges with dismiss |

**Skills Defined (8):**
- `extract-issues`, `enhance-issue`, `recommend-assignee`, `find-duplicates`
- `decompose-tasks`, `generate-diagram`, `improve-writing`, `summarize`

**Agents Defined (3):**
- `pr-review`, `ai-context`, `doc-generator`

**Technical Standards Met:**
- TypeScript strict types with interfaces
- MobX `observer()` pattern for reactivity
- shadcn/ui Command, Dialog, Collapsible, ScrollArea patterns
- WCAG 2.2 AA accessibility (keyboard nav, ARIA, touch targets)
- All files <700 lines, no TODOs/placeholders

**Tasks:**

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P4-009 | Create ChatView container | ✅ Done | `ChatView.tsx` with full integration |
| P4-010 | Create ChatHeader component | ✅ Done | `ChatHeader.tsx` with badges |
| P4-011 | Create MessageList component tree | ✅ Done | 6 components in `MessageList/` |
| P4-012 | Create TaskPanel component | ✅ Done | 4 components in `TaskPanel/` |
| P4-013 | Create ApprovalOverlay component | ✅ Done | 5 components in `ApprovalOverlay/` |
| P4-014 | Create ChatInput component | ✅ Done | Auto-resizing textarea |
| P4-015 | Create SkillMenu component | ✅ Done | Command-based searchable menu |
| P4-016 | Create AgentMenu component | ✅ Done | Command-based searchable menu |

### 4.3 Store Migration

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P4-017 | Update AIStore to include PilotSpaceStore | Add as property alongside existing stores | P4-001 | ⬜ |
| P4-018 | Create migration path for IssueExtractionStore | Redirect to PilotSpaceStore for new features | P4-001 | ⬜ |
| P4-019 | Create migration path for ConversationStore | Redirect to PilotSpaceStore for new features | P4-001 | ⬜ |
| P4-020 | Deprecate siloed stores (not remove yet) | Add deprecation warnings; log usage | P4-017 | ⬜ |

### 4.4 NoteCanvas Integration

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P4-021 | Add ChatView sidebar to NoteCanvas | Toggleable panel; preserves GhostText | P4-001, P4-009 ✅ | ⬜ |
| P4-022 | Implement `\skill` detection in editor | Triggers SkillMenu on `\` keystroke | P4-015 ✅ | ⬜ |
| P4-023 | Implement `@agent` detection in editor | Triggers AgentMenu on `@` keystroke | P4-016 ✅ | ⬜ |
| P4-024 | Connect selection context to PilotSpaceStore | Updates noteContext on selection | P4-005 | ⬜ |

### 4.5 UI-Backend Integration (NEW)

> **Purpose**: Wire ChatView components to backend `/api/v1/ai/chat` endpoint

**Integration Architecture:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UI-BACKEND INTEGRATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ChatView (✅ Done)          PilotSpaceStore (P4-001)        Backend         │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐  │
│  │ ChatInput       │───────▶│ sendMessage()   │───────▶│ POST /ai/chat   │  │
│  │ • \skill menu   │        │                 │        │ (P3-009)        │  │
│  │ • @agent menu   │        │ SSE streaming   │◀───────│                 │  │
│  └─────────────────┘        └─────────────────┘        │ PilotSpaceAgent │  │
│           │                         │                  │ (P3-001)        │  │
│           ▼                         ▼                  └─────────────────┘  │
│  ┌─────────────────┐        ┌─────────────────┐                             │
│  │ MessageList     │◀───────│ messages[]      │                             │
│  │ • UserMessage   │        │ streamContent   │                             │
│  │ • AssistantMsg  │        │ toolCalls[]     │                             │
│  │ • ToolCallList  │        └─────────────────┘                             │
│  └─────────────────┘                                                        │
│           │                         │                                       │
│           ▼                         ▼                                       │
│  ┌─────────────────┐        ┌─────────────────┐                             │
│  │ TaskPanel       │◀───────│ tasks Map       │                             │
│  │ ApprovalOverlay │◀───────│ pendingApprovals│                             │
│  └─────────────────┘        └─────────────────┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**SSE Event Mapping:**

| Backend Event | Store Update | UI Component |
|---------------|--------------|--------------|
| `message_start` | `isStreaming = true` | StreamingContent shows cursor |
| `text_delta` | `streamContent += delta` | AssistantMessage updates |
| `tool_use` | `toolCalls.push(tool)` | ToolCallList renders |
| `tool_result` | `toolCalls[id].output = result` | ToolCallItem updates status |
| `task_progress` | `tasks.set(id, task)` | TaskPanel updates |
| `approval_request` | `pendingApprovals.push(req)` | ApprovalOverlay shows |
| `message_stop` | `isStreaming = false; messages.push()` | MessageList finalizes |
| `error` | `error = message` | ChatView shows error toast |

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P4-025 | Wire ChatInput to PilotSpaceStore.sendMessage | Enter/submit triggers API call | P4-001, P4-014 ✅ | ⬜ |
| P4-026 | Implement SSE event handlers in PilotSpaceStore | All 8 event types handled correctly | P4-001, P3-009 | ⬜ |
| P4-027 | Wire MessageList to store.messages | Auto-scroll, streaming content display | P4-001, P4-011 ✅ | ⬜ |
| P4-028 | Wire TaskPanel to store.tasks | Real-time progress updates | P4-001, P4-012 ✅ | ⬜ |
| P4-029 | Wire ApprovalOverlay to store.pendingApprovals | Approval queue, approve/reject actions | P4-001, P4-013 ✅ | ⬜ |
| P4-030 | Implement skill invocation flow | `\skill` → sendMessage with skill context | P4-001, P4-015 ✅ | ⬜ |
| P4-031 | Implement agent mention flow | `@agent` → sendMessage with agent context | P4-001, P4-016 ✅ | ⬜ |
| P4-032 | Add error boundary and retry logic | Graceful error handling, reconnection | P4-001 | ⬜ |

**Integration Test Checklist:**
- [ ] User sends message → appears in MessageList → streams response
- [ ] User triggers `\extract-issues` → skill executes → results display
- [ ] User triggers `@pr-review` → subagent spawns → streams output
- [ ] Tool call appears → status updates → result shows
- [ ] Approval request → dialog opens → approve/reject works
- [ ] Task created → appears in TaskPanel → status updates
- [ ] Error occurs → toast shows → retry option works

---

## Phase 5: Integration & Testing

**Duration Estimate**: Sprint 7 (2 weeks)
**Dependencies**: Phases 1-4 complete
**Priority**: High

### 5.1 End-to-End Testing

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P5-001 | E2E test: Skill invocation via ChatView | User triggers `\extract-issues`, sees results | P4-030 | ⬜ |
| P5-002 | E2E test: Subagent invocation via ChatView | User triggers `@pr-review`, sees streaming output | P4-031 | ⬜ |
| P5-003 | E2E test: Approval flow | User extracts issues, approves subset, issues created | P4-029 | ⬜ |
| P5-004 | E2E test: Session resumption | User closes/reopens chat, context preserved | P4-001 | ⬜ |
| P5-005 | E2E test: Task tracking | User sees task list, progress updates | P4-028 | ⬜ |
| P5-006 | E2E test: Error recovery | Network failure → reconnect → resume | P4-032 | ⬜ |

### 5.2 Performance Validation

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P5-007 | Benchmark GhostText latency | <2s p95 maintained | P3-009 | ⬜ |
| P5-008 | Benchmark skill invocation latency | <10s for simple skills | P3-009 | ⬜ |
| P5-009 | Benchmark subagent streaming | First token <5s, continuous stream | P3-009 | ⬜ |
| P5-010 | Load test concurrent sessions | 100 concurrent users, no degradation | P3-009 | ⬜ |

### 5.3 Documentation Updates

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P5-011 | Update architecture documentation | Reflects implemented state | All phases | ⬜ |
| P5-012 | Create skill development guide | How to create custom skills | P2-009 | ⬜ |
| P5-013 | Create subagent development guide | How to add new subagents | P3-008 | ⬜ |
| P5-014 | Update API documentation | New /ai/chat endpoint documented | P3-009 | ⬜ |
| P5-015 | Create ChatView integration guide | How to extend ChatView components | P4-032 | ⬜ |

### 5.4 Cleanup & Deprecation

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P5-016 | Remove deprecated agent files | IssueExtractorAgent, etc. after migration verified | P5-001 | ⬜ |
| P5-017 | Remove deprecated store files | IssueExtractionStore, etc. after migration verified | P5-001 | ⬜ |
| P5-018 | Remove deprecated API endpoints | Old /extract-issues, etc. after traffic migrated | P5-001 | ⬜ |
| P5-019 | Clean up unused dependencies | Remove packages no longer needed | P5-016 | ⬜ |
| P5-020 | Final architecture audit | Verify all components align with target architecture | All | ⬜ |

---

## Phase 6: Polish & Refinement

**Duration Estimate**: Sprint 8-9 (4 weeks)
**Dependencies**: Phase 5 complete
**Priority**: Medium (post-MVP enhancements)

### 6.1 UI/UX Refinement

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-001 | Add loading skeletons to MessageList | Shimmer effect while streaming initializes | P4-027 | ⬜ |
| P6-002 | Add empty state illustrations | Friendly onboarding for new users | P4-009 | ⬜ |
| P6-003 | Implement message reactions | Thumbs up/down on assistant messages | P4-011 | ⬜ |
| P6-004 | Add copy-to-clipboard for code blocks | One-click copy with toast confirmation | P4-011 | ⬜ |
| P6-005 | Implement message regeneration | "Regenerate" button on assistant messages | P4-011, P4-001 | ⬜ |
| P6-006 | Add conversation branching UI | Fork conversation from any message | P4-001 | ⬜ |

### 6.2 Animations & Transitions

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-007 | Add message entrance animations | Slide-in with fade for new messages | P4-011 | ⬜ |
| P6-008 | Animate streaming cursor | Blinking cursor during text generation | P4-011 | ⬜ |
| P6-009 | Add TaskPanel expand/collapse animation | Smooth accordion transition | P4-012 | ⬜ |
| P6-010 | Animate ApprovalOverlay entrance | Slide-up with backdrop fade | P4-013 | ⬜ |
| P6-011 | Add skill/agent menu transitions | Popover with scale animation | P4-015, P4-016 | ⬜ |
| P6-012 | Implement progress bar animations | Smooth width transitions for tasks | P4-012 | ⬜ |

### 6.3 Error States & Edge Cases

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-013 | Design offline state UI | Show offline indicator, queue messages | P4-032 | ⬜ |
| P6-014 | Add rate limit handling | Show cooldown timer, suggest alternatives | P4-032 | ⬜ |
| P6-015 | Implement session expired dialog | Prompt to start new session or retry | P4-001 | ⬜ |
| P6-016 | Add API key missing state | Guide user to settings with clear CTA | P4-001 | ⬜ |
| P6-017 | Handle long-running operations | Show estimated time, allow cancellation | P4-028 | ⬜ |
| P6-018 | Add context limit warning | Warn when approaching token limit | P4-001 | ⬜ |

### 6.4 Accessibility Enhancements

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-019 | Add screen reader announcements | Live regions for new messages, status changes | P4-011 | ⬜ |
| P6-020 | Implement focus management | Focus trap in dialogs, restore on close | P4-013 | ⬜ |
| P6-021 | Add keyboard shortcuts | Cmd+Enter to send, Esc to cancel, etc. | P4-014 | ⬜ |
| P6-022 | Ensure color contrast compliance | WCAG 2.2 AA for all text/backgrounds | All P4 | ⬜ |
| P6-023 | Add reduced motion support | Respect `prefers-reduced-motion` | P6-007 to P6-012 | ⬜ |
| P6-024 | Implement high contrast mode | Support `forced-colors` media query | All P4 | ⬜ |

### 6.5 Theming & Responsiveness

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-025 | Ensure dark mode consistency | All ChatView components follow theme | All P4 | ⬜ |
| P6-026 | Add mobile responsive layout | ChatView works on 375px+ screens | P4-009 | ⬜ |
| P6-027 | Implement collapsible sidebar mode | ChatView as overlay on mobile | P4-021 | ⬜ |
| P6-028 | Add touch gesture support | Swipe to dismiss, pull to refresh | P4-009 | ⬜ |
| P6-029 | Optimize for tablet layout | Two-column layout for iPad | P4-009 | ⬜ |

### 6.6 Performance Optimization

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-030 | Virtualize MessageList | Handle 1000+ messages without lag | P4-011 | ⬜ |
| P6-031 | Lazy load message attachments | Images/files load on scroll into view | P4-011 | ⬜ |
| P6-032 | Optimize re-renders | Memoize expensive computations | All P4 | ⬜ |
| P6-033 | Add message pagination | Load older messages on scroll up | P4-011, P4-001 | ⬜ |
| P6-034 | Implement connection pooling | Reuse SSE connections when possible | P4-026 | ⬜ |
| P6-035 | Add response caching | Cache skill results for repeated queries | P4-001 | ⬜ |

### 6.7 Advanced Features

**Tasks:**

| ID | Task | Acceptance Criteria | Dependencies | Status |
|----|------|---------------------|--------------|--------|
| P6-036 | Add conversation search | Search within conversation history | P4-001 | ⬜ |
| P6-037 | Implement conversation export | Export as Markdown, JSON, or PDF | P4-001 | ⬜ |
| P6-038 | Add conversation templates | Save/load conversation starters | P4-001 | ⬜ |
| P6-039 | Implement multi-model selector | Switch between Haiku/Sonnet/Opus | P4-014 | ⬜ |
| P6-040 | Add usage analytics dashboard | Show token usage, cost per conversation | P4-001 | ⬜ |
| P6-041 | Implement conversation sharing | Generate shareable link for conversations | P4-001 | ⬜ |

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SDK integration complexity | Medium | High | Start with single skill migration; validate pattern before scaling |
| Session state corruption | Medium | High | Implement checkpointing early; automatic recovery |
| Frontend performance regression | Low | Medium | Incremental migration; feature flags for rollback |
| Breaking changes during migration | Medium | Medium | Maintain backward compatibility; deprecate before remove |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Extended migration timeline | Medium | Medium | Phase-based delivery; each phase delivers value |
| User disruption | Low | High | Feature flags; gradual rollout; A/B testing |
| Testing gaps | Medium | Medium | E2E tests per phase; automated regression |

---

## Success Criteria

### Phase Completion Criteria

| Phase | Criteria |
|-------|----------|
| **Phase 1** | SDK configuration working; CLAUDE.md loaded; sandbox provisioned |
| **Phase 2** | All 8 skills migrated; skill invocation via SDK working |
| **Phase 3** | PilotSpaceAgent streaming; /ai/chat endpoint live; subagents invokable |
| **Phase 4** | ChatView component complete; PilotSpaceStore integrated; skill/agent menus working |
| **Phase 5** | All E2E tests passing; performance benchmarks met; documentation updated |
| **Phase 6** | Animations smooth; accessibility audit passed; mobile responsive; dark mode consistent |

### Architecture Alignment Criteria

| Principle | Validation |
|-----------|------------|
| GhostText independent | Still <2s latency; no regression |
| Skills over simple agents | 8 skills operational; old agents deprecated |
| Subagents for complex tasks | PRReview, AIContext, DocGen as subagents |
| Task-driven execution | Task list visible in UI; progress tracked |
| Human-in-the-loop | Approval flow working; critical actions require approval |
| Claude Agent SDK native | Using SDK's skill loading, builtin tools, sandbox |

---

## Appendix: Component Tracing Results

### Current Backend Agents (13 Active)

| Agent | File | Type | Migration Target |
|-------|------|------|-----------------|
| GhostTextAgent | `ghost_text_agent.py` | Streaming | Keep (fast path) |
| MarginAnnotationAgentSDK | `margin_annotation_agent_sdk.py` | SDK | Skill: margin-annotation |
| IssueExtractorAgent | `issue_extractor_sdk_agent.py` | SDK | Skill: extract-issues |
| IssueEnhancerAgent | `issue_enhancer_agent_sdk.py` | SDK | Skill: enhance-issue |
| AssigneeRecommenderAgent | `assignee_recommender_agent_sdk.py` | SDK | Skill: recommend-assignee |
| DuplicateDetectorAgent | `duplicate_detector_agent_sdk.py` | SDK | Skill: find-duplicates |
| AIContextAgent | `ai_context_agent.py` | Streaming | Subagent: ai-context |
| ConversationAgent | `conversation_agent_sdk.py` | Streaming | Merged into PilotSpaceAgent |
| PRReviewAgent | `pr_review_agent.py` | Streaming | Subagent: pr-review |
| CommitLinkerAgent | `commit_linker_agent_sdk.py` | SDK | Skill: link-commits |
| DocGeneratorAgent | `doc_generator_agent.py` | SDK | Subagent: doc-generator |
| TaskDecomposerAgent | `task_decomposer_agent.py` | SDK | Skill: decompose-tasks |
| DiagramGeneratorAgent | `diagram_generator_agent.py` | SDK | Skill: generate-diagram |

### Current Frontend Stores (9 Active)

| Store | File | Migration Target |
|-------|------|-----------------|
| GhostTextStore | `GhostTextStore.ts` | Keep (independent) |
| MarginAnnotationStore | `MarginAnnotationStore.ts` | Migrate to PilotSpaceStore |
| AIContextStore | `AIContextStore.ts` | Migrate to PilotSpaceStore |
| IssueExtractionStore | `IssueExtractionStore.ts` | Migrate to PilotSpaceStore |
| ConversationStore | `ConversationStore.ts` | Migrate to PilotSpaceStore |
| PRReviewStore | `PRReviewStore.ts` | Migrate to PilotSpaceStore |
| ApprovalStore | `ApprovalStore.ts` | Migrate to PilotSpaceStore |
| AISettingsStore | `AISettingsStore.ts` | Keep (configuration) |
| CostStore | `CostStore.ts` | Keep (analytics) |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.3.0 | 2026-01-27 | Principal AI Systems Architect | Added Phase 6: Polish & Refinement (41 tasks across 7 categories) |
| 1.2.0 | 2026-01-27 | Principal AI Systems Architect | Added Phase 4.5 UI-Backend Integration, Critical Path, Cleanup tasks |
| 1.1.0 | 2026-01-27 | Principal AI Systems Architect | Phase 4.2 complete: 25 ChatView components created |
| 1.0.0 | 2026-01-27 | Principal AI Systems Architect | Initial remediation plan |
