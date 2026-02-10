# Application Services Layer - Pilot Space

**Purpose**: Command and query handlers for all business logic. Domain-focused, async-first, dependency-injected.

**Coverage**: 8+ domain services across note, issue, cycle, AI context, annotation, discussion, integration, and onboarding.

---

## Quick Reference

### Service Pattern: CQRS-lite (DD-064)

Every service follows the same structure:

```python
@dataclass
class CommandPayload:
    """Validated input at API boundary."""
    # Required fields
    workspace_id: UUID
    # Optional fields with sensible defaults

@dataclass
class CommandResult:
    """Typed output from service."""
    entity: DomainEntity
    # Additional computed fields

class SomeService:
    def __init__(self, session: AsyncSession, repository: SomeRepository):
        self._session = session
        self._repo = repository

    async def execute(self, payload: CommandPayload) -> CommandResult:
        """Execute the command. Payload → Validation → Repository → Result."""
        # 1. Validate
        # 2. Get related entities
        # 3. Create or update domain entity
        # 4. Persist via repository
        # 5. Log activity if applicable
        # 6. Return typed result
```

**Benefits**:
- Explicit payloads document expectations
- One-way flow: input → output (no side effects)
- Testable in isolation
- Clear separation of concerns
- Easy to trace in logs (all inputs captured)

### Service Count & Organization

```
8 core domain services:
├─ note/ (5 services)
│  ├─ CreateNoteService
│  ├─ UpdateNoteService
│  ├─ GetNoteService
│  ├─ CreateNoteFromChatService
│  └─ AIUpdateService
├─ issue/ (5 services)
│  ├─ CreateIssueService
│  ├─ UpdateIssueService
│  ├─ ListIssuesService
│  ├─ GetIssueService
│  └─ ActivityService
├─ cycle/ (5 services)
│  ├─ CreateCycleService
│  ├─ UpdateCycleService
│  ├─ GetCycleService
│  ├─ AddIssueToCycleService
│  └─ RolloverCycleService
├─ ai_context/ (3 services)
│  ├─ GenerateAIContextService
│  ├─ RefineAIContextService
│  └─ ExportAIContextService
├─ annotation/ (1 service)
│  └─ CreateAnnotationService
├─ discussion/ (1 service)
│  └─ CreateDiscussionService
├─ integration/ (4 services)
│  ├─ ConnectGitHubService
│  ├─ LinkCommitService
│  ├─ ProcessWebhookService
│  └─ AutoTransitionService
├─ onboarding/ (3 services)
│  ├─ CreateGuidedNoteService
│  ├─ GetOnboardingService
│  └─ UpdateOnboardingService
├─ role_skill/ (4 services)
│  ├─ CreateRoleSkillService
│  ├─ UpdateRoleSkillService
│  ├─ GenerateRoleSkillService
│  └─ ListRoleSkillsService
├─ homepage/ (3 services)
│  ├─ GetActivityService
│  ├─ GetDigestService
│  └─ DismissSuggestionService
└─ workspace.py (1 service)
   └─ WorkspaceService
```

---

## Core Pattern: CQRS-lite Explained

### What is CQRS-lite?

**Command/Query Separation without Event Sourcing.** Simple rule:

- **Commands** (mutations): `CreateIssueService.execute(CreateIssuePayload) → CreateIssueResult`
- **Queries** (reads): `GetIssueService.execute(GetIssuePayload) → GetIssueResult`

No complexity of event stores or replicated read models. Just:

```
Input Payload → Validation → Business Logic → Output Result
```

### Why Not Just Call Repositories?

Bad pattern (❌):
```python
@router.post("/issues")
async def create_issue(request: IssueCreateRequest, repo: IssueRepository):
    # No validation, no logging, no transaction boundary
    issue = Issue(name=request.name, ...)
    return await repo.create(issue)
```

