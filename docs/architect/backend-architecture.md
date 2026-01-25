# Backend Architecture

**Framework**: FastAPI + SQLAlchemy 2.0 (async) + Alembic
**Architecture**: Clean Architecture + DDD + CQRS-lite
**AI SDK**: Claude Agent SDK for AI orchestration
**Runtime**: Python 3.12+
**Platform**: Supabase (Auth, DB, Storage, Queues)

---

## CQRS-lite Pattern (Session 2026-01-22)

Pilot Space uses **CQRS-lite** (Command Query Responsibility Segregation without Event Sourcing):

| Concept | Implementation | Notes |
|---------|----------------|-------|
| **Commands** | Service Classes | `CreateIssueService.execute(payload)` |
| **Queries** | Service Classes | `GetIssueService.execute(payload)` |
| **Separation** | Different models | Command uses domain entity, Query can use ORM directly |
| **Event Sourcing** | Not used (MVP) | Domain events for side effects only |
| **Read Replicas** | Prepared for | Query services can switch to read replica later |

### Why CQRS-lite?

- **Simpler than full CQRS**: No event store, no projection rebuilding
- **Better than anemic services**: Services have single responsibility
- **Testable**: Each service is independently testable
- **Scalable**: Can add read replicas without changing application code

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  api/v1/routers/     │  api/v1/schemas/      │  api/webhooks/         │  │
│  │  (FastAPI Routers)   │  (Pydantic DTOs)      │  (GitHub, Slack)       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                              APPLICATION LAYER                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  application/services/     │  application/interfaces/                 │  │
│  │  (Command/Query services)  │  (Ports for infrastructure)              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                DOMAIN LAYER                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  domain/entities/   │  domain/value_objects/  │  domain/events/       │  │
│  │  domain/services/   │  domain/repositories/   │  domain/exceptions/   │  │
│  │  (Interfaces only)  │  (ABC interfaces)       │                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                            INFRASTRUCTURE LAYER                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  infrastructure/    │  infrastructure/   │  infrastructure/           │  │
│  │  persistence/       │  external/         │  queue/                    │  │
│  │  (SQLAlchemy impl)  │  (GitHub, Slack,   │  (Supabase Queues/pgmq)    │  │
│  │                     │   LLM providers)   │                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                 AI LAYER                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ai/orchestrator/   │  ai/providers/     │  ai/agents/                │  │
│  │  (Task routing)     │  (LLM adapters)    │  (Domain-specific agents)  │  │
│  │  ai/rag/            │  ai/prompts/       │                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### 1. Presentation Layer (`api/`)

**Purpose**: Handle HTTP requests, validation, serialization, and response formatting.

**Components**:
- **Routers**: FastAPI route definitions
- **Schemas**: Pydantic request/response DTOs
- **Middleware**: Auth, error handling, rate limiting
- **Webhooks**: Inbound webhook handlers (GitHub, Slack)

**Rules**:
- No business logic
- Transform external data to service payloads
- Transform service results to HTTP responses
- Handle authentication/authorization checks

```python
# api/v1/routers/issues.py
from fastapi import APIRouter, Depends, HTTPException, status
from pilot_space.api.v1.schemas.issue import CreateIssueRequest, IssueResponse
from pilot_space.application.services.issue.create_issue import CreateIssueService
from pilot_space.api.dependencies import get_current_user, get_service

router = APIRouter(prefix="/issues", tags=["issues"])

@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    request: CreateIssueRequest,
    current_user: User = Depends(get_current_user),
    service: CreateIssueService = Depends(get_service(CreateIssueService)),
):
    """Create a new issue with optional AI enhancement."""
    payload = CreateIssuePayload(
        project_id=str(request.project_id),
        title=request.title,
        description=request.description,
        priority=request.priority,
        created_by_id=str(current_user.id),
    )

    result = await service.execute(payload)

    return IssueResponse.from_domain(result.issue, result.ai_suggestions)
```

### 2. Application Layer (`application/`)

**Purpose**: Orchestrate services, coordinate domain logic, handle transactions.

**Components**:
- **Services**: Single-responsibility command/query handlers
- **Payloads**: Input DTOs for services (replacing Command/Query naming)
- **Interfaces**: Ports for infrastructure (UoW, event publisher)

