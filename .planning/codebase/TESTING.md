# Testing Patterns

**Analysis Date:** 2026-03-07

## Test Framework

**Backend Runner:**
- pytest 8.3+, pytest-asyncio 0.24+
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async test functions run automatically
- `--strict-markers`, `--strict-config` enforced

**Backend Assertion:**
- pytest built-in `assert`
- `unittest.mock` for `MagicMock`, `AsyncMock`, `patch`

**Frontend Runner:**
- Vitest with `@vitejs/plugin-react`
- Config: `frontend/vitest.config.ts`
- Environment: `jsdom`
- Globals: enabled (no per-file `import { describe, it, expect }` required — but explicitly imported for clarity)

**Frontend Assertion:**
- Vitest `expect` + `@testing-library/jest-dom/vitest` matchers (e.g., `toBeInTheDocument`, `toHaveAttribute`)
- `@testing-library/react` for `render`, `screen`, `renderHook`, `waitFor`, `act`

**E2E:**
- Playwright (`frontend/playwright.config.ts`)
- Targets: Chromium, Firefox, WebKit + Mobile Chrome/Safari
- Auth state pre-loaded via `storageState` (shared `e2e/.auth/user.json`)

**Run Commands:**
```bash
# Backend
cd backend && uv run pytest                          # All tests
cd backend && uv run pytest tests/unit/ -q           # Unit tests only
cd backend && uv run pytest -m "not slow"            # Skip slow tests
cd backend && uv run pytest --cov --cov-report=html  # With coverage

# Frontend
cd frontend && pnpm test                             # All Vitest tests
cd frontend && pnpm test -- --watch                  # Watch mode
cd frontend && pnpm test -- --coverage               # With coverage

# E2E
cd frontend && pnpm test:e2e                         # All Playwright tests
cd frontend && pnpm test:e2e --project=chromium      # Chromium only
```

## Test File Organization

**Backend:**
- Separate `tests/` directory at `backend/tests/`
- Mirrors source structure:
  - `tests/unit/repositories/` → tests for `src/.../repositories/`
  - `tests/unit/routers/` → tests for `src/.../api/v1/routers/`
  - `tests/unit/services/` → tests for `src/.../application/services/`
  - `tests/unit/ai/` → tests for `src/.../ai/`
  - `tests/unit/integrations/` → tests for `src/.../integrations/`
  - `tests/routers/` → older integration-style router tests (legacy location)
- Root `tests/conftest.py` provides all shared fixtures
- Sub-conftest files in `tests/unit/services/conftest.py` and `tests/security/conftest.py` for specialized DB setup

**Frontend:**
- Co-located `__tests__/` subdirectory within each module
- Pattern: `src/features/{feature}/components/__tests__/{ComponentName}.test.tsx`
- Hook tests: `src/features/{feature}/hooks/__tests__/{hookName}.test.ts`
- Store tests: `src/stores/features/{feature}/__tests__/{StoreName}.test.ts`
- E2E tests: `frontend/e2e/{feature}.spec.ts`

**Naming:**
- Backend: `test_{functionality}.py` (e.g., `test_issue_repository.py`, `test_notifications.py`)
- Frontend components: `{ComponentName}.test.tsx` (e.g., `IssueDetailSheet.test.tsx`)
- Frontend hooks: `{hookName}.test.ts` (e.g., `useWorkspaceDigest.test.ts`)
- E2E: `{feature}.spec.ts` (e.g., `issues.spec.ts`, `pr-review.spec.ts`)

**Structure:**
```
backend/tests/
├── conftest.py              # All shared fixtures
├── factories.py             # factory_boy factories
├── fixtures/
│   └── anthropic_mock.py   # AI mock helpers
├── unit/
│   ├── ai/
│   ├── integrations/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   │   ├── conftest.py     # SQLite DDL conftest
│   │   └── memory/
│   └── spaces/
├── security/
└── e2e/

frontend/src/features/{feature}/
├── components/
│   └── __tests__/
├── hooks/
│   └── __tests__/
└── pages/
    └── __tests__/
```