Good pattern (✅):
```python
@router.post("/issues")
async def create_issue(request: IssueCreateRequest, service: CreateIssueService):
    result = await service.execute(
        CreateIssuePayload(
            workspace_id=...,
            name=request.name,
            ...
        )
    )
    return result
```

**Advantages**:
1. **Testable**: Call service directly without HTTP
2. **Reusable**: Any caller (API, webhook, scheduled task) uses same service
3. **Validatable**: Payload dataclass catches missing fields at type-check time
4. **Loggable**: All inputs captured in one place
5. **Transactional**: Service controls session boundaries
6. **Traceable**: One service per command makes debugging obvious

---

## Services by Domain

### Note Services

**Location**: `backend/src/pilot_space/application/services/note/`

#### CreateNoteService

```python
@dataclass
class CreateNotePayload:
    workspace_id: UUID
    owner_id: UUID
    title: str
    content: dict[str, Any] | None = None  # TipTap JSON
    summary: str | None = None
    project_id: UUID | None = None
    template_id: UUID | None = None  # Copy from template
    is_pinned: bool = False

@dataclass
class CreateNoteResult:
    note: Note
    word_count: int = 0
    reading_time_mins: int = 0
    template_applied: bool = False

class CreateNoteService:
    async def execute(self, payload: CreateNotePayload) -> CreateNoteResult:
        """Create note with optional template copying."""
```

**Responsibilities**:
- Validate title (not empty, < 255 chars)
- Copy content from template if provided
- Calculate word count and reading time
- Persist note
- Return metadata

**Usage Example**:
```python
service = CreateNoteService(session=session)
result = await service.execute(
    CreateNotePayload(
        workspace_id=workspace.id,
        owner_id=user.id,
        title="Design Review Notes",
        is_pinned=True,
    )
)
return NoteResponse.from_domain(result.note)
```

#### UpdateNoteService

Updates note blocks, metadata, with smart content diffing.

```python
@dataclass
class UpdateNotePayload:
    workspace_id: UUID
    note_id: UUID
    title: str | None = None
    content: dict[str, Any] | None = None  # Replaces all blocks
    summary: str | None = None
    is_pinned: bool | None = None

@dataclass
class UpdateNoteResult:
    note: Note
    changed_fields: list[str]
```

**Key Feature**: Tracks which fields changed for activity logging.

#### GetNoteService

Retrieves note with eager-loaded relationships (annotations, discussions, issue links).

```python
@dataclass
class GetNotePayload:
    workspace_id: UUID
    note_id: UUID

@dataclass
class GetNoteResult:
    note: Note
    annotation_count: int
    discussion_count: int
    linked_issue_count: int
```

**Best Practices**:
- Always uses eager loading (`.options(joinedload(...))`)
- Verifies workspace membership before returning
- Scoped by `workspace_id` (RLS enforcement)

#### CreateNoteFromChatService

Converts chat session to persistent note (for saving conversations).

```python
@dataclass
class CreateNoteFromChatPayload:
    workspace_id: UUID
    user_id: UUID
    chat_session_id: UUID
    title: str

@dataclass
class CreateNoteFromChatResult:
    note: Note
    message_count: int
```

#### AIUpdateService

Applies AI-generated content updates to notes (from AI enhancement workflows).

```python
@dataclass
class AIUpdatePayload:
    workspace_id: UUID
    note_id: UUID
    updates: list[dict]  # Block updates from AI
    ai_metadata: dict[str, Any]

@dataclass
class AIUpdateResult:
    note: Note
    blocks_updated: int
    activity_id: UUID
```

---

### Issue Services

**Location**: `backend/src/pilot_space/application/services/issue/`

#### CreateIssueService

Most complex service. Handles sequence ID generation, state defaults, label attachment.

