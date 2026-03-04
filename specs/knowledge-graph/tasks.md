# Knowledge Graph — Dependency-Ordered Task Breakdown

**Version**: 1.0.0
**Created**: 2026-03-03
**Status**: Approved
**Companion docs**: `plan.md`, `ui-design-spec.md`

---

## Task Index

| Unit | Tasks | Phase | Size | Status |
|------|-------|-------|------|--------|
| U-01 | T-001 | 0 | M | Done (this document) |
| U-02 | T-002 – T-006 | 1 | L | Pending |
| U-03 | T-007 – T-010 | 2a | L | Pending |
| U-04 | T-011 – T-014 | 2b | M | Pending |
| U-05 | T-015 – T-019 | 3 | M | Pending |
| U-06 | T-020 – T-023 | 4a | M | Pending |
| U-07 | T-024 – T-026 | 4b | S | Pending |
| U-08 | T-027 – T-032 | 5 | M | Pending |
| U-09 | T-033 – T-036 | 6a | S | Pending |
| U-10 | T-037 – T-041 | 6b | M | Pending |
| U-11 | T-042 – T-048 | 6c | L | Pending |
| U-12 | T-049 – T-054 | 6d+6e | M | Pending |
| U-13 | T-055 – T-062 | 6f+6g+6h+7 | L | Pending |

---

## Unit 1 — Planning & Design Specs (Phase 0)

### T-001: Create architecture plan, UI design spec, and task breakdown

**Description**: Produce the three foundational specification documents for the knowledge graph feature. No code is written in this unit.

**Files Created**:
- `specs/knowledge-graph/plan.md`
- `specs/knowledge-graph/ui-design-spec.md`
- `specs/knowledge-graph/tasks.md`

**Dependencies**: None

**Size**: M

**Phase**: 0

**Acceptance Criteria**:
- [ ] `plan.md` covers all 9 sections listed in the plan requirements
- [ ] `ui-design-spec.md` covers all 10 sections with ASCII mockups for every component
- [ ] `tasks.md` lists all 13 units with dependencies, sizes, and acceptance criteria
- [ ] Schema decision (adjacency tables) is documented with rationale
- [ ] Embedding model decision (OpenAI 1536-dim) is documented with rationale
- [ ] API contracts cover all 5 endpoints with request/response shapes
- [ ] Design tokens are defined as CSS custom properties

---

## Unit 2 — Schema + Domain Entities (Phase 1)

### T-002: Create Alembic migration for graph_nodes and graph_edges

**Description**: Create the database migration that adds `graph_nodes` and `graph_edges` tables, both ENUMs, all indexes, and RLS policies. Adds `migrated_at` column to `memory_entries`. Does NOT drop any existing tables.

**Files Created**:
- `backend/alembic/versions/{N}_add_knowledge_graph_tables.py`

**Dependencies**: T-001

**Size**: M

**Phase**: 1

**Acceptance Criteria**:
- [ ] Migration creates `graph_node_type` and `graph_edge_type` ENUM types with all values from plan.md
- [ ] `graph_nodes` table matches schema in plan.md Section 3 exactly (all columns, types, constraints)
- [ ] `graph_edges` table matches schema in plan.md Section 3 exactly with UNIQUE (source_id, target_id, edge_type)
- [ ] HNSW cosine index created on `graph_nodes.embedding` (vector_cosine_ops)
- [ ] GIN FTS index created on `to_tsvector('english', content)`
- [ ] GIN index on `graph_nodes.properties`
- [ ] All B-tree indexes from plan.md Section 3 created
- [ ] RLS enabled and forced on both tables (following `rls-check.md`)
- [ ] Workspace isolation policy uses `current_setting('app.current_user_id', true)::uuid`
- [ ] Service_role bypass policy present on both tables
- [ ] `memory_entries.migrated_at TIMESTAMPTZ` column added
- [ ] `downgrade()` reverses all changes (drops tables, drops ENUMs, drops column)
- [ ] `alembic heads` shows single head after migration
- [ ] `alembic check` passes

---

### T-003: Define graph domain entities

**Description**: Create pure Python domain dataclasses for `GraphNode`, `GraphEdge`, and typed subtypes. No SQLAlchemy or infrastructure dependencies.

**Files Created**:
- `backend/src/pilot_space/domain/graph_node.py`
- `backend/src/pilot_space/domain/graph_edge.py`

**Dependencies**: T-001

**Size**: M

**Phase**: 1

**Acceptance Criteria**:
- [ ] `GraphNode` dataclass with all fields matching plan.md schema (id, workspace_id, user_id, node_type, external_id, label, content, properties, embedding, created_at, updated_at)
- [ ] `NodeType` string enum with all 14 values from plan.md
- [ ] `EdgeType` string enum with all 13 values from plan.md
- [ ] `GraphEdge` dataclass with all fields (id, source_id, target_id, edge_type, properties, weight, created_at)
- [ ] `GraphQuery` value object (query_text, workspace_id, user_id, node_types, limit, depth)
- [ ] `GraphContext` result container (nodes: list[ScoredNode], edges: list[GraphEdge])
- [ ] `ScoredNode` wraps GraphNode + score float
- [ ] No SQLAlchemy imports in domain files
- [ ] Full type hints, pyright strict-compatible
- [ ] Domain files < 700 lines

---

### T-004: Create SQLAlchemy ORM models

**Description**: SQLAlchemy 2.0 async models for `graph_nodes` and `graph_edges` tables, with pgvector `Vector(1536)` and SQLite fallback for tests.

**Files Created**:
- `backend/src/pilot_space/infrastructure/database/models/graph_node.py`
- `backend/src/pilot_space/infrastructure/database/models/graph_edge.py`

**Dependencies**: T-002, T-003

**Size**: S

**Phase**: 1

**Acceptance Criteria**:
- [ ] `GraphNodeModel` maps all columns from T-002 migration
- [ ] `GraphEdgeModel` maps all columns from T-002 migration
- [ ] `Vector(1536)` from pgvector used for embedding column
- [ ] SQLite fallback: `Text` type when pgvector not available (for test compatibility)
- [ ] Relationships: `GraphNodeModel.outgoing_edges`, `GraphNodeModel.incoming_edges`
- [ ] `__tablename__` matches migration table names exactly
- [ ] Full type annotations (MappedColumn, Mapped)
- [ ] Models < 150 lines each

---

### T-005: Unit tests for domain entities

**Description**: pytest unit tests for all domain dataclasses and value objects.

**Files Created**:
- `backend/tests/unit/domain/test_graph_node.py`
- `backend/tests/unit/domain/test_graph_edge.py`

**Dependencies**: T-003

**Size**: S

**Phase**: 1

**Acceptance Criteria**:
- [ ] Test NodeType enum has all 14 values
- [ ] Test EdgeType enum has all 13 values
- [ ] Test GraphNode construction with all required fields
- [ ] Test GraphNode with optional fields (user_id=None, external_id=None, embedding=None)
- [ ] Test GraphEdge weight validation (0.0–1.0)
- [ ] Test GraphEdge UNIQUE constraint logic (source, target, type combination)
- [ ] Test ScoredNode score range (0.0–1.0)
- [ ] All tests pass with `uv run pytest tests/unit/domain/`

