# AI Agent Reference

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

Pilot Space uses a **BYOK (Bring Your Own Key)** AI architecture with 16 specialized AI agents (9 primary + 7 helpers). This document provides a complete reference for each agent, including purpose, triggers, inputs/outputs, and configuration.

### Key Design Decisions

| Decision | Reference | Description |
|----------|-----------|-------------|
| DD-002 | BYOK Model | Anthropic required, OpenAI for embeddings, Gemini optional |
| DD-003 | Approval Model | Auto-execute non-destructive, approve critical actions |
| DD-006 | Unified PR Review | Single agent for architecture + security + quality |
| DD-011 | Provider Routing | Claude→code, Gemini→latency, OpenAI→embeddings |
| DD-048 | Confidence Tags | Recommended, Default, Current, Alternative |
| DD-058 | Agent Count | 9 primary + 7 helpers = 16 total |

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI ORCHESTRATOR                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Task Classification                              │    │
│  │   PR Review → Claude SDK (agentic)                                    │    │
│  │   Task Decomposition → Claude SDK (agentic)                           │    │
│  │   Doc Generation → Claude SDK query()                                 │    │
│  │   Ghost Text → Gemini Flash                                           │    │
│  │   Embeddings → OpenAI                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                         PRIMARY AGENTS (9)                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ GhostText    │ │ IssueEnhancer│ │ PRReview     │ │ TaskDecomp   │        │
│  │ Agent        │ │ Agent        │ │ Agent        │ │ Agent        │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ DocGenerator │ │ DiagramGen   │ │ AIContext    │ │ SmartSearch  │        │
│  │ Agent        │ │ Agent        │ │ Agent        │ │ Agent        │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐                                                            │
│  │ Assignee     │                                                            │
│  │ Recommender  │                                                            │
│  └──────────────┘                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                         HELPER COMPONENTS (7)                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Embedder     │ │ Retriever    │ │ Chunker      │ │ Summarizer   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                         │
│  │ Validator    │ │ Formatter    │ │ Confidence   │                         │
│  │              │ │              │ │ Scorer       │                         │
│  └──────────────┘ └──────────────┘ └──────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Primary Agents

### 1. GhostTextAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Provide real-time typing suggestions in Note Canvas |
| **Provider** | Google Gemini Flash (low latency) |
| **SDK Mode** | Direct API (non-agentic) |
| **Trigger** | 500ms typing pause |
| **Approval** | None (auto-display) |

**Inputs**:
```python
@dataclass
class GhostTextInput:
    current_block: str          # Current block text
    previous_blocks: list[str]  # Last 3 blocks for context
    document_summary: str       # Semantic summary of note
    user_history: dict          # Typing patterns, preferences
```

**Outputs**:
```python
@dataclass
class GhostTextOutput:
    suggestion: str             # 1-2 sentences (~50 tokens)
    confidence: float           # 0.0-1.0 confidence score
```

**Configuration**:
```yaml
ghost_text:
  provider: google
  model: gemini-2.0-flash
  max_tokens: 50
  temperature: 0.7
  trigger_delay_ms: 500
  cache_ttl_seconds: 30
```

**Word Boundary Handling** (DD-067):
- Buffer streaming chunks until whitespace/punctuation
- Display word-by-word, never partial tokens
- → key accepts one word at a time

---

### 2. IssueEnhancerAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Enhance issue title, description, suggest labels/priority |
| **Provider** | Anthropic Claude (quality) |
| **SDK Mode** | `query()` (one-shot) |
| **Trigger** | User requests enhancement OR title blur (duplicate check) |
| **Approval** | User review before applying |

**Inputs**:
```python
@dataclass
class IssueEnhanceInput:
    title: str
    description: str
    project_context: dict       # Labels, states, team members
    similar_issues: list[dict]  # For duplicate detection
```

**Outputs**:
```python
@dataclass
class IssueEnhanceOutput:
    enhanced_title: str
    enhanced_description: str
    acceptance_criteria: list[str]
    suggested_labels: list[LabelSuggestion]
    suggested_priority: PrioritySuggestion
    suggested_assignee: AssigneeSuggestion | None
    potential_duplicates: list[DuplicateMatch]
```

**Configuration**:
```yaml
issue_enhancer:
  provider: anthropic
  model: claude-sonnet-4
  max_tokens: 1000
  duplicate_threshold: 0.70
  confidence_display_threshold: 0.80  # Only show "Recommended" if >= 80%
```

---

### 3. PRReviewAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Unified PR review (architecture, security, quality, performance) |
| **Provider** | Anthropic Claude (agentic with MCP tools) |
| **SDK Mode** | Claude Agent SDK (full agentic) |
| **Trigger** | GitHub webhook on PR open |
| **Approval** | None (posts comments directly) |

