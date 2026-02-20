# Cycles Module - Sprint Management

_For project overview, see main `README.md` and `frontend/README.md`_

## Purpose

Sprint/cycle management with CRUD, burndown charts, velocity tracking, and state-cycle constraint enforcement.

---

## Module Structure

```
frontend/src/features/cycles/
├── pages/
│   └── cycle-detail-page.tsx     # Cycle detail, charts, issue list
├── components/
│   ├── cycle-selector.tsx        # Dropdown for cycle assignment
│   ├── burndown-chart.tsx        # Sprint burndown visualization
│   ├── velocity-chart.tsx        # Team velocity trends
│   ├── cycle-status-badge.tsx    # Active/completed/draft state
│   └── issue-cycle-list.tsx      # Issues in cycle with filters
├── hooks/
│   ├── useCycle.ts, useCycles.ts
│   ├── useCreateCycle.ts, useUpdateCycle.ts
│   ├── useCycleBurndown.ts, useVelocity.ts
└── __tests__/
```

---

## State-Cycle Constraints

| State       | Cycle Requirement  | Notes                             |
| ----------- | ------------------ | --------------------------------- |
| Backlog     | No cycle           | Unscheduled                       |
| Todo        | Optional           | Any cycle                         |
| In Progress | Required (active)  | CycleSelector disables non-active |
| In Review   | Required (active)  | Must remain in active cycle       |
| Done        | Leaves cycle       | Archived with metrics             |
| Cancelled   | Leaves immediately | No archival                       |

Enforced at backend (RLS) + frontend (CycleSelector disables invalid options). See `components/cycle-selector.tsx`.

---

## Key Features

**Burndown Chart**: X=days in cycle, Y=remaining story points. Ideal line (linear to 0) + actual line. See `components/burndown-chart.tsx`.

**Velocity Chart**: X=cycle name, Y=points. Green=completed, gray=cancelled. Last 5 cycles. See `components/velocity-chart.tsx`.

**Cycle Selector**: Active cycle (bold), upcoming, backlog. Past cycles grayed out. Validates state-cycle constraints.

---

## Hooks

| Hook                        | Purpose                  | Stale Time |
| --------------------------- | ------------------------ | ---------- |
| `useCycle(cycleId)`         | Single cycle + relations | 30s        |
| `useCycles()`               | List cycles              | 60s        |
| `useCreateCycle()`          | Create mutation          | --         |
| `useUpdateCycle()`          | Update mutation          | --         |
| `useCycleBurndown(cycleId)` | Burndown metrics         | 5m         |
| `useVelocity(workspaceId)`  | Last 5 cycles velocity   | 5m         |

---

## Related Documentation

- State-Cycle Constraints: Key entities section in main README.md
- **DD-065**: MobX + TanStack Query
- `docs/dev-pattern/45-pilot-space-patterns.md`
