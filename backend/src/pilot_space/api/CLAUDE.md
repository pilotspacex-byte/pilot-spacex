# API Layer Documentation - Pilot Space

**For backend architecture context, see `/backend/CLAUDE.md`**

---

## Quick Reference

### API Base Path
```
/api/v1/
```

### Middleware Pipeline
```
RequestContextMiddleware (extract headers)
  ↓
CORSMiddleware (allow origins)
  ↓
ExceptionHandler (RFC 7807)
  ↓
RateLimiter (1000 req/min, 100 req/min AI)
  ↓
AuthMiddleware (JWT validation)
  ↓
Router Endpoint
```

### Router Count: 20 Active

| Category | Routers | Endpoints |
|----------|---------|-----------|
| **Core Resources** | 7 | 35+ |
| **AI Features** | 10 | 40+ |
| **Support** | 3+ | 15+ |

### Key Constants

| Setting | Value |
|---------|-------|
| API version | v1 |
| Pagination default limit | 20 (1-100) |
| AI rate limit | 100 req/min (vs 1000 standard) |
| Max text field length | 10,000 chars |
| Issue name max | 255 chars |
| Token validation | Supabase JWT |

---

## Architecture Overview

### Request Lifecycle

```
1. Client Request (HTTP/SSE)
   └─ Headers: Authorization: Bearer <jwt>, X-Workspace-ID: <uuid>

2. RequestContextMiddleware
   └─ Extract workspace_id, correlation_id from headers
   └─ Store in request.state

3. AuthMiddleware
   └─ Validate JWT token via SupabaseAuth
   └─ Extract user_id, workspace_ids from token payload
   └─ Store user in request.state
   └─ Skip for public routes (/health, /docs, /login)

4. Router Endpoint Handler
   └─ Dependency injection (services, repos, DB session)
   └─ Validate request schema (Pydantic v2)
   └─ Call service layer (CQRS-lite pattern)
   └─ Return response schema (camelCase JSON)

5. Exception Handler (middleware)
   └─ Convert Python exceptions to RFC 7807
   └─ Return application/problem+json

6. Response
   └─ JSON (standard endpoints)
   └─ SSE (streaming endpoints: /chat, /ghost-text, etc.)
```

### Key Components

**Location**: `/backend/src/pilot_space/api/`

```
api/
├─ middleware/                    # Request processing pipeline
│  ├─ error_handler.py           # RFC 7807 Problem Details
│  ├─ auth_middleware.py         # JWT validation
│  ├─ request_context.py         # Workspace/correlation ID extraction
│  ├─ rate_limiter.py            # Rate limiting (1000 std, 100 AI)
│  └─ cors.py                    # CORS configuration
├─ v1/
│  ├─ routers/                   # 20 domain routers
│  │  ├─ Core: issues.py, workspace_notes.py, projects.py, workspaces.py, etc.
│  │  └─ AI: ai_chat.py, ghost_text.py, ai_costs.py, ai_approvals.py, etc.
│  ├─ schemas/                   # Pydantic v2 request/response models
│  │  ├─ base.py                 # BaseSchema, PaginatedResponse, ErrorResponse
│  │  ├─ issue.py                # IssueCreateRequest, IssueResponse
│  │  ├─ note.py                 # NoteCreateRequest, NoteDetailResponse
│  │  └─ ... (13 schema modules)
│  ├─ middleware/
│  │  └─ ai_context.py           # AI context extraction from notes/issues
│  └─ streaming.py               # SSE event definitions
└─ utils/
   └─ sse.py                     # SSE utility functions
```

---

## Middleware Stack

### 1. RequestContextMiddleware

**Purpose**: Extract workspace_id and correlation_id from headers.

**Location**: `/backend/src/pilot_space/api/middleware/request_context.py`

**Behavior**: Extracts `X-Workspace-ID` and `X-Correlation-ID` headers, stores in `request.state`

**Usage**: `workspace_id: WorkspaceId, correlation_id: CorrelationId` (type aliases for auto-injection)

### 2. AuthMiddleware

**Purpose**: Validate JWT tokens from Supabase Auth.

**Location**: `/backend/src/pilot_space/api/middleware/auth_middleware.py`

**Behavior**: Validates Bearer token, extracts user_id/workspace_ids, stores in `request.state.user`. Skips public routes (/health, /docs, /login, /callback, /refresh)

