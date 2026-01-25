# Contributing to Pilot Space

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

Thank you for contributing to Pilot Space! This guide covers our development workflow, code standards, and review process.

---

## Development Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| pnpm | 9+ | Package manager |
| Docker | 24+ | Local services |
| Supabase CLI | Latest | Local Supabase |

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/pilot-space.git
cd pilot-space

# Backend setup
cd backend
uv venv && source .venv/bin/activate
uv sync
pre-commit install

# Frontend setup
cd ../frontend
pnpm install

# Start services
docker compose up -d
supabase start

# Run development servers
cd backend && uvicorn pilot_space.main:app --reload &
cd frontend && pnpm dev
```

See [local-development.md](./local-development.md) for detailed setup instructions.

---

## Git Workflow

### Branch Naming

```
<type>/<issue-id>-<short-description>
```

**Types**:
- `feat/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation
- `test/` - Test additions/fixes
- `chore/` - Maintenance tasks

**Examples**:
```
feat/PS-123-add-ghost-text
fix/PS-456-login-timeout
refactor/PS-789-extract-ai-service
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<body - detailed description, motivation, context>

<footer - references to issues, breaking changes>
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `build`, `style`, `revert`

**Scopes**: `api`, `frontend`, `ai`, `auth`, `infra`, `db`, `docs`

**Example**:
```
feat(ai): add ghost text word boundary handling

Implement word-level streaming for ghost text suggestions per DD-067.
Buffer chunks until whitespace/punctuation before display to prevent
showing partial tokens.

- Add word boundary detection in GhostTextAgent
- Update SSE streaming to emit complete words
- Add tests for boundary edge cases

Closes: PS-234
Refs: DD-067
```

### Pull Request Process

1. **Create feature branch** from `main`
2. **Implement changes** with tests
3. **Run quality gates** locally
4. **Create PR** with description
5. **Address review feedback**
6. **Squash and merge** after approval

---

## Code Standards

### Python (Backend)

**Style**: PEP 8 + PEP 484 (type hints)

**Quality Gates**:
```bash
# Run all checks
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

**Requirements**:
- Type annotations on all public functions
- Docstrings on public classes and functions
- Test coverage > 80%
- File size < 700 lines

**Example**:
```python
from typing import Annotated
from pydantic import BaseModel, Field

class CreateIssuePayload(BaseModel):
    """Payload for creating a new issue."""

    title: Annotated[str, Field(min_length=1, max_length=200)]
    description: str | None = None
    priority: IssuePriority = IssuePriority.MEDIUM

async def create_issue(
    payload: CreateIssuePayload,
    repository: IssueRepository,
) -> Issue:
    """
    Create a new issue in the project.

    Args:
        payload: Issue creation data
        repository: Issue repository instance

    Returns:
        The created issue

    Raises:
        ValidationError: If payload is invalid
        DuplicateError: If similar issue exists
    """
    ...
```

### TypeScript (Frontend)

**Style**: ESLint + Prettier + strict TypeScript

**Quality Gates**:
```bash
# Run all checks
pnpm lint && pnpm type-check && pnpm test
```

**Requirements**:
- Strict TypeScript (no `any`)
- Discriminated unions for complex types
- Exhaustive switch statements
- Test coverage > 80%
- File size < 700 lines

**Example**:
```typescript
interface Issue {
  id: string;
  title: string;
  status: IssueStatus;
}

type IssueStatus =
  | { type: 'backlog' }
  | { type: 'in_progress'; startedAt: Date }
  | { type: 'completed'; completedAt: Date };

function getStatusLabel(status: IssueStatus): string {
  switch (status.type) {
    case 'backlog':
      return 'Backlog';
    case 'in_progress':
      return `Started ${status.startedAt.toLocaleDateString()}`;
    case 'completed':
      return `Completed ${status.completedAt.toLocaleDateString()}`;
    // TypeScript ensures exhaustiveness
  }
}
```

---

## Architecture Guidelines

### Backend Layers

```
api/           → HTTP endpoints, validation
application/   → Service classes (CQRS-lite)
domain/        → Entities, business rules
infrastructure/ → Database, external services
ai/            → AI agents and providers
```

