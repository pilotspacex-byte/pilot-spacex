# AI Layer Development Guide - Pilot Space

**For project overview and general context, see main CLAUDE.md at project root.**

## Quick Reference

### Quality Gates (Run Before Every Commit)

```bash
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

All three gates must PASS. No exceptions.

### Critical Files & Entry Points

| Component | File | Purpose |
|-----------|------|---------|
| Orchestrator | `ai/agents/pilotspace_agent.py` | Main agent routing to skills/subagents |
| Providers | `ai/providers/provider_selector.py` | Task-based provider routing + fallback chain |
| Resilience | `ai/infrastructure/resilience.py` | Retry + circuit breaker patterns |
| Approvals | `ai/sdk/permission_handler.py` | Human-in-the-loop for DD-003 |
| Sessions | `ai/session/session_manager.py` | Redis hot cache + PostgreSQL durable |
| Skills | `ai/skills/skill_discovery.py` | Auto-discovery from .claude/skills/ |
| Cost Tracking | `ai/infrastructure/cost_tracker.py` | Per-request token + cost logging |
| Circuit Breaker | `ai/circuit_breaker.py` | Provider resilience pattern |

### Key Constant Values

| Constant | Value | Context |
|----------|-------|---------|
| DEFAULT_MODEL_TIER | ModelTier.SONNET | PilotSpaceAgent default (cost-optimized) |
| SESSION_TTL_SECONDS | 86400 | PostgreSQL durable storage (24 hours) |
| REDIS_TTL_SECONDS | 1800 | Redis hot cache (30 minutes) |
| CIRCUIT_BREAKER_TIMEOUT | 30 seconds | Transition from OPEN to HALF_OPEN |
| FAILURE_THRESHOLD | 3 | Consecutive failures to open circuit |
| MAX_RETRIES | 3 | Exponential backoff attempts |
| BASE_DELAY | 1.0 second | Retry initial delay |
| MAX_DELAY | 60.0 seconds | Retry cap on exponential growth |
| JITTER | 0.3 | Randomization on retry delays |

---

## Architecture Overview

### AI Layer Structure

```
ai/
├── agents/                    # Orchestrator + subagents
│   ├── pilotspace_agent.py   # Main router (DD-086)
│   ├── subagents/
│   │   ├── pr_review_subagent.py        # Multi-turn code review
│   │   └── doc_generator_subagent.py    # ADR/spec generation
│   ├── agent_base.py         # StreamingSDKBaseAgent base class
│   └── pilotspace_stream_utils.py       # SDK message handling
│
├── mcp/                       # MCP Tool Servers (33 tools, 6 servers)
│   ├── note_server.py         # 9 note tools: write_to_note, extract_issues, etc.
│   ├── note_content_server.py # 5 content tools: insert_block, remove_block, etc.
│   ├── issue_server.py        # 4 CRUD + 6 relations = 10 tools
│   ├── issue_relation_server.py # Issue linking tools
│   ├── project_server.py      # 5 project tools
│   ├── comment_server.py      # 4 comment tools
│   └── registry.py            # Tool registry management
│
├── providers/                 # Provider selection & routing
│   ├── provider_selector.py   # Task → Provider routing (DD-011)
│   ├── key_validator.py       # BYOK key verification
│   └── mock.py                # Testing mock providers
│
├── sdk/                       # Claude Agent SDK integration
│   ├── permission_handler.py  # Human-in-the-loop (DD-003)
│   ├── session_handler.py     # Session resumption + storage
│   ├── hooks.py               # SDK lifecycle hooks
│   ├── config.py              # SDK configuration constants
│   └── sandbox_config.py      # Workspace sandbox settings
│
├── session/                   # Session management
│   └── session_manager.py     # Redis (hot) + PostgreSQL (durable)
│
├── skills/                    # Skill system
│   ├── skill_discovery.py     # Auto-discovery from .claude/skills/
│   └── skill_metadata.py      # Skill metadata parsing
│
├── infrastructure/            # Cross-cutting concerns
│   ├── cost_tracker.py        # Token usage + pricing
│   ├── resilience.py          # ResilientExecutor (retry + CB)
│   ├── cache.py               # Redis caching layer
│   ├── rate_limiter.py        # Rate limiting per user/workspace
│   ├── key_storage.py         # BYOK key vault integration
│   └── approval.py            # Approval workflow storage
│
├── circuit_breaker.py         # Circuit breaker pattern
├── exceptions.py              # AI-specific exceptions
├── context.py                 # Workspace context (RLS)
├── telemetry.py               # Analytics + logging
│
├── prompts/                   # Prompt templates
│   ├── issue_extraction.py    # Extract issues from notes
│   ├── pr_review.py          # PR review prompts
│   └── ghost_text.py         # Ghost text completion
│
└── templates/
    ├── skills/               # Skill definitions (YAML)
    ├── role_templates/       # Role-specific personas
    └── rules/                # Confidence/validation rules
