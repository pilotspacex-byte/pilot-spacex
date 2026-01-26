# Implementation Plan: MVP AI Agents Build with Claude Agent SDK

**Branch**: `004-mvp-agents-build` | **Date**: 2026-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-mvp-agents-build/spec.md`

**Note**: This plan migrates the Pilot Space AI layer from custom orchestration to Claude Agent SDK.

## Summary

Refactor and build all MVP AI agents (12 total) using Claude Agent SDK as the primary orchestration layer, replacing the current custom implementation with direct provider API calls. The migration introduces MCP tools for database/GitHub/search access, human-in-the-loop approval flows (DD-003), BYOK secure storage (DD-002), cost tracking, and session management for multi-turn conversations.

## Technical Context

**Language/Version**: Python 3.12+ (Backend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), claude-agent-sdk>=1.0,<2.0, anthropic, openai, google-generativeai
**Storage**: PostgreSQL 16+ with pgvector, Redis (sessions), Supabase Vault (key encryption)
**Testing**: pytest with >80% coverage, pytest-asyncio
**Target Platform**: Linux server (Docker/Kubernetes)
**Project Type**: Web application (backend API layer)
**Performance Goals**:
- Ghost text: <2s first token (p95)
- AI context: <30s completion (p95)
- PR review: <60s for PRs <1000 lines
- SSE first token: <1s
**Constraints**:
- File size ≤700 lines
- No blocking I/O in async functions
- BYOK model (no platform-hosted LLM)
- Human approval for critical actions
**Scale/Scope**: 5-100 team members per workspace, 50k+ issues

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. AI-Human Collaboration First** | ✅ PASS | ApprovalService implements DD-003 human-in-the-loop; AI suggestions require approval for critical actions |
| **II. Note-First Approach** | ✅ PASS | GhostTextAgent and MarginAnnotationAgent support Note Canvas; IssueExtractorAgent bridges notes to issues |
| **III. Documentation-Third Approach** | ✅ PASS | DocGeneratorAgent auto-generates docs from codebase |
| **IV. Task-Centric Workflow** | ✅ PASS | TaskDecomposerAgent breaks features into subtasks with AI-suggested acceptance criteria |
| **V. Collaboration & Knowledge Sharing** | ✅ PASS | DuplicateDetectorAgent, AssigneeRecommenderAgent enable team knowledge sharing |
| **VI. Agile Integration** | ✅ PASS | AIContextAgent generates sprint-ready implementation guides |
| **VII. Notation & Standards** | ✅ PASS | DiagramGeneratorAgent supports Mermaid, C4 Model diagrams |
| **Technology Standards** | ✅ PASS | FastAPI, PostgreSQL, Redis, BYOK, Claude Agent SDK per constitution |
| **Quality Gates** | ✅ PASS | All code passes ruff, pyright, pytest >80% coverage |

**Constitution Version**: 1.2.0

## Project Structure

### Documentation (this feature)

```text
specs/004-mvp-agents-build/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 entity definitions
├── quickstart.md        # Phase 1 developer guide
├── contracts/           # Phase 1 API contracts
│   ├── ai-endpoints.yaml
│   └── mcp-tools.yaml
└── tasks.md             # Phase 2 task breakdown
```

### Source Code (repository root)

```text
backend/src/pilot_space/ai/
├── __init__.py
├── config.py                           # AIConfig with provider settings
├── sdk_orchestrator.py                 # NEW: SDK-based orchestrator
│
├── agents/
│   ├── __init__.py
│   ├── sdk_base.py                     # NEW: SDK-based base agent
│   ├── ghost_text_agent.py             # REFACTOR: Use SDK streaming
│   ├── margin_annotation_agent.py      # REFACTOR: Use query()
│   ├── issue_extractor_agent.py        # REFACTOR: Use query()
│   ├── ai_context_agent.py             # REFACTOR: Use ClaudeSDKClient
│   ├── conversation_agent.py           # REFACTOR: Use ClaudeSDKClient
│   ├── pr_review_agent.py              # NEW: Unified review (DD-006)
│   ├── doc_generator_agent.py          # NEW: Use query()
│   ├── task_decomposer_agent.py        # NEW: Use query()
│   ├── diagram_generator_agent.py      # NEW: Use query()
│   ├── issue_enhancer_agent.py         # REFACTOR: Use query()
│   ├── assignee_recommender_agent.py   # REFACTOR: Use query()
│   └── duplicate_detector_agent.py     # REFACTOR: Use query()
│
├── tools/                              # NEW: MCP tool definitions
│   ├── __init__.py
│   ├── mcp_server.py                   # MCP server factory
│   ├── database_tools.py               # 7 tools: get_issue_context, etc.
│   ├── github_tools.py                 # 3 tools: get_pr_details, etc.
│   └── search_tools.py                 # 2 tools: semantic_search, etc.
│
├── infrastructure/                     # NEW: AI infrastructure
│   ├── __init__.py
│   ├── key_storage.py                  # SecureKeyStorage (DD-002)
│   ├── approval.py                     # ApprovalService (DD-003)
│   ├── cost_tracker.py                 # CostTracker with persistence
│   └── resilience.py                   # CircuitBreaker, retry
│
├── session/                            # NEW: Session management
│   ├── __init__.py
│   └── session_manager.py              # Redis-based sessions
│
├── providers/
│   ├── __init__.py
│   ├── provider_selector.py            # REFACTOR: DD-011 routing
│   └── mock.py                         # KEEP: Development mock
│
└── prompts/                            # Prompt templates
    ├── ghost_text.py
    ├── margin_annotation.py
    ├── issue_extraction.py
    ├── ai_context.py
    ├── pr_review.py                    # NEW
    ├── task_decomposition.py           # NEW
    └── diagram_generation.py           # NEW