**Token Claims**: user_id, email, workspace_ids, role_in_workspace (dict), is_email_verified

### 3. Error Handler

**Purpose**: Convert all exceptions to RFC 7807 Problem Details.

**Location**: `/backend/src/pilot_space/api/middleware/error_handler.py`

**Response Format**: `{"type": "...", "title": "...", "status": 400, "detail": "...", "instance": "/api/v1/..."}`

**Handled Types**: HTTPException (400/401/403/404/422/429/500), ValidationError (Pydantic), generic exceptions (500)

**Usage**: Raise `HTTPException(status_code=..., detail="...")` — middleware auto-wraps in RFC 7807

### 4. Rate Limiter

**Purpose**: Limit API abuse.

**Location**: `/backend/src/pilot_space/api/middleware/rate_limiter.py`

**Limits**: Standard 1000 req/min per user; AI endpoints 100 req/min (includes `/ai/*` routes)

**Response**: RFC 7807 with 429 status + retry-after guidance

### 5. CORS Middleware

**Purpose**: Enable cross-origin requests from frontend.

**Location**: `/backend/src/pilot_space/api/middleware/cors.py`

**Configuration**: Localhost 3000 for dev; configured via env var for production. Allows credentials, all methods/headers.

---

## Schema Design (Pydantic v2)

### Base Classes

**Location**: `/backend/src/pilot_space/api/v1/schemas/base.py`

All schemas inherit `BaseSchema` (ConfigDict: from_attributes=True, alias_generator=to_camel for camelCase JSON)

**Hierarchy**: BaseSchema → TimestampSchema, EntitySchema, SoftDeleteSchema, PaginationParams, PaginatedResponse[T], ErrorResponse, DeleteResponse, BulkResponse[T]

### Request Schemas

Validate at API boundary with Field constraints (min_length, max_length, etc.). Pydantic auto-validates on instantiation.

```python
class IssueCreateRequest(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    priority: IssuePriority = IssuePriority.NONE
    project_id: UUID
```

### Response Schemas

Include factory method for ORM → response mapping:

```python
class IssueResponse(BaseSchema):
    id: UUID
    name: str
    project: ProjectBriefSchema  # Nested
    state: StateBriefSchema

    @classmethod
    def from_issue(cls, issue: Issue) -> IssueResponse:
        return cls(id=issue.id, name=issue.name, ...)
```

### Pagination Response

`PaginatedResponse[T]`: items, total, next_cursor (base64), prev_cursor, has_next, has_prev, page_size

---

## Authentication & Authorization

### JWT Token Validation

**Token Source**: Supabase Auth (GoTrue)

**Flow**: Client sends `Authorization: Bearer <jwt>` → AuthMiddleware extracts → SupabaseAuth validates signature/expiry → Extracts user_id, email, workspace_ids, role_in_workspace

**Token Claims**: sub (user_id), email, workspace_ids, role_in_workspace (dict), iat, exp

### Authorization Checks

**Workspace Membership**: Every endpoint queries WorkspaceMember to verify user belongs to workspace

**Role-Based**: Some operations check role (owner/admin/member). Raise 403 if insufficient permissions.

---

## Router Organization (20 Routers)

### Core Resource Routers (CRUD)

#### 1. workspaces.py
**Prefix**: `/api/v1/workspaces`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List user's workspaces (paginated) |
| `/` | POST | Create new workspace (user becomes owner) |
| `/{id}` | GET | Get workspace details |
| `/{id}` | PATCH | Update workspace (name, description) |
| `/{id}` | DELETE | Soft-delete workspace |

**Example: Create Workspace**
```python
@router.post("", response_model=WorkspaceDetailResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceDetailResponse:
    """Create new workspace (POST /api/v1/workspaces)"""
    service = CreateWorkspaceService(...)
    result = await service.execute(
        CreateWorkspacePayload(
            name=request.name,
            owner_id=current_user.id,
        )
    )
    return WorkspaceDetailResponse.from_domain(result.workspace)
```

#### 2. workspace_members.py
**Prefix**: `/api/v1/workspaces/{workspace_id}/members`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List workspace members |
| `/{user_id}` | PATCH | Update member role (owner→admin) |
| `/{user_id}` | DELETE | Remove member |

