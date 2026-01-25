# Design Patterns and Conventions

Architectural patterns, coding conventions, and best practices for the Pilot Space codebase.

---

## Backend Patterns

### 1. Repository Pattern

Abstract data access behind interfaces to decouple domain from persistence.

```python
# domain/repositories/issue_repository.py
from abc import ABC, abstractmethod
from pilot_space.domain.entities.issue import Issue
from pilot_space.domain.value_objects import IssueId, ProjectId

class IssueRepository(ABC):
    """Abstract repository interface for Issues."""

    @abstractmethod
    async def get_by_id(self, issue_id: IssueId) -> Issue | None:
        """Retrieve an issue by its ID."""
        pass

    @abstractmethod
    async def add(self, issue: Issue) -> None:
        """Add a new issue to the repository."""
        pass

    @abstractmethod
    async def update(self, issue: Issue) -> None:
        """Update an existing issue."""
        pass

    @abstractmethod
    async def delete(self, issue_id: IssueId) -> None:
        """Soft-delete an issue."""
        pass

    @abstractmethod
    async def find_by_project(
        self,
        project_id: ProjectId,
        filters: IssueFilters | None = None,
    ) -> list[Issue]:
        """Find issues by project with optional filters."""
        pass
```

```python
# infrastructure/persistence/repositories/sqlalchemy_issue_repo.py
class SQLAlchemyIssueRepository(IssueRepository):
    """SQLAlchemy implementation of IssueRepository."""

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

    def _to_domain(self, model: IssueModel) -> Issue:
        """Map ORM model to domain entity."""
        return Issue(
            id=IssueId(model.id),
            # ... mapping
        )
```

### 2. Unit of Work Pattern

Coordinate multiple repository operations in a single transaction.

```python
# application/interfaces/unit_of_work.py
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

class UnitOfWork(ABC):
    """Abstract Unit of Work interface."""

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        pass

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event after commit."""
        pass
```

```python
# infrastructure/persistence/unit_of_work.py
class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._pending_events: list[DomainEvent] = []

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        await self._session.commit()
        # Publish events after successful commit
        for event in self._pending_events:
            await self._publish_event(event)
        self._pending_events.clear()

    async def rollback(self) -> None:
        await self._session.rollback()
        self._pending_events.clear()

    async def publish(self, event: DomainEvent) -> None:
        self._pending_events.append(event)
```

### 3. Service / Payload Pattern

Encapsulate business operations in single-responsibility service handlers.

```python
# application/services/issue/create_issue.py
from dataclasses import dataclass

@dataclass(frozen=True)
class CreateIssuePayload:
    """Payload for creating a new issue."""
    project_id: str
    title: str
    description: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    created_by_id: str

@dataclass
class CreateIssueResult:
    """Result of issue creation."""
    issue: Issue
    ai_suggestions: dict | None = None

class CreateIssueService:
    """
    Service for creating a new issue.

    Orchestrates:
    - Validation
    - Domain entity creation
    - AI enhancement (optional)
    - Persistence
    - Event publishing
    """

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
            # 1. Validate project exists
            project = await self._project_repo.get_by_id(
                ProjectId(payload.project_id)
            )
            if not project:
                raise ProjectNotFoundError(payload.project_id)

            # 2. Create domain entity
            issue = Issue.create(
                project_id=project.id,
                sequence_id=await self._issue_repo.get_next_sequence_id(project.id),
                title=payload.title,
                description=payload.description,
                created_by=UserId(payload.created_by_id),
            )

            # 3. Get AI suggestions (non-blocking)
            ai_suggestions = None
            if self._ai.is_enabled:
                ai_suggestions = await self._ai.enhance_issue(issue)

            # 4. Persist
            await self._issue_repo.add(issue)
            await self._uow.commit()

            # 5. Queue domain events
            for event in issue.pending_events:
                await self._uow.publish(event)

            return CreateIssueResult(issue=issue, ai_suggestions=ai_suggestions)
```

### 4. Domain Events Pattern

Decouple aggregates through asynchronous event publishing.

