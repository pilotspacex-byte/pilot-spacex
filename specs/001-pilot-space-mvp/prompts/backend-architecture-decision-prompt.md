# Backend Architecture Decision Prompt Template

> **Purpose**: Resolve backend architecture decisions with structured analysis, pattern alignment, and implementation guidance.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` Architecture Pattern Decisions section
>
> **Usage**: Use when facing backend architecture ambiguities requiring technical decision-making.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Backend Architect with 15 years designing scalable distributed systems.
You excel at:
- Service layer architecture (CQRS, DDD, Clean Architecture)
- Database design and query optimization (N+1 prevention, indexing strategies)
- API design patterns (REST, GraphQL, versioning, error handling)
- Dependency injection and testability patterns
- Performance optimization (caching, async processing, connection pooling)

# Stakes Framing (P6)

This backend architecture decision impacts [PROJECT_NAME]'s scalability and maintainability.
Getting it right will:
- Reduce operational costs by 40% through efficient query patterns
- Enable horizontal scaling without rewrites
- Prevent data integrity issues that could cost $100,000+ to fix

I'll tip you $200 for a thorough analysis with production-ready implementation guidance.

# Decision Context

## Question
[STATE THE SPECIFIC ARCHITECTURE QUESTION]

## Relevant Context
- **Current Stack**: [BACKEND_STACK]
- **Database**: [DATABASE_TYPE_AND_VERSION]
- **Related Patterns**: [EXISTING_PATTERNS_IN_CODEBASE]
- **Constraints**: [PERFORMANCE/SCALE/COMPLIANCE_CONSTRAINTS]
- **Affected Services**: [SERVICE_LIST]

# Task Decomposition (P3)

Evaluate this decision step by step:

## Step 1: Problem Framing
| Aspect | Details |
|--------|---------|
| **What problem are we solving?** | [PROBLEM_STATEMENT] |
| **Why does this matter?** | [BUSINESS_IMPACT] |
| **What are the constraints?** | [TECHNICAL_CONSTRAINTS] |
| **What does success look like?** | [SUCCESS_CRITERIA] |

## Step 2: Pattern Alignment Check
Verify against established patterns:

| Pattern Category | Project Standard | Decision Must Align With |
|------------------|------------------|--------------------------|
| Service Layer | [CURRENT_PATTERN] | [COMPATIBILITY_REQUIREMENT] |
| Repository | [CURRENT_PATTERN] | [COMPATIBILITY_REQUIREMENT] |
| DI Container | [CURRENT_PATTERN] | [COMPATIBILITY_REQUIREMENT] |
| Error Handling | [CURRENT_PATTERN] | [COMPATIBILITY_REQUIREMENT] |

## Step 3: Options Analysis
Identify at least 3 viable options:

### Option A: [OPTION_NAME]
**Description**: [HOW_IT_WORKS]

**Pros**:
- [PRO_1]
- [PRO_2]

**Cons**:
- [CON_1]
- [CON_2]

**Implementation Example**:
```python
# Code example showing pattern
```

### Option B: [OPTION_NAME]
[Same structure as Option A]

### Option C: [OPTION_NAME]
[Same structure as Option A]

## Step 4: Decision Matrix
| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Query Performance | [1-5] | [1-5] | [1-5] | [1-5] |
| Maintainability | [1-5] | [1-5] | [1-5] | [1-5] |
| Testability | [1-5] | [1-5] | [1-5] | [1-5] |
| Pattern Consistency | [1-5] | [1-5] | [1-5] | [1-5] |
| Migration Complexity | [1-5] | [1-5] | [1-5] | [1-5] |
| **Weighted Total** | | **[SCORE]** | **[SCORE]** | **[SCORE]** |

## Step 5: Decision Documentation
| Aspect | Details |
|--------|---------|
| **Chosen Option** | [OPTION_NAME] |
| **Rationale** | [WHY_THIS_WINS] |
| **Trade-offs Accepted** | [ACKNOWLEDGED_CONS] |
| **Reversibility** | [HOW_TO_CHANGE_LATER] |
| **Pattern Reference** | [DOC_REFERENCE] |

## Step 6: Implementation Guidance

**Recommended Pattern**:
```python
# Show the recommended code pattern with type hints
```

**Anti-Pattern** (avoid this):
```python
# Show the pattern that leads to problems
```

**N+1 Prevention Check**:
```python
# Show eager loading or query optimization pattern
```

**Edge Cases**:
| Scenario | Handling |
|----------|----------|
| [EDGE_CASE_1] | [HOW_TO_HANDLE] |
| [EDGE_CASE_2] | [HOW_TO_HANDLE] |

**Testing Approach**:
```python
# Show how to test this pattern
```

# Self-Evaluation Framework (P15)

Rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All options considered | ___ | |
| **Clarity**: Decision is unambiguous | ___ | |
| **Performance**: Query patterns optimized | ___ | |
| **Consistency**: Aligns with project patterns | ___ | |
| **Testability**: Pattern is easily testable | ___ | |

If any < 0.9, refine before presenting.

# Output Format

```markdown
### [N]. [DECISION_TITLE]

