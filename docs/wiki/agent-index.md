# Pilot Space Agent: Feature Wiki Index

> **Root location**: `backend/src/pilot_space/ai/`
> **Core design decisions**: DD-002 (BYOK), DD-003 (Approval), DD-011 (Provider Routing), DD-086 (Centralized Agent), DD-087 (Skill System), DD-088 (MCP Tools)

## Overview

Pilot Space embeds an AI agent directly into the SDLC workflow. The agent is built on the **centralized orchestrator pattern (DD-086)**: one `PilotSpaceAgent` handles all user-facing AI interactions, routing to skills (single-turn stateless operations) and subagents (multi-turn stateful tasks) as needed. Everything runs through a single SSE stream per conversation, with human-in-the-loop approval gates for consequential actions (DD-003).

---

## Feature Documents

| Document | What it covers |
|----------|----------------|
| [Orchestrator](./agent-orchestrator.md) | `PilotSpaceAgent` — 9-phase execution loop, intent pipeline, SSE delta buffering, stream utilities |
| [Subagents](./agent-subagents.md) | PR Review, Doc Generator, AI Context, Plan Generation, Role Skill Materializer |
| [MCP Tools & Servers](./agent-mcp-tools.md) | 33 tools across 6 servers, operation payload pattern, RLS enforcement, entity resolver |
| [Skills & Prompts](./agent-skills-prompts.md) | Skill discovery, execution lifecycle, prompt assembler (6-layer), intent classifier, all prompt templates |
| [SDK Integration](./agent-sdk-integration.md) | Claude Agent SDK hooks, permission handler (DD-003), approval waiter, command registry, SSE transformer |
| [Infrastructure & Resilience](./agent-infrastructure-resilience.md) | Provider routing (DD-011), circuit breaker, retry, BYOK encryption, cost tracking, ghost text, sessions, workers |

---

## System Architecture

```
Frontend (ChatView SSE client)
        ↑ 14 SSE event types
        │
POST /api/v1/ai/chat (FastAPI StreamingResponse)
        ↓
PilotSpaceAgent (orchestrator)   ←── agent-orchestrator.md
  │
  ├── IntentClassifier (~1ms, regex, no LLM)
  │     └── intent-pipeline → skill | subagent | free-conversation
  │
  ├── PromptAssembler (6-layer)  ←── agent-skills-prompts.md
  │     base → workspace → role → document → history → message
  │
  ├── SdkConfig (BYOK, sandbox)  ←── agent-sdk-integration.md
  │
  ├── Claude Agent SDK execution loop
  │     │
  │     ├── PreToolHook → PermissionHandler (DD-003)
  │     │     AUTO_EXECUTE | DEFAULT | CRITICAL
  │     │     └── CRITICAL: blocks → ApprovalWaiter (polls DB)
  │     │
  │     ├── MCP tool calls (in-process) ←── agent-mcp-tools.md
  │     │     NoteServer      (8 tools)
  │     │     NoteContentServer(5 tools)
  │     │     IssueServer     (8 tools)
  │     │     IssueRelationServer(4 tools)
  │     │     ProjectServer   (3 tools)
  │     │     CommentServer   (3 tools)
  │     │     + interaction, ownership (2 tools)
  │     │
  │     ├── PostToolHook → audit + cost delta
  │     │
  │     └── SSEDeltaBuffer → stream_event_transformer
  │
  ├── Subagents (spawned on @mention) ←── agent-subagents.md
  │     @pr-review    → PRReviewSubagent (GitHub, 5 dimensions)
  │     @doc-generator→ DocGeneratorSubagent (Markdown docs)
  │     @ai-context   → AIContextAgent (multi-turn context)
  │     \plan         → PlanGenerationAgent (task decomposition)
  │
  ├── Skills (spawned on \command) ←── agent-skills-prompts.md
  │     24 YAML-defined skills auto-discovered
  │     SkillExecutor: 6-step lifecycle, Redis lock, approval
  │
  └── Infrastructure ←── agent-infrastructure-resilience.md
        ProviderSelector (DD-011): task → model routing
        CircuitBreaker: 3-failure → OPEN → 30s → HALF_OPEN
        ResilientExecutor: 3 retries, 1-60s backoff, ±30% jitter
        CostTracker: per-request cost to PostgreSQL
        SecureKeyStorage: BYOK AES-256-GCM encrypted
        SessionManager: Redis 30-min + PG 24h dual-store
        GhostTextService: Haiku <2.5s, 1h cache
```

---

## Key Flows

### 1. User Sends a Message

```
User: "\extract-issues from my note"
    ↓
IntentClassifier: skill_invocation → "extract-issues"
    ↓
SkillExecutor.run("extract-issues", context)
  → 1. Validate input
  → 2. Approval tier: DEFAULT → emit approval_request SSE
  → 3. [User approves]
  → 4. PromptAssembler: 6-layer system prompt
  → 5. ProviderSelector: Sonnet
  → 6. LLM call → stream tokens
  → 7. VersioningHook: snapshot before/after
  → 8. emit structured_result SSE (IssueExtractionOutput)
```

### 2. Approval Workflow (DD-003)

```
Tool call: issue.delete_issue (CRITICAL tier)
    ↓
PermissionHandler.classify → CRITICAL
    ↓
ApprovalWaiter.wait(approval_id)
  → emit approval_request SSE (DestructiveApprovalModal opens)
  → poll DB every 2s for resolution
  → if approved: resume SDK execution
  → if rejected | 5min timeout: raise ApprovalRejectedError
```