**Inputs**:
```python
@dataclass
class PRReviewInput:
    pr_url: str
    repository: str
    base_branch: str
    head_branch: str
    files_changed: list[FileChange]
    project_id: UUID              # For context lookup
```

**Outputs**:
```python
@dataclass
class PRReviewOutput:
    review_comments: list[ReviewComment]
    summary: str
    severity_counts: dict[str, int]  # Critical, Warning, Suggestion
    review_status: str               # approve, request_changes, comment
```

**Review Aspects** (DD-006):

| Aspect | Checks |
|--------|--------|
| **Architecture** | Layer boundaries, dependency direction, design patterns |
| **Security** | OWASP basics, secret detection, injection vulnerabilities |
| **Quality** | Complexity, duplication, naming conventions, dead code |
| **Performance** | N+1 queries, blocking I/O, unnecessary allocations |
| **Documentation** | Missing docstrings, outdated comments |

**Comment Format**:
```markdown
🔴 **Critical** - SQL Injection Vulnerability

**Issue**: User input directly concatenated in query
**Location**: `src/db/user_repo.py:45`

**Suggestion**: Use parameterized queries
```python
# Instead of:
query = f"SELECT * FROM users WHERE id = {user_id}"

# Use:
query = "SELECT * FROM users WHERE id = $1"
await db.execute(query, user_id)
```

**Rationale**: [OWASP A03:2021 - Injection](https://owasp.org/...)
```

**MCP Tools Available**:
- `get_issue_context` - Fetch related issue for context
- `search_codebase` - Search for patterns in repo
- `get_file_content` - Read specific files
- `check_patterns` - Validate against project patterns

---

### 4. TaskDecomposerAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Break features/epics into subtasks with estimates |
| **Provider** | Anthropic Claude (agentic with MCP tools) |
| **SDK Mode** | Claude Agent SDK (agentic) |
| **Trigger** | User requests decomposition |
| **Approval** | User review before creating sub-issues |

**Inputs**:
```python
@dataclass
class TaskDecompInput:
    feature_description: str
    project_context: dict        # Team, tech stack, existing patterns
    parent_issue_id: UUID | None
```

**Outputs**:
```python
@dataclass
class TaskDecompOutput:
    subtasks: list[SubTask]
    dependency_graph: dict[str, list[str]]
    total_estimate_points: int
```

**SubTask Structure**:
```python
@dataclass
class SubTask:
    title: str
    description: str
    type: Literal["frontend", "backend", "database", "devops", "qa"]
    estimate_points: int  # Fibonacci: 1, 2, 3, 5, 8, 13
    dependencies: list[str]
    acceptance_criteria: list[str]
```

---

### 5. DocGeneratorAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate documentation from code or feature descriptions |
| **Provider** | Anthropic Claude |
| **SDK Mode** | `query()` (one-shot) |
| **Trigger** | User requests doc generation |
| **Approval** | User review before saving |

**Inputs**:
```python
@dataclass
class DocGenInput:
    source_type: Literal["code", "feature", "api"]
    content: str
    template: str | None         # Optional template to follow
    style: Literal["technical", "user", "api_reference"]
```

**Outputs**:
```python
@dataclass
class DocGenOutput:
    markdown_content: str
    sections: list[str]
    suggested_title: str
```

---

### 6. DiagramGeneratorAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Generate architecture diagrams from descriptions |
| **Provider** | Anthropic Claude |
| **SDK Mode** | `query()` (one-shot) |
| **Trigger** | User requests diagram |
| **Approval** | User review before inserting |

**Inputs**:
```python
@dataclass
class DiagramGenInput:
    description: str
    diagram_type: Literal["sequence", "class", "flowchart", "erd", "c4"]
    format: Literal["mermaid", "plantuml"]
```

**Outputs**:
```python
@dataclass
class DiagramGenOutput:
    diagram_code: str
    format: str
    description: str
```

**Supported Diagram Types** (DD-012):
- Sequence diagrams
- Class diagrams
- Flowcharts
- Entity-Relationship Diagrams
- C4 Component diagrams

---

### 7. AIContextAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Aggregate context (code, docs, issues) for development |
| **Provider** | Anthropic Claude (agentic with MCP tools) |
| **SDK Mode** | Claude Agent SDK (agentic) |
| **Trigger** | User views AI Context panel OR manual refresh |
| **Approval** | None (read-only) |

**Inputs**:
```python
@dataclass
class AIContextInput:
    issue_id: UUID
    include_code: bool = True
    include_docs: bool = True
    include_related: bool = True
```

