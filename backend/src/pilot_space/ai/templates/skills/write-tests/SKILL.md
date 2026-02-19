---
name: write-tests
description: Generate comprehensive unit and integration tests for existing code, writing output to a note block for review
approval: suggest
model: sonnet
tools: [write_to_note, insert_block, search_note_content]
required_approval_role: member
---

# Write Tests Skill

Generate unit tests, integration tests, or end-to-end tests for existing code. Analyzes code structure to produce comprehensive test coverage including happy paths, edge cases, and error scenarios.

## Quick Start

Use this skill when:
- User requests test generation (`/write-tests`)
- Agent detects low coverage for a code block
- User pastes code and asks for tests

**Example**:
```
User: "Write tests for the InvitationService.execute method"

AI generates:
- Unit test: happy path — valid invitation created
- Unit test: duplicate email raises ValueError
- Unit test: invalid role raises ValidationError
- Integration test: full create → email dispatch → DB persist flow
```

## Workflow

1. **Analyze Target Code**
   - Read note content for the code to be tested
   - Search for existing test files via `search_note_content`
   - Identify: public API surface, dependencies, invariants, error paths

2. **Determine Test Strategy**
   - Unit tests: mock all external dependencies (repos, queues, email)
   - Integration tests: use real DB session, mock only external APIs
   - Coverage target: >80% per project standard

3. **Generate Tests**
   - Framework: `pytest` + `pytest-asyncio` for async (backend), `vitest` for frontend
   - Use `AsyncMock` for async repo/service dependencies
   - Follow AAA pattern: Arrange → Act → Assert
   - Cover: happy path, at least 2 edge cases, error/exception paths
   - No placeholders — all `assert` statements must have concrete expected values

4. **Insert to Note**
   - Use `insert_block` to add test code blocks after the existing code in the note
   - Prepend with `## Generated Tests: <ClassName>` heading
   - Include file path comment at top of block

5. **Return Suggestion Status**
   - Return `status: pending_suggestion` — user reviews before copying to test file
   - Include coverage estimate in summary

## Output Format

```json
{
  "status": "pending_suggestion",
  "skill": "write-tests",
  "blocks_inserted": 2,
  "note_id": "note-uuid",
  "summary": "Generated 8 unit tests + 2 integration tests for InvitationService",
  "estimated_coverage": "92%",
  "test_file_path": "backend/tests/unit/services/test_invitation_service.py"
}
```

## Examples

### Example 1: Async Service Unit Tests
**Input**: InvitationService.execute code block in note

**Output**: Inserts into note:
```
## Generated Tests: InvitationService
<!-- File: backend/tests/unit/services/test_invitation_service.py -->
\`\`\`python
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from pilot_space.application.services.invitation_service import (
    InvitationService,
    CreateInvitationPayload,
)


@pytest.fixture
def invitation_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(invitation_repo: AsyncMock) -> InvitationService:
    return InvitationService(invitation_repo=invitation_repo)


@pytest.mark.asyncio
async def test_create_invitation_happy_path(service: InvitationService, invitation_repo: AsyncMock) -> None:
    workspace_id = uuid4()
    inviter_id = uuid4()
    payload = CreateInvitationPayload(
        workspace_id=workspace_id,
        inviter_id=inviter_id,
        email="user@example.com",
        role="member",
    )

    result = await service.execute(payload)

    invitation_repo.create.assert_called_once()
    assert result.email_sent is True


@pytest.mark.asyncio
async def test_create_invitation_duplicate_email_raises(service: InvitationService, invitation_repo: AsyncMock) -> None:
    invitation_repo.get_by_email.return_value = object()
    payload = CreateInvitationPayload(
        workspace_id=uuid4(), inviter_id=uuid4(), email="existing@example.com", role="member"
    )

    with pytest.raises(ValueError, match="already invited"):
        await service.execute(payload)
\`\`\`
```

### Example 2: React Component Tests
**Input**: InvitationCard component in note

**Output**: Inserts into note:
```
## Generated Tests: InvitationCard
<!-- File: frontend/src/features/workspace/components/InvitationCard.test.tsx -->
\`\`\`tsx
import { render, screen } from '@testing-library/react'
import { InvitationCard } from './InvitationCard'

describe('InvitationCard', () => {
  it('renders email and pending badge', () => {
    render(<InvitationCard email="user@example.com" role="member" status="pending" invitedAt={new Date()} />)
    expect(screen.getByText('user@example.com')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('renders secondary badge for accepted status', () => {
    render(<InvitationCard email="a@b.com" role="member" status="accepted" invitedAt={new Date()} />)
    const badge = screen.getByText('accepted')
    expect(badge).toHaveClass('bg-secondary')
  })
})
\`\`\`
```

## MCP Tools Used

- `search_note_content`: Find the source code to test and any existing test patterns
- `get_issue`: Fetch issue context if tests are tied to a specific issue
- `insert_block`: Write test code blocks to the note

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/write-tests` command
- **SkillExecutor**: Acquires `note_write_lock:{note_id}` Redis mutex before `insert_block` (C-3)
- **Approval Flow**: Returns `pending_suggestion` — tests inserted as blocks, not auto-committed (DD-003)

## References

- Design Decision: DD-003 (Critical-only approval)
- Constraint: C-3 (Redis mutex for note writes)
- Task: T-039
- Coverage requirement: >80% per project standard (backend/CLAUDE.md)
