# Pilot Space - Design Decisions & Clarifications

Architecture decision record optimized for AI context retrieval. Full rationale in expandable sections.

**Document Version**: 3.3 | **Last Updated**: 2026-01-28 | **Decisions**: 88

---

## Quick Reference: Decision Index

| ID | Decision | Status | Impact |
|----|----------|--------|--------|
| DD-001 | FastAPI replaces Django | Accepted | Stack |
| DD-002 | BYOK + Claude SDK orchestration | Accepted | AI |
| DD-003 | Critical-only AI approval | Accepted | AI |
| DD-004 | MVP: GitHub + Slack only | Accepted | Scope |
| DD-005 | No real-time collaboration MVP | Accepted | Scope |
| DD-006 | Unified AI PR Review | Accepted | AI |
| DD-007 | Basic RBAC (Owner/Admin/Member/Guest) | Accepted | Auth |
| DD-008 | Remove AI Studio | Accepted | Scope |
| DD-009 | Merge Space app into main | Accepted | Arch |
| DD-010 | Support tiers (features free) | Accepted | Business |
| DD-011 | Google Gemini support | Accepted | AI |
| DD-012 | Multi-format diagrams | Accepted | Features |
| DD-013 | Note-First workflow | Accepted | Core UX |
| DD-014–053 | UI/UX decisions | Accepted | UI |
| DD-054 | MVP exclusions | Accepted | Scope |
| DD-055 | AI Context architecture | Accepted | AI |
| DD-056 | AI Context updates: on-demand | Accepted | AI |
| DD-057 | GraphRAG hybrid (Phase 2) | Accepted | AI |
| DD-058 | Claude SDK mode clarification | Accepted | AI |
| DD-059 | Infrastructure SLA & Performance | Accepted | Infra |
| DD-060 | Supabase Platform Integration | Accepted | Infra |
| DD-061 | Authentication & Security | Accepted | Auth |
| DD-062 | Data Management Policies | Accepted | Data |
| DD-063 | API Design Standards | Accepted | API |
| DD-064 | Backend Architecture Patterns | Accepted | Arch |
| DD-065 | Frontend Architecture Patterns | Accepted | Arch |
| DD-066 | SSE Streaming Architecture | Accepted | AI |
| DD-067 | Note Canvas Implementation | Accepted | Features |
| DD-068 | Knowledge Graph Architecture | Accepted | Features |
| DD-069 | Background Job Configuration | Accepted | Infra |
| DD-070 | Embedding & Search Configuration | Accepted | AI |
| DD-071–085 | User Story Clarifications | Accepted | Features |
| DD-086 | Conversational Agent Architecture | Accepted | AI |
| DD-087 | Skill System Design | Accepted | AI |
| DD-088 | MCP Tool Registry | Accepted | AI |

---

## Foundational Decisions (DD-001–012)

### DD-001: FastAPI Replaces Django

**Stack**: FastAPI + SQLAlchemy 2.0 (async) + Alembic + Pydantic v2

| Layer | Technology |
|-------|------------|
| API | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | FastAPI-Users / custom JWT |

<details>
<summary>Rationale & Consequences</summary>

**Why**: Single framework, modern async, better AI workload support, cleaner OpenAPI docs.

**Trade-offs**: Lose Django admin (use SQLAdmin), need FastAPI/SQLAlchemy expertise.
</details>

---

### DD-002: BYOK with Claude Agent SDK Orchestration

**Required Keys**: Anthropic (orchestration), OpenAI (embeddings)
**Optional Keys**: Google (latency-sensitive), Azure (enterprise fallback)

**SDK Mode Selection**:

| Task Type | SDK Mode | Tools |
|-----------|----------|-------|
| PR Review, Task Decomp, AI Context | Claude SDK (agentic) | MCP: DB, GitHub, Search |
| Doc Generation, Issue Enhancement | Claude SDK `query()` | None |
| Ghost Text, Annotations | Google Gemini Flash | None |
| Embeddings | OpenAI text-embedding-3-large | None |

<details>
<summary>Configuration & Architecture Diagram</summary>

