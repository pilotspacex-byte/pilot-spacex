# AI Agent System

PilotSpace uses a **centralized AI orchestrator** pattern built on the Claude Agent SDK. A single `PilotSpaceAgent` routes user messages to skills, subagents, or direct responses via 33 MCP tools.

## Architecture Overview

```text
User Message
  ↓
POST /api/v1/ai/chat (SSE)
  ↓
PilotSpaceAgent (StreamingSDKBaseAgent)
  ├── 6-Layer System Prompt
  ├── Provider Routing (DD-011)
  ├── 33 MCP Tools (6 servers)
  ├── 24 Skills (auto-discovered)
  ├── 2 Subagents (PR Review, Doc Gen)
  ├── Approval Workflow (DD-003)
  ├── Session Manager (Redis + PostgreSQL)
  └── Resilience (Circuit Breaker + Retry)
  ↓
SSE Stream → Frontend
  ├── text_delta (response text)
  ├── tool_use (MCP tool invocation)
  ├── content_update (note/issue mutation)
  ├── approval_request (human-in-the-loop)
  └── message_stop (end)
```

## PilotSpaceAgent Orchestrator

**File**: `backend/src/pilot_space/ai/agents/pilotspace_agent.py`

The main entry point for all AI interactions. On each request:

1. **Resolve workspace provider** — fetch BYOK API key from Supabase Vault
2. **Build stream config** — materialize role skills, resolve prompt layers, detect skill
3. **Create SDK client** — `ClaudeSDKClient(sdk_options)` with 33 allowed tools
4. **Stream response** — merge SDK events + tool event queue
5. **Transform to SSE** — convert SDK messages to frontend-consumable events
6. **Persist session** — save user + assistant messages to Redis/PostgreSQL

## Provider Routing (DD-011)

Each AI task type routes to the optimal model based on complexity, latency, and cost:

| Task Type       | Provider  | Model                  | SLA    |
| --------------- | --------- | ---------------------- | ------ |
| PR Review       | Anthropic | Claude Opus            | <5min  |
| AI Context      | Anthropic | Claude Opus            | <30s   |
| Code Generation | Anthropic | Claude Sonnet          | <30s   |
| Conversation    | Anthropic | Claude Sonnet          | <30s   |
| Ghost Text      | Anthropic | Claude Haiku           | <1.5s  |
| Embeddings      | OpenAI    | text-embedding-3-large | <500ms |

**Fallback chains**: Each task type has a fallback model (e.g., PR Review: Opus → Sonnet).

## MCP Tool Servers

33 tools across 6 in-process MCP servers:

### pilot-notes (9 tools)

`write_to_note`, `update_note_block`, `enhance_text`, `extract_issues`, `create_issue_from_note`, `link_existing_issues`, `insert_pm_block`, `create_note`, `update_note`

### pilot-notes-content (5 tools)

`search_note_content`, `insert_block`, `remove_block`, `remove_content`, `replace_content`

### pilot-issues (4 tools)

`get_issue`, `search_issues`, `create_issue`, `update_issue`

### pilot-issues-relations (6 tools)

`link_issue_to_note`, `unlink_issue_from_note`, `link_issues`, `unlink_issues`, `add_sub_issue`, `transition_issue_state`

### pilot-projects (5 tools)

`get_project`, `search_projects`, `create_project`, `update_project`, `update_project_settings`

### pilot-comments (4 tools)

`create_comment`, `update_comment`, `search_comments`, `get_comments`

### Tool Execution Pattern

```python
@tool("tool_name", "description", {schema})
async def tool_handler(arg1, arg2):
    workspace_context = get_workspace_context()  # RLS check
    result = await repository.update(...)         # Execute
    return {
        "status": "pending_apply",                # or "pending_approval"
        "operation": "update_issue",
        "payload": {...},
    }
```

## Approval Workflow (DD-003)

| Category         | Approval        | Examples                    |
| ---------------- | --------------- | --------------------------- |
| Non-destructive  | Auto-execute    | search, get, suggestions    |
| Content creation | Configurable    | create_issue, write_to_note |
| Destructive      | Always required | delete, unlink, archive     |

**Flow**: Tool returns `pending_approval` → SSE `approval_request` → Frontend modal → User approves/rejects → Agent continues.

## 6-Layer System Prompt

1. **Identity** — "You are PilotSpace AI..."
2. **Safety + Tools + Style** — Approval rules, tool descriptions
3. **Role Adaptation** — Developer/PM/Architect/Tester-specific guidance
4. **Workspace Context** — Workspace name, projects, team
5. **Session State** — Memory, conversation summary, pending approvals
6. **Intent-Based Rules** — Extracted from user message classification

## Skills System

24 YAML-defined skills auto-discovered from `.claude/skills/`:

- `/extract-issues` — Issue extraction from note selection
- `/enhance-issue` — Add details, labels, priority
- `/decompose-tasks` — Break into subtasks
- `/find-duplicates` — Semantic duplicate detection
- `/adr-lite` — Auto-generate architecture decision records

Skills are **single-turn** and **stateless**. For multi-turn tasks, the agent delegates to **subagents**.

## Subagents

| Subagent             | Model         | Purpose                                                             |
| -------------------- | ------------- | ------------------------------------------------------------------- |
| PRReviewSubagent     | Claude Opus   | 5-aspect review: architecture, security, quality, performance, docs |
| DocGeneratorSubagent | Claude Sonnet | ADR, API docs, README, inline comments                              |

## Session Management

**Dual-store architecture**:

- **Redis** (30-min TTL): Fast retrieval for active conversations
- **PostgreSQL** (24h TTL): Durable storage, resumption after Redis expiry

Sessions track: messages, tool calls, token usage, costs, and approval state.

## Resilience

### Circuit Breaker (per provider)

```text
CLOSED (normal) → 3 failures → OPEN (fail-fast) → 30s → HALF_OPEN (probe)
                                                              ↓ success
                                                           CLOSED
```

### Retry Logic

- Max retries: 3
- Exponential backoff: 1s → 4s → 16s (with ±30% jitter)
- Retries on timeout and rate limit errors only

### Cost Tracking

Per-request tracking of input/output tokens and USD cost. Budget alerts trigger at 90% of workspace limit.