```python
@dataclass
class CreateIssuePayload:
    # Required
    workspace_id: UUID
    project_id: UUID
    reporter_id: UUID
    name: str

    # Optional (sensible defaults)
    description: str | None = None
    description_html: str | None = None
    priority: IssuePriority = IssuePriority.NONE
    state_id: UUID | None = None  # Uses project default if None
    assignee_id: UUID | None = None
    cycle_id: UUID | None = None
    module_id: UUID | None = None
    parent_id: UUID | None = None
    estimate_points: int | None = None
    start_date: date | None = None
    target_date: date | None = None
    label_ids: list[UUID] = field(default_factory=list)

    # AI enhancement
    ai_metadata: dict[str, Any] | None = None
    ai_enhanced: bool = False

@dataclass
class CreateIssueResult:
    issue: Issue
    activities: list[Activity]
    ai_enhanced: bool = False
```

**Implementation Flow**:

```python
async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
    # 1. Validate name (non-empty, <255 chars)
    if not payload.name or len(payload.name) > 255:
        raise ValueError("Issue name is required and <255 chars")

    # 2. Get next sequence ID (race-safe via database constraint)
    seq_id = await self._issue_repo.get_next_sequence_id(payload.project_id)

    # 3. Get default state if not provided
    state_id = payload.state_id or await self._get_default_state_id(payload.project_id)

    # 4. Create and persist domain entity
    issue = Issue(
        workspace_id=payload.workspace_id,
        project_id=payload.project_id,
        sequence_id=seq_id,
        name=payload.name.strip(),
        state_id=state_id,
        # ... other fields
    )
    issue = await self._issue_repo.create(issue)

    # 5. Attach labels + create activity records
    if payload.label_ids:
        await self._issue_repo.bulk_update_labels(issue.id, payload.label_ids)

    activities = [await self._activity_repo.create(
        Activity.create_for_issue_creation(payload.workspace_id, issue.id, ...)
    )]

    return CreateIssueResult(issue=issue, activities=activities)
```

**Key Points**:
- Sequence ID race-safe via database constraint (SELECT FOR UPDATE)
- Default state required; raises if not found
- Activity logging for audit trail
- Eager load relationships before response

#### UpdateIssueService

Field-level change detection with sentinel `UNCHANGED` to distinguish "no change" from "set to null".

**Returns**: `changed_fields` list for client-side optimistic updates. Creates activity records for all mutations.

#### ListIssuesService

Paginated search with filters (state, assignee, cycle, labels, search text). Supports cursor-based pagination for scalability. Full-text search via Meilisearch. All queries RLS-scoped by workspace_id.

#### GetIssueService

Retrieves single issue with full relationships, activity history, and context. Optional related issues + linked notes.

#### ActivityService

Logs all issue mutations for audit trail and activity feed. Activity types: CREATED, UPDATED, STATE_CHANGED, ASSIGNED, LABELED, AI_ENHANCED, DELETED.

---

### Cycle Services

**Location**: `backend/src/pilot_space/application/services/cycle/`

#### CreateCycleService

Creates sprint/cycle with date validation. Validates: name required, end_date >= start_date, only one ACTIVE cycle per project.

#### UpdateCycleService

Updates cycle with constraint verification. Cannot set ACTIVE if issues exceed capacity. Auto-deactivates other ACTIVE cycles.

#### GetCycleService

Retrieves cycle with velocity metrics, issue counts by state, and burn-down data.

#### AddIssueToCycleService

Assigns issue to cycle with state validation. Constraints: state must support cycle (not Backlog/Done), cycle must be ACTIVE/DRAFT.

#### RolloverCycleService

Completes cycle: archives Done issues, carries over In Progress → Todo to next cycle. Calculates velocity metrics. Logs activities for audit trail.

---

### AI Context Services

**Location**: `backend/src/pilot_space/application/services/ai_context/`

These services aggregate context for AI agents to reason about issues.

#### GenerateAIContextService

**Most complex service.** Aggregates: related issues (embeddings), linked notes, code references (GitHub), historical context. Features: 1hr cache with Redis, Gemini 768-dim embeddings, semantic similarity (0.7 threshold), complexity detection, Claude Code prompt generation via AIContextAgent (Sonnet).

