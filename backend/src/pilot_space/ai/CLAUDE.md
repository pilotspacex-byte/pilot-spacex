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
| Role Skills | `application/services/role_skill/generate_role_skill_service.py` | AI-powered dynamic template generation |
| Role Templates | `ai/templates/role_templates/` | 8 predefined SDLC role templates |
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

## Submodule Documentation

Detailed documentation is organized in submodule guides:

- **[agents/CLAUDE.md](agents/CLAUDE.md)** -- PilotSpaceAgent orchestrator, subagents (PR Review, Doc Generator), session management, approval workflow, message transformation pipeline
- **[mcp/CLAUDE.md](mcp/CLAUDE.md)** -- MCP Tools System (33 tools, 6 servers), Skills System (8 skills, YAML auto-discovery), Role Skill Dynamic Templates (8 role templates)
- **[templates/rules/pm_blocks.md](templates/rules/pm_blocks.md)** -- PM block types, TipTap JSON format, insert/update operations, edit guard rules
- **[providers/CLAUDE.md](providers/CLAUDE.md)** -- Provider Routing (DD-011, 20 task types), Resilience patterns (retry + circuit breaker), Cost tracking (per-request BYOK pricing)

---

## Architecture Overview

### AI Layer Structure

```
ai/
├── agents/                    # Orchestrator + subagents (see agents/CLAUDE.md)
├── mcp/                       # MCP Tool Servers (see mcp/CLAUDE.md)
├── providers/                 # Provider selection & routing (see providers/CLAUDE.md)
├── sdk/                       # Claude Agent SDK integration
├── session/                   # Session management (Redis + PostgreSQL)
├── skills/                    # Skill system (auto-discovery)
├── infrastructure/            # Cross-cutting concerns (cost, resilience, cache)
├── prompts/                   # Prompt templates
└── templates/                 # Skills YAML, role templates, rules
```

### Data Flow: Chat Request -> Response

```
Frontend POST /api/v1/ai/chat
    | (ChatRequest with workspace_id, user_id)
FastAPI Router (ai_chat.py)
    | PilotSpaceAgentDep injection
PilotSpaceAgent.stream(ChatInput)
    | (1) Get API key from Vault (per-workspace BYOK)
    | (2) Build system prompt + role skill injection
    | (3) Configure MCP servers + allowed_tools
ClaudeSDKClient (in-process)
    | (4) Routes: skill? -> skill execution
    |       OR: subagent? -> spawn subagent
    |       OR: tool call? -> MCP tool handler
Tool Handler (e.g., note_server.py)
    | (5) Tool validates + returns operation payload
transform_sdk_message()
    | (6) Converts payload -> SSE content_update event
SSE StreamingResponse
    | (7) Yields text_delta, tool_use, content_update, task_progress, approval_request
Frontend useContentUpdates() Hook
    | (8) Processes content_update -> TipTap editor mutation + API call
```

---

## Design Decisions Summary

| Decision | Summary |
|----------|---------|
| DD-086: Centralized Agent | Single PilotSpaceAgent orchestrator with skills (single-turn) + subagents (multi-turn). Replaces 13 siloed agents. |
| DD-087: Filesystem Skills | `.claude/skills/` YAML auto-discovery. Version-controlled, zero-latency, IDE-friendly. |
| DD-011: Provider Routing | Task-based selection (Opus/Sonnet/Flash) + per-task fallback chains. 20 task types. |
| DD-003: Human-in-Loop | Non-destructive auto-approve, content creation configurable, destructive always require approval. |

---

## Integration Patterns

### RLS Enforcement in AI Context

Every MCP tool respects RLS with 3-layer enforcement:

1. **Context Layer**: `get_workspace_context()` retrieves current workspace
2. **Application Layer**: Explicit `workspace_id` filter in all repository calls
3. **Database Layer**: PostgreSQL RLS policies via session variables

### AI -> SDK -> Tool -> Service -> Repository Flow

1. Frontend: User types message in ChatView
2. AI Router: POST request with message, session_id
3. PilotSpaceAgent.stream(): Gets API key, builds system prompt
4. MCP Tool Handler: Validates, returns operation payload
5. transform_sdk_message(): Converts to SSE event
6. Frontend Hook: Processes event, optionally calls API to persist

### Skill vs MCP Tool

- **Skill** (DD-087): Single-turn behavior in `.claude/skills/SKILL.md`. May invoke MCP tools internally.
- **MCP Tool**: Direct Python function with `@tool` decorator. Returns operation payloads.

---

## Common Pitfalls & Solutions

| Pitfall | Problem | Solution |
|---------|---------|----------|
| Blocking I/O in tools | Blocks event loop | Use `loop.run_in_executor()` for file I/O |
| Tool not returning payload | SDK can't transform | Return JSON `{"status": "pending_apply", ...}` |
| Circuit breaker per request | Failure count lost | Use `CircuitBreaker.get_or_create()` singleton |
| Missing RLS context | Cross-workspace data leak | Always `get_workspace_context()` + explicit filter |
| Approval not awaited | Tool executes immediately | Return `{"status": "pending_approval"}` + wait for user |

---

## Pre-Submission Checklist: AI Components

### Architecture & Patterns (CRITICAL)
- [ ] New agents inherit from `StreamingSDKBaseAgent[Input, Output]`
- [ ] MCP tools return operation payloads (`status: pending_apply` or `pending_approval`)
- [ ] Session state managed via `SessionManager` (Redis 30-min + PostgreSQL 24h)
- [ ] Approval flows use `PermissionHandler` for DD-003 classification
- [ ] Skill files follow `.claude/skills/{skill_name}/SKILL.md` format

### Security: RLS & Keys (CRITICAL)
- [ ] All MCP tool handlers call `get_workspace_context()` first
- [ ] Entity queries explicitly filtered by `workspace_id`
- [ ] API keys loaded from `SecureKeyStorage` (BYOK) or env var fallback
- [ ] No sensitive data logged

### Resilience & Cost
- [ ] Provider calls wrapped with `ResilientExecutor`
- [ ] `CircuitBreaker.get_or_create()` used (singleton per provider)
- [ ] `CostTracker.track_request()` called after every LLM call
- [ ] Error handling with SSE error events (recoverable flag, retry_after)

### Quality Gates (MUST PASS)
- [ ] `uv run pyright && uv run ruff check && uv run pytest --cov=.`
- [ ] File size <700 lines per file
- [ ] No TODO comments, mocks, or placeholder functions

---

## Related Documentation

- **Backend Parent**: `/backend/CLAUDE.md` (5-layer architecture)
- **Design Decisions**: `/docs/DESIGN_DECISIONS.md` (DD-086, DD-087, DD-011, DD-003)
- **Pilot Space Patterns**: `/docs/dev-pattern/45-pilot-space-patterns.md`
- **Claude SDK**: `docs/claude-sdk.txt`

---

## Generation Metadata

**Generated**: 2026-02-10 | **Scope**: `/backend/src/pilot_space/ai/` | **Language**: Python 3.12+

**Patterns**: Orchestrator (DD-086), Filesystem Skills (DD-087), MCP Tool Registry (33 tools), Provider Routing (DD-011), Circuit Breaker, Session Duality, Human-in-Loop (DD-003), Cost Tracking, RLS Enforcement

**Coverage Gaps**: Prompt caching optimization, rate limiting details, offline queue (pgmq), alert service implementation, GitHub integration for PR review
