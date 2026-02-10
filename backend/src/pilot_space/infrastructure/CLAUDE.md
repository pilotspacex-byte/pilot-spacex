# Infrastructure Layer Development Guide - Pilot Space

**For backend overview and general context, see `backend/CLAUDE.md`**

---

## Quick Reference

### Infrastructure Components

| Component | Technology | Count | Purpose |
|-----------|-----------|-------|---------|
| Models | SQLAlchemy 2.0 async | 35 | PostgreSQL entities with soft delete, RLS |
| Repositories | BaseRepository[T] | 18 | Type-safe data access with pagination |
| Migrations | Alembic | 36+ | Schema versioning, RLS policies, indexes |
| Database | PostgreSQL 16 | 1 | Async via Supabase (DD-060) |
| Cache | Redis 7 | 1 | Session cache (30-min TTL), AI cache (7-day TTL) |
| Search | Meilisearch 1.6 | 1 | Full-text search (typo-tolerant) |
| Queue | pgmq via Supabase | 1 | Async task processing (PR review, embeddings) |
| Auth | Supabase Auth (GoTrue) | 1 | JWT validation + RLS enforcement |
| Encryption | Supabase Vault | 1 | API key storage (AES-256-GCM) |

---

## Directory Structure

```
infrastructure/
├─ database/
│  ├─ models/              (35 SQLAlchemy models)
│  │  ├─ base.py          (BaseModel, mixins: TimestampMixin, SoftDeleteMixin, WorkspaceScopedMixin)
│  │  ├─ issue.py         (Issue, IssuePriority)
│  │  ├─ note.py          (Note)
│  │  ├─ project.py       (Project, State, StateGroup, Module)
│  │  ├─ cycle.py         (Cycle)
│  │  ├─ user.py          (User)
│  │  ├─ workspace.py     (Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceAPIKey)
│  │  ├─ activity.py      (Activity, ActivityType)
│  │  ├─ label.py         (Label, IssueLabel)
│  │  ├─ ai_*.py          (AIContext, AISession, AIMessage, AIToolCall, AICostRecord, AIApprovalRequest, AITask, AIConfiguration)
│  │  ├─ integration.py    (Integration, IntegrationLink)
│  │  ├─ note_*.py        (Note, NoteAnnotation, NoteIssueLink)
│  │  ├─ discussion_*.py   (ThreadedDiscussion, DiscussionComment)
│  │  ├─ embedding.py     (Embedding for vector search)
│  │  ├─ template.py      (StateTemplate for workflow templates)
│  │  ├─ user_role_skill.py (UserRoleSkill for role-based skills)
│  │  ├─ workspace_*.py    (WorkspaceDigest, DigestDismissal, WorkspaceOnboarding)
│  │  └─ __init__.py       (Model exports)
│  │
│  ├─ repositories/        (18 repositories + BaseRepository)
│  │  ├─ base.py          (BaseRepository[T] with CRUD, pagination, filtering)
│  │  ├─ issue_repository.py       (21 specialized methods)
│  │  ├─ note_repository.py        (15+ methods)
│  │  ├─ cycle_repository.py       (10+ methods)
│  │  ├─ project_repository.py     (Project CRUD + state management)
│  │  ├─ workspace_repository.py   (Workspace + member CRUD)
│  │  ├─ user_repository.py        (User lookup + preferences)
│  │  ├─ activity_repository.py    (Activity logging + queries)
│  │  ├─ label_repository.py       (Label CRUD)
│  │  ├─ ai_context_repository.py  (AI context retrieval + caching)
│  │  ├─ ai_configuration_repository.py (Workspace AI settings)
│  │  ├─ approval_repository.py    (Approval request tracking)
│  │  ├─ discussion_repository.py  (Threaded discussions + comments)
│  │  ├─ note_annotation_repository.py  (AI annotations per block)
│  │  ├─ note_issue_link_repository.py  (Bidirectional links)
│  │  ├─ issue_link_repository.py  (Issue dependencies)
│  │  ├─ integration_repository.py (GitHub/Slack integrations)
│  │  ├─ invitation_repository.py  (Workspace invitations)
│  │  ├─ onboarding_repository.py  (First-time setup tracking)
│  │  ├─ ai_task_repository.py     (Background AI tasks)
│  │  ├─ digest_repository.py      (Workspace digests + dismissals)
│  │  ├─ role_skill_repository.py  (Role-based skills + templates)
│  │  ├─ template_repository.py    (State templates)
│  │  ├─ homepage_repository.py    (Activity feed + featured items)
│  │  └─ __init__.py         (Repository exports)
│  │
│  ├─ engine.py            (SQLAlchemy engine, session factory, connection pooling)
│  ├─ base.py              (Base, BaseModel, mixins, camel_to_snake)
│  ├─ rls.py               (RLS context setters, policy SQL generators)
│  ├─ types.py             (JSONBCompat, custom column types)
│  └─ __init__.py
│
├─ cache/
│  ├─ redis.py            (RedisClient: async operations, JSON serialization)
│  ├─ ai_cache.py         (AICache: prompt/response caching with TTLs)
│  ├─ types.py            (CacheResult, cache constants)
│  └─ __init__.py
│
├─ auth/
│  ├─ supabase_auth.py    (SupabaseAuthClient: JWT validation, token parsing)
│  └─ __init__.py
│
├─ storage/
│  ├─ __init__.py         (Placeholder for Supabase Storage integration)
│
├─ search/
│  ├─ meilisearch.py      (MeilisearchClient: full-text, faceted, workspace-scoped)
│  ├─ config.py           (IndexName, INDEX_CONFIGS, DEFAULT_INDEX_SETTINGS)
│  ├─ models.py           (SearchHit, SearchResult, TaskInfo)
│  └─ __init__.py
│
├─ queue/
│  ├─ supabase_queue.py   (SupabaseQueueClient: pgmq via RPC, message ops)
│  ├─ models.py           (QueueName, QueueMessage, MessageStatus)
│  ├─ error_handlers.py   (Error handling + retry logic)
│  ├─ handlers/
│  │  ├─ pr_review_handler.py  (PR review task processing)
│  │  └─ __init__.py
│  └─ __init__.py
│
├─ jobs/
│  ├─ expire_approvals.py (Scheduled job: auto-expire approvals after 24h)
│  └─ __init__.py
│
├─ encryption.py          (Supabase Vault integration for API key encryption)
└─ __init__.py
```