---

### T-006: Update `__init__.py` barrel exports

**Description**: Add new domain and model exports to existing barrel files.

**Files Modified**:
- `backend/src/pilot_space/domain/__init__.py`
- `backend/src/pilot_space/infrastructure/database/models/__init__.py`

**Dependencies**: T-003, T-004

**Size**: S (< 1 hour)

**Phase**: 1

**Acceptance Criteria**:
- [ ] `domain/__init__.py` exports `GraphNode`, `GraphEdge`, `NodeType`, `EdgeType`, `GraphQuery`, `GraphContext`, `ScoredNode`
- [ ] `models/__init__.py` exports `GraphNodeModel`, `GraphEdgeModel`
- [ ] No circular import errors
- [ ] `uv run pyright` passes with no new errors

---

## Unit 3 — Repository Layer (Phase 2a)

### T-007: Implement `KnowledgeGraphRepository` — CRUD methods

**Description**: Core repository with upsert_node, upsert_edge, get_node, delete_expired_nodes.

**Files Created**:
- `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py`

**Dependencies**: T-004, T-006

**Size**: M

**Phase**: 2a

**Acceptance Criteria**:
- [ ] `upsert_node(node: GraphNode) -> GraphNode` — idempotent by (external_id, node_type, workspace_id)
- [ ] `upsert_edge(edge: GraphEdge) -> GraphEdge` — idempotent by (source_id, target_id, edge_type)
- [ ] `get_node(node_id: UUID) -> GraphNode | None`
- [ ] `delete_expired_nodes(before: datetime) -> int` — deletes non-domain AI artifact nodes older than cutoff
- [ ] `bulk_upsert_nodes(nodes: list[GraphNode]) -> list[GraphNode]` — batch insert in chunks of 100
- [ ] All methods are `async`, use SQLAlchemy 2.0 async session
- [ ] `set_rls_context()` called before every workspace-scoped query
- [ ] `selectinload` used for relationship loading (no N+1)
- [ ] File < 700 lines

---

### T-008: Implement `KnowledgeGraphRepository` — hybrid search

**Description**: The hybrid search query combining pgvector cosine similarity + tsvector full-text + recency + edge density scoring.

**Files Modified**:
- `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py`

**Dependencies**: T-007

**Size**: M

**Phase**: 2a

**Acceptance Criteria**:
- [ ] `hybrid_search(query_embedding, query_text, workspace_id, node_types, limit) -> list[ScoredNode]`
- [ ] Scoring formula: `0.5 * (1 - cosine_distance) + 0.2 * ts_rank + 0.2 * recency_score + 0.1 * edge_density_score`
- [ ] Falls back to `ts_rank`-only when `query_embedding is None`
- [ ] `node_types` filter applied when provided
- [ ] User-scoped nodes (`user_id IS NOT NULL`) filtered to requesting user_id
- [ ] Results ordered by score descending
- [ ] Limit respected (default 20)
- [ ] Query executes in < 200ms on typical dataset (tested manually)

---

### T-009: Implement `KnowledgeGraphRepository` — graph traversal

**Description**: BFS neighbor traversal and subgraph extraction using recursive CTEs.

**Files Modified**:
- `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py`

**Dependencies**: T-007

**Size**: M

**Phase**: 2a

**Acceptance Criteria**:
- [ ] `get_neighbors(node_id, edge_types, depth=1) -> list[GraphNode]` — BFS using recursive CTE
- [ ] `get_subgraph(root_id, max_depth=2, max_nodes=50) -> tuple[list[GraphNode], list[GraphEdge]]`
- [ ] Recursive CTE depth-limited by `max_depth` parameter
- [ ] `max_nodes` cap applied with priority: Issue/Note/Decision > PR/Branch/CodeRef > User/Pattern > Summary/SkillOutcome
- [ ] `get_user_context(user_id, workspace_id) -> list[GraphNode]` — returns user-scoped nodes + recent workspace interactions
- [ ] All workspace_id RLS context set before queries
- [ ] Duplicate nodes deduplicated in CTE result

---

### T-010: Repository unit tests

**Description**: pytest tests for all repository methods using SQLite in-memory (non-pgvector tests) and documented PostgreSQL-specific behavior.

**Files Created**:
- `backend/tests/unit/infrastructure/test_knowledge_graph_repository.py`

**Dependencies**: T-007, T-008, T-009

**Size**: M

**Phase**: 2a

**Acceptance Criteria**:
- [ ] Test `upsert_node` is idempotent (calling twice produces one row)
- [ ] Test `upsert_edge` is idempotent
- [ ] Test `get_neighbors` returns correct 1-hop neighbors
- [ ] Test `get_subgraph` respects `max_depth` limit
- [ ] Test `bulk_upsert_nodes` correctly inserts batch of nodes
- [ ] Test `hybrid_search` falls back to keyword-only when embedding is None
- [ ] Tests use `db_session` fixture from `conftest.py`
- [ ] Test file notes that pgvector-specific tests require `TEST_DATABASE_URL` (PostgreSQL)
- [ ] Coverage ≥ 80% for repository file

---

## Unit 4 — Application Services + DI (Phase 2b)

### T-011: Implement `GraphSearchService`

**Description**: Application service that wraps the repository's hybrid search, adds embedding via OpenAI, and 1-hop expansion.

**Files Created**:
- `backend/src/pilot_space/application/services/memory/graph_search_service.py`

**Dependencies**: T-009, T-010

**Size**: M

**Phase**: 2b

**Acceptance Criteria**:
- [ ] `GraphSearchService.search(payload: GraphSearchPayload) -> GraphSearchResult`
- [ ] `GraphSearchPayload(query, workspace_id, user_id, node_types, limit=10)`
- [ ] `GraphSearchResult(nodes: list[ScoredNode], edges: list[GraphEdge], query, embedding_used: bool)`
- [ ] Calls OpenAI `text-embedding-3-large` via `provider_selector.py` (TaskType.EMBEDDINGS)
- [ ] Falls back to keyword-only if OpenAI call fails
- [ ] 1-hop neighbor expansion for top-10 results
- [ ] Merges user-scoped nodes with workspace-scoped results
- [ ] Exponential backoff on OpenAI call (1s, 2s, 4s — 3 retries)
- [ ] No `google_api_key` dependency — OpenAI only

---

### T-012: Implement `GraphWriteService`

**Description**: Application service for transactional node + edge upsert with embedding job enqueue.

**Files Created**:
- `backend/src/pilot_space/application/services/memory/graph_write_service.py`

**Dependencies**: T-009, T-010

**Size**: M

**Phase**: 2b

