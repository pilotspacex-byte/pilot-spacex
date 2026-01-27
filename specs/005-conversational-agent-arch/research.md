# Research: Conversational Agent Architecture Migration

**Branch**: `005-conversational-agent-arch`
**Date**: 2026-01-27
**Status**: Complete

## Overview

This document captures research findings for migrating PilotSpace from a siloed agent architecture to a centralized conversational agent architecture using Claude Agent SDK.

## 1. Claude Agent SDK Integration Patterns

### 1.1 SDK Core Concepts

| Concept | Description | PilotSpace Usage |
|---------|-------------|------------------|
| **Skills** | Lightweight prompt-based capabilities in SKILL.md files | 8 skills for issue extraction, writing improvement, etc. |
| **Subagents** | Complex multi-turn agents via Task tool | 3 subagents for PR review, AI context, doc generation |
| **Tools** | SDK builtin tools (Read, Write, Bash, etc.) | Restricted per agent/skill purpose |
| **Hooks** | Pre/Post tool execution callbacks | PreToolUse for approval interception |
| **Sessions** | Persistent conversation context | Resume, fork for multi-session workflows |
| **Sandbox** | Isolated execution environment | Per-workspace isolation with read-only base skills |

### 1.2 Skill File Format (SKILL.md)

```yaml
---
name: skill-name
description: >
  Brief description shown in command menu.
---

# Skill Name

## Quick Start

Brief overview of when and how to use this skill.

## Workflow

1. Step one
2. Step two
3. Step three

## Output Format

Structured output specification (JSON schema, Markdown, etc.)

## Examples

@EXAMPLES.md for annotated examples.
```

**Key Findings**:
- Skills are loaded from `.claude/skills/{skill-name}/SKILL.md`
- YAML frontmatter provides metadata for menu display
- Workflow section guides SDK behavior
- Output Format section ensures structured responses

### 1.3 Agent Definition Format

```python
from claude_agent_sdk import AgentDefinition

SUBAGENT = AgentDefinition(
    description="Expert code review for quality, security, and best practices",
    prompt="""You are an expert code reviewer...

    ## Tools Available
    - Read: Read file contents
    - Grep: Search codebase
    - Glob: Find files by pattern

    ## Output Format
    ...
    """,
    tools=["Read", "Grep", "Glob"],
    model="opus",  # opus for complex analysis, sonnet for standard tasks
)
```

**Key Findings**:
- AgentDefinition is the SDK's native format for subagents
- Tools list restricts available tools for the subagent
- Model selection affects quality/cost tradeoff
- Prompt includes tool guidance and output format

### 1.4 Permission Handling (canUseTool)

```python
async def can_use_tool(
    tool_name: str,
    tool_input: dict,
    context: PermissionContext,
) -> PermissionResult:
    """SDK callback for tool permission decisions."""

    action_class = classify_action(tool_name, tool_input)

    if action_class == ActionClass.SAFE:
        return PermissionResult.ALLOW

    if action_class == ActionClass.CRITICAL:
        # Queue for human approval
        approval_id = await queue_approval(tool_name, tool_input, context)
        return PermissionResult.DENY_WITH_MESSAGE(
            f"Action requires approval. ID: {approval_id}"
        )

    return PermissionResult.ASK_USER
```

**Key Findings**:
- `canUseTool` callback intercepts tool execution
- Maps to existing ApprovalService classification
- Three outcomes: ALLOW, DENY_WITH_MESSAGE, ASK_USER
- Integrates with human-in-the-loop per DD-003

### 1.5 Session Management

```python
# Capture session ID from init message
async for message in query(input_text, options):
    if message.type == "init":
        session_id = message.session_id
        await persist_session(user_id, workspace_id, session_id)
    yield transform_message(message)

# Resume session
options.resume = stored_session_id

# Fork session for alternatives
options.fork_session = True
```

**Key Findings**:
- Session ID captured from `init` message
- `resume` parameter reconnects to previous context
- `fork_session` creates branch for exploring alternatives
- Sessions enable multi-session workflows per FR-018-021

## 2. SSE Streaming Architecture

### 2.1 Event Types

| Event Type | Description | Frontend Handler |
|------------|-------------|------------------|
| `message_start` | Conversation turn begins | `isStreaming = true` |
| `content_block_start` | Content block begins | Initialize block |
| `text_delta` | Incremental text | `streamContent += delta` |
| `tool_use` | Tool invocation | `toolCalls.push(tool)` |
| `tool_result` | Tool execution result | Update tool status |
| `task_progress` | Task status update | Update TaskPanel |
| `approval_request` | Human approval needed | Show ApprovalOverlay |
| `message_stop` | Conversation turn ends | Finalize message |
| `error` | Error occurred | Show error toast |