**Outputs**:
```python
@dataclass
class AIContextOutput:
    code_files: list[CodeFile]
    related_docs: list[Document]
    related_issues: list[Issue]
    claude_code_prompt: str      # Ready-to-copy prompt for Claude Code
    summary: str
```

**Code Discovery** (DD-055):
- AST analysis for file path patterns
- Symbol detection (functions, classes)
- GitHub API search for matching files

---

### 8. SmartSearchAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Semantic search with AI-generated summaries |
| **Provider** | OpenAI (embeddings) + Claude (summaries) |
| **SDK Mode** | Hybrid (embeddings + query) |
| **Trigger** | User searches |
| **Approval** | None |

**Inputs**:
```python
@dataclass
class SearchInput:
    query: str
    workspace_id: UUID
    filters: SearchFilters | None
    limit: int = 20
```

**Outputs**:
```python
@dataclass
class SearchOutput:
    results: list[SearchResult]
    ai_summary: str | None       # LLM summary of top results
    total_count: int
```

---

### 9. AssigneeRecommenderAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Suggest team members based on expertise and availability |
| **Provider** | Anthropic Claude |
| **SDK Mode** | `query()` (one-shot) |
| **Trigger** | Issue creation, assignee field focus |
| **Approval** | User selection |

**Inputs**:
```python
@dataclass
class AssigneeInput:
    issue: dict
    team_members: list[TeamMember]
    recent_assignments: list[Assignment]
```

**Outputs**:
```python
@dataclass
class AssigneeOutput:
    recommendations: list[AssigneeRecommendation]
```

**Factors Considered**:
- Code ownership (recent commits to related files)
- Past similar issues
- Current workload
- Expertise areas

---

## Helper Components

### 1. Embedder
Converts text to vector embeddings using OpenAI `text-embedding-3-large` (3072 dimensions).

### 2. Retriever
Performs similarity search in pgvector using HNSW indexing.

### 3. Chunker
Splits documents into semantic chunks (512 tokens, 50 token overlap).

### 4. Summarizer
Generates concise summaries using Claude Haiku 4.5 for speed.

### 5. Validator
Validates AI outputs against schemas before returning.

### 6. Formatter
Formats AI responses for display (markdown, JSON, etc.).

### 7. ConfidenceScorer
Calculates confidence scores for suggestions (DD-048).

---

## Provider Configuration

### BYOK Setup (DD-002)

```yaml
ai:
  providers:
    anthropic:
      required: true
      models: [claude-opus-4-5, claude-sonnet-4, claude-haiku-4]
      use_for: [pr_review, task_decomposition, doc_generation, ai_context]

    google:
      required: false  # Recommended for latency
      models: [gemini-2.0-flash, gemini-2.0-pro]
      use_for: [ghost_text, margin_annotations]
      fallback: anthropic

    openai:
      required: true  # Required for embeddings
      models: [text-embedding-3-large]
      use_for: [embeddings]
```

### Approval Matrix (DD-003)

| Action | Default Behavior | Configurable |
|--------|------------------|--------------|
| Display suggestions | Auto | No |
| Apply labels/priority | Show, user confirms | Yes |
| Create sub-issues | Require approval | Yes |
| Post PR comments | Auto | Yes |
| Delete/archive | **Always approval** | No |

---

## Rate Limiting

| Agent | Requests/min | Timeout |
|-------|--------------|---------|
| GhostText | 60 | 5s |
| IssueEnhancer | 30 | 30s |
| PRReview | 10 | 5min |
| TaskDecomposer | 20 | 60s |
| DocGenerator | 20 | 60s |
| DiagramGenerator | 20 | 30s |
| AIContext | 30 | 60s |
| SmartSearch | 60 | 10s |
| AssigneeRecommender | 30 | 15s |

---

## Error Handling

### Fallback Strategy

```python
async def execute_with_fallback(agent: BaseAgent, input: Any) -> Any:
    providers = agent.get_providers_in_order()

    for provider in providers:
        try:
            return await agent.execute(input, provider)
        except RateLimitError:
            await asyncio.sleep(exponential_backoff())
            continue
        except ProviderError:
            continue  # Try next provider

    raise AllProvidersFailedError()
```

### Circuit Breaker

```python
circuit_breaker:
  failure_threshold: 5
  recovery_timeout_seconds: 60
  half_open_requests: 3
```

---

## References

- [docs/architect/ai-layer.md](../../../../docs/architect/ai-layer.md) - AI layer architecture
- [docs/architect/claude-agent-sdk-architecture.md](../../../../docs/architect/claude-agent-sdk-architecture.md) - SDK integration
- [DESIGN_DECISIONS.md](../../../../docs/DESIGN_DECISIONS.md) - Related decisions