**Acceptance Criteria**:
- [ ] `GraphWriteService.write(payload: GraphWritePayload) -> GraphWriteResult`
- [ ] `GraphWritePayload(workspace_id, user_id, nodes: list[NodeInput], edges: list[EdgeInput])`
- [ ] `GraphWriteResult(node_ids: list[UUID], edge_ids: list[UUID], embedding_enqueued: bool)`
- [ ] Nodes and edges upserted in single transaction
- [ ] Embedding job enqueued to pgmq queue for each new/updated node
- [ ] Auto-edge detection: if node content contains UUID matching another node's external_id → create `RELATES_TO` edge
- [ ] Returns IDs of all persisted nodes and edges

---

### T-013: Wire services into DI container

**Description**: Register `GraphSearchService`, `GraphWriteService`, and `KnowledgeGraphRepository` in `container.py`.

**Files Modified**:
- `backend/src/pilot_space/container/container.py`

**Dependencies**: T-011, T-012

**Size**: S

**Phase**: 2b

**Acceptance Criteria**:
- [ ] `knowledge_graph_repository` registered as `providers.Factory`
- [ ] `graph_search_service` registered as `providers.Factory` with injected repository + provider_selector
- [ ] `graph_write_service` registered as `providers.Factory` with injected repository + queue
- [ ] Old `memory_search_service` and `memory_save_service` remain registered (not removed yet — parallel operation)
- [ ] New services added to `wiring_config.modules` if needed
- [ ] `uv run pyright` passes with no new errors

---

### T-014: Service unit tests

**Description**: pytest tests for `GraphSearchService` and `GraphWriteService` with mocked repository.

**Files Created**:
- `backend/tests/unit/application/test_graph_search_service.py`
- `backend/tests/unit/application/test_graph_write_service.py`

**Dependencies**: T-011, T-012

**Size**: S

**Phase**: 2b

**Acceptance Criteria**:
- [ ] Test search with embedding available → returns scored nodes
- [ ] Test search with embedding failure → falls back to keyword-only
- [ ] Test write creates nodes and edges and enqueues embedding jobs
- [ ] Test write is idempotent (duplicate nodes not doubled)
- [ ] Mock `KnowledgeGraphRepository` using `unittest.mock.AsyncMock`
- [ ] Coverage ≥ 80% for service files

---

## Unit 5 — Agent Integration (Phase 3)

### T-015: Replace `recall_workspace_context` with `recall_graph_context`

**Description**: Modify `ai/agents/pilotspace_intent_pipeline.py` to use `GraphSearchService` instead of `MemorySearchService`.

**Files Modified**:
- `backend/src/pilot_space/ai/agents/pilotspace_intent_pipeline.py`

**Dependencies**: T-013, T-014

**Size**: S

**Phase**: 3

**Acceptance Criteria**:
- [ ] `recall_graph_context(workspace_id, user_id, query, graph_search_service) -> GraphContext | None`
- [ ] Calls `graph_search_service.search()` with user_id included
- [ ] Returns `None` (no exception) if search service unavailable
- [ ] Old `recall_workspace_context` removed
- [ ] `uv run pyright` passes

---

### T-016: Replace `save_skill_outcome_to_memory` with `extract_and_persist_to_graph`

**Description**: After-stream hook that calls `GraphExtractionService` (stub in this unit, full impl in U-06) then `GraphWriteService`.

**Files Modified**:
- `backend/src/pilot_space/ai/agents/pilotspace_intent_pipeline.py`

**Dependencies**: T-015

**Size**: S

**Phase**: 3

**Acceptance Criteria**:
- [ ] `extract_and_persist_to_graph(messages, workspace_id, user_id, graph_write_service) -> None`
- [ ] Falls back to saving last-500-chars as `skill_outcome` node if extraction service unavailable (no regression)
- [ ] Old `save_skill_outcome_to_memory` removed
- [ ] Called in `PilotSpaceAgent._stream_with_space` finally block

---

### T-017: Update prompt assembler Layer 5

**Description**: Rewrite the `## Workspace Memory Context` section of the prompt to use structured graph context.

**Files Modified**:
- `backend/src/pilot_space/ai/prompt/prompt_assembler.py`

**Dependencies**: T-015

**Size**: S

**Phase**: 3

**Acceptance Criteria**:
- [ ] Layer 5 now renders structured sections: "Relevant Entities", "Your Context", "Learned Patterns"
- [ ] Each entity includes its type, label, and related entity labels
- [ ] Empty sections are omitted (not rendered as empty headers)
- [ ] Total Layer 5 content stays under 1500 tokens (checked via `len(content) < 6000` char guard)

---

### T-018: Fix embedding API key wiring in `PilotSpaceAgent`

**Description**: Ensure `graph_search_service` and `graph_write_service` are properly injected into `PilotSpaceAgent` via the DI container. Fix the root cause of the silent memory no-op bug.

**Files Modified**:
- `backend/src/pilot_space/ai/agents/pilotspace_agent.py`
- `backend/src/pilot_space/container/_factories.py`

**Dependencies**: T-013, T-017

**Size**: S

**Phase**: 3

**Acceptance Criteria**:
- [ ] `create_pilotspace_agent()` in `_factories.py` injects `graph_search_service` and `graph_write_service`
- [ ] `PilotSpaceAgent.__init__` accepts `graph_search_service` and `graph_write_service` parameters
- [ ] No `google_api_key` references in the embedding path
- [ ] Integration test confirms `recall_graph_context` is called before stream and returns non-empty results

---

### T-019: Agent integration tests

**Description**: Integration tests for the full recall → stream → persist cycle.

**Files Created**:
- `backend/tests/integration/test_agent_graph_integration.py`

**Dependencies**: T-016, T-018

**Size**: M

**Phase**: 3

**Acceptance Criteria**:
- [ ] Test: send message → recall returns graph context → graph context injected into Layer 5
- [ ] Test: stream completes → graph nodes persisted via write service
- [ ] Test: embedding service unavailable → graceful degradation (keyword fallback)
- [ ] Tests use mocked LLM (no real API calls)
- [ ] Tests note that PostgreSQL required for RLS-dependent assertions

---

## Unit 6 — Extraction Service (Phase 4a)

### T-020: Implement `GraphExtractionService`

**Description**: LLM-powered service that reads conversation messages and extracts entities and relationships as graph nodes and edges.

**Files Created**:
- `backend/src/pilot_space/application/services/memory/graph_extraction_service.py`

**Dependencies**: T-013

**Size**: M

**Phase**: 4a

**Acceptance Criteria**:
- [ ] `GraphExtractionService.extract(payload: ConversationExtractionPayload) -> ExtractionResult`
- [ ] `ConversationExtractionPayload(messages: list[AIMessage], workspace_id, user_id)`
- [ ] `ExtractionResult(nodes: list[NodeInput], edges: list[EdgeInput])`
- [ ] Uses cheapest available model (claude-haiku or equivalent via `provider_selector`)
- [ ] Extraction prompt returns structured JSON: `{ nodes: [...], edges: [...] }`
- [ ] Extracts: Decisions, LearnedPatterns, UserPreferences, WorkIntents from conversation
- [ ] Creates edges between extracted nodes and referenced entity IDs
- [ ] Skips extraction if conversation < 3 messages (cost gate)
- [ ] Handles malformed LLM JSON output gracefully (logs warning, returns empty ExtractionResult)