**Rules**:
- Dependencies point inward only
- Domain layer has no external dependencies
- Use dependency injection
- Service classes have single responsibility

### Frontend Structure

```
app/           → Next.js pages and layouts
features/      → Feature modules (colocated)
components/    → Shared UI components
stores/        → MobX stores (UI state only)
services/      → API clients
hooks/         → Custom React hooks
```

**Rules**:
- MobX for UI-only state
- TanStack Query for ALL server data
- Feature modules are self-contained
- Components are accessible by default

---

## Testing Guidelines

### Test Pyramid

```
       ╱╲
      ╱  ╲
     ╱ E2E╲        < 10%  - Critical flows
    ╱──────╲
   ╱ Integr ╲      ~20%  - API, database
  ╱──────────╲
 ╱   Unit     ╲    >70%  - Functions, hooks
╱──────────────╲
```

### Backend Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Full test suite with coverage
pytest --cov=pilot_space --cov-report=html
```

**Example**:
```python
# tests/unit/test_issue_service.py
import pytest
from pilot_space.application.services import CreateIssueService

class TestCreateIssueService:
    async def test_create_issue_with_valid_payload(
        self, mock_repository, mock_event_bus
    ):
        service = CreateIssueService(mock_repository, mock_event_bus)
        payload = CreateIssuePayload(title="Test issue")

        result = await service.execute(payload)

        assert result.title == "Test issue"
        mock_repository.save.assert_called_once()
```

### Frontend Tests

```bash
# Unit/integration tests
pnpm test

# E2E tests
pnpm test:e2e

# Coverage report
pnpm test --coverage
```

**Example**:
```typescript
// features/issues/IssueCard.test.tsx
import { render, screen } from '@testing-library/react';
import { IssueCard } from './IssueCard';

describe('IssueCard', () => {
  it('displays issue title and status', () => {
    const issue = {
      id: '1',
      title: 'Test Issue',
      status: { type: 'backlog' as const },
    };

    render(<IssueCard issue={issue} />);

    expect(screen.getByText('Test Issue')).toBeInTheDocument();
    expect(screen.getByText('Backlog')).toBeInTheDocument();
  });
});
```

### Accessibility Tests

```typescript
// Include axe-core in component tests
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = render(<IssueCard issue={mockIssue} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

## Pull Request Template

```markdown
## Summary
<!-- Brief description of changes -->

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
<!-- Link to related issues: Closes #123 -->

## Changes Made
<!-- List of specific changes -->

## Testing
<!-- How were changes tested? -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Quality Checklist
- [ ] Code follows style guidelines
- [ ] Type checking passes
- [ ] Lint passes
- [ ] Tests pass with >80% coverage
- [ ] No files exceed 700 lines
- [ ] Accessibility requirements met
- [ ] Documentation updated (if needed)

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->
```

---

## Review Checklist

Reviewers should verify:

### Code Quality
- [ ] Code is readable and well-structured
- [ ] Functions have single responsibility
- [ ] No N+1 queries
- [ ] No blocking I/O in async functions
- [ ] Error handling is appropriate

### Security
- [ ] Input validation at boundaries
- [ ] No hardcoded secrets
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (proper escaping)

### Testing
- [ ] Tests cover happy path and edge cases
- [ ] Tests are deterministic
- [ ] Mocks are appropriate (not over-mocked)

### Documentation
- [ ] Public APIs are documented
- [ ] Complex logic has comments
- [ ] README updated if needed

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Workflow

1. Create release branch: `release/v1.2.0`
2. Update changelog
3. Run full test suite
4. Create GitHub release
5. Deploy to staging
6. Verify staging
7. Deploy to production

---

## Getting Help

- **Documentation**: Check `docs/` and `specs/` directories
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Slack**: Join `#pilot-space-dev` channel

---

## References

- [testing-strategy.md](./testing-strategy.md) - Detailed testing guide
- [local-development.md](./local-development.md) - Local setup guide
- [ci-cd-pipeline.md](./ci-cd-pipeline.md) - CI/CD configuration
- [DESIGN_DECISIONS.md](../../../../docs/DESIGN_DECISIONS.md) - Architecture decisions
