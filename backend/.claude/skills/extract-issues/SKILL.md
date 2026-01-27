---
name: extract-issues
description: Extract potential issues from note content with AI confidence tagging
---

# Extract Issues Skill

Extract actionable issues from note canvas content using semantic analysis and confidence scoring.

## Quick Start

Use this skill when:
- User finishes brainstorming in note canvas
- AI detects potential work items in note content
- User explicitly requests issue extraction (`/extract-issues`)

**Example**:
```
User writes in note:
"We need to implement JWT authentication and add rate limiting
to the API. Also fix the login bug where users can't log in with email."

AI extracts:
- Issue 1: "Implement JWT authentication" (RECOMMENDED)
- Issue 2: "Add API rate limiting" (RECOMMENDED)
- Issue 3: "Fix email login bug" (RECOMMENDED - explicit bug mention)
```

## Workflow

1. **Analyze Note Content**
   - Parse note blocks (paragraphs, lists, headings)
   - Identify action items using verb patterns (implement, fix, add, create)
   - Detect explicit issue references ("bug", "feature", "task")

2. **Extract Candidate Issues**
   - For each potential issue:
     - Extract name (concise title, ≤100 chars)
     - Extract description (context from surrounding text)
     - Identify block_id for source linking
     - Detect labels from keywords (backend, frontend, security, etc.)
     - Infer priority from urgency markers (critical, urgent, nice-to-have)

3. **Score Confidence**
   - **RECOMMENDED**: Clear action item with explicit verb and context
     - Example: "Implement user authentication with JWT tokens"
   - **DEFAULT**: Implied action from discussion context
     - Example: "Authentication should use JWT" (implies implementation)
   - **ALTERNATIVE**: Possible interpretation, needs clarification
     - Example: "Maybe we should consider caching?" (tentative)

4. **Return Structured Output**
   - JSON array of issues with confidence tags
   - Preserve source block links
   - Include rationale for each confidence score

## Output Format

```json
{
  "issues": [
    {
      "name": "Implement JWT authentication",
      "description": "Add JWT-based authentication with refresh tokens to replace session cookies",
      "confidence": "RECOMMENDED",
      "source_block_id": "block-abc123",
      "labels": ["backend", "security"],
      "priority": "high",
      "rationale": "Clear implementation task with specific requirements (JWT, refresh tokens)"
    },
    {
      "name": "Add API rate limiting",
      "description": "Implement rate limiting middleware to prevent API abuse",
      "confidence": "RECOMMENDED",
      "source_block_id": "block-def456",
      "labels": ["backend", "infrastructure"],
      "priority": "medium",
      "rationale": "Explicit action item, standard security practice"
    },
    {
      "name": "Fix email login bug",
      "description": "Users cannot log in using email addresses, investigate validation logic",
      "confidence": "RECOMMENDED",
      "source_block_id": "block-ghi789",
      "labels": ["backend", "bug"],
      "priority": "critical",
      "rationale": "Explicit bug mention, blocks user access"
    }
  ],
  "summary": "Extracted 3 issues from note content",
  "total_blocks_analyzed": 8
}
```

## Examples

### Example 1: Feature Brainstorm
**Input**:
```markdown
# New Dashboard Ideas

We should add a real-time activity feed showing recent updates.
Users need better filtering - by project, priority, and assignee.
Dark mode would be nice to have eventually.
```

**Output**:
```json
{
  "issues": [
    {
      "name": "Add real-time activity feed",
      "confidence": "RECOMMENDED",
      "labels": ["frontend", "feature"],
      "priority": "medium",
      "rationale": "Clear feature request with specific requirement (real-time updates)"
    },
    {
      "name": "Implement advanced filtering",
      "confidence": "RECOMMENDED",
      "labels": ["frontend", "feature"],
      "priority": "high",
      "rationale": "User need explicitly stated with specific filters listed"
    },
    {
      "name": "Add dark mode theme",
      "confidence": "DEFAULT",
      "labels": ["frontend", "feature"],
      "priority": "low",
      "rationale": "Mentioned as 'nice to have', lower priority"
    }
  ]
}
```

### Example 2: Bug Report
**Input**:
```markdown
There's a critical bug in the login flow - users can't log in with email.
Investigation shows the regex validation is too strict.
```

**Output**:
```json
{
  "issues": [
    {
      "name": "Fix email login validation bug",
      "confidence": "RECOMMENDED",
      "labels": ["backend", "bug"],
      "priority": "critical",
      "rationale": "Explicit critical bug with root cause identified"
    }
  ]
}
```

### Example 3: Ambiguous Discussion
**Input**:
```markdown
Maybe we should think about caching?
Could potentially improve performance.
Not sure if Redis or in-memory would be better.
```

**Output**:
```json
{
  "issues": [
    {
      "name": "Evaluate caching strategy",
      "confidence": "ALTERNATIVE",
      "labels": ["backend", "performance"],
      "priority": "low",
      "rationale": "Tentative suggestion (maybe, could, not sure), needs discussion"
    }
  ]
}
```

## Integration Points

- **IssueExtractorAgent**: Primary agent implementing this workflow
- **MCP Tools**: Uses `search_related_notes` to find similar issues
- **Approval Flow**: Extracted issues require DEFAULT_REQUIRE_APPROVAL per DD-003
- **Note Linking**: Creates bidirectional links between issues and source blocks

## References

- Design Decision: DD-013 (Note-First Workflow)
- Design Decision: DD-048 (Confidence Tagging)
- Agent: `backend/src/pilot_space/ai/agents/issue_extractor_sdk_agent.py`
