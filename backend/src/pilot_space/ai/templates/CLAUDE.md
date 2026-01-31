# CLAUDE.md - PilotSpace AI Agent Instructions

**Audience**: Claude Code (claude.ai/code) AI agents operating within PilotSpace
**Purpose**: Project-specific instructions for AI-assisted development
**Version**: 1.0 | **Updated**: 2026-01-27

---

## Project Overview

PilotSpace is an AI-augmented SDLC platform with a **Note-First** workflow where users brainstorm with AI in collaborative documents, and issues emerge naturally from refined thinking.

**Core Differentiator**: Note canvas as default home, not dashboards. AI acts as embedded co-writing partner, not bolt-on feature.

---

## Note-First Workflow (DD-013)

PilotSpace workflow begins in notes, not tickets:

```
1. User opens Note Canvas
2. User writes/brainstorms with AI ghost text assistance
3. AI suggests margin annotations for potential issues
4. User accepts annotations → Issues created with full context
5. Issues link back to originating note blocks
```

**Implications for AI Agents**:
- Notes are primary context source, not just documentation
- Issue extraction must preserve note context links
- AI suggestions appear in real-time during writing
- All AI output must respect "human-in-the-loop" principle (DD-003)

---

## AI Confidence Tagging (DD-048)

All AI suggestions MUST include confidence tags. Use human-readable labels, not percentages:

| Tag | Meaning | When to Use |
|-----|---------|-------------|
| **RECOMMENDED** | Highest confidence, backed by evidence | Clear best practice, strong semantic match |
| **DEFAULT** | Standard choice, safe option | Most common pattern, no special context |
| **CURRENT** | Existing state, no change suggested | Documenting current approach |
| **ALTERNATIVE** | Valid option, different trade-offs | Multiple valid approaches exist |

**Examples**:

```json
{
  "suggestion": "Add type hints to public API",
  "confidence": "RECOMMENDED",
  "rationale": "PEP 484 compliance, matches project standard"
}
```

```json
{
  "assignee": "alice@example.com",
  "confidence": "DEFAULT",
  "rationale": "Primary frontend engineer, worked on similar components"
}
```

**Never use**: Percentages (87% confidence), numeric scores, vague terms (likely, probably)

---

## Human-in-the-Loop Approval (DD-003)

All AI actions are classified into three tiers:

### AUTO_EXECUTE
Non-destructive, suggestion-only actions that execute immediately:
- Ghost text suggestions
- Margin annotations
- AI context aggregation
- PR review comments
- Duplicate detection
- Assignee recommendations
- Documentation generation
- Diagram generation

### DEFAULT_REQUIRE_APPROVAL
Actions that create or modify entities (configurable per workspace):
- Create issue from annotation
- Create margin annotation
- Link commit to issue
- Update issue metadata
- Decompose issue into subtasks

### CRITICAL_REQUIRE_APPROVAL
Destructive actions that **always** require approval:
- Delete issue
- Merge pull request
- Close issue

**Workflow**:
1. Agent classifies action using `PermissionHandler`
2. If AUTO_EXECUTE: Proceed immediately
3. If REQUIRE_APPROVAL: Create approval request, return approval_id
4. User approves/rejects via UI
5. Agent polls approval status, executes if approved

**Implementation**:
```python
from pilot_space.ai.sdk import PermissionHandler

permission_result = await permission_handler.check_permission(
    workspace_id=workspace_id,
    user_id=user_id,
    agent_name="issue_extractor",
    action_name="create_issue",
    description="Create issue: Implement user authentication",
    proposed_changes={
        "name": "Implement user authentication",
        "project_id": "...",
        "priority": "high"
    },
)

if permission_result.requires_approval:
    return {"approval_id": permission_result.approval_id}
else:
    # Proceed with execution
    await create_issue(...)
```

---

## Available Skills

Skills are pre-built workflows accessible via `/skill-name` commands:

