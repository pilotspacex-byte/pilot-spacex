# SSE Event Contract: AI Context Tab

**Branch**: `005-conversation-fix` | **Date**: 2026-02-02

## Overview

The AI Context generation uses Server-Sent Events (SSE) to stream structured data sections independently. Each section arrives as its own event type, allowing the frontend to render sections incrementally as they become available.

## Endpoint

```
POST /api/v1/ai/workspaces/{workspace_id}/issues/{issue_id}/ai-context
```

**Headers**: `Accept: text/event-stream`, `Authorization: Bearer {jwt}`

## Event Types

### `phase` (existing)

Progress indicator during generation.

```
event: phase
data: {"name": "Analyzing issue", "status": "in_progress", "content": "Reading issue PS-201..."}
```

**Payload**:
```typescript
{
  name: string;          // Phase name
  status: 'pending' | 'in_progress' | 'complete';
  content?: string;      // Optional progress detail
}
```

### `context_summary`

Issue overview with aggregated stats.

```
event: context_summary
data: {"issueIdentifier":"PS-201","title":"Simplify password reset flow","summaryText":"Reduce password reset from 5 steps to 2-3 using magic links. Target 30% improvement in completion rate. Part of Auth UX cluster with 4 related issues.","stats":{"relatedCount":4,"docsCount":3,"filesCount":8,"tasksCount":5}}
```

**Payload**: `ContextSummary` (see data-model.md)

### `related_issues`

Issues related to the current issue with relationship types.

```
event: related_issues
data: {"items":[{"relationType":"blocks","issueId":"uuid-202","identifier":"PS-202","title":"Handle social login errors gracefully","summary":"OAuth error handling with retry logic for Google/GitHub sign-in failures.","status":"In Progress","stateGroup":"started"},{"relationType":"relates","issueId":"uuid-203","identifier":"PS-203","title":"Extend session timeout settings","summary":"Configurable session duration with remember-me option.","status":"Done","stateGroup":"completed"}]}
```

**Payload**:
```typescript
{
  items: ContextRelatedIssue[];
}
```

### `related_docs`

Documents (notes, ADRs, specs) related to the issue.

```
event: related_docs
data: {"items":[{"docType":"note","title":"Auth Refactor","summary":"Planning notes for authentication system overhaul."},{"docType":"adr","title":"ADR-0015: Error Handling in Auth Flows","summary":"Decision record for standardizing error messages."},{"docType":"spec","title":"Auth Module Spec v2","summary":"Technical specification for auth module."}]}
```

**Payload**:
```typescript
{
  items: ContextRelatedDoc[];
}
```

### `ai_tasks`

AI-generated implementation tasks with dependencies.

```
event: ai_tasks
data: {"items":[{"id":1,"title":"Create magic link service","estimate":"~2h","dependencies":[],"completed":false},{"id":2,"title":"Update email templates","estimate":"~1h","dependencies":[1],"completed":false}]}
```

**Payload**:
```typescript
{
  items: ContextTask[];
}
```

### `ai_prompts`

Ready-to-use prompts for Claude Code, mapped to tasks.

```
event: ai_prompts
data: {"items":[{"taskId":1,"title":"Task 1: Create Magic Link Service","content":"Create a magic link authentication service in src/auth/magic_link.py:\n\nRequirements:\n- Generate secure, time-limited tokens (15 min expiry)\n..."}]}
```

**Payload**:
```typescript
{
  items: ContextPrompt[];
}
```

### `context_error`

Per-section error. Other sections continue streaming.

```
event: context_error
data: {"section":"related_issues","message":"Failed to analyze related issues: timeout"}
```

**Payload**:
```typescript
{
  section: string;   // One of: summary, related_issues, related_docs, tasks, prompts
  message: string;   // Human-readable error message
}
```

### `context_complete`

All sections finished streaming. No more events will follow.

```
event: context_complete
data: {}
```

**Payload**: Empty object `{}`

## Event Ordering

Events arrive in this general order (not strictly guaranteed):

1. `phase` events (progress indicators) — multiple, interleaved
2. `context_summary` — arrives first among data events
3. `related_issues` and `related_docs` — arrive in parallel
4. `ai_tasks` — after issues/docs analysis
5. `ai_prompts` — after tasks are generated
6. `context_error` — can arrive at any point for any section
7. `context_complete` — always last

## Error Handling

- **Per-section error**: `context_error` event with section name. Frontend shows error state for that section only; other sections render normally.
- **Stream error** (HTTP 500, connection drop): SSEClient retries with exponential backoff (max 3 retries). After max retries, `onError` callback fires and store sets global error state.
- **Abort**: User navigates away or clicks "Regenerate" — `AbortController.abort()` cancels the stream cleanly.

## Backward Compatibility

The existing `complete` event type is still supported for backward compatibility. If the backend sends a single `complete` event with the legacy flat structure, the store populates legacy fields (`claudeCodePrompt`, `relatedDocs_legacy`, `relatedCode`, `similarIssues`) and the UI falls back to the old display format.

New section-based events take precedence when available. The store checks `result.summary !== null` to determine which rendering path to use.