#### 3. workspace_invitations.py
**Prefix**: `/api/v1/workspaces/{workspace_id}/invitations`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List pending invitations |
| `/` | POST | Send invitation to email |
| `/{token}` | POST | Accept invitation |
| `/{id}` | DELETE | Revoke invitation |

#### 4. projects.py
**Prefix**: `/api/v1/workspaces/{workspace_id}/projects`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List projects in workspace |
| `/` | POST | Create project |
| `/{id}` | GET | Get project details |
| `/{id}` | PATCH | Update project |
| `/{id}` | DELETE | Delete project (soft) |

#### 5. issues.py
**Prefix**: `/api/v1/issues`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Create issue (optional AI enhancement) |
| `/` | GET | Search issues (filters, pagination) |
| `/{id}` | GET | Get issue details |
| `/{id}` | PATCH | Update issue (state, assignee, etc.) |
| `/{id}` | DELETE | Delete issue |
| `/{id}/activities` | GET | Get activity timeline |
| `/{id}/comments` | POST | Add comment |

#### 6. workspace_notes.py
**Prefix**: `/api/v1/workspaces/{workspace_id}/notes`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List notes (paginated) |
| `/` | POST | Create note with TipTap blocks |
| `/{id}` | GET | Get note + blocks + metadata |
| `/{id}` | PATCH | Update note blocks/metadata |
| `/{id}` | DELETE | Delete note (soft) |
| `/{id}/pin` | POST | Pin to home |
| `/{id}/unpin` | POST | Unpin |

**Block Structure**: TipTap JSON format (paragraph, heading, etc.)

#### 7. workspace_cycles.py
**Prefix**: `/api/v1/workspaces/{workspace_id}/cycles`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List cycles in workspace |
| `/` | POST | Create cycle (sprint) |
| `/{id}` | GET | Get cycle details + velocity metrics |
| `/{id}` | PATCH | Update cycle (dates, name) |
| `/{id}/rollover` | POST | Complete cycle, carry-over issues |

---

### AI Feature Routers (Streaming)

#### 8. ai_chat.py
**Prefix**: `/api/v1/ai/chat`

**Purpose**: Unified conversational AI (PilotSpaceAgent orchestrator)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat` | POST | Start/continue chat (SSE or queue job ID) |
| `/chat/stream/{job_id}` | GET | SSE stream (queue mode) |
| `/chat/abort` | POST | Abort in-flight chat |
| `/chat/answer` | POST | Answer AI clarifying question |

**Request**: ChatRequest(message, session_id, fork_session_id, context: ChatContext)

**Response**: SSE events (message_start, text_delta, tool_use, tool_result, task_progress, approval_request, content_update, message_stop, error) or queue job_id/stream_url

**Auth**: Bearer token via query param for SSE (cookies may not work on GET)

#### 9. ghost_text.py
**Prefix**: `/api/v1/ghost-text`

**Purpose**: Latency-critical inline completions (<2.5s SLA, independent agent)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Get inline completion (SSE, max 50 tokens, <1.5s) |

**Provider**: Google Gemini Flash (cost-optimized)

#### 10. ai_costs.py
**Prefix**: `/api/v1/ai/costs`

**Purpose**: Track AI token usage + costs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Cost summary (total, by model, by month) |
| `/usage` | GET | Detailed token records (paginated) |
| `/budget` | PATCH | Set monthly budget cap |
| `/export` | GET | Export as CSV |

#### 11. ai_approvals.py
**Prefix**: `/api/v1/ai/approvals`

**Purpose**: Human-in-the-loop approval (DD-003)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List pending approvals |
| `/{id}` | GET | Get approval details |
| `/{id}/approve` | POST | Approve (with edits) |
| `/{id}/deny` | POST | Reject |
| `/{id}/permissions/{action}` | PATCH | Configure rules |

**Categories**: Non-destructive (auto), content creation (configurable), destructive (always)

#### 12. ai_configuration.py
**Prefix**: `/api/v1/ai/configuration`

**Purpose**: Manage AI settings + API keys

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Get workspace AI config |
| `/` | PATCH | Update preferences (approval, budget) |
| `/providers` | GET | List configured providers |
| `/providers/{provider}` | PATCH | Update API key (encrypted via Supabase Vault) |

#### 13. ai_sessions.py
**Prefix**: `/api/v1/ai/sessions`

**Purpose**: Manage AI chat session history

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | List user's sessions |
| `/{session_id}` | GET | Get session + metadata |
| `/{session_id}/messages` | GET | Get paginated messages |
| `/{session_id}` | DELETE | Delete (soft) |

#### 14. ai_extraction.py
**Prefix**: `/api/v1/ai/extraction`

**Purpose**: Extract issues from notes (skill invocation).

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | POST | Extract issues from text/note block |

**Invokes**: `extract-issues` skill → creates issues with NoteIssueLink

#### 15. ai_annotations.py
**Prefix**: `/api/v1/ai/annotations` (Legacy, being migrated)

**Purpose**: Margin annotations (AI margin suggestions).

#### 16. notes_ai.py
**Prefix**: `/api/v1/ghost-text` (Note-specific)

**Purpose**: Ghost text for note editor (similar to ghost_text.py but note context).

---

### Support Routers

#### 17. auth.py
**Prefix**: `/api/v1/auth`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/login` | POST | OAuth login (Supabase flow) |
| `/callback` | GET | OAuth callback handler |
| `/refresh` | POST | Refresh expired JWT |
| `/logout` | POST | Logout (client clears token) |
| `/profile` | GET | Get current user profile |

