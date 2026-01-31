---
name: recommend-assignee
description: Recommend assignee based on expertise matching and workload balance
---

# Recommend Assignee Skill

Suggest optimal assignee for issue using expertise matching, past work analysis, and workload balancing.

## Quick Start

Use this skill when:
- New issue created without assignee
- User requests assignee recommendation (`/recommend-assignee`)
- Issue reassignment needed due to skill mismatch

**Example**:
```
Issue: "Implement GraphQL API for user queries"

AI recommends:
- alice@example.com (RECOMMENDED)
  - Expertise: GraphQL, API design (15 prior issues)
  - Workload: 3 open issues (below team average of 5)
  - Recent: Completed "GraphQL schema design" 2 weeks ago
```

## Workflow

1. **Analyze Issue Requirements**
   - Extract technical keywords from title/description
   - Identify domain (backend, frontend, infra, design)
   - Classify complexity (low, medium, high)

2. **Build Team Expertise Profile**
   - For each workspace member:
     - Past issues worked on (completed, in-progress)
     - Labels/technologies from those issues
     - Success rate (completion time, quality)
   - Load expertise data from `user_expertise` table

3. **Score Candidates**
   - **Expertise Match** (0-100): Keyword overlap with past work
   - **Workload** (0-100): Inverse of current open issues
   - **Recency** (0-100): Recently worked on similar issues
   - **Domain Familiarity** (0-100): Experience in issue domain
   - Weighted score: Expertise (40%) + Workload (30%) + Recency (20%) + Domain (10%)

4. **Apply Business Rules**
   - Exclude members on PTO or unavailable
   - Consider role permissions (e.g., only admins for security issues)
   - Respect team preferences (preferred domains)

5. **Tag Confidence**
   - **RECOMMENDED**: High score (>80), clear expertise match
   - **DEFAULT**: Medium score (50-80), general fit
   - **ALTERNATIVE**: Multiple candidates with similar scores

## Output Format

```json
{
  "recommendations": [
    {
      "user_id": "user-abc123",
      "email": "alice@example.com",
      "name": "Alice Johnson",
      "confidence": "RECOMMENDED",
      "score": 92,
      "rationale": "Strong GraphQL expertise (15 prior issues), below workload average",
      "expertise_match": {
        "graphql": 95,
        "api_design": 88,
        "python": 82
      },
      "workload": {
        "open_issues": 3,
        "team_average": 5
      },
      "recent_work": [
        {"title": "GraphQL schema design", "completed": "2024-01-10"}
      ]
    },
    {
      "user_id": "user-def456",
      "email": "bob@example.com",
      "name": "Bob Smith",
      "confidence": "DEFAULT",
      "score": 68,
      "rationale": "API experience but no GraphQL history, workload is high",
      "expertise_match": {
        "api_design": 75,
        "python": 88
      },
      "workload": {
        "open_issues": 7,
        "team_average": 5
      }
    }
  ],
  "summary": "2 candidates found, 1 RECOMMENDED"
}
```

## Examples

### Example 1: Backend Issue
**Input**:
```json
{
  "issue": {
    "title": "Optimize database query performance",
    "description": "User list query takes 5+ seconds with 10k users",
    "labels": ["backend", "database", "performance"]
  }
}
```

**Output**:
```json
{
  "recommendations": [
    {
      "email": "charlie@example.com",
      "confidence": "RECOMMENDED",
      "score": 94,
      "rationale": "Database expert (PostgreSQL indexing), completed 8 perf issues",
      "expertise_match": {"postgresql": 98, "performance": 92, "backend": 85}
    }
  ]
}
```

### Example 2: Frontend Issue
**Input**:
```json
{
  "issue": {
    "title": "Implement responsive dashboard layout",
    "labels": ["frontend", "ui", "react"]
  }
}
```

**Output**:
```json
{
  "recommendations": [
    {
      "email": "diana@example.com",
      "confidence": "RECOMMENDED",
      "score": 88,
      "rationale": "Frontend specialist, recently completed similar dashboard work",
      "expertise_match": {"react": 95, "ui": 90, "css": 85},
      "recent_work": [
        {"title": "Dashboard redesign", "completed": "2024-01-05"}
      ]
    },
    {
      "email": "evan@example.com",
      "confidence": "ALTERNATIVE",
      "score": 86,
      "rationale": "Similar expertise, slightly higher workload",
      "expertise_match": {"react": 92, "ui": 88},
      "workload": {"open_issues": 6, "team_average": 5}
    }
  ]
}
```

### Example 3: Security Issue
**Input**:
```json
{
  "issue": {
    "title": "Fix XSS vulnerability in comment form",
    "labels": ["security", "bug", "frontend"]
  }
}
```

**Output**:
```json
{
  "recommendations": [
    {
      "email": "frank@example.com",
      "confidence": "RECOMMENDED",
      "score": 96,
      "rationale": "Security specialist with XSS remediation experience",
      "expertise_match": {"security": 98, "xss": 95, "frontend": 80},
      "certifications": ["OWASP Top 10 Training"]
    }
  ]
}
```

## Integration Points

- **AssigneeRecommenderAgent**: Primary agent implementing this workflow
- **MCP Tools**: Uses `get_workspace_members`, `search_issues`
- **Data Sources**: `user_expertise` table (updated on issue completion)
- **Approval Flow**: Recommendations are AUTO_EXECUTE (suggestions only)

## References

- Design Decision: DD-048 (Confidence Tagging)
- Agent: `backend/src/pilot_space/ai/agents/assignee_recommender_agent_sdk.py`
- Database: `user_expertise` table schema
