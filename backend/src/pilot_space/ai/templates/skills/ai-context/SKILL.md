---
name: ai-context
description: Generate comprehensive AI context for issue implementation with task breakdown and Claude Code prompts
---

# AI Context Skill

Generate comprehensive developer context for an issue: summary, complexity analysis, implementation tasks, related content, and a ready-to-use Claude Code prompt.

## Quick Start

Use this skill when:
- Developer opens "AI Context" tab on an issue detail page
- User explicitly requests context generation (`/ai-context`)
- System needs structured implementation guidance for an issue

**Example**:
```
Issue: "PILOT-42: Implement real-time notifications"

AI generates:
- Summary: Architecture overview + scope analysis
- Complexity: high (cross-cutting: backend + frontend + infra)
- Tasks: 6 ordered subtasks with estimates and dependencies
- Claude Code Prompt: Ready-to-use implementation guide
```

## Workflow

1. **Analyze the Issue**
   - Read the issue title, description, and metadata
   - Understand scope, complexity, and technical requirements
   - Identify the technical layers involved (DB, API, Frontend, Tests)

2. **Identify Related Content**
   - Use `search_issues` to find related or similar issues in the workspace
   - Use `search_notes` to find relevant notes and documentation
   - Check for linked PRs, commits, and code references

3. **Assess Complexity**
   - **low**: Single layer, straightforward implementation, 1-2 files
   - **medium**: Multiple files, standard patterns, some cross-cutting
   - **high**: Cross-layer changes, new architecture, significant testing

4. **Generate Implementation Tasks**
   - Break down into ordered, actionable subtasks
   - Identify dependencies between tasks (DAG structure)
   - Estimate effort per task: S (~1h), M (~2-3h), L (~4-6h), XL (~8h+)
   - Follow decomposition patterns:
     - Backend: DB schema → Repository → Service → API → Tests
     - Frontend: Component → State → Styling → Tests
     - Full-stack: Backend → Frontend → Integration tests

5. **Create Claude Code Prompt**
   - Summarize context for AI-assisted development
   - List relevant code files and references
   - Include implementation instructions and constraints
   - Reference existing patterns and conventions

6. **Return Structured Output**
   - JSON response matching the output format below
   - All fields populated with actionable content

## Output Format

```json
{
  "summary": "2-3 sentence summary of the issue and its implementation context",
  "analysis": "Detailed technical analysis including architecture considerations, affected components, and integration points",
  "complexity": "low|medium|high",
  "estimated_effort": "S|M|L|XL",
  "key_considerations": [
    "Important technical point or constraint",
    "Security or performance consideration",
    "Integration requirement"
  ],
  "suggested_approach": "Recommended implementation approach with rationale",
  "potential_blockers": [
    "Possible blocker or risk",
    "Dependency that must be resolved first"
  ],
  "tasks": [
    {
      "id": "task-1",
      "description": "Clear, actionable task description",
      "dependencies": [],
      "estimated_effort": "S|M|L",
      "order": 1
    },
    {
      "id": "task-2",
      "description": "Second task with dependency on first",
      "dependencies": ["task-1"],
      "estimated_effort": "M",
      "order": 2
    }
  ],
  "claude_code_sections": {
    "context": "Brief context for Claude Code session",
    "code_references": ["src/path/to/relevant/file.py", "src/another/file.ts"],
    "instructions": "Step-by-step implementation instructions",
    "constraints": "Code quality requirements, patterns to follow, testing requirements"
  }
}
```

## Guidelines

- Be specific and actionable in recommendations
- Consider edge cases and error handling requirements
- Think about testing requirements for each task
- Account for code quality and maintainability
- Reference existing patterns in the codebase when available
- Keep tasks small enough to be completed in a few hours
- Include file paths and line references where possible
- Highlight confidence level where appropriate

## Examples

### Example 1: Backend Feature

**Input**: Issue "Add rate limiting to API endpoints"