## Test Structure

**Backend Suite Organization:**
```python
"""Module docstring explaining what is tested and what is NOT."""

from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock
import pytest

pytestmark = pytest.mark.asyncio  # module-level async mark

# ---------------------------------------------------------------------------
# Helpers (builder functions, factory helpers)
# ---------------------------------------------------------------------------

def _make_orm_notification(...) -> Notification:
    """Build an in-memory ORM object for tests."""
    ...

# ---------------------------------------------------------------------------
# Tests: {Topic}
# ---------------------------------------------------------------------------

class Test{Topic}:
    """Tests for {SUT} behavior."""

    def test_{scenario}(self) -> None:
        """Docstring explains the assertion."""
        ...

    async def test_{async_scenario}(self, db_session: AsyncSession) -> None:
        ...
```

**Frontend Suite Organization:**
```typescript
// File-level JSDoc comment explaining coverage scope

vi.mock('@/services/api', () => ({ ... }));  // all mocks BEFORE imports

import { ... } from '../ModuleUnderTest';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockData: DataType = { ... };  // typed fixture objects

function createWrapper() {             // QueryClient wrapper for hooks
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// ---------------------------------------------------------------------------
// Tests: {Topic}
// ---------------------------------------------------------------------------

describe('{SUT}', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('{scenario}', async () => { ... });
});
```

**Patterns:**
- Setup: `beforeEach(() => { vi.clearAllMocks(); })` in frontend; `@pytest.fixture` in backend
- No `afterAll` teardown needed — db_session rolls back automatically
- Each test class focuses on a single method or behavior group
- Test method names are descriptive sentences (backend: `test_excludes_soft_deleted_by_default`)

## Mocking

**Backend Framework:** `unittest.mock` (`MagicMock`, `AsyncMock`, `patch`)

**Patterns:**
```python
# Patch via context manager (preferred for narrow scope)
with patch("pilot_space.dependencies.get_auth") as mock_get_auth:
    mock_auth = MagicMock()
    mock_auth.validate_token.return_value = mock_token_payload
    mock_get_auth.return_value = mock_auth
    yield mock_auth

# AsyncMock for coroutines
mock_service = MagicMock()
mock_service.create = AsyncMock(return_value=created_notification)

# Module-level patching (for worker tests)
import pilot_space.ai.workers.notification_worker as worker_module
original = worker_module.NotificationService
try:
    worker_module.NotificationService = MagicMock(return_value=mock_service)
    result = await worker._persist_notification(payload, mock_session)
finally:
    worker_module.NotificationService = original  # always restore
```

**Frontend Framework:** `vi.mock()` / `vi.fn()` / `vi.mocked()`

**Patterns:**
```typescript
// Module-level vi.mock (hoisted before all imports automatically)
vi.mock('@/services/api', () => ({
  notesApi: {
    list: vi.fn(),
    get: vi.fn(),
  },
}));

// Import AFTER mock declaration
import { notesApi } from '@/services/api';

// In test: use vi.mocked() to get typed mock
vi.mocked(notesApi.list).mockResolvedValue({ items: [...], total: 2 });

// For component dependencies (shadcn/ui, next/link etc.)
vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children, open }) => open ? <div data-testid="sheet">{children}</div> : null,
}));
```

**What to Mock:**
- All external HTTP/API calls (use `vi.mock` for API modules)
- Database session in unit tests (use `db_session` fixture instead of real DB)
- Redis client (`mock_redis` fixture from `conftest.py`)
- Supabase auth (`mock_auth` fixture patches `get_auth`)
- AI providers (`mock_ai_client` fixture; `mock_anthropic_api` for Anthropic-specific)
- Next.js router (`useRouter`, `usePathname` — pre-mocked in `vitest.setup.tsx`)
- Browser APIs (`matchMedia`, `ResizeObserver`, `IntersectionObserver` — pre-mocked in setup)

