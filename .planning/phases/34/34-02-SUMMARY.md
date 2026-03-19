---
phase: 34-mcp-observability
plan: 02
subsystem: ui
tags: [react, recharts, tanstack-query, mobx, mcp, dashboard]

# Dependency graph
requires:
  - phase: 34-01
    provides: GET /api/v1/ai/mcp-usage endpoint returning McpToolUsageResponse
provides:
  - getMcpToolUsage() method on aiApi with McpToolUsageEntry, McpServerSummary, McpToolUsageResponse types
  - MCP Tools tab in CostDashboardPage with lazy useQuery and horizontal BarChart
affects: [34-mcp-observability, costs-dashboard, ai-observability]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy tab query: useQuery with enabled: activeTab === 'by_mcp' to avoid fetching until tab clicked"
    - "X-Workspace-Id header pattern for workspace-scoped API calls (matches existing getCostSummary)"

key-files:
  created: []
  modified:
    - frontend/src/services/api/ai.ts
    - frontend/src/features/costs/pages/cost-dashboard-page.tsx

key-decisions:
  - "Used McpToolUsageEntry.server_name (not server_key) as chart label so display names show instead of raw UUIDs"
  - "Label format 'server_name: tool_name' for chart Y-axis to distinguish tools across servers"
  - "Wider YAxis width (156px vs 116px for features) to accommodate server+tool label format"

patterns-established:
  - "Lazy tab query: useQuery enabled flag tied to activeTab state prevents network calls until user clicks tab"

requirements-completed: [MCPOB-02]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 34 Plan 02: MCP Tools Usage Tab Summary

**MCP Tools tab added to AI Cost Dashboard — lazy-loaded horizontal BarChart showing per-tool invocation counts from GET /ai/mcp-usage, with empty state and server-resolved display names**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T21:56:33Z
- **Completed:** 2026-03-19T21:58:31Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `McpToolUsageEntry`, `McpServerSummary`, `McpToolUsageResponse` types to ai.ts
- Added `getMcpToolUsage()` to aiApi using the established `X-Workspace-Id` header pattern
- Extended CostDashboardPage with a third tab "MCP Tools" using the same lazy-query pattern as "By Feature"
- Horizontal BarChart displays invocation counts (integers, not USD), with empty state and FEATURE_COLORS palette

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: Add getMcpToolUsage + MCP Tools tab** - `c3f01df7` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/services/api/ai.ts` - Added 3 MCP types + getMcpToolUsage() method
- `frontend/src/features/costs/pages/cost-dashboard-page.tsx` - Added by_mcp tab with lazy query, BarChart, empty state

## Decisions Made
- Combined Tasks 1 and 2 into one commit since they are tightly coupled (the dashboard change imports the types added in task 1)
- Used `server_name: tool_name` compound label for chart Y-axis to identify tools across multiple servers unambiguously
- Left YAxis width at 156px (wider than the 116px used for feature names) to accommodate compound labels

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Prettier reformatted `cost-dashboard-page.tsx` on first commit attempt (pre-commit hook). Re-staged and committed successfully on second attempt — standard hook behavior, not a code issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- MCP observability frontend is complete (MCPOB-02 done)
- Backend endpoint (MCPOB-01, Plan 34-01) provides the data; this tab surfaces it to workspace admins
- No blockers

## Self-Check: PASSED

- `frontend/src/services/api/ai.ts` — FOUND
- `frontend/src/features/costs/pages/cost-dashboard-page.tsx` — FOUND
- Commit `c3f01df7` — FOUND

---
*Phase: 34-mcp-observability*
*Completed: 2026-03-19*