---

## SQLAlchemy Models (35 Total)

### Model Inheritance Hierarchy

```
Base (SQLAlchemy DeclarativeBase)
├─ BaseModel (UUID PK, timestamps, soft delete)
│  ├─ WorkspaceScopedModel (BaseModel + workspace_id FK)
│  │  ├─ Workspace (root tenant entity)
│  │  ├─ Project (project in workspace)
│  │  ├─ Issue (work item)
│  │  ├─ Note (note canvas)
│  │  ├─ Cycle (sprint)
│  │  ├─ Module (epic)
│  │  ├─ Activity (audit log)
│  │  ├─ Label (custom labels)
│  │  ├─ AIContext (issue context)
│  │  ├─ AISession (conversation session)
│  │  ├─ AIConfiguration (workspace AI settings)
│  │  ├─ Integration (GitHub/Slack configs)
│  │  ├─ NoteAnnotation (AI margin suggestions)
│  │  ├─ NoteIssueLink (note↔issue bidirectional)
│  │  ├─ ThreadedDiscussion (discussion root)
│  │  ├─ DiscussionComment (discussion reply)
│  │  ├─ IssueLink (issue dependencies)
│  │  ├─ Embedding (vector embeddings)
│  │  ├─ StateTemplate (workflow state template)
│  │  ├─ UserRoleSkill (role-skill mapping)
│  │  ├─ WorkspaceDigest (daily/weekly digest)
│  │  ├─ DigestDismissal (user dismiss record)
│  │  ├─ WorkspaceOnboarding (setup tracking)
│  │  ├─ AIApprovalRequest (human approval workflow)
│  │  ├─ AICostRecord (token tracking + billing)
│  │  └─ AITask (background AI tasks)
│  │
│  └─ User (global user, not workspace-scoped)
│
└─ WorkspaceMember (composite: user + workspace + role)
   WorkspaceInvitation (invite token)
   WorkspaceAPIKey (API keys for integrations)
   State (issue state, workspace-scoped)
   IssueLabel (issue-label assignment)
   AIMessage (conversational message)
   AIToolCall (MCP tool invocation record)
```

