# ChatView: ApprovalOverlay System

> **Location**: `frontend/src/features/ai/ChatView/ApprovalOverlay/`
> **Design Decision**: DD-003 (Critical-Only AI Approval / Human-in-the-Loop)

## Overview

The ApprovalOverlay system implements **DD-003 human-in-the-loop control**: every destructive or significant AI action requires explicit human approval before execution. It renders rich previews of what the AI intends to do, giving users the context needed to make an informed decision (approve or reject), and propagates the decision back to the backend via REST so the agent can proceed.

**Core principle**: AI cannot take consequential action without user consent. The user is always the final authority.

---

## 3-Tier Approval Classification

| Tier | Condition | UI | Auto-execute? |
|------|-----------|----|---------------|
| **CRITICAL** | Destructive actions (delete, merge, archive) | `DestructiveApprovalModal` — blocking, 5-min timer | Never |
| **DEFAULT** | Content creation/update (create issue, update note) | `InlineApprovalCard` — non-blocking, 24h expiration | Configurable per workspace |
| **AUTO** | AI suggestions (priority, labels, assignee) | No UI | Always auto-execute |

**Destructive action set** (routing to modal):
```
delete_issue, merge_pr, close_issue, archive_workspace,
delete_note, delete_comment, delete_project, force_close_cycle
```

All others route to inline cards.

---

## Architecture

```
ChatView (approval routing)
├── DestructiveApprovalModal    ← blocking modal for CRITICAL actions
│   ├── ContentDiff             ← before/after text comparison
│   ├── IssuePreview            ← issue creation preview
│   ├── IssueUpdatePreview      ← issue field change preview
│   └── GenericJSON             ← fallback for unknown action types
│
└── MessageList
    ├── InlineApprovalCard      ← non-blocking inline card (DEFAULT tier)
    └── SkillApprovalCard       ← skill-level approval with artifacts
```

**Batch operation**:
```
ConfirmAllButton  ←  intents only (NOT critical actions), confidence ≥ 70%
```

---

## Components

### `DestructiveApprovalModal.tsx`

**Responsibility**: Blocking modal for irreversible AI actions.

**Behavior**:
- **Non-dismissable**: No click-outside-to-close, no X button. User _must_ approve or reject.
- **5-minute auto-reject countdown**: If user takes no action in 5 minutes, request is auto-rejected (safety-first).
- **Reject button focused by default**: Focus is on the safer action to prevent accidental approvals.
- **Escape key = Reject**: Dismissal gesture maps to rejection, not approval.

**Countdown color thresholds**:
- `> 5 minutes` (countdown paused or long): gray text
- `1–5 minutes`: amber text
- `< 1 minute`: red text, pulsing animation

**Payload preview** (decision tree):
```
action_type === 'delete_issue'    → IssuePreview (shows what will be deleted)
action_type === 'update_note'     → ContentDiff (shows before/after text)
action_type === 'update_issue'    → IssueUpdatePreview (shows field changes)
fallback                          → GenericJSON (raw payload)
```

**Approval flow**:
1. SSE `approval_request` event → `store.addApproval(request)`
2. ChatView sees destructive action → renders `DestructiveApprovalModal`
3. User clicks Approve/Reject (or countdown expires)
4. POST `/api/v1/ai/approvals/{id}/resolve` with `{ decision: 'approved' | 'rejected', reason? }`
5. Backend executes (or cancels) the action
6. SSE `content_update` event → UI updates to reflect result
7. Modal unmounts; approval card in message stream collapses to chip

---

### `InlineApprovalCard.tsx`

**Responsibility**: Non-blocking approval card rendered inline in the message stream for DEFAULT-tier actions.

**Behavior**:
- Visible within the conversation flow (not a blocking overlay)
- 24-hour expiration countdown
- Optional rejection reason textarea
- `Escape` = reject (keyboard shortcut)
- `Enter` (when focused on approve button) = approve

**When used**: Issue creation, note updates, comment posting, task creation — content-generating actions that are reversible or low-risk.

**Visual**: Card with action title, reasoning (`why`), payload preview, and two action buttons (Approve / Reject).

---

### `SkillApprovalCard.tsx`

**Responsibility**: Approval card for skill-level operations that show planned work items.

**Difference from InlineApprovalCard**: Shows the skill's planned "work intents" (what sub-tasks the skill will perform) so users can preview the scope before approving.

**Live countdown**: Amber/red pulsing at thresholds, same as DestructiveApprovalModal.

**Artifact preview**: Shows skill output artifacts (e.g., list of issues to create) before approval.

---

### `ContentDiff.tsx`

**Responsibility**: Side-by-side or before/after diff viewer for text content changes.

**Used by**: `DestructiveApprovalModal` for `update_note`, `update_issue_description` actions.

**Features**:
- Tabbed view: "Before" / "After" / "Diff"
- Scrollable content panels
- Line-level change highlighting (additions in green, deletions in red)
- Character-level diff for short content