#### 18. integrations.py
**Prefix**: `/api/v1/integrations`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/github/connect` | POST | Connect GitHub account |
| `/github/disconnect` | POST | Disconnect GitHub |
| `/slack/connect` | POST | Connect Slack workspace |
| `/slack/disconnect` | POST | Disconnect Slack |

#### 19. webhooks.py
**Prefix**: `/api/v1/webhooks`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/github` | POST | GitHub webhook handler (PR events) |
| `/slack` | POST | Slack event handler |

**Signature Verification**: GitHub uses X-Hub-Signature-256 HMAC-SHA256 header

#### 20. Other Support Routers
- `homepage.py` — Activity feed, digest, onboarding upsell
- `skills.py` — Skill discovery (list available `.claude/skills/`)
- `role_skills.py` — User role/skill assignments
- `mcp_tools.py` — MCP tool registry, direct execution
- `debug.py` — Mock generator (dev only)

---

## Dependency Injection Pattern

**Location**: `/backend/src/pilot_space/dependencies/` (auth.py, services.py, ai.py, workspace.py)

**Pattern**: FastAPI Depends() with type aliases for auto-injection

**Key Dependencies**:

1. **DbSession**: `Annotated[AsyncSession, Depends(get_session)]` — Fresh DB session per request
2. **CurrentUserId**: `Annotated[UUID, Depends(get_current_user_id)]` — From request.state.user (set by AuthMiddleware)
3. **WorkspaceId**: `Annotated[UUID, Depends(get_workspace_id)]` — From X-Workspace-ID header
4. **Service Factories**: `Annotated[CreateIssueService, Depends(get_create_issue_service)]` — Fully-wired with repos
5. **AI Agent**: `Annotated[PilotSpaceAgent, Depends(get_pilotspace_agent)]` — Singleton orchestrator

**Usage**: Declare in endpoint signature, FastAPI auto-injects on request

```python
@router.post("/issues")
async def create_issue(
    request: IssueCreateRequest,
    service: CreateIssueServiceDep,  # Auto-injected
    user_id: CurrentUserId,
):
    result = await service.execute(CreateIssuePayload(...))
```

---

## Common Router Patterns

### Pattern 1: List with Pagination

```python
@router.get("/issues")
async def list_issues(
    workspace_id: WorkspaceId,
    page_size: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> PaginatedResponse[IssueResponse]:
    service = ListIssuesService(...)
    page = await service.execute(ListIssuesPayload(..., limit=page_size))
    return PaginatedResponse(items=[...], total=page.total, next_cursor=page.next_cursor, ...)
```

### Pattern 2: Create Resource

```python
@router.post("", status_code=201)
async def create_issue(
    request: IssueCreateRequest,
    service: CreateIssueServiceDep,
    user_id: CurrentUserId,
) -> IssueResponse:
    result = await service.execute(CreateIssuePayload(..., reporter_id=user_id))
    return IssueResponse.from_issue(result.issue)
```

### Pattern 3: Streaming Response (SSE)

