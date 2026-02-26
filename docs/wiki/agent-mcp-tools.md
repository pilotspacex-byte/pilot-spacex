# Pilot Space Agent: MCP Tools & Servers

> **Location**: `backend/src/pilot_space/ai/mcp/`, `backend/src/pilot_space/ai/tools/`
> **Design Decisions**: DD-088 (MCP Tool Registry), DD-003 (Human-in-the-Loop), DD-061 (RLS)

## Overview

The MCP (Model Context Protocol) layer is the **AI agent's hands** — the concrete operations it can perform on Pilot Space data. 33 tools across 6 specialized servers give the agent the ability to read, create, and modify notes, issues, projects, comments, and relationships. Every tool enforces RLS workspace isolation, many require human approval before execution, and results stream back to the frontend via SSE events. The servers run in-process (not as network daemons) for zero-latency tool calls.

---

## Architecture

```
PilotSpaceAgent (SDK config)
    ↓ registers in-process MCP servers:
┌───────────────────────────────────────────────────┐
│  note_server        (8 tools)   ← note CRUD       │
│  note_content_server(5 tools)   ← block operations│
│  issue_server       (8 tools)   ← issue CRUD      │
│  issue_relation_server(4 tools) ← relations/links │
│  project_server     (3 tools)   ← project ops     │
│  comment_server     (3 tools)   ← comment CRUD    │
│  interaction_server (1 tool)    ← questions       │
│  ownership_server   (1 tool)    ← assignment      │
└───────────────────────────────────────────────────┘
    ↓ per-tool execution:
registry.py         ← tool registration + approval level lookup
base.py             ← shared: RLS setup, error handling, auth
event_publisher.py  ← emit SSE events for tool results
block_ref_map.py    ← ¶N notation: block ID ↔ short reference
entity_resolver.py  ← UUID + human-readable ID resolution
```

---

## Tool Inventory (33 Tools)

### Note Server — `mcp/note_server.py` (8 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `note.list_notes` | AUTO | List workspace notes with pagination |
| `note.get_note` | AUTO | Read note metadata (title, created_at, blocks count) |
| `note.read_note` | AUTO | Read full note content (TipTap JSON) |
| `note.search_notes` | AUTO | Full-text search via Meilisearch |
| `note.create_note` | DEFAULT | Create new note with content |
| `note.update_note` | DEFAULT | Update note content |
| `note.delete_note` | CRITICAL | Delete note permanently |
| `note.link_note_to_issue` | DEFAULT | Create NoteIssueLink (REFERENCED) |

### Note Content Server — `mcp/note_content_server.py` (5 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `note_content.get_block` | AUTO | Read a specific block by ID or ¶N reference |
| `note_content.update_block` | DEFAULT | Update content of a specific block |
| `note_content.insert_block` | DEFAULT | Insert new block at position |
| `note_content.delete_block` | DEFAULT | Delete a block |
| `note_content.get_selected_blocks` | AUTO | Read the blocks user has selected |

### Issue Server — `mcp/issue_server.py` (8 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `issue.list_issues` | AUTO | List workspace issues with filters |
| `issue.get_issue` | AUTO | Read issue details |
| `issue.search_issues` | AUTO | Full-text + semantic search |
| `issue.create_issue` | DEFAULT | Create issue (title, description, priority, labels) |
| `issue.update_issue` | DEFAULT | Update issue fields |
| `issue.update_issue_state` | DEFAULT | Transition issue state machine |
| `issue.delete_issue` | CRITICAL | Delete issue permanently |
| `issue.bulk_create_issues` | DEFAULT | Create multiple issues atomically |

### Issue Relation Server — `mcp/issue_relation_server.py` (4 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `issue_relation.add_relation` | DEFAULT | Create issue → issue relationship |
| `issue_relation.remove_relation` | DEFAULT | Remove issue relationship |
| `issue_relation.get_relations` | AUTO | List all relations for an issue |
| `issue_relation.merge_pr` | CRITICAL | Mark PR as merged (closes related issues) |

### Project Server — `mcp/project_server.py` (3 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `project.list_projects` | AUTO | List workspace projects |
| `project.get_project` | AUTO | Read project details + members |
| `project.archive_workspace` | CRITICAL | Archive entire workspace |

### Comment Server — `mcp/comment_server.py` (3 tools)

| Tool | Approval | Description |
|------|----------|-------------|
| `comment.list_comments` | AUTO | List comments on an entity |
| `comment.post_comment` | DEFAULT | Post comment on issue/note |
| `comment.delete_comment` | CRITICAL | Delete a comment |

