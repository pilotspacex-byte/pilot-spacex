# Cross-Cutting Clarifications Prompt Template

> **Purpose**: Resolve technical decisions that affect multiple user stories or components, ensuring consistency across the codebase.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` Cross-Cutting Clarifications section
>
> **Usage**: Use when a technical decision affects multiple features and needs consistent resolution.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Software Architect with 15 years designing enterprise systems.
You excel at:
- Identifying cross-cutting concerns that span multiple features
- Establishing consistent patterns across large codebases
- Documenting decisions with clear traceability to affected components
- Balancing standardization with feature-specific needs

# Stakes Framing (P6)

Cross-cutting decisions impact the entire [PROJECT_NAME] codebase.
Getting these right will:
- Reduce inconsistency bugs by 70% through unified patterns
- Enable 40% faster onboarding with predictable conventions
- Prevent expensive refactoring when patterns conflict

I'll tip you $200 for comprehensive clarifications with clear implementation guidance.

# Clarification Context

## Concern Category
[CATEGORY_NAME] (e.g., Authentication, Background Jobs, Data Model, AI Provider)

## Affected Stories
[US-XX], [US-YY], [US-ZZ]

## Current State
- **Existing Pattern**: [CURRENT_APPROACH_IF_ANY]
- **Pain Points**: [INCONSISTENCIES_OR_GAPS]
- **Stakeholder Input**: [DECISIONS_ALREADY_MADE]

# Task Decomposition (P3)

Evaluate each clarification question step by step:

## Step 1: Question Inventory
List all questions requiring resolution:

| # | Question | Stories Affected | Impact if Unresolved |
|---|----------|------------------|---------------------|
| 1 | [QUESTION_1] | [US-XX, US-YY] | [RISK] |
| 2 | [QUESTION_2] | [US-XX, US-ZZ] | [RISK] |
| 3 | [QUESTION_3] | [US-YY, US-ZZ] | [RISK] |

## Step 2: Resolution Analysis
For each question:

### Question [N]: [QUESTION_TEXT]

**Options Considered**:
| Option | Pros | Cons |
|--------|------|------|
| [OPTION_A] | [PROS] | [CONS] |
| [OPTION_B] | [PROS] | [CONS] |

**Selected Answer**: [ANSWER]

**Rationale**: [WHY_THIS_ANSWER]

**Implementation Impact**:
| Story | Component | Change Required |
|-------|-----------|-----------------|
| [US-XX] | [COMPONENT] | [CHANGE] |
| [US-YY] | [COMPONENT] | [CHANGE] |

## Step 3: Consistency Verification
Verify answers don't conflict:

| Q1 Answer | Q2 Answer | Consistent? | Resolution if Not |
|-----------|-----------|-------------|-------------------|
| [ANS_1] | [ANS_2] | Yes/No | [RESOLUTION] |

## Step 4: Implementation Pattern
Document the unified pattern:

**Pattern Name**: [PATTERN_NAME]

**Code Example**:
```python
# Show the standard implementation
```

**Anti-Pattern** (avoid this):
```python
# Show inconsistent approach to avoid
```

**Enforcement**:
- [ ] Pre-commit hook: [HOOK_DESCRIPTION]
- [ ] Code review checklist: [CHECKLIST_ITEM]
- [ ] Documentation: [DOC_LOCATION]

# Self-Evaluation Framework (P15)

Rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All questions resolved | ___ | |
| **Consistency**: Answers don't conflict | ___ | |
| **Traceability**: Stories mapped to impacts | ___ | |
| **Implementability**: Patterns are actionable | ___ | |
| **Enforcement**: Consistency can be verified | ___ | |

If any < 0.9, refine before presenting.

# Output Format

```markdown
## [CONCERN_CATEGORY] (Cross-Cutting)

| Question | Answer | Stories Affected |
|----------|--------|------------------|
| [Q1] | [A1] | [US-XX, US-YY] |
| [Q2] | [A2] | [US-XX, US-ZZ] |

**Implementation Pattern**:
[CODE_EXAMPLE]

**Enforcement**: [HOW_TO_VERIFY]
```
```

---

## Example: Authentication & Authorization (from plan.md)

```markdown
## Authentication & Authorization (FR-060 to FR-062, FR-117 to FR-123)

| Question | Answer | Stories Affected |
|----------|--------|------------------|
| Auth system? | Supabase Auth (GoTrue) | All |
| Authorization? | Row-Level Security (RLS) | All |
| Session strategy? | Access token (1h) + Refresh token (7d) | All |
| API key encryption? | AES-256-GCM with Supabase Vault | US-11 |
| Admin RLS handling? | Role check in policy | All |

**Implementation Pattern**:
```python
# Service layer always receives user context
async def get_issues(
    workspace_id: UUID,
    user: AuthenticatedUser,  # From dependency injection
    db: AsyncSession
) -> list[Issue]:
    # RLS automatically filters by user's workspace access
    return await issue_repo.list_for_workspace(workspace_id)
