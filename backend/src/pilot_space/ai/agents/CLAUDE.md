# Agents Layer - PilotSpaceAgent Orchestrator & Subagents

**For AI layer overview, see parent [ai/CLAUDE.md](../CLAUDE.md).**

---

## PilotSpaceAgent: Orchestrator (DD-086)

**Purpose**: Centralized conversational agent routing user requests to skills (single-turn), subagents (multi-turn), or direct responses via MCP tools.

**Class**: `StreamingSDKBaseAgent[ChatInput, ChatOutput]` in `pilotspace_agent.py`

**Interface**: `async def stream(input_data: ChatInput, context: AgentContext) -> AsyncIterator[str]`

**Model**: ModelTier.SONNET (cost-optimized default)

### Constructor Dependencies

| Dependency | Purpose | Lifecycle |
|-----------|---------|-----------|
| tool_registry | 33 tools across 6 servers | Startup |
| provider_selector | Task -> Provider routing + fallbacks | Singleton |
| cost_tracker | Token usage + pricing | Per-request |
| resilient_executor | Retry + circuit breaker | Singleton per provider |
| permission_handler | DD-003 approval workflow | Per-request |
| session_handler | Redis + PostgreSQL durable storage | Singleton |
| space_manager | Workspace sandbox management | Lazy |
| subagents | PRReviewSubagent, DocGeneratorSubagent | On-demand |
| key_storage | Supabase Vault for BYOK keys | Singleton |

DI configuration: See `container.py:_create_pilotspace_agent`

### Startup Sequence

1. Load environment (config.py) -> DB pool -> Redis client
2. Create tool_registry (MCP servers) -> provider_selector (routing table)
3. Create PilotSpaceAgent (Singleton, lazy on first chat)
4. Skill discovery (auto-load `.claude/skills/`) -> Mount SSE routers

---

## Stream Method

1. Get API key (BYOK per workspace)
2. Build system prompt with dynamic context + role skill injection
3. Configure MCP servers (33 tools)
4. Create ClaudeSDKClient (in-process)
5. Stream SDK responses -> transform to SSE -> yield
6. Handle errors (ProviderUnavailableError) -> SSE error event
7. Cleanup active clients

Max tokens per session: 8,000 (configurable)

---

## Message Transformation Pipeline

**Transformer**: `transform_sdk_message()` in `pilotspace_stream_utils.py`

**SSE Event Types** (9):

| Event | Source |
|-------|--------|
| message_start, text_delta, tool_use, tool_result | SDK events |
| content_update | Note/issue mutations from tool payloads |
| task_progress, approval_request | Long-running ops |
| message_stop, error | Lifecycle |

**content_update format**: `{type, note_id, blocks: [{block_id, operation, content}]}`

---

## Session Management

**File**: `ai/session/session_manager.py`

**Dual-Store Architecture**:
- **Redis** (30-min TTL): Fast retrieval for active conversations
- **PostgreSQL** (24h TTL): Durable storage, resumption after Redis expiry

**Interface**: `create_session()`, `get_session()` (Redis-first with PostgreSQL fallback), `append_message()`, `delete_session()`

**Resumption**: ChatRequest specifies `resume_session_id` to continue previous conversation.

| Constant | Value |
|----------|-------|
| SESSION_TTL_SECONDS | 86400 (24h, PostgreSQL) |
| REDIS_TTL_SECONDS | 1800 (30min, Redis) |

---

## Approval Workflow (DD-003)

**File**: `ai/sdk/permission_handler.py`

**Classification**:

| Category | Approval | Examples |
|----------|----------|----------|
| Non-destructive | Auto-execute | get_issue, search, add_label, assign, transition |
| Content creation | Configurable | create_issue, create_comment, extract_issues |
| Destructive | Always required | delete_issue, unlink_issue, archive_workspace |

**Interface**: `check_permission(action, tool_call_id, data) -> PermissionResult`

**SSE Flow**: Tool call -> PermissionHandler classifies -> `approval_request` SSE event -> Frontend modal -> User responds via POST `/api/v1/ai/chat/answer` -> SDK continuation -> Tool executes

**Content Creation**: Configurable per workspace via `require_ai_approvals` setting.

---

## Subagents

All extend `StreamingSDKBaseAgent[Input, Output]` with async SSE streaming.

| Subagent | File | Model | Purpose |
|----------|------|-------|---------|
| PRReviewSubagent | `subagents/pr_review_subagent.py` | Opus | 5-aspect review (Architecture, Security, Quality, Performance, Docs) |
| DocGeneratorSubagent | `subagents/doc_generator_subagent.py` | Sonnet | ADR/API/spec generation |

---

## Data Flow: Chat Request -> Response

```
Frontend POST /api/v1/ai/chat
    | (ChatRequest with workspace_id, user_id)
FastAPI Router (ai_chat.py)
    | PilotSpaceAgentDep injection
PilotSpaceAgent.stream(ChatInput)
    | (1) Get API key (BYOK) -> (2) Build system prompt -> (3) Configure MCP
ClaudeSDKClient (in-process)
    | (4) Routes: skill? | subagent? | tool call?
Tool Handler (e.g., note_server.py)
    | (5) Returns operation payload
transform_sdk_message()
    | (6) Converts payload -> SSE content_update event
SSE StreamingResponse
    | (7) Yields text_delta, tool_use, content_update, task_progress, approval_request
Frontend useContentUpdates() Hook
    | (8) Processes content_update -> TipTap mutation + API persist
```

---

## Key Files

| Component | File |
|-----------|------|
| Orchestrator | `ai/agents/pilotspace_agent.py` |
| Base class | `ai/agents/agent_base.py` |
| Stream utils | `ai/agents/pilotspace_stream_utils.py` |
| PR Review | `ai/agents/subagents/pr_review_subagent.py` |
| Doc Generator | `ai/agents/subagents/doc_generator_subagent.py` |
| Permission | `ai/sdk/permission_handler.py` |
| Sessions | `ai/session/session_manager.py` |

---

## Related Documentation

- **AI Layer Parent**: [ai/CLAUDE.md](../CLAUDE.md)
- **MCP Tools**: [mcp/CLAUDE.md](../mcp/CLAUDE.md)
- **Providers**: [providers/CLAUDE.md](../providers/CLAUDE.md)
- **Design Decisions**: DD-086 (centralized agent), DD-003 (approval workflow)
