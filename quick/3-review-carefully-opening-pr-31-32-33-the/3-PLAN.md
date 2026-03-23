---
phase: quick-3
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  # PR 33 (feat/improve-issues-ui)
  - frontend/src/features/issues/components/property-chip.tsx
  - frontend/src/features/issues/components/issue-editor-content.tsx
  # PR 32 (feat/v1.0.0-alpha-2) — current branch
  - backend/src/pilot_space/application/services/note/move_page_service.py
  - backend/src/pilot_space/api/v1/routers/workspace_notes.py
  - backend/src/pilot_space/application/services/note/update_note_service.py
  - backend/tests/unit/services/conftest.py
  - frontend/src/features/notes/hooks/useProjectPageTree.ts
  # PR 31 (feat/project-graph-knowledge)
  - backend/src/pilot_space/api/v1/routers/knowledge_graph.py
  - backend/src/pilot_space/application/services/memory/knowledge_graph_query_service.py
  - frontend/src/features/projects/components/project-knowledge-graph.tsx
autonomous: true
must_haves:
  truths:
    - "Self-parenting is rejected with a clear error on move_page"
    - "icon_emoji is serialized in all note response helpers"
    - "All new note endpoints return RFC 7807 problem+json errors"
    - "Knowledge graph 404s return RFC 7807 format"
    - "GitHub nodes are deduplicated and max_nodes enforced after synthesis"
    - "All 3 PRs are merged to main"
  artifacts:
    - path: "backend/src/pilot_space/application/services/note/move_page_service.py"
      provides: "Self-parenting guard + tail-slot FOR UPDATE"
    - path: "backend/src/pilot_space/api/v1/routers/workspace_notes.py"
      provides: "icon_emoji serialization + problem+json errors"
    - path: "backend/src/pilot_space/application/services/memory/knowledge_graph_query_service.py"
      provides: "GitHub node dedup + max_nodes enforcement"
  key_links:
    - from: "move_page_service.py"
      to: "self-parenting guard"
      via: "ValueError if new_parent_id == note.id"
      pattern: "new_parent_id.*==.*note\\.id"
---

<objective>
Fix all Critical and Major CodeRabbit review issues across PRs 31, 32, and 33, then merge all three to main.

Purpose: Clear the review backlog so the three approved PRs can ship cleanly.
Output: All fixes committed to respective branches, all 3 PRs merged to main.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix PR 33 nitpicks + PR 31 Major issues (two feature branches)</name>
  <files>
    frontend/src/features/issues/components/property-chip.tsx
    frontend/src/features/issues/components/issue-editor-content.tsx
    backend/src/pilot_space/api/v1/routers/knowledge_graph.py
    backend/src/pilot_space/application/services/memory/knowledge_graph_query_service.py
    frontend/src/features/projects/components/project-knowledge-graph.tsx
  </files>
  <action>
**PR 33 — branch: `feat/improve-issues-ui`**

Switch to `feat/improve-issues-ui` branch and fix 2 nitpicks:

1. **property-chip.tsx** — Remove redundant `role="button"` attribute from native `<button>` elements. Native buttons already have implicit button role.

2. **issue-editor-content.tsx** — Extract the inline noop `() => {}` fallback for `onUpdate` into a module-level constant:
   ```ts
   const NOOP = () => {};
   ```
   Use `NOOP` wherever the inline noop appears. This avoids creating new function references on every render.

Run quality gate: `cd frontend && pnpm lint && pnpm type-check && pnpm test`

Commit to `feat/improve-issues-ui`, push.

---

**PR 31 — branch: `feat/project-graph-knowledge`**

Switch to `feat/project-graph-knowledge` branch and fix 5 Major issues:

1. **knowledge_graph.py** — Replace all `HTTPException(status_code=404, ...)` with RFC 7807 problem+json responses. Use the project's existing error response pattern (check how other routers do 404 — likely `raise_http_error` or return `ProblemDetail`). Check `backend/src/pilot_space/api/v1/routers/` for the pattern used by other routers (e.g., workspace_notes.py, projects.py). Match that pattern exactly.

2. **knowledge_graph_query_service.py** — Fix GitHub node synthesis issues:
   - **Deduplication**: After synthesizing GitHub nodes from linked PRs, deduplicate by `external_url` (or `pr_number + repo`) before adding to the graph. Use a `seen_urls: set` to track.
   - **node_types filtering**: If `node_types` filter is provided, only include GitHub nodes if "GITHUB_PR" (or equivalent) is in the filter. Also ensure the center_node is never filtered out (always include it regardless of `node_types`).
   - **max_nodes enforcement**: After GitHub node synthesis, enforce `max_nodes` cap on the total result (nodes + github_nodes). Truncate overflow nodes (not the center node).

3. **project-knowledge-graph.tsx** — Cap the `expandedNodes` accumulation. When expanding a node fetches neighbors, check total node count. If adding new nodes would exceed 200, show a toast/warning and skip the expansion. Guard: `if (currentNodes.size + newNodes.length > 200) { /* warn and skip */ }`.

Run quality gates for both backend and frontend:
- `cd backend && uv run ruff check src/pilot_space/api/v1/routers/knowledge_graph.py src/pilot_space/application/services/memory/knowledge_graph_query_service.py && uv run pyright`
- `cd frontend && pnpm lint && pnpm type-check && pnpm test`

Commit to `feat/project-graph-knowledge`, push.
  </action>
  <verify>
    <automated>cd frontend && pnpm type-check && pnpm test</automated>
  </verify>
  <done>PR 33 has no CodeRabbit findings. PR 31 has all 5 Major issues resolved. Both branches pushed.</done>