### Other Servers (2 tools)

| Tool | Server | Approval | Description |
|------|--------|----------|-------------|
| `interaction.ask_user` | interaction_server | AUTO | Emit QuestionBlock to user |
| `ownership.assign` | ownership_server | DEFAULT | Assign issue to team member |

---

## Approval Distribution

| Tier | Count | Examples |
|------|-------|---------|
| AUTO_EXECUTE | 13 | All `list_*`, `get_*`, `search_*`, `read_*` |
| DEFAULT (require approval) | 18 | All `create_*`, `update_*`, `post_*`, `link_*` |
| CRITICAL (always require) | 2 | `delete_issue`, `archive_workspace` |

---

## Key Patterns

### 3-Layer RLS Enforcement

Every tool call passes through three security layers:

```
Layer 1: Application context variable
  set_rls_context(workspace_id, user_id, role)
  → sets PostgreSQL session variables for RLS policies

Layer 2: Explicit workspace_id filter in query
  WHERE workspace_id = {workspace_id}
  → defense-in-depth against misconfigured RLS

Layer 3: Database-level RLS policy
  CREATE POLICY ... USING (workspace_id = current_setting('app.current_user_workspace_id')::uuid)
  → ultimate enforcement, cannot be bypassed by application layer
```

**Attacker scenario**: If Layer 1 or 2 is bypassed, Layer 3 (database) still blocks cross-workspace data access. The database is the absolute security boundary.

### Operation Payload Pattern

For DEFAULT and CRITICAL tools, the MCP handler does not execute immediately. Instead it returns an **operation payload** — a serialized description of what would be done — which is routed through the approval workflow:

```python
# Tool handler for create_issue:
async def create_issue(title, description, workspace_id):
    # Build payload but don't execute
    payload = IssueCreatePayload(title=title, description=description)

    # Route to approval
    return OperationPayload(
        action_type="create_issue",
        payload=payload.model_dump(),
        reasoning="User asked to create issue from note",
        confidence=0.95,
    )
    # Actual creation happens after user approves
```

**Why operation payloads?** The approval UI (`IssuePreview`, `ContentDiff`) needs the full payload to render a meaningful preview. Returning the payload before execution enables rich approval UX without a separate "preview" endpoint.

### Event Publisher — `mcp/event_publisher.py`

After a tool executes (post-approval), `EventPublisher` emits the result as an SSE event:

```python
async with publisher.tool_event(tool_use_id, tool_name):
    result = await actual_execute(payload)
    # On exit: emits tool_result SSE with result JSON
    # Atomic: yield of tool_use_id paired with tool_result
```

**Atomicity**: `asyncio.Lock` ensures `tool_use` and `tool_result` SSE events for the same tool call are never interleaved with another tool's events.

**"View in note" link**: For note-modifying tools (`update_note`, `update_block`), the result includes `note_id` → frontend `ToolCallCard` shows "View in note" link.

### Block Reference Map — `mcp/block_ref_map.py`

Note blocks are TipTap block UUIDs (`"3f7a2b1c-..."`). Passing full UUIDs in tool calls wastes tokens and makes prompts hard to read.

**¶N notation**: `BlockRefMap` maintains a short reference map:
```
¶1 = "3f7a2b1c-4d5e-..."
¶2 = "7a8b9c0d-1e2f-..."
```

The AI can say "update ¶3 to say..." instead of passing a 36-char UUID. `BlockRefMap.resolve("¶3")` → full UUID before hitting the database.

**Built fresh per request**: The map is rebuilt on each tool call that reads note content. Not cached — block IDs are stable but the map is cheap to build.

### Entity Resolver — `tools/entity_resolver.py`

Issues can be referenced by:
- UUID: `"3f7a2b1c-..."`
- Short ID: `"PILOT-42"` (project prefix + number)
- Title: `"Fix login bug"` (fuzzy match)

`EntityResolver.resolve_issue(ref, workspace_id)` handles all three and returns the canonical UUID. Prevents tool calls from failing on human-readable references.

---

## Database Tools (`tools/database_tools.py`)

Low-level database query tools available to subagents with elevated permissions. Used by `AIContextAgent` for broader data access patterns:

- `db.query_issues(filters)` — flexible issue query with date ranges, label filters, assignee filters
- `db.query_notes(filters)` — note search with content matching
- `db.semantic_search(query, limit)` — pgvector similarity search over note/issue embeddings

