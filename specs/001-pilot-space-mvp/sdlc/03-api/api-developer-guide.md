# API Developer Guide

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

The Pilot Space API is a RESTful API built with FastAPI that provides programmatic access to all platform features. This guide covers authentication, common operations, and best practices.

**Base URL**: `https://api.pilotspace.io/api/v1`
**OpenAPI Spec**: `https://api.pilotspace.io/api/v1/openapi.json`

---

## Quick Start

### 1. Authentication

Pilot Space uses Supabase Auth with JWT tokens. All API requests require authentication.

```bash
# Get access token via Supabase Auth
curl -X POST "https://your-project.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "abc123..."
}
```

### 2. Make Authenticated Requests

```bash
# Include access token in Authorization header
curl -X GET "https://api.pilotspace.io/api/v1/workspaces" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 3. Create Your First Issue

```bash
curl -X POST "https://api.pilotspace.io/api/v1/projects/{project_id}/issues" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user authentication",
    "description": "Add login/logout functionality",
    "priority": "high",
    "state_id": "backlog"
  }'
```

---

## Authentication

### Token Types

| Token | Lifetime | Storage | Use Case |
|-------|----------|---------|----------|
| Access Token | 1 hour | Memory | API requests |
| Refresh Token | 7 days | HttpOnly cookie | Token refresh |

### Refreshing Tokens

```bash
curl -X POST "https://your-project.supabase.co/auth/v1/token?grant_type=refresh_token" \
  -H "apikey: YOUR_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token"
  }'
```

### OAuth/SSO

For OAuth providers (Google, GitHub) or SAML SSO, use Supabase Auth flows:

```javascript
// JavaScript/TypeScript example
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// OAuth sign-in
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'github',
  options: {
    redirectTo: 'https://app.pilotspace.io/auth/callback'
  }
})
```

---

## API Conventions

### Request Format

- **Content-Type**: `application/json`
- **Accept**: `application/json`
- **Date format**: ISO 8601 (`2026-01-23T10:30:00Z`)
- **UUID format**: Standard UUID v4

### Response Format

All responses follow a standard envelope:

```json
// Success response
{
  "data": { ... },
  "meta": {
    "total": 100,
    "cursor": "abc123",
    "has_more": true
  }
}

// Error response (RFC 7807)
{
  "type": "https://api.pilotspace.io/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "Title is required",
  "instance": "/api/v1/issues"
}
```

### Pagination

Cursor-based pagination for stable results:

```bash
# First page
GET /api/v1/projects/{id}/issues?limit=25

# Next page
GET /api/v1/projects/{id}/issues?limit=25&cursor=eyJpZCI6...
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "meta": {
    "total": 250,
    "cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true
  }
}
```

### Rate Limiting

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Standard API | 1000 requests | 1 minute |
| AI endpoints | 100 requests | 1 minute |

Rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1706012400
```

---

## Core Endpoints

### Workspaces

```bash
# List workspaces
GET /api/v1/workspaces

# Get workspace details
GET /api/v1/workspaces/{workspace_id}

# Update workspace
PATCH /api/v1/workspaces/{workspace_id}
{
  "name": "Updated Workspace Name",
  "settings": { "ai_enabled": true }
}
```

### Projects

```bash
# List projects in workspace
GET /api/v1/workspaces/{workspace_id}/projects

# Create project
POST /api/v1/workspaces/{workspace_id}/projects
{
  "name": "API Backend",
  "identifier": "API",
  "description": "Backend services project"
}

# Get project
GET /api/v1/projects/{project_id}
```

### Issues

```bash
# List issues (with filters)
GET /api/v1/projects/{project_id}/issues?state=in_progress&priority=high&assignee_id=uuid

# Create issue
POST /api/v1/projects/{project_id}/issues
{
  "title": "Fix login bug",
  "description": "Users cannot log in with SSO",
  "priority": "high",
  "state_id": "uuid",
  "assignee_id": "uuid",
  "label_ids": ["uuid1", "uuid2"]
}

# Get issue with AI context
GET /api/v1/issues/{issue_id}?include=ai_context,activity

# Update issue
PATCH /api/v1/issues/{issue_id}
{
  "title": "Updated title",
  "state_id": "new-state-uuid"
}

# Delete issue (soft delete)
DELETE /api/v1/issues/{issue_id}
```

### Notes

```bash
# List notes in project
GET /api/v1/projects/{project_id}/notes

# Create note
POST /api/v1/projects/{project_id}/notes
{
  "title": "Sprint Planning Notes",
  "content": { ... } // TipTap JSON format
}

# Get note with annotations
GET /api/v1/notes/{note_id}?include=annotations,linked_issues

# Update note content
PATCH /api/v1/notes/{note_id}
{
  "content": { ... }
}
```

### Cycles (Sprints)

```bash
# List cycles
GET /api/v1/projects/{project_id}/cycles

# Create cycle
POST /api/v1/projects/{project_id}/cycles
{
  "name": "Sprint 15",
  "start_date": "2026-01-27",
  "end_date": "2026-02-10",
  "goals": "Complete authentication feature"
}

# Add issue to cycle
POST /api/v1/cycles/{cycle_id}/issues
{
  "issue_id": "uuid"
}

# Get cycle with metrics
GET /api/v1/cycles/{cycle_id}?include=metrics
```

---

## AI Endpoints

### Ghost Text (SSE)

Request AI suggestions while typing:

