# Pydantic v2 Schemas Documentation - Pilot Space

**Generated**: 2026-02-10

**Scope**: All request/response schemas in `/backend/src/pilot_space/api/v1/schemas/`

**Location**: `/backend/src/pilot_space/api/v1/schemas/` (13 schema modules)

**Language**: Python 3.12+ with Pydantic v2.6+

---

## Quick Reference

### Schema Inheritance Hierarchy

```
BaseSchema (root - camelCase JSON, populate_by_name=True)
├─ TimestampSchema (created_at, updated_at)
├─ EntitySchema (id + timestamps)
├─ SoftDeleteSchema (id + timestamps + is_deleted, deleted_at)
├─ PaginationParams (cursor-based pagination params)
├─ PaginatedResponse[T] (paginated list response)
├─ ErrorResponse (RFC 7807 Problem Details)
├─ SuccessResponse (simple success flag)
├─ DeleteResponse (id + success flag)
├─ BulkResponse[T] (bulk operation results)
├─ HealthResponse (health check)
└─ All domain-specific schemas inherit from BaseSchema or EntitySchema
```

### 13 Schema Modules

| Module | Exports | Purpose |
|--------|---------|---------|
| **base.py** | BaseSchema, EntitySchema, PaginatedResponse, ErrorResponse, etc. | Core schema classes and pagination |
| **auth.py** | LoginRequest, TokenResponse, UserProfileResponse | Authentication flows |
| **workspace.py** | WorkspaceCreate, WorkspaceDetailResponse, WorkspaceMemberResponse | Workspace CRUD + members |
| **project.py** | ProjectCreate, ProjectResponse, StateResponse | Project CRUD + state definitions |
| **issue.py** | IssueCreateRequest, IssueResponse, UserBriefSchema, StateBriefSchema | Issues with AI metadata |
| **note.py** | NoteCreate, NoteResponse, TipTapContentSchema, NoteBlockSchema | Notes with TipTap content |
| **cycle.py** | CycleCreateRequest, CycleResponse, CycleMetricsResponse, BurndownChartResponse | Cycles/sprints + velocity metrics |
| **annotation.py** | AnnotationCreate, AnnotationResponse, AnnotationType, AnnotationStatus | Note margin annotations |
| **discussion.py** | CommentCreate, CommentResponse, DiscussionStatus | Threaded discussions |
| **approval.py** | ApprovalRequestResponse, ApprovalDetailResponse, ApprovalStatus | Human-in-the-loop approvals (DD-003) |
| **cost.py** | CostSummaryResponse, CostByAgent, CostTrendsResponse | AI cost tracking and analytics |
| **ai_context.py** | GenerateContextRequest, AIContextResponse, RelatedItemResponse, TaskItemResponse | Issue AI context generation |
| **ai_configuration.py** | AIConfigurationResponse, AIConfigurationCreate, AIConfigurationUpdate | LLM provider configuration |

---

## Base Schema Architecture

### BaseSchema (Root Configuration)

**Location**: `base.py` (lines 18-29)

All schemas inherit from `BaseSchema`: `from_attributes=True` (ORM mapping), `populate_by_name=True` (accept both camelCase/snake_case input), `alias_generator=to_camel` (output camelCase JSON).

**Behavior**: Input accepts both formats. Output returns camelCase. ORM mapping via `.model_validate(orm_object)`.

**TimestampSchema**: Adds `created_at`, `updated_at` (datetime). Used by all domain entity responses.

**EntitySchema**: Extends TimestampSchema. Adds `id: UUID`. Used by all response schemas.

**SoftDeleteSchema**: Extends EntitySchema. Adds `is_deleted: bool`, `deleted_at: datetime | None`. Used for soft-deletable resources.

---

## Pagination Schemas

### Pagination Schemas

**PaginationParams**: cursor, page_size (default 20, range 1-100), sort_by (default "created_at"), sort_order (default "desc", pattern "^(asc|desc)$")

**PaginatedResponse[T]**: items, total, next_cursor, prev_cursor, has_next, has_prev, page_size. Example: `{"items": [...], "total": 145, "nextCursor": "base64...", "hasNext": true, "pageSize": 20}`

---

## Error Response Schemas

### Error & Success Responses