**RLS applies**: Even database tools go through `set_rls_context()` — workspace isolation is enforced at the database level regardless of which tool calls the query.

---

## Search Tools (`tools/search_tools.py`)

- `search.full_text(query, entity_type)` — Meilisearch full-text search (typo-tolerant)
- `search.semantic(query, entity_type, limit)` — pgvector cosine similarity (768-dim Gemini embeddings)
- `search.hybrid(query, entity_type)` — combined full-text + semantic with re-ranking

**Hybrid search**: Combines Meilisearch hits (precision) with pgvector results (recall). Re-ranking uses a simple weighted score: `0.6 * bm25_score + 0.4 * cosine_similarity`.

---

## GitHub Tools (`tools/github_tools.py`)

Integration tools for GitHub PR workflow (used by `PRReviewSubagent`):

- `github.get_pr(repo, pr_number)` — fetch PR metadata, diff, and existing comments
- `github.post_review(repo, pr_number, comments)` — post review comments with severity
- `github.get_commits(repo, branch)` — list commits since branch point

**Note**: GitHub tools are **stub implementations** in the current codebase — the structure and signatures are complete but the actual GitHub API calls use placeholder logic pending OAuth integration per workspace.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| In-process MCP (no network) | Python objects registered to SDK | `config.py` |
| ¶N short block references | `BlockRefMap` per request | `block_ref_map.py` |
| Human-readable issue refs | `EntityResolver` (UUID / PILOT-N / title) | `entity_resolver.py` |
| Atomic tool_use + tool_result SSE | `asyncio.Lock` in `EventPublisher` | `event_publisher.py` |
| "View in note" link in results | `note_id` injected in tool result | `event_publisher.py` |
| Circular dependency detection | DAG validation in `issue_relation_server` | `issue_relation_server.py` |
| Bulk issue creation atomicity | Single transaction for `bulk_create_issues` | `issue_server.py` |
| Semantic search deduplication | Hybrid re-ranking removes overlap | `search_tools.py` |
| RLS context per tool call | `set_rls_context()` in `base.py` | `base.py` |
| ReDoS prevention | Pattern length + quantifier limits | `base.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| 6 specialized servers (not 1 monolith) | Single Responsibility — each server owns its domain. Easier to test, evolve, and audit independently. |
| Operation payload before execution | Enables rich approval previews (`IssuePreview`, `ContentDiff`) without a separate preview API. |
| 3-layer RLS enforcement | Defense-in-depth. App-layer RLS context can be misconfigured; database-level policy is the absolute boundary. |
| ¶N block references | 36-char UUIDs in prompts waste tokens and are unreadable. `¶3` is 2 tokens and semantically clear. |
| In-process servers (not network) | 10-50ms latency saved per tool call vs. HTTP to a separate MCP daemon. RLS Python objects can be shared. |
| CRITICAL tier = 2 tools only | Minimizes friction. Only truly irreversible actions (permanent delete, workspace archive) are always-block. |
| Entity resolver (3 ref types) | AI naturally generates human-readable references ("PILOT-42"). Resolver prevents tool failures on valid AI output. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `mcp/README.md` | — | MCP layer architecture overview |
| `mcp/base.py` | ~150 | Base class: RLS setup, auth, error handling |
| `mcp/registry.py` | ~120 | Tool registration + approval level map |
| `mcp/event_publisher.py` | ~100 | Atomic SSE event emission for tool results |
| `mcp/block_ref_map.py` | ~80 | ¶N ↔ UUID block reference mapping |
| `mcp/note_server.py` | ~300 | 8 note CRUD tools |
| `mcp/note_content_server.py` | ~200 | 5 note block operations |
| `mcp/issue_server.py` | ~350 | 8 issue CRUD tools |
| `mcp/issue_relation_server.py` | ~200 | 4 relation + PR merge tools |
| `mcp/project_server.py` | ~150 | 3 project tools |
| `mcp/comment_server.py` | ~150 | 3 comment CRUD tools |
| `mcp/interaction_server.py` | ~80 | 1 question tool |
| `mcp/ownership_server.py` | ~80 | 1 assignment tool |
| `mcp/tools/pr_review.py` | ~120 | GitHub PR review tools |
| `tools/database_tools.py` | ~200 | Flexible DB query tools for subagents |
| `tools/entity_resolver.py` | ~150 | UUID / short-ID / title resolution |
| `tools/search_tools.py` | ~180 | Full-text + semantic + hybrid search |
| `tools/github_tools.py` | ~150 | GitHub API integration (stub) |
