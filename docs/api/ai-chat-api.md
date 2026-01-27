# AI Chat API Documentation (T101)

Comprehensive API reference for PilotSpace AI chat endpoints, including conversational agents, subagents, and skill invocations.

**Version**: 1.0 | **Last Updated**: 2026-01-28

---

## Table of Contents

- [Authentication](#authentication)
- [Chat Sessions](#chat-sessions)
- [Messages](#messages)
- [Skills](#skills)
- [Subagents](#subagents)
- [Approvals](#approvals)
- [SSE Event Types](#sse-event-types)
- [Error Codes](#error-codes)

---

## Authentication

All AI endpoints require the following headers:

```http
X-Workspace-ID: your-workspace-id
X-Anthropic-API-Key: your-anthropic-key
X-Google-API-Key: your-google-key (optional)
X-OpenAI-API-Key: your-openai-key (for embeddings)
```

**BYOK Model**: Users provide their own API keys (stored encrypted in Supabase Vault).

---

## Chat Sessions

### Create Chat Session

Create a new multi-turn conversation session.

**Endpoint**: `POST /api/v1/ai/chat/sessions`

**Request**:

```json
{
  "agent_name": "conversation",
  "system_context": "Optional context for system prompt"
}
```

**Response**: `201 Created`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "conversation",
  "system_context": "Optional context",
  "status": "active",
  "created_at": "2026-01-28T10:00:00Z",
  "ttl_seconds": 1800,
  "message_count": 0,
  "total_tokens": 0
}
```

**Fields**:
- `session_id`: UUID for this session
- `agent_name`: Agent handling conversation
- `system_context`: Additional context for AI
- `status`: `active` | `expired`
- `ttl_seconds`: Time-to-live (30 minutes)

---

### Get Session

Retrieve session metadata.

**Endpoint**: `GET /api/v1/ai/chat/sessions/{session_id}`

**Response**: `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "conversation",
  "status": "active",
  "created_at": "2026-01-28T10:00:00Z",
  "updated_at": "2026-01-28T10:05:00Z",
  "message_count": 4,
  "total_tokens": 1250,
  "total_cost_usd": 0.0025
}
```

---

### List Sessions

List user's chat sessions.

**Endpoint**: `GET /api/v1/ai/chat/sessions`

**Query Parameters**:
- `agent_name`: Filter by agent
- `status`: Filter by status (`active`, `expired`)
- `limit`: Results per page (default: 20)
- `offset`: Pagination offset

**Response**: `200 OK`

```json
{
  "items": [
    {
      "session_id": "...",
      "agent_name": "conversation",
      "status": "active",
      "updated_at": "2026-01-28T10:05:00Z",
      "message_count": 4
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### Delete Session

Delete a chat session and its history.

**Endpoint**: `DELETE /api/v1/ai/chat/sessions/{session_id}`

**Response**: `204 No Content`

---

## Messages

### Send Message (Streaming)

Send message to chat session with SSE streaming response.

**Endpoint**: `POST /api/v1/ai/chat/sessions/{session_id}/messages`

**Request**:

```json
{
  "message": "What is FastAPI?"
}
```

**Response**: `200 OK` with `text/event-stream` content type

**SSE Stream**:

```
event: token
data: {"content": "FastAPI"}

event: token
data: {"content": " is a"}

event: token
data: {"content": " modern"}

event: done
data: {"total_tokens": 150, "message_count": 2}
```

See [SSE Event Types](#sse-event-types) for details.

---

### Get Message History

Retrieve conversation history for a session.

**Endpoint**: `GET /api/v1/ai/chat/sessions/{session_id}/history`

**Response**: `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "What is FastAPI?",
      "timestamp": "2026-01-28T10:00:00Z",
      "tokens": 5
    },
    {
      "role": "assistant",
      "content": "FastAPI is a modern web framework...",
      "timestamp": "2026-01-28T10:00:02Z",
      "tokens": 45
    }
  ],
  "total_tokens": 50,
  "truncated": false
}
```

**Fields**:
- `truncated`: `true` if history exceeded 8000 token budget

---

## Skills

Skills are pre-built AI workflows accessible via `/skills/*` endpoints.

### Extract Issues from Note

Extract actionable issues from note content.

**Endpoint**: `POST /api/v1/ai/skills/extract-issues`

**Request**:

```json
{
  "note_id": "550e8400-e29b-41d4-a716-446655440000",
  "note_content": "We need to implement authentication with OAuth2",
  "auto_create": false
}
```

**Response**: `200 OK` (or `202 Accepted` if `auto_create=true`)

```json
{
  "issues": [
    {
      "name": "Implement OAuth2 authentication",
      "description": "Add OAuth2 authentication with Google and GitHub providers",
      "confidence": "RECOMMENDED",
      "rationale": "Clear implementation requirement with specific providers mentioned",
      "source_block_id": "block-uuid",
      "labels": ["backend", "security"],
      "priority": "high"
    }
  ]
}
```

**Confidence Tags**: `RECOMMENDED` | `DEFAULT` | `CURRENT` | `ALTERNATIVE` (see DD-048)

---

### Enhance Issue

Improve issue metadata with AI suggestions.

**Endpoint**: `POST /api/v1/ai/skills/enhance-issue`

**Request**:

```json
{
  "issue": {
    "id": "issue-uuid",
    "name": "Fix login bug",
    "description": "Users can't log in"
  }
}
```

**Response**: `200 OK`

```json
{
  "enhanced_issue": {
    "labels": ["backend", "security", "bug"],
    "labels_confidence": "RECOMMENDED",
    "priority": "critical",
    "priority_confidence": "RECOMMENDED",
    "improved_description": "Users are unable to authenticate due to JWT token validation failure. Affects all login attempts.",
    "suggested_assignee": {
      "user_email": "alice@example.com",
      "confidence": "DEFAULT"
    }
  }
}
```

---

### Recommend Assignee

Suggest assignee based on issue context and team expertise.

**Endpoint**: `POST /api/v1/ai/skills/recommend-assignee`

**Request**:

```json
{
  "issue_id": "issue-uuid",
  "issue_title": "Implement JWT authentication",
  "issue_description": "Add JWT-based auth with refresh tokens",
  "labels": ["backend", "security"]
}
```

**Response**: `200 OK`

```json
{
  "assignee": {
    "user_id": "user-uuid",
    "user_email": "alice@example.com",
    "confidence": "RECOMMENDED",
    "rationale": "Primary backend engineer, authored 80% of auth module, available capacity (2 current issues)",
    "expertise_match": 0.92,
    "current_workload": 2
  }
}
```

---

### Find Duplicates

Find similar issues using semantic search.

**Endpoint**: `POST /api/v1/ai/skills/find-duplicates`

**Request**:

```json
{
  "issue_title": "Implement user authentication",
  "issue_description": "Add JWT-based authentication system"
}
```

**Response**: `200 OK`

```json
{
  "duplicates": [
    {
      "issue_id": "existing-issue-uuid",
      "issue_title": "Add OAuth2 login",
      "similarity_score": 0.87,
      "confidence": "RECOMMENDED",
      "rationale": "Both issues involve authentication implementation"
    }
  ]
}
```

---

### Decompose Tasks

Break issue into subtasks with dependencies.

**Endpoint**: `POST /api/v1/ai/skills/decompose-tasks`

**Request**:

```json
{
  "issue_id": "issue-uuid",
  "issue_description": "Implement complete user authentication with OAuth2 and JWT"
}
```

**Response**: `200 OK`

```json
{
  "subtasks": [
    {
      "name": "Design authentication schema",
      "description": "Create database tables for users, sessions, and OAuth providers",
      "confidence": "RECOMMENDED",
      "dependencies": [],
      "estimated_effort": "small"
    },
    {
      "name": "Implement JWT generation and validation",
      "description": "Add JWT library, create token signing and verification logic",
      "confidence": "RECOMMENDED",
      "dependencies": ["Design authentication schema"],
      "estimated_effort": "medium"
    }
  ]
}
```

---

### Generate Diagram

Generate Mermaid diagram from description.

**Endpoint**: `POST /api/v1/ai/skills/generate-diagram`

**Request**:

```json
{
  "description": "Authentication flow with OAuth2",
  "diagram_type": "sequence"
}
```

**Response**: `200 OK`

```json
{
  "diagram": {
    "mermaid_code": "sequenceDiagram\n  User->>App: Login\n  App->>OAuth: Redirect\n  OAuth->>App: Token\n  App->>User: Success",
    "confidence": "RECOMMENDED",
    "diagram_type": "sequence"
  }
}
```

---

## Subagents

Subagents handle complex multi-turn tasks with streaming.

### PR Review Subagent

Interactive pull request review.

**Endpoint**: `POST /api/v1/ai/subagents/pr-review` (streaming)

**Request**:

```json
{
  "repository_id": "repo-uuid",
  "pr_number": 123,
  "include_architecture": true,
  "include_security": true,
  "include_performance": true
}
```

**Response**: `200 OK` with SSE stream

**SSE Events**:

```
event: finding
data: {"category": "security", "severity": "critical", "file_path": "auth.py", "line_number": 42, "description": "SQL injection vulnerability", "fix_suggestion": "Use parameterized queries"}

event: finding
data: {"category": "performance", "severity": "warning", "file_path": "api.py", "line_number": 100, "description": "N+1 query detected"}

event: summary
data: {"approval_status": "CHANGES_REQUESTED", "total_findings": 5, "critical": 1, "warnings": 3, "suggestions": 1}
```

---

### AI Context Subagent

Aggregate context for issue resolution.

**Endpoint**: `POST /api/v1/ai/subagents/ai-context` (streaming)

**Request**:

```json
{
  "issue_id": "issue-uuid",
  "include_notes": true,
  "include_code": true,
  "include_tasks": true
}
```

**Response**: `200 OK` with SSE stream

**SSE Events**:

```
event: related_note
data: {"note_id": "note-uuid", "title": "Auth Architecture", "relevance": "RECOMMENDED", "excerpt": "JWT implementation..."}

event: code_snippet
data: {"file_path": "src/auth/jwt.py", "line_number": 42, "code": "def verify_token...", "explanation": "Current JWT verification"}

event: task
data: {"name": "Update JWT library", "confidence": "RECOMMENDED", "dependencies": []}
```

---

### Doc Generator Subagent

Generate documentation from source code.

**Endpoint**: `POST /api/v1/ai/subagents/doc-generator` (streaming)

**Request**:

```json
{
  "doc_type": "api_reference",
  "source_files": ["src/api/v1/routers/issues.py"]
}
```

**Response**: `200 OK` with SSE stream

**SSE Events**:

```
event: section
data: {"heading": "Issues API", "content": "## Issues API\n\nManage project issues..."}

event: section
data: {"heading": "Endpoints", "content": "### GET /api/v1/issues\n\nList issues..."}
```

---

## Approvals

DD-003 human-in-the-loop approval flow.

### Get Approval Request

**Endpoint**: `GET /api/v1/ai/approvals/{approval_id}`

**Response**: `200 OK`

```json
{
  "id": "approval-uuid",
  "action_type": "extract_issues",
  "classification": "default_require",
  "status": "pending",
  "description": "Create 3 issues from note content",
  "proposed_changes": {
    "issues": [
      {"name": "Issue 1", "description": "..."}
    ]
  },
  "created_at": "2026-01-28T10:00:00Z",
  "expires_at": "2026-01-29T10:00:00Z"
}
```

---

### Approve Request

**Endpoint**: `POST /api/v1/ai/approvals/{approval_id}/approve`

**Response**: `200 OK`

```json
{
  "id": "approval-uuid",
  "status": "approved",
  "executed_result": {
    "issues_created": [
      {"id": "issue-uuid-1", "name": "Issue 1"},
      {"id": "issue-uuid-2", "name": "Issue 2"}
    ]
  }
}
```

---

### Reject Request

**Endpoint**: `POST /api/v1/ai/approvals/{approval_id}/reject`

**Request**:

```json
{
  "reason": "Not enough context in descriptions"
}
```

**Response**: `200 OK`

```json
{
  "id": "approval-uuid",
  "status": "rejected",
  "rejection_reason": "Not enough context in descriptions"
}
```

---

### List Approvals

**Endpoint**: `GET /api/v1/ai/approvals`

**Query Parameters**:
- `status`: Filter by status (`pending`, `approved`, `rejected`, `expired`)
- `action_type`: Filter by action type
- `limit`: Results per page (default: 20)

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "approval-uuid",
      "action_type": "extract_issues",
      "status": "pending",
      "created_at": "2026-01-28T10:00:00Z"
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

## SSE Event Types

All streaming endpoints use Server-Sent Events (SSE) format.

### Event Format

```
event: <event_type>
data: <json_payload>

```

### Common Event Types

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `token` | Streaming text token | `content`: string |
| `done` | Stream complete | `total_tokens`: int, `message_count`: int |
| `error` | Error occurred | `error`: string, `code`: string |
| `finding` | Review finding (PR review) | `category`, `severity`, `file_path`, `line_number`, `description`, `fix_suggestion` |
| `related_note` | Related note (AI context) | `note_id`, `title`, `relevance`, `excerpt` |
| `code_snippet` | Code snippet (AI context) | `file_path`, `line_number`, `code`, `explanation` |
| `section` | Documentation section (doc gen) | `heading`, `content` |
| `tool_call` | Tool execution | `tool_name`, `parameters`, `result` |

---

## Error Codes

All errors follow RFC 7807 Problem Details format.

### Error Response Format

```json
{
  "type": "/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "message field is required",
  "instance": "/api/v1/ai/chat/sessions/123/messages",
  "errors": [
    {"field": "message", "message": "Field is required"}
  ],
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Common Error Types

| Type | Status | Description |
|------|--------|-------------|
| `/errors/validation` | 422 | Invalid request data |
| `/errors/not-found` | 404 | Resource not found |
| `/errors/unauthorized` | 401 | Missing or invalid API key |
| `/errors/forbidden` | 403 | RLS policy violation |
| `/errors/rate-limit` | 429 | Rate limit exceeded |
| `/errors/ai-configuration` | 400 | AI provider not configured |
| `/errors/approval-required` | 202 | Action requires approval |
| `/errors/session-expired` | 410 | Session TTL exceeded |

### Rate Limiting

Rate limits are enforced per-user:

- **Ghost Text**: 100 requests/minute
- **Chat Messages**: 60 requests/minute
- **Skills**: 30 requests/minute
- **Subagents**: 10 concurrent sessions

**Rate Limit Headers**:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706443200
Retry-After: 60
```

---

## Examples

### Complete Chat Conversation Flow

```python
import httpx
import json

# Create session
session_response = httpx.post(
    "http://localhost:8000/api/v1/ai/chat/sessions",
    headers={"X-Workspace-ID": "demo", "X-Anthropic-API-Key": "key"},
    json={"agent_name": "conversation"}
)
session_id = session_response.json()["session_id"]

# Stream message
with httpx.stream(
    "POST",
    f"http://localhost:8000/api/v1/ai/chat/sessions/{session_id}/messages",
    headers={"X-Workspace-ID": "demo", "X-Anthropic-API-Key": "key"},
    json={"message": "What is FastAPI?"}
) as response:
    for line in response.iter_lines():
        if line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1].strip())
            if "content" in data:
                print(data["content"], end="", flush=True)
```

---

## References

- **Design Decisions**: `docs/DESIGN_DECISIONS.md`
- **Architecture**: `docs/architect/ai-layer.md`
- **Skills Reference**: `docs/ai/skills-reference.md`
- **Subagents Reference**: `docs/ai/subagents-reference.md`
- **Approval Workflow**: `docs/ai/approval-workflow.md`

---

**Last Updated**: 2026-01-28 | **Version**: 1.0