**Why**: Users must see _exactly_ what will change, not just a summary. Without the diff, approving a note update is a blind trust exercise.

---

### `IssuePreview.tsx`

**Responsibility**: Read-only preview of an issue that will be created or deleted.

**Fields shown**:
- Title
- State badge (Backlog / Todo / In Progress / etc.)
- Priority badge
- Type badge
- Estimated hours
- Labels
- Description (Markdown rendered)

**Used by**: Approval for `create_issue` and `delete_issue` actions.

---

### `IssueUpdatePreview.tsx`

**Responsibility**: Shows field-level changes for an issue update.

**Renders**: Each changed field as a "from → to" row with Markdown support for description changes.

**Used by**: Approval for `update_issue` actions.

---

### `GenericJSON.tsx`

**Responsibility**: Fallback preview for action types without a specialized renderer.

**Renders**: Formatted JSON of the action payload in a scrollable code block.

**When used**: New or unrecognized action types, or debug scenarios.

**Why it exists**: The approval system must handle future action types without requiring a UI update. GenericJSON ensures unknown types are still approvable with full payload visibility.

---

## Approval Workflow (End-to-End)

```
1. Backend AI agent decides to take action
       ↓
2. SSE event: `approval_request`
   { id, action_type, payload, reasoning, confidence, expires_at }
       ↓
3. PilotSpaceStore.addApproval(request)
   → store.pendingApprovals[] updated
       ↓
4. ChatView (observer) detects new approval
   → isDestructiveAction(action_type) ?
     YES → DestructiveApprovalModal opens (blocking)
     NO  → InlineApprovalCard renders in message stream
       ↓
5. User reviews preview, clicks Approve or Reject
       ↓
6. POST /api/v1/ai/approvals/{id}/resolve
   { decision: 'approved' | 'rejected', reason?: string }
       ↓
7. store.resolveApproval(id, decision)
   → card collapses to "Approved" / "Rejected" chip
       ↓
8. Backend: if approved → executes action → SSE content_update
           if rejected → cancels action → SSE tool_result (cancelled)
       ↓
9. UI reflects result (issue created, note updated, etc.)
```

---

## Implicit Features

| Feature | How | Where |
|---------|-----|-------|
| Non-dismissable modal | No `onOpenChange` escape hatch | `DestructiveApprovalModal` |
| 5-min auto-reject countdown | `setInterval` + `onExpire` callback | `DestructiveApprovalModal` |
| Reject button focused on open | `autoFocus` on reject button | `DestructiveApprovalModal` |
| Escape = reject | `onKeyDown` handler | `InlineApprovalCard`, `DestructiveApprovalModal` |
| Countdown color thresholds | `> 5m → 1m–5m → < 1m` | Both modal and inline |
| Animated pulse < 1m | Tailwind `animate-pulse` conditional | Both modal and inline |
| GenericJSON fallback | Decision tree always has fallback arm | `DestructiveApprovalModal` |
| Rejection reason textarea | Optional, sent with resolve request | `InlineApprovalCard` |
| 24h expiration on inline cards | `expires_at` from SSE event | `InlineApprovalCard` |
| Diff tabs (Before/After/Diff) | Tab state local to `ContentDiff` | `ContentDiff` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Modal for destructive, inline for safe | Destructive actions warrant interruption. Content creation does not. |
| Non-dismissable modal | Clicking outside to close could accidentally dismiss a pending delete. Safety-first. |
| Reject focused by default | Cognitive bias: default action should be the safer one. |
| Escape = reject | Dismissal gesture should never accidentally approve a dangerous action. |
| 5-min auto-reject (not auto-approve) | Timeout failure mode must be safe. Auto-approval would execute potentially harmful actions unattended. |
| GenericJSON fallback | New action types must remain approvable without a UI code change. |
| Confidence ≥ 70% for batch confirm | Below this threshold, AI classification is uncertain enough to require individual review. |
| Approval result via REST (not SSE) | Decision is a synchronous user action with immediate feedback needed. SSE is one-directional. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `ApprovalOverlay/DestructiveApprovalModal.tsx` | ~200 | Blocking 5-min auto-reject modal |
| `ApprovalOverlay/ContentDiff.tsx` | ~150 | Before/after diff viewer |
| `ApprovalOverlay/IssuePreview.tsx` | ~120 | Issue creation/deletion preview |
| `ApprovalOverlay/IssueUpdatePreview.tsx` | ~100 | Issue field change preview |
| `ApprovalOverlay/GenericJSON.tsx` | ~60 | Fallback JSON renderer |
| `MessageList/InlineApprovalCard.tsx` | ~180 | Non-blocking inline approval |
| `MessageList/SkillApprovalCard.tsx` | ~160 | Skill-level approval with artifacts |
| `ConfirmAllButton.tsx` | ~135 | Batch approve ≥70% confidence intents |
