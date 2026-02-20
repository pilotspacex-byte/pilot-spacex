# Application Services Layer - Pilot Space

**For parent layer overview, see [application/README.md](../README.md)**

---

## Overview

Application services implement business logic via the CQRS-lite pattern (DD-064). Every service follows `Service.execute(Payload) -> Result` with explicit dataclass payloads, typed results, and async execution. Services are the single entry point for all business operations -- routers, webhooks, and AI tools all call through services.

---

## Service Inventory

```
note/ (10 services)
  CreateNoteService, UpdateNoteService, GetNoteService, ListNotesService,
  DeleteNoteService, PinNoteService, CreateNoteFromChatService, AIUpdateService,
  ListAnnotationsService, UpdateAnnotationService

issue/ (6 services)
  CreateIssueService, UpdateIssueService, ListIssuesService,
  GetIssueService, DeleteIssueService, ActivityService

cycle/ (5 services)
  CreateCycleService, UpdateCycleService, GetCycleService,
  AddIssueToCycleService, RolloverCycleService

ai_context/ (3 services)
  GenerateAIContextService, RefineAIContextService, ExportAIContextService

annotation/ (1 service)
  CreateAnnotationService

discussion/ (1 service)
  CreateDiscussionService

integration/ (4 services)
  ConnectGitHubService, LinkCommitService,
  ProcessWebhookService, AutoTransitionService

onboarding/ (3 services)
  CreateGuidedNoteService, GetOnboardingService, UpdateOnboardingService

role_skill/ (5 services)
  CreateRoleSkillService, UpdateRoleSkillService, DeleteRoleSkillService,
  GenerateRoleSkillService, ListRoleSkillsService

homepage/ (3 services)
  GetActivityService, GetDigestService, DismissSuggestionService

workspace.py (1 service)
  WorkspaceService (InviteMember)
```

---

## Note Services

**Location**: `note/`

| Service | Purpose | Payload/Result | Key Constraints |
|---------|---------|----------------|-----------------|
| CreateNoteService | Create note with optional template | See `create_note_service.py` | Title required (<255 chars), calculates word count |
| UpdateNoteService | Update blocks/metadata with field diffing | See `update_note_service.py` | Tracks `changed_fields` for activity logging |
| GetNoteService | Retrieve with eager-loaded relations | See `get_note_service.py` | Loads annotations, discussions, issue links |
| ListNotesService | Paginated workspace notes | See `list_notes_service.py` | Cursor pagination, workspace-scoped |
| DeleteNoteService | Soft delete note | See `delete_note_service.py` | Soft delete only |
| PinNoteService | Toggle note pin status | See `pin_note_service.py` | -- |
| CreateNoteFromChatService | Convert chat session to note | See `create_note_from_chat_service.py` | Links to source chat session |
| AIUpdateService | Apply AI-generated content updates | See `ai_update_service.py` | Tracks blocks updated, creates activity |
| ListAnnotationsService | List annotations for a note | See `list_annotations_service.py` | Workspace-scoped |
| UpdateAnnotationService | Update annotation content | See `update_annotation_service.py` | Validates confidence [0.0-1.0] |

---

## Issue Services

**Location**: `issue/`

| Service | Purpose | Key Constraints |
|---------|---------|-----------------|
| CreateIssueService | Create issue with sequence ID, state, labels | Sequence ID race-safe via `SELECT FOR UPDATE`. Default state required. See `create_issue_service.py` |
| UpdateIssueService | Field-level change detection | Uses `UNCHANGED` sentinel to distinguish "no change" from "set to null". See `update_issue_service.py` |
| ListIssuesService | Paginated search with filters | Filters: state, assignee, cycle, labels, search text. Cursor-based. See `list_issues_service.py` |
| GetIssueService | Single issue with full relations | Eager-loads activity history, related issues, linked notes. See `get_issue_service.py` |
| DeleteIssueService | Soft delete issue | See `delete_issue_service.py` |
| ActivityService | Log issue mutations for audit trail | Activity types: CREATED, UPDATED, STATE_CHANGED, ASSIGNED, etc. See `activity_service.py` |

---

## Cycle Services

**Location**: `cycle/`

| Service | Purpose | Key Validation |
|---------|---------|----------------|
| CreateCycleService | Create sprint/cycle | name required, end_date >= start_date, one ACTIVE per project |
| UpdateCycleService | Update with constraints | Cannot ACTIVE if issues exceed capacity, auto-deactivates others |
| GetCycleService | Retrieve with metrics | Velocity, issue counts by state, burn-down data |
| AddIssueToCycleService | Assign issue to cycle | State must support cycle (not Backlog/Done), cycle ACTIVE/DRAFT |
| RolloverCycleService | Complete and carry over | Archives Done, moves In Progress/Todo to next, calculates velocity |

---

## AI Context Services

**Location**: `ai_context/`

| Service | Purpose | Key Features |
|---------|---------|-------------|
| GenerateAIContextService | Aggregate issue context for AI | 1hr Redis cache, Gemini 768-dim embeddings, semantic similarity (0.7 threshold), Claude Code prompt generation. See `generate_ai_context_service.py` |
| RefineAIContextService | Improve context from user feedback | Accepts `missing_info` list. See `refine_ai_context_service.py` |
| ExportAIContextService | Export to markdown/JSON/claude_dev | See `export_ai_context_service.py` |

---

## Other Services

### Annotation (`annotation/`)

**CreateAnnotationService**: AI margin suggestions on note blocks. Validates confidence [0.0-1.0], non-empty content, block exists. High confidence threshold: >=0.8. See `create_annotation_service.py`.

### Discussion (`discussion/`)

**CreateDiscussionService**: Atomically creates discussion thread + first comment in single transaction. Rollback on failure. See `create_discussion_service.py`.

### Integration (`integration/`)

| Service | Purpose |
|---------|---------|
| ConnectGitHubService | OAuth code exchange, token encryption via Supabase Vault |
| ProcessWebhookService | GitHub webhook events, HMAC-SHA256 signature verification |
| LinkCommitService | Auto-links commits to issues by parsing "Fixes #42", "Closes #123" |
| AutoTransitionService | PR opened -> In Review, PR merged -> Done, Commit pushed -> In Progress |

### Onboarding (`onboarding/`)

CreateGuidedNoteService (template notes), GetOnboardingService (tracks progress), UpdateOnboardingService (marks steps complete). Types defined in `onboarding/types.py`.

### Role Skill (`role_skill/`)

CreateRoleSkillService (max 3 roles, no duplicate `role_type`), UpdateRoleSkillService, DeleteRoleSkillService, GenerateRoleSkillService (AI-powered via Claude Sonnet with fallback), ListRoleSkillsService. Types defined in `role_skill/types.py`.

### Homepage (`homepage/`)

GetActivityService (workspace activity feed), GetDigestService (weekly/daily digest), DismissSuggestionService.

### Workspace (`workspace.py`)

Invites member: immediate add if user exists, pending invitation if not. Auto-accepts on signup.

---

## Related Documentation

- **Parent layer**: [application/README.md](../README.md) (CQRS-lite pattern, DI, error handling, transaction boundaries)
- **Repository pattern**: [infrastructure/database/README.md](../../infrastructure/database/README.md)
- **Domain entities**: [domain/models/README.md](../../domain/models/README.md)
- **Design decisions**: `docs/DESIGN_DECISIONS.md` (DD-064: CQRS-lite)