backend/src/pilot_space/api/v1/routers/
├── ai.py                               # REFACTOR: SSE endpoints

backend/tests/
├── unit/ai/
│   ├── test_sdk_orchestrator.py        # NEW
│   ├── test_approval_service.py        # NEW
│   ├── test_cost_tracker.py            # NEW
│   ├── test_session_manager.py         # NEW
│   └── agents/
│       ├── test_ghost_text_agent.py    # UPDATE
│       ├── test_pr_review_agent.py     # NEW
│       └── ...
├── integration/ai/
│   ├── test_mcp_tools.py               # NEW
│   └── test_sdk_agents.py              # NEW
└── e2e/ai/
    └── test_ai_endpoints.py            # NEW
```

**Structure Decision**: Web application structure with backend AI layer refactoring. No frontend changes in this feature scope.

## Complexity Tracking

> No Constitution Check violations requiring justification.

---

## Phase 0: Research Topics

### Research Task 1: Claude Agent SDK API Patterns

**Question**: How does claude-agent-sdk implement `query()` vs `ClaudeSDKClient` for different use cases?

**Research Areas**:
- SDK import structure and version requirements
- `query()` function signature and streaming behavior
- `ClaudeSDKClient` context manager pattern for multi-turn
- MCP tool registration via `@tool` decorator
- Error handling and retry behavior built into SDK

**Expected Output**: Code patterns for one-shot vs multi-turn agents

### Research Task 2: MCP Tool Definition Patterns

**Question**: How to define MCP tools that integrate with Pilot Space repositories?

**Research Areas**:
- `@tool` decorator parameters and schema definition
- Async tool implementation with database access
- Permission model (read-only vs write tools)
- Tool result formatting for agent consumption

**Expected Output**: MCP tool template with repository integration

### Research Task 3: SSE Streaming with SDK

**Question**: How to stream SDK responses through FastAPI SSE endpoints?

**Research Areas**:
- SDK `query()` async iterator pattern
- FastAPI `StreamingResponse` integration
- Error handling during stream
- Connection management and timeouts

**Expected Output**: SSE endpoint pattern with SDK streaming

### Research Task 4: Supabase Vault Integration

**Question**: How to use Supabase Vault for API key encryption at rest?

**Research Areas**:
- Vault encryption/decryption API
- Key rotation patterns
- Audit logging for key access
- Performance implications

**Expected Output**: SecureKeyStorage implementation pattern

### Research Task 5: Session Management for Multi-Turn

**Question**: How to manage multi-turn conversation state with session limits?

**Research Areas**:
- Redis session storage schema
- Message truncation when exceeding 20 messages / 8000 tokens
- Session TTL and cleanup
- Conversation history serialization

**Expected Output**: SessionManager implementation pattern

---

## Phase 1: Design Artifacts

### 1.1 Data Model (data-model.md)

**New Entities**:

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| `WorkspaceAPIKey` | BYOK API key storage | workspace_id, provider, encrypted_key, validation_status |
| `AIApprovalRequest` | Human-in-the-loop approvals | action_type, payload, status, expires_at |
| `AICostRecord` | Usage tracking | agent_type, provider, input_tokens, output_tokens, cost_usd |
| `AISession` | Multi-turn state | session_id, messages, context, total_cost |

**Database Migrations**:
- `add_workspace_api_keys_table.py`
- `add_ai_approval_requests_table.py`
- `add_ai_cost_records_table.py`
- `add_ai_sessions_table.py`

### 1.2 API Contracts (contracts/)

**AI Endpoints** (ai-endpoints.yaml):

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/v1/ai/notes/{note_id}/ghost-text` | POST | Stream ghost text | SSE |
| `/api/v1/ai/notes/{note_id}/annotations` | POST | Generate annotations | SSE |
| `/api/v1/ai/notes/{note_id}/extract-issues` | POST | Extract issues | SSE |
| `/api/v1/ai/issues/{issue_id}/context` | POST | Build AI context | SSE |
| `/api/v1/ai/prs/{pr_number}/review` | POST | Unified PR review | SSE |
| `/api/v1/ai/conversation` | POST | Multi-turn chat | SSE |
| `/api/v1/ai/approvals` | GET | List pending approvals | JSON |
| `/api/v1/ai/approvals/{id}/resolve` | POST | Approve/reject | JSON |
| `/api/v1/ai/costs/summary` | GET | Cost analytics | JSON |
| `/api/v1/workspaces/{id}/ai/settings` | GET/PUT | AI configuration | JSON |