```yaml
ai:
  orchestrator:
    sdk: claude-agent-sdk
    default_model: claude-opus-4-5
  providers:
    anthropic:
      models: [claude-opus-4-5, claude-sonnet-4, claude-haiku-4]
      use_for: [pr_review, task_decomposition, ai_context, doc_generation]
    google:
      models: [gemini-2.0-flash, gemini-2.0-pro]
      use_for: [ghost_text, margin_annotations, large_context]
    openai:
      models: [text-embedding-3-large]
      use_for: [embeddings]
```

```text
┌─────────────────────────────────────────────────────────────────┐
│                   TASK ROUTING LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Agentic (MCP tools)        → Claude SDK (full)                 │
│  One-shot Claude            → Claude SDK query()                │
│  Latency-Critical           → Google Gemini Flash               │
│  Embeddings                 → OpenAI text-embedding             │
└─────────────────────────────────────────────────────────────────┘
```

</details>

---

### DD-003: AI Autonomy - Critical-Only Approval

| Action | Behavior | Configurable |
|--------|----------|--------------|
| Suggest labels/priority | Auto-apply UI | Yes |
| Auto-transition on PR | Auto + notify | Yes |
| Create sub-issues | Require approval | Yes |
| Delete/archive | **Always approval** | No |

<details>
<summary>Configuration Schema</summary>

```yaml
project:
  ai_autonomy:
    level: balanced  # conservative | balanced | autonomous
    overrides:
      state_transitions: auto
      pr_comments: auto
      issue_creation: approval
```

</details>

---

### DD-004: MVP Integrations

**In Scope**: GitHub (PR linking, AI review), Slack (notifications, commands)

**Deferred**: GitLab, Discord, CI/CD (Phase 2)

**Removed**: Jira sync, Trello/Asana, Bitbucket, MS Teams

---

### DD-005: No Real-Time Collaboration in MVP

Standard save-based editing with autosave. Last-write-wins for concurrent edits.

**Future**: Y.js/HocusPocus for Pages in Phase 2 if demand exists.

---

### DD-006: Unified AI PR Review

Single feature covering: architecture, security, quality, performance, documentation.

| Aspect | Checks |
|--------|--------|
| Architecture | Layer boundaries, patterns, dependencies |
| Security | OWASP basics, secrets detection |
| Quality | Complexity, duplication, naming |
| Performance | N+1 queries, blocking calls |

---

### DD-007: Basic RBAC

| Role | Permissions |
|------|-------------|
| Owner | Full workspace control, billing, delete |
| Admin | Manage members, projects, integrations |
| Member | Create/edit issues, pages, cycles |
| Guest | View/comment on assigned issues |

**Phase 2**: Custom roles, granular permissions, project-level overrides.

---

### DD-008: Remove AI Studio

No custom agent creation. Built-in agents with workspace-level prompt customization only.

---

### DD-009: Merge Space App

Public views as routes in main app: `/public/projects/:id`, `/public/issues/:id`

---

### DD-010: Support Tiers

| Tier | Price | Features |
|------|-------|----------|
| Community | Free | Full platform |
| Pro Support | $10/seat/mo | Email, 48h SLA |
| Business | $18/seat/mo | Priority, 24h SLA |

**Principle**: Self-hosted always free. Paid = support only.

---

### DD-011: Google Gemini Support

| Model | Use Case | Context |
|-------|----------|---------|
| gemini-2.0-flash | Fast tasks (ghost text) | 256K |
| gemini-2.0-pro | Large codebase analysis | 2M |

---

### DD-012: Multi-Format Diagrams

Supported: Mermaid (default), PlantUML, C4 Model, Structurizr DSL

---

## Core UX Decisions (DD-013)

### DD-013: Note-First Collaborative Workspace

**Paradigm**: Users write in note canvas → AI assists → Issues emerge from refined thoughts

**Workflow**: Capture → Brainstorm (AI) → Refine (threads) → Extract (rainbow boxes) → Approve → Track

<details>
<summary>Key Features</summary>

| Feature | Description |
|---------|-------------|
| Note Canvas as Home | Default view is document, not dashboard |
| Margin Annotations | AI suggestions in margin (smart visibility) |
| Issue Extraction | Rainbow-bordered boxes wrap source text |
| Bidirectional Sync | Notes ↔ Issues stay connected |