### Model Features

**Base Mixins**:

```python
# TimestampMixin - Auto timestamps
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

# SoftDeleteMixin - Mark as deleted instead of removing
class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(tz=UTC)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None

# WorkspaceScopedMixin - Workspace isolation for RLS
class WorkspaceScopedMixin:
    @declared_attr
    def workspace_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            index=True,  # Essential for RLS filtering
        )
```

**Composite Key Pattern**:

```python
# WorkspaceMember: Role in workspace
class WorkspaceMember(Base, TimestampMixin):
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[Role] = mapped_column(SQLEnum(Role), default=Role.MEMBER)

    # Single table inheritance for role-based access control
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )
```

### Key Models

#### Issue Model

```python
class Issue(WorkspaceScopedModel):
    """Work item tracking.

    State machine: Backlog → Todo → In Progress → In Review → Done
                   (Can Cancelled, reopened)

    Identifier: {PROJECT.identifier}-{sequence_id} (e.g., PILOT-123)
    """

    sequence_id: Mapped[int]  # Project-scoped auto-increment
    name: Mapped[str]         # Title (1-255 chars)
    description: Mapped[str | None]  # Markdown
    description_html: Mapped[str | None]  # Pre-rendered HTML
    priority: Mapped[IssuePriority]  # none, low, medium, high, urgent

    # Foreign keys
    state_id: Mapped[UUID] = mapped_column(ForeignKey("states.id"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    assignee_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    cycle_id: Mapped[UUID | None] = mapped_column(ForeignKey("cycles.id"))
    module_id: Mapped[UUID | None] = mapped_column(ForeignKey("modules.id"))
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("issues.id"))  # Subtask

    # Planning fields
    estimate_points: Mapped[float | None]
    start_date: Mapped[date | None]
    target_date: Mapped[date | None]
    sort_order: Mapped[int] = mapped_column(default=0)

    # AI metadata (JSONB)
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default={})

    # Relationships
    state: Mapped[State] = relationship(lazy="select")
    project: Mapped[Project] = relationship(lazy="select")
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id], lazy="select")
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id], lazy="select")
    labels: Mapped[list[Label]] = relationship(secondary=issue_labels, lazy="select")
    sub_issues: Mapped[list[Issue]] = relationship(
        primaryjoin=parent_id,
        foreign_keys=[parent_id],
        remote_side=[id],
    )
    note_links: Mapped[list[NoteIssueLink]] = relationship(lazy="select")
    activities: Mapped[list[Activity]] = relationship(lazy="select")
```

#### Note Model

```python
class Note(WorkspaceScopedModel):
    """Block-based collaborative document (TipTap JSON).

    Home view default in Note-First workflow.
    Supports inline AI (ghost text, annotations, discussions).
    """

    title: Mapped[str]
    content: Mapped[dict[str, Any]] = mapped_column(JSONBCompat)  # TipTap JSON

    # Relationships
    annotations: Mapped[list[NoteAnnotation]] = relationship(lazy="select")
    issue_links: Mapped[list[NoteIssueLink]] = relationship(lazy="select")
    discussions: Mapped[list[ThreadedDiscussion]] = relationship(lazy="select")
```

#### AIContext Model

