---
name: find-duplicates
description: Find similar/duplicate issues using semantic search with pgvector
---

# Find Duplicates Skill

Detect potential duplicate issues using semantic similarity search with pgvector embeddings.

## Quick Start

Use this skill when:
- New issue being created (automatic check)
- User suspects duplicate exists (`/find-duplicates`)
- Cleaning up issue backlog

**Example**:
```
New issue: "Users cannot log in with email addresses"

AI finds duplicates:
- "Login fails for email users" (similarity: 0.92, RECOMMENDED duplicate)
- "Email authentication broken" (similarity: 0.88, RECOMMENDED duplicate)
- "User auth not working" (similarity: 0.65, ALTERNATIVE - may be related)
```

## Workflow

1. **Generate Embedding**
   - Combine issue title + description
   - Generate embedding using OpenAI text-embedding-3-large (3072 dims)
   - Store in `embeddings` column (pgvector)

2. **Semantic Search**
   - Query pgvector for similar issues using cosine similarity
   - Filter by project_id (same project)
   - Exclude closed/archived issues (optional)
   - Return top 10 matches

3. **Score Similarity**
   - **RECOMMENDED duplicate** (>0.85): Very high semantic overlap
   - **DEFAULT duplicate** (0.70-0.85): Likely duplicate, needs review
   - **ALTERNATIVE related** (0.60-0.70): Possibly related, not duplicate

4. **Provide Context**
   - Include issue status (open, in_progress, closed)
   - Show creation date (older = likely original)
   - Link to issue for review

## Output Format

```json
{
  "duplicates": [
    {
      "issue_id": "issue-abc123",
      "title": "Login fails for email users",
      "similarity": 0.92,
      "confidence": "RECOMMENDED",
      "status": "open",
      "created_at": "2024-01-15T10:00:00Z",
      "rationale": "Very high semantic similarity (0.92), same symptoms described",
      "url": "/issues/issue-abc123"
    },
    {
      "issue_id": "issue-def456",
      "title": "Email authentication broken",
      "similarity": 0.88,
      "confidence": "RECOMMENDED",
      "status": "in_progress",
      "created_at": "2024-01-20T14:30:00Z",
      "rationale": "High similarity, currently being worked on",
      "url": "/issues/issue-def456"
    },
    {
      "issue_id": "issue-ghi789",
      "title": "User auth not working",
      "similarity": 0.65,
      "confidence": "ALTERNATIVE",
      "status": "closed",
      "created_at": "2023-12-10T09:15:00Z",
      "rationale": "Moderate similarity, may be related but different root cause",
      "url": "/issues/issue-ghi789"
    }
  ],
  "summary": "Found 3 potential duplicates (2 RECOMMENDED)",
  "suggestion": "Review issue-abc123 before creating new issue"
}
```

## Examples

### Example 1: Clear Duplicate
**Input**:
```json
{
  "title": "Fix login error for email users",
  "description": "When users try to log in with email, they get validation error"
}
```

**Output**:
```json
{
  "duplicates": [
    {
      "issue_id": "issue-123",
      "title": "Login fails for email addresses",
      "similarity": 0.94,
      "confidence": "RECOMMENDED",
      "status": "open",
      "rationale": "Nearly identical issue, same email validation problem",
      "suggestion": "Close as duplicate of issue-123"
    }
  ],
  "summary": "Found 1 RECOMMENDED duplicate",
  "action": "BLOCK_CREATION"
}
```

### Example 2: Related but Not Duplicate
**Input**:
```json
{
  "title": "Add OAuth login support",
  "description": "Users want to log in with Google/GitHub"
}
```

**Output**:
```json
{
  "duplicates": [
    {
      "issue_id": "issue-456",
      "title": "Implement social login",
      "similarity": 0.78,
      "confidence": "DEFAULT",
      "status": "closed",
      "rationale": "Similar goal (social login) but was for Facebook only",
      "suggestion": "Reference issue-456 for implementation pattern"
    }
  ],
  "summary": "Found 1 related issue (not duplicate)",
  "action": "WARN_USER"
}
```

### Example 3: No Duplicates
**Input**:
```json
{
  "title": "Implement real-time notifications",
  "description": "Add WebSocket support for live updates"
}
```

**Output**:
```json
{
  "duplicates": [],
  "summary": "No duplicates found",
  "action": "ALLOW_CREATION"
}
```

## Similarity Thresholds

| Similarity Score | Confidence | Action | Interpretation |
|------------------|------------|--------|----------------|
| 0.90 - 1.00 | RECOMMENDED | Block creation, suggest duplicate | Nearly identical |
| 0.85 - 0.90 | RECOMMENDED | Warn user, allow override | Very similar |
| 0.70 - 0.85 | DEFAULT | Show for reference | Likely related |
| 0.60 - 0.70 | ALTERNATIVE | Show as context | Possibly related |
| < 0.60 | - | Don't show | Not related |

## Technical Details

### Embedding Generation
```python
import openai

# Generate embedding
embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input=f"{issue.title}\n\n{issue.description}",
    dimensions=3072,
)

# Store in database
issue.embedding = embedding.data[0].embedding
```

### Similarity Search
```sql
-- pgvector cosine similarity search
SELECT
    id,
    title,
    description,
    status,
    created_at,
    1 - (embedding <=> :query_embedding) AS similarity
FROM issues
WHERE
    project_id = :project_id
    AND status != 'archived'
    AND id != :excluding_issue_id
ORDER BY embedding <=> :query_embedding
LIMIT 10;
```

## Integration Points

- **DuplicateDetectorAgent**: Primary agent implementing this workflow
- **MCP Tools**: Uses `semantic_search` tool with pgvector
- **Embeddings**: OpenAI text-embedding-3-large (3072 dimensions)
- **Approval Flow**: Duplicate detection is AUTO_EXECUTE (warning only)

## References

- Design Decision: DD-048 (Confidence Tagging)
- Design Decision: DD-070 (Embedding Configuration)
- Agent: `backend/src/pilot_space/ai/agents/duplicate_detector_agent_sdk.py`
- Database: `issues.embedding` column (pgvector)
