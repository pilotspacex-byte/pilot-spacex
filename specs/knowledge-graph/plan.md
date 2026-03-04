# Knowledge Graph & Memory Database — Architecture Plan

**Version**: 1.0.0
**Created**: 2026-03-03
**Status**: Approved — implementation target
**Scope**: Replace flat `memory_entries` with a structured knowledge graph (`graph_nodes` + `graph_edges`) and redesign the issue detail page to expose graph exploration.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Data Flow Diagrams](#2-data-flow-diagrams)
3. [Schema Decision: Adjacency Tables vs Apache AGE](#3-schema-decision-adjacency-tables-vs-apache-age)
4. [Embedding Model Decision](#4-embedding-model-decision)
5. [Migration Strategy](#5-migration-strategy)
6. [Risk Assessment](#6-risk-assessment)
7. [API Contracts](#7-api-contracts)
8. [Phase Dependency Graph](#8-phase-dependency-graph)
9. [13 Work Units and Merge Order](#9-13-work-units-and-merge-order)

---

## 1. System Architecture

### High-Level Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js 15)                        │
│                                                                        │
│  IssueDetailPage                                                       │
│  ├─ IssueEditorContent                                                 │
│  │   ├─ GitHubImplementationSection  ─────────────────────────────┐   │
│  │   │   └─ Affected Nodes List (click → highlight)               │   │
│  │   └─ IssueKnowledgeGraphMini (200px, read-only)                │   │
│  └─ Right Panel Tabs [Chat | Knowledge Graph]                      │   │
│      ├─ ChatView (hidden, not unmounted when Graph active)         │   │
│      └─ IssueKnowledgeGraphFull (lazy-loaded, interactive)  ◄──────┘   │
│                                                                        │
│  API client: knowledgeGraphApi (TanStack Query, 30s stale)             │
└───────────────────────────┬────────────────────────────────────────────┘
                            │ HTTP/SSE
┌───────────────────────────▼────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                              │
│                                                                        │
│  api/v1/knowledge_graph.py   api/v1/issues/{id}/knowledge-graph        │
│         │                                   │                          │
│         ▼                                   ▼                          │
│  GraphSearchService              KnowledgeGraphRepository              │
│  GraphWriteService                (hybrid search, BFS, upsert)        │
│  GraphExtractionService                    │                           │
│         │                                   │                          │
│         ▼                                   ▼                          │
│  PilotSpaceAgent                    PostgreSQL + pgvector              │
│  ├─ recall_graph_context()           graph_nodes (vector(1536))        │
│  └─ extract_and_persist_to_graph()   graph_edges                       │
│         │                                                              │
│         ▼                                                              │
│  EmbeddingWorker (pgmq queue)                                          │
│  └─ OpenAI text-embedding-3-large (1536-dim)                           │
└────────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────────────┐
│                       STORAGE LAYER                                    │
│                                                                        │
│  graph_nodes        graph_edges        [deprecated] memory_entries     │
│  - id UUID PK       - id UUID PK       (kept for rollback safety,      │
│  - workspace_id     - source_id FK      no new writes)                 │
│  - user_id (null)   - target_id FK                                     │
│  - node_type ENUM   - edge_type ENUM   constitution_rules              │
│  - external_id UUID - properties JSONB  (migrated → graph_nodes)       │
│  - label TEXT       - weight FLOAT                                     │
│  - content TEXT     - created_at                                       │
│  - properties JSONB                                                    │
│  - embedding v(1536)                                                   │
│  - created_at                                                          │
│  - updated_at                                                          │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `graph_nodes` | First-class entity storage with pgvector embeddings |
| `graph_edges` | Typed directed relationships between nodes |
| `KnowledgeGraphRepository` | CRUD, hybrid search, BFS traversal, bulk upsert |
| `GraphSearchService` | Embed query → hybrid search → 1-hop expansion → score |
| `GraphWriteService` | Transactional upsert nodes + edges → enqueue embeddings |
| `GraphExtractionService` | LLM-powered entity/relation extraction from conversations |
| `PilotSpaceAgent` | Orchestrates recall (before prompt) + persist (after stream) |
| `EmbeddingWorker` | Async OpenAI embedding via pgmq queue |
| `knowledgeGraphApi` | Frontend API client for graph endpoints |
| `useIssueKnowledgeGraph` | TanStack Query hook, 30s staleTime |
| `IssueKnowledgeGraphMini` | 200px static preview, hover-only, collapsible section |
| `IssueKnowledgeGraphFull` | Full interactive graph in right panel tab |
| `GitHubImplementationSection` | GitHub activity + inline implementation plan + affected nodes |

---

## 2. Data Flow Diagrams

### 2a. Write Path: Conversation → Extraction → Graph

```
User sends message
      │
      ▼
PilotSpaceAgent._build_stream_config()
      │
      ├─ recall_graph_context(workspace_id, user_id, message)
      │       │
      │       ▼
      │   GraphSearchService.search(payload)
      │       │
      │       ├─ Embed query → OpenAI text-embedding-3-large (async, 150ms)
      │       ├─ hybrid_search: 0.5*cosine + 0.2*ts_rank + 0.2*recency + 0.1*edge_density
      │       ├─ Expand 1-hop neighbors for relationship context
      │       └─ Merge user-scoped + workspace-scoped results
      │
      ▼
Prompt Assembly (Layer 5: Workspace Knowledge Graph Context)
      │
      ▼
Stream to client via SSE
      │
      ▼ (stream complete — finally block)
extract_and_persist_to_graph(conversation_messages)
      │
      ├─ GraphExtractionService.extract(messages)
      │       │
      │       └─ LLM call (claude-haiku / flash — cheap + fast)
      │               └─ Structured JSON: nodes[], edges[]
      │
      └─ GraphWriteService.write(nodes, edges)
              │
              ├─ Upsert nodes (idempotent by external_id + node_type)
              ├─ Upsert edges (idempotent by source+target+type)
              └─ Enqueue embedding jobs → pgmq → EmbeddingWorker
                      │
                      └─ OpenAI API → vector(1536) → UPDATE graph_nodes
```

### 2b. Read Path: Query → Hybrid Search → Context Injection

```
GraphSearchService.search(payload)
      │
      ├─ 1. Embed query: OpenAI text-embedding-3-large → query_vec[1536]
      │
      ├─ 2. Hybrid DB query (single SQL):
      │       SELECT *,
      │         0.5 * (1 - embedding <=> query_vec) +
      │         0.2 * ts_rank(to_tsvector(content), query) +
      │         0.2 * recency_score(updated_at) +
      │         0.1 * edge_density_score(id)
      │       AS score
      │       FROM graph_nodes
      │       WHERE workspace_id = $1
      │         AND (user_id IS NULL OR user_id = $2)
      │         AND (node_types IS NULL OR node_type = ANY($3))
      │       ORDER BY score DESC
      │       LIMIT 20
      │
      ├─ 3. 1-hop neighbor expansion:
      │       For each top-10 hit → fetch direct neighbors (depth=1)
      │       SELECT * FROM graph_nodes gn
      │       JOIN graph_edges ge ON (ge.source_id = gn.id OR ge.target_id = gn.id)
      │       WHERE (ge.source_id = ANY($hit_ids) OR ge.target_id = ANY($hit_ids))
      │
      └─ 4. Format as GraphContext:
              ## Workspace Knowledge Graph Context

              ### Relevant Entities
              - [issue] PS-42: "Implement auth flow" (related to: PS-38, PS-45)
              - [decision] "Chose Supabase Auth over custom JWT" (decided in: PS-38)

              ### Your Context
              - You frequently work on: authentication, API design
              - Recent preference: "prefer explicit error messages over generic ones"

              ### Learned Patterns
              - "Auth endpoints need RLS context set before DB access" (from: 3 conversations)
```

### 2c. Issue Subgraph Path: Issue Detail Page → Graph API → Frontend

```
IssueDetailPage mounts
      │
      ▼
useIssueKnowledgeGraph(workspaceId, issueId, { depth: 2, maxNodes: 50 })
      │
      ▼
GET /api/v1/issues/{issue_id}/knowledge-graph?depth=2&max_nodes=50
      │
      ▼
KnowledgeGraphRepository.get_subgraph(root_id, max_depth=2)
      │
      ├─ Find graph node by external_id = issue_id
      ├─ BFS via recursive CTE (PostgreSQL WITH RECURSIVE)
      │       WITH RECURSIVE subgraph AS (
      │         SELECT id, 0 as depth FROM graph_nodes WHERE external_id = $issue_id
      │         UNION ALL
      │         SELECT gn.id, sg.depth + 1
      │         FROM graph_nodes gn
      │         JOIN graph_edges ge ON (ge.source_id = gn.id OR ge.target_id = gn.id)
      │         JOIN subgraph sg ON (ge.source_id = sg.id OR ge.target_id = sg.id)
      │         WHERE sg.depth < $max_depth
      │       )
      │       SELECT DISTINCT * FROM graph_nodes WHERE id IN (SELECT id FROM subgraph)
      │
      ├─ Synthesize ephemeral GitHub nodes from integration_links (not persisted)
      ├─ Cap at max_nodes by priority: Issue/Note/Decision > PR/Branch/CodeRef > User/Pattern > Summary
      └─ Return GraphResponse { nodes, edges, centerNodeId }
```

---

## 3. Schema Decision: Adjacency Tables vs Apache AGE

### Decision: Adjacency Tables (Option B)

**Committed to adjacency tables (`graph_nodes` + `graph_edges` + recursive CTEs).**

### Rationale

| Factor | Adjacency Tables | Apache AGE |
|--------|-----------------|------------|
| **PostgreSQL extension dependency** | None — pure SQL | Requires `CREATE EXTENSION age` |
| **Supabase-hosted compatibility** | Full — Supabase runs standard PostgreSQL 15+ | Supabase does NOT support Apache AGE (not in approved extension list) |
| **Query language** | SQL + recursive CTEs | Cypher (additional language to learn) |
| **pgvector compatibility** | Native — both in same query | Compatible but requires SQL wrapper around Cypher |
| **RLS enforcement** | Standard PostgreSQL RLS on tables | RLS must be applied at SQL wrapper level; Cypher queries bypass table-level RLS |
| **Rollback simplicity** | DROP TABLE graph_nodes, graph_edges | DROP EXTENSION age (destructive, affects all Cypher graphs) |
| **Graph depth** | Practical limit: 3-5 hops (recursive CTE overhead) | Arbitrary depth (native graph traversal) |
| **Issue scale** | 5-50 nodes per issue subgraph: CTEs fast (<50ms) | Overkill for 5-50 nodes |
| **Team familiarity** | SQL — all engineers know it | Cypher — additional training |

### Trade-offs Accepted

- **Deep traversal performance**: Recursive CTEs degrade beyond depth 5. Mitigated by: cap at depth 3 in API, HNSW index for initial seed nodes, B-tree indexes on edge columns.
- **Graph algorithm library**: No built-in PageRank, shortest path, etc. Mitigated by: the use case (RAG context injection) only requires shallow BFS (depth 1-3), not full graph analytics.
- **Schema verbosity**: Adjacency tables require explicit edge rows. Mitigated by: idempotent upsert with (source_id, target_id, edge_type) unique constraint.

### Schema

```sql
-- Node Types
CREATE TYPE graph_node_type AS ENUM (
  'issue', 'note', 'project', 'cycle', 'user',
  'pull_request', 'code_reference', 'decision',
  'skill_outcome', 'conversation_summary', 'learned_pattern',
  'constitution_rule', 'work_intent', 'user_preference'
);

-- Edge Types
CREATE TYPE graph_edge_type AS ENUM (
  'relates_to', 'caused_by', 'led_to', 'decided_in',
  'authored_by', 'assigned_to', 'belongs_to', 'references',
  'learned_from', 'summarizes', 'blocks', 'duplicates', 'parent_of'
);

CREATE TABLE graph_nodes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- NULL = workspace-scoped
  node_type    graph_node_type NOT NULL,
  external_id  UUID,                      -- Reference to original entity (issue.id, note.id, etc.)
  label        TEXT NOT NULL,             -- Display name (PS-42, note title, user name)
  content      TEXT NOT NULL DEFAULT '',  -- Full text content for hybrid search
  properties   JSONB NOT NULL DEFAULT '{}', -- Type-specific metadata
  embedding    vector(1536),              -- OpenAI text-embedding-3-large
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE graph_edges (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id   UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  target_id   UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
  edge_type   graph_edge_type NOT NULL,
  properties  JSONB NOT NULL DEFAULT '{}',
  weight      FLOAT NOT NULL DEFAULT 1.0,  -- 0.0-1.0 relationship strength
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_id, target_id, edge_type)  -- Idempotent upsert
);

-- Indexes
CREATE INDEX idx_graph_nodes_workspace_type    ON graph_nodes (workspace_id, node_type);
CREATE INDEX idx_graph_nodes_external_id       ON graph_nodes (external_id) WHERE external_id IS NOT NULL;
CREATE INDEX idx_graph_nodes_user_id           ON graph_nodes (user_id)      WHERE user_id IS NOT NULL;
CREATE INDEX idx_graph_nodes_embedding         ON graph_nodes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_graph_nodes_content_fts       ON graph_nodes USING gin (to_tsvector('english', content));
CREATE INDEX idx_graph_nodes_properties        ON graph_nodes USING gin (properties);
CREATE INDEX idx_graph_edges_source            ON graph_edges (source_id);
CREATE INDEX idx_graph_edges_target            ON graph_edges (target_id);
CREATE INDEX idx_graph_edges_type              ON graph_edges (edge_type);
```

---

## 4. Embedding Model Decision

### Decision: OpenAI `text-embedding-3-large` (1536-dim)

**Committed to OpenAI embeddings, unifying on 1536-dim vectors.**

### Why Not Gemini (Current System)

The existing Gemini embedding (`gemini-embedding-exp-03-07`, 768-dim) is **permanently broken** in the current system:

1. **`google_api_key` never injected**: In `container/_factories.py`, `create_pilotspace_agent()` does not pass `memory_search_service` or `memory_save_service`. Even if it did, the `MemorySearchPayload` never receives the `google_api_key` from config. The system always falls back to keyword-only search.

2. **Evidence**: `MemorySearchService.search()` catches `GoogleApiKeyMissing` and silently degrades to `ts_rank`-only. No embedding recall has ever worked in production.

3. **Existing embeddings table uses 1536-dim**: The `embeddings` table (planned for issue/note search) already has `vector(1536)`. Using 768-dim for graph nodes would create inconsistency requiring two HNSW indexes.

### Why OpenAI

| Factor | OpenAI `text-embedding-3-large` | Gemini `gemini-embedding-exp-03-07` |
|--------|--------------------------------|-------------------------------------|
| **Dimensions** | 1536 (matches existing `embeddings` table) | 768 |
| **ProviderSelector wiring** | Already configured: `TaskType.EMBEDDINGS → OpenAI` | Never properly wired (api_key missing) |
| **Cost** | $0.00013/1K tokens | $0 (but broken = $∞ in engineering time) |
| **Quality** | MTEB Leaderboard top-3 | Experimental model, not production-stable |
| **Latency** | ~150ms p95 | N/A (never worked) |
| **Dimension consistency** | Unified with existing embeddings table | Would require separate HNSW index |

### Migration Handling for Existing 768-dim Vectors

- `memory_entries` rows with 768-dim embeddings are migrated to `graph_nodes` with `embedding = NULL`.
- The EmbeddingWorker will recompute 1536-dim embeddings for migrated nodes asynchronously.
- During the recomputation window (estimated 1-7 days depending on row count), graph search falls back to keyword-only for those nodes (same behavior as current broken system — no regression).
- New nodes always get 1536-dim embeddings via the write path queue.

---

## 5. Migration Strategy

### Principles

1. **Zero downtime**: `memory_entries` table kept alive with all existing data. No reads or writes removed from existing code until Phase 3 (agent integration) is complete and validated.
2. **Rollback safety**: Each phase is independently reversible. The new graph tables can be dropped without affecting existing functionality until Phase 3 switches the agent to use graph services.
3. **Gradual migration**: Data moves from `memory_entries` → `graph_nodes` via a one-time migration script. Old rows are not deleted — they are kept with a `migrated_at` column.
4. **No dimension downtime**: New nodes immediately get 1536-dim embedding enqueued. Old migrated nodes get it lazily via the worker.

### Phase-by-Phase Migration

```
Phase 1 (Schema):
  ├─ CREATE TABLE graph_nodes, graph_edges (with RLS)
  ├─ CREATE TYPE graph_node_type, graph_edge_type
  ├─ CREATE all indexes
  └─ ALTER TABLE memory_entries ADD COLUMN migrated_at TIMESTAMPTZ

Phase 2 (Services):
  ├─ New services running in PARALLEL with old services
  ├─ Old MemorySearchService / MemorySaveService untouched
  └─ DI container has both old + new services wired

Phase 3 (Agent Integration — the cutover):
  ├─ Switch PilotSpaceAgent to use GraphSearchService + GraphWriteService
  ├─ Old recall_workspace_context / save_skill_outcome_to_memory retired
  └─ Validation: run both old and new in shadow mode for 1 sprint

Phase 7 (Cleanup):
  ├─ Run data migration script: memory_entries → graph_nodes
  ├─ Mark memory_entries deprecated (no new writes)
  └─ Drop old services after 2-sprint observation period
```

### Data Migration Script

The migration script (Unit 13, T-060: `backend/scripts/migrate_memory_to_graph.py`) will:

1. Batch-read `memory_entries` in pages of 500
2. Map `source_type` to `node_type`:
   - `INTENT` → `work_intent`
   - `SKILL_OUTCOME` → `skill_outcome`
   - `USER_FEEDBACK` → `user_preference`
   - `CONSTITUTION` → `constitution_rule`
3. Upsert into `graph_nodes` (idempotent — re-runnable)
4. Set `embedding = NULL` (recomputed by worker)
5. Set `memory_entries.migrated_at = now()`
6. Also migrate `constitution_rules` → `graph_nodes` as `constitution_rule` nodes

---

## 6. Risk Assessment

### Risk Matrix

| Risk | Probability | Impact | Mitigation | Rollback |
|------|-------------|--------|------------|---------|
| **OpenAI embedding API latency spike** | Medium | Medium | Timeout 10s, retry 3x with exponential backoff; fall back to keyword-only | Disable embedding enqueue in pgmq, graph search uses keyword fallback |
| **Recursive CTE timeout on deep graphs** | Low | Medium | Hard cap depth=3 in API, LIMIT 200 rows in CTE | Reduce depth cap to 2 |
| **graph_nodes grows unbounded** | Medium | Low | TTL field + `delete_expired_nodes()` job via pg_cron (30-day default) | Truncate non-domain node types |
| **Migration script corrupts memory_entries** | Very Low | High | Dry-run mode, idempotent upsert, do not delete source rows | Revert by clearing migrated_at; source data intact |
| **Phase 3 cutover breaks agent recall** | Low | High | Shadow mode testing (run both systems 1 sprint); feature flag per workspace | Revert PilotSpaceAgent to old services via config flag |
| **GraphExtractionService LLM cost blowup** | Low | Medium | Only run extraction if conversation > 3 messages; Haiku/Flash model only; cost gate | Disable extraction service, fall back to old 500-char save |
| **RLS policy misconfiguration** | Low | Critical | Follow rls-check.md rules; integration tests on PostgreSQL (not SQLite) | Disable graph endpoints; old memory system unaffected |
| **pgvector HNSW index build OOM** | Very Low | Medium | Build index with `maintenance_work_mem = 256MB`; use CONCURRENTLY | Drop and rebuild with lower `ef_construction` |
| **Frontend graph library bundle too large** | Low | Low | React.lazy() for full graph; mini-graph uses lightweight SVG renderer | Remove full graph, keep mini-graph only |

### Rollback Strategy Per Phase

```
Phase 1 rollback: alembic downgrade -1 → drops graph_nodes, graph_edges tables
Phase 2 rollback: remove new services from DI container; old services untouched
Phase 3 rollback: revert pilotspace_agent.py to old recall/save functions (single git revert)
Phase 4 rollback: disable GraphExtractionService in DI (set to no-op)
Phase 5 rollback: remove api/v1/knowledge_graph.py router from main.py
Phase 6 rollback: revert frontend components (git revert range)
Phase 7 rollback: not applicable (migration is additive; source data preserved)
```

---

## 7. API Contracts

### 7.1 `GET /api/v1/knowledge-graph/search`

**Purpose**: Hybrid search across all graph nodes in a workspace.

**Request**:
```
GET /api/v1/knowledge-graph/search
    ?q=<text>&node_types=issue,note&limit=10
Authorization: Bearer <token>
```

Note: `workspace_id` is derived from the authenticated user's current workspace context (via RLS + JWT claims), not passed as a query parameter. This matches the project's auth pattern for all workspace-scoped endpoints.

**Response** (`200 OK`):
```json
{
  "nodes": [
    {
      "id": "uuid",
      "nodeType": "issue",
      "label": "PS-42",
      "summary": "Implement auth flow for the API gateway",
      "properties": { "state": "in_progress", "priority": "high" },
      "createdAt": "2026-03-01T12:00:00Z",
      "score": 0.87
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "sourceId": "uuid",
      "targetId": "uuid",
      "edgeType": "relates_to",
      "label": "relates to",
      "weight": 0.9
    }
  ],
  "centerNodeId": null,
  "total": 42,
  "query": "auth flow"
}
```

**Error responses**:
- `400` — missing `q` parameter
- `403` — workspace access denied (RLS)
- `422` — invalid `node_types` enum value

---

### 7.2 `GET /api/v1/knowledge-graph/nodes/{node_id}/neighbors`

**Purpose**: Fetch direct neighbors of a node for graph expansion (double-click interaction).

**Request**:
```
GET /api/v1/knowledge-graph/nodes/{node_id}/neighbors
    ?depth=1&edge_types=relates_to,blocks
Authorization: Bearer <token>
```

**Response** (`200 OK`):
```json
{
  "nodes": [ /* same GraphNodeDTO shape */ ],
  "edges": [ /* same GraphEdgeDTO shape */ ],
  "centerNodeId": "{node_id}"
}
```

**Error responses**:
- `404` — node not found or not in user's workspace
- `403` — workspace access denied

---

### 7.3 `GET /api/v1/knowledge-graph/subgraph`

**Purpose**: Extract a local subgraph rooted at a given node.

**Request**:
```
GET /api/v1/knowledge-graph/subgraph
    ?root_id=<uuid>&max_depth=2&max_nodes=100
Authorization: Bearer <token>
```

**Response** (`200 OK`): Same `GraphResponse` shape.

---

### 7.4 `GET /api/v1/knowledge-graph/user-context`

**Purpose**: Fetch the requesting user's personal knowledge graph context (user-scoped nodes + recent workspace interactions).

**Request**:
```
GET /api/v1/knowledge-graph/user-context
Authorization: Bearer <token>
```

**Response** (`200 OK`):
```json
{
  "nodes": [
    {
      "id": "uuid",
      "nodeType": "user_preference",
      "label": "Prefers explicit error messages",
      "summary": "User expressed preference for detailed error messages over generic ones",
      "properties": { "frequency": 3, "lastSeen": "2026-02-28" },
      "createdAt": "2026-02-15T09:00:00Z"
    },
    {
      "id": "uuid",
      "nodeType": "learned_pattern",
      "label": "Auth endpoints need RLS context",
      "summary": "Observed across 3 conversations involving auth and database queries",
      "properties": { "confidence": 0.9 },
      "createdAt": "2026-02-20T14:30:00Z"
    }
  ],
  "edges": [],
  "centerNodeId": null
}
```

---

### 7.5 `GET /api/v1/issues/{issue_id}/knowledge-graph`

**Purpose**: Issue-scoped subgraph for the issue detail page. The primary frontend-facing endpoint.

**Request**:
```
GET /api/v1/issues/{issue_id}/knowledge-graph
    ?depth=2&node_types=issue,note,decision&max_nodes=50&include_github=true
Authorization: Bearer <token>
```

**Response** (`200 OK`):
```json
{
  "nodes": [
    {
      "id": "uuid",
      "nodeType": "issue",
      "label": "PS-42",
      "summary": "Implement auth flow for the API gateway",
      "properties": { "state": "in_progress", "priority": "high", "identifier": "PS-42" },
      "createdAt": "2026-02-01T10:00:00Z"
    },
    {
      "id": "uuid-ephemeral-1",
      "nodeType": "pull_request",
      "label": "#87 Add JWT middleware",
      "summary": "Merged PR implementing the JWT auth middleware",
      "properties": { "state": "merged", "url": "https://github.com/org/repo/pull/87" },
      "createdAt": "2026-02-20T16:00:00Z"
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "sourceId": "uuid-ephemeral-1",
      "targetId": "uuid",
      "edgeType": "references",
      "label": "implements",
      "weight": 1.0
    }
  ],
  "centerNodeId": "uuid"
}
```

**Business logic** (prioritized cap):
1. Issue/Note/Decision nodes — always included
2. PR/Branch/CodeReference nodes — included next
3. User/LearnedPattern nodes — included if space
4. ConversationSummary/SkillOutcome — trimmed first if over `max_nodes`

**Error responses**:
- `404` — issue not found or not in user's workspace
- `403` — workspace access denied

---

## 8. Phase Dependency Graph

```
Phase 0 (Planning + Design Specs) ──────────────────────────────┐
         │                                                       │
         ▼                                                       │
Phase 1 (Schema + Domain + SQLAlchemy Models)                   │
         │                                                       │
         ▼                                                       │
Phase 2 (Repository + Services + DI Wiring)                     │
         │                                                       │
         ├──────────────────────────────────────┐               │
         ▼                                       ▼               │
Phase 3 (Agent Integration)            Phase 5 (REST API)        │
         │                                       │               │
         ▼                                       │               ▼
Phase 4 (Extraction + Enrichment)               │       Phase 6 (Frontend)
         │                                       │         (requires Phase 0b
         └───────────────────────────────────────┘          + Phase 5)
                          │
                          ▼
                  Phase 7 (Migration + Cleanup)

Parallel opportunities:
- Phase 3 and Phase 5 can run in parallel (both depend only on Phase 2)
- Phase 4 can start after Phase 3 is merged
- Phase 6 sub-tasks 6a-6e can run in parallel (all depend on Phase 5)
- Phase 6f-6g must run after 6a-6e are complete
```

---

## 9. 13 Work Units and Merge Order

| Unit | Title | Phase | Depends On | Size | Description |
|------|-------|-------|------------|------|-------------|
| **U-01** | Planning & Design Specs | 0 | — | M | `plan.md`, `ui-design-spec.md`, `tasks.md` (this document) |
| **U-02** | Schema + Domain Entities | 1 | U-01 | L | Alembic migration, SQLAlchemy models, domain dataclasses, unit tests |
| **U-03** | Repository Layer | 2 | U-02 | L | `KnowledgeGraphRepository` with hybrid search, BFS, bulk upsert |
| **U-04** | Application Services + DI | 2 | U-03 | M | `GraphSearchService`, `GraphWriteService`, DI container wiring |
| **U-05** | Agent Integration | 3 | U-04 | M | Replace `recall_workspace_context` + `save_skill_outcome_to_memory`, fix embedding wiring, update Layer 5 prompt |
| **U-06** | Extraction Service | 4 | U-05 | M | `GraphExtractionService` — LLM-powered entity/relation extraction, auto-edge detection |
| **U-07** | Embedding Worker | 4 | U-04 | S | Update `memory_embedding_handler.py` for 1536-dim + new node types |
| **U-08** | REST API Endpoints | 5 | U-04 | M | `api/v1/knowledge_graph.py` — 5 endpoints, Pydantic schemas, API tests |
| **U-09** | Graph Library + Shared Primitives | 6a | U-08 | S | Install `@xyflow/react`, Zod schemas, `knowledgeGraphApi` client, design tokens |
| **U-10** | Mini-Graph Component | 6b | U-09 | M | `IssueKnowledgeGraphMini` — static force layout, hover tooltips, empty state |
| **U-11** | Full Graph Component | 6c | U-09 | L | `IssueKnowledgeGraphFull` — toolbar, node anatomy, edge anatomy, detail panel, minimap |
| **U-12** | Right Panel Tab System + GitHub Section | 6d+6e | U-09 | M | `IssueNoteLayout` tab system, `GitHubImplementationSection`, `useImplementationPlan` hook |
| **U-13** | Integration + Responsive + Tests + Migration | 6f+6g+6h+7 | U-10, U-11, U-12 | L | Wire `IssueDetailPage`, mobile Sheet, a11y, Vitest tests, data migration script, cleanup |

### Merge Order

```
U-01 → U-02 → U-03 → U-04 → [U-05, U-07, U-08] (parallel)
                                    ↓        ↓
                                   U-06     U-09 → [U-10, U-11, U-12] (parallel)
                                              ↓
                                            U-13
```

All branches merge to `main`. Each unit is a separate PR with its own branch (`feat/knowledge-graph-unit-N-*`). The coordinator verifies the merge order before approving each PR.
