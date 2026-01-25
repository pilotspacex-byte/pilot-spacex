# Testing Strategy

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This document defines the testing strategy for Pilot Space MVP, including test types, coverage requirements, and testing patterns for both backend and frontend.

---

## Test Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱E2E ╲           5-10% of tests
                 ╱──────╲          Critical user flows
                ╱        ╲
               ╱Integration╲       15-20% of tests
              ╱────────────╲       API, database, AI
             ╱              ╲
            ╱     Unit       ╲     70-80% of tests
           ╱──────────────────╲    Functions, hooks, components
```

---

## Test Categories

### Unit Tests (70-80%)

**Purpose**: Test individual functions, classes, and components in isolation.

**Characteristics**:
- Fast execution (<100ms per test)
- No external dependencies
- Mock all collaborators
- Deterministic results

**Backend Examples**:
- Domain entity validation
- Service class business logic
- Utility functions
- Value object behavior

**Frontend Examples**:
- React component rendering
- Custom hooks
- State store actions
- Utility functions

### Integration Tests (15-20%)

**Purpose**: Test interactions between components and external systems.

**Characteristics**:
- Medium execution time
- Real database (test container)
- Real HTTP calls (mocked external services)
- May require setup/teardown

**Backend Examples**:
- Repository + database
- API endpoint + service + repository
- AI agent + mocked LLM provider

**Frontend Examples**:
- Component + API client (MSW)
- Form submission flow
- TipTap editor behavior

### End-to-End Tests (5-10%)

**Purpose**: Test critical user flows through the entire system.

**Characteristics**:
- Slow execution
- Full application stack
- Browser automation (Playwright)
- Focus on happy paths

**Critical Flows**:
1. User authentication (signup, login, logout)
2. Note creation with ghost text
3. Issue creation from note extraction
4. PR review trigger and display
5. Sprint board drag-and-drop

---

## Backend Testing

### Tools

| Tool | Purpose |
|------|---------|
| pytest | Test framework |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage reporting |
| pytest-mock | Mocking utilities |
| factory-boy | Test data factories |
| testcontainers | Database containers |
| httpx | Async HTTP client for API tests |

### Directory Structure

```
backend/tests/
├── conftest.py              # Shared fixtures
├── factories/               # Test data factories
│   ├── issue_factory.py
│   ├── note_factory.py
│   └── user_factory.py
├── unit/
│   ├── domain/
│   │   ├── test_issue.py
│   │   └── test_note.py
│   ├── application/
│   │   ├── test_create_issue_service.py
│   │   └── test_ghost_text_service.py
│   └── ai/
│       ├── test_pr_review_agent.py
│       └── test_ghost_text_agent.py
├── integration/
│   ├── api/
│   │   ├── test_issues_api.py
│   │   └── test_notes_api.py
│   └── repositories/
│       └── test_issue_repository.py
└── e2e/
    └── test_issue_lifecycle.py
```

### Fixtures (conftest.py)

```python
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pilot_space.infrastructure.database import Base

@pytest.fixture(scope="session")
def postgres():
    """Start PostgreSQL container for tests."""
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
async def db_session(postgres):
    """Create async database session."""
    engine = create_async_engine(postgres.get_connection_url())
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
def mock_ai_provider():
    """Mock AI provider for unit tests."""
    with patch("pilot_space.ai.providers.ClaudeProvider") as mock:
        mock.return_value.complete.return_value = AsyncIterator(["response"])
        yield mock
```

### Unit Test Example

```python
# tests/unit/application/test_create_issue_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from pilot_space.application.services import CreateIssueService
from pilot_space.application.payloads import CreateIssuePayload
from tests.factories import IssueFactory

class TestCreateIssueService:
    @pytest.fixture
    def service(self):
        repository = AsyncMock()
        event_bus = MagicMock()
        return CreateIssueService(repository, event_bus)

    async def test_create_issue_success(self, service):
        payload = CreateIssuePayload(
            title="Test Issue",
            description="Test description",
            project_id="uuid"
        )

        result = await service.execute(payload)

        assert result.title == "Test Issue"
        service.repository.save.assert_called_once()
        service.event_bus.publish.assert_called_once()

    async def test_create_issue_validates_title(self, service):
        payload = CreateIssuePayload(
            title="",  # Invalid: empty title
            project_id="uuid"
        )

        with pytest.raises(ValidationError):
            await service.execute(payload)