```python
# domain/events/base.py
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass
class DomainEvent:
    """Base class for domain events."""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)

# domain/events/issue_events.py
@dataclass
class IssueCreated(DomainEvent):
    issue_id: IssueId
    project_id: ProjectId
    title: str
    created_by: UserId

@dataclass
class IssueStateChanged(DomainEvent):
    issue_id: IssueId
    old_state: IssueState
    new_state: IssueState
    changed_by: UserId

@dataclass
class IssueAssigned(DomainEvent):
    issue_id: IssueId
    old_assignee: UserId | None
    new_assignee: UserId | None
    assigned_by: UserId
```

```python
# infrastructure/messaging/event_handlers/issue_event_handler.py
from pilot_space.domain.events.issue_events import IssueCreated, IssueStateChanged

class IssueEventHandler:
    """Handles issue domain events."""

    def __init__(
        self,
        notification_service: NotificationService,
        search_indexer: SearchIndexer,
        embedding_indexer: EmbeddingIndexer,
    ):
        self._notifications = notification_service
        self._search = search_indexer
        self._embeddings = embedding_indexer

    async def handle_issue_created(self, event: IssueCreated) -> None:
        # Index for search
        await self._search.index_issue(event.issue_id)

        # Create embeddings
        await self._embeddings.index_entity("issue", event.issue_id)

        # Notify team
        await self._notifications.notify_issue_created(event)

    async def handle_state_changed(self, event: IssueStateChanged) -> None:
        # Notify assignee
        await self._notifications.notify_state_changed(event)

        # Update search index
        await self._search.update_issue_state(event.issue_id, event.new_state)
```

### 5. Value Object Pattern

Immutable objects representing domain concepts.

```python
# domain/value_objects/identifiers.py
from dataclasses import dataclass
from uuid import UUID, uuid4

@dataclass(frozen=True)
class EntityId:
    """Base class for entity identifiers."""
    value: UUID

    @classmethod
    def generate(cls) -> "EntityId":
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "EntityId":
        return cls(value=UUID(value))

    def __str__(self) -> str:
        return str(self.value)

@dataclass(frozen=True)
class IssueId(EntityId):
    """Issue identifier."""
    pass

@dataclass(frozen=True)
class ProjectId(EntityId):
    """Project identifier."""
    pass
```

```python
# domain/value_objects/priority.py
from enum import Enum

class Priority(Enum):
    """Issue priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @classmethod
    def from_string(cls, value: str | None) -> "Priority | None":
        if value is None:
            return None
        try:
            return cls(value.lower())
        except ValueError:
            raise InvalidPriorityError(f"Invalid priority: {value}")

    @property
    def sort_order(self) -> int:
        """Numeric order for sorting (lower = higher priority)."""
        return {
            Priority.URGENT: 1,
            Priority.HIGH: 2,
            Priority.MEDIUM: 3,
            Priority.LOW: 4,
            Priority.NONE: 5,
        }[self]
```

---

## Frontend Patterns

### 1. Container/Presenter Pattern

Separate data fetching from presentation.

```tsx
// Container (Server Component)
// app/(workspace)/[workspaceSlug]/projects/[projectId]/issues/page.tsx

import { getIssues } from '@/services/api/issues';
import { IssueBoard } from '@/components/issues/IssueBoard';

export default async function IssuesPage({ params, searchParams }) {
  const { projectId } = await params;
  const issues = await getIssues(projectId);

  return <IssueBoard initialIssues={issues} />;
}
```

```tsx
// Presenter (Client Component)
// components/issues/IssueBoard.tsx
'use client';

interface IssueBoardProps {
  initialIssues: Issue[];
}

export function IssueBoard({ initialIssues }: IssueBoardProps) {
  // UI logic only, no data fetching
  return (
    <div className="grid grid-cols-4 gap-4">
      {STATE_COLUMNS.map((state) => (
        <StateColumn
          key={state.id}
          state={state}
          issues={initialIssues.filter((i) => i.state === state.id)}
        />
      ))}
    </div>
  );
}
```

### 2. Compound Components Pattern

Build flexible component APIs for complex UI.

