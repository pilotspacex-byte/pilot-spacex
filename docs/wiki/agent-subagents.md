# Pilot Space Agent: Subagents

> **Location**: `backend/src/pilot_space/ai/agents/subagents/`, `agents/ai_context_agent.py`, `agents/plan_generation_agent.py`
> **Design Decisions**: DD-086 (Centralized Agent Architecture), DD-011 (Provider Routing)

## Overview

Subagents are **multi-turn, stateful agents** spawned by the `PilotSpaceAgent` orchestrator for complex, domain-specific tasks. Unlike skills (single-turn, stateless), subagents maintain their own conversation history, can call multiple MCP tools, and stream results back through the orchestrator's SSE pipe. There are 3 subagents plus 2 specialized agents. All use Claude Sonnet by default (DD-011) except where domain complexity demands otherwise.

**Orchestrator → Subagent boundary**: The orchestrator detects intent (`@pr-review`, `@doc-generator`, `@ai-context`), constructs the subagent with workspace context, and delegates. The subagent streams events as `task_progress` SSE events, which the orchestrator forwards to the frontend.

---

## Subagent Roster

| Agent | Type | Model | Streaming | Primary tool servers |
|-------|------|-------|-----------|---------------------|
| `PRReviewSubagent` | Subagent | Sonnet | Yes | `github`, `issue`, `comment` |
| `DocGeneratorSubagent` | Subagent | Sonnet | Yes | `note`, `note_content`, `issue` |
| `AIContextAgent` | Multi-turn | Sonnet | Yes (refine) | `db`, `search`, `note`, `issue` |
| `PlanGenerationAgent` | Query-only | Sonnet | No | `issue`, `project` |
| `RoleSkillMaterializer` | Service | N/A | N/A | None (filesystem I/O) |

---

## `PRReviewSubagent` (`subagents/pr_review_subagent.py`)

**Purpose**: Perform a structured 5-dimension code review on a GitHub PR and post inline comments.

**Triggered by**: `@pr-review` mention in ChatInput, or GitHub webhook `pull_request.opened`/`pull_request.synchronize`.

**5 review dimensions**:
1. **Architecture** — design patterns, separation of concerns, SOLID violations
2. **Code Quality** — readability, complexity, naming, duplication
3. **Security** — OWASP top 10, injection risks, auth bypass, data exposure
4. **Performance** — N+1 queries, blocking I/O, algorithmic complexity
5. **Documentation** — missing docstrings, unclear interfaces, changelog

**Execution flow**:
```
1. github.get_pr(repo, pr_number) → fetch diff + existing comments
2. For each changed file:
   → PilotSpaceAgent context (issue linked to PR if available)
   → Prompt assembly (pr_review.py template, Opus-grade instructions)
3. LLM generates ReviewComment[] with file/line/severity
4. Post review via github.post_review() after approval (DEFAULT tier)
5. Stream progress as task_progress SSE events
6. Emit structured_result with full review summary
```

**Why Sonnet, not Opus?** Sonnet handles the majority of PR reviews well. Opus is reserved for the highest-complexity reviews (>500 file changes, security-critical PRs) and dispatched via `ProviderSelector` task override.

**Severity levels**: `critical` → `major` → `minor` → `nitpick`. Only `critical` and `major` comments are posted as blocking review requests. `minor` and `nitpick` are informational.

**Result SSE**: Emits `StructuredResultCard`-compatible output with issue count by severity, most critical finding, and link to full GitHub review.

---

## `DocGeneratorSubagent` (`subagents/doc_generator_subagent.py`)

**Purpose**: Generate technical documentation from code, notes, and issue context.

**Triggered by**: `@doc-generator` mention, or explicitly via `\generate-docs` skill.

**Document types**:
- **API Documentation** — endpoint descriptions, request/response schemas, error codes
- **README** — project overview, setup, usage, architecture summary
- **Architecture Decision Record (ADR)** — problem, options, decision, consequences
- **Module Documentation** — class/function docs from code structure