```

### Data Flow: Chat Request → Response

```
Frontend POST /api/v1/ai/chat
    ↓ (ChatRequest with workspace_id, user_id)
FastAPI Router (ai_chat.py)
    ↓ PilotSpaceAgentDep injection
PilotSpaceAgent.stream(ChatInput)
    ↓ (1) Get API key from Vault (per-workspace BYOK)
    ↓ (2) Build system prompt + subagent definitions
    ↓ (3) Configure MCP servers + allowed_tools
ClaudeSDKClient (in-process)
    ↓ (4) Routes: skill detected? → skill execution
    ↓       OR: subagent mentioned? → spawn subagent
    ↓       OR: tool call? → MCP tool handler
Tool Handler (e.g., note_server.py)
    ↓ (5) Tool validates + returns operation payload
    ↓       e.g., {"status": "pending_apply", "note_id": "...", "block_id": "...", "operation": "..."}
transform_sdk_message() in pilotspace_note_helpers.py
    ↓ (6) Converts payload → SSE content_update event
    ↓       {"type": "content_update", "note_id": "...", "blocks": [...]}
SSE StreamingResponse
    ↓ (7) Yields text_delta, tool_use, content_update, task_progress, approval_request
Frontend useContentUpdates() Hook
    ↓ (8) Processes content_update → TipTap editor mutation + API call
    ↓ (9) Displays SSE text_delta in chat UI
```

---

## Design Decisions

### DD-086: Centralized Agent Architecture

**Problem**: 13 siloed agents (extraction, enhancement, PR review, etc.) caused:
- Context fragmentation (each agent rebuilds context independently)
- Session proliferation (user sessions spread across multiple backends)
- Cost inefficiency (no prompt caching across related operations)

**Solution**: Single `PilotSpaceAgent` orchestrator with:
- **Skills** (single-turn): `.claude/skills/` YAML → filesystem auto-discovery
- **Subagents** (multi-turn): PRReviewSubagent, DocGeneratorSubagent spawned on-demand
- **Unified SSE stream**: Single connection for all AI events

**Tradeoff**: Orchestrator latency ~200-500ms for routing, offset by unified caching and session management.

### DD-087: Filesystem Skill System

**Why not registry in database?**
- Version control: Skills are code, belong in git
- Zero latency: Loaded at startup, no DB queries for discovery
- IDE support: Developers use familiar YAML editors
- Modification safety: Changes in development branch, never production

**Format**:
```yaml
---
name: extract-issues
description: Detect actionable items from note text
invocable: explicit  # or "auto" for intent detection
---

# Prompt and instructions follow YAML frontmatter
```

**Discovery**: Agent startup scans `.claude/skills/{skill_name}/SKILL.md`, aggregates into SDK.

### DD-011: Provider Routing per Task Type

**Task → Provider Mapping**:

| Task | Provider | Reason | SLA |
|------|----------|--------|-----|
| PR review | Claude Opus | Deep reasoning, cross-aspect references | <5min |
| AI context aggregation | Claude Sonnet | Cost-optimized, sufficient for assembly | <30s |
| Ghost text completion | Gemini Flash | Latency-critical, small token count | <2.5s |
| Embeddings (semantic search) | Gemini gemini-embedding-001 | 768-dim, HNSW optimized | <500ms |

**Fallback Chain**:
```
Try Claude Opus (pr_review) →
  on failure → Try Claude Sonnet →
    on failure → Try Gemini Pro →
      on failure → Queue offline + notify user
```

**Circuit Breaker Integration**: 5 consecutive failures → OPEN state (fail-fast), 30s timeout → HALF_OPEN (probe), 1 success → CLOSED.

### DD-003: Critical-Only Human-in-the-Loop

**Classification Matrix**:

| Action | Category | Approval Required | Handler |
|--------|----------|-------------------|---------|
| Search/Get (read-only) | Non-destructive | No | auto_approve |
| Add label, assign, transition state | Non-destructive | No | auto_approve |
| Create/update issue or comment | Content creation | **Configurable** | request_approval |
| Extract issues from notes | Content creation | **Configurable** | request_approval |
| Delete issue, archive workspace | Destructive | **Always** | require_approval |
| Merge PR, remove user from team | Destructive | **Always** | require_approval |

**Implementation**:
```python
# In PermissionHandler
result = check_permission(action="create_issue", tool_call_id="tc_123")
if result.requires_approval:
    approval_req = ApprovalRequest(
        tool_call_id="tc_123",
        expires_at=now + timedelta(hours=24),
        data={"issue": {...}}
    )
    # Wait for approval_waiter or user SDK tool call