**Rules**:
- One service per file
- Services orchestrate, don't contain business logic
- Transaction boundaries at service level
- Publish domain events after commit

```python
# application/services/issue/create_issue.py
from dataclasses import dataclass
from pilot_space.domain.entities.issue import Issue
from pilot_space.domain.repositories.issue_repository import IssueRepository
from pilot_space.application.interfaces.unit_of_work import UnitOfWork

@dataclass
class CreateIssuePayload:
    """Input payload for CreateIssueService."""
    project_id: str
    title: str
    description: str | None
    priority: str | None
    created_by_id: str

@dataclass
class CreateIssueResult:
    issue: Issue
    ai_suggestions: dict | None

class CreateIssueService:
    """Service to create a new issue with optional AI enhancement."""

    def __init__(
        self,
        uow: UnitOfWork,
        issue_repo: IssueRepository,
        project_repo: ProjectRepository,
        ai_orchestrator: AIOrchestrator,
    ):
        self._uow = uow
        self._issue_repo = issue_repo
        self._project_repo = project_repo
        self._ai = ai_orchestrator

    async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
        async with self._uow:
            # Validate project exists
            project = await self._project_repo.get_by_id(ProjectId(payload.project_id))
            if not project:
                raise ProjectNotFoundError(payload.project_id)

            # Get next sequence ID
            sequence_id = await self._issue_repo.get_next_sequence_id(project.id)

            # Create domain entity
            issue = Issue.create(
                project_id=project.id,
                sequence_id=sequence_id,
                title=payload.title,
                description=payload.description,
                priority=Priority.from_string(payload.priority) if payload.priority else None,
                created_by=UserId(payload.created_by_id),
            )

            # Get AI suggestions (non-blocking)
            ai_suggestions = await self._ai.enhance_issue(issue)

            # Persist
            await self._issue_repo.add(issue)
            await self._uow.commit()

            # Publish domain events
            for event in issue.pending_events:
                await self._uow.publish(event)

            return CreateIssueResult(issue=issue, ai_suggestions=ai_suggestions)
```

### 3. Domain Layer (`domain/`)

**Purpose**: Core business logic, entities, value objects, domain events.

**Components**:
- **Entities**: Aggregate roots and entities with behavior
- **Value Objects**: Immutable domain concepts
- **Services**: Pure domain logic that doesn't fit in entities
- **Repositories**: Interfaces (ABC) for data access
- **Events**: Domain events for cross-aggregate communication
- **Exceptions**: Domain-specific errors

**Rules**:
- Pure Python (no framework dependencies)
- No I/O operations
- Rich domain models with behavior
- Entities protect invariants
- Value objects are immutable

```python
# domain/entities/issue.py
from dataclasses import dataclass, field
from datetime import datetime
from pilot_space.domain.value_objects import IssueId, ProjectId, UserId, Priority, IssueState
from pilot_space.domain.events.issue_events import IssueCreated, IssueStateChanged

@dataclass
class Issue:
    id: IssueId
    project_id: ProjectId
    sequence_id: int
    title: str
    description: str | None
    state: IssueState
    priority: Priority | None
    assignee_id: UserId | None
    created_by: UserId
    created_at: datetime
    updated_at: datetime

    _pending_events: list = field(default_factory=list, repr=False)

    @classmethod
    def create(
        cls,
        project_id: ProjectId,
        sequence_id: int,
        title: str,
        description: str | None,
        priority: Priority | None,
        created_by: UserId,
    ) -> "Issue":
        """Factory method to create a new Issue with proper initialization."""
        if not title or len(title.strip()) == 0:
            raise InvalidIssueTitleError("Issue title cannot be empty")

        if len(title) > 255:
            raise InvalidIssueTitleError("Issue title cannot exceed 255 characters")

        issue = cls(
            id=IssueId.generate(),
            project_id=project_id,
            sequence_id=sequence_id,
            title=title.strip(),
            description=description,
            state=IssueState.backlog(),
            priority=priority,
            assignee_id=None,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        issue._pending_events.append(IssueCreated(issue_id=issue.id, project_id=project_id))
        return issue

    def change_state(self, new_state: IssueState, changed_by: UserId) -> None:
        """Transition issue to a new state with validation."""
        if not self.state.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {self.state} to {new_state}"
            )

        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.utcnow()

        # Mark completed if entering completed state
        if new_state.is_completed and not old_state.is_completed:
            self.completed_at = datetime.utcnow()

        self._pending_events.append(
            IssueStateChanged(
                issue_id=self.id,
                old_state=old_state,
                new_state=new_state,
                changed_by=changed_by,
            )
        )

    def assign_to(self, assignee_id: UserId | None, assigned_by: UserId) -> None:
        """Assign issue to a user."""
        old_assignee = self.assignee_id
        self.assignee_id = assignee_id
        self.updated_at = datetime.utcnow()

        self._pending_events.append(
            IssueAssigned(
                issue_id=self.id,
                old_assignee=old_assignee,
                new_assignee=assignee_id,
                assigned_by=assigned_by,
            )
        )

    @property
    def identifier(self) -> str:
        """Return the human-readable identifier (e.g., PS-123)."""
        # Note: This would need project prefix injected or looked up
        return f"#{self.sequence_id}"

    @property
    def pending_events(self) -> list:
        """Return pending domain events (read-only copy)."""
        return self._pending_events.copy()

    def clear_events(self) -> None:
        """Clear pending events after publishing."""
        self._pending_events.clear()
```