| Skill | Purpose | Input | Output |
|-------|---------|-------|--------|
| `/extract-issues` | Extract issues from note | Note content | Issues with confidence tags |
| `/enhance-issue` | Enhance issue details | Issue ID | Enhanced issue with labels/priority |
| `/recommend-assignee` | Suggest assignee | Issue context | Assignee with rationale |
| `/find-duplicates` | Find similar issues | Issue title/desc | Duplicate candidates |
| `/decompose-tasks` | Break into subtasks | Issue description | Subtask list with dependencies |
| `/generate-diagram` | Create Mermaid diagram | Description | Mermaid code |
| `/improve-writing` | Improve clarity/style | Text content | Improved version |
| `/summarize` | Summarize content | Content + format | Summary (bullet/brief/detailed) |

**Usage in Agent Code**:
Skills are implemented in `backend/.claude/skills/{skill-name}/SKILL.md`. Reference skill workflows when implementing similar functionality.

---

## Available Subagents

Subagents handle complex multi-turn tasks with streaming:

### PRReviewSubagent
**Purpose**: Interactive PR review with architecture/security/performance analysis
**Input**: `repository_id`, `pr_number`
**Output**: Streaming review findings (SSE)
**Model**: Claude Sonnet 4
**Tools**: get_pr_diff, get_pr_files, add_review_comment

### AIContextSubagent
**Purpose**: Conversational issue context aggregation
**Input**: `issue_id`
**Output**: Streaming context discoveries (SSE)
**Model**: Claude Sonnet 4
**Tools**: search_related_notes, search_codebase, find_similar_issues, get_issue_history

### DocGeneratorSubagent
**Purpose**: Interactive documentation generation
**Input**: `doc_type`, `source_files`
**Output**: Streaming generated documentation (SSE)
**Model**: Claude Sonnet 4
**Tools**: read_source_file, analyze_api_endpoints, get_existing_docs

**When to use Subagents vs Skills**:
- **Subagents**: Multi-turn conversations, streaming responses, complex context
- **Skills**: One-shot tasks, structured output, quick workflows

---

## Output Format Guidelines

### RFC 7807 Problem Details
All error responses MUST use RFC 7807 format:

```json
{
  "type": "/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "Issue name cannot be empty",
  "instance": "/api/v1/issues",
  "errors": [
    {"field": "name", "message": "Field is required"}
  ],
  "trace_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Issue Extraction Format
When extracting issues from notes:

```json
{
  "issues": [
    {
      "name": "Implement user authentication",
      "description": "Add JWT-based auth with refresh tokens",
      "confidence": "RECOMMENDED",
      "source_block_id": "block-uuid",
      "labels": ["backend", "security"],
      "priority": "high",
      "rationale": "Mentioned 3 times in note, clear acceptance criteria"
    }
  ]
}
```

### Margin Annotation Format
When creating margin annotations:

```json
{
  "type": "suggestion",
  "block_id": "block-uuid",
  "confidence": "RECOMMENDED",
  "content": "Consider breaking this into subtasks",
  "action": {
    "type": "create_issues",
    "subtasks": [
      {"name": "Design schema", "priority": "medium"},
      {"name": "Implement API", "priority": "high"}
    ]
  }
}
```

### AI Context Format
When building AI context:

```json
{
  "summary": "Issue involves authentication flow redesign",
  "related_documents": [
    {
      "type": "note",
      "id": "note-uuid",
      "title": "Auth Architecture Review",
      "relevance": "RECOMMENDED",
      "excerpt": "JWT implementation considerations..."
    }
  ],
  "code_snippets": [
    {
      "file": "src/auth/jwt.py",
      "line": 42,
      "code": "def verify_token(token: str) -> User:",
      "relevance": "DEFAULT",
      "explanation": "Current JWT verification logic"
    }
  ],
  "task_breakdown": [
    {
      "name": "Update JWT library",
      "confidence": "RECOMMENDED",
      "dependencies": []
    }
  ]
}
```

---

## MCP Tools Available

Agents have access to these MCP (Model Context Protocol) tools:

### Note Tools (6 tools)

**Reading Notes**:
- `summarize_note(note_id)`: Read the full content of a note as markdown. **Always call this first** before making any changes to understand the note structure and content. Returns note title, content blocks, and metadata.

**Editing Notes**:
- `update_note_block(note_id, block_id, new_content_markdown, operation)`: Update or append content in a specific block. Use `operation="replace"` to replace existing block content, or `operation="append"` to add new content after the block. Returns operation status and affected block IDs.
- `enhance_text(note_id, block_id, enhanced_markdown)`: Replace a block's content with an improved/enhanced version. Use this when the user asks to improve, rewrite, clarify, or enhance text. This is a specialized version of `update_note_block` for better clarity.

**Issue Management**:
- `extract_issues(note_id, block_ids, issues)`: Identify and create multiple issues from note content. Each issue in the `issues` array should have `title`, `description`, `type` (task/bug/feature), and `priority` (low/medium/high/critical). Creates issues with NoteIssueLink of type EXTRACTED. Returns created issue data for inline node insertion.
- `create_issue_from_note(note_id, block_id, title, description, priority, issue_type)`: Create a single issue linked to a specific note block. Use this for focused issue creation when the user wants to create one issue from a specific section. Returns issue data with note link.
- `link_existing_issues(note_id, search_query, workspace_id)`: Search for existing issues in the workspace and link them to the note. Use this to connect related work without creating duplicates. Returns matching issues with relevance scores.

**Note Tools Workflow**:

```python
# 1. Always start by reading the note
note_content = await tool_registry.execute_tool(
    "summarize_note",
    {"note_id": str(note_id)},
)