```python
class AIContext(WorkspaceScopedModel):
    """Aggregated issue context for AI processing.

    Cached for 24h. Includes:
    - Related issues (semantic similarity)
    - Issue description + comments
    - Linked notes
    - Code file context
    - Dependencies graph
    """

    issue_id: Mapped[UUID] = mapped_column(ForeignKey("issues.id"), unique=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONBCompat)  # Full context
    cache_expires_at: Mapped[datetime]  # TTL for Redis cache

    # Cache metadata
    related_issues: Mapped[list[UUID]] = mapped_column(JSONBCompat)  # Issue IDs
    last_generated_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

#### AISession & AIMessage

```python
class AISession(WorkspaceScopedModel):
    """Multi-turn conversation session.

    - Hot cache: Redis (30-min sliding expiration)
    - Durable: PostgreSQL (24h TTL for resumption)
    - Context: Optional workspace_id for scoped operations
    """

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    session_context: Mapped[dict[str, Any]] = mapped_column(JSONBCompat, default={})
    last_activity_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]  # 24h TTL

    messages: Mapped[list[AIMessage]] = relationship(lazy="select")

class AIMessage(Base, TimestampMixin, SoftDeleteMixin):
    """Conversational message (user or assistant).

    Stores full message + tool calls + token usage.
    Part of session history for resumption.
    """

    session_id: Mapped[UUID] = mapped_column(ForeignKey("ai_sessions.id"), index=True)
    role: Mapped[MessageRole]  # user, assistant
    content: Mapped[str]
    tool_calls: Mapped[list[AIToolCall]] = relationship(lazy="select")
    token_usage: Mapped[dict[str, int]] = mapped_column(JSONBCompat)  # {prompt, completion}
```

---

## Repository Pattern

### BaseRepository[T] - Generic CRUD

Located in `repositories/base.py`. All repositories inherit from this.

**Constructor**:

```python
class BaseRepository[T: BaseModel]:
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
```

**Core Methods**:

| Method | Purpose | Notes |
|--------|---------|-------|
| `get_by_id(id)` | Fetch single by PK | Skips soft-deleted by default |
| `get_by_id_scalar(id)` | Fetch without relationships | Overrides eager loading for validation |
| `get_all(limit, offset)` | Fetch all with pagination | Ordered by `created_at desc` |
| `create(entity)` | Insert new entity | Returns with generated ID |
| `update(entity)` | Persist changes | Must fetch + modify + flush |
| `delete(id, hard=False)` | Mark deleted or hard delete | Soft delete by default |
| `restore(entity)` | Undo soft delete | Clears `deleted_at` |
| `count(filters)` | Count matching | Excludes soft-deleted |
| `exists(id)` | Check existence | Boolean return |
| `find_by(**kwargs)` | Find by attributes | Returns list, AND logic |
| `find_one_by(**kwargs)` | Find first match | Returns single or None |
| `search(term, columns)` | Full-text search | ILIKE pattern matching |
| `paginate(cursor, page_size, sort_by, sort_order, filters)` | Cursor pagination | Returns CursorPage with metadata |

**Cursor Pagination**:

```python
@dataclass
class CursorPage[T: BaseModel]:
    items: Sequence[T]
    total: int
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool = False
    has_prev: bool = False
    page_size: int = 20
    filters: dict[str, Any] = field(default_factory=dict)
```

### Specialized Repositories

**IssueRepository** (21 specialized methods):

```python
# Eager loading with relationships
async def get_by_id_with_relations(issue_id: UUID) -> Issue | None:
    """Load issue with project, state, assignee, labels, etc."""
    return select(Issue).options(
        joinedload(Issue.project),
        joinedload(Issue.state),
        joinedload(Issue.assignee),
        joinedload(Issue.reporter),
        selectinload(Issue.labels),
        selectinload(Issue.sub_issues),
        selectinload(Issue.note_links),
    )

# Workspace-scoped queries
async def find_by_workspace(
    workspace_id: UUID,
    filters: IssueFilters | None = None,
) -> list[Issue]:
    """Find all issues in workspace with optional filters."""
    # Filters: state_ids, assignee_ids, label_ids, cycle_id, module_id, date ranges

# Sequence ID generation (prevents race condition)
async def get_next_sequence_id(project_id: UUID) -> int:
    """Get next sequence ID for issue identifier."""
    result = await session.execute(
        select(func.max(Issue.sequence_id) + 1).where(Issue.project_id == project_id)
    )
    return result.scalar() or 1

# Bulk label assignment
async def bulk_update_labels(issue_id: UUID, label_ids: list[UUID]) -> None:
    """Assign multiple labels to issue in single transaction."""