```python
# domain/value_objects/issue_state.py
from dataclasses import dataclass
from enum import Enum

class StateGroup(Enum):
    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class IssueState:
    name: str
    group: StateGroup
    color: str

    @classmethod
    def backlog(cls) -> "IssueState":
        return cls(name="Backlog", group=StateGroup.BACKLOG, color="#666666")

    @classmethod
    def todo(cls) -> "IssueState":
        return cls(name="Todo", group=StateGroup.UNSTARTED, color="#3b82f6")

    @classmethod
    def in_progress(cls) -> "IssueState":
        return cls(name="In Progress", group=StateGroup.STARTED, color="#f59e0b")

    @classmethod
    def done(cls) -> "IssueState":
        return cls(name="Done", group=StateGroup.COMPLETED, color="#22c55e")

    @property
    def is_completed(self) -> bool:
        return self.group == StateGroup.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        return self.group == StateGroup.CANCELLED

    def can_transition_to(self, new_state: "IssueState") -> bool:
        """Define valid state transitions."""
        # Cancelled is terminal
        if self.group == StateGroup.CANCELLED:
            return False

        # Can always go to cancelled
        if new_state.group == StateGroup.CANCELLED:
            return True

        # Allow any non-terminal transitions
        return True
```

### 4. Infrastructure Layer (`infrastructure/`)

**Purpose**: Implement interfaces defined by domain/application layers.

**Components**:
- **Persistence**: SQLAlchemy models, repository implementations, UoW
- **Cache**: Redis client (sessions, AI response cache)
- **Search**: Meilisearch client
- **Storage**: Supabase Storage client (S3-compatible)
- **Queue**: Supabase Queues (pgmq + pg_cron) for background tasks
- **Auth**: Supabase Auth client, JWT validation
- **External**: GitHub, Slack adapters, LLM provider adapters

**Rules**:
- Implement domain repository interfaces
- Handle all I/O concerns
- Map between ORM models and domain entities
- No business logic

