---
phase: quick-project-knowledge
plan: "01"
subsystem: knowledge-graph
tags: [knowledge-graph, project, reactflow, fastapi, tanstack-query]
dependency_graph:
  requires: []
  provides: [project-knowledge-graph-endpoint, project-knowledge-tab]
  affects: [ProjectSidebar, knowledge_graph_router]
tech_stack:
  added: []
  patterns:
    - ReactFlow project-scoped graph (reusing issue graph utilities)
    - Project KG endpoint mirroring issue KG endpoint pattern
key_files:
  created:
    - backend/src/pilot_space/api/v1/routers/knowledge_graph.py (projects_kg_router added)
    - backend/tests/unit/api/test_knowledge_graph_project.py
    - frontend/src/features/projects/hooks/useProjectKnowledgeGraph.ts
    - frontend/src/features/projects/components/project-knowledge-graph.tsx
    - frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/knowledge/page.tsx
  modified:
    - backend/src/pilot_space/api/v1/routers/__init__.py
    - backend/src/pilot_space/main.py
    - frontend/src/services/api/knowledge-graph.ts
    - frontend/src/components/projects/ProjectSidebar.tsx
    - frontend/src/features/projects/hooks/index.ts
decisions:
  - Reused all issue graph utilities (computeForceLayout, nodeTypes, GraphEmptyState) without duplication
  - GitHub synthesis queries integration_links for all project issues via subquery (not just one issue)
  - maxNodes default is 100 for projects (vs 50 for issues) since projects have broader scope
  - Knowledge nav item placed between Cycles and Chat using Brain icon from lucide-react
metrics:
  duration: "~20 minutes"
  completed: "2026-03-12"
  tasks_completed: 2
  files_changed: 10
---

# Quick Task 1: Project Knowledge Tab Summary

**One-liner:** Project-scoped knowledge graph tab with ReactFlow visualization via GET /workspaces/{wid}/projects/{pid}/knowledge-graph endpoint.

## What Was Built

Added a "Knowledge" tab to the project detail sidebar that displays an interactive graph visualization of a project's knowledge graph — showing connected issues, notes, cycles, PRs, commits, branches, code references, and other entities.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Backend project-scoped KG endpoint + API client method | 543d353d |
| 2 | Frontend Knowledge tab — hook, component, route, sidebar | 78cfd3c3 |

## Task 1: Backend + API Client

**Endpoint:** `GET /api/v1/workspaces/{workspace_id}/projects/{project_id}/knowledge-graph`

- Added `projects_kg_router` to `knowledge_graph.py` mirroring the `issues_kg_router` pattern
- Project existence check returns 404 if project not found or deleted
- Finds PROJECT graph node by `external_id == project_id`
- Returns empty `GraphResponse` with `center_node_id=project_id` if no graph node exists
- `include_github=true` synthesizes ephemeral PR/branch/commit nodes from all project issues' `integration_links` via subquery
- Node type filter and importance tier sorting (same as issue endpoint)
- `max_nodes` accepts up to 200 (vs 100 for issues) to accommodate larger project graphs
- Registered in `routers/__init__.py` and mounted in `main.py`
- 11 unit tests covering 404, empty response, success, GitHub synthesis, filter, sort, and RLS

**Frontend API client:** Added `getProjectGraph` method to `knowledgeGraphApi` in `knowledge-graph.ts`

## Task 2: Frontend Components

**Hook** (`useProjectKnowledgeGraph.ts`):
- Follows exact `use-issue-knowledge-graph.ts` pattern
- `projectKnowledgeGraphKeys` key factory with `all`, `project`, `projectWithOptions`
- `staleTime: 30_000`, `maxNodes: 100` defaults

**Component** (`project-knowledge-graph.tsx`):
- Self-contained full-page graph, no `observer()`, no MobX
- Filter chips: Issues, Notes, Cycles, PRs, Commits, Code, All
- Depth slider (1-3, default 2)
- Node count display in toolbar
- `ReactFlowProvider` wrapping, `ErrorBoundary` on canvas
- Node click shows detail panel (nodeType badge, label, summary, timestamp)
- Node double-click expands neighbors via `getNodeNeighbors` (cap at 200 nodes with toast)
- `startTransition` for layout computation to avoid blocking
- Wider layout params: `width: 1000, height: 600, linkDistance: 100, chargeStrength: -150`
- Reuses `computeForceLayout`, `nodeTypes`, `GraphEmptyState` from issues feature

**Route** (`/projects/{projectId}/knowledge/page.tsx`):
- `'use client'` page using `useProject` for project data
- Loading skeleton, error/not-found state
- Header with "Knowledge Graph" title and project name
- `ProjectKnowledgeGraph` fills remaining height

**Sidebar** (`ProjectSidebar.tsx`):
- Added `Brain` icon from `lucide-react`
- `{ label: 'Knowledge', icon: Brain, segment: 'knowledge' }` inserted after Cycles

## Deviations from Plan

None — plan executed exactly as written.

## Verification

All quality gates passed:

- Backend tests: `pytest tests/unit/api/test_knowledge_graph_project.py` — 11/11 passed
- Frontend type-check: `pnpm type-check` — 0 errors
- Frontend lint: `pnpm lint` — 0 errors (22 pre-existing warnings, unrelated to this plan)

## Self-Check: PASSED

Files exist:
- `backend/tests/unit/api/test_knowledge_graph_project.py` — FOUND
- `frontend/src/features/projects/hooks/useProjectKnowledgeGraph.ts` — FOUND
- `frontend/src/features/projects/components/project-knowledge-graph.tsx` — FOUND
- `frontend/src/app/(workspace)/[workspaceSlug]/projects/[projectId]/knowledge/page.tsx` — FOUND

Commits exist:
- `543d353d` — FOUND (feat: project-scoped KG endpoint)
- `78cfd3c3` — FOUND (feat: Knowledge tab)
