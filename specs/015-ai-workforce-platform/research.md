# Research Decisions: AI Workforce Platform

**Feature**: 015 — AI Workforce Platform
**Plan**: `specs/015-ai-workforce-platform/plan.md`

---

## RD-1: CRDT Library Selection (AD-4, FR-024)

**Question**: Which CRDT library for real-time collaborative editing?

| Option | Bundle Size | ProseMirror Binding | Transport | Community |
|--------|------------|-------------------|-----------|-----------|
| **Yjs** | ~35KB | y-prosemirror (official TipTap) | Pluggable (y-websocket, y-supabase) | Largest (10K+ GitHub stars) |
| Automerge 2.0 | ~200KB | prosemirror-automerge (alpha) | Custom | Growing (4K stars) |
| Liveblocks | SDK-based | @liveblocks/yjs (Yjs wrapper) | Managed WebSocket | Commercial |

**Decision**: **Yjs**

**Rationale**:
- TipTap officially supports Yjs via `@tiptap/extension-collaboration` and `@tiptap/extension-collaboration-cursor`
- Smallest bundle (35KB vs 200KB for Automerge)
- `y-supabase` provider leverages existing Supabase Realtime infrastructure — no new WebSocket server
- Battle-tested at scale (Notion, Figma use Yjs-based CRDTs)
- Automerge's ProseMirror binding is alpha-quality, risky for production
- Liveblocks adds vendor dependency + cost per connection

---

## RD-2: CRDT Transport (AD-4, FR-024)

**Question**: What transport layer for Yjs document sync?

| Option | Infrastructure | Latency | Scaling |
|--------|---------------|---------|---------|
| **y-supabase** | Existing Supabase Realtime | <200ms (WebSocket) | Per-channel capacity from Supabase plan |
| y-websocket | New WebSocket server | <100ms | Requires separate deployment + scaling |
| Custom via Redis pub/sub | Redis + custom adapter | ~300ms | Complex, requires custom Yjs provider |

**Decision**: **y-supabase**

**Rationale**:
- Zero new infrastructure — uses existing Supabase Realtime channels
- Each note gets its own Realtime channel (topic: `note:{note_id}`)
- Supabase handles connection management, presence, and channel cleanup
- y-websocket would require deploying + scaling a separate WebSocket server
- Tradeoff: slightly higher latency than bare WebSocket, but within 200ms target (FR-024)

---

## RD-3: Block Ownership Enforcement Layer (FR-008)

**Question**: At which layer should block ownership be enforced?

| Option | Where | Pros | Cons |
|--------|-------|------|------|
| **Y.js update handler (app middleware)** | Frontend, in Y.js `beforeTransaction` | Rejects before CRDT merge; clean boundary | Requires frontend-side check; malicious client could bypass |
| CRDT-level (modified Yjs) | Yjs source code | Impossible to bypass | Fork maintenance burden; Yjs updates become complex |
| Backend validation only | Server-side | Authoritative | Allows momentary invalid states on client; rollback UX is poor |

**Decision**: **Application middleware in Y.js update handler + backend validation**

**Rationale**:
- Y.js `doc.on('beforeTransaction')` observer checks ownership before applying local changes — immediate UX feedback
- Backend (MCP tools) also validates ownership before writing — defense in depth
- No need to fork Yjs; middleware approach is recommended by Yjs docs
- If a client bypasses frontend check, backend rejects the write via MCP tool ownership validation
- CRDT merge on reconnect: ownership-violating changes from offline edits are discarded at merge

---

## RD-4: Memory Engine — Vector Store (AD-11, FR-101)

**Question**: Which vector store for the memory engine?

| Option | Infrastructure | Dimensions | Index Type | Latency |
|--------|---------------|-----------|------------|---------|
| **pgvector** | Existing PostgreSQL | 768 | HNSW | <50ms at 10K vectors |
| Qdrant | New service | Any | HNSW | <20ms at 1M vectors |
| Pinecone | Managed SaaS | Any | Proprietary | <50ms, managed |
| ChromaDB | Embedded | Any | HNSW | <30ms, but single-process |

**Decision**: **pgvector**