```python
# infrastructure/persistence/repositories/sqlalchemy_issue_repo.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pilot_space.domain.entities.issue import Issue
from pilot_space.domain.repositories.issue_repository import IssueRepository
from pilot_space.domain.value_objects import IssueId, ProjectId
from pilot_space.infrastructure.persistence.models.issue import IssueModel

class SQLAlchemyIssueRepository(IssueRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, issue_id: IssueId) -> Issue | None:
        result = await self._session.execute(
            select(IssueModel).where(
                IssueModel.id == issue_id.value,
                IssueModel.is_deleted == False,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def add(self, issue: Issue) -> None:
        model = self._to_model(issue)
        self._session.add(model)

    async def update(self, issue: Issue) -> None:
        model = await self._session.get(IssueModel, issue.id.value)
        if model:
            self._update_model(model, issue)

    async def get_next_sequence_id(self, project_id: ProjectId) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(IssueModel.sequence_id), 0) + 1)
            .where(IssueModel.project_id == project_id.value)
        )
        return result.scalar_one()

    async def find_by_project(
        self,
        project_id: ProjectId,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Issue]:
        query = select(IssueModel).where(
            IssueModel.project_id == project_id.value,
            IssueModel.is_deleted == False,
        )

        if state:
            query = query.where(IssueModel.state_name == state)

        query = query.order_by(IssueModel.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self._session.execute(query)
        return [self._to_domain(model) for model in result.scalars()]

    def _to_domain(self, model: IssueModel) -> Issue:
        """Map ORM model to domain entity."""
        return Issue(
            id=IssueId(model.id),
            project_id=ProjectId(model.project_id),
            sequence_id=model.sequence_id,
            title=model.name,
            description=model.description,
            state=IssueState(
                name=model.state_name,
                group=StateGroup(model.state_group),
                color=model.state_color,
            ),
            priority=Priority(model.priority) if model.priority else None,
            assignee_id=UserId(model.assignee_id) if model.assignee_id else None,
            created_by=UserId(model.reporter_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Issue) -> IssueModel:
        """Map domain entity to ORM model."""
        return IssueModel(
            id=entity.id.value,
            project_id=entity.project_id.value,
            sequence_id=entity.sequence_id,
            name=entity.title,
            description=entity.description,
            state_name=entity.state.name,
            state_group=entity.state.group.value,
            state_color=entity.state.color,
            priority=entity.priority.value if entity.priority else None,
            assignee_id=entity.assignee_id.value if entity.assignee_id else None,
            reporter_id=entity.created_by.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
```

---

## Dependency Injection

Use `dependency-injector` for wiring components:

```python
# container.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pilot_space.infrastructure.persistence.repositories import (
    SQLAlchemyIssueRepository,
    SQLAlchemyProjectRepository,
)
from pilot_space.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from pilot_space.application.services.issue.create_issue import CreateIssueService
from pilot_space.ai.orchestrator import AIOrchestrator

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Database
    db_engine = providers.Singleton(
        create_async_engine,
        config.database_url,
        echo=config.debug,
    )

    session_factory = providers.Factory(
        AsyncSession,
        bind=db_engine,
        expire_on_commit=False,
    )

    # Unit of Work
    uow = providers.Factory(
        SQLAlchemyUnitOfWork,
        session_factory=session_factory,
    )

    # Repositories
    issue_repository = providers.Factory(
        SQLAlchemyIssueRepository,
        session=session_factory,
    )

    project_repository = providers.Factory(
        SQLAlchemyProjectRepository,
        session=session_factory,
    )

    # AI Orchestrator
    ai_orchestrator = providers.Singleton(
        AIOrchestrator,
        config=config.ai,
    )

    # Application Services
    create_issue_service = providers.Factory(
        CreateIssueService,
        uow=uow,
        issue_repo=issue_repository,
        project_repo=project_repository,
        ai_orchestrator=ai_orchestrator,
    )
```

---

## Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOW                                     │
└──────────────────────────────────────────────────────────────────────────────┘

1. HTTP Request arrives
        │
        ▼
┌───────────────────┐
│    Middleware     │ ◄── Auth, Rate Limit, Correlation ID
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│     Router        │ ◄── Validate request, create Payload
│   (Presentation)  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│     Service       │ ◄── Orchestrate domain logic
│   (Application)   │     Begin transaction (UoW)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Domain Entity    │ ◄── Execute business rules
│     (Domain)      │     Emit domain events
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Repository      │ ◄── Persist changes
│ (Infrastructure)  │     Map entity ↔ ORM model
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Commit + Publish│ ◄── Commit transaction
│      Events       │     Publish domain events
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Response Schema  │ ◄── Map domain to response DTO
│   (Presentation)  │
└─────────┬─────────┘
          │
          ▼
     HTTP Response
```

---

## Error Handling (RFC 7807 Problem Details)

Pilot Space uses **RFC 7807 Problem Details** for all error responses (per Constitution v1.1.0).

### Domain Exceptions

```python
# domain/exceptions/base.py
from dataclasses import dataclass

@dataclass
class DomainError(Exception):
    """Base exception for domain errors with RFC 7807 support."""
    type: str
    title: str
    detail: str
    status: int = 400

