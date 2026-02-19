---
name: review-architecture
description: Analyze system architecture described in a note, identify design gaps, scalability concerns, and recommend improvements — auto-executes
approval: auto
model: opus
---

# Review Architecture Skill

Perform a senior architect-level review of system architecture described in a note. Analyzes component design, data flows, scalability patterns, and alignment with project design decisions. Writes structured findings to a PM block for stakeholder review.

## Quick Start

Use this skill when:
- User requests an architecture review (`/review-architecture`)
- Agent detects architecture diagrams or system design in note content
- User asks "is this design good?" or "what are the risks here?"

**Example**:
```
User: "Review the architecture for our new notification system"

AI reviews:
- Component boundaries: Are responsibilities well-separated?
- Scalability: What's the bottleneck at 10k users?
- Data model: Correct relationship cardinality? Index strategy?
- Integration points: External dependencies, circuit breakers?
- Alignment: Does this follow DD-001 (async-first) and DD-064 (CQRS-lite)?
```

## Workflow

1. **Parse Architecture Description**
   - Read all content from note (diagrams, prose, component lists, data models)
   - Use `search_notes` to find related architecture decisions or existing components
   - Use `get_project` to understand project scope and tech stack constraints

2. **Analyze Architecture Dimensions**
   - **Component Design**: SRP violations, God classes, missing abstractions
   - **Data Model**: Normalization, relationship cardinality, index coverage, N+1 risks
   - **Scalability**: Bottlenecks, stateful components, horizontal scaling barriers
   - **Resilience**: Single points of failure, missing circuit breakers, timeout strategy
   - **Security**: Auth boundaries, data isolation, RLS enforcement plan
   - **Design Alignment**: DD-001 (async-first), DD-003 (approval), DD-064 (CQRS), DD-086 (centralized agent)

3. **Classify Findings**
   - **BLOCKER**: Fundamental design flaw — must fix before implementation
   - **HIGH**: Scalability or security risk — fix in sprint before ship
   - **MEDIUM**: Technical debt — plan for next sprint
   - **LOW**: Optional improvement — backlog item

4. **Write Findings + PM Block**
   - Use `write_to_note` to append `## Architecture Review` section
   - Use `create_pm_block` to generate an ADR-lite block summarizing the recommendation
   - Include: overall health score, risk matrix, top 3 recommendations

5. **Auto-Execute**
   - Return `status: completed` — review is read-only (DD-003)

## Output Format

```json
{
  "status": "completed",
  "skill": "review-architecture",
  "note_id": "note-uuid",
  "summary": "Architecture review complete: 0 BLOCKERS, 2 HIGH, 3 MEDIUM",
  "findings": {
    "blockers": 0,
    "high": 2,
    "medium": 3,
    "low": 1
  },
  "health_score": 72,
  "top_recommendation": "Add circuit breaker to notification dispatch — single point of failure at Slack API",
  "verdict": "REQUEST_CHANGES"
}
```

## Examples

### Example 1: Microservice Design Review
**Input**: Architecture note describing a notification service with direct DB calls

**Output**: Appends to note:
```
## Architecture Review

**Health Score**: 72/100 | **Verdict**: REQUEST_CHANGES

### [HIGH] Notification service makes direct DB calls — bypasses repository layer
**Component**: NotificationService → DB
**Issue**: Violates clean architecture. Service should use INotificationRepository. Direct SQLAlchemy calls in service layer create untestable coupling.
**Recommendation**: Introduce `INotificationRepository` protocol with `PostgresNotificationRepository` impl. Wire via DI container (DD-064).

### [HIGH] No circuit breaker on Slack API dispatch
**Component**: NotificationDispatcher → Slack API
**Issue**: Slack API outage will cause unbounded request queuing and potential OOM.
**Recommendation**: Wrap in `ResilientExecutor` with circuit breaker (3 failures → OPEN, 30s recovery). Use Supabase Queue for retry on failure.

### [MEDIUM] Missing idempotency key on notification dispatch
**Issue**: Retry on transient failure will send duplicate Slack messages.
**Recommendation**: Add `idempotency_key = sha256(user_id + event_type + event_id)` to dispatch payload.
```

### Example 2: Data Model Review
**Input**: Proposed schema with junction table for many-to-many relationship

**Output**: Flags missing composite unique constraint, recommends partial index for active records.

## MCP Tools Used

- `search_notes`: Find related architecture decisions and existing component patterns
- `get_project`: Fetch project context for scope and tech stack constraints
- `write_to_note`: Append architecture review findings to the note
- `create_pm_block`: Generate ADR-lite decision record for key recommendations

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/review-architecture` command (Opus model)
- **SkillExecutor**: Uses `note_write_lock` mutex only for PM block creation (C-3)
- **Approval Flow**: AUTO_EXECUTE — architecture review is advisory, non-destructive (DD-003)

## References

- Design Decision: DD-003 (review is AUTO_EXECUTE)
- Design Decision: DD-086 (Opus for deep analysis)
- Design Decisions: DD-001, DD-003, DD-064, DD-086 — alignment targets
- Task: T-042
