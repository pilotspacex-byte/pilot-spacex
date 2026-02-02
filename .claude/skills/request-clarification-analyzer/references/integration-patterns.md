# Integration Patterns with Other Skills

This document explains how the request-clarification-analyzer skill integrates with other skills to create comprehensive workflows.

## Integration Philosophy

The request-clarification-analyzer acts as a **pre-processor** that:
1. Analyzes ambiguous user requests
2. Generates context-aware clarification questions
3. Refines requirements before passing to downstream skills
4. Prevents costly rework from unclear specifications

**Key Principle**: Clarify BEFORE specification/planning/implementation, not after.

---

## Primary Integration: Specification-Driven Development (SDD)

### Integration Point: Phase 1 (Specification Creation)

**Workflow**:
```
User Request (vague) → Clarification Analyzer → Refined Request → SDD Specification Phase
```

### When to Invoke Clarification

**Automatic Triggers** (clarification-analyzer should run automatically):
- [ ] Request contains ambiguous terms (scale, fast, real-time, etc.)
- [ ] Multiple valid interpretations exist
- [ ] Request conflicts with known architectural patterns
- [ ] Scope is undefined or unbounded
- [ ] Technology choices are unspecified

**Manual Invocation**:
- User explicitly requests clarification: "Can you help clarify my requirements?"
- SDD Phase 2 (Clarify) detects ambiguities marked `[NEEDS CLARIFICATION]` in spec.md

### Integration Example

**User Request**: "Add user dashboard with analytics"

**Step 1: Clarification Analyzer**
```markdown
Analyzing request against project context...

**Ambiguity Detected**: "analytics" is undefined

**Question 1 of 3**: What type of analytics should the dashboard display?

| Option | Description | Existing Pattern | Score |
|--------|-------------|------------------|-------|
| A | Basic usage metrics (logins, actions) | Similar to admin-dashboard/metrics | 85/100 |
| B | Real-time event stream | Kafka consumer pattern | 65/100 |
| C | Historical trends with charts | analytics-service/reports | 75/100 |

**Recommended**: Option A - Simplest, matches admin dashboard pattern

**User Choice**: A

**Refined Output**:
"Add user dashboard displaying basic usage metrics (login count, action history, last active timestamp) following the admin-dashboard/metrics pattern"
```

**Step 2: SDD Specification Phase**
```markdown
Now generating structured specification from refined requirements...

# Feature Specification: User Dashboard - Basic Usage Metrics

**Input**: "Add user dashboard displaying basic usage metrics (login count, action history, last active timestamp) following the admin-dashboard/metrics pattern"

## User Story 1 - User Views Personal Activity Metrics (Priority: P1)

As a logged-in user, I want to see my recent activity metrics so that I can understand my usage patterns.

**Acceptance Scenarios**:
1. **Given** user is authenticated, **When** user navigates to /dashboard, **Then** display login count (last 30 days)
2. **Given** user is authenticated, **When** dashboard loads, **Then** display last 10 actions with timestamps
3. **Given** user is authenticated, **When** dashboard loads, **Then** display "last active" timestamp

[Remainder of specification follows SDD template...]
```

**Benefit**: Specification is concrete and actionable, not vague.

---

## Integration Workflow Patterns

### Pattern 1: Pre-Specification Clarification (Recommended)

**When**: User provides high-level feature idea

**Workflow**:
1. **Clarification Analyzer**: Generate questions, refine requirements
2. **SDD Phase 1 (Specify)**: Create structured specification from refined input
3. **SDD Phase 2 (Clarify)**: Handle remaining ambiguities with spec-level questions
4. **SDD Phase 3-6**: Plan → Tasks → Implement

**Advantages**:
- Catches ambiguities early
- Refined input produces better specifications
- Reduces back-and-forth during implementation

**Example Commands**:
```bash
# User provides vague request
User: "I want to add authentication to the dashboard"

# Clarification analyzer automatically runs
[Skill: request-clarification-analyzer]
→ Question: Which auth pattern? (JWT, API key, OAuth)
→ User chooses: JWT with RBAC

# SDD specification phase with refined input
[Skill: specification-driven-development]
→ /speckit.specify "Add JWT authentication with RBAC to dashboard"
```

### Pattern 2: Mid-Specification Clarification

**When**: SDD Phase 2 detects `[NEEDS CLARIFICATION]` markers in spec.md

**Workflow**:
1. **SDD Phase 1 (Specify)**: Creates spec with `[NEEDS CLARIFICATION: term]` markers
2. **Clarification Analyzer**: Invoked automatically for marked terms
3. **SDD Phase 2 (Clarify)**: Updates spec with clarified requirements
4. **SDD Phase 3-6**: Continue with planning and implementation