```tsx
// components/ui/command.tsx
import * as React from 'react';
import { Command as CommandPrimitive } from 'cmdk';

const CommandContext = React.createContext<{ open: boolean }>({ open: false });

function Command({ children, ...props }) {
  const [open, setOpen] = React.useState(false);

  return (
    <CommandContext.Provider value={{ open }}>
      <CommandPrimitive {...props}>{children}</CommandPrimitive>
    </CommandContext.Provider>
  );
}

function CommandInput(props) {
  return <CommandPrimitive.Input {...props} />;
}

function CommandList({ children }) {
  return <CommandPrimitive.List>{children}</CommandPrimitive.List>;
}

function CommandItem({ children, onSelect, ...props }) {
  return (
    <CommandPrimitive.Item onSelect={onSelect} {...props}>
      {children}
    </CommandPrimitive.Item>
  );
}

// Usage
<Command>
  <CommandInput placeholder="Search..." />
  <CommandList>
    <CommandItem onSelect={() => {}}>Item 1</CommandItem>
    <CommandItem onSelect={() => {}}>Item 2</CommandItem>
  </CommandList>
</Command>
```

### 3. Custom Hook Pattern

Encapsulate stateful logic for reuse.

```tsx
// hooks/useAutosave.ts
import { useState, useCallback, useEffect, useRef } from 'react';
import { useDebouncedCallback } from 'use-debounce';

interface UseAutosaveOptions {
  delay?: number;
  onSave: (content: unknown) => Promise<void>;
  onError?: (error: Error) => void;
}

type SaveStatus = 'idle' | 'pending' | 'saving' | 'saved' | 'error';

export function useAutosave({
  delay = 1500,
  onSave,
  onError,
}: UseAutosaveOptions) {
  const [status, setStatus] = useState<SaveStatus>('idle');
  const contentRef = useRef<unknown>(null);

  const debouncedSave = useDebouncedCallback(async () => {
    if (contentRef.current === null) return;

    setStatus('saving');
    try {
      await onSave(contentRef.current);
      setStatus('saved');
      // Reset to idle after showing "Saved"
      setTimeout(() => setStatus('idle'), 2000);
    } catch (error) {
      setStatus('error');
      onError?.(error as Error);
    }
  }, delay);

  const triggerSave = useCallback(
    (content: unknown) => {
      contentRef.current = content;
      setStatus('pending');
      debouncedSave();
    },
    [debouncedSave]
  );

  const cancelSave = useCallback(() => {
    debouncedSave.cancel();
    setStatus('idle');
  }, [debouncedSave]);

  return {
    status,
    triggerSave,
    cancelSave,
    isPending: status === 'pending' || status === 'saving',
  };
}
```

### 4. Optimistic Updates Pattern

Update UI immediately, rollback on failure.

```tsx
// hooks/useIssueState.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useIssueState(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ issueId, state }: { issueId: string; state: string }) =>
      issuesApi.updateState(issueId, state),

    onMutate: async ({ issueId, state }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['issues', projectId] });

      // Snapshot previous value
      const previous = queryClient.getQueryData<Issue[]>(['issues', projectId]);

      // Optimistic update
      queryClient.setQueryData<Issue[]>(['issues', projectId], (old = []) =>
        old.map((issue) =>
          issue.id === issueId ? { ...issue, state } : issue
        )
      );

      return { previous };
    },

    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(['issues', projectId], context.previous);
      }
      toast.error('Failed to update issue state');
    },

    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['issues', projectId] });
    },
  });
}
```

### 5. Render Props / Function as Children

Pass render logic as props for flexibility.

```tsx
// components/ui/data-table.tsx
interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  renderRow?: (item: T, index: number) => React.ReactNode;
  renderEmpty?: () => React.ReactNode;
  isLoading?: boolean;
}

export function DataTable<T>({
  data,
  columns,
  renderRow,
  renderEmpty,
  isLoading,
}: DataTableProps<T>) {
  if (isLoading) {
    return <TableSkeleton columns={columns.length} />;
  }

  if (data.length === 0) {
    return renderEmpty?.() ?? <EmptyState />;
  }

  return (
    <table>
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((item, index) =>
          renderRow ? (
            renderRow(item, index)
          ) : (
            <tr key={index}>
              {columns.map((col) => (
                <td key={col.key}>{col.render(item)}</td>
              ))}
            </tr>
          )
        )}
      </tbody>
    </table>
  );
}
```