**Rationale**:
- Already in use for AI context embeddings (existing HNSW indexes, 768-dim)
- No new service to deploy or manage (KISS principle)
- PostgreSQL HNSW index delivers <50ms search at our scale (1000-10K entries per workspace)
- Collocated with other data — enables efficient joins (e.g., memory + workspace context)
- RLS natively supported via PostgreSQL policies
- Qdrant/Pinecone only justified at >100K vectors; our scale is 1-10K per workspace
- ChromaDB is single-process, doesn't fit multi-process FastAPI deployment

---

## RD-5: Memory Engine — Keyword Search (AD-11, FR-101)

**Question**: Which keyword search for hybrid memory retrieval?

| Option | Infrastructure | Ranking | Integration |
|--------|---------------|---------|-------------|
| **PostgreSQL FTS (tsvector/GIN)** | Existing | ts_rank (BM25-like) | Native SQL |
| Meilisearch | Existing (used for full-text) | Custom ranking | Separate service, separate API |
| Elasticsearch | New service | BM25 | Complex deployment |

**Decision**: **PostgreSQL FTS**

**Rationale**:
- Existing GIN indexes in use (notes table already has `ix_notes_title_text` tsvector index)
- `ts_rank` provides BM25-equivalent ranking — good enough for memory search
- GENERATED ALWAYS column for `keywords tsvector` — zero application logic needed
- No additional service dependency (Meilisearch is used for user-facing search, but memory search is internal)
- Weighted fusion: `final_score = 0.7 * vector_score + 0.3 * keyword_score` — simple SQL

---

## RD-6: Skill Execution Model (AD-1, FR-085)

**Question**: How should skills execute?

| Option | Process Model | Latency | Complexity |
|--------|--------------|---------|------------|
| **SDK subagents (within FastAPI)** | In-process | <3s spawn | Low — uses existing DI + MCP |
| CLI subprocess | External process | 5-10s spawn | High — needs sandbox, IPC, process management |
| Queue-based workers | Separate processes via pgmq | 2-5s pickup | Medium — needs worker deployment, queue management |

**Decision**: **SDK subagents within FastAPI process**

**Rationale**:
- Claude Agent SDK `Agent(model, tools, system_prompt).run()` runs in-process
- Existing DI container provides all dependencies (MCP servers, repositories, services)
- Existing MCP tool infrastructure reused — just filter tools per skill's whitelist
- No new deployment units, no IPC overhead, no sandbox management
- Token budget + asyncio timeout provide resource control
- Semaphore limits concurrent skills to 5 per workspace (FR-109)
- Tradeoff: skills share FastAPI process memory — mitigated by per-skill token budget and timeout

---

## RD-7: Skill Definition Format (AD-9, FR-091)

**Question**: How should skills be defined?

| Option | Human-Readable | Version Control | SDK Integration |
|--------|---------------|----------------|-----------------|
| **SKILL.md** | Excellent | Git-friendly | SDK auto-discovers from `.claude/skills/` |
| YAML manifests | Good | Git-friendly | Requires custom registry |
| DB records | Fair | Not version-controlled | Requires custom CRUD + management UI |
| Python decorators | Poor for non-devs | Git-friendly | Custom executor needed |

**Decision**: **Hybrid: filesystem (core) + DB (custom)**