**Example**:
```markdown
# From spec.md after Phase 1

## Functional Requirements

1. System shall provide [NEEDS CLARIFICATION: real-time] updates to dashboard
2. Users can [NEEDS CLARIFICATION: export] their data
3. System shall [NEEDS CLARIFICATION: scale] to handle increased load

---

# Clarification analyzer processes each marker

**Clarifying "real-time"**:
- [ ] WebSocket updates every 100ms?
- [ ] Server-sent events every 1s?
- [ ] Polling every 5s?

User chooses: "Polling every 5s is sufficient"

**Updated spec.md**:
1. System shall provide dashboard updates via polling (5-second interval)
```

### Pattern 3: Architecture Conflict Resolution

**When**: Request conflicts with established architectural patterns

**Workflow**:
1. **Clarification Analyzer**: Detects architecture violation
2. **Presents conflict**: Shows request vs established pattern
3. **Offers alternatives**: Architecture-compliant options with rationale
4. **User decides**: Proceed with compliant option OR justify violation
5. **SDD continues**: With compliant approach or documented exception

**Example** (Three-Tier Architecture):
```markdown
⚠️ **Architecture Conflict Detected**

Request: "Data Center service directly processes camera streams"

**Violation**: Three-tier architecture rule:
- Tier 3 (Data Center) NEVER accesses raw camera streams
- Reference: CLAUDE.md line 234, docs/dev-pattern/10-three-tier-architecture.md

**Architecture-Compliant Alternatives**:

| Option | Approach | Compliance |
|--------|----------|------------|
| A | Edge publishes frames → Kafka → Data Center consumes | ✅ Maintains tier isolation |
| B | Edge publishes processed events → Kafka → Data Center | ✅ Best practice (lower bandwidth) |
| C | Allow direct camera access (requires justification) | ❌ Violates security boundary |

**Recommended**: Option B - Edge processes video, publishes detection events, Data Center consumes events for analytics

**User Choice**: Option B

→ SDD proceeds with Option B, no architecture violation
```

---

## Integration with Domain-Specific Skills

### Integration: backend-payload-api Skill

**Scenario**: User requests new API endpoint, but authentication pattern is unclear

**Workflow**:
1. **Clarification Analyzer**:
   - Detects: "API endpoint" request
   - Questions: Authentication pattern (JWT, API key, none)?
   - Recommends: Based on auth-patterns.md analysis
2. **User Chooses**: JWT with permission-based middleware
3. **backend-payload-api Skill**:
   - Uses clarified auth pattern: `RequireCameraRead` dependency
   - Generates endpoint following exact pattern
   - Includes integration with auth-service client

**Example**:
```markdown
User: "Create endpoint to list user cameras"

Clarification Analyzer:
→ Which authentication? (Recommended: JWT + RequireCameraRead)
User: Yes, JWT

backend-payload-api Skill:
→ Generates endpoint with:
  - Path: /api/v1/cameras
  - Auth: Depends(RequireCameraRead)
  - Service: CameraService integration
  - Response: List[CameraResponseModel]
```

### Integration: service-repository-pattern Skill

**Scenario**: User requests data access layer, but query optimization approach is unclear

**Workflow**:
1. **Clarification Analyzer**:
   - Detects: Data access request with relationships
   - Questions: N+1 prevention strategy? (selectinload vs joinedload)
   - Recommends: Based on relationship type (one-to-many vs many-to-one)
2. **User Confirms**: Use selectinload for one-to-many
3. **service-repository-pattern Skill**:
   - Implements repository with eager loading
   - Uses recommended selectinload strategy
   - Follows base repository pattern

**Example**:
```markdown
User: "Create repository to fetch users with their permissions"

Clarification Analyzer:
→ Relationship type: User → Permissions is one-to-many
→ Recommended: selectinload(User.permissions) for N+1 prevention
User: Confirmed

service-repository-pattern Skill:
→ Generates UserRepository with:
  - Method: get_user_with_permissions(user_id)
  - Eager loading: options(selectinload(User.permissions))
  - Type-safe: Returns UserEntity with loaded permissions
```

### Integration: api-exception-handler Skill

**Scenario**: User requests error handling, but specific error types are unclear

**Workflow**:
1. **Clarification Analyzer**:
   - Detects: Error handling request
   - Questions: Which error categories? (validation, auth, not found, conflict)
   - Recommends: Based on endpoint purpose
2. **User Specifies**: Need validation and not found errors
3. **api-exception-handler Skill**:
   - Generates custom exceptions for specified categories
   - Implements RFC 7807 handlers
   - Registers with FastAPI exception handlers

