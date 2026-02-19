---
name: review-code
description: Perform a thorough code review on note content, checking correctness, security, performance, and style — auto-executes and writes feedback to note
approval: auto
model: opus
---

# Review Code Skill

Perform a production-grade code review on code blocks in the current note. Uses Opus for deep analysis, checking correctness, security vulnerabilities, performance bottlenecks, and adherence to project patterns. Writes structured feedback directly to the note.

## Quick Start

Use this skill when:
- User requests a code review (`/review-code`)
- Agent detects code blocks that need quality checking
- User asks "review this" or "is this code correct?"

**Example**:
```
User: "Review this FastAPI endpoint I wrote"

AI reviews:
- Security: SQL injection risk in raw query? Missing RLS enforcement?
- Performance: N+1 query in loop? Missing eager loading?
- Correctness: Missing error handling? Wrong HTTP status codes?
- Style: Type hints? Pydantic v2 model? Conventional naming?
```

## Workflow

1. **Collect Code to Review**
   - Read all code blocks from the current note
   - Use `search_note_content` to find referenced dependencies or patterns
   - Use `get_issue` if issue context is in note headers

2. **Analyze Code**
   - **Security**: OWASP Top 10, RLS enforcement, input validation, SQL injection, XSS
   - **Performance**: N+1 queries, missing indexes, blocking I/O in async, connection pooling
   - **Correctness**: Error handling completeness, type safety, edge cases, async/await usage
   - **Architecture**: CQRS-lite compliance, repository pattern, separation of concerns, file size (<700 lines)
   - **Style**: Type hints, docstrings on public APIs, naming conventions

3. **Classify Findings**
   - **CRITICAL**: Security vulnerabilities, data loss risks, production crashes
   - **HIGH**: Performance degradation, logic errors, missing error handling
   - **MEDIUM**: Architecture violations, missing tests, style issues
   - **LOW**: Minor improvements, optional optimizations, documentation gaps

4. **Write Review to Note**
   - Use `write_to_note` to append a `## Code Review` section
   - For each finding: severity badge + location + issue + suggested fix
   - Include a summary scorecard

5. **Auto-Execute**
   - No approval required — review is read-only, no mutations (DD-003 AUTO_EXECUTE)
   - Return `status: completed` with finding counts

## Output Format

```json
{
  "status": "completed",
  "skill": "review-code",
  "note_id": "note-uuid",
  "summary": "Code review complete: 0 CRITICAL, 1 HIGH, 2 MEDIUM, 3 LOW",
  "findings": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3
  },
  "verdict": "REQUEST_CHANGES"
}
```

## Examples

### Example 1: Backend Endpoint Review
**Input**: FastAPI endpoint code block in note

**Output**: Appends to note:
```
## Code Review

**Verdict**: REQUEST_CHANGES | **Score**: 7/10

### [HIGH] Missing workspace_id filter — potential RLS bypass
**Location**: `routers/invitations.py:34`
**Issue**: `repo.list_all()` does not filter by workspace_id. RLS policies at DB level prevent data leakage, but application-layer filtering is required per security architecture.
**Fix**:
\`\`\`python
# Before
results = await repo.list_all()
# After
results = await repo.list_by_workspace(workspace_id)
\`\`\`

### [MEDIUM] No HTTP 404 handling
**Location**: `routers/invitations.py:41`
**Issue**: `repo.get_by_id()` may return `None` but code does not raise HTTPException(404).
**Fix**: Add `if not invitation: raise HTTPException(status_code=404, detail="Invitation not found")`

### [LOW] Missing return type annotation
**Location**: `routers/invitations.py:28`
**Fix**: Add `-> InvitationResponse` to function signature
```

### Example 2: React Component Review
**Input**: React component with state management

**Output**: Flags direct state mutation, missing `observer()` wrapper, missing `key` prop in list render.

## MCP Tools Used

- `search_note_content`: Find code blocks and referenced context in the note
- `get_issue`: Fetch issue requirements if review is issue-linked
- `write_to_note`: Append review findings to the note (read-only review, no code edits)

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/review-code` command (Opus model for depth)
- **SkillExecutor**: No write lock needed — `write_to_note` is append-only to review section
- **Approval Flow**: AUTO_EXECUTE — review feedback is non-destructive (DD-003)

## References

- Design Decision: DD-003 (review is AUTO_EXECUTE — non-destructive annotation)
- Design Decision: DD-086 (Opus for deep analysis tasks)
- Task: T-041
- OWASP Top 10: https://owasp.org/www-project-top-ten/