```

### Integration Test Example

```python
# tests/integration/api/test_issues_api.py
import pytest
from httpx import AsyncClient
from pilot_space.main import app
from tests.factories import UserFactory, ProjectFactory

class TestIssuesAPI:
    @pytest.fixture
    async def client(self, db_session):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def auth_headers(self, db_session):
        user = await UserFactory.create(session=db_session)
        token = create_test_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    async def test_create_issue(self, client, auth_headers, db_session):
        project = await ProjectFactory.create(session=db_session)

        response = await client.post(
            f"/api/v1/projects/{project.id}/issues",
            headers=auth_headers,
            json={
                "title": "Test Issue",
                "description": "Description"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["title"] == "Test Issue"

    async def test_create_issue_unauthorized(self, client):
        response = await client.post(
            "/api/v1/projects/uuid/issues",
            json={"title": "Test"}
        )

        assert response.status_code == 401
```

### AI Agent Test Example

```python
# tests/unit/ai/test_ghost_text_agent.py
import pytest
from unittest.mock import AsyncMock
from pilot_space.ai.agents import GhostTextAgent
from pilot_space.ai.providers import MockProvider

class TestGhostTextAgent:
    @pytest.fixture
    def agent(self):
        provider = MockProvider(
            responses=["Consider adding", " authentication"]
        )
        return GhostTextAgent(provider=provider)

    async def test_generates_suggestion(self, agent):
        input_data = GhostTextInput(
            current_block="We need to implement",
            previous_blocks=["# Authentication Feature"],
            document_summary="Feature specification"
        )

        result = await agent.execute(input_data)

        assert result.suggestion is not None
        assert len(result.suggestion) <= 100  # Max ~50 tokens

    async def test_handles_word_boundaries(self, agent):
        """Verify word boundary handling per DD-067."""
        chunks = []
        async for chunk in agent.stream(input_data):
            chunks.append(chunk)

        # Each chunk should be a complete word
        for chunk in chunks:
            assert not chunk.endswith("-")  # No partial words
```

---

## Frontend Testing

### Tools

| Tool | Purpose |
|------|---------|
| Vitest | Test framework |
| React Testing Library | Component testing |
| MSW | API mocking |
| Playwright | E2E testing |
| axe-core | Accessibility testing |

### Directory Structure

```
frontend/tests/
├── setup.ts                 # Test setup and mocks
├── mocks/
│   ├── handlers.ts         # MSW request handlers
│   └── server.ts           # MSW server setup
├── unit/
│   ├── hooks/
│   │   └── useIssues.test.ts
│   └── utils/
│       └── formatDate.test.ts
├── integration/
│   ├── features/
│   │   ├── IssueBoard.test.tsx
│   │   └── NoteCanvas.test.tsx
│   └── flows/
│       └── CreateIssueFlow.test.tsx
└── e2e/
    ├── auth.spec.ts
    ├── note-creation.spec.ts
    └── issue-board.spec.ts
```

### MSW Setup

```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/v1/projects/:id/issues', () => {
    return HttpResponse.json({
      data: [
        { id: '1', title: 'Issue 1', status: 'backlog' },
        { id: '2', title: 'Issue 2', status: 'in_progress' },
      ],
      meta: { total: 2 }
    });
  }),

  http.post('/api/v1/ai/ghost-text', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"text": "Consider"}\n\n'));
        controller.enqueue(encoder.encode('data: {"text": " adding"}\n\n'));
        controller.close();
      },
    });

    return new HttpResponse(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });
  }),
];
```

### Component Test Example

```typescript
// tests/integration/features/IssueCard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { IssueCard } from '@/features/issues/IssueCard';
import { createWrapper } from '@/tests/utils';

expect.extend(toHaveNoViolations);

describe('IssueCard', () => {
  const mockIssue = {
    id: '1',
    title: 'Test Issue',
    status: { type: 'backlog' as const },
    priority: 'high',
    labels: [{ id: '1', name: 'bug', color: '#ff0000' }],
  };

  it('renders issue details', () => {
    render(<IssueCard issue={mockIssue} />, { wrapper: createWrapper() });

    expect(screen.getByText('Test Issue')).toBeInTheDocument();
    expect(screen.getByText('Backlog')).toBeInTheDocument();
    expect(screen.getByText('bug')).toBeInTheDocument();
  });

  it('handles click to open detail', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <IssueCard issue={mockIssue} onSelect={onSelect} />,
      { wrapper: createWrapper() }
    );

    await user.click(screen.getByRole('article'));

    expect(onSelect).toHaveBeenCalledWith('1');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <IssueCard issue={mockIssue} />,
      { wrapper: createWrapper() }
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <IssueCard issue={mockIssue} onSelect={onSelect} />,
      { wrapper: createWrapper() }
    );

    const card = screen.getByRole('article');
    card.focus();
    await user.keyboard('{Enter}');

    expect(onSelect).toHaveBeenCalled();
  });
});
```

### Hook Test Example

```typescript
// tests/unit/hooks/useGhostText.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useGhostText } from '@/features/notes/hooks/useGhostText';
import { createWrapper } from '@/tests/utils';