```

**Enforcement**:
- Pre-commit: `rls-policy-check` validates all tables have RLS
- Code review: Verify user context passed to all data access
```

---

## Example: Background Jobs (from plan.md)

```markdown
## Background Jobs (FR-095 to FR-101)

| Question | Answer | Stories Affected |
|----------|--------|------------------|
| Queue system? | Supabase Queues (pgmq + pg_cron) | US-03, US-10, US-14 |
| Priority levels? | High (PR review), Normal (embeddings), Low (graph recalc) | US-03, US-10, US-14 |
| AI job timeout? | 5 minutes | All AI features |
| Failed job handling? | Dead letter queue + admin notification | All |
| Batch schedule? | Nightly 2 AM UTC | US-10, US-14 |

**Implementation Pattern**:
```python
# Queue job with priority
await queue.enqueue(
    queue_name="ai_high",  # Priority queue
    payload={"pr_id": pr_id, "repo": repo},
    timeout=timedelta(minutes=5)
)
```

**Enforcement**:
- All AI jobs use `ai_high`, `ai_normal`, or `ai_low` queues
- Timeout explicitly set (no defaults)
```

---

## Example: Data Model & API (from plan.md)

```markdown
## Data Model & API (FR-001 to FR-065)

| Question | Answer | Stories Affected |
|----------|--------|------------------|
| Issue link modeling? | Junction table `issue_links` | US-02, US-12 |
| Pagination strategy? | Cursor-based | All list views |
| List response format? | `{data: [...], meta: {total, cursor, hasMore}}` | All APIs |
| Optimistic updates? | TanStack Query with rollback | All mutations |
| Issue state transitions? | All forward; completed→started; any→cancelled | US-04, US-18 |
| Soft-delete restoration? | Creator OR admin/owner | All entities |
| Export/import format? | JSON archive (ZIP) | US-11 |

**Implementation Pattern**:
```python
# Cursor-based pagination response
class PaginatedResponse(Generic[T]):
    data: list[T]
    meta: PaginationMeta

class PaginationMeta:
    total: int
    cursor: str | None
    has_more: bool
```
```

---

## Example: AI Provider Routing (from plan.md)

```markdown
## AI Provider Routing (All AI features)

| Question | Answer | Stories Affected |
|----------|--------|------------------|
| Failover strategy? | Auto failover to next-best provider on error | All AI |
| Rate limiting? | 1000/min standard, 100/min AI endpoints | All |
| AI streaming? | SSE via FastAPI StreamingResponse | US-01, US-12 |
| AI execution boundary? | All AI in FastAPI. Edge Functions for webhooks only | All AI |

**Implementation Pattern**:
```python
# Provider routing with failover
async def complete(prompt: str, task_type: TaskType) -> str:
    providers = get_providers_for_task(task_type)
    for provider in providers:
        try:
            return await provider.complete(prompt)
        except ProviderError:
            continue
    raise AllProvidersFailedError()
```

**Provider Selection by Task**:
| Task Type | Primary | Fallback |
|-----------|---------|----------|
| Code review | Claude | GPT-4 |
| Ghost text | Gemini Flash | Claude Haiku |
| Embeddings | OpenAI | - |
```

---

## Concern Categories

Use this template for these cross-cutting concerns:

### Infrastructure
- Authentication & session management
- Authorization & RLS patterns
- Background job processing
- Caching strategies
- Logging & observability

### Data
- Pagination patterns
- Soft delete behavior
- Audit logging
- Data export/import

### API
- Error response format
- Versioning strategy
- Rate limiting
- Response envelopes

### AI Layer
- Provider routing
- Streaming patterns
- Context aggregation
- Timeout handling

### Frontend
- State management boundaries
- Real-time update merging
- Error display patterns
- Loading states

---

## Validation Checklist

Before finalizing clarifications:

- [ ] All questions have definitive answers (no "TBD")
- [ ] Each answer lists affected stories
- [ ] Answers don't contradict each other
- [ ] Implementation patterns provided with code
- [ ] Anti-patterns documented
- [ ] Enforcement mechanism specified

---

*Template Version: 1.0*
*Extracted from: plan.md v7.0 Cross-Cutting Clarifications*
*Techniques Applied: P3 (decomposition), P6 (stakes), P15 (self-eval), P16 (persona)*