**Output**:
```json
{
  "summary": "Implement rate limiting middleware for all API endpoints to prevent abuse and ensure fair usage across workspace members.",
  "analysis": "Requires FastAPI middleware integration with Redis-backed counters. Should support per-user and per-workspace limits with configurable thresholds.",
  "complexity": "medium",
  "estimated_effort": "M",
  "key_considerations": [
    "Use Redis for distributed rate limit counters",
    "Support both per-user and per-workspace limits",
    "Return RFC 7807 error responses on limit exceeded"
  ],
  "suggested_approach": "Implement as FastAPI middleware using Redis INCR with TTL for sliding window counters",
  "potential_blockers": [
    "Redis connection must be available",
    "Need to define rate limit tiers per endpoint"
  ],
  "tasks": [
    {
      "id": "task-1",
      "description": "Create RateLimiter class with Redis backend",
      "dependencies": [],
      "estimated_effort": "M",
      "order": 1
    },
    {
      "id": "task-2",
      "description": "Integrate as FastAPI middleware with per-route config",
      "dependencies": ["task-1"],
      "estimated_effort": "M",
      "order": 2
    },
    {
      "id": "task-3",
      "description": "Add rate limit headers to responses (X-RateLimit-*)",
      "dependencies": ["task-2"],
      "estimated_effort": "S",
      "order": 3
    },
    {
      "id": "task-4",
      "description": "Write unit and integration tests",
      "dependencies": ["task-2"],
      "estimated_effort": "M",
      "order": 4
    }
  ],
  "claude_code_sections": {
    "context": "Adding rate limiting middleware to FastAPI backend",
    "code_references": ["backend/src/pilot_space/api/v1/middleware/"],
    "instructions": "Create Redis-backed rate limiter with sliding window, integrate as middleware",
    "constraints": "Follow existing middleware patterns, use RFC 7807 errors, >80% test coverage"
  }
}
```

### Example 2: Full-Stack Feature

**Input**: Issue "Implement issue comment threads"

**Output**:
```json
{
  "summary": "Add threaded comments to issue detail page, allowing team discussion with nested replies, mentions, and real-time updates.",
  "analysis": "Full-stack feature requiring new DB model, API endpoints, MobX store, and React components. Must integrate with existing issue detail layout.",
  "complexity": "high",
  "estimated_effort": "L",
  "tasks": [
    {
      "id": "task-1",
      "description": "Create Comment SQLAlchemy model with self-referential parent_id",
      "dependencies": [],
      "estimated_effort": "S",
      "order": 1
    },
    {
      "id": "task-2",
      "description": "Create CommentRepository with nested query support",
      "dependencies": ["task-1"],
      "estimated_effort": "M",
      "order": 2
    },
    {
      "id": "task-3",
      "description": "Create CommentService with CQRS-lite pattern",
      "dependencies": ["task-2"],
      "estimated_effort": "M",
      "order": 3
    },
    {
      "id": "task-4",
      "description": "Create CRUD API endpoints for comments",
      "dependencies": ["task-3"],
      "estimated_effort": "M",
      "order": 4
    },
    {
      "id": "task-5",
      "description": "Build CommentThread React component with nested rendering",
      "dependencies": ["task-4"],
      "estimated_effort": "L",
      "order": 5
    },
    {
      "id": "task-6",
      "description": "Write backend + frontend tests",
      "dependencies": ["task-4", "task-5"],
      "estimated_effort": "M",
      "order": 6
    }
  ]
}
```

## Integration Points

- **MCP Tools**: Uses `search_issues`, `search_notes`, `get_issue` from PilotSpaceAgent's tool servers
- **Approval Flow**: Context generation is non-destructive (auto-execute per DD-003)
- **Provider**: Runs through PilotSpaceAgent orchestrator (Claude Sonnet for cost efficiency)
- **Output**: Parsed by `parse_context_response()` in `ai/prompts/ai_context.py`

## References

- Design Decision: DD-086 (Centralized Agent Architecture)
- Design Decision: DD-087 (Filesystem Skill System)
- Prompts: `backend/src/pilot_space/ai/prompts/ai_context.py`
- Service: `backend/src/pilot_space/application/services/ai_context/`