```

---

## PilotSpaceAgent: Orchestrator (DD-086)

### Architecture

**Class**: `StreamingSDKBaseAgent[ChatInput, ChatOutput]`

**Key Method**: `async def stream(input_data: ChatInput, context: AgentContext) → AsyncIterator[str]`

```python
class PilotSpaceAgent(StreamingSDKBaseAgent[ChatInput, ChatOutput]):
    """Main orchestrator agent — routes to skills, subagents, or direct responses."""

    AGENT_NAME = "pilotspace_agent"
    DEFAULT_MODEL_TIER = ModelTier.SONNET  # Cost-optimized

    SYSTEM_PROMPT_BASE = """
    You are PilotSpace AI, an embedded assistant in a Note-First SDLC platform.

    ## Tool categories
    **Notes** (9 tools): write_to_note, update_note_block, extract_issues, ...
    **Issues** (10 tools): get_issue, search_issues, create_issue, link_issues, ...
    **Projects** (5 tools): get_project, create_project, update_project, ...
    **Comments** (4 tools): create_comment, update_comment, search_comments, ...

    ## Approval tiers
    - Auto-execute: search/get tools (read-only)
    - Require approval: create/update/link tools (configurable)
    - Always require: unlink/delete tools (destructive)

    Subagents: pr-review, doc-gen
    Return operation payloads; never mutate DB directly.
    """

    SUBAGENT_MAP = {
        "pr-review": "PRReviewSubagent",
        "doc-gen": "DocGeneratorSubagent",
    }
```

### Initialization Flow

**Dependency Injection** (in `container.py`):
```python
pilotspace_agent = providers.Singleton(
    _create_pilotspace_agent,
    tool_registry=tool_registry,
    provider_selector=provider_selector,
    cost_tracker=cost_tracker,
    resilient_executor=resilient_executor,
    permission_handler=permission_handler,
    session_handler=session_handler,
)
```

**Constructor Dependencies**:
| Dependency | Purpose | Initialized |
|-----------|---------|-------------|
| tool_registry | 33 tools across 6 servers | On startup |
| provider_selector | Task → Provider routing + fallbacks | Singleton |
| cost_tracker | Token usage + pricing | Per-request |
| resilient_executor | Retry + circuit breaker | Singleton per provider |
| permission_handler | DD-003 approval workflow | Per-request |
| session_handler | Redis + PostgreSQL durable storage | Singleton |
| space_manager | Workspace sandbox management | Lazy |
| subagents | PRReviewSubagent, DocGeneratorSubagent | Spawned on-demand |
| key_storage | Supabase Vault for BYOK keys | Singleton |

**Startup Sequence**:
1. Load environment variables (config.py)
2. Initialize database connection pool (SQLAlchemy async engine)
3. Create Redis client (hot cache)
4. Create tool_registry (MCP servers)
5. Create provider_selector (task routing table)
6. Create PilotSpaceAgent (Singleton, lazy-initialized on first chat request)
7. Skill discovery (auto-load from `.claude/skills/`)
8. Mount SSE routers in FastAPI app

### Stream Method

**Entry Point for Chat**:

1. Get API key (BYOK per workspace)
2. Build system prompt with dynamic context
3. Configure MCP servers (33 tools total)
4. Create ClaudeSDKClient with in-process subprocess
5. Stream SDK responses → transform to SSE → yield
6. Handle errors (ProviderUnavailableError) → SSE error event
7. Cleanup active clients

Max tokens per session: 8,000 (configurable)

### Message Transformation Pipeline

**From SDK to SSE**: `transform_sdk_message()` (delegates to pilotspace_agent_helpers.py)

**Event Types Emitted** (9 types):
- message_start, text_delta, tool_use, tool_result (SDK events)
- content_update (note/issue mutations from tool payloads)
- task_progress, approval_request (long-running ops)
- message_stop, error

**Example: content_update Event**:
```json
{
  "type": "content_update",
  "note_id": "550e8400-e29b-41d4-a716-446655440000",
  "blocks": [{
    "block_id": "¶1",
    "operation": "replace",
    "content": "<p>Updated text</p>"
  }]
}
```

### Session Management Integration

**Resumption**: ChatRequest can specify `resume_session_id` (instead of `session_id`) to continue a previous conversation

PilotSpaceAgent detects resume_session_id → SessionManager.get_session() → Restores from Redis or PostgreSQL → SDK continues with full context

---

## Provider Routing & Fallback (DD-011)

### ProviderSelector Class

**File**: `ai/providers/provider_selector.py` (447 lines)

**Models**:
```python
@enum.auto
class Provider(str, Enum):
    """Available LLM providers."""
    ANTHROPIC_OPUS = "anthropic-opus"
    ANTHROPIC_SONNET = "anthropic-sonnet"
    ANTHROPIC_HAIKU = "anthropic-haiku"
    GOOGLE_FLASH = "google-flash"
    GOOGLE_PRO = "google-pro"
    OPENAI_EMBEDDING = "openai-embedding"

