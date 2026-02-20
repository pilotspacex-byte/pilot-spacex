# Pydantic v2 Schemas - Pilot Space

**Location**: `/backend/src/pilot_space/api/v1/schemas/` (13+ schema modules)

---

## Schema Inheritance Hierarchy

```
BaseSchema (root - camelCase JSON, populate_by_name=True, from_attributes=True)
+-- TimestampSchema (created_at, updated_at)
+-- EntitySchema (id + timestamps)
+-- SoftDeleteSchema (id + timestamps + is_deleted, deleted_at)
+-- PaginationParams (cursor-based pagination params)
+-- PaginatedResponse[T] (paginated list response)
+-- ErrorResponse (RFC 7807 Problem Details)
+-- SuccessResponse / DeleteResponse / BulkResponse[T]
+-- All domain schemas inherit from BaseSchema or EntitySchema
```

Base class configuration defined in `base.py:BaseSchema`.

---

## Schema Modules

| Module | Key Exports | Purpose |
|--------|-------------|---------|
| **base.py** | BaseSchema, EntitySchema, PaginatedResponse, ErrorResponse | Foundation + pagination |
| **auth.py** | LoginRequest, TokenResponse, UserProfileResponse | Authentication |
| **workspace.py** | WorkspaceCreate, WorkspaceDetailResponse, WorkspaceMemberResponse | Workspace CRUD + members |
| **project.py** | ProjectCreate, ProjectResponse, StateResponse | Project CRUD + states |
| **issue.py** | IssueCreateRequest, IssueResponse, UserBriefSchema, StateBriefSchema | Issues with AI metadata |
| **note.py** | NoteCreate, NoteResponse, TipTapContentSchema | Notes with TipTap content |
| **cycle.py** | CycleCreateRequest, CycleResponse, CycleMetricsResponse | Cycles + velocity metrics |
| **annotation.py** | AnnotationCreate, AnnotationResponse, AnnotationType | Margin annotations |
| **discussion.py** | CommentCreate, CommentResponse, DiscussionStatus | Threaded discussions |
| **approval.py** | ApprovalRequestResponse, ApprovalDetailResponse, ApprovalStatus | DD-003 approvals |
| **cost.py** | CostSummaryResponse, CostByAgent, CostTrendsResponse | AI cost tracking |
| **ai_context.py** | GenerateContextRequest, AIContextResponse | Issue AI context |
| **ai_configuration.py** | AIConfigurationResponse, AIConfigurationUpdate | LLM provider config |

---

## Key Schema Details

### Issue Schemas (`issue.py`)

**IssueCreateRequest**: name (1-255, required), description, priority (default NONE), state_id, project_id (required), assignee_id, cycle_id, module_id, parent_id, estimate_points (0-100), start_date, target_date, label_ids, enhance_with_ai (bool)

**IssueUpdateRequest**: All fields optional (null = don't update) + `clear_*` flags (clear_assignee, clear_cycle, clear_module, clear_parent, clear_estimate, clear_start_date, clear_target_date) for explicit nulling

**IssueResponse**: Full entity with nested briefs (ProjectBriefSchema, StateBriefSchema, UserBriefSchema, LabelBriefSchema) + FK IDs for mutations. Factory: `from_issue(cls, issue)`

### Note Schemas (`note.py`)

**TipTapContentSchema**: type (must equal "doc"), content (list of blocks). Validator enforces type="doc".

**NoteCreate**: project_id (optional), title (1-255), content (TipTapContentSchema | None), is_pinned

### Workspace Schemas (`workspace.py`)

**WorkspaceCreate**: name (1-255), slug (pattern: `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`), description (0-2000)

### Cycle Schemas (`cycle.py`)

**CycleCreateRequest**: name (1-255), project_id (required), start_date, end_date, status (DRAFT/ACTIVE/COMPLETED/CANCELLED)

**CycleMetricsResponse**: total/completed/in_progress issues, total/completed points, completion_percentage, velocity

### Approval Schemas (`approval.py`)

**ApprovalStatus**: PENDING, APPROVED, REJECTED, EXPIRED (24h TTL)

**Categories** (DD-003): Non-destructive -> auto, content creation -> configurable, destructive -> always require

### Cost Schemas (`cost.py`)

Model config: `frozen=True` (immutable), `strict=True`. Fields: agent_name, total_cost_usd, request_count, tokens

---

## Field Validation Patterns

| Field Type | Syntax | Example |
|-----------|--------|---------|
| Required string | `Field(..., min_length=1, max_length=N)` | name (1-255) |
| Optional string | `Type \| None = Field(None, max_length=N)` | description |
| String pattern | `Field(..., pattern=r"...")` | slug |
| Numeric range | `Field(default, ge=min, le=max)` | estimate_points (0-100) |
| Enum | `EnumType = EnumType.DEFAULT` | IssuePriority.NONE |
| UUID FK | `UUID` or `UUID \| None = None` | project_id |

**Custom validators**: `@field_validator` for cross-field constraints. See `annotation.py` (highlight range), `note.py` (TipTap type), `workspace.py` (slug pattern).

---

## Core Patterns

**Explicit Null Fields**: `clear_*` boolean flags in update requests. `clear_assignee=true` clears; `assignee_id=null` means don't update. See `issue.py:IssueUpdateRequest`.

**Brief + Full Relations**: Responses include both `project_id: UUID` (for mutations) and `project: ProjectBriefSchema` (for display).

**Factory Methods**: `@classmethod from_issue(cls, issue)` converts domain entities to response DTOs via `.model_validate()` for nested relations.

**Pagination**: `PaginatedResponse[T]` with opaque base64 cursors. See `base.py`.

**Configuration Variants**: Cost schemas use `frozen=True, strict=True` for immutability.

---

## Pre-Submission Checklist

- [ ] All fields have `description` in Field()
- [ ] Field constraints (min_length, max_length, ge, le, pattern)
- [ ] Optional fields: `Type | None = None`
- [ ] Brief schemas for nested relations (prevent N+1, avoid circles)
- [ ] Response includes both IDs and nested relations
- [ ] from_domain() factory method for entity -> DTO
- [ ] Pagination: use PaginatedResponse[T]
- [ ] Errors: RFC 7807 ErrorResponse
- [ ] All inherit BaseSchema (camelCase output)
- [ ] Explicit nulling: `clear_*` flags where needed

---

## Related Documentation

- **API Layer**: [`../../README.md`](../../README.md)
- **Router Details**: [`../README.md`](../README.md)
- **Application Services**: [`../../../application/README.md`](../../../application/README.md)
- **Design Decisions**: `docs/DESIGN_DECISIONS.md`