**MCP Tools** (mcp-tools.yaml):

| Tool | Category | Permission | Purpose |
|------|----------|------------|---------|
| `get_issue_context` | Database | Read-only | Fetch issue with relations |
| `get_note_content` | Database | Read-only | Fetch note blocks |
| `get_project_context` | Database | Read-only | Fetch project settings |
| `find_similar_issues` | Database | Read-only | Embedding similarity search |
| `search_codebase` | Search | Read-only | Code search in repo |
| `semantic_search` | Search | Read-only | pgvector semantic search |
| `get_pr_details` | GitHub | Read-only | Fetch PR metadata |
| `get_pr_diff` | GitHub | Read-only | Fetch PR diff |
| `search_code_in_repo` | GitHub | Read-only | Search code in GitHub |
| `create_note_annotation` | Database | Write | Create annotation |
| `create_issue` | Database | Write | Create issue (requires approval) |
| `post_pr_comment` | GitHub | Write | Post review comment |

### 1.3 Agent Architecture

**Agent Classification**:

| Agent | SDK Pattern | Model | Max Budget | Tools Required |
|-------|-------------|-------|------------|----------------|
| GhostTextAgent | `query()` one-shot | claude-4-5-haiku | $0.01 | None |
| MarginAnnotationAgent | `query()` one-shot | claude-sonnet-4-5 | $0.10 | get_note_content |
| IssueExtractorAgent | `query()` one-shot | claude-sonnet-4-5 | $0.20 | get_note_content |
| AIContextAgent | `ClaudeSDKClient` multi-turn | claude-opus-4-5 | $10.00 | All read tools |
| ConversationAgent | `ClaudeSDKClient` multi-turn | claude-sonnet-4-5 | $5.00 | Contextual |
| PRReviewAgent | `query()` one-shot | claude-opus-4-5 | $20.00 | get_pr_diff, search_codebase |
| DocGeneratorAgent | `query()` one-shot | claude-sonnet-4-5 | $5.00 | search_codebase, semantic_search |
| TaskDecomposerAgent | `query()` one-shot | claude-opus-4-5 | $5.00 | get_issue_context |
| DiagramGeneratorAgent | `query()` one-shot | claude-sonnet-4-5 | $2.00 | get_issue_context |
| IssueEnhancerAgent | `query()` one-shot | claude-sonnet-4-5 | $0.50 | get_project_context |
| AssigneeRecommenderAgent | `query()` one-shot | claude-4-5-haiku | $0.10 | get_issue_context |
| DuplicateDetectorAgent | `query()` one-shot | claude-sonnet-4-5 | $0.50 | find_similar_issues |