class IssueError(DomainError):
    """Base exception for issue domain errors."""
    pass

class IssueNotFoundError(IssueError):
    def __init__(self, issue_id: str):
        super().__init__(
            type="https://api.pilotspace.io/errors/issue-not-found",
            title="Issue Not Found",
            detail=f"Issue with ID '{issue_id}' does not exist or has been deleted.",
            status=404,
        )
        self.issue_id = issue_id

class InvalidIssueTitleError(IssueError):
    def __init__(self, reason: str):
        super().__init__(
            type="https://api.pilotspace.io/errors/invalid-issue-title",
            title="Invalid Issue Title",
            detail=reason,
            status=400,
        )

class InvalidStateTransitionError(IssueError):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            type="https://api.pilotspace.io/errors/invalid-state-transition",
            title="Invalid State Transition",
            detail=f"Cannot transition issue from '{from_state}' to '{to_state}'.",
            status=400,
        )
```

### RFC 7807 Response Schema

```python
# api/v1/schemas/error.py
from pydantic import BaseModel, Field

class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response."""
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Short summary of the problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation")
    instance: str | None = Field(None, description="URI reference to specific occurrence")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "https://api.pilotspace.io/errors/issue-not-found",
                "title": "Issue Not Found",
                "status": 404,
                "detail": "Issue with ID 'abc-123' does not exist.",
                "instance": "/api/v1/issues/abc-123"
            }
        }
```

### Global Error Handler

```python
# api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from pilot_space.domain.exceptions import DomainError

async def domain_exception_handler(request: Request, exc: DomainError):
    """Convert DomainError to RFC 7807 Problem Details response."""
    return JSONResponse(
        status_code=exc.status,
        content={
            "type": exc.type,
            "title": exc.title,
            "status": exc.status,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
        media_type="application/problem+json",
    )

# Register in main.py
app.add_exception_handler(DomainError, domain_exception_handler)
```

---

## Testing Strategy

### Unit Tests (Domain + Application)

```python
# tests/unit/domain/test_issue.py
import pytest
from pilot_space.domain.entities.issue import Issue
from pilot_space.domain.value_objects import ProjectId, UserId, IssueState

def test_create_issue():
    issue = Issue.create(
        project_id=ProjectId.generate(),
        sequence_id=1,
        title="Fix login bug",
        description="Users cannot login",
        priority=None,
        created_by=UserId.generate(),
    )

    assert issue.title == "Fix login bug"
    assert issue.state.group.value == "backlog"
    assert len(issue.pending_events) == 1

def test_create_issue_empty_title_raises():
    with pytest.raises(InvalidIssueTitleError):
        Issue.create(
            project_id=ProjectId.generate(),
            sequence_id=1,
            title="",
            description=None,
            priority=None,
            created_by=UserId.generate(),
        )

def test_state_transition():
    issue = Issue.create(...)
    issue.change_state(IssueState.in_progress(), UserId.generate())

    assert issue.state.name == "In Progress"
    assert len(issue.pending_events) == 2  # Created + StateChanged
```

### Integration Tests (Repository + Database)

```python
# tests/integration/test_issue_repository.py
import pytest
from pilot_space.infrastructure.persistence.repositories import SQLAlchemyIssueRepository

@pytest.mark.asyncio
async def test_add_and_retrieve_issue(db_session):
    repo = SQLAlchemyIssueRepository(db_session)

    issue = Issue.create(...)
    await repo.add(issue)
    await db_session.commit()

    retrieved = await repo.get_by_id(issue.id)

    assert retrieved is not None
    assert retrieved.title == issue.title
```

---

## Related Documents

- [Project Structure](./project-structure.md) - Full directory layout
- [Design Patterns](./design-patterns.md) - Detailed patterns
- [AI Layer](./ai-layer.md) - AI architecture with Claude Agent SDK
- [Infrastructure](./infrastructure.md) - Supabase platform setup
- [RLS Patterns](./rls-patterns.md) - Row-Level Security policies
- [Feature-Story Mapping](./feature-story-mapping.md) - User stories to components
- [Data Model](../../specs/001-pilot-space-mvp/data-model.md) - Entity definitions
- [Constitution](../../.specify/memory/constitution.md) - Technology standards