#### RefineAIContextService

Improves context quality based on user feedback. Accepts missing_info list and generates additional context.

#### ExportAIContextService

Exports context to markdown/JSON/claude_dev formats for sharing or integration.

---

### Annotation Services

**Location**: `backend/src/pilot_space/application/services/annotation/`

#### CreateAnnotationService

Creates AI margin suggestions on note blocks. Validates: confidence [0.0-1.0], non-empty content, block exists. High confidence threshold: >=0.8.

---

### Discussion Services

**Location**: `backend/src/pilot_space/application/services/discussion/`

#### CreateDiscussionService

Atomically creates discussion thread + first comment in single transaction. Rollback on failure.

---

### Integration Services

**Location**: `backend/src/pilot_space/application/services/integration/`

#### ConnectGitHubService

OAuth code exchange, token encryption via Supabase Vault (AES-256-GCM), user info fetch.

#### ProcessWebhookService

Handles GitHub webhook events (push, PR, release). HMAC-SHA256 signature verification.

#### LinkCommitService

Auto-links commits to issues by parsing "Fixes #42", "Closes #123" from commit messages.

#### AutoTransitionService

Auto-transitions issues based on webhook events: PR opened → In Review, PR merged → Done, Commit pushed → In Progress.

---

### Onboarding Services

**Location**: `backend/src/pilot_space/application/services/onboarding/`

#### CreateGuidedNoteService, GetOnboardingService, UpdateOnboardingService

Manages onboarding workflow: creates template notes, tracks progress, marks steps complete.

---

### Role Skill Services

**Location**: `backend/src/pilot_space/application/services/role_skill/`

Manages role-based skill assignments (developer, designer, pm). Services: Create, Update, Generate, List.

---

### Homepage Services

**Location**: `backend/src/pilot_space/application/services/homepage/`

Services: GetActivityService (workspace activity feed), GetDigestService (weekly/daily digest), DismissSuggestionService.

---

### Workspace Service

**Location**: `backend/src/pilot_space/application/services/workspace.py`

Invites member to workspace: immediate add if user exists, pending invitation if not. Auto-accepts on signup.

---

## Service Composition & Dependency Injection

### How Services Are Instantiated

**In Router** (preferred):

```python
@router.post("/issues")
async def create_issue(
    payload: IssueCreateRequest,
    session: DbSession,  # Injected by FastAPI
):
    service = CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        activity_repository=ActivityRepository(session),
        label_repository=LabelRepository(session),
    )
    result = await service.execute(...)
    return result
```

**Via Container** (for complex setups):

```python
# In container.py
class Container(containers.DeclarativeContainer):
    issue_repo = providers.Factory(IssueRepository, session=session_factory)
    activity_repo = providers.Factory(ActivityRepository, session=session_factory)
    create_issue_service = providers.Factory(
        CreateIssueService,
        session=session_factory,
        issue_repository=issue_repo,
        activity_repository=activity_repo,
        label_repository=label_repo,
    )

# In router
@router.post("/issues")
async def create_issue(
    payload: IssueCreateRequest,
    service: Annotated[CreateIssueService, Depends(container.create_issue_service)],
):
    result = await service.execute(...)
```

**Singletons vs Factories**:
- **Singletons**: Config, Engine, SessionFactory, ResilientExecutor
- **Factories**: Repositories, Services (new instance per request)

---

## Payload & Result Patterns

### Payload Design

**Rule**: One @dataclass per operation, optional fields have sensible defaults.

```python
# Good: Explicit defaults
@dataclass
class UpdateIssuePayload:
    issue_id: UUID
    actor_id: UUID
    name: str | _Unchanged = UNCHANGED  # Explicit: no change
    description: str | None | _Unchanged = UNCHANGED  # Explicit: no change

# Bad: No way to distinguish "no change" from "set to None"
@dataclass
class UpdateIssuePayload:
    issue_id: UUID
    actor_id: UUID
    name: str | None = None  # Ambiguous!
```