</details>

---

## UI/UX Decisions Summary (DD-014–053)

| ID | Decision | Summary | Why |
|----|----------|---------|-----|
| DD-014 | Issue Detail Modal | Quick view modal, not full page | Preserves writing context; full page for deep editing |
| DD-015 | Block-Linked Annotations | Click annotation → scroll to block | Clear visual relationship between suggestion and context |
| DD-016 | New Note AI Prompt | AI greeting + template suggestions | Reduces blank page anxiety; leverages user history |
| DD-017 | Sidebar Organization | Project folders + tag filtering | Projects = logical groups; tags = cross-cutting views |
| DD-018 | Command Palette | Smart AI suggestions by context | Context-aware actions save time; fuzzy handles typos |
| DD-019 | Search Modal | Full-page spotlight (Cmd+K) | Large modal for results; preview avoids navigation |
| DD-020 | Selection Toolbar | Rich formatting + AI actions | AI actions contextual to selected text; quick extract |
| DD-021 | Keyboard Shortcuts | Slash (/) + hotkeys (Cmd+) | Multiple discovery methods for different learning styles |
| DD-022 | Ghost Text | Tab = full, → = word-by-word | Fine control; non-intrusive; familiar from code editors |
| DD-023 | Version History | Snapshots with AI reasoning | Full audit trail; easy revert; AI transparency |
| DD-024 | Issue Detection | Margin indicator, not inline | Non-intrusive; text preserved until explicit approval |
| DD-025 | AI Error States | Non-blocking margin + retry | Preserves workflow; consistent with AI annotations |
| DD-026 | FAB | Bottom-right, opens AI search | Quick access from any view; combines search + AI |
| DD-027 | AI Panel | Collapsible bottom + chips | Detailed AI results; chips for quick actions |
| DD-028 | Status Indicators | Detailed text ("Analyzing...") | Transparency; reduces perceived wait (Claude Code pattern) |
| DD-029 | Artifact Preview | Collapsed 2-3 lines + fade | Space-efficient; expand for full content |
| DD-030 | Code Blocks | Syntax + line numbers + copy | Developer-focused; standard code display features |
| DD-031 | Image Insert | Paste, drag, upload, URL | Multiple methods for different workflows |
| DD-032 | Issue Extraction | Interactive inline, one at a time | Source highlighted; edit before accept; focused flow |
| DD-033 | Templates | System + User + AI-generated | Cover all use cases; AI learns from patterns |
| DD-034 | Note Header | Metadata + AI reading time | Quick context without reading; AI-enhanced estimate |
| DD-035 | TOC | Auto-generated from headings | Navigation for long docs; no manual maintenance |
| DD-036 | Similar Notes | AI guidance on differences | Avoid duplication; understand relationships |
| DD-037 | Graph View | Force-directed (Obsidian-style) | Visual exploration of knowledge relationships |
| DD-038 | Notifications | AI-prioritized smart inbox | Surface important items; reduce noise |
| DD-039 | API Keys | Workspace-level, admin-managed | Centralized control; single billing point |
| DD-040 | Context Menus | Standard + AI section | Familiar UX; AI discoverable but not dominant |
| DD-041 | Block Reorder | Keyboard only (Cmd+Shift+↑/↓) | Precision over drag-and-drop; accessibility |
| DD-042 | Tags | AI-suggested based on content | Reduce manual tagging; consistent taxonomy |
| DD-043 | Bulk Actions | Standard + AI (Summarize, Extract) | Efficiency for batch operations |
| DD-044 | Tooltips | Progressive (instant → 1s detail) | Quick labels; detail on hover-wait |
| DD-045 | Onboarding | Sample "Product Launch" project | Learn by exploring real example |
| DD-046 | Long Notes | Virtual scroll (1000+ blocks) | Performance for large documents |
| DD-047 | Model Selection | Auto-select best, user override | Optimal defaults; power user control |
| DD-048 | Confidence Tags | Recommended/Default/Current/Alt | Human-readable vs confusing percentages |
| DD-049 | Autosave | 1-2s debounce, subtle indicator | No data loss; non-distracting feedback |
| DD-050 | Undo Stack | Text + AI + block moves | Full recovery including AI changes |
| DD-051 | Recent Notes | Edited + viewed combined | Single list; both access patterns matter |
| DD-052 | Pin Notes | Sidebar top section | Quick access to frequently used notes |
| DD-053 | Margin Panel | Resizable (150-350px) | User controls annotation space |