**Execution flow**:
```
1. Read relevant notes (note.read_note)
2. Read linked issues (issue.get_issue) for context
3. note_content.get_selected_blocks() for user-selected scope (if any)
4. LLM generates structured Markdown documentation
5. Stream sections as they complete via task_progress
6. Present complete doc via structured_result SSE
7. Optionally: create_note(generated_doc) after user approval
```

**Output**: Markdown document, optionally inserted as a new note in the workspace.

**Streaming**: Each section (Overview, Installation, Usage, API Reference, etc.) streams progressively so users see output before the full document is complete.

---

## `AIContextAgent` (`agents/ai_context_agent.py`)

**Purpose**: Multi-turn context aggregation — builds a comprehensive "context document" for an issue by searching notes, related issues, PR history, and linked documentation.

**Triggered by**: `@ai-context` mention, or from issue detail page "Generate AI Context" button.

**Multi-turn flow**:
```
Turn 1: Initial context generation
  → search.hybrid(issue_title + description)
  → db.query_notes(linked_to_issue)
  → db.query_issues(same_project, similar_labels)
  → LLM assembles initial context document

Turn 2+: User refinement
  → User asks "add more about the authentication flow"
  → Agent searches for auth-related notes/issues
  → Refines and expands the context document
  → Streams updates in real-time
```

**Context document sections**:
- Issue background (why this issue exists)
- Related technical context (linked notes, code references)
- Similar past issues (semantic search matches)
- Team context (who knows about this, past discussions)
- Implementation hints (related PRs, decisions)

**Streaming on refine**: Unlike initial generation (which can be batched), refinement turns stream tokens progressively — users see the updated section as it's written.

**Why multi-turn for context?** Context generation is inherently iterative. The first pass provides broad coverage; subsequent turns focus on gaps the user identifies. A single-turn approach would require the user to specify exactly what they want upfront, which they often can't do until they see the initial output.

---

## `PlanGenerationAgent` (`agents/plan_generation_agent.py`)

**Purpose**: Decompose a feature request into a structured implementation plan with tasks, dependencies, and effort estimates.

**Triggered by**: `\generate-implementation-plan` skill, or from issue detail page "Decompose Tasks" button.

**Input**: Issue title + description + acceptance criteria.

**Output**: `TaskDecompositionOutput` — `AgentTask[]` with:
- Task name and description
- Effort estimate (story points or hours)
- Dependencies (which tasks must complete first)
- Suggested assignee role (frontend/backend/fullstack)
- Acceptance criteria per task

**Query-only execution**: `PlanGenerationAgent` uses `SDK.query()` (not `SDK.run()`) — no multi-turn conversation, no tool calls during generation. It generates the plan in a single LLM call with the full issue context injected.

**DAG validation**: After generation, `output_schemas.TaskDecompositionOutput.validate_dag()` checks for circular dependencies. If detected, a second LLM pass resolves the cycles.

**Why query-only?** Implementation plans are typically generated once and reviewed, not iteratively refined through the same agent session. If refinement is needed, a new invocation is cheaper than maintaining multi-turn state.

---

## `RoleSkillMaterializer` (`agents/role_skill_materializer.py`)

**Purpose**: Write a `SKILL.md` file to the user's agent sandbox that describes which skills are available for their workspace role — enabling the Claude Agent SDK's native skill discovery.

**Not a subagent** — this is a service called on workspace connection, not on user message.

**Why it exists**: The Claude Agent SDK discovers available skills by reading `.claude/skills/` directory. The materialized file bridges Pilot Space's role-based access control to the SDK's filesystem-based discovery.

**Materialization**:
```
workspace_members[user_id].role
  → filter skills: guest=read-only, member=standard, admin=all
  → render SKILL.md template with allowed skill names + descriptions
  → write to /sandbox/{user_id}/{workspace_id}/.claude/skills/SKILL.md
```

**Invalidation**: Re-materialized on every workspace connect and on role change. The file is cheap to rebuild (~10ms) so it's never cached.

---

## Subagent vs. Skill: Decision Guide

