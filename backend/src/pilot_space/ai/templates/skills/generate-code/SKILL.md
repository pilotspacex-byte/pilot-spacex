---
name: generate-code
description: Generate production-ready code for a feature or task, writing output directly to a note as a structured block
feature_module: docs
approval: suggest
model: sonnet
tools: [write_to_note, insert_block, replace_content]
required_approval_role: member
---

# Generate Code Skill

Generate production-ready code based on a feature description, issue context, or note content. Writes code blocks to the current note for review and integration.

## Quick Start

Use this skill when:
- User requests code generation for a feature (`/generate-code`)
- Agent detects an issue needs a code scaffold
- User provides a description of what code they need

**Example**:
```
User: "Generate a FastAPI endpoint for creating workspace invitations"

AI generates:
- Pydantic schema (InvitationCreateRequest, InvitationResponse)
- Service class (InvitationService.execute)
- Repository method stub (InvitationRepository.create)
- Router endpoint (POST /workspaces/{workspace_id}/invitations)
```

## Workflow

1. **Gather Context**
   - Read current note content for requirements and constraints
   - Fetch related issue details if issue_id is present in context
   - Identify target language/framework from workspace or note context
   - Check existing code patterns via `search_note_content` for consistency

2. **Plan Code Structure**
   - Identify components: schema, service, repository, router (backend) or component, hook, store (frontend)
   - Determine file placement following project conventions
   - Identify dependencies and imports needed

3. **Generate Code**
   - Write idiomatic, production-ready code with type hints
   - Follow project conventions: CQRS-lite (backend), MobX + TanStack Query (frontend)
   - Include docstrings for public APIs
   - No placeholders, no TODOs — complete implementations only

4. **Insert to Note**
   - Use `insert_block` to write each code block as a separate code fence
   - Prepend with a brief explanation heading
   - Include file path comment at top of each block

5. **Request Suggestion Approval**
   - Return `status: pending_suggestion` for user review before integration
   - User can edit blocks directly in the note before accepting

## Output Format

```json
{
  "status": "pending_suggestion",
  "skill": "generate-code",
  "blocks_inserted": 4,
  "note_id": "note-uuid",
  "summary": "Generated FastAPI endpoint with schema, service, repository stub, and router",
  "files_referenced": [
    "backend/src/pilot_space/api/v1/schemas/invitation.py",
    "backend/src/pilot_space/application/services/invitation_service.py",
    "backend/src/pilot_space/infrastructure/database/repositories/invitation_repository.py",
    "backend/src/pilot_space/api/v1/routers/invitations.py"
  ]
}
```

## Examples

### Example 1: Backend Service
**Input**: "Generate a service for creating workspace invitations with email validation"

**Output**: Inserts into note:
```
## Generated: InvitationService
<!-- File: backend/src/pilot_space/application/services/invitation_service.py -->
\`\`\`python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pilot_space.domain.entities.invitation import Invitation


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateInvitationPayload:
    workspace_id: UUID
    inviter_id: UUID
    email: str
    role: str = "member"


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateInvitationResult:
    invitation: Invitation
    email_sent: bool


class InvitationService:
    def __init__(self, invitation_repo: IInvitationRepository) -> None:
        self._repo = invitation_repo

    async def execute(self, payload: CreateInvitationPayload) -> CreateInvitationResult:
        """Create a workspace invitation and dispatch email notification."""
        ...
\`\`\`
```

### Example 2: React Component
**Input**: "Generate a React component for displaying an invitation card"

**Output**: Inserts into note:
```
## Generated: InvitationCard Component
<!-- File: frontend/src/features/workspace/components/InvitationCard.tsx -->
\`\`\`tsx
import { observer } from 'mobx-react-lite'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface InvitationCardProps {
  email: string
  role: string
  status: 'pending' | 'accepted' | 'expired'
  invitedAt: Date
}

export const InvitationCard = observer(function InvitationCard({
  email, role, status, invitedAt,
}: InvitationCardProps) {
  return (
    <Card>
      <CardHeader>{email}</CardHeader>
      <CardContent>
        <Badge variant={status === 'pending' ? 'default' : 'secondary'}>{status}</Badge>
      </CardContent>
    </Card>
  )
})
\`\`\`
```

## MCP Tools Used

- `search_note_content`: Find context and existing patterns in the current note
- `get_issue`: Fetch issue details when issue context is referenced
- `insert_block`: Write generated code blocks to the note
- `write_to_note`: Append summary heading and file references

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/generate-code` command or intent detection
- **SkillExecutor**: Acquires `note_write_lock:{note_id}` Redis mutex before `insert_block` (C-3)
- **Approval Flow**: Returns `pending_suggestion` — user reviews in note, no auto-persist (DD-003)
- **Memory**: Saves generated code pattern to workspace memory after user acceptance (T-050)

## References

- Design Decision: DD-003 (Critical-only approval)
- Design Decision: DD-086 (PilotSpaceAgent orchestrator)
- Constraint: C-3 (Redis mutex for note writes)
- Task: T-038
