---
name: improve-writing
description: Improve writing clarity, conciseness, and style for technical documentation
---

# Improve Writing Skill

Enhance technical writing clarity, conciseness, and readability while preserving technical accuracy.

## Quick Start

Use this skill when:
- Drafting issue descriptions, documentation, or notes
- User requests writing improvement (`/improve-writing`)
- AI detects unclear or verbose text

**Example**:
```
Original: "The thing is that when users are trying to log in to the system,
they sometimes get errors and it doesn't work properly."

Improved: "Users encounter login errors intermittently. Root cause unknown."

Confidence: RECOMMENDED
Changes: Removed filler words, made specific, added action item
```

## Workflow

1. **Analyze Text**
   - Identify issues:
     - **Clarity**: Vague terms ("thing", "sometimes", "properly")
     - **Conciseness**: Filler words ("the thing is", "trying to")
     - **Structure**: Long sentences, lack of paragraphs
     - **Technical accuracy**: Imprecise terminology

2. **Apply Improvements**
   - **Clarity**:
     - Replace vague terms with specifics
     - Use active voice over passive
     - Define acronyms on first use
   - **Conciseness**:
     - Remove filler words and redundancy
     - Shorten long sentences (max 25 words)
     - Use bullet points for lists
   - **Structure**:
     - Add headers for sections
     - Break into digestible paragraphs (3-4 sentences)
     - Use consistent formatting

3. **Preserve Technical Content**
   - Keep all technical terms and specifics
   - Maintain code examples verbatim
   - Don't alter user intent or meaning

4. **Tag Confidence**
   - **RECOMMENDED**: Clear improvement, no ambiguity
   - **DEFAULT**: General enhancement, maintains meaning
   - **ALTERNATIVE**: Multiple valid approaches, style preference

## Output Format

```json
{
  "original": "Original text...",
  "improved": "Improved text...",
  "confidence": "RECOMMENDED",
  "changes": [
    {"type": "clarity", "description": "Replaced 'thing' with 'authentication module'"},
    {"type": "conciseness", "description": "Removed filler phrase 'the thing is that'"},
    {"type": "structure", "description": "Split into two sentences for readability"}
  ],
  "readability_score": {
    "original": 45,
    "improved": 68,
    "metric": "Flesch Reading Ease"
  },
  "suggestions": [
    "Consider adding code example for login flow",
    "Specify browser/environment for reproducibility"
  ]
}
```

## Examples

### Example 1: Issue Description
**Input**:
```
There's this problem where the API is super slow when we have lots of users
trying to access the database at the same time and it causes timeouts and
stuff which is really bad for performance.
```

**Output**:
```json
{
  "improved": "API response times exceed 5 seconds under high load (100+ concurrent users), causing database connection timeouts. This degrades user experience and triggers rate limiting.\n\nRoot cause: N+1 query pattern in user list endpoint.\n\nAcceptance criteria:\n- Response time < 500ms at 100 concurrent users\n- No database connection timeouts\n- Implement query result caching",
  "confidence": "RECOMMENDED",
  "changes": [
    {"type": "clarity", "description": "Specified exact metrics (5 seconds, 100 users)"},
    {"type": "structure", "description": "Added sections for root cause and acceptance criteria"},
    {"type": "technical", "description": "Identified specific issue (N+1 queries)"}
  ]
}
```

### Example 2: Documentation
**Input**:
```
To set up the project, first you need to install Node.js and then you should
run npm install and after that you can start the development server with npm run dev.
```

**Output**:
```json
{
  "improved": "## Setup\n\nPrerequisites:\n- Node.js 20+\n- pnpm 9+\n\nInstallation:\n```bash\npnpm install\npnpm dev\n```\n\nThe development server will start at http://localhost:3000",
  "confidence": "RECOMMENDED",
  "changes": [
    {"type": "structure", "description": "Added headers and bullet points"},
    {"type": "clarity", "description": "Specified version requirements"},
    {"type": "format", "description": "Used code blocks for commands"}
  ]
}
```

### Example 3: Technical Note
**Input**:
```
We're thinking about maybe using Redis for caching because it might help with
performance issues we've been seeing, but we're not totally sure if it's the
right solution or if we should just optimize our queries instead.
```

**Output**:
```json
{
  "improved": "## Caching Strategy Options\n\n**Problem**: Database queries slow under load (2-5s response time)\n\n**Options**:\n1. **Redis caching** (RECOMMENDED)\n   - Pros: Fast reads, reduces DB load\n   - Cons: Adds infrastructure complexity\n   \n2. **Query optimization** (ALTERNATIVE)\n   - Pros: No new dependencies\n   - Cons: May not solve scaling issues\n\n**Decision needed**: Benchmark both approaches with production data volume",
  "confidence": "DEFAULT",
  "changes": [
    {"type": "structure", "description": "Formatted as decision document"},
    {"type": "clarity", "description": "Listed explicit pros/cons"},
    {"type": "action", "description": "Added next step (benchmarking)"}
  ]
}
```

### Example 4: Error Message
**Input**:
```
Something went wrong and we couldn't process your request. Please try again later.
```

**Output**:
```json
{
  "improved": "Failed to create issue: Database connection timeout.\n\nTroubleshooting:\n- Check database status at /admin/health\n- Retry in 30 seconds\n- Contact support if issue persists\n\nError code: DB_TIMEOUT_001",
  "confidence": "RECOMMENDED",
  "changes": [
    {"type": "clarity", "description": "Specified exact error (DB timeout)"},
    {"type": "actionable", "description": "Added troubleshooting steps"},
    {"type": "technical", "description": "Added error code for support"}
  ]
}
```

## Writing Guidelines

### Clarity
- ✅ Use specific terms: "JWT authentication" not "auth stuff"
- ✅ Define acronyms: "REST API (Representational State Transfer)"
- ✅ Active voice: "User clicks button" not "Button is clicked by user"
- ❌ Avoid vague terms: "thing", "stuff", "kind of", "sometimes"

### Conciseness
- ✅ Short sentences: Max 25 words per sentence
- ✅ Remove filler: "in order to" → "to", "due to the fact that" → "because"
- ✅ Direct language: "We will implement" → "Implement"
- ❌ Avoid redundancy: "completely finished", "end result", "future plans"

### Structure
- ✅ Headers for sections: ##, ###
- ✅ Bullet points for lists
- ✅ Code blocks with language: ```python
- ✅ Paragraphs: 3-4 sentences max
- ❌ Avoid wall of text

### Technical Accuracy
- ✅ Preserve code examples exactly
- ✅ Keep technical terms (API, JWT, PostgreSQL)
- ✅ Maintain version numbers (Python 3.12, Node 20)
- ❌ Don't simplify at cost of accuracy

## Integration Points

- **Note Canvas**: Real-time writing suggestions
- **Issue Templates**: Auto-enhance issue descriptions
- **Ghost Text**: Inline improvement suggestions
- **Approval Flow**: Writing improvements are AUTO_EXECUTE (suggestions only)

## References

- Design Decision: DD-048 (Confidence Tagging)
- Writing Guide: docs/WRITING_GUIDE.md (if exists)
- Readability: Flesch Reading Ease score (target: 60-70 for technical docs)