**What NOT to Mock:**
- SQLAlchemy models themselves (use real ORM objects with in-memory SQLite)
- Pydantic schemas (use `model_validate()` on real ORM instances)
- Pure business logic (domain entities, utility functions)
- MobX stores in store tests (test the real store class)

## Fixtures and Factories

**Backend Factories** (`backend/tests/factories.py`):
```python
class UserFactory(BaseFactory):
    class Meta:
        model = User
    email: str = Sequence(lambda n: f"user{n}@example.com")
    full_name: str = Sequence(lambda n: f"Test User {n}")

class WorkspaceFactory(BaseFactory):
    class Meta:
        model = Workspace
    # ...
```

Factory classes: `UserFactory`, `WorkspaceFactory`, `ProjectFactory`, `IssueFactory`, `NoteFactory`, `StateFactory`, `WorkspaceMemberFactory`

**Inline fixtures for db tests** (preferred for repository tests):
```python
@pytest.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a workspace for tests."""
    ws = Workspace(id=uuid4(), name="Test Workspace", slug="test-ws", owner_id=uuid4())
    db_session.add(ws)
    await db_session.flush()
    return ws
```

**Frontend fixtures** — typed inline objects:
```typescript
function makeNote(overrides: Partial<Note> = {}): Note {
  return {
    id: 'note-1',
    title: 'Test Note',
    content: { type: 'doc', content: [] },
    workspaceId: 'ws-default',
    ...overrides,
  };
}

const mockDigestResponse: DigestResponse = { data: { suggestions: [...] } };
```

**Fixture location:**
- Backend shared fixtures: `backend/tests/conftest.py`
- Backend specialized fixtures: `backend/tests/unit/services/conftest.py`, `backend/tests/security/conftest.py`
- Frontend: inline within each test file (no shared fixture file)
- AI mocks: `backend/tests/fixtures/anthropic_mock.py`

## Coverage

**Requirements:**
- Backend: `fail_under = 80` with `branch = true` (`backend/pyproject.toml`)
- Frontend: 80% threshold on branches, functions, lines, statements (`frontend/vitest.config.ts`)

**Exclusions (Backend):**
- `*/tests/*`, `*/__init__.py` from source measurement
- Lines: `pragma: no cover`, `def __repr__`, `raise NotImplementedError`, `if TYPE_CHECKING:`, `if __name__ == .__main__.:`

**Exclusions (Frontend):**
- `src/**/*.d.ts`, test files themselves
- `src/app/**/layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`

**View Coverage:**
```bash
# Backend
cd backend && uv run pytest --cov --cov-report=html
open backend/htmlcov/index.html

# Frontend
cd frontend && pnpm test -- --coverage
open frontend/coverage/index.html
```

## Test Types

**Backend Unit Tests:**
- Scope: single service, repository method, schema, or worker method in isolation
- DB: SQLite in-memory (`sqlite+aiosqlite:///:memory:`) via `db_session` fixture
- External deps: mocked via `unittest.mock`
- Location: `backend/tests/unit/`
- `pytestmark = pytest.mark.asyncio` at module level for async tests

**Backend Router/Integration Tests:**
- Scope: full HTTP request → response via `AsyncClient` + ASGI transport
- DB: SQLite in-memory + Container override for Redis
- Auth: mocked via `mock_auth` fixture
- Location: `backend/tests/routers/` (older), `backend/tests/unit/routers/` (newer)
- Use `client_with_workspace` or `authenticated_client` fixture

**Frontend Unit Tests (Vitest):**
- Scope: individual component rendering, hook behavior, store operations
- Mocking: `vi.mock()` for API and router deps; RTL's `render`/`renderHook` for React
- Store tests: instantiate store directly (`new NoteStore()`) without DI
- Hook tests: `renderHook()` wrapped in `QueryClientProvider`

