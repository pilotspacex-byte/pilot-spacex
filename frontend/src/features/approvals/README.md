# Approvals Module - Human-in-the-Loop

_For project overview, see main `README.md` and `frontend/README.md`_

## Purpose

Human-in-the-loop workflow for AI-generated actions requiring oversight (DD-003). UI for reviewing, approving, and rejecting AI actions with 24-hour expiration.

---

## Approval Classification (DD-003)

| Category         | Examples                    | Approval Required  | Impact                  |
| ---------------- | --------------------------- | ------------------ | ----------------------- |
| Non-Destructive  | Auto-label, transition      | No (auto-execute)  | Low-risk, reversible    |
| Content Creation | Extract issues, PR comments | Yes (configurable) | Medium-risk             |
| Destructive      | Delete issue, merge PR      | Always             | High-risk, irreversible |

---

## Module Structure

```
frontend/src/features/approvals/
├── pages/
│   ├── approval-queue-page.tsx    # 5-tab filter (Pending/Approved/Rejected/Expired/All)
│   └── index.ts
├── components/
│   ├── approval-card.tsx          # Card view (default) with quick actions
│   ├── approval-list-item.tsx     # Compact list view
│   ├── approval-detail-modal.tsx  # Full detail with risk assessment
│   └── index.ts
└── __tests__/
```

---

## Components

**ApprovalQueuePage**: 5-tab filter, pending count badge, empty states, modal detail view. Uses ApprovalStore.

**ApprovalCard**: Status/action badges, context preview (2 lines), metadata (agent, requester, created), expiration countdown, quick Approve/Reject buttons (pending only).

**ApprovalDetailModal**: Header with status, metadata grid, RiskAssessment (color-coded), PayloadPreview (JSON + copy), optional note textarea (1000 char), "Approve & Execute" + "Reject" buttons, expiration warning.

---

## State Management

**Store**: `stores/ai/ApprovalStore.ts`

**Observable**: requests, pendingCount, isLoading, error, selectedRequest, filter.

**Actions**: `loadPending()`, `loadAll(status?)`, `approve(id, note?, selectedIssues?)`, `reject(id, note?)`, `selectRequest(request)`, `setFilter(filter)`.

---

## 24-Hour Expiration

Each approval has `expires_at` (24h from creation). UI shows countdown via `formatDistanceToNow(expiresAt)`. When expired: red text, destructive alert, Approve/Reject buttons hidden, status set to 'expired' server-side.

**Quick Actions** (on card): Direct approve/reject, no confirmation, for simple actions.
**Detail Modal**: Full context, payload, risk assessment, optional note, for complex/destructive actions.

---

## API Endpoints

```
GET  /api/v1/ai/approvals?status=pending|approved|rejected|expired
POST /api/v1/ai/approvals/{id}/resolve  { approved: bool, note?, selected_issues? }
```

**Types**: See `types/` for `ApprovalRequest` and `ApprovalResolutionRequest` interfaces.

---

## Integration Points

**Upstream**: Router (`/[workspaceSlug]/approvals/`), sidebar badge (`approval.pendingCount`), PilotSpaceStore (`approval_request` SSE event).

**Downstream**: `aiApi` (listApprovals, resolveApproval), ApprovalStore, shadcn/ui (Dialog, Button, Badge, Tabs).

---

## Related Documentation

- **DD-003**: Critical-only AI approval
- **DD-086**: Centralized PilotSpaceAgent
- `docs/architect/pilotspace-agent-architecture.md`