**ErrorResponse** (RFC 7807): type, title, status, detail, instance, errors (validation). Example: `{"type": "https://httpstatuses.com/400", "title": "Bad Request", "status": 400, "detail": "Invalid cursor format"}`

**SuccessResponse**: success (bool), message (string). Used for non-data responses.

**DeleteResponse** (extends SuccessResponse): Adds `id: UUID` of deleted resource.

---

## Domain Schema Modules

### Issue Schemas (`issue.py`)

**Brief Schemas** (nested in responses): UserBriefSchema (id, email, display_name), StateBriefSchema (id, name, color, group), LabelBriefSchema (id, name, color), ProjectBriefSchema (id, name, identifier)

#### IssueCreateRequest

**Fields**: name (1-255 chars, required), description, description_html, priority (default NONE), state_id, project_id (required), assignee_id, cycle_id, module_id, parent_id (sub-issues), estimate_points (0-100), start_date, target_date (ISO format), label_ids (list), enhance_with_ai (bool, default False)

**Constraints**: name required + non-empty; estimate_points 0-100; UUIDs valid format; dates ISO.

#### IssueUpdateRequest

**Fields**: All IssueCreateRequest fields are optional (null = don't update) + `clear_assignee`, `clear_cycle`, `clear_module`, `clear_parent`, `clear_estimate`, `clear_start_date`, `clear_target_date` (bool flags for explicit nulling)

**Pattern**: `clear_*=true` explicitly clears field (set to NULL); null value means "don't update"; explicit value updates field. Example: `{"clear_assignee": true}` unassigns; `{"name": null}` skips name update; `{"assignee_id": "..."}` assigns.

#### IssueResponse

**Fields**: id, workspace_id, sequence_id, identifier, name, description, priority, estimate_points, start_date, target_date, sort_order, created_at, updated_at (timestamps), project_id, assignee_id, reporter_id, cycle_id, parent_id (foreign keys), project (ProjectBriefSchema), state (StateBriefSchema), assignee (UserBriefSchema | None), reporter (UserBriefSchema), labels (list[LabelBriefSchema]), ai_metadata, has_ai_enhancements, sub_issue_count

**Factory**: `@classmethod from_issue(cls, issue) → IssueResponse` converts domain entity to response schema via `.model_validate()` for nested relations.

### Note Schemas (`note.py`)

**Location**: `backend/src/pilot_space/api/v1/schemas/note.py`

#### TipTap Content Schema

**Fields**: type (default="doc", validated), content (list[dict[str, Any]], document blocks)

**Validator**: type field must equal "doc" (raises ValueError otherwise)

**Structure**: `{"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "..."}]}, ...]}`

### Note Schemas (`note.py`)

**NoteCreate**: project_id (optional), title (1-255 chars), content (TipTapContentSchema | None), is_pinned (bool)

**NoteResponse**: Extends EntitySchema. Fields: project_id, title, is_pinned, word_count, last_edited_by_id. Note: Excludes full content (GET /notes/{id} for full detail).

### Workspace Schemas (`workspace.py`)

**WorkspaceCreate**: name (1-255 chars), slug (pattern: `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$` - lowercase/numbers/hyphens only, no leading/trailing dash), description (0-2000 chars, optional)

**WorkspaceResponse**: Extends EntitySchema. Fields: name, slug, description, owner_id, member_count, project_count

**WorkspaceDetailResponse**: Extends WorkspaceResponse. Adds: settings (JSON, optional), current_user_role

### Cycle Schemas (`cycle.py`)

**CycleCreateRequest**: name (1-255 chars), description, project_id (required), start_date, end_date (ISO), owned_by_id, status (default DRAFT: DRAFT/ACTIVE/COMPLETED/CANCELLED)

**CycleMetricsResponse**: cycle_id, total_issues, completed_issues, in_progress_issues, not_started_issues, total_points (sum), completed_points, completion_percentage (0-100), velocity (points/day)

### Annotation Schemas (`annotation.py`)

**Location**: `backend/src/pilot_space/api/v1/schemas/annotation.py`

#### AnnotationType Enum

Values: SUGGESTION (improvement), WARNING (issue), QUESTION (clarification), INSIGHT (context), REFERENCE (link), ISSUE_CANDIDATE (tracked), INFO (informational)

#### AnnotationCreate

**Fields**: note_id, block_id, type (AnnotationType), content (1-1000 chars), highlight_start (ge=0), highlight_end (ge=0)

**Validator**: highlight_end must be >= highlight_start (raises ValueError if violated)

### Approval Schemas (`approval.py`)

Implements DD-003 human-in-the-loop approval workflow.

#### ApprovalStatus Enum

Values: PENDING (awaiting), APPROVED, REJECTED, EXPIRED (24h TTL)

#### ApprovalRequestResponse (List)

**Fields**: id, agent_name, action_type (e.g., create_issues), status, created_at, expires_at (24h), requested_by, context_preview

#### ApprovalDetailResponse (Detail)

**Fields**: id, agent_name, action_type, status, payload (full action JSON), context (optional), created_at, expires_at, resolved_at, resolved_by, resolution_note

**Approval Categories (DD-003)**:
- **Non-destructive** → Auto-execute, notify (labels, annotations)
- **Content creation** → Require approval if configured (create issues, PR comments)
- **Destructive** → Always require approval (delete issues, merge PRs)

### Cost Schemas (`cost.py`)

**CostByAgent** (frozen=True, strict=True): agent_name, total_cost_usd, request_count, input_tokens, output_tokens

**CostSummaryResponse** (strict=True): workspace_id, period_start, period_end, total_cost_usd, total_requests, total_input_tokens, total_output_tokens, by_agent, by_user, by_day

### AI Context Schemas (`ai_context.py`)

**GenerateContextRequest**: force_regenerate (bool, default False)

**AIContextResponse**: related_items, code_references, implementation_tasks, conversation, metadata (generation timestamp, model, token count)

### AI Configuration Schemas (`ai_configuration.py`)

**AIConfigurationResponse**: workspace_id, approval_mode (auto|require_approval), providers_configured (list[str]), budget_monthly_usd, features_enabled (dict[str, bool])

---

## Field Validation Patterns

### Common Field Constraints

| Field Type | Syntax | Example |
|-----------|--------|---------|
| Required string | `str = Field(..., min_length=1, max_length=N)` | name (1-255 chars) |
| Optional string | `str \| None = Field(None, max_length=N)` | description (0-2000 chars) |
| String pattern | `str = Field(..., pattern=r"^[a-z0-9-]+$")` | slug validation |
| Numeric range | `int = Field(default, ge=min, le=max)` | estimate_points (0-100) |
| Percentage | `float = Field(..., ge=0, le=1)` | completion % |
| Enum | `EnumType = EnumType.DEFAULT` | IssuePriority.NONE |
| UUID foreign key | `UUID` or `UUID \| None = None` | project_id, assignee_id |
| Date/DateTime | `date \| None = None` or `datetime` | ISO format (YYYY-MM-DD, RFC3339) |

### Custom Field Validators

**Pattern**: Use `@field_validator("field_name")` decorator to validate cross-field constraints.

**Examples**:
- Highlight validation (annotation.py): highlight_end >= highlight_start
- TipTap type validation (note.py): type must equal "doc"
- Slug pattern (workspace.py): `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$` (lowercase + hyphens, no leading/trailing dash)

---

## Domain Entity → DTO Mapping Pattern

### from_domain() Class Methods

Response schemas use `@classmethod from_domain(cls, entity)` to convert domain entities to DTOs. Maps nested relations via `.model_validate(relation)` for eager-loaded attributes.

**Pattern**: `ProjectBriefSchema.model_validate(issue.project)` converts SQLAlchemy model to schema.

**Router usage**: `return IssueResponse.from_issue(result.issue)` after service executes.

### Why Both Fields and Relations?

Response schemas include **both** IDs (for mutations) and nested objects (for display):
- `project_id: UUID` — Client updates via PATCH
- `project: ProjectBriefSchema` — Client reads display info

Avoids N+1 queries (via eager loading) and serves both use cases.

---

## Schema Organization by Domain

### 1. Core Infrastructure Schemas

| Module | Schemas | Purpose |
|--------|---------|---------|
| **base.py** | BaseSchema, EntitySchema, PaginatedResponse, ErrorResponse | Foundation classes, pagination, errors |
| **auth.py** | LoginRequest, TokenResponse, UserProfileResponse | Authentication flows |

### 2. Workspace Management Schemas

| Module | Schemas | Purpose |
|--------|---------|---------|
| **workspace.py** | WorkspaceCreate, WorkspaceResponse, WorkspaceMemberResponse, InvitationResponse | Workspace CRUD, members, invitations |
| **project.py** | ProjectCreate, ProjectResponse, StateResponse | Project CRUD, state definitions |

### 3. Issue & Task Schemas

| Module | Schemas | Purpose |
|--------|---------|---------|
| **issue.py** | IssueCreateRequest, IssueResponse, UserBriefSchema, StateBriefSchema | Issues (main work items) with AI metadata |
| **cycle.py** | CycleCreateRequest, CycleResponse, CycleMetricsResponse, BurndownChartResponse | Sprints/cycles, velocity, burndown metrics |

### 4. Collaboration Schemas

| Module | Schemas | Purpose |
|--------|---------|---------|
| **note.py** | NoteCreate, NoteResponse, TipTapContentSchema | Note canvas (Note-First paradigm) |
| **discussion.py** | CommentCreate, CommentResponse, DiscussionStatus | Threaded discussions on notes |
| **annotation.py** | AnnotationCreate, AnnotationResponse, AnnotationType | Margin annotations (AI suggestions) |

### 5. AI/Agent Schemas

| Module | Schemas | Purpose |
|--------|---------|---------|
| **approval.py** | ApprovalRequestResponse, ApprovalDetailResponse, ApprovalStatus | Human-in-the-loop approvals (DD-003) |
| **cost.py** | CostSummaryResponse, CostByAgent, CostTrendsResponse | AI cost tracking (BYOK pricing) |
| **ai_context.py** | GenerateContextRequest, RelatedItemResponse, TaskItemResponse | Issue AI context generation |
| **ai_configuration.py** | AIConfigurationResponse, AIConfigurationCreate | LLM provider configuration (BYOK) |

---

---

## Configuration & Model Config

**Standard (BaseSchema)**: `from_attributes=True` (ORM mapping), `populate_by_name=True` (accept snake_case input), `alias_generator=to_camel` (output camelCase JSON)

**Cost Schemas**: `frozen=True` (immutable, hashable), `strict=True` (strict type validation)

---

## Pagination Implementation Details

**Cursor Format**: Opaque base64-encoded strings (e.g., "MjAyNC0wMi0xMC1wMS5pLjM=" encodes "2024-02-10-p1.i.3"). Client cannot manipulate format; stable across schema versions.

**Usage**: Initial request `GET /api/v1/issues?page_size=20` returns `next_cursor`. Subsequent requests: `GET /api/v1/issues?page_size=20&cursor=<next_cursor>`.

**Response fields**: items, total, next_cursor, prev_cursor, has_next, has_prev, page_size.

---

## Common Patterns & Best Practices

**Explicit Null Fields**: Use `clear_*` boolean flags in request to distinguish "don't update" (null) from "clear field" (True). Service layer checks: `if payload.clear_assignee: issue.assignee_id = None`.

**Brief + Full Relations**: Responses include both `project_id: UUID` (mutations) and `project: ProjectBriefSchema` (display).

**Factory Methods**: Use `@classmethod from_issue(cls, issue)` to convert domain entities to response schemas. Maps nested relations via `.model_validate()`.

**Request → Service → Response**: Router receives schema, passes to service via payload, returns response schema via `from_domain()` factory method.

---

## Pre-Submission Checklist (Schema Changes)

- [ ] All fields have `description` in Field()
- [ ] Field constraints validate input (min_length, max_length, ge, le, pattern)
- [ ] Optional fields: `Field | None = None` (explicit default)
- [ ] Required fields: no defaults, use `Field(...)`
- [ ] Enums for choice fields (IssuePriority, StateGroup)
- [ ] Type hints: UUID (not str), date (not str), datetime (not str)
- [ ] Brief schemas for nested relations (prevent N+1, avoid circles)
- [ ] Response includes both IDs (mutations) and relations (display)
- [ ] from_domain() factory methods for entity→DTO conversion
- [ ] Pagination: use PaginatedResponse[T] for list endpoints
- [ ] Errors: return RFC 7807 ErrorResponse
- [ ] All inherit BaseSchema (camelCase JSON output + populate_by_name)
- [ ] Explicit nulling: use `clear_*` flags (distinguish null from don't-update)

---

---

## Files & Organization

### Schema File Structure

```
backend/src/pilot_space/api/v1/schemas/
├─ __init__.py              # Exports all schemas for import
├─ base.py                  # BaseSchema, EntitySchema, PaginatedResponse, ErrorResponse
├─ auth.py                  # LoginRequest, TokenResponse, UserProfileResponse
├─ workspace.py             # WorkspaceCreate, WorkspaceResponse, WorkspaceMemberResponse
├─ project.py               # ProjectCreate, ProjectResponse, StateResponse
├─ issue.py                 # IssueCreateRequest, IssueResponse, UserBriefSchema
├─ note.py                  # NoteCreate, NoteResponse, TipTapContentSchema
├─ cycle.py                 # CycleCreateRequest, CycleResponse, CycleMetricsResponse
├─ annotation.py            # AnnotationCreate, AnnotationResponse, AnnotationType
├─ discussion.py            # CommentCreate, CommentResponse, DiscussionStatus
├─ approval.py              # ApprovalRequestResponse, ApprovalDetailResponse
├─ cost.py                  # CostSummaryResponse, CostByAgent, CostTrendsResponse
├─ ai_context.py            # GenerateContextRequest, AIContextResponse
├─ ai_configuration.py      # AIConfigurationResponse, AIConfigurationCreate
├─ ai_suggestion.py         # [Not analyzed - future feature]
├─ integration.py           # [GitHub integration schemas]
├─ pr_review.py             # [PR review schemas]
├─ export.py                # [Data export schemas]
├─ role_skill.py            # [Role/skill assignment schemas]
├─ homepage.py              # [Homepage/activity schemas]
├─ onboarding.py            # [Onboarding flow schemas]
└─ CLAUDE.md                # This file
```

---

## Relationship to Other Modules

**API Layer**: Request schema → Pydantic validation → Service.execute(Payload) → Domain Entity → Response.from_domain() → camelCase JSON

**Domain Layer**: Request schemas validate at boundary. Payloads in service layer created from requests. Response schemas convert entities via `from_domain()`. No Pydantic models in domain (clean separation).

**Infrastructure Layer**: Schemas use `from_attributes=True` for ORM mapping. `.model_validate(orm_object)` converts SQLAlchemy models. Factory methods handle nested relation mapping.

---

## Common Issues & Solutions

**N+1 Queries**: Nested relations must be eager-loaded in service layer via `.options(joinedload(...))` before schema conversion.

**Circular References**: Use brief schemas (IDs only) to avoid cycles. Example: NoteResponse has `issue_ids: list[UUID]` not `issues: list[IssueResponse]`.

**Missing OpenAPI Docs**: Always include `description` parameter in Field(). `name: str` without description won't appear in /docs.

**Optional Field Defaults**: Use `field: Type | None = None` not `field: Type | None` (implicit required). Pydantic requires explicit None default.

---

## Generation Metadata

**Generated**: 2026-02-10 | **Original**: 1,678 lines | **Refactored**: 466 lines (72% reduction)

**Scope**: 13 schema modules (base, auth, workspace, project, issue, note, cycle, annotation, discussion, approval, cost, ai_context, ai_configuration)

**Patterns Detected**: BaseSchema hierarchy, Pydantic v2 validation, ORM mapping via from_attributes, factory methods from_domain(), brief nested schemas, explicit null flags (clear_*), RFC 7807 errors, cursor pagination, frozen+strict mode

**Coverage**: All 13 modules documented with field lists, validators, patterns. Validation examples removed per refactor goals.

---

## Related Documentation

**See also**:
- `/backend/CLAUDE.md` — Backend architecture, CQRS-lite pattern, dependency injection
- `/backend/src/pilot_space/api/CLAUDE.md` — API layer, middleware, routers, authentication
- `/backend/src/pilot_space/application/CLAUDE.md` — Service layer, payloads, domain services
- `docs/dev-pattern/45-pilot-space-patterns.md` — Project-specific patterns
- `docs/DESIGN_DECISIONS.md` — Design decision context for schema choices