---

### T-021: Auto-edge detection in `GraphWriteService`

**Description**: After upsert, scan node content for UUID references matching other nodes and create implicit RELATES_TO edges.

**Files Modified**:
- `backend/src/pilot_space/application/services/memory/graph_write_service.py`

**Dependencies**: T-012, T-020

**Size**: S

**Phase**: 4a

**Acceptance Criteria**:
- [ ] UUID regex scan on `node.content` and `node.properties`
- [ ] For each UUID found: query `graph_nodes` for matching `external_id` in same workspace
- [ ] If match found: upsert `RELATES_TO` edge with weight=0.5
- [ ] Max 10 auto-edges per node (prevent explosion)
- [ ] Auto-edges marked in `edge.properties["auto_generated"] = True`

---

### T-022: Wire extraction service into DI container

**Description**: Register `GraphExtractionService` in DI container.

**Files Modified**:
- `backend/src/pilot_space/container/container.py`

**Dependencies**: T-020

**Size**: S (< 30 min)

**Phase**: 4a

**Acceptance Criteria**:
- [ ] `graph_extraction_service` registered as `providers.Factory`
- [ ] Injected with `provider_selector` for LLM calls
- [ ] Wired into modules list if using `@inject`

---

### T-023: Extraction service tests

**Description**: Unit tests for `GraphExtractionService` with mocked LLM.

**Files Created**:
- `backend/tests/unit/application/test_graph_extraction_service.py`

**Dependencies**: T-020

**Size**: S

**Phase**: 4a

**Acceptance Criteria**:
- [ ] Test: conversation with decision statement → produces `DecisionNode`
- [ ] Test: conversation < 3 messages → returns empty ExtractionResult
- [ ] Test: malformed LLM JSON → returns empty ExtractionResult, no exception
- [ ] Test: user preference expressed → produces `UserPreferenceNode`
- [ ] Mock `provider_selector` with fixed JSON response

---

## Unit 7 — Embedding Worker (Phase 4b)

### T-024: Update embedding worker for 1536-dim + new node types

**Description**: Modify `memory_embedding_handler.py` to handle `graph_nodes` embedding requests with OpenAI 1536-dim vectors.

**Files Modified**:
- `backend/src/pilot_space/infrastructure/queue/handlers/memory_embedding_handler.py`

**Dependencies**: T-013

**Size**: S

**Phase**: 4b

**Acceptance Criteria**:
- [ ] Worker handles a new job type: `graph_node_embedding` (in addition to existing `memory_embedding`)
- [ ] Job payload: `{ "node_id": UUID, "content": str }`
- [ ] Calls OpenAI `text-embedding-3-large` via `provider_selector`
- [ ] Stores result as `vector(1536)` in `graph_nodes.embedding`
- [ ] Exponential backoff on OpenAI failure (1s, 2s, 4s — max 3 retries)
- [ ] Job marked failed (not retried indefinitely) after 3 failures

---

### T-025: Update `GraphWriteService` to enqueue correct job type

**Description**: Ensure `GraphWriteService` enqueues `graph_node_embedding` jobs after node upsert.

**Files Modified**:
- `backend/src/pilot_space/application/services/memory/graph_write_service.py`

**Dependencies**: T-024

**Size**: S (< 30 min)

**Phase**: 4b

**Acceptance Criteria**:
- [ ] Enqueued job type is `graph_node_embedding`
- [ ] Job payload includes `node_id` and `content`
- [ ] Jobs enqueued in a batch (one `pgmq.send_batch()` call per write, not N individual calls)

---

### T-026: Embedding worker tests

**Description**: Unit tests for the updated embedding worker.

**Files Created/Modified**:
- `backend/tests/unit/infrastructure/test_memory_embedding_handler.py`

**Dependencies**: T-024, T-025

**Size**: S

**Phase**: 4b

**Acceptance Criteria**:
- [ ] Test: valid job → calls OpenAI → stores embedding
- [ ] Test: OpenAI failure → retries 3 times then marks failed
- [ ] Test: unknown job type → logs warning, no crash
- [ ] Mock OpenAI client

---

## Unit 8 — REST API Endpoints (Phase 5)

### T-027: Define Pydantic response schemas

**Description**: Create the `GraphNodeDTO`, `GraphEdgeDTO`, `GraphResponse` Pydantic models used by all knowledge graph endpoints.

**Files Created**:
- `backend/src/pilot_space/api/v1/schemas/knowledge_graph_schemas.py`

**Dependencies**: T-003

**Size**: S

**Phase**: 5

**Acceptance Criteria**:
- [ ] `GraphNodeDTO` with all fields from plan.md Section 7 API contracts (camelCase)
- [ ] `GraphEdgeDTO` with all fields
- [ ] `GraphResponse(nodes, edges, centerNodeId, total?, query?)`
- [ ] `NodeType` and `EdgeType` exported as string literals (TypeScript-compatible)
- [ ] All Pydantic models use `model_config = ConfigDict(from_attributes=True)`

---

### T-028: Implement `/api/v1/knowledge-graph/search` endpoint

**Description**: Hybrid search endpoint for workspace-level graph exploration.

**Files Modified**:
- `backend/src/pilot_space/api/v1/knowledge_graph.py` (new file)

**Dependencies**: T-013, T-027

**Size**: S

**Phase**: 5

**Acceptance Criteria**:
- [ ] `GET /api/v1/knowledge-graph/search?q=&node_types=&limit=`
- [ ] Requires authenticated user (Supabase JWT)
- [ ] Calls `graph_search_service.search()` with `workspace_id` from user's current workspace
- [ ] Returns `GraphResponse`
- [ ] 400 if `q` missing
- [ ] 403 if workspace access denied (let RLS raise, catch and return 403)

---

### T-029: Implement `/api/v1/knowledge-graph/nodes/{id}/neighbors` endpoint

**Description**: Node neighbor expansion endpoint used by double-click interaction in the full graph.

**Files Modified**:
- `backend/src/pilot_space/api/v1/knowledge_graph.py`

**Dependencies**: T-028

**Size**: S

**Phase**: 5

**Acceptance Criteria**:
- [ ] `GET /api/v1/knowledge-graph/nodes/{node_id}/neighbors?depth=1&edge_types=`
- [ ] 404 if node not found or not in user's workspace
- [ ] Default depth: 1
- [ ] Returns `GraphResponse` with `centerNodeId = node_id`

---

### T-030: Implement `/api/v1/knowledge-graph/subgraph` endpoint

**Description**: Subgraph extraction endpoint for general graph exploration.

**Files Modified**:
- `backend/src/pilot_space/api/v1/knowledge_graph.py`

**Dependencies**: T-029

**Size**: S

**Phase**: 5

