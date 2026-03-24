---
name: decompose-tasks
description: Break down issue into subtasks with dependencies using AI planning
feature_module: projects
---

# Decompose Tasks Skill

Automatically break down complex issues into actionable subtasks with dependencies and estimates.

## Quick Start

Use this skill when:
- Large feature needs breakdown into subtasks
- User requests task decomposition (`/decompose-tasks`)
- Issue is too complex for single assignee

**Example**:
```
Issue: "Implement user authentication system"

AI decomposes into:
1. Design database schema for users/sessions (2 days, no dependencies)
2. Implement JWT token generation (1 day, depends on #1)
3. Create login/logout API endpoints (2 days, depends on #2)
4. Add frontend login form (1 day, depends on #3)
5. Write integration tests (1 day, depends on #3, #4)
```

## Workflow

1. **Analyze Issue Scope**
   - Parse description for distinct components
   - Identify technical layers (DB, API, Frontend, Tests)
   - Detect implied tasks from acceptance criteria

2. **Generate Subtask Graph**
   - **Decomposition Strategy**:
     - Backend features: DB schema → API → Tests
     - Frontend features: Component → State → Styling → Tests
     - Full-stack: Backend → Frontend → Integration
   - Identify parallel vs sequential tasks
   - Build dependency graph (DAG)

3. **Estimate Complexity**
   - **Small** (0.5-1 day): Simple implementation, single file
   - **Medium** (1-3 days): Multiple files, standard patterns
   - **Large** (3-5 days): Cross-cutting changes, new architecture

4. **Tag Confidence**
   - **RECOMMENDED**: Standard decomposition for known patterns
   - **DEFAULT**: General breakdown, may need refinement
   - **ALTERNATIVE**: Multiple valid approaches, team choice

## Output Format

```json
{
  "subtasks": [
    {
      "order": 1,
      "name": "Design user database schema",
      "description": "Create users, sessions, and refresh_tokens tables with proper indexes",
      "confidence": "RECOMMENDED",
      "estimated_days": 2,
      "labels": ["backend", "database"],
      "dependencies": [],
      "acceptance_criteria": [
        "Schema supports email and OAuth login",
        "Indexes on email and session_token fields",
        "Migration script tested"
      ],
      "code_references": [
        {
          "file": "backend/src/pilot_space/infrastructure/database/models/user.py",
          "lines": "1-50",
          "description": "Existing User model to extend",
          "badge": "Model"
        },
        {
          "file": "backend/alembic/versions/",
          "description": "Migration directory for new schema",
          "badge": "Migration"
        }
      ],
      "ai_prompt": "Create database schema for user sessions with proper indexes.\n\n## Context\nIssue: AUTH-42 - Implement user authentication system\nAdd support for both email and OAuth login with session management.\n\n## Requirements\n- Create users, sessions, and refresh_tokens tables\n- Add indexes on email and session_token fields\n- Write migration script for schema changes\n\n## Acceptance Criteria\n- [x] Schema supports email and OAuth login\n- [x] Indexes on email and session_token fields\n- [x] Migration script tested\n\n## Files to Reference\n- `backend/src/pilot_space/infrastructure/database/models/user.py` (lines 1-50) - Existing User model to extend\n- `backend/alembic/versions/` - Migration directory for new schema\n\n## Technical Constraints\n- Use SQLAlchemy 2.0 async\n- Follow repository pattern\n- Ensure RLS policies for multi-tenant isolation"
    },
    {
      "order": 2,
      "name": "Implement JWT token service",
      "description": "Create service for generating and validating JWT access/refresh tokens",
      "confidence": "RECOMMENDED",
      "estimated_days": 1,
      "labels": ["backend", "security"],
      "dependencies": [1],
      "acceptance_criteria": [
        "Access tokens expire after 15 minutes",
        "Refresh tokens stored in database",
        "Token validation handles expired tokens"
      ]
    },
    {
      "order": 3,
      "name": "Create login/logout API endpoints",
      "description": "POST /auth/login and POST /auth/logout endpoints with proper error handling",
      "confidence": "RECOMMENDED",
      "estimated_days": 2,
      "labels": ["backend", "api"],
      "dependencies": [2],
      "acceptance_criteria": [
        "Login returns access and refresh tokens",
        "Logout invalidates refresh token",
        "Rate limiting applied (5 attempts/minute)"
      ]
    },
    {
      "order": 4,
      "name": "Build login form component",
      "description": "React login form with email/password validation and error display",
      "confidence": "RECOMMENDED",
      "estimated_days": 1,
      "labels": ["frontend", "react"],
      "dependencies": [3],
      "can_parallel_with": [],
      "acceptance_criteria": [
        "Form validates email format client-side",
        "Displays backend error messages",
        "Redirects to dashboard on success"
      ]
    },
    {
      "order": 5,
      "name": "Write authentication integration tests",
      "description": "End-to-end tests for full login/logout flow",
      "confidence": "RECOMMENDED",
      "estimated_days": 1,
      "labels": ["testing"],
      "dependencies": [3, 4],
      "acceptance_criteria": [
        "Tests cover happy path and error cases",
        "Tests verify token persistence",
        "Tests check session expiration"
      ]
    }
  ],
  "summary": "Decomposed into 5 subtasks, estimated 7 days total",
  "critical_path": [1, 2, 3, 4],
  "parallel_opportunities": ["#4 and #5 can start after #3"]
}
```

