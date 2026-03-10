# Coding Conventions

**Analysis Date:** 2026-03-07

## Naming Patterns

**Backend (Python):**
- Files: `snake_case` (e.g., `create_note_service.py`, `issue_repository.py`)
- Classes: `PascalCase` (e.g., `IssueRepository`, `CreateNoteService`)
- Functions/methods: `snake_case` (e.g., `get_issue_timeline`, `bulk_update_labels`)
- Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE` (e.g., `AUTO_SAVE_DEBOUNCE_MS`, `_SUMMARY_LENGTH`)
- Private attrs: underscore-prefixed (e.g., `_auto_save_timer`, `_disposers`)
- Dataclass payloads: `{Action}{Entity}Payload` (e.g., `CreateNotePayload`, `UpdateWorkspacePayload`)
- Dataclass results: `{Action}{Entity}Result` (e.g., `CreateNoteResult`)

**Frontend (TypeScript):**
- Component files: `PascalCase.tsx` (e.g., `IssueDetailSheet.tsx`, `HomepageHub.tsx`)
- Hook files: `camelCase.ts` (e.g., `useWorkspaceDigest.ts`, `useIssueLinks.ts`)
- Service/API files: `kebab-case.ts` (e.g., `homepage-api.ts`, `knowledge-graph.ts`)
- Store files: `PascalCase.ts` (e.g., `NoteStore.ts`, `CycleStore.ts`)
- Type files: `kebab-case.ts` (e.g., `cycle-store-types.ts`)
- Test directories: `__tests__/` subdirectory within the feature module
- Hooks: prefix `use` (e.g., `useWorkspaceDigest`, `useActiveCycleMetrics`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `AUTO_SAVE_DEBOUNCE_MS`, `STALE_THRESHOLD_DAYS`)

## Code Style

**Backend Formatting:**
- Tool: Ruff (configured in `backend/ruff.toml`)
- Line length: 100 characters
- Quotes: Double quotes (`"`) for both inline and docstrings
- Python version target: 3.12
- Enabled rule sets: E, W, F, I (isort), UP, B (bugbear), SIM, ASYNC, DTZ, PT (pytest-style), TCH, ARG, PL, TRY, PERF, RUF

**Backend Linting:**
- All imports sorted via `isort` rules with `known-first-party = ["pilot_space"]`
- `combine-as-imports = true`, `force-wrap-aliases = true`
- `from __future__ import annotations` required at top of every module
- `if TYPE_CHECKING:` block used to defer type-only imports

**Frontend Formatting:**
- Tool: Prettier (configured in `frontend/.prettierrc`)
- `singleQuote: true`
- `semi: true`
- `tabWidth: 2`
- `trailingComma: "es5"`
- `printWidth: 100`
- `arrowParens: "always"`
- `endOfLine: "lf"`

**Frontend Linting:**
- Tool: ESLint with `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript`
- Unused vars allowed when prefixed with `_` (args, vars, caught errors all)

## Import Organization

**Backend (Python):**
1. `from __future__ import annotations` (always first line of module)
2. Standard library imports
3. Third-party imports (FastAPI, SQLAlchemy, Pydantic, etc.)
4. First-party imports (`from pilot_space.xxx import ...`)
5. `if TYPE_CHECKING:` block for type-only imports at end of import section

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from pilot_space.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from pilot_space.infrastructure.database.repositories.issue_repository import IssueRepository
```

**Frontend (TypeScript):**
1. React import (if needed)
2. Third-party libraries (`mobx`, `@tanstack/react-query`, `vitest`, etc.)
3. Path aliased imports (`@/lib/...`, `@/services/...`, `@/types`, `@/features/...`)
4. Relative imports

```typescript
import { makeAutoObservable, runInAction, reaction } from 'mobx';
import type { Note, NoteAnnotation } from '@/types';
import { notesApi } from '@/services/api';
import { VersionStore } from '@/features/notes/stores/VersionStore';
```

**Path Aliases:**
- `@/` maps to `frontend/src/` (configured in `vitest.config.ts` and Next.js)

## Error Handling

**Backend:**
- Services raise `ValueError` for business logic errors (e.g., slug conflict)
- Routers catch `ValueError` and convert to `HTTPException` with appropriate status codes
- All error responses use RFC 7807 `application/problem+json` (not `application/json`)
- `HTTPException` with `status.HTTP_404_NOT_FOUND`, `status.HTTP_403_FORBIDDEN` etc.
- `structlog` for structured logging; never use bare `print()`

```python
try:
    result = await service.create_workspace(payload)