| | Skill | Subagent |
|--|-------|---------|
| Turns | 1 (single request) | N (multi-turn conversation) |
| State | Stateless | Stateful (conversation history) |
| Definition | YAML file | Python class |
| Output | `structured_result` SSE | `task_progress` stream |
| Examples | `extract-issues`, `improve-writing` | PR review, doc generation |
| When to use | Defined transformation on known input | Open-ended task requiring iteration |

---

## How Subagent Results Flow Back

Subagents don't have their own SSE connection to the frontend. They communicate back through the orchestrator's SSE pipe:

```
Frontend SSE connection (to PilotSpaceAgent)
    ↓
PilotSpaceAgent dispatches to subagent
    ↓
Subagent calls: orchestrator.emit_sse_event(task_progress, {step, status})
    ↓
PilotSpaceAgent's SSE stream writes the event
    ↓
Frontend receives task_progress event → TaskPanel updates
```

**Why through orchestrator?** The frontend has one SSE connection per conversation. Subagents cannot create new SSE connections — they must use the existing pipe. This also ensures task_progress events are interleaved correctly with other events (tool_use, text_delta) from the orchestrator.

---

## Implicit Features

| Feature | Mechanism | File |
|---------|-----------|------|
| PR review auto-triggered on webhook | FastAPI webhook handler → `PRReviewSubagent` | Router layer |
| Severity-based comment filtering | `severity in {critical, major}` → posting | `pr_review_subagent.py` |
| Doc streaming by section | `task_progress` per section | `doc_generator_subagent.py` |
| Context refinement multi-turn | `SDK.run()` with persistent `session_id` | `ai_context_agent.py` |
| Plan DAG cycle resolution | Second LLM pass if cycles detected | `plan_generation_agent.py` |
| Role-based skill discovery | Materialized `SKILL.md` on connect | `role_skill_materializer.py` |
| Sonnet default for all subagents | `ProviderSelector` task mapping | `provider_selector.py` |
| BYOK key per subagent invocation | `SecureKeyStorage.get_api_key()` in constructor | All subagents |
| RLS context on every DB call | `set_rls_context()` in subagent base class | `agent_base.py` |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Subagents separate from orchestrator (DD-086) | Single Responsibility. PR review logic doesn't belong in the orchestrator. Independent testability, deployability, model selection. |
| All through orchestrator's SSE pipe | One SSE connection per frontend session. Subagents must use the existing pipe. |
| Sonnet default (not Opus) | Sonnet handles 95% of subagent tasks at 5x lower cost. Opus reserved for tasks that demonstrably need it. |
| `PlanGenerationAgent` query-only | Plans are generated once. Multi-turn state for a single-generation task wastes memory. |
| `AIContextAgent` multi-turn | Context is inherently iterative — users refine after seeing the first pass. |
| `RoleSkillMaterializer` as service not subagent | It runs once on connect, not on user message. Wrong lifecycle for a conversational agent. |
| DAG validation post-generation | Generating with constraint instructions adds prompt complexity. Validation + correction pass is cleaner and cheaper. |

---

## Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `agents/agent_base.py` | ~200 | Base class: BYOK, RLS, retry, telemetry |
| `agents/types.py` | ~150 | `AgentTask`, `ReviewComment`, `ContextDocument` types |
| `agents/subagents/pr_review_subagent.py` | ~350 | 5-dimension GitHub PR review |
| `agents/subagents/doc_generator_subagent.py` | ~280 | Multi-type doc generation |
| `agents/ai_context_agent.py` | ~300 | Multi-turn context aggregation |
| `agents/plan_generation_agent.py` | ~220 | Single-pass task decomposition |
| `agents/role_skill_materializer.py` | ~100 | Role → `SKILL.md` filesystem bridge |
| `prompts/pr_review.py` | ~140 | PR review prompt (5 dimensions) |
| `prompts/ai_context.py` | ~120 | Context generation prompt |
| `prompts/implementation_plan.py` | ~130 | Plan decomposition prompt |
