# Cost Dashboard Module

_For project overview, see main `CLAUDE.md` and `frontend/CLAUDE.md`_

## Purpose

Track and visualize AI costs across workspace with provider routing insights (DD-011). Displays cost breakdowns by agent, user, and time period for workspace admins.

**Design Decisions**: DD-002 (BYOK), DD-011 (provider routing), DD-065 (state split)

---

## File Structure

```
frontend/src/features/costs/
├── index.ts
├── pages/
│   └── cost-dashboard-page.tsx
└── components/
    ├── cost-summary-card.tsx       # Metric with trend indicator
    ├── cost-trends-chart.tsx       # Recharts AreaChart (daily costs)
    ├── cost-by-agent-chart.tsx     # Recharts PieChart (donut, agent distribution)
    ├── cost-table-view.tsx         # Sortable user cost table
    └── date-range-selector.tsx     # Preset date ranges (7/30/90 days)
```

---

## Components

| Component         | Purpose            | Key Features                                                  |
| ----------------- | ------------------ | ------------------------------------------------------------- |
| CostDashboardPage | Orchestrator       | Loads summary, date range control, 4 cards + 2 charts + table |
| CostSummaryCard   | Single metric      | Trend % change, arrow indicator (red/green)                   |
| CostTrendsChart   | Daily costs        | Recharts AreaChart, gradient fill, custom tooltip             |
| CostByAgentChart  | Agent distribution | Interactive donut, click-to-filter, custom legend             |
| CostTableView     | User breakdown     | Sortable by name/cost/requests, avatar + initials             |
| DateRangeSelector | Date presets       | Today, 7/30/90 days (default: 30), this month                 |

---

## Provider Routing (DD-011)

| Agent                 | Provider  | Model         | Cost Tier |
| --------------------- | --------- | ------------- | --------- |
| `pilot_space_agent`   | Anthropic | Claude Opus   | Highest   |
| `ghost_text_agent`    | Google    | Gemini Flash  | Low       |
| `pr_review_agent`     | Anthropic | Claude Opus   | Highest   |
| `ai_context_agent`    | Anthropic | Claude Sonnet | Medium    |
| `doc_generator_agent` | Anthropic | Claude Sonnet | Medium    |

---

## Data Model

**Endpoint**: `GET /workspaces/{workspace_id}/ai/costs/summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

**Response**: `{ total_cost_usd, total_requests, by_agent: [{agent_name, total_cost_usd, request_count}], by_user: [{user_id, user_name, total_cost_usd, request_count}], by_day: [{date, total_cost_usd, request_count}] }`

**Token Types**: Input (prompt + context), Output (AI response), Cached (reused, 90% discount).

---

## State Management

**Store**: `stores/ai/CostStore.ts`

**Observable**: summary, isLoading, error, dateRange (default: last 30 days).

**Computed**: totalCost, totalRequests, totalTokens, avgCostPerRequest, costByAgent, costTrends, costPerUser.

**Actions**: `loadSummary(workspaceId)`, `setDateRange(range, workspaceId)`, `setPresetRange(preset, workspaceId)`.

---

## Related Documentation

- `docs/architect/frontend-architecture.md`
- `docs/dev-pattern/21c-frontend-mobx-state.md`