**Acceptance Criteria**:
- [ ] `GET /api/v1/knowledge-graph/subgraph?root_id=&max_depth=2&max_nodes=100`
- [ ] 400 if `root_id` missing
- [ ] Returns `GraphResponse`

---

### T-031: Implement `/api/v1/issues/{issue_id}/knowledge-graph` endpoint

**Description**: Issue-scoped subgraph endpoint — the primary endpoint used by the frontend issue detail page. Synthesizes ephemeral GitHub nodes.

**Files Modified**:
- `backend/src/pilot_space/api/v1/issues.py` (add new route) or a new router

**Dependencies**: T-029

**Size**: M

**Phase**: 5

**Acceptance Criteria**:
- [ ] `GET /api/v1/issues/{issue_id}/knowledge-graph?depth=2&node_types=&max_nodes=50&include_github=true`
- [ ] Finds `graph_nodes` row with `external_id = issue_id`
- [ ] BFS via `get_subgraph()` from that root node
- [ ] If `include_github=true`: synthesizes ephemeral PR/Branch/Commit nodes from `integration_links` table
- [ ] Ephemeral nodes have `id` prefixed with `ephemeral-` to distinguish from persisted nodes
- [ ] Priority cap applied (plan.md Section 7.5 business logic)
- [ ] Returns `GraphResponse` with the issue node as `centerNodeId`
- [ ] 404 if issue not found in user's workspace
- [ ] RLS enforced: workspace_id on issue and graph nodes must match

---

### T-032: API endpoint tests

**Description**: pytest tests for all 5 knowledge graph endpoints.

**Files Created**:
- `backend/tests/api/test_knowledge_graph_api.py`

**Dependencies**: T-028 – T-031

**Size**: M

**Phase**: 5

**Acceptance Criteria**:
- [ ] Test each endpoint with valid authenticated request → 200 with correct `GraphResponse` shape
- [ ] Test missing required params → 400
- [ ] Test unauthenticated request → 401
- [ ] Test node not in user's workspace → 404
- [ ] Test `/issues/{id}/knowledge-graph` with `include_github=true` → ephemeral nodes present
- [ ] Mock `GraphSearchService` and `KnowledgeGraphRepository` in tests
- [ ] Coverage ≥ 80% for `knowledge_graph.py`

---

## Unit 9 — Graph Library + Shared Primitives (Phase 6a)

### T-033: Install `@xyflow/react` and `d3-force`

**Description**: Install graph visualization library and force layout package.

**Files Modified**:
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`

**Dependencies**: T-001 (design spec), T-032 (API must exist)

**Size**: S (< 30 min)

**Phase**: 6a

**Acceptance Criteria**:
- [ ] `@xyflow/react` installed (latest stable)
- [ ] `d3-force` installed (for static force layout computation)
- [ ] `pnpm install` succeeds with no peer dependency warnings
- [ ] `pnpm type-check` passes

---

### T-034: Create Zod schemas for graph API responses

**Description**: TypeScript Zod schemas matching the backend's `GraphResponse`, `GraphNodeDTO`, `GraphEdgeDTO`.

**Files Created**:
- `frontend/src/services/api/schemas/knowledge-graph-schemas.ts`

**Dependencies**: T-033

**Size**: S

**Phase**: 6a

**Acceptance Criteria**:
- [ ] `GraphNodeDTOSchema` (Zod) matches backend Pydantic `GraphNodeDTO` exactly
- [ ] `GraphEdgeDTOSchema` (Zod) matches backend Pydantic `GraphEdgeDTO` exactly
- [ ] `GraphResponseSchema` (Zod) wraps both
- [ ] `NodeType` and `EdgeType` exported as `z.enum([...])` with all values
- [ ] TypeScript types inferred: `type GraphNodeDTO = z.infer<typeof GraphNodeDTOSchema>`

---

### T-035: Create `knowledgeGraphApi` client

**Description**: TanStack Query-compatible API client functions for all knowledge graph endpoints.

**Files Created**:
- `frontend/src/services/api/knowledge-graph.ts`

**Dependencies**: T-034

**Size**: S

**Phase**: 6a

**Acceptance Criteria**:
- [ ] `knowledgeGraphApi.getIssueGraph(workspaceId, issueId, params)` → `Promise<GraphResponse>`
- [ ] `knowledgeGraphApi.getNodeNeighbors(workspaceId, nodeId, depth?)` → `Promise<GraphResponse>`
- [ ] `knowledgeGraphApi.searchGraph(workspaceId, query, nodeTypes?)` → `Promise<GraphResponse>`
- [ ] All responses validated through Zod schemas
- [ ] Uses existing `ApiError.fromAxiosError` for error handling
- [ ] Full TypeScript types, no `any`

---

### T-036: Add design tokens and `useIssueKnowledgeGraph` hook

**Description**: Add CSS custom properties from ui-design-spec.md Section 3 to globals.css. Create TanStack Query hook.

**Files Modified**:
- `frontend/src/styles/globals.css`

**Files Created**:
- `frontend/src/features/issues/hooks/use-issue-knowledge-graph.ts`
- `frontend/src/features/issues/hooks/use-implementation-plan.ts`

**Dependencies**: T-035

**Size**: S

**Phase**: 6a

**Acceptance Criteria**:
- [ ] All `--graph-*` CSS custom properties from ui-design-spec.md Section 3 added to `:root` and `.dark`
- [ ] `@keyframes graph-highlight-pulse` defined
- [ ] `@media (prefers-reduced-motion: reduce)` overrides all animation durations to 0ms
- [ ] `useIssueKnowledgeGraph(workspaceId, issueId, options)` hook with 30s staleTime
- [ ] `useImplementationPlan(workspaceId, issueId)` hook wrapping `issuesApi.getImplementContext`
- [ ] `pnpm type-check` passes

---

## Unit 10 — Mini-Graph Component (Phase 6b)

### T-037: Implement `IssueKnowledgeGraphMini` — layout engine

**Description**: Static force-directed layout computation for the mini-graph using d3-force. Produces node positions once on data load.

**Files Created**:
- `frontend/src/features/issues/components/issue-knowledge-graph-mini.tsx`
- `frontend/src/features/issues/utils/compute-graph-layout.ts`

**Dependencies**: T-036

**Size**: M

**Phase**: 6b

**Acceptance Criteria**:
- [ ] `computeGraphLayout(nodes, edges) -> { id: string; x: number; y: number }[]` — synchronous, runs once
- [ ] Layout respects 200px height × container width bounds
- [ ] Node positions are stable (same input → same output, seeded randomness)
- [ ] `IssueKnowledgeGraphMini` renders SVG with circles (20px diameter, node type color) at computed positions
- [ ] 2-letter abbreviation inside each circle (white text, 9px)
- [ ] Edges rendered as SVG lines between node centers

---

### T-038: Implement `IssueKnowledgeGraphMini` — tooltips and interactions

**Description**: Hover tooltips using Radix `Tooltip` and the "Expand full view" button.

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-mini.tsx`

**Dependencies**: T-037