---

## Cross-Skill Communication Protocol

### Handoff Format

When clarification-analyzer completes, it produces structured output for downstream skills:

**Output Format**:
```json
{
  "original_request": "user's original text",
  "refined_request": "clarified, unambiguous requirements",
  "context": {
    "project_patterns": ["pattern1", "pattern2"],
    "constraints": ["constraint1", "constraint2"],
    "recommendations": {
      "auth_pattern": "JWT with permission-based middleware",
      "data_access": "Repository pattern with selectinload",
      "architecture_tier": "Tier 3 (Data Center)"
    }
  },
  "clarifications": [
    {
      "question": "Which authentication pattern?",
      "answer": "JWT with RBAC",
      "score": 95,
      "rationale": "Matches 23 existing endpoints"
    }
  ],
  "ready_for_downstream_skills": true
}
```

### Skill Invocation Pattern

**From Clarification → SDD**:
```markdown
[Clarification Complete]

**Refined Requirements**:
"Add JWT authentication with permission-based RBAC to dashboard following auth-service/middleware/auth.py:45-89 pattern"

**Project Context**:
- Auth Pattern: JWT + RBAC (95/100 score, exact match)
- Performance SLA: <10ms API response (current: ~8ms)
- Architecture: Tier 3 (Data Center) - user-facing API

**Ready for**: specification-driven-development skill (Phase 1: Specify)

→ Proceed to generate structured specification
```

**From Clarification → Domain Skill**:
```markdown
[Clarification Complete]

**Refined Requirements**:
"Create CameraRepository with eager loading of camera_config using selectinload()"

**Project Context**:
- Pattern: Repository pattern (libs/database/repositories/base.py:22-259)
- N+1 Prevention: selectinload for one-to-many (40/40 pattern match)
- Type Safety: Full type annotations required

**Ready for**: service-repository-pattern skill

→ Proceed to generate repository implementation
```

---

## Multi-Skill Orchestration Example

### End-to-End Feature Implementation

**User Request**: "I want users to see their camera list with live status"

**Step 1: Clarification Analyzer**

```markdown
Analyzing: "camera list with live status"

**Ambiguity 1**: What is "live status"?
Options:
- A: Connection status (online/offline) - 90/100 (simple, matches health check pattern)
- B: Live video feed - 40/100 (complex, high bandwidth, wrong tier)
- C: Last event timestamp - 75/100 (useful, medium complexity)

User chooses: A (connection status)

**Ambiguity 2**: Authentication pattern?
Options:
- A: JWT + RequireCameraRead - 97/100 (exact match, 23 endpoints)
- B: API key - 50/100 (wrong use case)

User chooses: A (JWT)

**Ambiguity 3**: Query optimization?
Options:
- A: Eager load config with selectinload - 85/100 (prevents N+1)
- B: Separate queries - 20/100 (N+1 problem)

User chooses: A (eager loading)

**Refined Request**:
"Create authenticated API endpoint GET /api/v1/cameras that returns user's cameras with connection status (online/offline), using JWT + RequireCameraRead permission, with eager loading of camera_config via selectinload"
```

**Step 2: SDD Specification**

```markdown
[specification-driven-development: Phase 1]

Creating spec.md from refined request...

## User Story 1 - User Views Camera List with Status (P1)

As an authenticated user, I want to see my cameras with their connection status so that I can monitor which cameras are currently operational.

**Acceptance Scenarios**:
1. Given authenticated user, When GET /api/v1/cameras, Then return 200 with camera list
2. Given camera is online, When fetching list, Then status shows "online"
3. Given camera is offline, When fetching list, Then status shows "offline"

[Full spec continues...]
```

**Step 3: SDD Planning**

```markdown
[specification-driven-development: Phase 3]

Creating plan.md with technical decisions...

## Technical Decisions

### API Design
- **Endpoint**: GET /api/v1/cameras
- **Auth**: JWT + RequireCameraRead (following auth-service pattern)
- **Response**: List[CameraStatusModel] with pagination

### Data Access
- **Repository**: CameraRepository.get_user_cameras_with_status(user_id, tenant_id)
- **Optimization**: selectinload(Camera.camera_config) to prevent N+1

### Status Logic
- **Online**: last_heartbeat within 60 seconds
- **Offline**: last_heartbeat > 60 seconds or null

[Full plan continues...]
```

**Step 4: SDD Task Generation**

