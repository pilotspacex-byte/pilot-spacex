# API v1 Router Details

**Parent**: [`../README.md`](../README.md) (API Layer)

---

## Router Organization (20 Routers)

### Core Resource Routers (7)

#### 1. workspaces.py — `/api/v1/workspaces`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List user's workspaces (paginated) |
| `/` | POST | Create new workspace (user becomes owner) |
| `/{id}` | GET | Get workspace details |
| `/{id}` | PATCH | Update workspace (name, description) |
| `/{id}` | DELETE | Soft-delete workspace |

#### 2. workspace_members.py — `/api/v1/workspaces/{workspace_id}/members`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List workspace members |
| `/{user_id}` | PATCH | Update member role |
| `/{user_id}` | DELETE | Remove member |

#### 3. workspace_invitations.py — `/api/v1/workspaces/{workspace_id}/invitations`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List pending invitations |
| `/` | POST | Send invitation to email |
| `/{token}` | POST | Accept invitation |
| `/{id}` | DELETE | Revoke invitation |

#### 4. projects.py — `/api/v1/workspaces/{workspace_id}/projects`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List projects in workspace |
| `/` | POST | Create project |
| `/{id}` | GET | Get project details |
| `/{id}` | PATCH | Update project |
| `/{id}` | DELETE | Delete project (soft) |

#### 5. issues.py — `/api/v1/issues`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Create issue (optional AI enhancement) |
| `/` | GET | Search issues (filters, pagination) |
| `/{id}` | GET | Get issue details |
| `/{id}` | PATCH | Update issue (state, assignee, etc.) |
| `/{id}` | DELETE | Delete issue |
| `/{id}/activities` | GET | Get activity timeline |
| `/{id}/comments` | POST | Add comment |

#### 6. workspace_notes.py — `/api/v1/workspaces/{workspace_id}/notes`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List notes (paginated) |
| `/` | POST | Create note with TipTap blocks |
| `/{id}` | GET | Get note + blocks + metadata |
| `/{id}` | PATCH | Update note blocks/metadata |
| `/{id}` | DELETE | Delete note (soft) |
| `/{id}/pin` | POST | Pin to home |
| `/{id}/unpin` | POST | Unpin |

#### 7. workspace_cycles.py — `/api/v1/workspaces/{workspace_id}/cycles`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List cycles in workspace |
| `/` | POST | Create cycle (sprint) |
| `/{id}` | GET | Get cycle details + velocity metrics |
| `/{id}` | PATCH | Update cycle (dates, name) |
| `/{id}/rollover` | POST | Complete cycle, carry-over issues |

---

### AI Feature Routers (10)

#### 8. ai_chat.py — `/api/v1/ai/chat`

Unified PilotSpaceAgent orchestrator.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Start/continue chat (SSE or queue job ID) |
| `/chat/stream/{job_id}` | GET | SSE stream (queue mode) |
| `/chat/abort` | POST | Abort in-flight chat |
| `/chat/answer` | POST | Answer AI clarifying question |

**Request**: ChatRequest(message, session_id, fork_session_id, context: ChatContext)
**Response**: SSE events (message_start, text_delta, tool_use, tool_result, task_progress, approval_request, content_update, message_stop, error)

#### 9. ghost_text.py — `/api/v1/ghost-text`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Get inline completion (SSE, max 50 tokens, <1.5s) |

Provider: Gemini Flash. SLA: <2.5s total.

#### 10. ai_costs.py — `/api/v1/ai/costs`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Cost summary (total, by model, by month) |
| `/usage` | GET | Detailed token records (paginated) |
| `/budget` | PATCH | Set monthly budget cap |
| `/export` | GET | Export as CSV |

#### 11. ai_approvals.py — `/api/v1/ai/approvals`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List pending approvals |
| `/{id}` | GET | Get approval details |
| `/{id}/approve` | POST | Approve (with edits) |
| `/{id}/deny` | POST | Reject |
| `/{id}/permissions/{action}` | PATCH | Configure rules |

#### 12. ai_configuration.py — `/api/v1/ai/configuration`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Get workspace AI config |
| `/` | PATCH | Update preferences (approval, budget) |
| `/providers` | GET | List configured providers |
| `/providers/{provider}` | PATCH | Update API key (Supabase Vault encrypted) |

#### 13. ai_sessions.py — `/api/v1/ai/sessions`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List user's sessions |
| `/{session_id}` | GET | Get session + metadata |
| `/{session_id}/messages` | GET | Get paginated messages |
| `/{session_id}` | DELETE | Delete (soft) |

#### 14. ai_extraction.py — `/api/v1/ai/extraction`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Extract issues from text/note block |

Invokes `extract-issues` skill, creates issues with NoteIssueLink.

#### 15-17. ai_annotations.py, notes_ai.py, ai_context.py / workspace_notes_ai.py

Legacy/specialized AI endpoints for margin annotations, note-specific ghost text, and context generation.

---

### Support Routers (3+)

#### 18. auth.py — `/api/v1/auth`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/login` | POST | OAuth login (Supabase flow) |
| `/callback` | GET | OAuth callback handler |
| `/refresh` | POST | Refresh expired JWT |
| `/logout` | POST | Logout |
| `/profile` | GET | Get current user profile |

#### 19. integrations.py — `/api/v1/integrations`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/github/connect` | POST | Connect GitHub account |
| `/github/disconnect` | POST | Disconnect GitHub |
| `/slack/connect` | POST | Connect Slack workspace |
| `/slack/disconnect` | POST | Disconnect Slack |

#### 20. webhooks.py — `/api/v1/webhooks`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/github` | POST | GitHub webhook handler (PR events) |
| `/slack` | POST | Slack event handler |

Signature verification: GitHub uses X-Hub-Signature-256 HMAC-SHA256.

#### Other Support Routers

- `homepage.py` -- Activity feed, digest, onboarding
- `skills.py` -- Skill discovery (`.claude/skills/`)
- `role_skills.py` -- User role/skill assignments
- `mcp_tools.py` -- MCP tool registry, direct execution
- `debug.py` -- Mock generator (dev only)

---

## Middleware

| Middleware | File | Purpose |
|-----------|------|---------|
| RequestContext | `middleware/request_context.py` | Extract X-Workspace-ID, X-Correlation-ID headers |
| Auth | `middleware/auth_middleware.py` | Validate JWT, extract user claims, skip public routes |
| Error Handler | `middleware/error_handler.py` | Convert exceptions to RFC 7807 |
| Rate Limiter | `middleware/rate_limiter.py` | 1000 req/min standard, 100 req/min AI |
| CORS | `middleware/cors.py` | Origin allowlisting, credentials |

---

## Common Patterns

Router patterns (list with pagination, create resource, SSE streaming, update, delete) follow standard FastAPI conventions. See actual router files for implementation:

- **Pagination**: Cursor-based via `PaginationParams` + `PaginatedResponse[T]`. Cursors are opaque base64-encoded strings.
- **Field Nulling**: `clear_*` boolean flags distinguish "don't update" from "clear field". See `schemas/issue.py:IssueUpdateRequest`.
- **Nested Relations**: Responses include both FK IDs (for mutations) and nested objects (for display). See `schemas/issue.py:IssueResponse`.

---

## Related Documentation

- **Parent API Layer**: [`../README.md`](../README.md)
- **Schemas**: [`schemas/README.md`](schemas/README.md)
- **Application Services**: [`../../application/README.md`](../../application/README.md)