except ValueError as e:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(e),
    )
```

**Frontend:**
- TanStack Query `isError` state for query failures
- MobX `error: string | null` field on stores for operation errors
- `runInAction()` wraps all async state mutations in MobX stores
- API errors handled in `ApiError.fromAxiosError` (supports both `application/json` and `application/problem+json`)

```typescript
try {
  const result = await notesApi.update(id, data);
  runInAction(() => {
    this.notes.set(id, result);
    this.error = null;
  });
} catch (err) {
  runInAction(() => {
    this.error = err instanceof Error ? err.message : 'Unknown error';
  });
}
```

## Logging

**Backend:**
- Framework: `structlog` (configured via `pilot_space.infrastructure.logging`)
- Pattern: module-level logger `logger = get_logger(__name__)`
- Location: `backend/src/pilot_space/infrastructure/logging.py`
- Every router and service module creates `logger = get_logger(__name__)` at module level

**Frontend:**
- No dedicated logging framework — console only in dev/debug paths
- Browser errors surfaced through UI state, not console.error in production paths

## Comments

**Backend:**
- Module-level docstrings required on every file (triple-quoted)
- Class docstrings required
- Function docstrings required with Google-style Args/Returns sections
- `# ===...===` section dividers used in large files (e.g., `conftest.py`, `routers`)
- `# -----------...` used for grouping within test files
- Inline `# noqa: E712` for intentional SQLAlchemy `== False` comparisons

**Frontend:**
- File-level JSDoc comment block for feature modules
- `// ─────...` decorators used to separate logical sections within test files
- `// Mock Next.js router` style comments to explain global test setup
- Barrel `index.ts` files have JSDoc `/** Feature name - ticket ref */` at top

## Module Design

**Backend Exports:**
- Modules expose classes and functions directly (no `__all__` except domain models)
- `__init__.py` files used as barrel re-exports for key modules (e.g., `dependencies/__init__.py`, `infrastructure/database/models/__init__.py`)
- `src/pilot_space/dependencies.py` is the primary barrel re-export file (excluded from 700-line check)

**Frontend Exports:**
- Feature modules use `index.ts` barrel exports grouping by: Types, API client, Constants, Components, Hooks
- Components export named exports (not default), e.g., `export { HomepageHub }`
- Stores and services are exported from feature `index.ts` when consumed cross-feature

**Barrel Pattern (Frontend):**
```typescript
// types
export type { ActivityCard, IssuePriority } from './types';
// api client
export { homepageApi } from './api/homepage-api';
// constants
export { ITEMS_PER_PAGE, STALE_THRESHOLD_DAYS } from './constants';
// components
export { HomepageHub } from './components/HomepageHub';
// hooks
export { useActiveCycleMetrics } from './hooks/useActiveCycleMetrics';
```

## Function Design

**Backend:**
- Async functions for all I/O (DB, HTTP, Redis, queue)
- Keyword-only arguments enforced with `*` for optional parameters (e.g., `*, limit: int = 50, include_deleted: bool = False`)
- Dataclasses with `frozen=True, slots=True` for service payloads/results
- Repository methods accept `UUID` objects (not strings)

**Frontend:**
- Hooks return named object destructure pattern: `{ data, isLoading, isError, mutate }`
- MobX stores use `makeAutoObservable(this, {}, { autoBind: true })` in constructor
- Private auto-save timers and disposers stored as `private _fieldName` (underscore-prefixed)
- `runInAction(() => {...})` wraps all observable mutations in async methods

## MobX State (Frontend-Specific)

- All complex observable state lives in MobX stores under `frontend/src/stores/`
- Feature-specific stores live in `frontend/src/stores/features/{feature}/`
- Stores registered on `RootStore` at `frontend/src/stores/RootStore.ts`
- `observer()` wrapper on React components that read MobX observables
- **Critical**: `IssueEditorContent` must NOT be `observer()` — see `frontend/.claude/rules/tiptap.md`
- `reaction()` used for side effects (auto-save, cross-store sync)
- `runInAction()` required for any observable mutation inside async code

---

*Convention analysis: 2026-03-07*