**Rationale**:
- SKILL.md = YAML frontmatter (name, description) + markdown body (workflow, tools, output format)
- Core skills: SKILL.md files shipped in repo, version-controlled, copied to sandbox at agent init
- Custom skills: stored in DB, materialized to workspace sandbox via existing `materialize_role_skills()` pipeline
- SDK reads SKILL.md files from the merged sandbox directory (not `.claude/skills/` at project root — that's for Claude Code CLI skills)
- Custom skills need DB storage for CRUD management (Settings → Skills UI)
- No custom SkillExecutor — SDK handles execution via `AgentDefinition` + `tools` parameter

---

## RD-8: Agent Loop Pattern (AD-7, AD-10, FR-100)

**Question**: What orchestration pattern for the agent loop?

| Option | Steps | Memory | Statefulness |
|--------|-------|--------|-------------|
| **ZeroClaw-adapted loop** | msg → recall → analyze → skill → save → respond | Persistent (pgvector + FTS) | Memory across sessions |
| Single-shot query | msg → LLM → tools → respond (current) | None | Per-session only |
| ReAct loop | observe → think → act → observe... | Optional | Per-turn |

**Decision**: **ZeroClaw-adapted agent loop**

**Rationale**:
- Adds memory recall BEFORE LLM analysis — context from prior sessions informs decisions
- Adds memory save AFTER skill execution — learnings persist for future sessions
- Current single-shot query works but loses context between sessions (FR-102)
- ReAct is too fine-grained — skills already encapsulate tool use; loop operates at skill level
- Pipeline: `receive_message → recall_context → llm_analyze_and_select → execute_skill → save_memory → respond`
- Memory engine provides hybrid search (RD-4 + RD-5) for recall step

---

## RD-9: Intent Confirmation UI (AD-8, FR-013)

**Question**: Where should intents be presented for confirmation?

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| **Chat panel** | In chat message stream | Natural conversational flow; consistent with AD-8 | Chat can get busy |
| Inline note blocks | In-note, near source text | Context-adjacent | Clutters note canvas; contradicts AD-8 |
| Modal dialog | Overlay | Focused attention | Interrupts flow; annoying for multiple intents |

**Decision**: **Chat panel with structured cards**

**Rationale**:
- AD-8 mandates chat-primary interface — intents are part of the conversation
- IntentConfirmationCard renders in chat with [Confirm] [Edit] [Dismiss] action buttons
- Multiple intents rendered as a list — user can bulk-confirm (>=70% confidence)
- Focus Mode in note hides AI blocks — chat is the right place for transient workflow
- Note receives only the final artifacts, not intermediate workflow state

---

## RD-10: Note Density Management (AD-3, FR-095-099)

**Question**: How to prevent AI output from overwhelming the note canvas?

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **Collapsible sections + Focus Mode** | AI blocks collapse; toggle hides all AI | Clean UX, progressive disclosure | Requires new TipTap extension |
| Pagination / "Load More" | Show 50 blocks, load more on scroll | Simple | Breaks document reading flow |
| Separate AI canvas | AI output in side panel, not in note | Clean separation | Defeats "notes as artifact store" principle |

**Decision**: **Collapsible sections + sidebar panels + Focus Mode**

**Rationale**:
- Collapsible AI blocks: intent groups and progress blocks collapse to summary headers
- Focus Mode: toggle CSS class to hide all `ai:*` blocks — instant clean view
- Sidebar panels: version history, presence, conversations live in sidebar (not inline blocks)
- Preserves document structure (unlike pagination)
- Keeps notes as artifact store (unlike separate canvas)
- TipTap extension `CollapsibleAIBlockExtension` wraps consecutive ai-owned blocks

---

## RD-11: Version Storage Format (FR-034-042)

**Question**: How to store note versions?

| Option | Size | Diff Support | CRDT Compat |
|--------|------|-------------|-------------|
| **Yjs state vectors + full snapshots** | Medium | Built-in | Native |
| Full document snapshots only | Large | Requires JSON diff | No Yjs awareness |
| Delta diffs only | Small | Native | Complex restore |

**Decision**: **Yjs state vectors for collaborative state + full snapshots for AI operations**

**Rationale**:
- Yjs provides efficient state vectors (binary, incremental) — use for auto-save versions
- AI before/after versions need full content snapshots (independent of CRDT state)
- Restore: apply Yjs state vector (resets CRDT state) OR set content from full snapshot
- Delta-only storage is fragile (chain breaks lose history); full snapshots are safer for AI operations
- Storage cost is acceptable: ~5KB per full snapshot at 200 blocks; 100 versions = 500KB per note

---

## RD-12: DAG Rendering for Dependency Map (FR-051-052)

**Question**: How to render the issue dependency DAG?

| Option | Layout Algo | Bundle | Interactivity |
|--------|------------|--------|---------------|
| **dagre + D3.js** | Dagre (hierarchical) | ~80KB | SVG with D3 zoom/pan |
| React Flow | Dagre or Elkjs | ~120KB | React-based, drag-and-drop |
| vis.js | Physics-based | ~150KB | Canvas-based |
| Mermaid | Auto-layout | ~200KB | Static SVG |

**Decision**: **dagre + D3.js**

**Rationale**:
- dagre provides clean hierarchical DAG layout — best for dependency visualization
- D3.js for SVG rendering with zoom/pan (FR-052) — lightweight, performant
- React Flow overkill for read-only display (drag-and-drop not needed)
- vis.js physics-based layout is unpredictable for DAGs
- Mermaid is static — no interactivity (need click-to-popover for node details)
- Critical path highlighting: longest-path algorithm on DAG, highlighted edges in red