---

## Scope Exclusions (DD-054)

| Feature | Reason | Phase |
|---------|--------|-------|
| Offline editing | Infrastructure complexity | - |
| Note sharing/export | Focus on core workflow | Phase 2 |
| Saved views/filters | Keep filtering simple | Phase 2 |
| Focus/Zen mode | Standard layout sufficient | - |
| Quick capture extension | Must be in app | - |
| Inline comments | Team collaboration | Phase 2 |
| Mobile-specific | Desktop-first | Phase 2 |

**Removed Permanently**: Jira sync, Trello/Asana, AI Studio, Ollama, MS Teams, Bitbucket

---

## AI Architecture Decisions (DD-055–058)

### DD-055: AI Context Architecture

**Approach**: Hybrid (real-time discovery + cached embeddings)

| Aspect | Decision |
|--------|----------|
| Data Source | Hybrid (real-time + cached) |
| File Relevance | Semantic similarity + explicit tags |
| Code Depth | AST-aware (functions/classes) |
| Export Format | Markdown for Claude Code |

<details>
<summary>Architecture Diagram</summary>

```text
Data Sources              Context Engine              Output
┌──────────────┐        ┌────────────────┐        ┌──────────────┐
│ Real-Time    │───────▶│ Aggregation +  │───────▶│ UI Tab       │
│ • Issue links│        │ Scoring        │        │ Markdown     │
│ • Doc search │        └────────┬───────┘        │ Claude Code  │
│ • Git history│                 │                └──────────────┘
├──────────────┤        ┌────────▼───────┐
│ Cached       │───────▶│ Task           │
│ • Embeddings │        │ Generation     │
│ • AST index  │        └────────────────┘
└──────────────┘
```

</details>

---

### DD-056: AI Context Update Strategy

**Decision**: On-demand only with change notifications

- User opens AI Context tab → fresh generation
- Data changes → badge shows "Updates available"
- User clicks "Regenerate" → new context

---

### DD-057: GraphRAG Hybrid Retrieval (Phase 2)

**Algorithm**: Reciprocal Rank Fusion (RRF)

```text
RRF_score(d) = Σ 1/(k + rank_i(d))   where k=60
```

**Why RRF**: No normalization needed, robust fusion, pure SQL implementation.

<details>
<summary>SQL Implementation</summary>

```sql
-- Hybrid search combining vector + graph retrieval
CREATE FUNCTION hybrid_search(query_embedding vector, query_entity_id uuid, ...)
RETURNS TABLE (entity_id uuid, rrf_score float, ...)
-- See full implementation in Phase 2 specs
```

</details>

---

### DD-058: Claude Agent SDK Mode Clarification

**Key Insight**: Claude Agent SDK is Anthropic-only. Non-Claude providers use direct SDKs.

| Category | Orchestrator | Examples |
|----------|--------------|----------|
| Agentic (MCP tools) | Claude SDK (full) | PR Review, Task Decomp, AI Context |
| One-shot Claude | Claude SDK `query()` | Doc Generation, Issue Enhancement |
| Non-Claude tasks | Direct SDKs | Ghost Text (Gemini), Embeddings (OpenAI) |

**API Key Dependencies**:

| Key | Status | Impact if Missing |
|-----|--------|-------------------|
| Anthropic | Required | Core AI features disabled |
| OpenAI | Required | Semantic search disabled |
| Google | Recommended | Ghost text slower (Haiku fallback) |

<details>
<summary>Architecture Diagram</summary>