### 2.2 Backend Implementation

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/ai/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Unified conversational AI endpoint."""

    agent = PilotSpaceAgent(
        key_storage=get_key_storage(),
        permission_handler=get_permission_handler(),
        session_handler=get_session_handler(),
    )

    async def generate():
        async for event in agent.stream(
            input_text=request.message,
            context=request.context,
        ):
            yield f"event: {event.type}\ndata: {event.json()}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### 2.3 Frontend SSE Client

```typescript
class SSEClient {
  private eventSource: EventSource | null = null;

  connect(url: string, handlers: EventHandlers): void {
    this.eventSource = new EventSource(url);

    this.eventSource.addEventListener('message_start', (e) => {
      handlers.onMessageStart(JSON.parse(e.data));
    });

    this.eventSource.addEventListener('text_delta', (e) => {
      handlers.onTextDelta(JSON.parse(e.data));
    });

    // ... other event handlers

    this.eventSource.onerror = (e) => {
      handlers.onError(e);
      this.reconnect();
    };
  }

  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
  }
}
```

**Key Findings**:
- SSE is unidirectional (server → client)
- EventSource API handles reconnection automatically
- Custom events via `event:` field in SSE protocol
- Headers disable buffering for real-time streaming

## 3. Skill Migration Analysis

### 3.1 Migration Complexity Matrix

| Current Agent | Target Skill | Complexity | Notes |
|--------------|--------------|------------|-------|
| IssueExtractorAgent | extract-issues | Medium | JSON output with DD-048 confidence |
| IssueEnhancerAgent | enhance-issue | Low | Single prompt transformation |
| AssigneeRecommenderAgent | recommend-assignee | Medium | Needs expertise matrix |
| DuplicateDetectorAgent | find-duplicates | High | pgvector integration |
| TaskDecomposerAgent | decompose-tasks | Medium | Dependency modeling |
| DiagramGeneratorAgent | generate-diagram | Low | Mermaid output |
| N/A (new) | improve-writing | Low | Text transformation |
| N/A (new) | summarize | Low | Content summarization |

### 3.2 High-Complexity: find-duplicates

**Challenge**: Requires pgvector semantic search integration.

**Solution**:
1. Skill invokes MCP tool for vector search
2. MCP tool (`pilotspace_search`) queries pgvector
3. Results returned to skill for ranking
4. Skill formats output with similarity scores

```yaml
---
name: find-duplicates
description: >
  Find potentially duplicate issues using semantic similarity.
---

# Find Duplicates

## Workflow

1. Read the input issue content
2. Use `pilotspace_search` tool to find similar issues
3. Filter results by similarity threshold (default: 0.85)
4. Rank and format matches with confidence tags

## Tools Required

- pilotspace_search: Semantic search via pgvector
```

### 3.3 Subagent Refactoring

**PRReviewAgent → PRReviewSubagent**:
- Adapts to `AgentDefinition` format
- Tools: Read, Grep, Glob (no write access)
- Model: Opus (for comprehensive analysis)
- Output: Structured review with categories

**AIContextAgent → AIContextSubagent**:
- Multi-turn aggregation workflow
- Tools: Read, Grep, Glob, WebSearch
- Model: Opus (for context understanding)
- Output: Aggregated context summary

**DocGeneratorAgent → DocGeneratorSubagent**:
- Documentation generation from code
- Tools: Read, Write, Grep
- Model: Sonnet (sufficient for docs)
- Output: Markdown documentation

## 4. Frontend Store Consolidation

### 4.1 Current Store Landscape

| Store | Purpose | Migration Strategy |
|-------|---------|-------------------|
| GhostTextStore | Inline completions | **Keep** (independent fast path) |
| MarginAnnotationStore | AI annotations | Migrate to PilotSpaceStore |
| AIContextStore | Issue context | Migrate to PilotSpaceStore |
| IssueExtractionStore | Issue extraction | Migrate to PilotSpaceStore |
| ConversationStore | Chat history | Migrate to PilotSpaceStore |
| PRReviewStore | PR review state | Migrate to PilotSpaceStore |
| ApprovalStore | Approval queue | Migrate to PilotSpaceStore |
| AISettingsStore | AI configuration | **Keep** (configuration) |
| CostStore | Usage tracking | **Keep** (analytics) |

### 4.2 PilotSpaceStore Interface

```typescript
interface PilotSpaceStore {
  // Conversation State
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  sessionId: string | null;
  error: string | null;

  // Task State
  tasks: Map<string, AgentTask>;
  activeTasks: AgentTask[];      // computed
  completedTasks: AgentTask[];   // computed

  // Approval State
  pendingApprovals: ApprovalRequest[];
  hasUnresolvedApprovals: boolean;  // computed

  // Context State
  noteContext: NoteContext | null;
  issueContext: IssueContext | null;
  activeSkill: string | null;
  skillArgs: string | null;
  mentionedAgents: string[];

  // Actions
  sendMessage(content: string): Promise<void>;
  setContext(context: ConversationContext): void;
  abort(): void;
  clear(): void;
  approveAction(requestId: string): Promise<void>;
  rejectAction(requestId: string, reason?: string): Promise<void>;
}
```

### 4.3 MobX Implementation Pattern

```typescript
import { makeAutoObservable, runInAction } from 'mobx';

class PilotSpaceStore {
  messages: ChatMessage[] = [];
  isStreaming = false;
  // ...

  constructor(private rootStore: AIStore) {
    makeAutoObservable(this);
  }

  async sendMessage(content: string): Promise<void> {
    const userMessage = this.createUserMessage(content);

    runInAction(() => {
      this.messages.push(userMessage);
      this.isStreaming = true;
      this.streamContent = '';
      this.error = null;
    });

    try {
      await this.streamResponse(content);
    } catch (error) {
      runInAction(() => {
        this.error = error.message;
      });
    } finally {
      runInAction(() => {
        this.isStreaming = false;
      });
    }
  }
}
```

## 5. API Contract Design

### 5.1 Request Schema

```typescript
interface ChatRequest {
  message: string;
  context: {
    note_id: string | null;
    issue_id: string | null;
    project_id: string | null;
    selected_text: string | null;
    selected_block_ids: string[];
  };
  session_id: string | null;
}
```

### 5.2 SSE Event Schemas

```typescript
// message_start
interface MessageStartEvent {
  type: 'message_start';
  message_id: string;
  session_id: string;
}

// text_delta
interface TextDeltaEvent {
  type: 'text_delta';
  message_id: string;
  delta: string;
}

// tool_use
interface ToolUseEvent {
  type: 'tool_use';
  tool_call_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

// approval_request
interface ApprovalRequestEvent {
  type: 'approval_request';
  request_id: string;
  action_type: string;
  description: string;
  consequences: string;
  affected_entities: Entity[];
  urgency: 'low' | 'medium' | 'high';
  expires_at: string;  // ISO 8601
}

// task_progress
interface TaskProgressEvent {
  type: 'task_progress';
  task_id: string;
  subject: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;  // 0-100
  description?: string;
}
```

## 6. Performance Considerations

### 6.1 GhostText Independence

**Requirement**: GhostText must maintain <2s latency independent of ChatView operations.

**Solution**:
- GhostText uses separate endpoint (`/api/v1/notes/{noteId}/ghost-text`)
- Separate store (GhostTextStore) not affected by migration
- AbortController cancels in-flight requests on continued typing
- Dedicated Haiku model for fast inference

### 6.2 Concurrent Request Handling

**Requirement**: Queue concurrent skill/subagent requests (FR-005a).

**Solution**:
```typescript
class RequestQueue {
  private queue: QueuedRequest[] = [];
  private processing = false;

  async enqueue(request: Request): Promise<void> {
    this.queue.push(request);
    this.notifyUser('queued');

    if (!this.processing) {
      await this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    this.processing = true;

    while (this.queue.length > 0) {
      const request = this.queue.shift()!;
      await this.execute(request);
    }

    this.processing = false;
  }
}
```

### 6.3 Session Context Limits

**Challenge**: Long conversations may exceed context limits.

**Solution**:
- Monitor token usage during streaming
- Trigger automatic compaction when approaching 80% limit
- Preserve essential context (recent messages, active tasks)
- Notify user when compaction occurs (FR-021)

## 7. Security Considerations

### 7.1 RLS Enforcement

- All database queries must pass through RLS policies
- Skill output filtered by workspace membership
- Subagent tool access restricted to user's scope

### 7.2 API Key Security

- BYOK model: Users provide their own API keys
- Keys stored encrypted in Supabase Vault
- Never exposed in logs or error messages
- Session-scoped decryption only

### 7.3 Sandbox Isolation

- Per-workspace sandbox directories
- Read-only base skills mount
- User skills in isolated directories
- No cross-workspace access

## 8. Open Questions Resolved

| Question | Resolution |
|----------|------------|
| How to handle concurrent skill invocation? | Queue with notification (per spec clarification) |
| Which model for each task type? | Opus for complex (PR review, context), Sonnet for standard, Haiku for fast (ghost text) |
| How to migrate existing conversation history? | Session ID mapping; preserve in ConversationStore during transition |
| When to remove deprecated stores? | Phase 5 cleanup after E2E tests pass |

## References

- [Claude Agent SDK Documentation](../../docs/claude-sdk.txt)
- [Target Architecture v1.5.0](../../docs/architect/pilotspace-agent-architecture.md)
- [Remediation Plan v1.3.0](../../docs/architect/agent-architecture-remediation-plan.md)
- [DD-003: Human-in-the-Loop](../../docs/DESIGN_DECISIONS.md)
- [DD-048: AI Confidence Tags](../../docs/DESIGN_DECISIONS.md)