---

## API Design Conventions

### RESTful Endpoints

```
# Resource naming (plural nouns)
GET    /api/v1/workspaces              # List workspaces
POST   /api/v1/workspaces              # Create workspace
GET    /api/v1/workspaces/{id}         # Get workspace
PUT    /api/v1/workspaces/{id}         # Update workspace
DELETE /api/v1/workspaces/{id}         # Delete workspace

# Nested resources
GET    /api/v1/projects/{id}/issues    # List project issues
POST   /api/v1/projects/{id}/issues    # Create issue in project

# Actions (verbs when needed)
POST   /api/v1/issues/{id}/assign      # Assign issue
POST   /api/v1/issues/{id}/transition  # Change state
POST   /api/v1/notes/{id}/extract      # Extract issues from note

# AI endpoints (special namespace)
POST   /api/v1/ai/enhance-issue        # Enhance issue with AI
GET    /api/v1/ai/ghost-text           # SSE stream for ghost text
POST   /api/v1/ai/decompose            # Decompose feature to tasks
```

### Response Format

```python
# Success response
{
    "data": { ... },
    "meta": {
        "request_id": "uuid",
        "timestamp": "2026-01-21T10:00:00Z"
    }
}

# List response with pagination
{
    "data": [ ... ],
    "meta": {
        "total": 100,
        "page": 1,
        "per_page": 20,
        "has_next": true,
        "cursor": "abc123"
    }
}

# Error response
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Issue title is required",
        "details": [
            {
                "field": "title",
                "message": "This field is required"
            }
        ]
    },
    "meta": {
        "request_id": "uuid"
    }
}
```

### Pydantic Schema Conventions

```python
# api/v1/schemas/issue.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class IssueBase(BaseModel):
    """Base schema with shared fields."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = Field(None, pattern="^(urgent|high|medium|low|none)$")

class CreateIssueRequest(IssueBase):
    """Request schema for creating an issue."""
    project_id: UUID
    assignee_id: UUID | None = None
    labels: list[UUID] = Field(default_factory=list)

class UpdateIssueRequest(BaseModel):
    """Request schema for updating an issue (partial update)."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    priority: str | None = None
    assignee_id: UUID | None = None

class IssueResponse(IssueBase):
    """Response schema for an issue."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier: str  # e.g., "PS-123"
    state: str
    assignee: UserSummary | None
    created_by: UserSummary
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, issue: Issue) -> "IssueResponse":
        return cls(
            id=issue.id.value,
            identifier=issue.identifier,
            title=issue.title,
            description=issue.description,
            state=issue.state.name,
            priority=issue.priority.value if issue.priority else None,
            # ... other fields
        )
```

---

## Error Handling Conventions

### Domain Exceptions

```python
# domain/exceptions/base.py
class DomainError(Exception):
    """Base exception for domain errors."""
    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)

class NotFoundError(DomainError):
    """Resource not found."""
    pass

class ValidationError(DomainError):
    """Domain validation failed."""
    pass

class PermissionError(DomainError):
    """Insufficient permissions."""
    pass

# domain/exceptions/issue.py
class IssueNotFoundError(NotFoundError):
    def __init__(self, issue_id: str):
        super().__init__(f"Issue not found: {issue_id}", "ISSUE_NOT_FOUND")

class InvalidStateTransitionError(ValidationError):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            f"Cannot transition from {from_state} to {to_state}",
            "INVALID_STATE_TRANSITION"
        )
```

### Global Exception Handler

```python
# api/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from pilot_space.domain.exceptions import DomainError, NotFoundError, PermissionError

async def domain_exception_handler(request: Request, exc: DomainError):
    status_code = 400

    if isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, PermissionError):
        status_code = 403

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
            "meta": {
                "request_id": request.state.request_id,
            }
        },
    )

# Register in main.py
app.add_exception_handler(DomainError, domain_exception_handler)
```