</task>

<task type="auto">
  <name>Task 2: Fix PR 32 Critical + Major issues (current branch)</name>
  <files>
    backend/src/pilot_space/application/services/note/move_page_service.py
    backend/src/pilot_space/api/v1/routers/workspace_notes.py
    backend/src/pilot_space/application/services/note/update_note_service.py
    backend/tests/unit/services/conftest.py
    frontend/src/features/notes/hooks/useProjectPageTree.ts
  </files>
  <action>
Switch back to `feat/v1.0.0-alpha-2` (current branch).

Fix 7 issues (1 Critical, 6 Major):

1. **CRITICAL: Self-parenting guard** in `move_page_service.py` — Add check BEFORE the descendant check (around line 127):
   ```python
   # Guard: cannot move a page to itself
   if payload.new_parent_id is not None and payload.new_parent_id == note.id:
       msg = "Cannot move a page to itself (would create a self-referential cycle)"
       raise ValueError(msg)
   ```
   Add a unit test for this case in the appropriate test file.

2. **Major: icon_emoji write-only** in `workspace_notes.py` — Find `_note_to_response`, `_note_to_detail_response`, and `_note_to_tree_response` helper functions. Add `icon_emoji=note.icon_emoji` (or equivalent field name) to the response dict/model in each. Check the response schema/model to find the correct field name.

3. **Major: Tail-slot race condition** in `move_page_service.py` — The `_compute_tail_position` method already uses `for_update=True` on `get_siblings`. Verify this is actually passing through to the query as `SELECT ... FOR UPDATE`. If `get_siblings` in the repository does NOT support `for_update`, add `with_for_update()` to the query. If it already does, document with a comment that this is intentional for concurrency safety.

4. **Major: SQLite test conftest missing icon_emoji** in `tests/unit/services/conftest.py` — Find the raw DDL `CREATE TABLE` for notes and add the `icon_emoji` column (TEXT, nullable). Match the column type from the SQLAlchemy model.

5. **Major: Project tree fetch capped at 100** in `useProjectPageTree.ts` — Find the `limit: 100` or similar param and increase to `500` or remove the limit entirely (paginate on scroll if needed). Add a comment explaining the cap choice.

6. **Major: DragEnd parentId comparison** — Check if the actual code in `frontend/src/components/layout/DraggableTreeNode.tsx` or similar has the bug described (comparing parentId incorrectly). If the bug is ONLY in the planning doc and not in actual code, skip. If in code, fix the comparison.

7. **Major: problem+json for new note endpoints** in `workspace_notes.py` — Check that error responses in new note endpoints (create, move, reorder, etc.) use the RFC 7807 pattern. Convert any bare `HTTPException` to the project's standard error response format.

8. **Major: UpdateNotePayload icon_emoji handling** in `update_note_service.py` — Ensure `icon_emoji` from the update payload is actually written to the note model. Check if the service copies `icon_emoji` from payload to the note entity. If missing, add `note.icon_emoji = payload.icon_emoji` (with appropriate None/sentinel handling for "clear emoji" vs "don't change").

Run quality gates:
- `cd backend && uv run ruff check --fix && uv run pyright && uv run pytest`
- `cd frontend && pnpm lint && pnpm type-check && pnpm test`

Commit to `feat/v1.0.0-alpha-2`, push.
  </action>
  <verify>
    <automated>cd backend && uv run ruff check && uv run pyright && cd ../frontend && pnpm type-check && pnpm test</automated>
  </verify>
  <done>All 7 PR 32 issues fixed. Self-parenting rejected with test. icon_emoji serialized. Error responses use RFC 7807. Branch pushed.</done>
</task>

<task type="auto">
  <name>Task 3: Merge all 3 PRs to main</name>
  <files></files>
  <action>
Merge PRs in order (cleanest first to minimize conflicts):

1. **PR 33** (feat/improve-issues-ui):
   ```bash
   gh pr merge 33 --squash --delete-branch
   ```

2. **PR 31** (feat/project-graph-knowledge):
   ```bash
   gh pr merge 31 --squash --delete-branch
   ```

3. **PR 32** (feat/v1.0.0-alpha-2):
   This is the largest PR. Before merging, rebase on main to pick up the merged PR 33 and 31:
   ```bash
   git checkout feat/v1.0.0-alpha-2
   git fetch origin main
   git rebase origin/main
   # Resolve any conflicts
   git push --force-with-lease
   gh pr merge 32 --squash --delete-branch
   ```

If any merge has conflicts, resolve them and push before proceeding to the next.

After all merges, verify main is clean:
```bash
git checkout main
git pull
```
  </action>
  <verify>
    <automated>gh pr view 31 --json state -q '.state' && gh pr view 32 --json state -q '.state' && gh pr view 33 --json state -q '.state'</automated>
  </verify>
  <done>All 3 PRs show state "MERGED". Main branch has all changes.</done>
</task>

</tasks>

<verification>
- `gh pr view 31 --json state` returns MERGED
- `gh pr view 32 --json state` returns MERGED
- `gh pr view 33 --json state` returns MERGED
- `git log main --oneline -5` shows the 3 squash merge commits
</verification>

<success_criteria>
- All Critical and Major CodeRabbit issues fixed across 3 PRs
- Quality gates pass on all 3 branches before merge
- All 3 PRs merged to main via squash merge
- No regressions in existing tests
</success_criteria>

<output>
After completion, update `.planning/STATE.md` with quick task 3 completion.
</output>