```text
┌─────────────────────────────────────────────────────────────────┐
│                    TASK CLASSIFICATION                           │
├─────────────────────────────────────────────────────────────────┤
│  task.requires_tools? ─────────────────────────────────────┐    │
│         │                                                   │    │
│    YES  │  NO                                              │    │
│         │   └─ task.type == "embeddings"?                  │    │
│         │              │                                    │    │
│         │         YES  │  NO                               │    │
│         │              │   └─ task.latency_critical?       │    │
│         │              │              │                     │    │
│         │              │         YES  │  NO                │    │
│         ▼              ▼              ▼     ▼               │    │
│  Claude SDK     OpenAI         Gemini    Claude SDK        │    │
│  (Agentic)      Embeddings     Flash     query()           │    │
└─────────────────────────────────────────────────────────────────┘
```

</details>

---

## Infrastructure Clarifications (DD-059–060)

### DD-059: Infrastructure SLA & Performance

**Date**: 2026-01-20 | **Status**: Accepted

| Metric | Target |
|--------|--------|
| Uptime | 99.5% (~3.6 hours/month max downtime) |
| RTO | 4 hours |
| API reads (p95) | < 500ms |
| API writes (p95) | < 1s |
| Rate limit (standard) | 1000 req/min per workspace |
| Rate limit (AI endpoints) | 100 req/min per workspace |

**Deferred to Phase 2**: Structured logging, metrics, tracing
**Deferred to Phase 3**: GDPR, SOC2, data residency compliance

---

### DD-060: Supabase Platform Integration

**Date**: 2026-01-22 | **Status**: Accepted

**Decision**: Consolidate infrastructure to Supabase platform (10+ services → 2-3)

| Component | Solution |
|-----------|----------|
| Auth | Supabase Auth (GoTrue) - email, OAuth, SAML 2.0 SSO |
| Database | PostgreSQL 16+ via Supabase |
| Vector Search | pgvector + HNSW (m=16, ef_construction=64) |
| Storage | Supabase Storage (S3-compatible, RLS, CDN) |
| Queues | Supabase Queues (pgmq + pg_cron) |
| Realtime | Supabase Realtime (per-workspace channel) |
| Connection Pool | Managed PgBouncer (no separate container) |

**No LDAP in MVP**: SAML 2.0 SSO covers enterprise needs.

---

## Security Clarifications (DD-061)

### DD-061: Authentication & Security

**Date**: 2026-01-22 | **Status**: Accepted

| Aspect | Decision |
|--------|----------|
| Auth Provider | Supabase Auth (GoTrue) |
| Token Strategy | Access (1h) + Refresh (7d), rotate on refresh |
| Authorization | Row-Level Security (RLS) at database level |
| API Key Encryption | AES-256-GCM with Supabase Vault |
| Service Role Key | Backend services only (FastAPI) |
| Anon Key | Client-side SDK (RLS enforced) |

**RLS Policy Pattern**:

```sql
-- Workspace member check
workspace_members.role IN ('admin', 'owner')
-- User identification
auth.uid() = user_id
```

---

## Data Management Clarifications (DD-062)

### DD-062: Data Management Policies

**Date**: 2026-01-22 | **Status**: Accepted

**Issue State Transitions**:

| From | To | Allowed |
|------|----|----|
| unstarted | started | ✅ |
| started | completed | ✅ |
| completed | started | ✅ (reopen) |
| any | cancelled | ✅ |
| cancelled | any | ❌ (terminal) |
| unstarted | completed | ❌ (no skip) |

**Soft Deletion**:

- 30-day recovery window
- Restoration by: original creator OR workspace admin/owner
- Deleted linked issue in note: strikethrough + "Deleted" badge

**Export/Import**:

- Format: JSON archive (ZIP with structured JSON per entity)
- Import: restore-from-backup only (same format as export)
- No migration tools in MVP

---

## API Design Clarifications (DD-063)

### DD-063: API Design Standards

**Date**: 2026-01-22 | **Status**: Accepted

| Aspect | Decision |
|--------|----------|
| Versioning | URL path (`/api/v1/issues`) |
| Error Format | RFC 7807 Problem Details |
| Pagination | Cursor-based (stable with real-time updates) |
| Response Envelope | `{data: [...], meta: {total, cursor, hasMore}}` |
| Optimistic Updates | TanStack Query with automatic rollback |

**GitHub Rate Limit Handling**: Queue with exponential backoff (1 min initial, 30 min max) + user notification