### Result Design

**Rule**: Always include computed metadata beyond the domain entity.

```python
# Good: Includes computed fields
@dataclass
class CreateIssueResult:
    issue: Issue  # Domain entity
    activities: list[Activity]  # Related entities
    ai_enhanced: bool  # Metadata about operation

# Bad: Just returns entity
@dataclass
class CreateIssueResult:
    issue: Issue  # What changed? What was logged?
```

---

## Transaction Boundaries

### Session Lifecycle

Each service receives `AsyncSession` (NOT sessionmaker). Session created per request, passed to service.

```python
# Request middleware creates session
async with get_session() as session:
    # Pass to service
    service = CreateIssueService(..., session=session)
    result = await service.execute(payload)
    # Session auto-commits on exit (if no exception)
    # Rollback on exception
```

### Explicit Transaction Control

For services spanning multiple operations:

```python
async def execute(self, payload: SomePayload) -> SomeResult:
    async with self._session.begin():  # Explicit transaction
        # Multiple operations here
        obj1 = await self._repo1.create(...)
        obj2 = await self._repo2.create(...)
        # Commits only if both succeed
```

### No Nested Transactions

SQLAlchemy async uses savepoints for nested transactions. Generally avoid:

```python
# Avoid: Hard to reason about
async with session.begin():
    async with session.begin_nested():  # Savepoint
        ...
```

---

## Error Handling in Services

**Pattern**: Raise `ValueError` or custom exceptions. Let middleware convert to RFC 7807.

```python
async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
    # Validation errors
    if not payload.name:
        raise ValueError("Issue name is required")

    # Business logic errors
    if await self._check_duplicate(payload.name):
        raise ValueError("Issue with this name already exists")

    # Not found errors
    state = await self._state_repo.get_by_id(payload.state_id)
    if not state:
        raise ValueError(f"State not found: {payload.state_id}")

    # All raised as-is; middleware converts to 400/404 depending on code
```

**Error Handler** (in main.py):

```python
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={
            "type": "/errors/validation-error",
            "title": "Validation failed",
            "status": 400,
            "detail": str(exc),
            "instance": str(request.url),
        }
    )
```

---

## Best Practices

### 1. Keep Services Focused

**Each service = one command or query.**

❌ Wrong:
```python
class IssueService:
    async def create_and_assign(self, ...):  # Two operations
    async def create_and_add_to_cycle(self, ...):  # Two operations
    async def bulk_create(self, ...):  # One command, but composite
```

✅ Right:
```python
class CreateIssueService:
    async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult

class AssignIssueService:
    async def execute(self, payload: AssignIssuePayload) -> AssignIssueResult

class BulkCreateIssuesService:
    async def execute(self, payload: BulkCreateIssuesPayload) -> BulkCreateIssuesResult
```

### 2. Validate at Boundaries

**Payloads should be validated by Pydantic v2 in router, not in service.**

```python
# In router (API boundary)
@router.post("/issues")
async def create_issue(
    payload: IssueCreateRequest,  # Pydantic validates shape
    session: DbSession,
):
    service = CreateIssueService(...)
    # Payload is already valid
    result = await service.execute(
        CreateIssuePayload(
            workspace_id=...,
            name=payload.name,  # Safe
            ...
        )
    )

# Service focuses on business logic validation, not shape validation
```

### 3. Use Eager Loading

**Every repository query must eager-load relationships to prevent N+1.**

```python
# Bad: N+1 queries in response serialization
issues = await session.execute(select(Issue))
for issue in issues.scalars():
    assignee = issue.assignee  # Query per issue!

# Good: Eager load
issues = await session.execute(
    select(Issue).options(
        joinedload(Issue.assignee),
        joinedload(Issue.project),
        joinedload(Issue.labels),
    )
)
```