**Size**: S

**Phase**: 6b

**Acceptance Criteria**:
- [ ] Hover over node → Radix `Tooltip` shows `{nodeType}: {label}` (max 40 chars)
- [ ] No zoom, no pan, no click-to-select in mini-graph
- [ ] "Expand full view" button: `Button` ghost sm, `Maximize2` icon, right-aligned below graph
- [ ] Clicking button calls `onExpandFullView()` prop
- [ ] Mini-graph wrapped in `CollapsibleSection` with `Network` icon and node count

---

### T-039: Implement `IssueKnowledgeGraphMini` — empty and loading states

**Dependencies**: T-038

**Size**: S

**Phase**: 6b

**Acceptance Criteria**:
- [ ] Loading: 3 pulsing circles with connecting lines (see ui-design-spec.md Section 10)
- [ ] Empty: SVG illustration + "No graph data yet." + "Use AI chat to build connections."
- [ ] Empty state hides "Expand full view" button

---

### T-040: Implement dark mode support for mini-graph

**Dependencies**: T-038

**Size**: S (< 1 hour)

**Phase**: 6b

**Acceptance Criteria**:
- [ ] SVG circle colors use CSS variables (`var(--graph-node-{type})`)
- [ ] Edge lines use `var(--graph-edge-medium)`
- [ ] Background uses `var(--graph-bg)`
- [ ] Visual check: dark mode colors correct in browser

---

### T-041: Vitest unit tests for mini-graph component

**Files Created**:
- `frontend/src/features/issues/components/__tests__/issue-knowledge-graph-mini.test.tsx`

**Dependencies**: T-039, T-040

**Size**: S

**Phase**: 6b

**Acceptance Criteria**:
- [ ] Test: renders with data → shows correct number of circles
- [ ] Test: hover on node → tooltip appears
- [ ] Test: click "Expand full view" → `onExpandFullView` called
- [ ] Test: empty data → empty state renders, no "Expand" button
- [ ] Test: loading state → skeleton renders
- [ ] `pnpm test` passes

---

## Unit 11 — Full Graph Component (Phase 6c)

### T-042: Implement `IssueKnowledgeGraphFull` — React Flow setup and custom node

**Description**: Set up `@xyflow/react` canvas, convert `GraphNodeDTO` to React Flow nodes, implement custom `GraphNodeComponent`.

**Files Created**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`
- `frontend/src/features/issues/components/graph-node-component.tsx`

**Dependencies**: T-036

**Size**: M

**Phase**: 6c

**Acceptance Criteria**:
- [ ] `IssueKnowledgeGraphFull` mounts `ReactFlow` with `fitView`
- [ ] `GraphNodeDTO[]` converted to React Flow `Node[]` with computed positions (d3-force)
- [ ] `GraphEdgeDTO[]` converted to React Flow `Edge[]`
- [ ] `GraphNodeComponent` renders: border (node type color), icon (Lucide, 14px), label (truncated 20 chars), summary (truncated 30 chars)
- [ ] Current issue node (matching `issueId`) renders with `box-shadow: var(--graph-node-current-glow)`
- [ ] AI-generated node types show `Sparkles` 10px badge top-right
- [ ] Zoom range: 0.3× – 3× (`minZoom={0.3} maxZoom={3}`)

---

### T-043: Implement graph toolbar (filters + depth selector)

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`

**Dependencies**: T-042

**Size**: S

**Phase**: 6c

**Acceptance Criteria**:
- [ ] Toolbar renders above graph canvas (44px, `border-b`)
- [ ] "← Chat" button calls `onClose()` prop
- [ ] Node type filter chips (multi-select toggle): Issues, Notes, PRs, Decisions, Code, All
- [ ] Filter chips use node type color when active (filled), outline when inactive
- [ ] Depth selector: 3-way toggle (1, 2, 3 hops) — triggers `useIssueKnowledgeGraph` refetch with new depth
- [ ] Active filters applied client-side to hide/show node types

---

### T-044: Implement node selection and detail panel

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`

**Dependencies**: T-043

**Size**: M

**Phase**: 6c

**Acceptance Criteria**:
- [ ] Click node → selected state (3px ring), connected edges highlighted, others dimmed (opacity 0.1)
- [ ] Detail panel slides up from bottom (200ms ease-out) with `height` animation
- [ ] Panel shows: node type badge, label, summary, key properties (state, priority if issue)
- [ ] "Open Issue →" link for `issue` and `note` node types only
- [ ] "Expand neighborhood" button → triggers double-click behavior (fetch 1-hop neighbors)
- [ ] Click canvas background → deselect + close detail panel
- [ ] `highlightNodeId` prop: auto-centers graph + pulse animation + opens detail panel

---

### T-045: Implement node expansion (double-click fetch 1 hop)

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`

**Dependencies**: T-044

**Size**: S

**Phase**: 6c

**Acceptance Criteria**:
- [ ] Double-click node → `GET /api/v1/knowledge-graph/nodes/{id}/neighbors?depth=1`
- [ ] New nodes added to graph state with settle animation
- [ ] Duplicate nodes (already in graph) not re-added
- [ ] New edges added between all nodes now in graph
- [ ] Loading indicator on double-clicked node during fetch

---

### T-046: Implement edge styling by weight

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`

**Dependencies**: T-042

**Size**: S

**Phase**: 6c

**Acceptance Criteria**:
- [ ] Edge weight ≥ 0.7: solid 2px, `--graph-edge-strong`, label always shown
- [ ] Edge weight 0.3–0.7: solid 1px, `--graph-edge-medium`, label on hover
- [ ] Edge weight < 0.3: dashed (4,4), 1px, `--graph-edge-weak`, label hidden (shown via filter)
- [ ] Directional `arrowClosed` markers on all edges
- [ ] Edge label style per ui-design-spec.md Section 5

---

### T-047: Implement minimap and zoom controls

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`

**Dependencies**: T-042

**Size**: S (< 1 hour)

**Phase**: 6c

**Acceptance Criteria**:
- [ ] `<MiniMap>` component from `@xyflow/react`, bottom-right, 80×60px
- [ ] `<Controls>` component, bottom-left, vertical stack layout
- [ ] `<Background>` component with dot grid (`var(--graph-grid)` color)

---

### T-048: Vitest tests for full graph component

**Files Created**:
- `frontend/src/features/issues/components/__tests__/issue-knowledge-graph-full.test.tsx`

**Dependencies**: T-042 – T-047

**Size**: M

**Phase**: 6c

**Acceptance Criteria**:
- [ ] Test: renders with data → correct number of nodes visible
- [ ] Test: click node → detail panel appears
- [ ] Test: click canvas → detail panel closes
- [ ] Test: `highlightNodeId` set → node has highlight class
- [ ] Test: filter chip toggled → nodes of that type hidden
- [ ] Test: "← Chat" button → `onClose` called
- [ ] Test: empty state renders when data has 0 nodes
- [ ] `pnpm test` passes

---

