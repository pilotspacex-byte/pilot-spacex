# API Reference

PilotSpace backend exposes a RESTful API at `/api/v1/` with SSE streaming for AI endpoints.

## Authentication

All API requests require a Bearer token:

```text
Authorization: Bearer <jwt>
X-Workspace-Id: <uuid>
```

- **JWT Provider**: Supabase Auth (HS256) or AuthCore (RS256)
- **Token lifetime**: 1 hour (access), 7 days (refresh)
- **Refresh**: Automatic via Supabase SDK; frontend interceptor handles 401 → retry

## Error Format (RFC 7807)

All errors return `Content-Type: application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "Field 'name' is required",
  "instance": "/api/v1/issues"
}
```

| Status | Meaning                                         |
| ------ | ----------------------------------------------- |
| 400    | Validation failure / business logic error       |
| 401    | Missing or expired JWT                          |
| 403    | Insufficient permissions (role check)           |
| 404    | Resource not found                              |
| 422    | Pydantic validation errors (with field details) |
| 429    | Rate limit exceeded                             |
| 500    | Unhandled exception                             |

## Core Endpoints

### Notes

| Method   | Endpoint                                    | Description                      |
| -------- | ------------------------------------------- | -------------------------------- |
| `POST`   | `/{workspaceId}/notes`                      | Create note                      |
| `GET`    | `/{workspaceId}/notes`                      | List notes (paginated)           |
| `GET`    | `/{workspaceId}/notes/{noteId}`             | Get note with relations          |
| `PATCH`  | `/{workspaceId}/notes/{noteId}`             | Update note (optimistic locking) |
| `DELETE` | `/{workspaceId}/notes/{noteId}`             | Soft-delete note                 |
| `POST`   | `/{workspaceId}/notes/{noteId}/pin`         | Pin note                         |
| `GET`    | `/{workspaceId}/notes/{noteId}/annotations` | List annotations                 |
| `GET`    | `/{workspaceId}/notes/{noteId}/versions`    | Version history                  |

### Issues

| Method  | Endpoint                                     | Description                     |
| ------- | -------------------------------------------- | ------------------------------- |
| `POST`  | `/{workspaceId}/issues`                      | Create issue                    |
| `GET`   | `/{workspaceId}/issues`                      | List issues (cursor-paginated)  |
| `GET`   | `/{workspaceId}/issues/{issueId}`            | Get issue with activity         |
| `PATCH` | `/{workspaceId}/issues/{issueId}`            | Update issue fields             |
| `PUT`   | `/{workspaceId}/issues/{issueId}/state`      | Transition state (accepts name) |
| `GET`   | `/{workspaceId}/issues/{issueId}/activities` | Activity timeline (infinite)    |

### AI Chat (SSE)

| Method   | Endpoint                   | Description              |
| -------- | -------------------------- | ------------------------ |
| `POST`   | `/ai/chat`                 | Stream AI response (SSE) |
| `POST`   | `/ai/chat/answer`          | Submit approval decision |
| `POST`   | `/ai/ghost-text`           | Get inline completion    |
| `GET`    | `/ai/sessions`             | List AI sessions         |
| `DELETE` | `/ai/sessions/{sessionId}` | Delete session           |

### AI Configuration

| Method | Endpoint                         | Description               |
| ------ | -------------------------------- | ------------------------- |
| `GET`  | `/ai/configuration`              | Get workspace AI settings |
| `PUT`  | `/ai/configuration`              | Update AI settings        |
| `POST` | `/ai/configuration/validate-key` | Validate provider API key |
| `GET`  | `/ai/costs`                      | Get cost summary          |

### Projects & Cycles

| Method | Endpoint                                 | Description        |
| ------ | ---------------------------------------- | ------------------ |
| `POST` | `/{workspaceId}/projects`                | Create project     |
| `GET`  | `/{workspaceId}/projects`                | List projects      |
| `POST` | `/{workspaceId}/cycles`                  | Create cycle       |
| `GET`  | `/{workspaceId}/cycles`                  | List cycles        |
| `POST` | `/{workspaceId}/cycles/{cycleId}/issues` | Add issue to cycle |

### Integrations

| Method | Endpoint                            | Description          |
| ------ | ----------------------------------- | -------------------- |
| `GET`  | `/integrations/github/auth-url`     | Get GitHub OAuth URL |
| `POST` | `/integrations/github/callback`     | Complete OAuth flow  |
| `GET`  | `/integrations/github/repositories` | List connected repos |

## SSE Event Types

AI chat endpoints return Server-Sent Events:

| Event              | Payload                             | Description            |
| ------------------ | ----------------------------------- | ---------------------- |
| `text_delta`       | `{messageId, delta}`                | Incremental text chunk |
| `tool_use`         | `{toolUseId, toolName, input}`      | MCP tool invocation    |
| `tool_result`      | `{toolUseId, result}`               | Tool execution result  |
| `content_update`   | `{operation, payload, status}`      | Note/issue mutation    |
| `approval_request` | `{approvalId, action, description}` | Human-in-the-loop      |
| `task_progress`    | `{taskId, status, progress}`        | Long-running task      |
| `message_stop`     | `{messageId}`                       | End of response        |
| `error`            | `{code, message}`                   | Error notification     |

## Rate Limits

| Scope              | Limit         | Window   |
| ------------------ | ------------- | -------- |
| Standard endpoints | 1000 requests | 1 minute |
| AI endpoints       | 100 requests  | 1 minute |
| Ghost text         | 10 requests   | 1 second |

Rate limit headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`.

## Pagination

Cursor-based pagination for large datasets:

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6IjEyMyJ9",
  "prev_cursor": null,
  "has_next": true,
  "has_prev": false,
  "total_count": 142
}
```

Use `?cursor={next_cursor}&page_size=50` for next page.
