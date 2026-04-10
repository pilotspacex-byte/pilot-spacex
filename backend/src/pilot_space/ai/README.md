# AI Layer - Pilot Space

**Parent**: `/backend/README.md` | **Language**: Python 3.12+

---

## Submodule Documentation

- **[agents/README.md](agents/README.md)** -- PilotSpaceAgent orchestrator, subagents, session management, approval workflow, message transformation
- **[mcp/README.md](mcp/README.md)** -- MCP Tools (33 tools, 6 servers), Skills (8 YAML auto-discovery), Role Skill Templates (8 roles)
- **[providers/README.md](providers/README.md)** -- Provider Routing (DD-011, 20 task types), Resilience (retry + circuit breaker), Cost tracking
- **[templates/rules/pm_blocks.md](templates/rules/pm_blocks.md)** -- PM block types, TipTap JSON format, edit guard rules

---

## Architecture

```
ai/
├── agents/                    # Orchestrator + subagents
├── mcp/                       # MCP Tool Servers
├── providers/                 # Provider selection & routing
├── sdk/                       # Claude Agent SDK integration
├── session/                   # Session management (Redis + PostgreSQL)
├── skills/                    # Skill system (auto-discovery)
├── infrastructure/            # Cross-cutting (cost, resilience, cache)
├── prompts/                   # Prompt templates
└── templates/                 # Skills YAML, role templates, rules
```

## Memory & Permissions (Phase 69)

Granular per-tool governance plus typed memory recall, both hot-path
budgeted and DD-003-safe. See **DD-089** for the full decision.

- **Memory recall** — `MemoryRecallService` (`application/services/memory/memory_recall_service.py`) wraps `GraphSearchService` with a 5-type filter (`note_summary`, `issue_decision`, `agent_turn`, `user_correction`, `pr_review_finding`), a 30s `AIResponseCache`, and per-key single-flight. The orchestrator’s `recall_graph_context()` seam (`agents/pilotspace_agent.py`) injects the result into the `<memory>` prompt block built by `prompt/prompt_assembler.py`. SSE emits a `memory_used` event so the chat UI can render the MemoryUsedChip.
- **Granular permissions** — `PermissionService` (`application/services/permissions/permission_service.py`) is a 5-tier resolver: LRU → DB row → workspace overrides → DD-003 default → `ASK`. Admin mutations go through `PUT /api/v1/workspaces/{id}/ai-permissions` and write an audit log.
- **DD-003 invariant — defense in depth**: CRITICAL tools cannot reach AUTO at the **service** (`set()` raises), the **handler** (`sdk/permission_handler.py` re-checks at invocation), or the **UI** (`can_set_auto=false`). Removing any one layer is a regression.
- **Telemetry** — `ai/telemetry/memory_metrics.py` exposes module-level counters: `record_recall_hit/miss`, `record_recall_latency_ms`, `get_hit_rate()`, `get_latency_p95_ms()`, `snapshot()`. Wired into `MemoryRecallService.recall()`.
- **SLOs (pinned in CI)** — `tests/performance/test_phase69_latency.py` enforces recall p95 < 200ms (cache warm) and resolver p95 < 5ms (cache warm).

## Critical Files

| Component | File | Purpose |
|-----------|------|---------|
| Orchestrator | `agents/pilotspace_agent.py` | Main agent routing to skills/subagents |
| Providers | `providers/provider_selector.py` | Task-based provider routing + fallback chain |
| Resilience | `infrastructure/resilience.py` | Retry + circuit breaker patterns |
| Approvals | `sdk/permission_handler.py` | Human-in-the-loop (DD-003) |
| Sessions | `session/session_manager.py` | Redis hot cache + PostgreSQL durable |
| Skills | `skills/skill_discovery.py` | Auto-discovery from `.claude/skills/` |
| Role Skills | `../application/services/role_skill/generate_role_skill_service.py` | AI-powered dynamic template generation |
| Role Templates | `templates/role_templates/` | 8 predefined SDLC role templates |
| Cost Tracking | `infrastructure/cost_tracker.py` | Per-request token + cost logging |
| Circuit Breaker | `circuit_breaker.py` | Provider resilience pattern |

## Key Constants

| Constant | Value |
|----------|-------|
| DEFAULT_MODEL_TIER | ModelTier.SONNET (cost-optimized) |
| SESSION_TTL_SECONDS | 86400 (24h PostgreSQL) |
| REDIS_TTL_SECONDS | 1800 (30min hot cache) |
| CIRCUIT_BREAKER_TIMEOUT | 30s (OPEN -> HALF_OPEN) |
| FAILURE_THRESHOLD | 3 consecutive failures |
| MAX_RETRIES / BASE_DELAY / MAX_DELAY | 3 / 1.0s / 60.0s |

---

## Data Flow: Chat Request -> Response

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

## Design Decisions

| Decision | Summary |
|----------|---------|
| DD-086: Centralized Agent | Single PilotSpaceAgent orchestrator with skills (single-turn) + subagents (multi-turn) |
| DD-087: Filesystem Skills | `.claude/skills/` YAML auto-discovery, version-controlled, zero-latency |
| DD-011: Provider Routing | Task-based selection (Opus/Sonnet/Flash) + per-task fallback chains, 20 task types |
| DD-003: Human-in-Loop | Non-destructive auto-approve, content creation configurable, destructive always require approval |

---

## Integration Patterns

### RLS Enforcement in AI Context

Every MCP tool respects RLS with 3-layer enforcement:
1. **Context Layer**: `get_workspace_context()` retrieves current workspace
2. **Application Layer**: Explicit `workspace_id` filter in all repository calls
3. **Database Layer**: PostgreSQL RLS policies via session variables

### Skill vs MCP Tool

- **Skill** (DD-087): Single-turn behavior in `.claude/skills/SKILL.md`. May invoke MCP tools internally.
- **MCP Tool**: Direct Python function with `@tool` decorator. Returns operation payloads.

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Blocking I/O in tools | Use `loop.run_in_executor()` for file I/O |
| Tool not returning payload | Return JSON `{"status": "pending_apply", ...}` |
| Circuit breaker per request | Use `CircuitBreaker.get_or_create()` singleton |
| Missing RLS context | Always `get_workspace_context()` + explicit filter |
| Approval not awaited | Return `{"status": "pending_approval"}` + wait for user |

---

## Pre-Submission Checklist

- [ ] New agents inherit from `StreamingSDKBaseAgent[Input, Output]`
- [ ] MCP tools return operation payloads (`status: pending_apply` or `pending_approval`)
- [ ] Session state via `SessionManager` (Redis 30-min + PostgreSQL 24h)
- [ ] Approval flows use `PermissionHandler` for DD-003 classification
- [ ] Skill files follow `.claude/skills/{skill_name}/SKILL.md` format
- [ ] All MCP tool handlers call `get_workspace_context()` first
- [ ] Entity queries filtered by `workspace_id`
- [ ] API keys from `SecureKeyStorage` (BYOK) or env var fallback
- [ ] Provider calls wrapped with `ResilientExecutor`
- [ ] `CostTracker.track_request()` called after every LLM call
- [ ] Quality gates pass: `uv run pyright && uv run ruff check && uv run pytest --cov=.`