# 2. Identify which blocks to modify based on content
# Note content includes block IDs and markdown content

# 3. Update content in specific blocks
await tool_registry.execute_tool(
    "update_note_block",
    {
        "note_id": str(note_id),
        "block_id": "block-uuid",
        "new_content_markdown": "# Updated heading\n\nNew content here",
        "operation": "replace",  # or "append"
    },
)

# 4. Extract issues from identified blocks
await tool_registry.execute_tool(
    "extract_issues",
    {
        "note_id": str(note_id),
        "block_ids": ["block-1", "block-2"],
        "issues": [
            {
                "title": "Implement authentication",
                "description": "Add JWT-based auth",
                "type": "task",
                "priority": "high",
            },
            {
                "title": "Add input validation",
                "description": "Validate all API inputs",
                "type": "task",
                "priority": "medium",
            },
        ],
    },
)

# 5. Link existing related issues
await tool_registry.execute_tool(
    "link_existing_issues",
    {
        "note_id": str(note_id),
        "search_query": "authentication security",
        "workspace_id": str(workspace_id),
    },
)
```

**Critical Notes**:
- **Always** call `summarize_note` first to understand the note structure before making changes
- Use `enhance_text` for text improvements, `update_note_block` for structural changes
- When extracting multiple related issues, prefer `extract_issues` over multiple `create_issue_from_note` calls
- Check for existing related issues with `link_existing_issues` before creating new ones to avoid duplicates
- All note modification tools trigger the approval flow (DD-003) if configured in workspace settings

### Database Tools (7 tools)
- `get_issue_by_id`: Retrieve issue details
- `create_issue_in_db`: Create new issue (requires approval)
- `update_issue_in_db`: Update issue metadata (requires approval)
- `search_issues`: Search issues with filters
- `get_related_notes`: Get notes linked to issue
- `create_annotation_in_db`: Create margin annotation (requires approval)
- `get_workspace_members`: Get workspace team members

### GitHub Tools (3 tools)
- `get_pr_diff`: Get PR diff for review
- `get_pr_files`: List files changed in PR
- `link_commit_to_issue`: Link commit to issue (requires approval)

### Search Tools (2 tools)
- `semantic_search`: Search using pgvector embeddings
- `search_codebase`: Full-text code search

**Tool Usage**:
All database write tools trigger approval flow (DD-003). Read-only tools execute immediately.

```python
# Example: Creating issue via MCP tool
result = await tool_registry.execute_tool(
    "create_issue_in_db",
    {
        "workspace_id": str(workspace_id),
        "project_id": str(project_id),
        "name": "Fix login bug",
        "description": "Users cannot log in with email",
        "priority": "critical",
    },
)
```

---

## Model Selection Guidelines (DD-011)

Choose models based on task characteristics:

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| **Code Review** | Claude Sonnet 4 | Best reasoning, security analysis |
| **Architecture** | Claude Opus 4.5 | Highest reasoning for complex design |
| **Ghost Text** | Gemini 2.0 Flash | Lowest latency for real-time suggestions |
| **Embeddings** | text-embedding-3-large | Best semantic search quality |
| **Issue Enhancement** | Claude Sonnet 4 | Good balance of quality and cost |
| **Documentation** | Claude Sonnet 4 | Strong technical writing |

**Configuration**:
```python
from pilot_space.ai.sdk import get_model_for_task