## Examples

### Example 1: Backend Feature
**Input**:
```json
{
  "issue": {
    "title": "Add rate limiting to API",
    "description": "Implement rate limiting middleware to prevent API abuse"
  }
}
```

**Output**:
```json
{
  "subtasks": [
    {
      "order": 1,
      "name": "Research rate limiting libraries",
      "estimated_days": 0.5,
      "confidence": "RECOMMENDED"
    },
    {
      "order": 2,
      "name": "Implement rate limiting middleware",
      "estimated_days": 1,
      "dependencies": [1]
    },
    {
      "order": 3,
      "name": "Add configuration for rate limits",
      "estimated_days": 0.5,
      "dependencies": [2]
    },
    {
      "order": 4,
      "name": "Write rate limiting tests",
      "estimated_days": 1,
      "dependencies": [2]
    }
  ],
  "total_estimated_days": 3
}
```

### Example 2: Frontend Feature
**Input**:
```json
{
  "issue": {
    "title": "Create dashboard analytics widget",
    "description": "Display user activity metrics with charts"
  }
}
```

**Output**:
```json
{
  "subtasks": [
    {
      "order": 1,
      "name": "Design widget component structure",
      "estimated_days": 0.5
    },
    {
      "order": 2,
      "name": "Implement data fetching with TanStack Query",
      "estimated_days": 1,
      "dependencies": [1]
    },
    {
      "order": 3,
      "name": "Add chart visualization with Recharts",
      "estimated_days": 2,
      "dependencies": [2]
    },
    {
      "order": 4,
      "name": "Style widget with TailwindCSS",
      "estimated_days": 1,
      "dependencies": [3],
      "can_parallel_with": [5]
    },
    {
      "order": 5,
      "name": "Write component tests",
      "estimated_days": 1,
      "dependencies": [3]
    }
  ]
}
```

### Example 3: Complex Full-Stack Feature
**Input**:
```json
{
  "issue": {
    "title": "Implement real-time notifications",
    "description": "Add WebSocket support for live activity notifications"
  }
}
```

**Output**:
```json
{
  "subtasks": [
    {
      "order": 1,
      "name": "Design notification data model",
      "estimated_days": 1,
      "labels": ["backend", "database"]
    },
    {
      "order": 2,
      "name": "Set up Supabase Realtime subscriptions",
      "estimated_days": 2,
      "dependencies": [1],
      "labels": ["backend", "infrastructure"]
    },
    {
      "order": 3,
      "name": "Create notification MobX store",
      "estimated_days": 1,
      "dependencies": [1],
      "labels": ["frontend", "state"]
    },
    {
      "order": 4,
      "name": "Build notification UI component",
      "estimated_days": 2,
      "dependencies": [3],
      "labels": ["frontend", "react"]
    },
    {
      "order": 5,
      "name": "Integrate Realtime with MobX",
      "estimated_days": 1,
      "dependencies": [2, 3],
      "labels": ["frontend"]
    },
    {
      "order": 6,
      "name": "Add notification sound/desktop alerts",
      "estimated_days": 1,
      "dependencies": [4],
      "labels": ["frontend"]
    },
    {
      "order": 7,
      "name": "Write E2E tests for notifications",
      "estimated_days": 2,
      "dependencies": [5, 6],
      "labels": ["testing"]
    }
  ],
  "total_estimated_days": 10,
  "critical_path": [1, 2, 5, 6],
  "parallel_opportunities": ["#3 and #2 can run in parallel"]
}
```

## Integration Points

- **PilotSpaceAgent**: Orchestrator routes to this skill via intent detection or `/decompose-tasks` command
- **MCP Tools**: Uses `search_codebase` to find similar implementations
- **Approval Flow**: Task creation requires DEFAULT_REQUIRE_APPROVAL per DD-003
- **Dependency Graph**: Validates DAG structure (no cycles) via `DecompositionResult` model validator

## References

- Design Decision: DD-048 (Confidence Tagging)
- Design Decision: DD-003 (Approval for subtask creation)
- Schema: `backend/src/pilot_space/ai/sdk/output_schemas.py`