@enum.auto
class TaskType(str, Enum):
    """Task categories for provider routing."""
    PR_REVIEW = "pr_review"           # Opus
    CONTEXT_AGGREGATION = "context"   # Sonnet
    GHOST_TEXT = "ghost_text"         # Gemini Flash
    SEMANTIC_SEARCH = "semantic_search"  # Gemini embeddings
```

**Routing Table** (lines 105-240):
```python
_ROUTING_TABLE = {
    TaskType.PR_REVIEW: ProviderConfig(
        primary=Provider.ANTHROPIC_OPUS,
        fallback=[Provider.ANTHROPIC_SONNET, Provider.GOOGLE_PRO],
        max_tokens=8_000,
        cache_control="ephemeral",  # Prompt caching
    ),
    TaskType.CONTEXT_AGGREGATION: ProviderConfig(
        primary=Provider.ANTHROPIC_SONNET,
        fallback=[Provider.GOOGLE_PRO],
        max_tokens=2_000,
    ),
    TaskType.GHOST_TEXT: ProviderConfig(
        primary=Provider.GOOGLE_FLASH,
        fallback=[Provider.ANTHROPIC_SONNET],
        max_tokens=50,
        timeout_sec=2.5,
    ),
}
```

### Selection API

**Simple Selection**: `provider = provider_selector.select(task_type=TaskType.PR_REVIEW)` → ProviderConfig

**Fallback Handling**:
- Try primary with ResilientExecutor
- On ProviderUnavailableError, get_fallback() → retry with fallback provider
- Chain: Opus → Sonnet → Gemini Pro

**Health Check**: `is_provider_healthy(provider)` checks circuit breaker state

### Circuit Breaker Integration

**Per-Provider State Machine** (singleton per provider):

CLOSED (normal) → 5 failures → OPEN (fail-fast) → 30s timeout → HALF_OPEN (probe) → success → CLOSED | failure → OPEN

---

## Resilience Patterns

### ResilientExecutor (exponential backoff + circuit breaker)

**File**: `ai/infrastructure/resilience.py`

**Configuration**: `RetryConfig(max_retries=3, base_delay=1s, max_delay=60s, jitter=30%)`

**Execution**: For each attempt up to max_retries:
1. Circuit breaker check
2. Execute operation with timeout
3. On timeout/rate limit → exponential backoff with jitter → retry
4. On success → return result

**Decorator Form**: `@with_resilience(provider="anthropic", timeout_sec=30, retry_config=...)`

### Circuit Breaker (prevent cascading failures)

**File**: `ai/circuit_breaker.py`

**State Transitions**: CLOSED → 5 failures → OPEN → 30s timeout → HALF_OPEN → probe success/failure

**Singleton Pattern**: `CircuitBreaker.get_or_create(name)` ensures one breaker per provider

**Metrics**: `get_metrics()` returns name, state, failure_count, success_count, last_failure_time

---

## MCP Tools System (33 Tools, 6 Servers)

### Tool Servers Overview

| Server | Count | Purpose | Key Tools |
|--------|-------|---------|-----------|
| `note_server` | 9 | Note writing/mutation | write_to_note, update_note_block, extract_issues, create_issue_from_note, link_existing_issues, enhance_text, summarize_note, search_notes, create_note |
| `note_content_server` | 5 | Block-level operations | insert_block, remove_block, replace_block, append_block, move_block |
| `issue_server` | 4 + 6 | Issue CRUD + relations | create_issue, update_issue, get_issue, search_issues (CRUD); link_issues, unlink_issues, add_label, transition_state, assign_issue, get_related (relations) |
| `issue_relation_server` | 3 | Issue linking | create_link, delete_link, list_links |
| `project_server` | 5 | Project management | create_project, update_project, get_project, list_projects, archive_project |
| `comment_server` | 4 | Comment management | create_comment, update_comment, delete_comment, search_comments |
| **Total** | **33** | **All AI mutations** | **All return operation payloads** |

### Tool Categories by RLS Scope

**Note Tools** (14 tools: 9 note_server + 5 note_content_server):
- Scope: Note + workspace
- Operations: Create, read, update, extract, enhance
- No cross-note linking

**Issue Tools** (13 tools: 4 CRUD + 6 relations + 3 relation_server):
- Scope: Issue + workspace
- Operations: CRUD, state transition, labeling, assignment, linking
- Cross-issue relationships supported

**Project Tools** (5 tools):
- Scope: Project + workspace
- Operations: CRUD, archiving
- Contains issues

**Comment Tools** (4 tools):
- Scope: Comment + parent (issue/note) + workspace
- Operations: CRUD
- Always tied to parent entity

### Tool Registration & Discovery

**MCP Server Creation** (example: note_server.py):

Tools use `@tool` decorator and return operation payloads (JSON with `status: pending_apply`):

```python
@tool("update_note_block", "Update or append block by ID")
def update_note_block(note_id: str, block_id: str, operation: str, content: str) → str:
    resolved_note_id = _resolve_note_id({"note_id": note_id})
    return json.dumps({
        "status": "pending_apply",
        "note_id": resolved_note_id,
        "block_id": block_id,
        "operation": operation,
        "content": content,
    })