## Unit 12 — Right Panel Tab System + GitHub Section (Phase 6d+6e)

### T-049: Modify `IssueNoteLayout` to add tab system

**Description**: Add `rightPanelTab`, `onRightPanelTabChange`, and `knowledgeGraphContent` props to `IssueNoteLayout`. Implement CSS `display: none` tab hiding (not unmount).

**Files Modified**:
- `frontend/src/features/issues/components/issue-note-layout.tsx`

**Dependencies**: T-036

**Size**: M

**Phase**: 6d

**Acceptance Criteria**:
- [ ] Tab bar renders at top of right panel (40px, `border-b`)
- [ ] `MessageSquare` icon for Chat tab, `Network` icon for Knowledge Graph tab
- [ ] Active tab has 2px bottom border indicator per ui-design-spec.md Section 7
- [ ] Chat content wrapped in `div` with `className={cn(activeTab !== 'chat' && 'hidden')}`
- [ ] Graph content wrapped in `div` with `className={cn(activeTab !== 'knowledge-graph' && 'hidden')}`
- [ ] Tab transition: `var(--graph-tab-transition)` (200ms, instant if reduced motion)
- [ ] `IssueKnowledgeGraphFull` lazy-loaded via `React.lazy` + `Suspense`
- [ ] `hasActivatedGraph` state tracks whether graph was ever opened (to avoid unmounting)
- [ ] `pnpm type-check` passes

---

### T-050: Implement `GitHubImplementationSection` — Area 1 (GitHub Activity)

**Description**: Port all existing `GitHubSection` behavior to the new component file.

**Files Created**:
- `frontend/src/features/issues/components/github-implementation-section.tsx`

**Dependencies**: T-049

**Size**: S

**Phase**: 6e

**Acceptance Criteria**:
- [ ] All PR, branch, and commit display from current `GitHubSection` preserved
- [ ] Status badges: `[merged]`, `[open]`, `[closed]`
- [ ] External link icons for PRs and branches
- [ ] Empty state: `[Create Branch]` + `[Implement with Claude]` buttons
- [ ] Section header: `Zap` icon (replacing existing icon), "GitHub & Implementation"
- [ ] `CreateBranchPopover` and `ImplementPopover` references removed from `IssueEditorContent`

---

### T-051: Implement `GitHubImplementationSection` — Area 2 (Implementation Plan)

**Description**: Add inline implementation plan panel with task checklist, CLI commands, affected graph nodes.

**Files Modified**:
- `frontend/src/features/issues/components/github-implementation-section.tsx`

**Dependencies**: T-050

**Size**: M

**Phase**: 6e

**Acceptance Criteria**:
- [ ] Implementation Plan section renders below separator line when `aiContext` data exists
- [ ] Branch name shown
- [ ] Task checklist: read-only checkboxes, checked tasks have `line-through` + `text-muted-foreground`
- [ ] CLI commands: monospace code blocks with `Copy` icon buttons
- [ ] Copy button shows `Check` icon for 1.5s after copy then reverts
- [ ] Affected nodes list: clickable rows that call `onHighlightNode(nodeId)` prop
- [ ] Node type indicator shape and color from ui-design-spec.md Section 6
- [ ] `[Generate Plan]` button when no `aiContext` exists
- [ ] `[Regenerate]` button when `aiContext` exists
- [ ] `useImplementationPlan` hook used for data fetching

---

### T-052: Vitest tests for tab system

**Files Created**:
- `frontend/src/features/issues/components/__tests__/issue-note-layout.test.tsx`

**Dependencies**: T-049

**Size**: S

**Phase**: 6d

**Acceptance Criteria**:
- [ ] Test: default tab is "chat" → chat content visible, graph hidden
- [ ] Test: click Graph tab → graph content visible, chat hidden (display: none, not unmounted)
- [ ] Test: click Chat tab → chat visible again (state preserved)
- [ ] Test: tab active indicator on correct tab
- [ ] `pnpm test` passes

---

### T-053: Vitest tests for `GitHubImplementationSection`

**Files Created**:
- `frontend/src/features/issues/components/__tests__/github-implementation-section.test.tsx`

**Dependencies**: T-051

**Size**: S

**Phase**: 6e

**Acceptance Criteria**:
- [ ] Test: with aiContext data → plan renders (branch, tasks, CLI commands, affected nodes)
- [ ] Test: without aiContext → `[Generate Plan]` button renders
- [ ] Test: click affected node → `onHighlightNode` called with correct nodeId
- [ ] Test: click copy CLI command → clipboard written
- [ ] `pnpm test` passes

---

### T-054: Remove `implement-popover.tsx` and `ImplementPopover` references

**Description**: Delete the now-inlined `ImplementPopover` component and remove its usage from `IssueEditorContent`.

**Files Deleted**:
- `frontend/src/features/issues/components/implement-popover.tsx`

**Files Modified**:
- `frontend/src/features/issues/components/issue-editor-content.tsx`

**Dependencies**: T-051

**Size**: S (< 30 min)

**Phase**: 6e

**Acceptance Criteria**:
- [ ] `implement-popover.tsx` deleted
- [ ] `issue-editor-content.tsx` no longer imports `ImplementPopover`
- [ ] `issue-editor-content.tsx` now imports `GitHubImplementationSection`
- [ ] `pnpm type-check` passes with no errors

---

## Unit 13 — Integration + Responsive + Tests + Migration (Phase 6f+6g+6h+7)

### T-055: Wire `IssueDetailPage` — connect all components

**Description**: Add `rightPanelTab` state, connect mini-graph "Expand" to tab switch, connect implementation panel node clicks to graph highlight.

**Files Modified**:
- `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`

**Dependencies**: T-049, T-051, T-041, T-048

**Size**: M

**Phase**: 6f

**Acceptance Criteria**:
- [ ] `rightPanelTab: RightPanelTab` state managed in `IssueDetailPage`
- [ ] `highlightNodeId: string | undefined` state managed in `IssueDetailPage`
- [ ] `onExpandFullView` from mini-graph → sets `rightPanelTab = 'knowledge-graph'`
- [ ] `onHighlightNode(nodeId)` from implementation panel → sets `rightPanelTab = 'knowledge-graph'` + `highlightNodeId = nodeId`
- [ ] `highlightNodeId` cleared after 3s (after pulse animation completes)
- [ ] `IssueNoteLayout` receives all new props
- [ ] `IssueEditorContent` receives `onExpandFullView` and `onHighlightNode` callbacks
- [ ] `pnpm type-check` passes

---

### T-056: Mobile responsive layout for knowledge graph