### 4. Log Strategically

**Log at boundaries (entry, exit, errors). Don't log inside loops.**

```python
async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
    logger.info(
        "Creating issue",
        extra={
            "workspace_id": str(payload.workspace_id),
            "project_id": str(payload.project_id),
            "reporter_id": str(payload.reporter_id),
        }
    )

    # ... execution ...

    logger.info(
        "Issue created",
        extra={
            "issue_id": str(result.issue.id),
            "sequence_id": result.issue.sequence_id,
        }
    )
    return result
```

### 5. Test Services, Not Routers

**Services are testable in isolation. Test via `service.execute()` not HTTP.**

```python
# Good: Direct service testing
@pytest.mark.asyncio
async def test_create_issue_service():
    service = CreateIssueService(
        session=session,
        issue_repository=IssueRepository(session),
        ...
    )
    result = await service.execute(CreateIssuePayload(...))
    assert result.issue.id is not None
    assert result.issue.sequence_id == 1

# Bad: HTTP testing (slower, less control)
response = client.post("/api/v1/issues", json={"name": "..."})
assert response.status_code == 201
```

### 6. Handle Soft Deletes

**Services should respect `is_deleted` flag. Never hard delete.**

```python
async def delete_issue(self, issue_id: UUID) -> None:
    # Don't delete; soft delete
    issue = await self._repo.get_by_id(issue_id)
    issue.is_deleted = True
    await self._repo.update(issue)
```

### 7. Avoid Mutable Default Arguments

```python
# Bad: Mutable default is shared across calls
@dataclass
class Payload:
    label_ids: list[UUID] = []  # Danger!

# Good: Use field default factory
@dataclass
class Payload:
    label_ids: list[UUID] = field(default_factory=list)
```

---

## Common Patterns

### Pattern: State Transitions with Constraints

```python
async def transition_issue_state(
    self,
    issue_id: UUID,
    new_state_id: UUID,
    actor_id: UUID,
) -> UpdateIssueResult:
    """Transition issue with constraint validation."""
    issue = await self._issue_repo.get_by_id(issue_id)
    new_state = await self._state_repo.get_by_id(new_state_id)

    # Validate transition
    if not self._can_transition(issue.state, new_state):
        raise ValueError(
            f"Cannot transition from {issue.state.name} to {new_state.name}"
        )

    # If moving to In Progress, require cycle
    if new_state.group == StateGroup.IN_PROGRESS and not issue.cycle_id:
        raise ValueError(
            "In Progress issues must be assigned to a cycle"
        )

    # Update
    issue.state_id = new_state_id
    issue = await self._issue_repo.update(issue)

    # Activity
    activity = Activity.create_for_state_change(
        workspace_id=issue.workspace_id,
        issue_id=issue.id,
        actor_id=actor_id,
        old_state=...,
        new_state=new_state,
    )
    await self._activity_repo.create(activity)

    return UpdateIssueResult(issue=issue, activities=[activity])
```

### Pattern: Bulk Operations

```python
async def bulk_assign_issues(
    self,
    workspace_id: UUID,
    issue_ids: list[UUID],
    assignee_id: UUID,
    actor_id: UUID,
) -> BulkAssignResult:
    """Assign multiple issues to same person."""
    issues = await self._issue_repo.get_many_by_ids(issue_ids)

    # Update all
    for issue in issues:
        issue.assignee_id = assignee_id
        await self._issue_repo.update(issue)

    # Create activities
    activities = [
        Activity.create_for_assignment(
            workspace_id=workspace_id,
            issue_id=issue.id,
            actor_id=actor_id,
            assignee_id=assignee_id,
        )
        for issue in issues
    ]
    for activity in activities:
        await self._activity_repo.create(activity)

    return BulkAssignResult(
        issues=issues,
        activities=activities,
        total=len(issues),
    )
```

### Pattern: Caching with TTL

