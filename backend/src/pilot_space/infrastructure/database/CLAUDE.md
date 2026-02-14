# Database Layer - Pilot Space

**Parent**: [infrastructure/CLAUDE.md](../../infrastructure/CLAUDE.md)

---

## Overview

Async SQLAlchemy 2.0 models, type-safe repositories with RLS enforcement, connection pooling, and Alembic migrations. All data access flows through repositories.

---

## SQLAlchemy Models (35 Total)

### Model Inheritance Hierarchy

```
Base (SQLAlchemy DeclarativeBase)
+-- BaseModel (UUID PK, timestamps, soft delete)
|   +-- WorkspaceScopedModel (BaseModel + workspace_id FK)
|   |   +-- Workspace, Project, Issue, Note, Cycle, Module
|   |   +-- Activity, Label, AIContext, AISession, AIConfiguration
|   |   +-- Integration, NoteAnnotation, NoteIssueLink
|   |   +-- ThreadedDiscussion, DiscussionComment, IssueLink
|   |   +-- Embedding, StateTemplate, UserRoleSkill
|   |   +-- WorkspaceDigest, DigestDismissal, WorkspaceOnboarding
|   |   +-- AIApprovalRequest, AICostRecord, AITask
|   +-- User (global, not workspace-scoped)
+-- WorkspaceMember (composite PK: user + workspace + role)
   WorkspaceInvitation, WorkspaceAPIKey, State
   IssueLabel, AIMessage, AIToolCall
```

### Base Mixins

Defined in `models/base.py`:

- **TimestampMixin**: `created_at` (server_default=now), `updated_at` (onupdate=now)
- **SoftDeleteMixin**: `is_deleted` (bool), `deleted_at`. Methods: `soft_delete()`, `restore()`
- **WorkspaceScopedMixin**: `workspace_id` FK (indexed, cascade delete)

### Key Models

- **Issue** (WorkspaceScopedModel): State machine, 13 indexes, ai_metadata JSONB. See `models/issue.py`.
- **Note** (WorkspaceScopedModel): TipTap JSON content, GIN full-text index on title. See `models/note.py`.
- **AIContext** (WorkspaceScopedModel): Cached issue context with 24h expiry. See `models/ai_context.py`.
- **AISession/AIMessage**: Multi-turn conversation with tool calls and token usage. See `models/ai_session.py`.
- **WorkspaceMember**: Composite PK (workspace_id, user_id), role enum. See `models/workspace_member.py`.

---

## Repository Pattern

### BaseRepository[T]

**File**: `repositories/base.py`

**Interface**: Generic CRUD with 14 core methods:

| Method | Purpose |
|--------|---------|
| `get_by_id(id)` | Fetch by PK (skips soft-deleted) |
| `get_by_id_scalar(id)` | Fetch without relationships |
| `get_all(limit, offset)` | Paginated list (created_at desc) |
| `create(entity)` | Insert, return with generated ID |
| `update(entity)` | Persist changes (fetch + modify + flush) |
| `delete(id, hard=False)` | Soft delete by default |
| `restore(entity)` | Undo soft delete |
| `count(filters)` / `exists(id)` | Count / existence check |
| `find_by(**kwargs)` / `find_one_by(**kwargs)` | Attribute-based search |
| `search(term, columns)` | ILIKE pattern matching |
| `paginate(cursor, page_size, sort_by, sort_order, filters)` | Cursor pagination -> CursorPage[T] |

### Specialized Repositories (18)

| Repository | Methods | Key Features |
|-----------|---------|--------------|
| IssueRepository | 21 | Eager loading with relations, workspace-scoped queries, race-safe sequence_id, bulk label assignment |
| NoteRepository | 15+ | Annotations eager load, workspace paginated, content search |
| AIContextRepository | 10+ | Cache with TTL, invalidation, get-or-generate |
| CycleRepository | -- | Status filtering, issue count aggregation |
| ProjectRepository | -- | Member validation, state templates |

For implementation details, see actual repository files in `repositories/`.

### Naming Conventions

- Repositories match model names: `IssueRepository`, `NoteRepository`, `CycleRepository`
- Methods follow pattern: `get_by_*`, `find_by_*`, `list_by_*`, `create_*`, `update_*`

---

## Database Connection & Session Management

### Connection Pool

**File**: `engine.py`

| Setting | Value | Rationale |
|---------|-------|-----------|
| `pool_size` | 5 | Base concurrent connections |
| `max_overflow` | 10 | Burst handling |
| `pool_timeout` | 30s | Wait before timeout |
| `pool_pre_ping` | True | Verify connections |

### Session Management

Context manager with auto-commit/rollback. Configuration: `expire_on_commit=False`, `autoflush=False` (manual flush control). FastAPI integration via `Depends(get_db_session)`.

See `engine.py` for session factory and `dependencies.py` for FastAPI integration.

---

## Migrations (36+ via Alembic)

### Key Migrations

| ID | Purpose |
|----|---------|
| 001 | Enable pgvector (768-dim embeddings) |
| 002 | Core entities (users, workspaces, projects, issues) |
| 003 | Project entities (State, StateGroup, Module) |
| 004 | RLS policies |
| 005-006 | Note + Issue entities |
| 010-011 | AIContext, performance indexes |
| 012-017 | AI configs, API keys, approvals, cost records, sessions |
| 020 | AI conversational tables (AIMessage, AIToolCall) |
| 028-035 | Digests, RLS refinements, role skills |

### Commands

```bash
alembic revision --autogenerate -m "Add column"  # Generate
alembic upgrade head                              # Apply
alembic downgrade -1                              # Rollback
alembic current                                   # Check status
```

### RLS Migration Pattern

Migrations that create tables must also enable RLS and create workspace isolation policies. See existing migration files in `alembic/versions/` for the `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY` pattern.

---

## Troubleshooting

- **N+1 Detection**: Enable `echo=True` on engine. Look for repeated SELECT per entity type. Fix with `.options(joinedload(...))`.
- **Pool Exhaustion**: "QueuePool Overflow" -- check `engine.pool.checkedout()`, increase `max_overflow`.
- **Stale Connections**: `pool_pre_ping=True` auto-verifies. Check PostgreSQL `idle_in_transaction_session_timeout` for persistent issues.

---

## Related Documentation

- **Parent**: [infrastructure/CLAUDE.md](../../infrastructure/CLAUDE.md)
- **RLS security**: [auth/CLAUDE.md](../auth/CLAUDE.md)
- **Domain entities**: [domain/models/CLAUDE.md](../../domain/models/CLAUDE.md)
- **Application services**: [application/CLAUDE.md](../../application/CLAUDE.md)