describe('useGhostText', () => {
  it('fetches suggestion after delay', async () => {
    vi.useFakeTimers();

    const { result } = renderHook(
      () => useGhostText({ currentBlock: 'We need to' }),
      { wrapper: createWrapper() }
    );

    expect(result.current.suggestion).toBeNull();

    vi.advanceTimersByTime(500); // Trigger delay

    await waitFor(() => {
      expect(result.current.suggestion).toBe('Consider adding');
    });

    vi.useRealTimers();
  });

  it('cancels on new input', async () => {
    const { result, rerender } = renderHook(
      ({ block }) => useGhostText({ currentBlock: block }),
      {
        wrapper: createWrapper(),
        initialProps: { block: 'Initial' },
      }
    );

    rerender({ block: 'New input' });

    // Previous request should be aborted
    expect(result.current.isLoading).toBe(true);
  });
});
```

### E2E Test Example

```typescript
// tests/e2e/note-creation.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Note Creation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await loginAsTestUser(page);
  });

  test('creates note with ghost text', async ({ page }) => {
    // Navigate to notes
    await page.click('[data-testid="nav-notes"]');
    await page.click('[data-testid="new-note-button"]');

    // Type in editor
    const editor = page.locator('[data-testid="note-editor"]');
    await editor.click();
    await page.keyboard.type('We need to implement');

    // Wait for ghost text
    await page.waitForTimeout(600); // 500ms delay + buffer
    const ghostText = page.locator('[data-testid="ghost-text"]');
    await expect(ghostText).toBeVisible();

    // Accept ghost text
    await page.keyboard.press('Tab');

    // Verify text inserted
    await expect(editor).toContainText('We need to implement');
  });

  test('extracts issue from note', async ({ page }) => {
    const editor = page.locator('[data-testid="note-editor"]');
    await editor.click();
    await page.keyboard.type('We need to fix the login bug');

    // Wait for annotation
    const annotation = page.locator('[data-testid="margin-annotation"]');
    await expect(annotation).toBeVisible();

    // Click to extract issue
    await annotation.click();
    await page.click('[data-testid="extract-issue-button"]');

    // Verify issue created
    await expect(page.locator('[data-testid="issue-created-toast"]')).toBeVisible();
  });
});
```

---

## Coverage Requirements

| Category | Minimum Coverage |
|----------|------------------|
| Overall | 80% |
| Backend Domain | 90% |
| Backend Services | 85% |
| Frontend Components | 80% |
| AI Agents | 75% (with mocked providers) |

### CI Coverage Gates

```yaml
# .github/workflows/test.yml
- name: Backend Tests
  run: |
    pytest --cov=pilot_space --cov-fail-under=80 --cov-report=xml

- name: Frontend Tests
  run: |
    pnpm test --coverage --coverageThreshold='{"global":{"lines":80}}'
```

---

## Testing AI Features

### Mocking LLM Providers

```python
# tests/mocks/ai_providers.py
class MockLLMProvider:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    async def complete(self, prompt: str, **kwargs):
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response

    async def stream(self, prompt: str, **kwargs):
        for word in self.responses[self.call_count].split():
            yield word + " "
        self.call_count += 1
```

### Testing Streaming (SSE)

```typescript
// Frontend SSE testing with MSW
import { http, HttpResponse } from 'msw';

http.get('/api/v1/ai/ghost-text', () => {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      for (const word of ['Consider', 'adding', 'tests']) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ text: word })}\n\n`)
        );
        await delay(50);
      }

      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    },
  });

  return new HttpResponse(stream, {
    headers: { 'Content-Type': 'text/event-stream' },
  });
});
```

---

## References

- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [local-development.md](./local-development.md) - Development setup
- [ci-cd-pipeline.md](./ci-cd-pipeline.md) - CI configuration