```

**NoteRepository** (15+ methods):

```python
async def get_by_id_with_annotations(note_id: UUID) -> Note | None:
    """Load note with AI annotations and issue links."""

async def find_by_workspace_paginated(
    workspace_id: UUID,
    cursor: str | None = None,
    page_size: int = 20,
) -> CursorPage[Note]:
    """Paginated note listing for canvas view."""

async def search_content(
    workspace_id: UUID,
    search_term: str,
) -> list[Note]:
    """Full-text search in note content and blocks."""
```

**AIContextRepository** (10+ methods):

```python
async def get_cached(issue_id: UUID) -> AIContext | None:
    """Get cached context if not expired."""

async def invalidate_cache(issue_id: UUID) -> None:
    """Expire context cache (called on issue update)."""

async def get_or_generate(
    issue_id: UUID,
    cache_ttl: int = 86400,  # 24h
) -> AIContext:
    """Return cached or generate new context."""
```

### Repository Best Practices

**Always use eager loading**:

```python
# ❌ WRONG - N+1 queries
issues = await repo.get_all()
for issue in issues:
    assignee = issue.assignee  # Triggers query per issue

# ✅ CORRECT - Loaded in single query
issues = await session.execute(
    select(Issue).options(
        joinedload(Issue.assignee),
        joinedload(Issue.project),
        selectinload(Issue.labels),
    )
)
```

**Filter by workspace_id explicitly**:

```python
# ❌ WRONG - No workspace scoping (RLS violation)
issues = await session.execute(select(Issue))

# ✅ CORRECT - Explicit workspace scope
issues = await session.execute(
    select(Issue).where(Issue.workspace_id == workspace_id)
)
```

**Use soft delete by default**:

```python
# Repository.delete() marks as deleted, not removed
await repo.delete(issue)  # Sets is_deleted=True, deleted_at=now()

# Hard delete only for cleanup (rare)
await repo.delete(issue, hard=True)

# Include soft-deleted in queries if needed
entities = await repo.get_all(include_deleted=True)
```

---

## Database Connection & Session Management

### Engine Configuration (`engine.py`)

```python
def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Async SQLAlchemy engine with connection pooling."""
    settings = settings or get_settings()

    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=5,           # Base pool size
        max_overflow=10,       # Overflow connections
        pool_timeout=30.0,     # Wait timeout
        pool_pre_ping=True,    # Verify connections before use
    )

# Singleton pattern avoids multiple engine instances
_manager = EngineManager()

def get_engine() -> AsyncEngine:
    return _manager.get_engine()

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects in memory after commit
        autoflush=False,         # Manual flush control
    )
```

### Session Management

**Context manager for automatic cleanup**:

```python
@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get session with automatic rollback on exception."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**In FastAPI endpoints**:

```python
@router.post("/issues")
async def create_issue(
    request: IssueCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Session auto-committed on successful return."""
    service = CreateIssueService(session=session, ...)
    result = await service.execute(payload)
    return result
```

### Connection Pool Constants

| Setting | Value | Rationale |
|---------|-------|-----------|
| `pool_size` | 5 | Base connections for concurrent requests |
| `max_overflow` | 10 | Burst handling (peak load) |
| `pool_timeout` | 30s | Wait time before timeout |
| `pool_pre_ping` | True | Verify connections (prevent stale) |

---

## RLS (Row-Level Security) - Core Security Boundary

**RLS violations expose sensitive data across workspaces.** Database-level enforcement prevents application-layer bypass.

### RLS Architecture (`rls.py`)

**Set RLS context at request start**:

```python
async def set_rls_context(
    session: AsyncSession,
    user_id: UUID,
    workspace_id: UUID | None = None,
) -> None:
    """Set PostgreSQL session variables for policies."""
    await session.execute(
        text(f"SET LOCAL app.current_user_id = '{user_id}'")
    )
    if workspace_id:
        await session.execute(
            text(f"SET LOCAL app.current_workspace_id = '{workspace_id}'")
        )