**E2E Tests (Playwright):**
- Scope: full user workflow in real browser against running dev servers
- Auth: pre-loaded storage state (`e2e/.auth/user.json`) from `global-setup.ts`
- Assertions: `expect(locator).toBeVisible()`, `toContainText()`, `toHaveAttribute()`
- Selectors: `data-testid` attributes (`[data-testid="issue-card"]`)
- Unauth tests: suffix `.unauth.spec.ts` (matched by `chromium-unauth` project)
- Location: `frontend/e2e/`

## Common Patterns

**Backend Async Testing:**
```python
pytestmark = pytest.mark.asyncio

class TestGetByIdForResponse:
    async def test_returns_issue_with_required_relations(
        self, db_session: AsyncSession, issue: Issue
    ) -> None:
        repo = IssueRepository(db_session)
        result = await repo.get_by_id_for_response(issue.id)
        assert result is not None
        assert result.project is not None  # verify joinedload worked
```

**Backend Error Testing:**
```python
with pytest.raises(ValueError, match="unknown_type"):
    await worker._persist_notification(payload, mock_session)
```

**Frontend Async Hook Testing:**
```typescript
it('fetches digest when workspaceId is provided', async () => {
  vi.mocked(homepageApi.getDigest).mockResolvedValue(mockDigestResponse);

  const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
    wrapper: createWrapper(),
  });

  await waitFor(() => expect(result.current.isLoading).toBe(false));
  expect(result.current.suggestions).toHaveLength(3);
});
```

**Frontend Mutation Testing:**
```typescript
act(() => {
  result.current.dismiss(mockSuggestion1);
});

await waitFor(() => {
  expect(homepageApi.dismissSuggestion).toHaveBeenCalledWith('ws-1', {
    suggestionId: 'sug-1',
    entityId: 'entity-1',
    entityType: 'issue',
    category: 'stale_issues',
  });
});
```

**Frontend Component Testing:**
```typescript
it('does not render when issueId is null', () => {
  const { container } = render(
    <IssueDetailSheet issueId={null} workspaceId="ws-1" workspaceSlug="test-ws" onClose={vi.fn()} />
  );
  expect(container.querySelector('[data-testid="sheet"]')).not.toBeInTheDocument();
});
```

**E2E Test Pattern:**
```typescript
test.describe('Issue Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should create issue', async ({ page }) => {
    await page.click('[data-testid="create-issue-button"]');
    await page.fill('[data-testid="issue-title-input"]', 'Fix login button');
    await page.click('[data-testid="submit-issue-button"]');
    await expect(page.locator('[data-testid="issue-card"]')).toContainText('Fix login button');
  });
});
```

## Test Markers (Backend)

```
slow         # Long-running tests (deselect with -m "not slow")
integration  # Tests requiring external services
infrastructure  # DB, Redis, Meilisearch, auth, sandbox tests
api          # API endpoint tests
e2e          # End-to-end tests
performance  # Benchmark/latency tests (excluded from PR gate)
contract     # Schema parity between backend and frontend
```

## Critical Gotchas

1. **SQLite vs PostgreSQL**: Default `db_session` uses SQLite in-memory. RLS policies, pgvector, and pgmq do NOT work in SQLite. Set `TEST_DATABASE_URL` for integration/security tests.

2. **`db_session` vs `db_session_committed`**: `db_session` rolls back on teardown — data never committed. Use `db_session_committed` for unique constraint tests or cross-session visibility.

3. **`get_settings()` cache**: Uses `@lru_cache`. Call `get_settings.cache_clear()` in fixtures that modify env vars.

4. **Frontend `vi.mock` hoisting**: `vi.mock()` calls are hoisted above imports automatically. Always declare mocks before the import of the module-under-test.

5. **QueryClient in hook tests**: Always wrap `renderHook()` calls in a fresh `QueryClient` with `retry: false` to prevent test interference.

6. **MobX `observer` on TipTap**: Never wrap `IssueEditorContent` in `observer()`. Use the context bridge pattern instead. See `frontend/src/features/issues/contexts/issue-note-context.ts`.

---

*Testing analysis: 2026-03-07*
