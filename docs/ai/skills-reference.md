# Skills Reference Documentation (T102)

Comprehensive reference for all 8 PilotSpace AI skills, including SKILL.md format specification and usage examples.

**Version**: 1.0 | **Last Updated**: 2026-01-28

---

## Table of Contents

- [Overview](#overview)
- [SKILL.md Format Specification](#skillmd-format-specification)
- [Available Skills](#available-skills)
  - [extract-issues](#extract-issues)
  - [enhance-issue](#enhance-issue)
  - [recommend-assignee](#recommend-assignee)
  - [find-duplicates](#find-duplicates)
  - [decompose-tasks](#decompose-tasks)
  - [generate-diagram](#generate-diagram)
  - [improve-writing](#improve-writing)
  - [summarize](#summarize)
- [Creating Custom Skills](#creating-custom-skills)

---

## Overview

**Skills** are pre-built AI workflows that provide specific capabilities to PilotSpace users and agents. Each skill is defined in a `SKILL.md` file following a standardized format.

**Key Characteristics**:
- **One-shot execution**: Skills complete in a single request/response
- **Structured output**: Return JSON conforming to defined schema
- **Confidence tagging**: All suggestions include DD-048 confidence tags
- **Discoverable**: Auto-discovered from `backend/.claude/skills/*/SKILL.md`

**Usage Contexts**:
1. **Direct API invocation**: `POST /api/v1/ai/skills/{skill-name}`
2. **Agent workflows**: Agents reference skills via `execute_skill()`
3. **User commands**: Users type `/skill-name` in UI

---

## SKILL.md Format Specification

All skills must follow this structure:

```markdown
---
name: skill-name
description: Brief one-line description
version: 1.0
author: PilotSpace AI
tags: [category1, category2]
---

## Quick Start

Brief usage guide (2-3 sentences).

## When to Use

- Use when <scenario 1>
- Use when <scenario 2>
- Don't use when <anti-pattern>

## Workflow

1. **Step 1**: Description
2. **Step 2**: Description
3. **Step 3**: Description

## Input Format

\`\`\`json
{
  "field1": "description",
  "field2": "description"
}
\`\`\`

## Output Format

\`\`\`json
{
  "result": {
    "field1": "value",
    "confidence": "RECOMMENDED",
    "rationale": "explanation"
  }
}
\`\`\`

## Examples

### Example 1: Basic Usage

**Input**:
\`\`\`json
{...}
\`\`\`

**Output**:
\`\`\`json
{...}
\`\`\`

## Integration Points

- **Agent**: Which agent uses this skill
- **Endpoint**: API endpoint
- **UI**: Where skill is invoked in UI

## Confidence Tagging

All outputs must include:
- `confidence`: RECOMMENDED | DEFAULT | CURRENT | ALTERNATIVE
- `rationale`: Explanation (1-2 sentences)

## Error Handling

- `ValidationError`: Missing required fields
- `NotFoundError`: Referenced entity doesn't exist
- `RateLimitError`: Exceeded usage quota
```

---

## Available Skills

### extract-issues

**Extract actionable issues from note content.**

**Location**: `backend/.claude/skills/extract-issues/SKILL.md`

#### Quick Start

Analyzes note content using NLP to identify action items, feature requests, and bug reports, then structures them as issues with metadata.

#### When to Use

- ✅ User has written brainstorming notes with embedded action items
- ✅ Note contains feature descriptions that should become issues
- ✅ Multiple issues are mentioned in a single note
- ❌ Note is purely informational with no action items

#### Input

```json
{
  "note_id": "uuid",
  "note_content": "Full note text",
  "auto_create": false
}
```

#### Output

```json
{
  "issues": [
    {
      "name": "Implement OAuth2 authentication",
      "description": "Add OAuth2 with Google/GitHub providers",
      "confidence": "RECOMMENDED",
      "rationale": "Clear feature requirement with specific providers",
      "source_block_id": "block-uuid",
      "labels": ["backend", "security"],
      "priority": "high"
    }
  ]
}
```

#### Confidence Criteria

- **RECOMMENDED**: Explicit action verbs ("implement", "fix", "add") + clear scope
- **DEFAULT**: Mentioned feature without urgency markers
- **ALTERNATIVE**: Vague suggestions ("maybe", "consider")

---

### enhance-issue

**Enhance issue metadata with AI suggestions.**

**Location**: `backend/.claude/skills/enhance-issue/SKILL.md`

#### Quick Start

Takes an existing issue and suggests improved labels, priority, description, and assignee based on content analysis and workspace context.

#### When to Use

- ✅ Issue has minimal metadata (no labels, priority)
- ✅ Description is unclear or incomplete
- ✅ Need assignee recommendation
- ❌ Issue already has complete metadata

#### Input

```json
{
  "issue": {
    "id": "uuid",
    "name": "Fix login bug",
    "description": "Users can't log in"
  }
}
```

#### Output

```json
{
  "enhanced_issue": {
    "labels": ["backend", "security", "bug"],
    "labels_confidence": "RECOMMENDED",
    "priority": "critical",
    "priority_confidence": "RECOMMENDED",
    "improved_description": "Users unable to authenticate due to JWT token validation failure. Affects all login attempts since v2.1.0 deployment.",
    "suggested_assignee": {
      "user_email": "alice@example.com",
      "confidence": "DEFAULT",
      "rationale": "Primary backend engineer with auth module experience"
    }
  }
}
```

---

### recommend-assignee

**Suggest assignee based on issue context and team expertise.**

**Location**: `backend/.claude/skills/recommend-assignee/SKILL.md`

#### Quick Start

Analyzes issue content, labels, and workspace member expertise to recommend the best assignee.

#### Input

```json
{
  "issue_id": "uuid",
  "issue_title": "Implement JWT authentication",
  "issue_description": "Add JWT-based auth with refresh tokens",
  "labels": ["backend", "security"]
}
```

#### Output

```json
{
  "assignee": {
    "user_id": "uuid",
    "user_email": "alice@example.com",
    "confidence": "RECOMMENDED",
    "rationale": "Authored 80% of auth module, available capacity (2 issues)",
    "expertise_match": 0.92,
    "current_workload": 2
  }
}
```

#### Confidence Criteria

- **RECOMMENDED**: >80% expertise match + low workload (<3 issues)
- **DEFAULT**: Moderate match (50-80%) or average workload
- **ALTERNATIVE**: Low match (<50%) or high workload (>5 issues)

---

### find-duplicates

**Find similar issues using semantic search.**

**Location**: `backend/.claude/skills/find-duplicates/SKILL.md`

#### Quick Start

Uses OpenAI embeddings + pgvector to find semantically similar issues, preventing duplicate work.

#### Input

```json
{
  "issue_title": "Implement user authentication",
  "issue_description": "Add JWT-based authentication system"
}
```

#### Output

```json
{
  "duplicates": [
    {
      "issue_id": "uuid",
      "issue_title": "Add OAuth2 login",
      "similarity_score": 0.87,
      "confidence": "RECOMMENDED",
      "rationale": "Both involve authentication implementation, high semantic overlap"
    }
  ]
}
```

#### Similarity Thresholds

- **RECOMMENDED**: >0.85 similarity (likely duplicate)
- **DEFAULT**: 0.70-0.85 similarity (possibly related)
- **ALTERNATIVE**: 0.50-0.70 similarity (tangentially related)

---

### decompose-tasks

**Break issue into subtasks with dependencies.**

**Location**: `backend/.claude/skills/decompose-tasks/SKILL.md`

#### Quick Start

Decomposes complex issues into manageable subtasks with dependency tracking and effort estimates.

#### Input

```json
{
  "issue_id": "uuid",
  "issue_description": "Implement complete user authentication with OAuth2 and JWT"
}
```

#### Output

```json
{
  "subtasks": [
    {
      "name": "Design authentication schema",
      "description": "Create DB tables for users, sessions, OAuth providers",
      "confidence": "RECOMMENDED",
      "dependencies": [],
      "estimated_effort": "small"
    },
    {
      "name": "Implement JWT generation",
      "description": "Add JWT library, token signing/verification",
      "confidence": "RECOMMENDED",
      "dependencies": ["Design authentication schema"],
      "estimated_effort": "medium"
    }
  ]
}
```

#### Effort Levels

- `small`: 1-2 hours
- `medium`: 3-8 hours
- `large`: 1-2 days
- `xlarge`: >2 days

---

### generate-diagram

**Generate Mermaid diagram from description.**

**Location**: `backend/.claude/skills/generate-diagram/SKILL.md`

#### Quick Start

Creates Mermaid diagrams (sequence, flowchart, ER, class) from natural language descriptions.

#### Input

```json
{
  "description": "Authentication flow with OAuth2",
  "diagram_type": "sequence"
}
```

#### Output

```json
{
  "diagram": {
    "mermaid_code": "sequenceDiagram\n  User->>App: Login\n  App->>OAuth: Redirect\n  OAuth->>App: Token\n  App->>User: Success",
    "confidence": "RECOMMENDED",
    "diagram_type": "sequence"
  }
}
```

#### Supported Diagram Types

- `sequence`: Sequence diagrams (interactions)
- `flowchart`: Flowcharts (process flow)
- `er`: Entity-relationship diagrams
- `class`: Class diagrams (OOP)
- `state`: State machines

---

### improve-writing

**Improve text clarity, style, and grammar.**

**Location**: `backend/.claude/skills/improve-writing/SKILL.md`

#### Quick Start

Enhances note/issue content for clarity, conciseness, and professional tone while preserving technical accuracy.

#### Input

```json
{
  "text": "We need to implement authentication with OAuth2 support maybe",
  "style": "technical"
}
```

#### Output

```json
{
  "improved_text": "Implement OAuth2 authentication with support for Google and GitHub providers.",
  "confidence": "RECOMMENDED",
  "changes": [
    {"type": "clarity", "description": "Removed hedging word 'maybe'"},
    {"type": "specificity", "description": "Added provider examples"}
  ]
}
```

#### Style Options

- `technical`: Precise, jargon-appropriate
- `concise`: Remove redundancy
- `professional`: Formal tone
- `casual`: Conversational tone

---

### summarize

**Summarize content in various formats.**

**Location**: `backend/.claude/skills/summarize/SKILL.md`

#### Quick Start

Condenses long text into brief summaries (bullet points, single sentence, or multi-paragraph).

#### Input

```json
{
  "content": "Long text content...",
  "format": "bullets",
  "max_length": 100
}
```

#### Output

```json
{
  "summary": "- Key point 1\n- Key point 2\n- Key point 3",
  "confidence": "RECOMMENDED",
  "format": "bullets",
  "original_length": 500,
  "summary_length": 85
}
```

#### Summary Formats

- `bullets`: Bullet-point list
- `brief`: 1-2 sentences
- `detailed`: Multi-paragraph summary
- `executive`: High-level overview

---

## Creating Custom Skills

To create a new skill:

### 1. Create Skill Directory

```bash
mkdir backend/.claude/skills/my-skill
touch backend/.claude/skills/my-skill/SKILL.md
```

### 2. Follow SKILL.md Format

Use the [format specification](#skillmd-format-specification) above.

### 3. Implement Skill Logic

Create corresponding agent or handler:

```python
# backend/src/pilot_space/ai/agents/my_skill_agent.py
from pilot_space.ai.agents.sdk_base import SDKBaseAgent

class MySkillAgent(SDKBaseAgent[MySkillInput, MySkillOutput]):
    AGENT_NAME = "my_skill"

    async def execute(self, input_data, context):
        # Implementation
        return MySkillOutput(...)
```

### 4. Register Skill

Skills are auto-discovered by `SkillRegistry` on startup.

### 5. Test Skill

```python
# backend/tests/unit/ai/test_my_skill.py
async def test_my_skill():
    agent = MySkillAgent(...)
    result = await agent.run(input_data, context)
    assert result.success
    assert result.output.confidence in ["RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"]
```

---

## Best Practices

### Confidence Tagging

✅ **DO**:
- Provide specific rationale (>20 characters)
- Use evidence from input data
- Be consistent across similar cases

❌ **DON'T**:
- Use vague rationale ("seems good")
- Default to RECOMMENDED without justification
- Omit rationale field

### Input Validation

✅ **DO**:
- Validate all required fields
- Check field types and constraints
- Return clear error messages

❌ **DON'T**:
- Accept invalid UUIDs
- Allow empty required fields
- Return generic "invalid input" errors

### Output Quality

✅ **DO**:
- Return structured JSON
- Include all required fields
- Provide actionable suggestions

❌ **DON'T**:
- Return plain text when JSON expected
- Omit confidence/rationale fields
- Provide vague or unusable suggestions

---

## References

- **API Documentation**: `docs/api/ai-chat-api.md`
- **Skill Implementation**: `backend/src/pilot_space/ai/agents/*_agent.py`
- **Design Decision DD-048**: Confidence tagging standard
- **Agent SDK Patterns**: `docs/architect/claude-agent-sdk-architecture.md`

---

**Last Updated**: 2026-01-28 | **Version**: 1.0