---

## Testing Conventions

### Unit Test Structure

```python
# tests/unit/domain/test_issue.py
import pytest
from pilot_space.domain.entities.issue import Issue
from pilot_space.domain.value_objects import ProjectId, UserId
from pilot_space.domain.exceptions import InvalidIssueTitleError

class TestIssueCreation:
    """Tests for Issue.create() factory method."""

    def test_creates_issue_with_valid_data(self):
        # Arrange
        project_id = ProjectId.generate()
        user_id = UserId.generate()

        # Act
        issue = Issue.create(
            project_id=project_id,
            sequence_id=1,
            title="Fix login bug",
            description="Users cannot login",
            created_by=user_id,
        )

        # Assert
        assert issue.title == "Fix login bug"
        assert issue.state.name == "Backlog"
        assert len(issue.pending_events) == 1

    def test_raises_for_empty_title(self):
        # Arrange & Act & Assert
        with pytest.raises(InvalidIssueTitleError):
            Issue.create(
                project_id=ProjectId.generate(),
                sequence_id=1,
                title="",
                description=None,
                created_by=UserId.generate(),
            )

    def test_raises_for_title_exceeding_max_length(self):
        with pytest.raises(InvalidIssueTitleError):
            Issue.create(
                project_id=ProjectId.generate(),
                sequence_id=1,
                title="x" * 256,
                description=None,
                created_by=UserId.generate(),
            )

class TestIssueStateTransition:
    """Tests for Issue state transitions."""

    @pytest.fixture
    def issue(self):
        return Issue.create(
            project_id=ProjectId.generate(),
            sequence_id=1,
            title="Test issue",
            description=None,
            created_by=UserId.generate(),
        )

    def test_can_transition_to_in_progress(self, issue):
        issue.change_state(IssueState.in_progress(), UserId.generate())

        assert issue.state.name == "In Progress"
        assert len(issue.pending_events) == 2  # Created + StateChanged
```

### Integration Test Structure

```python
# tests/integration/api/test_issues_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
class TestIssuesAPI:
    """Integration tests for /issues endpoints."""

    async def test_create_issue(self, client: AsyncClient, auth_headers: dict):
        # Arrange
        payload = {
            "project_id": "project-uuid",
            "title": "New feature",
            "description": "Implement new feature",
        }

        # Act
        response = await client.post(
            "/api/v1/issues",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "New feature"
        assert data["state"] == "Backlog"

    async def test_create_issue_without_auth_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/issues", json={})

        assert response.status_code == 401
```

---

## Code Quality Rules

### File Size Limits

- **Maximum 700 lines per file**
- Split large files into focused modules

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Python class | PascalCase | `IssueRepository` |
| Python function | snake_case | `create_issue` |
| Python constant | UPPER_SNAKE | `MAX_TITLE_LENGTH` |
| Python private | _prefix | `_validate_title` |
| TypeScript component | PascalCase | `IssueCard` |
| TypeScript hook | camelCase + use | `useIssues` |
| TypeScript type | PascalCase | `Issue` |

### Import Order

```python
# Python imports
# 1. Standard library
import os
from datetime import datetime
from uuid import UUID

# 2. Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

# 3. Local application
from pilot_space.domain.entities import Issue
from pilot_space.domain.value_objects import IssueId
from pilot_space.application.services import CreateIssueService
```

```typescript
// TypeScript imports
// 1. React/Next.js
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. Third-party
import { observer } from 'mobx-react-lite';
import { useQuery } from '@tanstack/react-query';

// 3. Local
import { Button } from '@/components/ui/button';
import { useIssues } from '@/hooks/useIssues';
import type { Issue } from '@/types/issue';
```

---

## Related Documents

- [Backend Architecture](./backend-architecture.md) - Layer implementation details
- [Frontend Architecture](./frontend-architecture.md) - Component patterns
- [Project Structure](./project-structure.md) - Directory organization