---

## Backend Architecture Clarifications (DD-064)

### DD-064: Backend Architecture Patterns

**Date**: 2026-01-22 | **Status**: Accepted

| Pattern | Implementation |
|---------|----------------|
| Use Case Organization | CQRS-lite (Command/Query separation, no event sourcing) |
| Service Structure | Service Classes with Payloads (`CreateIssueService.execute(payload)`) |
| Repository | Generic + Specific (`BaseRepository[T]` + domain extensions) |
| DI | `dependency-injector` library with full container |
| AI Agent Structure | Claude Agent SDK with state machines |
| Migrations | Alembic autogenerate + manual review |
| Config | Pydantic Settings + `.env` files |
| Logging | Structlog JSON with correlation IDs |
| UUID Generation | Database-generated via `gen_random_uuid()` |
| Activity Log | Action-only (actor, action, entity_type, entity_id, timestamp) |

---

## Frontend Architecture Clarifications (DD-065)

### DD-065: Frontend Architecture Patterns

**Date**: 2026-01-22 | **Status**: Accepted

**State Management Split**:

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Server Data | TanStack Query | Fetching, caching, mutations, optimistic updates |
| UI State | MobX | Selection, toggles, local drafts, temp filters |

**Rule**: No MobX store subscribes to TanStack Query. Use `useQuery` hooks directly.

**Structure**:

| Aspect | Decision |
|--------|----------|
| Module Organization | Feature folders (`features/issues/`, `features/notes/`) |
| TipTap Extensions | Extension per feature (`GhostTextExtension`, `MarginAnnotationExtension`) |
| Error Handling | Inline only (show in triggering component) |
| Auth Flow | Supabase JS Client SDK (automatic token refresh) |
| File Uploads | Direct to Supabase Storage with signed URL |
| Command Palette Search | Client-side fuzzy (fuse.js) for commands, server for content |
| Realtime Scope | Per-workspace channel, client-side filtering |
| Dynamic Import Threshold | > 50KB gzipped (Sigma.js, Mermaid, AI Panel) |
| Barrel Conventions | Feature-level only, no `export *` |

**Supabase Realtime + TanStack Query Merge**: Optimistic merge via `queryClient.setQueryData()`. Last-write-wins. Skip if local mutation pending.

---

## SSE Streaming Clarifications (DD-066)

### DD-066: SSE Streaming Architecture

**Date**: 2026-01-22 | **Status**: Accepted

**Architecture**: Separate EventSource per AI operation + cookie-based auth

| Aspect | Decision |
|--------|----------|
| Stream Multiplexing | No - separate stream per operation |
| Auth Method | HttpOnly cookie (1h access token) |
| Heartbeat | Server sends every 30s (`: heartbeat\n\n`) |
| Client Timeout | 45s no data → reconnect |
| Reconnect Strategy | 3 attempts, exponential backoff (1s, 2s, 4s) |
| Request Cancellation | AbortController per request |

**Error Display by Context**:

| Context | Display |
|---------|---------|
| Ghost Text | Inline muted "AI unavailable" (3s fade) |
| AI Panel | Panel error state + retry button |
| PR Review | Toast + notification center |
| Network Error | Retry with exponential backoff (3 attempts) |

**Command Palette AI Context**: Current selection + active entity type + document title. Cache 30s per entity.

---

## Note Canvas Clarifications (DD-067)

### DD-067: Note Canvas Implementation

**Date**: 2026-01-22 | **Status**: Accepted

**Ghost Text**:

| Aspect | Decision |
|--------|----------|
| Trigger | 500ms typing pause only (no manual trigger) |
| Context | Current block + 3 previous + 3 sections summary + user patterns |
| Max Length | 1-2 sentences (~50 tokens) |
| Code Blocks | Code-aware suggestions |
| Cancel | Any keystroke auto-cancels |

**Word Boundary Handling**:

| Aspect | Decision |
|--------|----------|
| Streaming | Buffer chunks until whitespace/punctuation before display |
| Word-by-word (→) | Split on whitespace, advance by complete words only |
| Partial token | Never display; wait for complete token from stream |
| Edge case | If stream ends mid-word, display complete word only |