model = get_model_for_task("code")  # Returns "claude-sonnet-4-20250514"
model = get_model_for_task("latency")  # Returns "gemini-2.0-flash"
```

---

## Session Management

For multi-turn conversations, use SessionHandler:

```python
from pilot_space.ai.sdk import SessionHandler

# Create session
session_handler = SessionHandler(session_manager)
session = await session_handler.create_session(
    workspace_id=workspace_id,
    user_id=user_id,
    agent_name="ai_context",
)

# Add messages
await session_handler.add_message(
    session_id=session.session_id,
    role="user",
    content="Tell me about authentication issues",
    tokens=12,
)

# Get messages for SDK (respects 8000 token budget)
messages = session.get_messages_for_sdk(max_tokens=8000)
```

**Session Lifecycle**:
- **TTL**: 30 minutes from last update
- **Storage**: Redis with session_id key
- **Budget**: Maximum 8000 tokens per session
- **Cleanup**: Automatic expiration after TTL

---

## Error Handling

All agents must handle errors gracefully:

```python
from pilot_space.ai.agents.sdk_base import AgentResult

try:
    result = await execute_task(...)
    return AgentResult.ok(result)
except ValidationError as e:
    return AgentResult.fail(f"Validation failed: {e}")
except APIError as e:
    return AgentResult.fail(f"API error: {e}")
except Exception as e:
    logger.exception("Unexpected error in agent")
    return AgentResult.fail("Internal error occurred")
```

**Error Categories**:
- **Validation**: Input data invalid (return helpful message)
- **Authorization**: User lacks permission (suggest contacting admin)
- **NotFound**: Entity doesn't exist (suggest alternatives)
- **RateLimitExceeded**: API quota hit (suggest retry time)
- **Internal**: Unexpected errors (log full trace, return generic message)

---

## Testing Requirements

All agent code must include tests:

```python
import pytest
from pilot_space.ai.agents.issue_extractor_sdk_agent import IssueExtractorAgent

@pytest.mark.asyncio
async def test_extract_issues_with_confidence():
    agent = IssueExtractorAgent(...)
    input_data = ExtractIssuesInput(
        note_content="Implement user auth with JWT tokens"
    )
    result = await agent.execute(input_data, context)

    assert result.success
    assert len(result.output.issues) > 0
    assert result.output.issues[0].confidence in [
        "RECOMMENDED", "DEFAULT", "CURRENT", "ALTERNATIVE"
    ]
```

**Coverage Requirements**:
- 80% minimum test coverage
- Test all confidence tag branches
- Test approval flow integration
- Test error cases (validation, authorization)

---

## Quick Reference

**Check Permission**:
```python
from pilot_space.ai.sdk import PermissionHandler
result = await permission_handler.check_permission(...)
```

**Create Session**:
```python
from pilot_space.ai.sdk import SessionHandler
session = await session_handler.create_session(...)
```

**Execute Tool**:
```python
result = await tool_registry.execute_tool(tool_name, params)
```

**Tag Confidence**:
```python
{"confidence": "RECOMMENDED", "rationale": "..."}
```

**Stream Response**:
```python
async for chunk in subagent.execute_stream(input_data, context):
    yield f"data: {chunk}\n\n"
```

---

## Additional Resources

- **Architecture**: `docs/architect/ai-layer.md`
- **Design Decisions**: `docs/DESIGN_DECISIONS.md`
- **Skills**: `backend/.claude/skills/*/SKILL.md`
- **Agent SDK**: `docs/architect/claude-agent-sdk-architecture.md`

For questions or clarifications, refer to project documentation or ask the development team.
