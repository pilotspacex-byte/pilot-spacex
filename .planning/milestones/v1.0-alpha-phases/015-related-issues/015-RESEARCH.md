# Phase 15: Related Issues - Research

**Researched:** 2026-03-10
**Domain:** Issue relationship discovery — semantic similarity via knowledge graph + manual linking + dismissal persistence
**Confidence:** HIGH

## Summary

Phase 15 adds a "Related Issues" panel to the existing issue detail page. The codebase already has every foundational piece: `IssueLink` model (with `RELATED` type), `IssueLinkRepository` (with `find_all_for_issue`), `KnowledgeGraphRepository` (with `hybrid_search` using pgvector), the existing `GET /workspaces/{id}/issues/{id}/relations` endpoint, and the frontend `useIssueRelations` hook. The knowledge graph is populated by the existing `kg_populate` background job (Phase 12 dependency satisfied).

The gap is: (1) a backend semantic-similarity endpoint that queries the KG for ISSUE nodes similar to a given issue and returns scored results with relationship reasons; (2) a dismissal table + endpoint so dismissed suggestions never resurface; (3) a backend endpoint for creating/deleting RELATED `IssueLink` records from the issue detail page; and (4) the frontend panel that renders AI suggestions (with dismiss) and manual link search.

**Primary recommendation:** Use the existing `IssueLink` table with `IssueLinkType.RELATED` for manual links, and add a new `issue_suggestion_dismissal` table for AI suggestion dismissal. Serve semantic suggestions from a new `GET /workspaces/{id}/issues/{id}/related-suggestions` endpoint that calls `KnowledgeGraphRepository.hybrid_search` with `node_types=[NodeType.ISSUE]`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RELISS-01 | Issue detail shows auto-suggested related issues (semantic similarity via knowledge graph) | `KnowledgeGraphRepository.hybrid_search` with `NodeType.ISSUE` filter; `GraphNodeModel.external_id` links graph node to `Issue.id`; new endpoint `GET .../related-suggestions` |
| RELISS-02 | User can manually link/unlink issues as related from the issue detail page | `IssueLink` model with `IssueLinkType.RELATED` exists; `IssueLinkRepository` create/delete; needs `POST`/`DELETE` endpoints wired to `workspace_issues.py` router |
| RELISS-03 | Related issues surface connections via shared notes, same project, and semantic similarity score | `graph_edges` table edges between ISSUE nodes already carry `weight`; `GraphEdgeModel.edge_type` (RELATES_TO, BELONGS_TO); `properties` JSONB can carry reason string; new `reason` field on suggestion response |
| RELISS-04 | User can dismiss AI suggestions (dismissed suggestions don't re-appear) | New `issue_suggestion_dismissal` table (mirrors `DigestDismissal` pattern); `POST /workspaces/{id}/issues/{id}/related-suggestions/{target_id}/dismiss` |
</phase_requirements>

---

## Standard Stack

### Core (already in codebase — no new dependencies)

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| `KnowledgeGraphRepository` | existing | Hybrid pgvector + FTS search for ISSUE nodes | `hybrid_search(node_types=[NodeType.ISSUE])` |
| `IssueLink` + `IssueLinkType.RELATED` | existing | Persistent manual links between issues | Schema already has `RELATED` type |
| `IssueLinkRepository` | existing | CRUD for issue links | `find_all_for_issue` returns both directions |
| `WorkspaceScopedModel` | existing | Base for `IssueSuggestionDismissal` | RLS patterns from `DigestDismissal` |
| `EmbeddingService` | existing | Generate query embedding from issue text | Used in `KgPopulateHandler`; needed for suggestion query |
| pgvector `<=>` operator | existing | Cosine similarity in `hybrid_search_pg` | Already wired in `_graph_helpers.py` |

### New additions

| Component | Purpose |
|-----------|---------|
| Migration `072_add_issue_suggestion_dismissals` | New `issue_suggestion_dismissals` table |
| `IssueSuggestionDismissal` SQLAlchemy model | Persists dismissed AI suggestions per user+issue+target |
| `GET .../issues/{id}/related-suggestions` endpoint | Returns ranked similar issues with reason strings |
| `POST .../issues/{id}/relations` endpoint | Creates a `RELATED` IssueLink |
| `DELETE .../issues/{id}/relations/{link_id}` endpoint | Soft-deletes an IssueLink |
| `POST .../issues/{id}/related-suggestions/{target_id}/dismiss` | Creates dismissal row |

---

## Architecture Patterns

### Backend: New Endpoint File vs Extending Existing Router

The `workspace_issues.py` router is already 635+ lines. Following the file-size constraint:

- `POST` and `DELETE` for `/relations` go into `workspace_issues.py` if they fit; otherwise a new `workspace_issue_relations.py` router (mirror of `dependency_graph.py`)
- The `related-suggestions` and `dismiss` endpoints go into a new `workspace_issue_suggestions.py` router to keep concerns separated
- Both routers get mounted in `main.py`

**Recommendation:** One new router file `workspace_issue_suggestions.py` covering suggestions + dismissals.

### Semantic Similarity Query Pattern

```python
# Source: knowledge_graph_repository.py hybrid_search() + kg_populate_handler.py
# Step 1: get the ISSUE graph node for the given issue
issue_node = await kg_repo._find_node_by_external(
    workspace_id=workspace_id,
    node_type=NodeType.ISSUE,
    external_id=issue_id,
)

# Step 2: use node embedding as query vector, filter to ISSUE nodes only
scored_nodes = await kg_repo.hybrid_search(
    query_embedding=issue_node.embedding,   # list[float] | None
    query_text=issue_node.content,          # fallback for keyword search
    workspace_id=workspace_id,
    node_types=[NodeType.ISSUE],
    limit=10,
)

# Step 3: exclude self and already-linked issues
# Step 4: exclude dismissed issues (JOIN against issue_suggestion_dismissals)
# Step 5: enrich with reason: "same project", "shared note", or similarity score
```

### Reason Enrichment Logic

```
reason =
  if graph_edge(ISSUE_A -> ISSUE_B, edge_type=BELONGS_TO same project) → "same project"
  else if graph_edge via NOTE_CHUNK (RELATES_TO) → "shared note"
  else → f"Semantic match ({round(score * 100)}%)"
```

Use `KnowledgeGraphRepository.get_edges_between` on the result node IDs to check intra-result edges.

### Dismissal Table Pattern (mirrors DigestDismissal)

```python
class IssueSuggestionDismissal(WorkspaceScopedModel):
    __tablename__ = "issue_suggestion_dismissals"

    user_id: Mapped[UUID]         # FK → users.id CASCADE
    source_issue_id: Mapped[UUID] # issue that showed the suggestion
    target_issue_id: Mapped[UUID] # the suggested issue being dismissed
    dismissed_at: Mapped[datetime]
    # UniqueConstraint(user_id, source_issue_id, target_issue_id)
```

Query filter in suggestions endpoint:
```sql
-- Exclude dismissed: source_issue_id=:issue_id AND user_id=:user_id
```

### Frontend: Panel Component Pattern

The `IssuePropertiesPanel` right sidebar already shows `SourceNotesList`, `LinkedPRsList`. Add a `RelatedIssuesPanel` as a collapsible section below those, following the `CollapsibleSection` pattern visible in `collapsible-section.tsx`.

```
RelatedIssuesPanel (observer)
  ├── "AI Suggestions" section (useRelatedSuggestions query)
  │     each suggestion: IssueBriefCard + reason badge + dismiss button
  └── "Linked Issues" section (useIssueRelations query, filter type=RELATED)
        each link: IssueBriefCard + unlink button
        + "Link issue" search input (combobox using issue list)
```

### Recommended Project Structure (new files only)

```
backend/
├── alembic/versions/072_add_issue_suggestion_dismissals.py
├── src/pilot_space/
│   ├── infrastructure/database/models/issue_suggestion_dismissal.py
│   ├── infrastructure/database/repositories/issue_suggestion_dismissal_repository.py
│   └── api/v1/routers/workspace_issue_suggestions.py

frontend/src/features/issues/
├── components/related-issues-panel.tsx         # new panel component
├── hooks/use-related-suggestions.ts            # TanStack query hook
├── hooks/use-dismiss-suggestion.ts             # useMutation hook
└── components/__tests__/related-issues-panel.test.tsx
```

### Anti-Patterns to Avoid

- **Lazy-loading related issues in IssueResponse**: Do NOT add suggestions to the main issue GET response. Use a separate query that loads on demand.
- **N+1 issue fetch for suggestion enrichment**: Batch-fetch all issues by their `external_id` in one query after getting `ScoredNode` list.
- **Using graph search without embedding fallback**: If the ISSUE node has no embedding yet (just created), fall back to text-only search — `hybrid_search` already handles this.
- **Symmetric RELATED link confusion**: `IssueLink` is stored once (source→target). The `find_all_for_issue` already handles bidirectional display. On create, always store with lower UUID as source (or just store once and rely on bidirectional query).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic similarity | Custom cosine math | `KnowledgeGraphRepository.hybrid_search` | Already wired with pgvector + FTS fusion |
| Issue node lookup | Manual SQL | `find_node_by_external(workspace_id, NodeType.ISSUE, issue_id)` | Exists in `_graph_helpers.py` |
| RLS dismissal isolation | Manual WHERE clause | `WorkspaceScopedModel` + `set_rls_context()` | RLS policy auto-enforced at DB layer |
| Dismissal table | Re-using DigestDismissal with `suggestion_category` | New `issue_suggestion_dismissals` table | Cleaner schema; avoids category-string coupling |
| Issue search for manual link | Full-text search reimplementation | Existing `GET /workspaces/{id}/issues?search=` endpoint | Already supports `search` param |

---

## Common Pitfalls

### Pitfall 1: No graph node for newly-created issue
**What goes wrong:** Suggestion endpoint returns empty for a brand-new issue because `kg_populate` hasn't run yet.
**Why it happens:** Background job is async; new issues don't immediately have a graph node or embedding.
**How to avoid:** Return 200 with empty list (not 404). Document that suggestions appear after background job completes.
**Warning signs:** Suggestion endpoint 404s for new issues.

### Pitfall 2: Embedding is NULL even for existing issues
**What goes wrong:** `hybrid_search` falls back to keyword-only, returns low-quality results.
**Why it happens:** No OpenAI/Ollama key configured → `EmbeddingService` skips embedding generation.
**How to avoid:** Suggestions still work (text fallback). Surface `embedding_used: bool` in response so UI can show a notice. Already handled by `KnowledgeGraphRepository.hybrid_search`.

### Pitfall 3: Self-suggestion (issue returns itself)
**What goes wrong:** Similarity search returns the issue itself as top result.
**Why it happens:** Cosine similarity of a vector with itself = 1.0.
**How to avoid:** Explicitly filter `external_id != issue_id` in the suggestions query, OR filter out before returning results.

### Pitfall 4: Duplicate RELATED links
**What goes wrong:** User creates A→B link, then B→A link.
**Why it happens:** `UniqueConstraint(source, target, type)` allows (A,B,RELATED) and (B,A,RELATED) as two separate rows.
**How to avoid:** In the create endpoint, check `link_exists(source, target, RELATED) OR link_exists(target, source, RELATED)` before inserting. Return 409 if either exists. `IssueLinkRepository.link_exists()` already exists.

### Pitfall 5: Dismissals not scoped to user
**What goes wrong:** One user dismissing a suggestion affects all workspace members.
**Why it happens:** Forgetting `user_id` filter in the dismissal query.
**How to avoid:** Always filter dismissals by `user_id = current_user_id` AND `source_issue_id = issue_id`.

### Pitfall 6: IssueLink soft-delete vs hard-delete
**What goes wrong:** Deleted link resurfaces because `is_deleted` check is missing.
**Why it happens:** `IssueLinkRepository.find_all_for_issue` already filters `is_deleted == False` — but the base `delete()` from `BaseRepository` sets `is_deleted=True`. Don't use `session.delete()` directly.
**How to avoid:** Use `BaseRepository.soft_delete()` (or equivalent pattern) for link deletion.

### Pitfall 7: Missing `session: SessionDep` in new router
**What goes wrong:** `get_current_session()` raises `RuntimeError: No session in current context`.
**Why it happens:** Session ContextVar not populated (CLAUDE.md gotcha #1).
**How to avoid:** Every new route handler MUST declare `session: SessionDep` in signature.

### Pitfall 8: New file using `@inject` not in wiring_config
**What goes wrong:** DI injection silently uses default values.
**Why it happens:** `wiring_config.modules` in `container.py` is an explicit allowlist.
**How to avoid:** If new router file uses `@inject` + `Provide[Container.x]`, add its module path to `wiring_config.modules`. Prefer using `Annotated[T, Depends(...)]` deps from `repository_deps.py` instead.

---

## Code Examples

### Semantic Suggestion Query (backend pattern)

```python
# Source: knowledge_graph_repository.py + _graph_helpers.py
async def get_related_suggestions(
    issue_id: UUID,
    workspace_id: UUID,
    user_id: UUID,
    kg_repo: KnowledgeGraphRepository,
    dismissal_repo: IssueSuggestionDismissalRepository,
    limit: int = 8,
) -> list[RelatedSuggestion]:
    # 1. Find issue's graph node
    node = await kg_repo._find_node_by_external(
        workspace_id, NodeType.ISSUE, issue_id
    )
    if node is None:
        return []  # kg_populate not yet run

    # 2. Hybrid search for similar ISSUE nodes
    scored = await kg_repo.hybrid_search(
        query_embedding=node.embedding,
        query_text=node.content,
        workspace_id=workspace_id,
        node_types=[NodeType.ISSUE],
        limit=limit + 5,  # overfetch, then filter
    )

    # 3. Exclude self + dismissed
    dismissed_ids = await dismissal_repo.get_dismissed_target_ids(
        user_id=user_id, source_issue_id=issue_id
    )
    candidates = [
        sn for sn in scored
        if sn.node.external_id != issue_id
        and sn.node.external_id not in dismissed_ids
    ][:limit]

    # 4. Batch-fetch Issue models for identifier/name
    # 5. Enrich with reason string
    return [build_suggestion(sn, ...) for sn in candidates]
```

### Create RELATED Link (backend)

```python
# POST /workspaces/{workspace_id}/issues/{issue_id}/relations
# Mirrors existing list_issue_relations pattern
@router.post("/{workspace_id}/issues/{issue_id}/relations", ...)
async def create_issue_relation(
    session: SessionDep,
    workspace_id: WorkspaceIdOrSlug,
    issue_id: IssueIdPath,
    body: IssueLinkCreateRequest,  # target_issue_id: UUID, link_type: Literal["related"]
    current_user_id: SyncedUserId,
    workspace_repo: WorkspaceRepositoryDep,
    link_repo: IssueLinkRepositoryDep,
) -> IssueLinkSchema:
    workspace = await _resolve_workspace(workspace_id, workspace_repo)
    await set_rls_context(session, current_user_id, workspace.id)
    # Check duplicate
    if await link_repo.link_exists(issue_id, body.target_issue_id, IssueLinkType.RELATED, workspace.id):
        raise HTTPException(409, detail="Link already exists")
    link = IssueLink(
        workspace_id=workspace.id,
        source_issue_id=issue_id,
        target_issue_id=body.target_issue_id,
        link_type=IssueLinkType.RELATED,
    )
    session.add(link)
    await session.flush()
    ...
```

### Frontend TanStack Query Hook (new pattern)

```typescript
// Source: pattern from use-issue-relations.ts
export function useRelatedSuggestions(workspaceId: string, issueId: string) {
  return useQuery<RelatedSuggestion[]>({
    queryKey: ['issues', workspaceId, issueId, 'related-suggestions'],
    queryFn: () => issuesApi.getRelatedSuggestions(workspaceId, issueId),
    enabled: UUID_RE.test(workspaceId) && UUID_RE.test(issueId),
    staleTime: 60_000,  // suggestions don't change often
  });
}

export function useDismissSuggestion(workspaceId: string, issueId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetIssueId: string) =>
      issuesApi.dismissSuggestion(workspaceId, issueId, targetIssueId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['issues', workspaceId, issueId, 'related-suggestions'],
      });
    },
  });
}
```

### IssueLink Create/Delete API Client

```typescript
// Extends issuesApi in frontend/src/services/api/issues.ts
createRelation(workspaceId: string, issueId: string, targetIssueId: string): Promise<IssueRelation> {
  return apiClient.post(`/workspaces/${workspaceId}/issues/${issueId}/relations`, {
    target_issue_id: targetIssueId,
    link_type: 'related',
  });
},
deleteRelation(workspaceId: string, issueId: string, linkId: string): Promise<void> {
  return apiClient.delete(`/workspaces/${workspaceId}/issues/${issueId}/relations/${linkId}`);
},
getRelatedSuggestions(workspaceId: string, issueId: string): Promise<RelatedSuggestion[]> {
  return apiClient.get(`/workspaces/${workspaceId}/issues/${issueId}/related-suggestions`);
},
dismissSuggestion(workspaceId: string, issueId: string, targetIssueId: string): Promise<void> {
  return apiClient.post(
    `/workspaces/${workspaceId}/issues/${issueId}/related-suggestions/${targetIssueId}/dismiss`
  );
},
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Manual-only issue links | AI semantic suggestions + manual | Phase 15 adds the AI layer |
| `DigestDismissal` for suggestion suppression | New `IssueSuggestionDismissal` table | Same pattern, purpose-built table |
| `hybrid_search` used only in knowledge graph view | Re-used for related issue suggestions | Avoids duplicating pgvector logic |

**Already implemented (no Phase 15 work needed):**
- `IssueLink` model with `RELATED` type
- `GET .../relations` endpoint (list)
- `useIssueRelations` frontend hook
- Knowledge graph background job (populates ISSUE nodes)
- `hybrid_search` with pgvector cosine + FTS fusion

**Missing (Phase 15 must build):**
- `POST`/`DELETE` `.../relations` endpoints
- `GET .../related-suggestions` endpoint
- `issue_suggestion_dismissals` table + model + repository
- `POST .../related-suggestions/{target_id}/dismiss` endpoint
- Frontend `RelatedIssuesPanel` component
- Frontend hooks: `useRelatedSuggestions`, `useDismissSuggestion`, `useCreateRelation`, `useDeleteRelation`

---

## Open Questions

1. **Reason string enrichment performance**
   - What we know: `get_edges_between` is a single SELECT checking both endpoints in node_ids pool
   - What's unclear: How many edges exist between 8 suggested ISSUE nodes? Could be O(N²) edge check.
   - Recommendation: Call `get_edges_between(candidate_node_ids + [source_node_id])` once, scan in Python. Acceptable for N=8.

2. **IssueLink create — who is source vs target?**
   - What we know: `UniqueConstraint(source_id, target_id, link_type)` — order matters for dedup
   - What's unclear: Should A→B and B→A both be allowed for RELATED type?
   - Recommendation: Store only once. Check `link_exists(source, target)` OR `link_exists(target, source)` before insert. Return 409 on either. This matches the `find_all_for_issue` bidirectional query pattern.

3. **Dismissal scope: global or per-source-issue?**
   - What we know: RELISS-04 says "never re-appears for that issue" — scoped to the source issue
   - What's unclear: Should dismissing A from B's view also dismiss B from A's view?
   - Recommendation: Source-issue-scoped only. Column `source_issue_id` in dismissal table.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x (async) + vitest (frontend) |
| Config file | `backend/pyproject.toml` (pytest) + `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` |
| Quick run command (frontend) | `cd frontend && pnpm test -- related-issues` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RELISS-01 | GET related-suggestions returns scored ISSUE nodes | unit | `pytest tests/api/test_related_issues.py::test_get_suggestions_returns_scored_issues -x` | Wave 0 |
| RELISS-01 | Suggestions exclude self-issue | unit | `pytest tests/api/test_related_issues.py::test_suggestions_exclude_self -x` | Wave 0 |
| RELISS-02 | POST /relations creates RELATED IssueLink | unit | `pytest tests/api/test_related_issues.py::test_create_related_link -x` | Wave 0 |
| RELISS-02 | DELETE /relations/{id} soft-deletes link | unit | `pytest tests/api/test_related_issues.py::test_delete_related_link -x` | Wave 0 |
| RELISS-02 | POST /relations 409 on duplicate | unit | `pytest tests/api/test_related_issues.py::test_create_duplicate_link_returns_409 -x` | Wave 0 |
| RELISS-03 | Suggestion reason reflects shared note / same project / similarity | unit | `pytest tests/api/test_related_issues.py::test_suggestion_reason_enrichment -x` | Wave 0 |
| RELISS-04 | POST dismiss creates dismissal row | unit | `pytest tests/api/test_related_issues.py::test_dismiss_suggestion -x` | Wave 0 |
| RELISS-04 | Dismissed suggestion absent from subsequent GET | unit | `pytest tests/api/test_related_issues.py::test_dismissed_not_returned -x` | Wave 0 |
| RELISS-01 | RelatedIssuesPanel renders AI suggestions | unit | `cd frontend && pnpm test -- related-issues-panel` | Wave 0 |
| RELISS-04 | Dismiss button calls mutation and invalidates query | unit | `cd frontend && pnpm test -- related-issues-panel` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/api/test_related_issues.py -x -q`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/api/test_related_issues.py` — covers RELISS-01, RELISS-02, RELISS-03, RELISS-04 (xfail stubs)
- [ ] `frontend/src/features/issues/components/__tests__/related-issues-panel.test.tsx` — covers frontend RELISS-01, RELISS-04
- [ ] `backend/src/pilot_space/infrastructure/database/models/issue_suggestion_dismissal.py` — new model
- [ ] `backend/src/pilot_space/infrastructure/database/repositories/issue_suggestion_dismissal_repository.py` — new repo
- [ ] `backend/alembic/versions/072_add_issue_suggestion_dismissals.py` — new migration

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection — `backend/src/pilot_space/infrastructure/database/models/issue_link.py` (IssueLink model + IssueLinkType.RELATED confirmed)
- Codebase inspection — `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py` (hybrid_search, find_node_by_external)
- Codebase inspection — `backend/src/pilot_space/domain/graph_node.py` (NodeType.ISSUE, GraphNode)
- Codebase inspection — `backend/src/pilot_space/domain/graph_edge.py` (EdgeType: RELATES_TO, BELONGS_TO, PARENT_OF)
- Codebase inspection — `backend/src/pilot_space/api/v1/routers/workspace_issues.py` (existing /relations GET; line count = ~635)
- Codebase inspection — `backend/src/pilot_space/infrastructure/database/models/digest_dismissal.py` (dismissal pattern)
- Codebase inspection — `backend/src/pilot_space/container/_base.py` (issue_link_repository and knowledge_graph_repository both registered as Factory providers)
- Codebase inspection — `backend/src/pilot_space/api/v1/repository_deps.py` (IssueLinkRepositoryDep already exists)
- Codebase inspection — `frontend/src/features/issues/hooks/use-issue-relations.ts` (useIssueRelations hook exists)
- Codebase inspection — `frontend/src/services/api/issues.ts` (getRelations exists; createRelation/deleteRelation missing)
- Codebase inspection — `backend/alembic/versions/` (latest migration is 071; next is 072)

### Secondary (MEDIUM confidence)

- Codebase inspection — `backend/src/pilot_space/infrastructure/queue/handlers/kg_populate_handler.py` (KG is populated for issues; `_SIMILARITY_THRESHOLD = 0.75` shows similarity scoring is already active)
- Codebase inspection — `backend/tests/api/test_workspace_mcp_servers.py` (xfail Wave 0 stub pattern confirmed for Phase 14)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all foundational models, repositories, and hooks verified by direct code inspection
- Architecture: HIGH — patterns confirmed by examining 4 analogous implementations (DigestDismissal, IssueLinkRepository, knowledge_graph router, MCP server Phase 14)
- Pitfalls: HIGH — identified from known gotchas in CLAUDE.md + direct code inspection of edge cases (self-loop, duplicate link constraint, missing session dep)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain; fast-moving items: migration numbering — always verify with `alembic heads` before creating 072)