| Question | [FULL_QUESTION] |
|----------|-----------------|
| **Decision** | [CHOSEN_APPROACH] - [BRIEF_DESCRIPTION] |
| **Pattern Reference** | [PATTERN_DOC] |
| **Implementation** | [KEY_IMPLEMENTATION_DETAIL] |
| **[ADDITIONAL_ASPECT]** | [DETAIL] |
```
```

---

## Example Decisions (from plan.md)

### 1. CQRS Handlers Pattern

| Question | How to structure command/query handlers? |
|----------|------------------------------------------|
| **Decision** | Service Classes with Payloads (`CreateIssueService.execute(payload)`) |
| **Pattern Reference** | Custom, inspired by 08-service-layer |
| **Implementation** | Separate service class per command, payload DTO as input |
| **Testing** | Mock repository, verify service calls repository methods |

### 2. Repository Pattern

| Question | Generic vs specific repositories? |
|----------|-----------------------------------|
| **Decision** | Generic + Specific (`BaseRepository[T]` + domain methods) |
| **Pattern Reference** | 07-repository-pattern |
| **Generic Scope** | CRUD operations, pagination, soft delete |
| **Specific Scope** | Domain queries (e.g., `find_by_workspace_and_state`) |

### 3. DI Container Selection

| Question | Which DI container for Python backend? |
|----------|----------------------------------------|
| **Decision** | `dependency-injector` library (Singleton + Factory) |
| **Pattern Reference** | 26-dependency-injection |
| **Implementation** | Container per module, wire at application startup |
| **Testing** | Override providers in test fixtures |

### 4. Error Format

| Question | How to format API errors? |
|----------|---------------------------|
| **Decision** | RFC 7807 Problem Details |
| **Implementation** | `{"type": "...", "title": "...", "status": N, "detail": "..."}` |
| **Consistency** | All endpoints return same error shape |

### 5. AI Agent Pattern

| Question | How to structure AI agents? |
|----------|----------------------------|
| **Decision** | Claude Agent SDK (state machine orchestration) |
| **Pattern Reference** | Custom (not in patterns library) |
| **Implementation** | Agent class with `query()` for one-shot, `ClaudeSDKClient` for multi-turn |
| **Streaming** | SSE via FastAPI StreamingResponse |

---

## Decision Categories

Use this template for these backend architecture decisions:

### Service Layer
- Command/Query handler structure
- Service class responsibilities
- Transaction boundaries
- Event publishing patterns

### Data Access
- Repository pattern selection
- Query optimization (N+1 prevention)
- Eager vs lazy loading
- Pagination strategies (cursor vs offset)

### Infrastructure
- DI container configuration
- Configuration management
- Logging and tracing
- Cache layer design

### API Design
- Error format standardization
- Versioning strategy
- Request validation patterns
- Response envelope design

### AI Layer
- Agent orchestration patterns
- Provider routing strategies
- Streaming response handling
- Context aggregation patterns

---

## Validation Checklist

Before finalizing decision:

- [ ] At least 3 options analyzed
- [ ] Decision matrix completed with weighted scores
- [ ] Pattern alignment verified against project standards
- [ ] Code examples for both pattern and anti-pattern
- [ ] N+1 query prevention verified
- [ ] Testing approach documented
- [ ] Reversibility path clear

---

*Template Version: 1.0*
*Extracted from: plan.md v7.0 Architecture Pattern Decisions*
*Techniques Applied: P3 (decomposition), P6 (stakes), P15 (self-eval), P16 (persona)*