**Margin Annotations**:

| Aspect | Decision |
|--------|----------|
| Position | Vertical stack next to block, scroll if overflow |
| Anchor | CSS Anchor Positioning API (Chrome 125+), fallback for Safari/Firefox |

**Issue Detection**:

| Aspect | Decision |
|--------|----------|
| Patterns | Action verbs + entities ("implement X", "fix Y", "add Z") |
| Pre-fill | Title + description + priority + labels (AI suggests all) |

**Virtualization**: `@tanstack/react-virtual` with TipTap NodeView wrapper, ResizeObserver for block heights

**Tab Key Priority**: 1) code block indent, 2) ghost text accept, 3) default behavior

**Content Change Detection**: Block-level via TipTap transaction. >20% blocks changed OR title/heading → trigger embedding. Debounce 5s.

---

## Knowledge Graph Clarifications (DD-068)

### DD-068: Knowledge Graph Architecture

**Date**: 2026-01-22 | **Status**: Accepted

**Visualization**: Sigma.js + react-sigma (WebGL, ForceAtlas2, 50K+ nodes)

Stack: Graphology (data) + Sigma.js (render) + @react-sigma/core + layout-force + minimap

| Aspect | Decision |
|--------|----------|
| Layout | Always auto-layout (no position persistence) |
| Relationship Types | Explicit (user) + Semantic (AI) + Mentions |
| Storage | PostgreSQL adjacency table (`from_id`, `to_id`, `type`, `weight`) |
| Semantic Detection | Embedding similarity (cosine > 0.7) + metadata |
| Update Schedule | Explicit links on save; semantic weekly batch |

---

## Background Job Clarifications (DD-069)

### DD-069: Background Job Configuration

**Date**: 2026-01-22 | **Status**: Accepted

**Priority Levels**:

| Level | Examples |
|-------|----------|
| High | PR review, ghost text |
| Normal | Embeddings, summaries |
| Low | Graph recalculation |

**Configuration**:

| Aspect | Value |
|--------|-------|
| AI Job Timeout | 5 minutes (retry on timeout) |
| Failed Job Handling | Dead letter queue + admin notification after max retries |
| Batch Schedule | Nightly 2 AM UTC (semantic graph, cleanup) |
| Job Cleanup | Completed jobs older than 7 days |

---

## Embedding & Search Clarifications (DD-070)

### DD-070: Embedding & Search Configuration

**Date**: 2026-01-22 | **Status**: Accepted

| Aspect | Decision |
|--------|----------|
| Embedding Model | OpenAI text-embedding-3-large (3072 dims) |
| Chunk Size | 512 tokens, 50 token overlap |
| Regeneration Trigger | >20% content diff (hash comparison) |
| Summary Granularity | Document + sections (H1/H2). No paragraph-level. |
| Summary Model | Claude Haiku 4.5 (fast bulk processing) |
| Structure Extraction | On save via async job (available within 30s) |
| AST Languages | Python, TypeScript/JavaScript, Go, Java, Rust (regex fallback for others) |

---

## User Story Clarifications (DD-071–085)

### DD-071: Issue Creation (US-2)

| Aspect | Decision |
|--------|----------|
| Duplicate Detection | Auto on title blur |
| 100% Match | Warn but allow (dialog with link to existing) |
| Confidence Display | "Recommended" tag for ≥80% only |

---

### DD-072: PR Review (US-3)

| Aspect | Decision |
|--------|----------|
| Trigger | Auto on PR open via webhook |
| Comment Format | Severity (🔴🟡🔵) + suggestion + rationale + AI fix prompt |
| Review Aspects | Architecture + Security + Quality (patterns, vulns, smells, coverage) |

---

### DD-073: Sprint Planning (US-4)

| Aspect | Decision |
|--------|----------|
| Velocity Calculation | Sum of story points for completed issues |
| Cycle Rollover | Manual selection modal (incomplete → rollover vs backlog) |

---

### DD-074: Modules/Epics (US-5)

| Aspect | Decision |
|--------|----------|
| Target Date | Optional with overdue warning badge |
| Progress Calculation | Hybrid: story points if available, issue count fallback |

---

### DD-075: Task Decomposition (US-7)