### 3. Ghost Text (Independent Path)

```
User stops typing for 500ms
    ↓
GET /api/v1/ai/ghost-text (separate SSE endpoint)
    ↓
GhostTextService (bypasses PilotSpaceAgent)
  → Cache lookup (1h Redis)
  → Claude Haiku call (<1.5s)
  → Stream tokens
  → Cache result
Total: <2.5s SLA
```

### 4. PR Review (Subagent via Webhook)

```
GitHub webhook: pull_request.opened
    ↓
FastAPI webhook handler → queue (pgmq)
    ↓
Background worker → PRReviewSubagent.run()
  → github.get_pr(repo, pr_number)
  → LLM review (5 dimensions)
  → Filter: severity in {critical, major} → post comments
  → emit SSE notification to workspace
```

---

## Provider Routing Quick Reference (DD-011)

| Task | Model | Why |
|------|-------|-----|
| PR Review | Claude Opus 4.5 | Deep code analysis, security audit |
| AI Context | Claude Opus 4.5 | Multi-turn context building |
| Issue Enhancement | Claude Sonnet 4 | Balanced quality/cost |
| Issue Extraction | Claude Sonnet 4 | Structured reasoning |
| Doc Generation | Claude Sonnet 4 | Code-aware writing |
| Conversation | Claude Sonnet 4 | Default |
| Ghost Text | Claude Haiku 3.5 | <2.5s latency SLA |
| Assignee Recommendation | Claude Haiku 3.5 | Fast scoring |
| Semantic Search | OpenAI embedding 3-large | 3072-dim, HNSW-indexed |

---

## Approval Tier Quick Reference (DD-003)

| Tier | Examples | UI |
|------|---------|-----|
| AUTO_EXECUTE | All `list_*`, `get_*`, `search_*` | No UI, proceeds immediately |
| DEFAULT | `create_issue`, `update_note`, `post_comment` | Inline approval card (24h) |
| CRITICAL | `delete_issue`, `archive_workspace`, `merge_pr` | Blocking modal (5-min auto-reject) |

---

## Skill Quick Reference (24 Skills)

| Category | Skills |
|----------|--------|
| Issues | `extract-issues`, `enhance-issue`, `find-duplicates`, `recommend-assignee`, `decompose-tasks` |
| Writing | `improve-writing`, `summarize`, `generate-pm-blocks` |
| Notes | `summarize-note`, `generate-diagram` |
| Planning | `daily-standup`, `generate-implementation-plan` |
| Documentation | `generate-docs`, `generate-api-docs` |
| Code | `generate-tests`, `review-code` |
| Session | `\resume` (session history), `\new` (fresh session) |

---

## Security Model

| Layer | Enforcement | Where |
|-------|-------------|-------|
| BYOK key encryption | Fernet AES-256, 600K PBKDF2 iterations | `key_storage.py` |
| RLS context per request | `set_rls_context(workspace_id, user_id, role)` | `agent_base.py` |
| Workspace isolation in queries | Explicit `WHERE workspace_id=...` | All MCP servers |
| Database-level RLS | PostgreSQL row policies | All tables |
| Approval gates (DD-003) | Permission check before every tool call | `permission_handler.py` |
| Per-user rate limiting | Sliding window, 60 req/min ghost text | `rate_limiter.py` |
| Sandbox filesystem isolation | `/sandbox/{user_id}/{workspace_id}/` only | `sandbox_config.py` |

---

## Files at a Glance

```
backend/src/pilot_space/ai/
├── README.md                          ← complete AI layer overview
├── agents/
│   ├── README.md                      ← agent-specific architecture
│   ├── pilotspace_agent.py            ← main orchestrator (~488 lines)
│   ├── pilotspace_intent_pipeline.py  ← routing table
│   ├── pilotspace_note_helpers.py     ← note context + chunking
│   ├── pilotspace_agent_helpers.py    ← workspace context + subagent routing
│   ├── pilotspace_stream_utils.py     ← SSE building, error wrapping
│   ├── sse_delta_buffer.py            ← 50ms token batching
│   ├── stream_event_transformer.py    ← SDK → 14 SSE types
│   ├── agent_base.py                  ← RLS, BYOK, retry, telemetry base
│   ├── types.py                       ← AgentTask, AIRequest types
│   ├── ai_context_agent.py            ← multi-turn context subagent
│   ├── plan_generation_agent.py       ← task decomposition (query-only)
│   ├── role_skill_materializer.py     ← role → SKILL.md filesystem
│   └── subagents/
│       ├── pr_review_subagent.py      ← 5-dimension PR review
│       └── doc_generator_subagent.py  ← multi-type doc generation
├── mcp/                               ← 6 in-process MCP servers, 33 tools
├── sdk/                               ← Claude Agent SDK integration (15 files)
├── skills/                            ← skill discovery + executor + versioning
├── prompt/                            ← prompt assembler + intent classifier
├── prompts/                           ← prompt templates per feature
├── providers/                         ← DD-011 routing + BYOK validation
├── infrastructure/                    ← cost, cache, key storage, rate limiter
├── services/ghost_text.py             ← independent <2.5s path
├── session/                           ← Redis + PG dual-store session
├── workers/                           ← digest + memory background workers
├── alerts/                            ← cost threshold alerts
├── analytics/                         ← token efficiency metrics
├── circuit_breaker.py                 ← 3-state CB per provider
├── degradation.py                     ← graceful feature fallbacks
└── telemetry.py                       ← Prometheus + structured metrics
```