---

## Phase 2: Implementation Phases

### Phase 2.1: Infrastructure Foundation

**Tasks**: T001-T012

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T001 | Create `ai/tools/mcp_server.py` with factory function | - | P0 |
| T002 | Implement `database_tools.py` (7 tools) | T001 | P0 |
| T003 | Implement `github_tools.py` (3 tools) | T001 | P1 |
| T004 | Implement `search_tools.py` (2 tools) | T001 | P1 |
| T005 | Create `infrastructure/key_storage.py` (DD-002) | - | P0 |
| T006 | Create `infrastructure/approval.py` (DD-003) | - | P0 |
| T007 | Create `infrastructure/cost_tracker.py` | - | P1 |
| T008 | Create `session/session_manager.py` | - | P1 |
| T009 | Add database migration: workspace_api_keys | T005 | P0 |
| T010 | Add database migration: ai_approval_requests | T006 | P0 |
| T011 | Add database migration: ai_cost_records | T007 | P1 |
| T012 | Refactor `providers/provider_selector.py` (DD-011) | - | P0 |

**Validation**: Unit tests for all infrastructure components

### Phase 2.2: SDK Base & Orchestrator

**Tasks**: T013-T018

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T013 | Create `agents/sdk_base.py` with BaseAgent | T001 | P0 |
| T014 | Create `sdk_orchestrator.py` | T013, T005, T006, T007 | P0 |
| T015 | Update `container.py` with new DI providers | T014 | P0 |
| T016 | Update `api/v1/routers/ai.py` SSE endpoints | T014 | P0 |
| T017 | Add approval endpoints to router | T006, T016 | P1 |
| T018 | Add cost tracking endpoints to router | T007, T016 | P2 |

**Validation**: Integration tests for orchestrator with mock provider

### Phase 2.3: Agent Migration (P0 Agents)

**Tasks**: T019-T026

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T019 | Migrate GhostTextAgent to SDK | T013 | P0 |
| T020 | Migrate AIContextAgent to ClaudeSDKClient | T013, T002, T004 | P0 |
| T021 | Migrate IssueExtractorAgent to SDK | T013, T002 | P0 |
| T022 | Implement PRReviewAgent (DD-006) | T013, T003 | P0 |
| T023 | Update prompts/ghost_text.py | T019 | P0 |
| T024 | Update prompts/ai_context.py | T020 | P0 |
| T025 | Create prompts/pr_review.py | T022 | P0 |
| T026 | Unit tests for P0 agents | T019-T022 | P0 |

**Validation**: All P0 agents pass unit tests with mock provider

### Phase 2.4: Agent Migration (P1 Agents)