```markdown
[specification-driven-development: Phase 4]

Creating tasks.md with executable steps...

## Task List

- [ ] T001 [P] [US1] Create CameraStatusModel response schema (DTOs)
- [ ] T002 [US1] Add get_user_cameras_with_status to CameraRepository with selectinload
- [ ] T003 [US1] Create CameraService.get_user_cameras_with_status method
- [ ] T004 [US1] Implement GET /api/v1/cameras endpoint with RequireCameraRead
- [ ] T005 [US1] Write repository tests (>95% coverage)
- [ ] T006 [US1] Write service tests
- [ ] T007 [US1] Write endpoint E2E tests

[Full tasks continue...]
```

**Step 5: Domain Skills Execute Tasks**

```markdown
[service-repository-pattern: T002]
→ Creates CameraRepository method with eager loading

[backend-payload-api: T004]
→ Creates endpoint with JWT auth, service integration

[tdd-unit-testing: T005-T007]
→ Creates comprehensive test suite

[Each task references clarified requirements and patterns]
```

**Result**: Feature implemented correctly on first try, following all established patterns, with no rework needed due to ambiguity.

---

## Integration Best Practices

### DO: Proactive Clarification

✅ **Invoke clarification-analyzer early** when:
- Request is vague or high-level
- Multiple valid interpretations exist
- User is unfamiliar with project patterns
- Request might conflict with architecture

✅ **Example Triggers**:
```python
trigger_clarification = any([
    has_ambiguous_terms(request),  # "fast", "scale", "real-time"
    has_multiple_interpretations(request),
    might_violate_architecture(request),
    lacks_technical_specifics(request)
])
```

### DO: Pass Rich Context

✅ **When handing off to downstream skills**, include:
- Refined requirements (unambiguous)
- Clarification Q&A history
- Recommended patterns with scores
- Project context summary
- Constraints and SLAs

✅ **Example Handoff**:
```markdown
**Refined Requirements**: [Clear, unambiguous statement]

**Clarifications Made**:
1. Auth Pattern: JWT + RBAC (score: 97/100, exact match)
2. Query Strategy: selectinload (score: 85/100, prevents N+1)
3. Tier Placement: Tier 3 Data Center (user-facing API)

**Ready for**: [downstream-skill-name]
```

### DO: Maintain Traceability

✅ **Link clarifications to requirements**:
- SDD spec.md references clarification decisions
- Tasks include rationale from clarification
- Implementation comments reference scoring rationale

✅ **Example**:
```python
# Repository method uses selectinload based on clarification analysis
# Rationale: Prevents N+1 queries (score: 85/100)
# Reference: request-clarification-analyzer decision Q2
def get_user_cameras_with_status(self, user_id: UUID) -> list[Camera]:
    return await self.session.execute(
        select(Camera)
        .options(selectinload(Camera.camera_config))  # N+1 prevention
        .where(Camera.user_id == user_id)
    )
```

### DON'T: Over-Clarify

❌ **Avoid asking questions when**:
- Request is already specific and unambiguous
- Only one valid interpretation exists
- Pattern match is obvious (score >90)
- User has explicitly specified approach

❌ **Example: Don't ask**:
```markdown
User: "Add GET /api/v1/cameras endpoint with JWT auth following the RequireCameraRead pattern"

❌ Don't ask: "Which authentication pattern should we use?"
✅ Instead: Proceed directly (request is explicit and unambiguous)
```

### DON'T: Ask Implementation Details Too Early

❌ **Clarification is for WHAT, not HOW**:
- Focus on requirements, scope, patterns
- Avoid implementation minutiae
- Leave technical details to domain skills

❌ **Example: Don't ask**:
```markdown
❌ Don't: "Should we use async def or def for the endpoint?"
✅ Instead: Let backend-payload-api skill handle async patterns

❌ Don't: "How many spaces should we indent?"
✅ Instead: Formatting is handled by black/ruff, not clarification

❌ Don't: "Which variable name for the user ID?"
✅ Instead: Naming conventions are in coding standards
```

---

## Skill Communication Checklist

When clarification-analyzer hands off to another skill:

- [ ] **Refined requirements**: Clear, unambiguous, actionable
- [ ] **Context included**: Relevant patterns, constraints, SLAs
- [ ] **Recommendations documented**: With scores and rationale
- [ ] **Conflicts resolved**: No architecture violations
- [ ] **Traceability maintained**: Link clarifications to decisions
- [ ] **Ready state confirmed**: Downstream skill can proceed without further clarification

When downstream skill receives handoff:

- [ ] **Validate refined requirements**: Confirm they're actionable
- [ ] **Apply recommended patterns**: Use scored pattern matches
- [ ] **Respect constraints**: Honor architecture and SLA constraints
- [ ] **Reference clarifications**: Include rationale in implementation
- [ ] **Report issues**: If clarifications insufficient, request additional clarification