async def clear_rls_context(session: AsyncSession) -> None:
    """Reset session variables (called on cleanup)."""
    await session.execute(text("RESET app.current_user_id"))
    await session.execute(text("RESET app.current_workspace_id"))
```

**Middleware integration**:

```python
@app.middleware("http")
async def rls_middleware(request: Request, call_next):
    """Set RLS context for all requests."""
    user_id = request.state.user_id  # From auth token
    workspace_id = request.path_params.get("workspace_id")

    async with get_db_session() as session:
        await set_rls_context(session, user_id, workspace_id)
        request.state.session = session
        return await call_next(request)
```

### RLS Policies

**Workspace isolation (generic)**:

```sql
-- For tables with workspace_id column
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

CREATE POLICY "{table}_workspace_isolation"
ON {table}
FOR ALL
USING (
    workspace_id IN (
        SELECT wm.workspace_id
        FROM workspace_members wm
        WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
        AND wm.is_deleted = false
    )
);

CREATE POLICY "{table}_service_role"
ON {table}
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

**User table (allows seeing self + workspace members)**:

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_self"
ON users
FOR SELECT
USING (
    id = current_setting('app.current_user_id', true)::uuid
);

CREATE POLICY "users_workspace_members"
ON users
FOR SELECT
USING (
    id IN (
        SELECT wm.user_id FROM workspace_members wm
        WHERE wm.workspace_id IN (
            SELECT wm2.workspace_id FROM workspace_members wm2
            WHERE wm2.user_id = current_setting('app.current_user_id', true)::uuid
            AND wm2.is_deleted = false
        )
        AND wm.is_deleted = false
    )
);
```

**WorkspaceMembers (read-only for members, modify for admins)**:

```sql
CREATE POLICY "workspace_members_read"
ON workspace_members
FOR SELECT
USING (
    workspace_id IN (
        SELECT wm.workspace_id FROM workspace_members wm
        WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
        AND wm.is_deleted = false
    )
);

CREATE POLICY "workspace_members_admin"
ON workspace_members
FOR ALL
USING (
    workspace_id IN (
        SELECT wm.workspace_id FROM workspace_members wm
        WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
        AND wm.role IN ('OWNER', 'ADMIN')
        AND wm.is_deleted = false
    )
);
```

### RLS Verification Checklist

- [ ] RLS policy created for every multi-tenant table
- [ ] Service layer validates workspace membership before mutations
- [ ] Repository queries scoped by `workspace_id` OR rely on RLS
- [ ] `set_rls_context()` called in middleware/request handler
- [ ] Integration tests verify cross-workspace isolation (create 2 workspaces, verify leakage prevented)
- [ ] No raw SQL queries without RLS enforcement

### Common RLS Pitfalls

```python
# ❌ WRONG - No workspace scope (leaks data)
select(Issue)  # Returns issues from ALL workspaces

# ✅ CORRECT - Explicit scope + RLS backup
select(Issue).where(Issue.workspace_id == workspace_id)

# ❌ WRONG - Trusts user input without verification
await repo.find_by_workspace(user_provided_workspace_id)

# ✅ CORRECT - RLS context set, RLS policies filter automatically
await set_rls_context(session, user_id, workspace_id)
# Now database enforces access control

# ❌ WRONG - Service role query bypasses RLS
# (Intended only for admin operations, never user-facing queries)
```

---

## Migrations (36+ via Alembic)

### Migration Strategy

Alembic tracks schema changes in `backend/alembic/versions/`.

**Key migrations**:

| ID | Purpose |
|----|---------|
| 001 | Enable pgvector extension (768-dim embeddings) |
| 002 | Core entities (users, workspaces, projects, issues) |
| 003 | Project entities (State, StateGroup, Module) |
| 004 | RLS policies (enforcement at database level) |
| 005 | Note entities (canvas + blocks) |
| 006 | Issue entities (labels, links, cycles) |
| 010 | AIContext entity (cached context) |
| 011 | Performance indexes (workspace_id, state_id, etc.) |
| 012 | AI configurations (API keys, preferences) |
| 014 | Workspace API keys (for integrations) |
| 015 | AI approval requests (human-in-the-loop) |
| 016 | AI cost records (token tracking + billing) |
| 017 | AI sessions (conversation history) |
| 020 | AI conversational tables (AIMessage, AIToolCall) |
| 028-035 | Recent: Digests, RLS refinements, role skills |

### Creating Migrations

**Auto-generate from model changes**:

```bash
# Create migration file (auto-detects schema changes)
alembic revision --autogenerate -m "Add issue_priority column"