**Description**: Handle mobile breakpoints per ui-design-spec.md Section 5 (Responsive Behavior).

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`
- `frontend/src/features/issues/components/issue-knowledge-graph-mini.tsx`

**Dependencies**: T-055

**Size**: S

**Phase**: 6g

**Acceptance Criteria**:
- [ ] Mini-graph hidden on mobile (< 768px) — `hidden sm:block`
- [ ] Full graph: on mobile, renders in a full-screen `Sheet` component triggered by a header button
- [ ] Sheet trigger button added to `IssueNoteHeader` on mobile (< 768px)
- [ ] Tab bar hidden on mobile (only full-screen Sheet used)
- [ ] Implementation plan section: collapsed by default on mobile, expandable

---

### T-057: Accessibility — keyboard navigation for graph

**Description**: Implement all keyboard navigation requirements from ui-design-spec.md Section 9.

**Files Modified**:
- `frontend/src/features/issues/components/issue-knowledge-graph-full.tsx`
- `frontend/src/features/issues/components/issue-knowledge-graph-mini.tsx`
- `frontend/src/features/issues/components/issue-note-layout.tsx`

**Dependencies**: T-055

**Size**: M

**Phase**: 6g

**Acceptance Criteria**:
- [ ] Tab bar: `role="tablist"`, tabs `role="tab"` with `aria-selected`
- [ ] Graph canvas: `role="application"` with dynamic `aria-label`
- [ ] Each graph node: `role="button"`, `aria-label="{nodeType}: {label}"`, `aria-pressed` for selected
- [ ] Detail panel: `role="region"` with `aria-live="polite"`
- [ ] Keyboard: Tab cycles through nodes, Enter selects, Escape deselects
- [ ] Focus ring visible on all interactive elements
- [ ] Screen reader announcements on tab switch, node selection

---

### T-058: Accessibility — WCAG 2.1 AA audit

**Dependencies**: T-057

**Size**: S

**Phase**: 6g

**Acceptance Criteria**:
- [ ] All node type colors meet 4.5:1 contrast against `bg-background` (verified with axe-core or manual check)
- [ ] All interactive elements meet 44×44px minimum touch target
- [ ] Color is not the only differentiator — node shapes + abbreviations confirm type
- [ ] Focus rings visible in both light and dark mode
- [ ] Axe-core accessibility check passes (0 violations) in Vitest with `@axe-core/react`

---

### T-059: End-to-end tests for knowledge graph user flows

**Description**: Playwright tests for the 3 interaction flows in ui-design-spec.md Section 8.

**Files Created**:
- `frontend/e2e/knowledge-graph.test.ts`

**Dependencies**: T-055, T-056, T-057

**Size**: M

**Phase**: 6h

**Acceptance Criteria**:
- [ ] Flow 1: Open Knowledge Graph section → expand mini-graph → click "Expand full view" → Graph tab active
- [ ] Flow 2: Open GitHub section → click affected node → Graph tab active + node highlighted
- [ ] Flow 3: Click node in full graph → detail panel appears with correct content
- [ ] Tests run against local dev server (`pnpm dev`)
- [ ] All 3 flows pass

---

### T-060: Data migration script: `memory_entries` → `graph_nodes`

**Description**: One-time migration script to port existing `memory_entries` rows to `graph_nodes`. Re-runnable, idempotent.

**Files Created**:
- `backend/scripts/migrate_memory_to_graph.py`

**Dependencies**: T-007, T-012

**Size**: M

**Phase**: 7

**Acceptance Criteria**:
- [ ] Script reads `memory_entries` in pages of 500
- [ ] Maps `source_type` → `node_type` per migration strategy in plan.md Section 5
- [ ] Upserts into `graph_nodes` (idempotent — re-runnable without duplicates)
- [ ] Sets `graph_nodes.embedding = NULL` (recomputed by worker)
- [ ] Sets `memory_entries.migrated_at = now()` after each batch
- [ ] Also migrates `constitution_rules` → `graph_nodes` as `constitution_rule` type
- [ ] `--dry-run` flag available (logs actions without writing)
- [ ] Script is idempotent: rows with `migrated_at IS NOT NULL` are skipped
- [ ] Completion log: "Migrated N nodes from memory_entries, M from constitution_rules"

---

### T-061: Mark `memory_entries` write path deprecated

**Description**: After successful migration validation, add deprecation markers to `MemorySaveService` and `MemorySearchService`. No deletion yet — observation period.

**Files Modified**:
- `backend/src/pilot_space/application/services/memory/memory_save_service.py`
- `backend/src/pilot_space/application/services/memory/memory_search_service.py`

**Dependencies**: T-060

**Size**: S (< 30 min)

**Phase**: 7

**Acceptance Criteria**:
- [ ] Both service classes have `# DEPRECATED: Use GraphWriteService / GraphSearchService` docstring comment
- [ ] No functional changes — services still work (kept for rollback safety)
- [ ] `uv run pyright` passes

---

### T-062: Final quality gate and integration validation

**Description**: Run all quality gates; confirm migration is complete; update CLAUDE.md with knowledge graph architecture note.

**Dependencies**: T-058, T-059, T-060, T-061

**Size**: S

**Phase**: 7

**Acceptance Criteria**:
- [ ] `make quality-gates-backend` passes (pyright + ruff + pytest --cov, fail_under=80)
- [ ] `make quality-gates-frontend` passes (eslint + tsc --noEmit + vitest)
- [ ] `pnpm test:e2e` passes (Flow 1–3 from T-059)
- [ ] `alembic heads` shows single head
- [ ] `alembic check` passes
- [ ] Migration script run on staging: N rows migrated successfully
- [ ] Knowledge graph section visible and functional in issue detail page (manual smoke test)
- [ ] Graph search returns results from migrated `skill_outcome` and `constitution_rule` nodes

---

## Parallel Execution Map

```
T-001 (U-01 done)
  │
  ├─► T-002, T-003 (parallel — both depend on T-001 only)
  │
  ├─► T-004 (after T-002 + T-003)
  ├─► T-005 (after T-003)
  ├─► T-006 (after T-004)
  │
  ├─► T-007, T-008, T-009 (serial — T-007 first, then T-008 + T-009 parallel)
  ├─► T-010 (after T-007-T-009)
  │
  ├─► T-011, T-012 (parallel — both after T-010)
  ├─► T-013 (after T-011 + T-012)
  ├─► T-014 (after T-011 + T-012)
  │
  ├─► T-015 through T-019 (serial agent integration chain)
  │
  ├─► T-020, T-024 (parallel — extraction + embedding worker, both after T-013)
  ├─► T-021, T-025 (after T-020 or T-024 respectively)
  ├─► T-022, T-026 (after T-020 + T-024 respectively)
  ├─► T-023 (after T-020)
  │
  ├─► T-027 (after T-013 — schemas needed by API)
  ├─► T-028 (after T-027)
  ├─► T-029, T-030 (parallel, after T-028)
  ├─► T-031 (after T-029)
  ├─► T-032 (after T-028-T-031)
  │
  ├─► T-033 (after T-032 — frontend can start)
  ├─► T-034, T-035, T-036 (serial frontend primitives)
  │
  ├─► T-037-T-041 (mini-graph, serial)
  ├─► T-042-T-048 (full graph, mostly serial)
  ├─► T-049-T-054 (tab system + github section, partially parallel)
  │
  └─► T-055-T-062 (integration + migration, serial chain)
```