```

Server aggregates tools: `create_sdk_mcp_server(name="pilot-notes", tools=[...])`

**Tool Aggregation**: Exported tool names (mcp__server__tool format) are gathered in `pilotspace_agent.py` for allowed_tools configuration (33 total across 6 servers)

### Tool Execution Flow

**Request → Payload → Transform → SSE**:

1. User: "Add a task to the note"
2. PilotSpaceAgent.stream() routes to write_to_note MCP tool
3. Tool returns operation payload: `{"status": "pending_apply", "note_id": "...", "blocks": [...]}`
4. transform_sdk_message() converts payload to SSE event: `{"type": "content_update", ...}`
5. Frontend useContentUpdates hook processes event
6. TipTap mutation + optional API persist

### RLS Enforcement in Tools

**Pattern: Every tool validates workspace_id**:

1. Get workspace from context: `workspace_id = get_workspace_context()`
2. Explicit filter in repo call: `issue_repo.get(issue_id=issue_id, workspace_id=workspace_id)`
3. PostgreSQL RLS also enforces via session variables (app.current_workspace_id)

See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - RLS section for full RLS pattern documentation

---

## Skills System (DD-087)

### Skill Discovery

**File**: `ai/skills/skill_discovery.py`

**Filesystem Structure**:
```
.claude/skills/
├── extract-issues/
├── enhance-issue/
├── improve-writing/
├── summarize/
├── find-duplicates/
├── recommend-assignee/
├── decompose-tasks/
└── generate-diagram/
```

Each skill has a `SKILL.md` file with YAML frontmatter + instructions:
```yaml
---
name: extract-issues
description: Detect actionable items from note text
invocable: explicit  # or "auto" for intent detection
---
# Instructions follow YAML frontmatter
```

**Discovery at Startup**:
- `discover_skills()` scans `.claude/skills/` subdirectories
- Parses YAML frontmatter + body
- Returns `dict[skill_name: SkillInfo]`
- Passed to SDK via `ClaudeAgentOptions`

### Skill Invocation

**Explicit** (slash commands): User types `/extract-issues` → SDK detects and invokes → Skill instructions applied → May call MCP tools

**Auto** (intent detection): SDK recognizes trigger keywords → Skill invoked without explicit command → Results presented automatically

---

## Session Management

### SessionManager (Redis + PostgreSQL)

**File**: `ai/session/session_manager.py`

**Dual-Store Architecture**:
- **Redis** (hot cache, 30-min TTL): Fast session retrieval for active conversations
- **PostgreSQL** (durable, 24h TTL): Session resumption after Redis expiry, message history

**Core Methods**:
- `create_session()` → Stores in Redis + PostgreSQL
- `get_session()` → Tries Redis first, falls back to PostgreSQL with restoration
- `append_message()` → Updates both stores
- `delete_session()` → Cleans up both stores

---

## Approval Workflow (DD-003)

### PermissionHandler

**File**: `ai/sdk/permission_handler.py`

**Classification Matrix** (3 categories):

| Category | Approval | Examples |
|----------|----------|----------|
| Non-destructive | Auto-execute | get_issue, search, add_label, assign, transition |
| Content creation | Configurable | create_issue, create_comment, extract_issues |
| Destructive | Always required | delete_issue, unlink_issue, archive_workspace |

**API**: `check_permission(action, tool_call_id, data)` → PermissionResult with approval request if needed

**ApprovalRequest**: Stores action, data, 24h expiration, approval/rejection timestamps

### SSE Approval Flow

**Event Sequence** (Destructive Action Example):

1. **Detection**: AI calls `delete_issue()` tool
2. **Permission Check**: `PermissionHandler.check_permission("delete_issue", ...)` → `requires_approval_result()`
3. **SSE Event**: Emit `approval_request` event:
   ```json
   {
     "type": "approval_request",
     "tool_call_id": "tc_123",
     "action": "delete_issue",
     "data": {"issue_id": "...", "title": "Old feature"},
     "expires_in_seconds": 86400
   }
   ```
4. **Frontend Modal**: Renders issue details (readonly), Approve/Reject buttons, countdown timer
5. **User Response**: Clicks "Approve" → POST `/api/v1/ai/chat/answer`:
   ```json
   {"question_id": "tc_123", "response": "approved"}
   ```
6. **SDK Continuation**: `agent.submit_tool_result(session_id, "tc_123", "approved")` → SDK re-invokes tool
7. **Execution**: MCP tool now has permission to execute → DB mutation → SSE event

**Content Creation Approval** (configurable per workspace):
- Workspace setting: `require_ai_approvals: true/false`
- If enabled: Same flow as destructive
- If disabled: `PermissionHandler.auto_approve()` → Tool executes immediately

---

## Cost Tracking

### CostTracker

**File**: `ai/infrastructure/cost_tracker.py`

**Pricing** (provider-specific token rates):
- Claude Opus: $3/$15 per 1M tokens (input/output)
- Claude Sonnet: $3/$15 per 1M tokens
- Gemini Flash: $0.075/$0.3 per 1M tokens
- Cached tokens: 90% discount applied

**API**: `track_request()` logs prompt/completion/cached tokens, calculates USD cost, persists to PostgreSQL, triggers budget alert at 90% of workspace limit

---

## Subagents: Multi-Turn Conversational Agents

All subagents extend `StreamingSDKBaseAgent[Input, Output]` with async streaming of SSE events.

### PRReviewSubagent

**File**: `ai/agents/subagents/pr_review_subagent.py`

**Model**: Claude Opus (deep reasoning for 5 aspects)

**Flow**: Fetch PR from GitHub → Build multi-aspect prompt → Stream review via SDK → Transform to SSE

**Aspects**: Architecture, Security, Code Quality, Performance, Documentation

### DocGeneratorSubagent

**Similar pattern** for ADR/API/spec generation with Claude Sonnet

---

## Error Handling

### Custom Exceptions

**File**: `ai/exceptions.py`

Core exceptions: `AIException` (base), `ProviderUnavailableError` (circuit open), `AITimeoutError`, `RateLimitError` (with retry_after), `ApprovalTimeoutError`

### Error Propagation

**SSE error event** (sent to frontend):
```json
{
  "type": "error",
  "code": "provider_unavailable",
  "message": "Claude API temporarily unavailable",
  "recoverable": true,
  "retry_after_seconds": 30
}
```

---

## Integration with Backend Patterns

### RLS Enforcement in AI Context

**Every MCP tool respects RLS** with 3-layer enforcement:

1. **Context Layer**: `get_workspace_context()` retrieves current workspace from request
2. **Application Layer**: Explicit `workspace_id` filter in all repository calls
3. **Database Layer**: PostgreSQL RLS policies via session variables (app.current_workspace_id)

Pattern:
```python
async def issue_tool(issue_id: str) → str:
    workspace_id = get_workspace_context()
    issue = await issue_repo.get(issue_id=UUID(issue_id), workspace_id=workspace_id)
    if not issue:
        raise PermissionError(f"Issue not found in workspace {workspace_id}")