```python
async def get_issue_context(
    self,
    issue_id: UUID,
    force_refresh: bool = False,
) -> IssueContext:
    """Get cached context or generate if missing/stale."""
    # Check cache
    cache_key = f"issue_context:{issue_id}"
    if not force_refresh:
        cached = await self._cache.get(cache_key)
        if cached:
            return json.loads(cached)

    # Generate
    context = await self._generate_context(issue_id)

    # Cache (1 hour)
    await self._cache.setex(cache_key, 3600, json.dumps(context))

    return context
```

---

## Generation Metadata

- **Scope**: 8 domain services, 32 individual service classes
- **Payloads**: 40+ @dataclass payloads (validated at API boundary)
- **Results**: 40+ @dataclass results (typed outputs)
- **Patterns Detected**:
  - CQRS-lite: `Service.execute(Payload) → Result` pattern in every service
  - Payload validation: Optional fields with sensible defaults
  - Result enrichment: Always includes computed metadata
  - Transaction boundaries: Session per request, explicit `async with session.begin()`
  - Activity logging: All mutations logged for audit trail
  - Eager loading: All repository queries use `.options(joinedload(...))`
  - Error handling: ValueError raised, converted to RFC 7807 by middleware

- **Coverage**:
  - Note CRUD: Create, Update, Get, CreateFromChat, AIUpdate
  - Issue CRUD: Create, Update, List, Get, Activity logging
  - Cycle management: Create, Update, Get, AddToIssue, Rollover
  - AI context: Generate, Refine, Export
  - Annotations: Create
  - Discussions: Create (with first comment)
  - Integrations: GitHub OAuth, Webhook processing, Commit linking, Auto-transition
  - Onboarding: Create guided note, Get progress, Update progress
  - Role skills: Create, Update, Generate, List
  - Homepage: Get activity, Get digest, Dismiss suggestion
  - Workspace: Invite member

- **Key Dependencies**:
  - AsyncSession (database)
  - Repositories: IssueRepository, NoteRepository, CycleRepository, AIContextRepository, etc.
  - External: GitHubClient (OAuth), EmbeddingClient (semantic search), AIContextAgent
  - Infrastructure: CacheClient (Redis), IntegrationLinkRepository

---

## Related Documentation

See parent guide for context:

- **Backend architecture**: `backend/CLAUDE.md` (5-layer Clean Architecture overview)
- **Repository pattern**: `backend/src/pilot_space/infrastructure/database/repositories/` (BaseRepository[T], eager loading, RLS)
- **Domain entities**: `backend/src/pilot_space/domain/` (rich domain models)
- **Routers**: `backend/src/pilot_space/api/v1/` (API endpoints using services)
- **Testing**: `backend/tests/unit/services/`, `backend/tests/integration/` (service test examples)
- **Design decisions**: `docs/DESIGN_DECISIONS.md` (DD-064: CQRS-lite, DD-001: async-first)
- **Dev patterns**: `docs/dev-pattern/45-pilot-space-patterns.md` (project-specific overrides)

---

## Standards Summary

**For all application services**:

- [ ] One `@dataclass` payload per operation
- [ ] Optional fields have sensible defaults (use `field(default_factory=...)` for mutables)
- [ ] One `@dataclass` result per operation with computed metadata
- [ ] Async method named `execute(payload: Payload) → Result`
- [ ] Validation in payload shape (Pydantic) + business logic (service)
- [ ] All database access via repositories (never direct SQLAlchemy)
- [ ] Eager load all relationships (`.options(joinedload(...))`)
- [ ] Log entry + exit with correlation IDs
- [ ] Raise `ValueError` for validation/business errors
- [ ] Create activity records for all mutations
- [ ] Tests cover happy path + 2 edge cases
- [ ] Coverage >80% (run `pytest --cov=.`)
- [ ] No TODOs, mocks, or placeholders
- [ ] Type hints on all parameters and returns (pyright strict mode)
