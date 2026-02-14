# API Layer - Pilot Space

**Parent**: `/backend/CLAUDE.md` | **Base Path**: `/api/v1/`

---

## Submodule Documentation

| Module | Doc | Covers |
|--------|-----|--------|
| **Router Details** | [`v1/CLAUDE.md`](v1/CLAUDE.md) | All 20 router endpoints, middleware deep-dives, common patterns, API conventions |

---

## Middleware Pipeline

```
RequestContextMiddleware (extract workspace_id, correlation_id)
  |
CORSMiddleware (allow origins)
  |
ExceptionHandler (RFC 7807 Problem Details)
  |
RateLimiter (1000 req/min standard, 100 req/min AI)
  |
AuthMiddleware (JWT validation via Supabase Auth)
  |
Router Endpoint
```

## Key Constants

| Setting | Value |
|---------|-------|
| Pagination default limit | 20 (range: 1-100) |
| AI rate limit | 100 req/min |
| Max text field length | 10,000 chars |
| Issue name max | 255 chars |

---

## Architecture

### Directory Structure

```
api/
├── middleware/                    # Request processing pipeline
│   ├── error_handler.py           # RFC 7807 Problem Details
│   ├── auth_middleware.py         # JWT validation
│   ├── request_context.py         # Workspace/correlation ID extraction
│   ├── rate_limiter.py            # Rate limiting
│   └── cors.py                    # CORS configuration
├── v1/
│   ├── routers/                   # 20 domain routers
│   ├── schemas/                   # Pydantic v2 request/response models
│   ├── dependencies.py            # Service/repository DI type aliases
│   ├── middleware/
│   │   └── ai_context.py
│   ├── streaming.py               # SSE event definitions
│   └── CLAUDE.md                  # Router details
└── utils/
    └── sse.py                     # SSE utility functions
```

### Request Lifecycle

```
1. Client Request (HTTP/SSE)
   Headers: Authorization: Bearer <jwt>, X-Workspace-ID: <uuid>
2. RequestContextMiddleware -> Store workspace_id, correlation_id in request.state
3. AuthMiddleware -> Validate JWT, extract user_id/workspace_ids (skip public routes)
4. Router Handler -> DI injection, Pydantic validation, service call, response schema
5. ExceptionHandler -> Convert exceptions to RFC 7807
6. Response -> JSON (standard) or SSE (streaming)
```

---

## Authentication & Authorization

**Token Source**: Supabase Auth (GoTrue)

**Flow**: `Authorization: Bearer <jwt>` -> AuthMiddleware validates signature/expiry -> Extracts user_id, email, workspace_ids, role_in_workspace

**Workspace Membership**: Every endpoint verifies user belongs to workspace. Role-based checks (owner/admin/member) raise 403 if insufficient.

---

## Router Overview

**Core Resources** (7 routers, 35+ endpoints): workspaces, workspace_members, workspace_invitations, projects, issues, workspace_notes, workspace_cycles

**AI Features** (10 routers, 40+ endpoints): ai_chat, ghost_text, ai_costs, ai_approvals, ai_configuration, ai_sessions, ai_extraction, ai_annotations, notes_ai, ai_context

**Support** (3+ routers, 15+ endpoints): auth, integrations, webhooks, homepage, skills, role_skills, mcp_tools, debug

See [`v1/CLAUDE.md`](v1/CLAUDE.md) for individual endpoint tables.

---

## Dependency Injection

**Configuration**: `container.py` (DI container DSL) + `api/v1/dependencies.py` (type aliases)

### Key Patterns

- **SessionDep**: Triggers ContextVar session context. See `dependencies/auth.py`.
- **Service injection**: Use type aliases from `api/v1/dependencies.py` (e.g., `CreateIssueServiceDep`). Requires `@inject` decorator.
- **Repository injection**: Use repository type aliases (e.g., `ProjectRepositoryDep`). Requires `@inject` decorator.
- **When to skip @inject**: Endpoints using only `SessionDep`, `CurrentUser`, `WorkspaceId`, or FastAPI parameter functions.
- **Type alias inventory**: 35 services + 9 repositories. See `api/v1/dependencies.py`.
- **Test overrides**: Use `app.dependency_overrides[Container.service_name]`. See `api/v1/dependencies.py` for names.

---

## Error Handling (RFC 7807)

All errors return: `{"type": "...", "title": "...", "status": N, "detail": "...", "instance": "..."}`

| Code | When |
|------|------|
| 400 | Validation failures |
| 401 | Missing/expired JWT |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 422 | Pydantic validation errors (includes field details) |
| 429 | Rate limit exceeded |
| 500 | Unhandled exceptions |

---

## Schema Design (Pydantic v2)

**Base**: `BaseSchema` with `ConfigDict(from_attributes=True, alias_generator=to_camel)` for camelCase JSON.

**Hierarchy**: BaseSchema -> TimestampSchema, EntitySchema, SoftDeleteSchema, PaginationParams, PaginatedResponse[T], ErrorResponse, DeleteResponse, BulkResponse[T]

**Request schemas**: Validate at API boundary with `Field` constraints. See `api/v1/schemas/`.

**Response schemas**: Include `from_{entity}()` factory methods for ORM -> response mapping. See `api/v1/schemas/`.

---

## Related Documentation

- **Router Details (all 20 routers)**: [`v1/CLAUDE.md`](v1/CLAUDE.md)
- **Backend Architecture**: `/backend/CLAUDE.md`
- **Application Services**: [`../application/CLAUDE.md`](../application/CLAUDE.md)
- **Infrastructure/Repos**: [`../infrastructure/CLAUDE.md`](../infrastructure/CLAUDE.md)