```

See [infrastructure/CLAUDE.md](src/pilot_space/infrastructure/CLAUDE.md) - "RLS (Row-Level Security)" for comprehensive RLS architecture documentation.

### Integration with Service Layer

**AI → SDK → Tool → Service → Repository → Persistence Flow**:

1. **Frontend**: User types message in ChatView
2. **AI Router** (`ai_chat.py`): POST request with message, session_id
3. **PilotSpaceAgent.stream()**: Gets API key, builds system prompt, creates ClaudeSDKClient
4. **ClaudeSDKClient**: Routes to MCP tools or skills based on intent
5. **MCP Tool Handler**: Validates, calls repository (RLS-scoped), returns operation payload
6. **transform_sdk_message()**: Converts operation payload to SSE event
7. **SSE Event**: Sent to frontend (content_update, text_delta, etc.)
8. **Frontend Hook** (`useContentUpdates`): Processes event, optionally calls API to persist
9. **Router → Service.execute(Payload)**: CQRS-lite pattern (if explicit persist needed)
10. **Domain Logic**: Validation, events, state transitions
11. **Repository.update()**: RLS-enforced PostgreSQL mutation

**Key**: Some mutations happen in AI tool (step 5), others via subsequent frontend API call (steps 8-11). Dual-write pattern minimizes latency while maintaining consistency.

### Skill vs MCP Tool Relationship

**Skill** (DD-087): Single-turn behavior defined in `.claude/skills/SKILL.md`. May invoke MCP tools internally.

**MCP Tool**: Direct Python function with `@tool` decorator. Registered via `create_sdk_mcp_server()`. Accepts structured parameters, returns operation payloads.

**Flow**: User command → Skill execution → Optionally calls MCP tool → Returns result → SDK transforms to SSE

See [docs/dev-pattern/45-pilot-space-patterns.md](../../../docs/dev-pattern/45-pilot-space-patterns.md) - "AI Agent Patterns" for complete skill system architecture.

---

---

## Common Pitfalls & Solutions

| Pitfall | Problem | Solution |
|---------|---------|----------|
| **Blocking I/O in tools** | Blocks event loop | Use `loop.run_in_executor()` for file I/O |
| **Tool not returning payload** | SDK can't transform | Return JSON `{"status": "pending_apply", ...}` |
| **Circuit breaker per request** | Failure count lost | Use `CircuitBreaker.get_or_create()` singleton |
| **Missing RLS context** | Cross-workspace data leak | Always `get_workspace_context()` + explicit filter |
| **Approval not awaited** | Tool executes immediately | Return `{"status": "pending_approval"}` + wait for user |

---

## Pre-Submission Checklist: AI Components

**Rate each item (0-1) before submitting code to `/backend/src/pilot_space/ai/`**

### Architecture & Patterns ⭐ CRITICAL
- [ ] New agents inherit from `StreamingSDKBaseAgent[Input, Output]` with async streaming: ___
- [ ] MCP tools return operation payloads (JSON, `status: pending_apply` or `pending_approval`): ___
- [ ] Session state managed via `SessionManager` (Redis 30-min hot + PostgreSQL 24-day durable): ___
- [ ] Approval flows use `PermissionHandler` for DD-003 classification (non-destructive/content/destructive): ___
- [ ] Skill system files follow `.claude/skills/{skill_name}/SKILL.md` format: ___

### Security: RLS & Keys ⭐ CRITICAL
- [ ] All MCP tool handlers call `get_workspace_context()` first: ___
- [ ] Entity queries explicitly filtered by `workspace_id`: ___
- [ ] API keys loaded from `SecureKeyStorage` (BYOK) or env var fallback: ___
- [ ] No sensitive data logged (keys, tokens, user data, workspace details): ___
- [ ] No cross-workspace data leakage in tool results: ___

### Resilience: Timeouts & Fallbacks
- [ ] Provider calls wrapped with `ResilientExecutor` (retry + circuit breaker): ___
- [ ] `CircuitBreaker.get_or_create()` used (singleton per provider, not per-request): ___
- [ ] Timeout configured per task type (PR review <5min, ghost text <2.5s, context <30s): ___
- [ ] Fallback provider chain configured for all agentic tasks: ___
- [ ] Error handling with SSE error events (type: "error", recoverable flag, retry_after): ___

### Cost Tracking & Logging
- [ ] `CostTracker.track_request()` called after every LLM call: ___
- [ ] Token counts logged (prompt, completion, cached): ___
- [ ] Per-workspace cost tracking with budget alerts at 90%: ___

### Quality Gates (MUST PASS)
- [ ] Run: `uv run pyright && uv run ruff check && uv run pytest --cov=.`: ___
- [ ] Type checking PASS (pyright strict mode): ___
- [ ] Linting PASS (ruff, no errors): ___
- [ ] Tests PASS with coverage >80%: ___
- [ ] File size <700 lines per file: ___
- [ ] No TODO comments, mocks, or placeholder functions: ___

**If any score <0.9, address gaps before commit.** Incomplete resilience = production incidents.

## Quick Implementation Reference

### Adding a New MCP Tool

**Steps**:
1. Create tool handler with `@tool` decorator in relevant server file (e.g., `mcp/note_server.py`)
2. Return operation payload: `{"status": "pending_apply", "note_id": "...", ...}`
3. Export tool name: `TOOL_NAMES = ["mcp__pilot-notes__new_tool"]`
4. Aggregate in `pilotspace_agent.py` ALL_TOOL_NAMES list
5. Add to PilotSpaceAgent system prompt (tool categories section)
6. Test: `pytest tests/ai/mcp/test_note_server.py`
7. Verify RLS: Add workspace scoping + explicit filter

See: [mcp/](src/pilot_space/ai/mcp/) for 6 existing server implementations

### Adding a New Skill

**Steps**:
1. Create directory: `.claude/skills/{skill_name}/`
2. Create SKILL.md with YAML frontmatter:
   ```yaml
   ---
   name: skill-name
   description: What the skill does
   invocable: explicit  # or "auto"
   ---
   # Instructions follow
   ```
3. No registration needed - auto-discovered at startup
4. Invoke via slash command: `/skill-name`
5. Or SDK intent detection triggers automatically

See: [skills/](src/pilot_space/ai/skills/) and [.claude/skills/](../../../.claude/skills/) examples

### Adding a New Provider

**Steps**:
1. Add to `Provider` enum in `provider_selector.py`
2. Add to `_ROUTING_TABLE` with task mapping
3. Add to `PRICING_TABLE` in `cost_tracker.py`
4. Create `CircuitBreaker.get_or_create(name)` for resilience
5. Test fallback chain: `test_provider_selector.py`

Example: If adding Claude Haiku for cost-sensitive tasks:
```python
# provider_selector.py
TaskType.SUMMARIZATION: ProviderConfig(
    primary=Provider.ANTHROPIC_HAIKU,  # New
    fallback=[Provider.ANTHROPIC_SONNET],
    max_tokens=1_000,
)