| Aspect | Decision |
|--------|----------|
| Estimation Unit | Story points (Fibonacci: 1, 2, 3, 5, 8, 13) |

---

### DD-076: Architecture Diagrams (US-8)

| Aspect | Decision |
|--------|----------|
| Edit Mode | Code editor + live preview side-by-side |

---

### DD-077: Slack Integration (US-9)

| Aspect | Decision |
|--------|----------|
| `/pilot create` | Opens Slack modal with title, description, priority fields |

---

### DD-078: Semantic Search (US-10)

| Aspect | Decision |
|--------|----------|
| Document Structure | Tree-based for docs, AST for code |
| Code AST Storage | Function/class signatures + docstrings (top-level symbols) |

---

### DD-079: AI Context (US-12)

| Aspect | Decision |
|--------|----------|
| Code Discovery | AST analysis of code references (file paths + symbols) |
| File Resolution | GitHub API search in linked repos |
| Context Extraction | Function signature + docstring + import dependencies |

---

### DD-080: Command Palette (US-13)

| Aspect | Decision |
|--------|----------|
| AI Suggestion Learning | Context-only ranking (no frequency learning) |

---

### DD-081: Templates (US-15)

| Aspect | Decision |
|--------|----------|
| AI-generated Storage | Workspace-level library |
| Placeholder Syntax | Smart detection (AI infers, no special syntax) |

---

### DD-082: Sample Project (US-16)

| Aspect | Decision |
|--------|----------|
| Deletion | Permanent delete (no soft delete for sample data) |

---

### DD-083: Notifications (US-17)

| Aspect | Decision |
|--------|----------|
| Priority Factors | Urgency (deadline), assignment, mention type |

---

### DD-084: GitHub Integration (US-18)

| Aspect | Decision |
|--------|----------|
| Commit Linking | Hybrid: parse on webhook + scheduled scan for missed |
| PR Merge Behavior | Always auto-complete issue (PR merge → Completed) |
| Branch Suggestion | `feature/PROJ-123-issue-title` format |

---

### DD-085: Accessibility & Focus

**Date**: 2026-01-22 | **Status**: Accepted

| Aspect | Decision |
|--------|----------|
| Conformance | WCAG 2.1 Level AA |
| Focus Navigation | Tab stays in editor. Escape → sidebar. F6 cycles regions. |
| Reduced Motion | CSS `@media (prefers-reduced-motion)` + Tailwind variants |
| Testing | Vitest + jsdom (integration), Playwright (E2E), MSW (SSE), axe-core (a11y) |

---

## Appendix: Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    PILOT SPACE MVP                               │
├─────────────────────────────────────────────────────────────────┤
│  WEB APP (React + TypeScript)                                   │
│  Routes: /app/* (auth) | /admin/* | /public/* (merged Space)   │
├─────────────────────────────────────────────────────────────────┤
│  FASTAPI BACKEND                                                 │
│  REST API | SQLAlchemy 2.0 | Alembic | Pydantic v2 | JWT       │
├─────────────────────────────────────────────────────────────────┤
│  DATA: PostgreSQL + pgvector | Redis | Supabase Queues         │
├─────────────────────────────────────────────────────────────────┤
│  EXTERNAL: GitHub | Slack | LLM Providers | Supabase Storage   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase Roadmap

### Phase 1: MVP

- Core PM (workspaces, projects, issues, cycles, modules, pages)
- AI: Issue enhancement, task decomposition, PR review, doc generation, semantic search
- Integrations: GitHub, Slack, Webhooks
- Basic RBAC

### Phase 2: Enhanced

- Real-time collaboration (Pages)
- GraphRAG hybrid search
- ADR, Sprint planning AI, Retrospective AI
- GitLab, Discord, CI/CD display
- Custom RBAC, SSO, Audit logging

### Phase 3: Enterprise

- Advanced analytics, workflow automation
- LDAP, compliance reporting, custom reports

---

*Document Version: 3.2 | Migrated: 2026-01-23 | Decisions: 58 original + 27 clarifications = 85 total*
*Source: spec.md clarification sessions (2026-01-20, 2026-01-21, 2026-01-22)*
