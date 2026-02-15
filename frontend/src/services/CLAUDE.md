# Frontend API Services

**Scope**: `frontend/src/services/api/` (9 API clients)
**Stack**: Axios + TypeScript generics + RFC 7807 errors + TanStack Query integration

---

## Overview

Typed HTTP clients for all backend REST endpoints. All clients use Axios interceptors for Supabase JWT auth and RFC 7807 error handling. Snake_case from backend auto-transforms to camelCase on frontend.

---

## Base Client

**Implementation**: `client.ts`

| Component           | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `ApiError`          | Custom error class -- RFC 7807 compliant (`status`, `type`, `detail`, `isRetryable`) |
| `ApiProblemDetails` | Error interface matching FastAPI exception format                                    |
| `apiClient`         | HTTP methods (GET, POST, PUT, PATCH, DELETE) with `<T>` generic returns              |

**Request Flow**: Request -> Interceptor (add Bearer token) -> Axios -> Response -> Interceptor (error handling)

**Interceptor Auto-Handling**:

- 401: Sign out + redirect to `/login`
- 429: Toast rate limit warning with retry-after duration
- 403: "Access Denied" toast
- 500+: "Server Error" toast (except 501)

**Retryable Status Codes**: 408, 429, 500-503 (except 501)

**Response Wrappers**: `PaginatedResponse<T>` (items, total, page, pageSize, hasMore) and optional `ApiResponse<T>` (data, meta). See `client.ts` for interfaces.

---

## API Clients (9 Total)

| Client           | File              | Scope                                           | Key Methods                                                                     |
| ---------------- | ----------------- | ----------------------------------------------- | ------------------------------------------------------------------------------- |
| **Issues**       | `issues.ts`       | CRUD + state machine + AI                       | `list`, `get`, `create`, `update`, `updateState`, `enhance`, `checkDuplicates`  |
| **Notes**        | `notes.ts`        | TipTap docs + metadata + annotations            | `list`, `get`, `create`, `updateContent` (auto-save), `pin`, `linkIssue`        |
| **AI**           | `ai.ts`           | SSE streaming, settings, approvals, costs, chat | `getGhostTextUrl()`, `getWorkspaceSettings()`, `createConversationSession()`    |
| **Workspaces**   | `workspaces.ts`   | CRUD, member mgmt                               | `list`, `get`, `create`, `getMembers()`, `inviteMember()`, `updateMemberRole()` |
| **Projects**     | `projects.ts`     | Lightweight CRUD                                | `list`, `get`, `create`, `update`, `delete`                                     |
| **Cycles**       | `cycles.ts`       | Sprint planning, metrics                        | `list`, `get`, `create`, `addIssue()`, `rollover()`, `getBurndownData()`        |
| **Approvals**    | `approvals.ts`    | Human-in-the-loop (DD-003)                      | `listPending()`, `approve()`, `reject()`, `getPendingCount()`                   |
| **Integrations** | `integrations.ts` | GitHub OAuth, PR webhooks                       | `getGitHubAuthUrl()`, `completeGitHubAuth()`, `listRepositories()`              |
| **Onboarding**   | `onboarding.ts`   | First-time setup                                | `getOnboardingState()`, `updateOnboardingStep()`, `validateProviderKey()`       |
| **Role Skills**  | `role-skills.ts`  | SDLC roles, AI generation                       | `getTemplates()`, `getRoleSkills()`, `createRoleSkill()`, `generateSkill()`     |

SSE endpoints return URLs only (no HTTP call). Import all clients via barrel export: `import { issuesApi } from '@/services/api'`.

---

## Error Handling

All errors conform to RFC 7807 Problem Details. See `client.ts:ApiError` for the custom error class with `status`, `title`, `detail`, `type`, `errors` (validation), and `isRetryable`.

**Usage**: Catch `ApiError` instances for type-safe error handling. Validation errors available via `error.errors` (field-to-messages mapping). Interceptor handles 401/403/429/500+ automatically with toast notifications.

**Graceful Degradation**: For non-critical endpoints, catch and return null (e.g., optional AI context fetch).

---

## SSE Client

**Implementation**: `lib/sse-client.ts`

Custom streaming client for POST-based SSE (EventSource only supports GET).

| Feature        | Detail                                                     |
| -------------- | ---------------------------------------------------------- |
| POST with body | Uses fetch ReadableStream instead of EventSource           |
| Auth headers   | Automatically adds Bearer token from Supabase session      |
| Event parsing  | Handles chunked `event:` + `data:` lines                   |
| Reconnection   | Exponential backoff (1s -> 2s -> 4s -> 8s) up to 3 retries |
| Abort control  | AbortController for cancellation                           |
| Type safety    | `SSEEvent { type, data }` with parsed JSON                 |

**Setup**: `new SSEClient({ url, method: 'POST', body, onMessage, onError, onComplete })`. Methods: `connect()`, `abort()`.

**Event Types**: `message_start`, `text_delta`, `tool_use`, `tool_result`, `content_update`, `approval_request`, `task_progress`, `message_stop`, `error`.

---

## Workspace Scoping

All endpoints require workspace ID (path param, query param, or header). RLS enforces `auth.user_workspace_ids()` contains the requested workspace.

---

## TanStack Query Patterns

- **Query Key Factories**: Hierarchical keys per feature (e.g., `issuesKeys.detail(issueId)`)
- **Optimistic Updates**: Cancel in-flight -> snapshot -> update UI -> rollback on error -> refetch on settle
- **Pagination**: Cursor-based with `keepPreviousData: true`
- **Dependent Queries**: Use `enabled` flag to chain
- **Invalidation**: Mutation `onSettled` invalidates related queries

---

## Related Documentation

- **MobX Stores**: [`../stores/CLAUDE.md`](../stores/CLAUDE.md)
- **AI Feature Module**: [`../features/ai/CLAUDE.md`](../features/ai/CLAUDE.md)
- **Frontend Architecture**: [`../../CLAUDE.md`](../../CLAUDE.md)