**Tasks**: T027-T036

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T027 | Migrate MarginAnnotationAgent to SDK | T013, T002 | P1 |
| T028 | Migrate ConversationAgent to ClaudeSDKClient | T013, T008 | P1 |
| T029 | Implement DocGeneratorAgent | T013, T004 | P1 |
| T030 | Implement TaskDecomposerAgent | T013, T002 | P1 |
| T031 | Migrate IssueEnhancerAgent to SDK | T013, T002 | P1 |
| T032 | Migrate DuplicateDetectorAgent to SDK | T013, T002 | P1 |
| T033 | Create prompts/task_decomposition.py | T030 | P1 |
| T034 | Update prompts/margin_annotation.py | T027 | P1 |
| T035 | Update prompts/issue_extraction.py | T021 | P1 |
| T036 | Unit tests for P1 agents | T027-T032 | P1 |

**Validation**: All P1 agents pass unit tests

### Phase 2.5: Agent Migration (P2 Agents)

**Tasks**: T037-T042

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T037 | Implement DiagramGeneratorAgent | T013, T002 | P2 |
| T038 | Migrate AssigneeRecommenderAgent to SDK | T013, T002 | P2 |
| T039 | Create prompts/diagram_generation.py | T037 | P2 |
| T040 | Update prompts/issue_enhancement.py | T031 | P2 |
| T041 | Unit tests for P2 agents | T037-T038 | P2 |
| T042 | Integration tests for all agents | T026, T036, T041 | P2 |

**Validation**: All agents pass integration tests

### Phase 2.6: E2E & Polish

**Tasks**: T043-T050

| ID | Task | Dependencies | Priority |
|----|------|--------------|----------|
| T043 | E2E tests for SSE endpoints | T042 | P1 |
| T044 | E2E tests for approval flow | T017, T043 | P1 |
| T045 | E2E tests for cost tracking | T018, T043 | P2 |
| T046 | Performance benchmarks (ghost text <2s) | T043 | P1 |
| T047 | Security audit (key storage, approval bypass) | T005, T006 | P0 |
| T048 | Documentation: quickstart.md | T042 | P2 |
| T049 | Documentation: API contracts | T042 | P2 |
| T050 | Remove deprecated orchestrator.py | T042 | P2 |

**Validation**: All E2E tests pass, performance SLOs met

---

## Quality Gates

### Pre-Merge Checklist

- [ ] `uv run ruff check .` passes
- [ ] `uv run pyright` passes
- [ ] `uv run pytest --cov=pilot_space.ai --cov-report=term-missing` >80%
- [ ] No N+1 queries in MCP tools
- [ ] No blocking I/O in async functions
- [ ] All files ≤700 lines
- [ ] No TODOs or placeholder code
- [ ] RFC 7807 errors for all API endpoints
- [ ] Human-in-the-loop verified for critical actions
- [ ] API keys never logged or exposed

### Performance Validation

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| Ghost text first token | <2s (p95) | `test_ghost_text_latency` |
| AI context completion | <30s (p95) | `test_ai_context_latency` |
| PR review completion | <60s (<1000 lines) | `test_pr_review_latency` |
| SSE first token | <1s | `test_sse_first_token` |
| Approval flow roundtrip | <500ms | `test_approval_latency` |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Claude Agent SDK API changes | Pin to minor version (>=1.0,<2.0) |
| Provider rate limits | Circuit breaker with 30s recovery |
| Session token overflow | FIFO truncation at 8000 tokens |
| Key storage breach | Supabase Vault encryption + audit logs |
| Approval bypass | Always-require list cannot be overridden |

---

## Deliverables

1. **Infrastructure** (Phase 2.1): MCP server, key storage, approval service, cost tracker, session manager
2. **Orchestrator** (Phase 2.2): SDK-based orchestrator with DI integration
3. **Agents** (Phase 2.3-2.5): 12 agents migrated/implemented with SDK patterns
4. **API** (Phase 2.2): SSE endpoints, approval endpoints, cost endpoints
5. **Tests** (Phase 2.6): Unit, integration, E2E tests with >80% coverage
6. **Documentation** (Phase 2.6): quickstart.md, API contracts

---

## Next Steps

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Create feature branch `004-mvp-agents-build`
3. Begin Phase 2.1 infrastructure foundation