```python
@router.post("/chat")
async def chat(request: ChatRequest, agent: PilotSpaceAgentDep) -> StreamingResponse:
    async def event_generator():
        async for event in agent.stream(ChatInput(...)):
            yield f"data: {event.model_dump_json()}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Pattern 4: Update Resource

```python
@router.patch("/{id}")
async def update_issue(id: UUID, request: IssueUpdateRequest, service: UpdateIssueServiceDep) -> IssueResponse:
    result = await service.execute(UpdateIssuePayload(id=id, ...))
    return IssueResponse.from_issue(result.issue)
```

### Pattern 5: Delete Resource

```python
@router.delete("/{id}")
async def delete_issue(id: UUID, service: DeleteIssueServiceDep) -> DeleteResponse:
    await service.execute(DeleteIssuePayload(id=id, ...))
    return DeleteResponse(id=id)
```

---

## Common API Patterns

### Explicit Field Nulling

**Problem**: Distinguish "don't change" (null) vs "clear field" (explicit).

**Solution**: Use `clear_*` boolean flags in request:

```python
class IssueUpdateRequest(BaseSchema):
    name: str | None = None              # null = don't update
    assignee_id: UUID | None = None
    clear_assignee: bool = False         # true = set to NULL
    clear_cycle: bool = False
```

### Nested Relations in Responses

Include both nested objects (for display) and foreign key IDs (for mutations):

```python
class IssueResponse(BaseSchema):
    id: UUID
    project: ProjectBriefSchema  # Display
    project_id: UUID             # For updates
    assignee: UserBriefSchema | None
    assignee_id: UUID | None
```

### Pagination Cursor Format

Cursors are base64-encoded and opaque (prevents client manipulation):

```
next_cursor = base64.b64encode("2024-02-10-p1.i.3".encode()).decode()
# → "MjAyNC0wMi0xMC1wMS5pLjM="
```

---

## Error Handling

### RFC 7807 Problem Details

All errors return RFC 7807 format: `{"type": "https://httpstatuses.com/400", "title": "...", "status": 400, "detail": "...", "instance": "..."}`

### Status Codes

| Code | Meaning | When to Use |
|------|---------|------------|
| 400 | Bad Request | Validation failures |
| 401 | Unauthorized | Missing/expired JWT |
| 403 | Forbidden | User not authorized for resource |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Pydantic validation errors (includes field details) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unhandled exceptions |

**Usage**: `raise HTTPException(status_code=401, detail="Token has expired")` — middleware auto-wraps in RFC 7807

---

## Example: Create Issue

**Request** (POST /api/v1/issues):
```json
{"name": "Fix login bug", "projectId": "...", "priority": "high", "enhanceWithAi": true}
```

**Response** (201):
```json
{"id": "...", "sequenceId": 42, "name": "Fix login bug", "project": {...}, "state": {...}, ...}
```

---

## Generation Metadata

**Documentation Generated**: 2026-02-10

**Scope**: 20 FastAPI routers, middleware stack, schema design, DI pattern, authentication

**Key Files Analyzed**:
- `backend/src/pilot_space/main.py` — FastAPI app setup, router mounting
- `backend/src/pilot_space/api/middleware/` — 5 middleware modules
- `backend/src/pilot_space/api/v1/routers/` — 20 router modules
- `backend/src/pilot_space/api/v1/schemas/` — 13 schema modules
- `backend/src/pilot_space/dependencies/` — 5 dependency modules

**Patterns Documented**:
- CQRS-lite request/response flow
- RFC 7807 error handling
- Pydantic v2 schema validation
- Dependency injection (Depends, type aliases)
- JWT authentication + authorization
- RLS context setting
- SSE streaming (chat, ghost text)
- Cursor-based pagination
- Explicit field nulling (clear_* pattern)
- Nested relations in responses

**Coverage**:
- All 20 routers categorized and documented
- Complete middleware pipeline explained
- DI pattern with code examples
- 5 common router patterns shown
- Error handling per HTTP status code
- Real request/response examples

**Missing / Deferred**:
- Rate limiter implementation details (module not analyzed)
- WebSocket support (no WebSocket endpoints in current implementation)
- GraphQL layer (REST-only API)
- OpenAPI schema customization (auto-generated from docstrings)
- API versioning strategy for future v2 API