# Apply migration
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check current migration
alembic current
```

**Migration anatomy**:

```python
"""Add issue_priority column."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    """Add column and create enum type."""
    # Create enum type
    op.execute(
        "CREATE TYPE issue_priority_enum AS ENUM ('none', 'low', 'medium', 'high', 'urgent')"
    )

    # Add column to table
    op.add_column(
        'issues',
        sa.Column('priority', sa.Enum('none', 'low', 'medium', 'high', 'urgent', name='issue_priority_enum'), nullable=False, server_default='none')
    )

def downgrade():
    """Drop column and enum type."""
    op.drop_column('issues', 'priority')
    op.execute("DROP TYPE issue_priority_enum")
```

### RLS Migration Pattern

```python
"""Add RLS policy for issues table."""
from alembic import op

def upgrade():
    """Enable RLS and create policies."""
    op.execute("""
    ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
    ALTER TABLE issues FORCE ROW LEVEL SECURITY;

    CREATE POLICY "issues_workspace_isolation"
    ON issues
    FOR ALL
    USING (
        workspace_id IN (
            SELECT wm.workspace_id FROM workspace_members wm
            WHERE wm.user_id = current_setting('app.current_user_id', true)::uuid
            AND wm.is_deleted = false
        )
    );
    """)

def downgrade():
    """Drop RLS policies."""
    op.execute("DROP POLICY IF EXISTS issues_workspace_isolation ON issues")
    op.execute("ALTER TABLE issues DISABLE ROW LEVEL SECURITY")
```

---

## Cache Layer (`cache/`)

**RedisClient**: Async operations with JSON serialization. Connection pool with configurable max_connections, socket_timeout. Methods: set (with TTL), get, delete, incr, exists.

**AICache**: Caches AI responses by prompt hash (SHA-256) with workspace scoping. TTL: 7 days for responses, 24h for context.

| Cache Key Pattern | TTL | Purpose |
|-------------------|-----|---------|
| `session:{session_id}` | 30min | Hot session cache |
| `ai:context:{issue_id}` | 24h | AI context for issue |
| `ai:response:{hash}` | 7d | Response by prompt hash |
| `rate_limit:{user_id}:{endpoint}` | 1min | Rate limit counters |

---

## Authentication (`auth/`)

**SupabaseAuthClient**: JWT validation (HS256/ES256 algorithms) with TokenPayload dataclass. Returns user_id (UUID), expiration check, metadata. Methods: verify_token(), get_user_by_id() via Supabase Admin API. Used in AuthMiddleware for request validation.

---

## Search Layer (`search/`)

**MeilisearchClient**: Workspace-scoped full-text search with typo tolerance. Methods: search() (with workspace_id filter, faceting, limit), index_document() (add/update). Index configs define searchable, filterable, and sortable attributes per index (issues, notes, pages). Returns SearchResult with matched documents and task info.

---

## Queue Layer (`queue/`)

**SupabaseQueueClient**: Async task processing via pgmq (PostgreSQL Message Queue). Methods: enqueue() (with visibility timeout), dequeue() (batch), ack() (remove after success). Queue names: AI_TASKS, PR_REVIEWS, WEBHOOKS, NOTIFICATIONS. Queue handlers in `handlers/` process messages asynchronously and ack on success.

---

## Encryption (`encryption.py`)

**EncryptionService**: Encrypt/decrypt via Supabase Vault (AES-256-GCM). Methods: encrypt_api_key() (store), decrypt_api_key() (retrieve). Key types: github, slack, openai. WorkspaceAPIKey model stores encrypted_key with workspace_id scoping. Decrypt on-demand only.

---

## Infrastructure Initialization

**Application Startup** (`main.py` lifespan): Test database connection, initialize Redis, Meilisearch. All clients connected at startup, disconnected at shutdown.

**Dependency Injection Container** (`container.py`): Singletons for config, engine, session_factory, Redis. Factories for repositories and services (new instance per request). Injected via FastAPI Depends().

---

## Common Patterns & Anti-Patterns

**Eager Load Relationships**: Use `.options(joinedload(...))` for one-to-one, `.options(selectinload(...))` for one-to-many. Prevents N+1 queries when accessing related objects in loops.

**Workspace Scoping**: Always filter by workspace_id in queries. Missing scoping causes RLS violations.

**Soft Delete**: Default is soft delete (sets is_deleted=True). Hard delete only for cleanup. Repository.delete() uses soft by default.

**Anti-Pattern - Lazy Loading**: Accessing relationships in loops triggers query per item. Always eager load before loops.

**Anti-Pattern - Blocking I/O**: Never use blocking file I/O, time.sleep(), or subprocess in async functions. Use asyncio.get_event_loop().run_in_executor(None, _sync_func) for sync operations.

---

---

## Troubleshooting

**N+1 Query Detection**: Enable SQLAlchemy echo (engine created with echo=True). Look for repeated SELECT for same entity type. Fix: Use eager loading with .options(joinedload(...)).

**RLS Enforcement**: Run `SELECT current_setting('app.current_user_id')` to verify RLS context is set. Query should return only workspace-scoped data. Test cross-workspace isolation in integration tests.

**Connection Pool Exhaustion**: "QueuePool Overflow" means max_overflow reached. Check pool stats with engine.pool.checkedout(). Increase max_overflow or reduce concurrent requests.

---

## Best Practices Summary

**Database**:
- Async-only (no blocking I/O)
- Eager load relationships (prevent N+1)
- Soft delete by default (is_deleted flag)
- RLS enforcement on all multi-tenant tables
- Indexes on frequently filtered columns (workspace_id, state_id, etc.)

**Repositories**:
- Inherit from BaseRepository[T] for consistency
- Override only for specialized queries
- Always filter by workspace_id
- Use type hints for all parameters/returns
- Document complex filter logic

**Migrations**:
- Auto-generate from model changes: `alembic revision --autogenerate`
- Always include RLS policies in migrations
- Add indexes for frequently queried columns
- Test rollback/downgrade locally

**Caching**:
- Use Redis for session state (30-min TTL)
- Cache AI responses by prompt hash (7-day TTL)
- Graceful degradation (fallback to DB on cache miss)
- Log cache errors but don't fail requests

**Security**:
- RLS is the enforcement boundary (not application logic)
- Encrypt sensitive data (API keys via Vault)
- Validate workspace membership before mutations
- Never trust user input for filtering without RLS

---

## Generation Metadata

**Generated**: 2026-02-10

**Scope Analyzed**:
- 35 SQLAlchemy models (12 categories)
- 18 repositories + BaseRepository
- 36+ Alembic migrations
- 5 infrastructure services (database, cache, auth, search, queue)
- RLS policies + security boundary
- Connection pooling + session management

**Key Patterns Detected**:
- BaseRepository[T] generic CRUD with soft delete
- WorkspaceScopedModel mixin for RLS
- Eager loading (joinedload/selectinload)
- Cursor-based pagination with metadata
- Database-level RLS enforcement (PostgreSQL policies)
- Async SQLAlchemy 2.0 throughout
- Redis hot cache + PostgreSQL durable storage
- Supabase platform consolidation (Auth, Queue, Vault, Storage)

**Coverage Gaps**:
- Health check endpoint for Redis/Meilisearch connectivity (partially implemented)
- Migration rollback tests (tested manually, not automated)
- Performance regression tests for large datasets (missing)
- Vault encryption integration tests (mocked)

**Suggested Next Steps**:
1. Add health check endpoints for all infrastructure dependencies
2. Implement performance benchmarks for eager loading patterns
3. Create automated migration rollback tests
4. Document partition strategy for multi-region deployment (Phase 3)
5. Add observability: query timing, cache hit/miss rates, connection pool metrics