```bash
# SSE endpoint for streaming
curl -N "https://api.pilotspace.io/api/v1/ai/ghost-text" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "current block text",
    "previous_blocks": ["block 1", "block 2", "block 3"],
    "document_summary": "Sprint planning notes"
  }'
```

Response (Server-Sent Events):

```
event: token
data: {"text": "Consider"}

event: token
data: {"text": " adding"}

event: done
data: {"full_text": "Consider adding acceptance criteria"}
```

### Issue Enhancement

```bash
POST /api/v1/ai/enhance-issue
{
  "title": "Fix bug",
  "description": "Something is broken"
}

# Response
{
  "data": {
    "enhanced_title": "Fix authentication timeout bug in SSO flow",
    "enhanced_description": "## Problem\nUsers experience...\n\n## Acceptance Criteria\n- [ ] ...",
    "suggested_labels": [
      { "id": "uuid", "name": "bug", "confidence": 0.95 }
    ],
    "suggested_priority": { "value": "high", "confidence": 0.85 },
    "suggested_assignee": { "id": "uuid", "name": "Alex", "confidence": 0.72 }
  }
}
```

### Duplicate Detection

```bash
POST /api/v1/ai/detect-duplicates
{
  "title": "Login not working",
  "description": "Cannot log in",
  "project_id": "uuid"
}

# Response
{
  "data": {
    "duplicates": [
      {
        "issue_id": "uuid",
        "title": "SSO login fails",
        "similarity": 0.85
      }
    ]
  }
}
```

### Task Decomposition

```bash
POST /api/v1/ai/decompose-task
{
  "feature_description": "Implement user authentication with SSO support",
  "project_id": "uuid"
}

# Response
{
  "data": {
    "subtasks": [
      {
        "title": "Set up Supabase Auth configuration",
        "description": "Configure OAuth providers...",
        "type": "backend",
        "estimate_points": 3,
        "dependencies": []
      },
      {
        "title": "Create login UI components",
        "description": "Build login form...",
        "type": "frontend",
        "estimate_points": 5,
        "dependencies": ["uuid-of-first-task"]
      }
    ]
  }
}
```

### PR Review (Webhook-Triggered)

PR reviews are triggered automatically by GitHub webhooks. To manually trigger:

```bash
POST /api/v1/ai/review-pr
{
  "pr_url": "https://github.com/org/repo/pull/123",
  "project_id": "uuid"
}

# Response (async - returns job ID)
{
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "estimated_completion": "2026-01-23T10:35:00Z"
  }
}

# Check job status
GET /api/v1/jobs/{job_id}
```

---

## Webhooks (Inbound)

### GitHub Webhook Events

Configure webhook URL: `https://api.pilotspace.io/api/v1/webhooks/github`

Supported events:
- `pull_request.opened` - Triggers AI review
- `pull_request.closed` - Updates linked issues
- `push` - Links commits to issues

### Slack Events

Configure event subscription: `https://api.pilotspace.io/api/v1/webhooks/slack`

Supported events:
- `app_mention` - Respond to mentions
- `slash_command` - Handle `/pilot` commands
- `link_shared` - Unfurl Pilot Space links

---

## Error Handling

### Error Response Format (RFC 7807)

```json
{
  "type": "https://api.pilotspace.io/errors/not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "Issue with ID 'abc123' not found",
  "instance": "/api/v1/issues/abc123"
}
```

### Common Error Codes

| Status | Type | Description |
|--------|------|-------------|
| 400 | `bad-request` | Invalid request format |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not-found` | Resource not found |
| 409 | `conflict` | Resource conflict (e.g., duplicate) |
| 422 | `validation-error` | Request validation failed |
| 429 | `rate-limited` | Rate limit exceeded |
| 500 | `internal-error` | Server error |

### Retry Strategy

For transient errors (429, 5xx), implement exponential backoff:

```python
import time
import requests

def api_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            time.sleep(2 ** attempt)  # Exponential backoff
            continue

        return response

    raise Exception("Max retries exceeded")
```

---

## SDKs and Tools

### Official SDKs

| Language | Package | Status |
|----------|---------|--------|
| Python | `pilot-space-sdk` | Planned |
| TypeScript | `@pilot-space/sdk` | Planned |

### API Exploration

- **OpenAPI Spec**: `/api/v1/openapi.json`
- **Swagger UI**: `/api/v1/docs`
- **ReDoc**: `/api/v1/redoc`

---

## Best Practices

### 1. Use Cursor Pagination

Always use cursor-based pagination for listing endpoints to ensure stable results during real-time updates.

### 2. Handle SSE Properly

For AI streaming endpoints, use proper EventSource handling:

```javascript
const eventSource = new EventSource('/api/v1/ai/ghost-text', {
  headers: { 'Authorization': `Bearer ${token}` }
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle streaming token
};

eventSource.onerror = () => {
  eventSource.close();
  // Implement reconnection logic
};
```

### 3. Implement Optimistic Updates

For better UX, implement optimistic updates with rollback:

```javascript
// Optimistically update UI
updateLocalState(newData);

try {
  await api.updateIssue(id, newData);
} catch (error) {
  // Rollback on failure
  rollbackLocalState(previousData);
  showError(error);
}
```

### 4. Cache API Keys Validation

When configuring BYOK keys, cache validation results to avoid repeated validation calls.

---

## Related Documentation

- [Authentication Guide](./authentication-guide.md) - Detailed auth flows
- [AI Endpoints Guide](./ai-endpoints-guide.md) - AI feature details
- [Webhook Contracts](./webhook-contracts.md) - Webhook specifications
- [Error Catalog](./error-catalog.md) - Complete error reference