# cost_tracker.py
Provider.ANTHROPIC_HAIKU: {
    "input_tokens": 0.8 / 1_000_000,
    "output_tokens": 4.0 / 1_000_000,
}
```

### Debugging AI Issues

**Session Stuck/Lost**:
- Check Redis: `redis-cli GET session:{session_id}`
- Check PostgreSQL: `SELECT * FROM chat_session WHERE id = '{session_id}'`
- Force restoration: Restart service (clears Redis, postgres persists)

**Tool Not Executing**:
- Check permission classification: `PermissionHandler.ACTION_CLASSIFICATIONS`
- Check tool registered: Tool name in `pilotspace_agent.py` ALL_TOOL_NAMES
- Check RLS: Verify `get_workspace_context()` returns correct workspace_id

**Circuit Breaker Stuck OPEN**:
- Check metrics: `CircuitBreaker.get_metrics()`
- Manually close: Restart service or call `breaker.reset()` (development only)
- Config: Adjust failure_threshold (default: 5) or timeout_seconds (default: 30s)

**Cost Spike**:
- Query: `SELECT SUM(cost_usd) FROM ai_cost_record WHERE workspace_id = '{ws_id}' AND created_at > NOW() - INTERVAL 1 HOUR`
- Check cached tokens: Prompt caching should show ~90% discount on input tokens
- Provider routing: Verify task-to-provider mapping uses cost-optimized selections

---

## Related Documentation

### Architecture & Patterns
- **Backend Parent**: `/backend/CLAUDE.md` (5-layer architecture overview)
- **Design Decisions**: `/docs/DESIGN_DECISIONS.md` (DD-086 orchestrator, DD-087 skills, DD-011 provider routing, DD-003 approval)
- **Pilot Space Patterns**: `/docs/dev-pattern/45-pilot-space-patterns.md` (AI agent patterns override)
- **Backend Patterns**: `/docs/dev-pattern/` (service layer, repository, validation, error handling)

### Backend Integration Points
- **Router**: `/backend/src/pilot_space/api/v1/routers/ai_chat.py` (PilotSpaceAgent entry point, SSE streaming)
- **Router**: `/backend/src/pilot_space/api/v1/routers/notes_ai.py` (ghost text agent)
- **Router**: `/backend/src/pilot_space/api/v1/routers/ai_pr_review.py` (PR review agent)
- **Services**: `/backend/src/pilot_space/application/services/` (CQRS-lite pattern)
- **Infrastructure**: `/backend/src/pilot_space/infrastructure/CLAUDE.md` (RLS, repositories, migrations)

### Frontend Integration
- **State**: `/frontend/src/stores/PilotSpaceStore.ts` (unified orchestrator state)
- **Hooks**: `/frontend/src/features/ai/hooks/useContentUpdates.ts`, `useChatStream.ts`
- **Components**: `/frontend/src/features/ai/ChatView.tsx` (SSE listener)
- **Store**: `/frontend/src/stores/ApprovalStore.ts` (approval workflow state)

### External References
- **Claude SDK**: `docs/claude-sdk.txt` (full SDK documentation)
- **MCP Protocol**: https://modelcontextprotocol.io/ (Model Context Protocol specification)

---

## Generation Metadata

**Generated**: 2026-02-10
**Scope**: `/backend/src/pilot_space/ai/` complete module documentation
**Languages**: Python 3.12+
**Files Analyzed**: 50+ core files

### Patterns Detected
- **Orchestrator Pattern**: PilotSpaceAgent (DD-086)
- **Filesystem Skill Discovery**: Auto-loaded YAML (DD-087)
- **MCP Tool Registry**: 33 tools across 6 servers
- **Provider Routing**: Task-based selection + fallback chain (DD-011)
- **Circuit Breaker**: Per-provider resilience
- **Exponential Backoff Retry**: Jitter + timeout integration
- **Session Duality**: Redis hot + PostgreSQL durable
- **Human-in-Loop**: Permission handler for approvals (DD-003)
- **Cost Tracking**: Per-request BYOK pricing
- **RLS Enforcement**: Workspace-scoped queries + PostgreSQL policies

### Coverage Gaps
- **Prompt Caching**: Not fully documented (ephemeral cache_control used, optimization potential)
- **Rate Limiting**: Infrastructure present but not detailed
- **Offline Queue**: pgmq integration mentioned, implementation not shown
- **Alert Service**: Cost alerts triggered, implementation details missing
- **GitHub Integration**: PR review references GitHub client, not fully explored

### Suggested Next Steps
1. **Document Prompt Templates**: Create `ai/prompts/CLAUDE.md` with all prompt designs
2. **Document Role Templates**: Create `ai/templates/CLAUDE.md` for persona specifications
3. **API Endpoint Documentation**: All 3 SSE chat endpoints with full examples
4. **Troubleshooting Guide**: Common issues (circuit breaker stuck, session loss, etc.)
5. **Performance Tuning**: Token budgets, cache strategies, batch optimization
