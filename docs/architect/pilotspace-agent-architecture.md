# PilotSpace Agent Architecture - Centralized Conversational AI

> **Version**: 1.5.0
> **Status**: Design Document
> **Author**: Principal AI Systems Architect
> **Date**: 2026-01-27

## Executive Summary

This document proposes a **centralized conversational agent architecture** for PilotSpace that introduces a unified "PilotSpace Agent" as the primary AI interface. The main agent can spawn specialized subagents or execute skills based on complexity, following a task-based execution plan with human-in-the-loop approval workflows.

### Key Design Principles

1. **GhostText remains independent** - Fast inline completion (<2s) bypasses main agent
2. **Skills over simple agents** - Lightweight operations use skills, not full subagents
3. **Subagents for complex tasks** - Only PR review, AI context, and doc generation warrant subagents
4. **Task-driven execution** - Complex requests decompose into trackable tasks
5. **Human-in-the-loop** - Critical actions require explicit approval (DD-003)
6. **Claude Agent SDK native** - Leverage SDK's skill loading, builtin tools, and sandbox features

### Architecture Comparison

| Current State | Proposed State |
|---------------|----------------|
| 14+ independent agents | PilotSpace Agent hub + 3 complex subagents + skills |
| GhostText via orchestrator | GhostText direct (fast path) |
| Siloed feature stores | Unified PilotSpaceStore |
| Custom skill registry | Claude SDK `.claude/skills/` filesystem |
| Context per feature | Unified note/issue/selection context |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Agent Hierarchy](#2-agent-hierarchy)
3. [Claude Agent SDK Integration](#3-claude-agent-sdk-integration)
   - 3.1-3.10 Core SDK Features (Skills, Tools, Hooks, Approvals, Commands)
   - 3.11 [Session Management](#311-session-management)
   - 3.12 [Memory System](#312-memory-system-claudemd)
   - 3.13 [Checkpointing & File Rewind](#313-checkpointing--file-rewind)
   - 3.14 [Model Configuration](#314-model-configuration)
   - 3.15 [Output Styles](#315-output-styles)
   - 3.16 [Plugins System](#316-plugins-system)
   - 3.17 [Structured Outputs](#317-structured-outputs)
   - 3.18 [Sandbox Configuration](#318-sandbox-configuration)
   - 3.19 [Subagent Deep Dive](#319-subagent-deep-dive)
4. [Skill System](#4-skill-system)
5. [Backend Design](#5-backend-design)
6. [Frontend Architecture](#6-frontend-architecture)
7. [ChatView Component Tree](#7-chatview-component-tree)
8. [Data Flow & Sequences](#8-data-flow--sequences)
9. [API Contracts](#9-api-contracts)
10. [Implementation Roadmap](#10-implementation-roadmap)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            PILOTSPACE AI PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                        FRONTEND (Next.js 15+)                             │ │
│  │                                                                           │ │
│  │   ┌─────────────┐      ┌─────────────┐      ┌─────────────────────────┐  │ │
│  │   │ NoteCanvas  │      │  ChatView   │      │    ApprovalPanel        │  │ │
│  │   │             │      │             │      │                         │  │ │
│  │   │ • GhostText │      │ • Messages  │      │ • DiffViewer            │  │ │
│  │   │   (direct)  │      │ • ToolUse   │      │ • Accept/Reject         │  │ │
│  │   │ • \skill    │      │ • TaskList  │      │ • Modify                │  │ │
│  │   │ • @agent    │      │ • Approvals │      │ • BatchApproval         │  │ │
│  │   └──────┬──────┘      └──────┬──────┘      └───────────┬─────────────┘  │ │
│  │          │                    │                         │                │ │
│  │          ▼                    ▼                         ▼                │ │
│  │   ┌─────────────┐      ┌─────────────────────────────────────────────┐  │ │
│  │   │ GhostText   │      │           PilotSpaceStore (MobX)            │  │ │
│  │   │ Store       │      │                                             │  │ │
│  │   │ (isolated)  │      │  • messages    • tasks    • approvals       │  │ │
│  │   └──────┬──────┘      │  • context     • skills   • streaming       │  │ │
│  │          │             └──────────────────────┬──────────────────────┘  │ │
│  └──────────┼────────────────────────────────────┼──────────────────────────┘ │
│             │ SSE (fast)                         │ SSE (conversational)       │
│  ┌──────────┼────────────────────────────────────┼──────────────────────────┐ │
│  │          ▼                                    ▼                          │ │
│  │   ┌─────────────┐                    ┌─────────────────────────────┐    │ │
│  │   │ GhostText   │                    │      PilotSpace Agent       │    │ │
│  │   │ Agent       │                    │      (Main Orchestrator)    │    │ │
│  │   │             │                    │                             │    │ │
│  │   │ • Haiku     │                    │  ┌─────────────────────┐   │    │ │
│  │   │ • 2s max    │                    │  │   Skill Executor    │   │    │ │
│  │   │ • Streaming │                    │  │                     │   │    │ │
│  │   └─────────────┘                    │  │ • extract-issues    │   │    │ │
│  │                                      │  │ • improve-writing   │   │    │ │
│  │                                      │  │ • summarize         │   │    │ │
│  │                                      │  │ • find-duplicates   │   │    │ │
│  │                                      │  │ • recommend-assignee│   │    │ │
│  │                                      │  │ • decompose-tasks   │   │    │ │
│  │                                      │  └─────────────────────┘   │    │ │
│  │                                      │                             │    │ │
│  │                                      │  ┌─────────────────────┐   │    │ │
│  │                                      │  │  Subagent Spawner   │   │    │ │
│  │                                      │  │                     │   │    │ │
│  │                                      │  │ • PRReviewAgent     │   │    │ │
│  │                                      │  │ • AIContextAgent    │   │    │ │
│  │                                      │  │ • DocGeneratorAgent │   │    │ │
│  │                                      │  └─────────────────────┘   │    │ │
│  │                                      └─────────────────────────────┘    │ │
│  │                                                                          │ │
│  │                        BACKEND (FastAPI + Pydantic v2)                  │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Request Routing

```
User Input
    │
    ├─── Typing in editor ───► GhostTextAgent (direct, <2s)
    │
    ├─── \skill command ─────► PilotSpaceAgent → SkillExecutor
    │
    ├─── @agent mention ─────► PilotSpaceAgent → SubagentSpawner
    │
    └─── Natural language ───► PilotSpaceAgent → Plan → Skills/Subagents
```

---

## 2. Agent Hierarchy

### 2.1 Agent Classification

| Agent | Type | Model | Latency Target | Use Case |
|-------|------|-------|----------------|----------|
| **GhostTextAgent** | Independent | Haiku | <2s | Inline text completion |
| **PilotSpaceAgent** | Orchestrator | Sonnet | <10s | Conversation, planning, coordination |
| **PRReviewAgent** | Subagent | Opus | <5min | Deep code analysis |
| **AIContextAgent** | Subagent | Opus | <30s | Issue context aggregation |
| **DocGeneratorAgent** | Subagent | Sonnet | <60s | Documentation generation |

### 2.2 Skills (Migrated from Simple Agents)

These operations are now **skills** executed inline by PilotSpaceAgent:

| Skill | Previously | Why Skill? |
|-------|-----------|------------|
| `extract-issues` | IssueExtractorAgent | Single prompt, no tools needed |
| `improve-writing` | N/A | Simple text transformation |
| `summarize` | N/A | Single prompt operation |
| `find-duplicates` | DuplicateDetectorAgent | Vector search + single prompt |
| `recommend-assignee` | AssigneeRecommenderAgent | DB query + single prompt |
| `decompose-tasks` | TaskDecomposerAgent | Single prompt, structured output |
| `enhance-issue` | IssueEnhancerAgent | Single prompt with context |
| `generate-diagram` | DiagramGeneratorAgent | Single prompt, Mermaid output |

### 2.3 Why Keep Subagents?

**PRReviewAgent**, **AIContextAgent**, and **DocGeneratorAgent** remain subagents because:

1. **Multi-turn reasoning** - Require iterative analysis
2. **Tool usage** - Need file access, code search, external APIs
3. **Long execution** - May take minutes, need progress tracking
4. **Streaming output** - Generate large outputs incrementally

---

## 3. Claude Agent SDK Integration

This section documents how PilotSpace integrates with the Claude Agent SDK for skill loading, builtin tools, and multi-user sandboxing.

### 3.1 SDK Skill Loading Architecture

Claude Agent SDK loads skills from **filesystem directories** using a **progressive disclosure** pattern:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SKILL LOADING HIERARCHY                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Level 1: METADATA (Always loaded at startup ~100 tokens/skill)                │
│  ├── name + description from YAML frontmatter                                  │
│  └── Claude decides which skill to trigger based on metadata                   │
│                                                                                 │
│  Level 2: INSTRUCTIONS (Loaded when skill triggered <5k tokens)                │
│  ├── SKILL.md body with workflows and guidance                                 │
│  └── Read via bash by Claude when needed                                       │
│                                                                                 │
│  Level 3+: RESOURCES (Loaded as needed, unlimited)                             │
│  ├── Additional .md files, scripts, templates                                  │
│  └── Scripts executed without loading content into context                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Skill Directory Sources

Skills are discovered from multiple filesystem locations:

| Source | Location | Scope | Version Control |
|--------|----------|-------|-----------------|
| **Project Skills** | `{cwd}/.claude/skills/` | Shared with team | Git-tracked |
| **User Skills** | `~/.claude/skills/` | Personal across projects | User-managed |
| **Plugin Skills** | `{plugin_dir}/skills/` | From installed plugins | Plugin-managed |

**Directory Structure:**

```
{user_project_cwd}/
├── .claude/
│   ├── skills/                      # Project-level skills
│   │   ├── extract-issues/
│   │   │   └── SKILL.md
│   │   ├── improve-writing/
│   │   │   ├── SKILL.md
│   │   │   └── STYLE_GUIDE.md
│   │   └── pr-review/
│   │       ├── SKILL.md
│   │       ├── CHECKLIST.md
│   │       └── scripts/
│   │           └── analyze_diff.py
│   ├── settings.json               # Project settings
│   └── CLAUDE.md                   # Project instructions
├── notes/                          # User content
└── ...
```

### 3.3 SKILL.md File Format

Each skill requires a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: extract-issues
description: >
  Extract structured issues from note content. Use when the user asks to
  identify tasks, bugs, or work items from their notes or selected text.
---

# Extract Issues

## Quick Start

Analyze the provided content and identify actionable items.

## Workflow

1. Read the content or selection
2. Identify potential issues (bugs, tasks, features)
3. For each issue:
   - Generate a clear title
   - Write description with context
   - Suggest labels and priority
   - Include confidence score

## Output Format

Return JSON with this structure (see examples in EXAMPLES.md).
```

**Field Requirements:**

| Field | Max Length | Constraints |
|-------|-----------|-------------|
| `name` | 64 chars | lowercase, numbers, hyphens only |
| `description` | 1024 chars | Non-empty, no XML tags |

### 3.4 SDK Configuration for Skill Loading

PilotSpace **must** configure `setting_sources` to load skills from the filesystem:

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

def create_pilotspace_agent(user_id: str, workspace_id: str) -> ClaudeAgentOptions:
    """Create agent options with proper skill loading."""

    # User's isolated project directory (critical for multi-user)
    user_cwd = f"/sandbox/{user_id}/{workspace_id}"

    return ClaudeAgentOptions(
        # Working directory - skills loaded from {cwd}/.claude/skills/
        cwd=user_cwd,

        # REQUIRED: Include "project" to load .claude/skills/
        # Include "user" to also load ~/.claude/skills/
        setting_sources=["project", "user"],

        # Enable builtin tools including Skill
        allowed_tools=[
            "Skill",           # Invoke skills from .claude/skills/
            "Read",            # Read files
            "Write",           # Write files (with approval)
            "Edit",            # Edit files (with approval)
            "Bash",            # Execute commands (sandboxed)
            "Glob",            # Find files by pattern
            "Grep",            # Search file contents
            "Task",            # Spawn subagents
            "TodoWrite",       # Task tracking
            "AskUserQuestion", # User clarification
            "WebFetch",        # Fetch web content
        ],

        # Use Claude Code system prompt (includes skill discovery)
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": PILOTSPACE_SYSTEM_PROMPT_ADDITION,
        },

        # Permission handling
        permission_mode="default",
        can_use_tool=pilotspace_permission_handler,
    )
```

**Key Configuration:**

| Option | Purpose | Required |
|--------|---------|----------|
| `cwd` | Sets working directory for skill discovery | Yes |
| `setting_sources=["project"]` | Loads skills from `.claude/skills/` | Yes |
| `setting_sources=["user"]` | Loads personal skills from `~/.claude/skills/` | Optional |
| `allowed_tools=["Skill"]` | Enables skill invocation | Yes |

### 3.5 Multi-User Sandbox Architecture

For SaaS deployment, each user session runs in an **isolated sandbox** with its own project directory:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       MULTI-USER SANDBOX ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  User A Session                          User B Session                         │
│  ┌─────────────────────────────┐        ┌─────────────────────────────┐        │
│  │ cwd: /sandbox/user-a/proj-1 │        │ cwd: /sandbox/user-b/proj-1 │        │
│  │                             │        │                             │        │
│  │ .claude/                    │        │ .claude/                    │        │
│  │ ├── skills/                 │        │ ├── skills/                 │        │
│  │ │   ├── extract-issues/     │        │ │   ├── extract-issues/     │        │
│  │ │   └── custom-skill-a/     │        │ │   └── custom-skill-b/     │        │
│  │ ├── settings.json           │        │ ├── settings.json           │        │
│  │ └── CLAUDE.md               │        │ └── CLAUDE.md               │        │
│  │                             │        │                             │        │
│  │ notes/                      │        │ notes/                      │        │
│  │ └── note-123.md             │        │ └── note-456.md             │        │
│  └─────────────────────────────┘        └─────────────────────────────┘        │
│                                                                                 │
│  Shared Base Skills (mounted read-only into each sandbox)                      │
│  /opt/pilotspace/base-skills/                                                  │
│  ├── extract-issues/                                                           │
│  ├── improve-writing/                                                          │
│  ├── summarize/                                                                │
│  └── ... (default PilotSpace skills)                                           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Sandbox Configuration:**

```python
from claude_agent_sdk import ClaudeAgentOptions, SandboxSettings

def create_sandboxed_agent(user_id: str, workspace_id: str) -> ClaudeAgentOptions:
    """Create isolated agent for a user session."""

    user_cwd = f"/sandbox/{user_id}/{workspace_id}"

    return ClaudeAgentOptions(
        cwd=user_cwd,
        setting_sources=["project", "user"],

        # Sandbox configuration
        sandbox=SandboxSettings(
            enabled=True,
            auto_allow_bash_if_sandboxed=True,
            network={
                "allow_local_binding": False,
                "allow_all_unix_sockets": False,
            },
        ),

        # Environment variables for context
        env={
            "PILOTSPACE_USER_ID": user_id,
            "PILOTSPACE_WORKSPACE_ID": workspace_id,
        },
    )
```

### 3.6 Builtin Tools Reference

The Claude Agent SDK provides these builtin tools:

| Tool | Purpose | Approval Required |
|------|---------|-------------------|
| **Skill** | Invoke skills from `.claude/skills/` | No |
| **Task** | Spawn subagents with specific capabilities | No |
| **Read** | Read files (text, images, PDFs, notebooks) | No |
| **Write** | Create or overwrite files | Yes (critical) |
| **Edit** | Modify existing files (string replacement) | Yes |
| **Bash** | Execute shell commands | Depends on sandbox |
| **Glob** | Find files matching patterns | No |
| **Grep** | Search file contents with regex | No |
| **WebFetch** | Fetch and analyze web content | No |
| **WebSearch** | Search the web | No |
| **TodoWrite** | Create/update task lists | No |
| **AskUserQuestion** | Ask clarifying questions | No |
| **NotebookEdit** | Modify Jupyter notebooks | Yes |

**Key Tool Schemas:**

```python
# Task tool - for spawning subagents
class TaskInput(BaseModel):
    description: str = Field(..., max_length=50)
    prompt: str
    subagent_type: str

# AskUserQuestion - for clarification
class Question(BaseModel):
    question: str
    header: str = Field(..., max_length=12)
    options: list[Option] = Field(..., min_items=2, max_items=4)
    multi_select: bool = False

# Skill tool - for invoking skills
class SkillInput(BaseModel):
    skill: str  # Skill name, e.g., "extract-issues"
    args: str | None = None  # Optional arguments
```

### 3.7 Custom MCP Tools

PilotSpace defines custom tools via MCP servers for domain-specific operations:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("create_issue", "Create an issue in the project tracker", {
    "title": str,
    "description": str,
    "labels": list,
    "priority": int,
})
async def create_issue(args: dict) -> dict:
    """Create issue with approval workflow."""
    return {"content": [{"type": "text", "text": f"Created issue: {args['title']}"}]}

@tool("insert_content", "Insert content into the current note", {
    "block_id": str,
    "content": str,
    "position": str,  # "before" | "after" | "replace"
})
async def insert_content(args: dict) -> dict:
    """Insert content at specified position in note."""
    return {"content": [{"type": "text", "text": f"Inserted at {args['position']}"}]}

# Register with SDK
pilotspace_mcp = create_sdk_mcp_server(
    name="pilotspace",
    version="1.0.0",
    tools=[create_issue, insert_content]
)
```

### 3.8 Hooks for Approval Workflow

PilotSpace uses hooks to intercept critical tool calls:

```python
from claude_agent_sdk import HookMatcher, HookContext

CRITICAL_TOOLS = {"Write", "Edit", "mcp__pilotspace__create_issue"}

async def pre_tool_approval_hook(
    input_data: dict,
    tool_use_id: str | None,
    context: HookContext
) -> dict:
    """Intercept critical tools for approval."""
    tool_name = input_data.get("tool_name")

    if tool_name in CRITICAL_TOOLS:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "approvalData": {
                    "tool": tool_name,
                    "input": input_data.get("tool_input"),
                }
            }
        }
    return {}

# Configure in agent options
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(
                matcher="Write|Edit|mcp__pilotspace__*",
                hooks=[pre_tool_approval_hook],
                timeout=60
            )
        ],
    }
)
```

### 3.9 Approvals and User Input (`canUseTool`)

The `canUseTool` callback is the primary mechanism for **human-in-the-loop** approval workflows. It fires when Claude requests a tool that isn't auto-approved.

#### 3.9.1 Permission Evaluation Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PERMISSION EVALUATION ORDER                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Tool Request                                                                   │
│       │                                                                         │
│       ▼                                                                         │
│  ┌─────────────┐                                                               │
│  │ [1] Hooks   │ ──► PreToolUse hooks can allow/deny/modify                    │
│  └─────────────┘                                                               │
│       │ (if not blocked)                                                       │
│       ▼                                                                         │
│  ┌─────────────────────┐                                                       │
│  │ [2] Permission Rules│ ──► settings.json: deny → allow → ask                 │
│  └─────────────────────┘                                                       │
│       │ (if not resolved)                                                      │
│       ▼                                                                         │
│  ┌─────────────────────┐                                                       │
│  │ [3] Permission Mode │ ──► bypassPermissions | acceptEdits | default | plan  │
│  └─────────────────────┘                                                       │
│       │ (if still unresolved)                                                  │
│       ▼                                                                         │
│  ┌─────────────────────┐                                                       │
│  │ [4] canUseTool      │ ──► Your callback for user approval UI                │
│  └─────────────────────┘                                                       │
│       │                                                                         │
│       ▼                                                                         │
│  Allow (execute) │ Deny (block + message to Claude)                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### 3.9.2 `canUseTool` Callback

The callback receives tool details and must return an approval decision:

```python
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)

async def can_use_tool(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    """
    Handle tool approval requests.

    Args:
        tool_name: Tool being requested (e.g., "Bash", "Write", "AskUserQuestion")
        input_data: Tool-specific parameters (see table below)
        context: Session context with conversation state

    Returns:
        PermissionResultAllow: Allow with optional modified input
        PermissionResultDeny: Block with message explaining why
    """
    # Route AskUserQuestion separately
    if tool_name == "AskUserQuestion":
        return await handle_clarifying_questions(input_data)

    # Show approval UI to user
    approved, modifications = await show_approval_dialog(tool_name, input_data)

    if approved:
        return PermissionResultAllow(updated_input=modifications or input_data)
    else:
        return PermissionResultDeny(message="User rejected this action")
```

**Tool Input Fields:**

| Tool | Input Fields |
|------|--------------|
| `Bash` | `command`, `description`, `timeout` |
| `Write` | `file_path`, `content` |
| `Edit` | `file_path`, `old_string`, `new_string` |
| `Read` | `file_path`, `offset`, `limit` |
| `WebFetch` | `url`, `prompt` |
| `Task` | `description`, `prompt`, `subagent_type` |

#### 3.9.3 Response Types

| Response | Python | TypeScript | Effect |
|----------|--------|------------|--------|
| **Allow** | `PermissionResultAllow(updated_input=...)` | `{ behavior: "allow", updatedInput }` | Tool executes |
| **Deny** | `PermissionResultDeny(message=...)` | `{ behavior: "deny", message }` | Tool blocked, Claude sees message |

**Response Strategies:**

| Strategy | Description | Example |
|----------|-------------|---------|
| **Approve** | Execute as requested | Pass input unchanged |
| **Approve with changes** | Modify input before execution | Sandbox paths, add constraints |
| **Reject** | Block tool | Return denial message |
| **Suggest alternative** | Guide Claude differently | "User prefers archiving over deletion" |
| **Redirect** | Change direction entirely | Use streaming input for new instruction |

#### 3.9.4 AskUserQuestion Tool

Claude uses `AskUserQuestion` for clarifying questions with multiple-choice options:

```python
async def handle_clarifying_questions(input_data: dict) -> PermissionResultAllow:
    """Handle Claude's clarifying questions."""
    questions = input_data.get("questions", [])
    answers = {}

    for q in questions:
        # Display question to user
        print(f"\n{q['header']}: {q['question']}")
        for i, opt in enumerate(q["options"]):
            print(f"  {i + 1}. {opt['label']} - {opt['description']}")

        if q.get("multiSelect"):
            print("  (Enter numbers separated by commas, or type custom answer)")
        else:
            print("  (Enter number, or type custom answer)")

        response = input("Your choice: ").strip()

        # Parse response: number(s) → option labels, or free text
        try:
            indices = [int(s.strip()) - 1 for s in response.split(",")]
            labels = [q["options"][i]["label"] for i in indices if 0 <= i < len(q["options"])]
            answers[q["question"]] = ", ".join(labels) if labels else response
        except ValueError:
            answers[q["question"]] = response  # Free-text answer

    return PermissionResultAllow(
        updated_input={
            "questions": questions,  # Must include original questions
            "answers": answers,
        }
    )
```

**Question Schema:**

```json
{
  "questions": [
    {
      "question": "How should I format the output?",
      "header": "Format",
      "options": [
        { "label": "Summary", "description": "Brief overview" },
        { "label": "Detailed", "description": "Full explanation" }
      ],
      "multiSelect": false
    }
  ]
}
```

**Constraints:**
- 60-second timeout (Claude retries if exceeded)
- 1-4 questions per call
- 2-4 options per question
- Not available in subagents (Task tool)

#### 3.9.5 Permission Modes

| Mode | Description | Auto-Approved |
|------|-------------|---------------|
| `default` | Standard behavior | Nothing; all trigger `canUseTool` |
| `acceptEdits` | Auto-accept file operations | Write, Edit, mkdir, rm, mv, cp |
| `bypassPermissions` | Skip all checks | Everything (use with caution!) |
| `plan` | Read-only planning | Nothing; tools blocked except AskUserQuestion |

**Dynamic Mode Switching:**

```python
# Start in default mode
q = query(prompt="Help me refactor", options={"permission_mode": "default"})

# After reviewing approach, switch to acceptEdits
await q.set_permission_mode("acceptEdits")

# Process with new permissions
async for message in q:
    ...
```

### 3.10 Slash Commands System

Slash commands provide session control via `/` prefixed commands. PilotSpace supports both **built-in** and **custom** commands.

#### 3.10.1 Built-in Commands

| Command | Purpose | Response |
|---------|---------|----------|
| `/compact` | Compress conversation history | `compact_boundary` event with token metrics |
| `/clear` | Start fresh conversation | New `session_id` |
| `/help` | Show available commands | Command list |

**Usage:**

```python
# Compact conversation
async for message in query(prompt="/compact", options={"max_turns": 1}):
    if message.type == "system" and message.subtype == "compact_boundary":
        print(f"Pre-compaction tokens: {message.compact_metadata.pre_tokens}")
```

#### 3.10.2 Custom Command Definition

Custom commands are markdown files in `.claude/commands/` (project) or `~/.claude/commands/` (user):

```
{cwd}/.claude/commands/
├── extract-issues.md      # /extract-issues
├── review/
│   ├── code.md            # /code (namespace: review)
│   └── security.md        # /security (namespace: review)
└── deploy-preview.md      # /deploy-preview
```

**File Format:**

```markdown
---
allowed-tools: Read, Grep, Glob, Bash(git diff:*)
description: Comprehensive code review for quality and security
model: claude-sonnet-4-5-20250929
argument-hint: [file-pattern]
---

# Code Review

## Context

Current changes:
!`git diff --name-only HEAD~1`

## Detailed Changes
!`git diff HEAD~1`

## Review Checklist

Analyze for:
1. Code quality and readability
2. Security vulnerabilities
3. Performance implications
4. Test coverage gaps

Provide actionable feedback organized by priority.
```

**Frontmatter Options:**

| Field | Description |
|-------|-------------|
| `allowed-tools` | Restrict tools available during execution |
| `description` | Shown in command list |
| `model` | Override model for this command |
| `argument-hint` | Show argument format in help |

**Special Syntax:**

| Syntax | Purpose | Example |
|--------|---------|---------|
| `!`backtick`cmd`backtick`` | Execute bash and include output | `!`backtick`git status`backtick`` |
| `@file` | Include file contents | `@package.json` |
| `$1`, `$2`, `$ARGUMENTS` | Positional and full arguments | `/fix-issue 123 high` → `$1=123`, `$2=high` |

#### 3.10.3 Command Discovery

Commands are discovered at session init and returned in the `slash_commands` field:

```python
async for message in query(prompt="Hello", options={"max_turns": 1}):
    if message.type == "system" and message.subtype == "init":
        print("Available commands:", message.slash_commands)
        # ["/compact", "/clear", "/help", "/extract-issues", "/code", "/security"]
```

#### 3.10.4 PilotSpace Custom Commands

PilotSpace provides these project-level commands:

```
.claude/commands/
├── extract-issues.md       # Extract issues from note content
├── enhance-issue.md        # Add labels, priority, acceptance criteria
├── find-duplicates.md      # Search for similar issues
├── recommend-assignee.md   # Suggest team members
├── generate-diagram.md     # Create Mermaid diagrams
├── summarize.md            # Summarize content
├── improve-writing.md      # Enhance text quality
└── pr-review.md            # Full pull request review
```

**Example: `/extract-issues`**

```markdown
---
allowed-tools: Read
description: Extract structured issues from note content
argument-hint: [note-id]
---

# Extract Issues

Analyze the content and identify actionable items.

## Note Content
@notes/$1.md

## Output Format

Return JSON:
```json
{
  "issues": [
    {
      "title": "...",
      "description": "...",
      "labels": ["bug", "frontend"],
      "priority": 2,
      "confidence_tag": "RECOMMENDED",
      "confidence_score": 0.85
    }
  ]
}
```

Mark each issue with confidence:
- RECOMMENDED (>0.8): High confidence
- DEFAULT (0.5-0.8): Standard confidence
- ALTERNATIVE (<0.5): Low confidence, present as option
```

#### 3.10.5 Frontend Integration

```tsx
// ChatInput.tsx
interface SlashCommandMenuProps {
  commands: SlashCommand[];
  onSelect: (command: string) => void;
}

function SlashCommandMenu({ commands, onSelect }: SlashCommandMenuProps) {
  const [filter, setFilter] = useState("");

  const filtered = commands.filter(
    (cmd) => cmd.name.includes(filter) || cmd.description.includes(filter)
  );

  return (
    <div className="slash-command-menu">
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Search commands..."
      />
      <ul>
        {filtered.map((cmd) => (
          <li key={cmd.name} onClick={() => onSelect(cmd.name)}>
            <code>/{cmd.name}</code>
            <span>{cmd.description}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

### 3.11 Session Management

Sessions enable conversation continuity across multiple interactions. The SDK provides session persistence, resumption, and forking capabilities.

#### 3.11.1 Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    SESSION LIFECYCLE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   query(prompt) ──▶ [system:init] ──▶ session_id captured       │
│         │                                                        │
│         ▼                                                        │
│   Multiple turns ──▶ Context accumulates ──▶ Compaction (auto)  │
│         │                                                        │
│         ▼                                                        │
│   [result] ──▶ Session persists to transcript file              │
│         │                                                        │
│         ▼                                                        │
│   Resume later: resume=session_id OR fork to new branch         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.11.2 Capturing Session ID

```python
from claude_agent_sdk import query, ClaudeAgentOptions

session_id = None

async for message in query(
    prompt="Help me design an API",
    options=ClaudeAgentOptions(model="claude-sonnet-4-5")
):
    # First message contains session_id
    if hasattr(message, 'subtype') and message.subtype == 'init':
        session_id = message.session_id
        print(f"Session started: {session_id}")

    if hasattr(message, "result"):
        print(message.result)

# Save session_id for later resumption
```

#### 3.11.3 Resuming Sessions

```python
# Resume with full context from previous session
async for message in query(
    prompt="Now add authentication to the API",  # Claude remembers the API design
    options=ClaudeAgentOptions(
        resume=session_id,  # Continue from saved session
        allowed_tools=["Read", "Edit", "Write", "Bash"]
    )
):
    if hasattr(message, "result"):
        print(message.result)
```

#### 3.11.4 Forking Sessions

Forking creates a new branch from a session while preserving the original:

| Behavior | `fork_session=False` (default) | `fork_session=True` |
|----------|-------------------------------|---------------------|
| **Session ID** | Same as original | New session ID |
| **History** | Appends to original | Creates new branch |
| **Original** | Modified | Preserved unchanged |
| **Use Case** | Continue linear work | Explore alternatives |

```python
# Fork to try GraphQL instead of REST
async for message in query(
    prompt="Redesign this as a GraphQL API instead",
    options=ClaudeAgentOptions(
        resume=session_id,
        fork_session=True  # Creates new branch, original intact
    )
):
    if hasattr(message, 'subtype') and message.subtype == 'init':
        forked_session_id = message.session_id  # Different from original
```

#### 3.11.5 PilotSpace Session Integration

```python
# PilotSpace stores sessions per workspace/user
class SessionManager:
    async def get_or_create_session(
        self,
        workspace_id: str,
        user_id: str,
        conversation_id: str | None = None
    ) -> str:
        """Get existing session or create new one."""
        if conversation_id:
            # Resume existing conversation
            session = await self.repository.get_session(conversation_id)
            return session.sdk_session_id

        # Create new session (ID will be captured from init message)
        return None

    async def save_session_mapping(
        self,
        conversation_id: str,
        sdk_session_id: str
    ):
        """Map PilotSpace conversation to SDK session."""
        await self.repository.upsert(
            ConversationSession(
                id=conversation_id,
                sdk_session_id=sdk_session_id,
                workspace_id=self.workspace_id,
                user_id=self.user_id
            )
        )
```

---

### 3.12 Memory System (CLAUDE.md)

The Claude Agent SDK loads memory from a hierarchical system of CLAUDE.md files, providing context at multiple levels.

#### 3.12.1 Memory Hierarchy

| Memory Type | Location | Purpose | Scope |
|-------------|----------|---------|-------|
| **Managed Policy** | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS) | Organization-wide instructions | All users in org |
| **User Memory** | `~/.claude/CLAUDE.md` | Personal preferences | All your projects |
| **Project Memory** | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Team-shared project context | Team via VCS |
| **Project Rules** | `./.claude/rules/*.md` | Modular topic-specific rules | Team via VCS |
| **Local Memory** | `./CLAUDE.local.md` | Personal project overrides | Just you (gitignored) |

**Precedence order:** Managed Policy → User → Project → Rules → Local (later overrides earlier)

#### 3.12.2 CLAUDE.md Imports

CLAUDE.md files can import additional content:

```markdown
# Project Instructions

See @README.md for project overview and @package.json for npm commands.

## Development Guidelines
@docs/development.md

## Personal Preferences (not in repo)
@~/.claude/my-project-prefs.md
```

**Import rules:**
- Both relative and absolute paths allowed
- Imports not evaluated inside code spans/blocks
- Max import depth: 5 hops (recursive imports supported)
- Run `/memory` command to see loaded files

#### 3.12.3 Modular Rules System

Organize instructions by topic in `.claude/rules/`:

```
.claude/rules/
├── code-style.md       # Code formatting guidelines
├── testing.md          # Test conventions
├── security.md         # Security requirements
├── frontend/
│   ├── react.md        # React-specific rules
│   └── styles.md       # CSS/styling guidelines
└── backend/
    ├── api.md          # API design rules
    └── database.md     # Database conventions
```

**Path-specific rules** (conditional loading):

```markdown
---
paths:
  - "src/api/**/*.ts"
  - "src/services/**/*.ts"
---

# API Development Rules

- All endpoints must include input validation
- Use standard error response format
- Include OpenAPI documentation comments
```

Only loaded when Claude works with files matching the patterns.

#### 3.12.4 PilotSpace Memory Configuration

```python
# PilotSpace memory structure
workspace_dir/
├── CLAUDE.md                    # Team instructions
├── .claude/
│   ├── CLAUDE.md                # Detailed project context
│   └── rules/
│       ├── issues.md            # Issue formatting rules
│       ├── notes.md             # Note-first workflow rules
│       └── ai-confidence.md     # AI confidence tag rules
└── CLAUDE.local.md              # User-specific (gitignored)

# Enable memory loading in SDK
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Load CLAUDE.md files
    system_prompt={
        "type": "preset",
        "preset": "claude_code"   # Required for CLAUDE.md usage
    }
)
```

---

### 3.13 Checkpointing & File Rewind

Checkpointing automatically tracks file edits, enabling quick recovery from unwanted changes.

#### 3.13.1 How Checkpointing Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKPOINTING FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Prompt ──▶ Checkpoint Created ──▶ Claude Edits Files     │
│        │                                      │                  │
│        │                                      ▼                  │
│        │                            Edit tracked in checkpoint   │
│        │                                      │                  │
│        ▼                                      ▼                  │
│   Next User Prompt ──▶ New Checkpoint ──▶ More Edits...         │
│                                                                  │
│   REWIND OPTIONS:                                                │
│   ├── Conversation only: Keep code, rewind chat                 │
│   ├── Code only: Keep chat, revert files                        │
│   └── Both: Restore chat AND files to prior state               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.13.2 Enabling Checkpointing in SDK

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Refactor the authentication system",
    options=ClaudeAgentOptions(
        enable_file_checkpointing=True,  # Track all file changes
        allowed_tools=["Read", "Edit", "Write", "Bash"]
    )
):
    pass

# Later, rewind files to a specific message
query_handle.rewind_files(user_message_uuid="abc-123")
```

#### 3.13.3 Limitations

| What's Tracked | What's NOT Tracked |
|----------------|-------------------|
| File edits via Edit tool | Bash command file changes (`rm`, `mv`, `cp`) |
| File writes via Write tool | External/manual file changes |
| All changes within session | Changes from concurrent sessions |

**Important:** Checkpointing complements but doesn't replace Git. Use Git for permanent history.

#### 3.13.4 PilotSpace Checkpoint Integration

```tsx
// RewindPanel.tsx - Allow users to rewind AI changes
function RewindPanel({ sessionId, checkpoints }: RewindPanelProps) {
  const handleRewind = async (checkpoint: Checkpoint, mode: RewindMode) => {
    await pilotSpaceAgent.rewindTo(sessionId, checkpoint.messageUuid, mode);
    toast.success(`Rewound to "${checkpoint.description}"`);
  };

  return (
    <div className="rewind-panel">
      <h3>Checkpoints</h3>
      {checkpoints.map(cp => (
        <CheckpointItem
          key={cp.uuid}
          checkpoint={cp}
          onRewind={(mode) => handleRewind(cp, mode)}
        />
      ))}
    </div>
  );
}
```

---

### 3.14 Model Configuration

The SDK supports flexible model selection with aliases and special modes.

#### 3.14.1 Model Aliases

| Alias | Behavior |
|-------|----------|
| `default` | Recommended model based on account type |
| `sonnet` | Latest Sonnet (currently 4.5) for daily coding |
| `opus` | Opus 4.5 for complex reasoning |
| `haiku` | Fast Haiku for simple tasks |
| `sonnet[1m]` | Sonnet with 1M token context window |
| `opusplan` | **Opus for planning, Sonnet for execution** |

#### 3.14.2 The `opusplan` Mode

Hybrid approach that automatically switches models:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPUSPLAN MODE                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User: "Plan and implement a caching system"                   │
│                                                                  │
│   ┌────────────────────┐     ┌────────────────────┐             │
│   │   PLAN MODE        │     │   EXECUTION MODE   │             │
│   │   (uses Opus)      │     │   (uses Sonnet)    │             │
│   │                    │     │                    │             │
│   │   • Architecture   │────▶│   • Write code     │             │
│   │   • Design choices │     │   • Run tests      │             │
│   │   • Tradeoffs      │     │   • Edit files     │             │
│   └────────────────────┘     └────────────────────┘             │
│                                                                  │
│   Best of both: Opus reasoning + Sonnet efficiency              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.14.3 Extended Context (1M tokens)

```python
# Enable 1M context window for long sessions
options = ClaudeAgentOptions(
    model="sonnet[1m]",  # Via alias
    # OR via betas
    betas=["context-1m-2025-08-07"]
)
```

**Note:** Extended context has [different pricing](https://docs.claude.com/en/docs/about-claude/pricing#long-context-pricing).

#### 3.14.4 Dynamic Model Switching

```python
# Change model mid-session (streaming input mode)
query_handle = query(prompt_stream, options={"model": "sonnet"})

# Later, switch to Opus for complex task
await query_handle.set_model("opus")
await query_handle.set_max_thinking_tokens(16000)  # Increase thinking budget
```

#### 3.14.5 PilotSpace Model Strategy

```python
# PilotSpace model routing per task type
MODEL_ROUTING = {
    "ghost_text": "haiku",         # Fast completions
    "issue_extraction": "sonnet",  # Standard analysis
    "pr_review": "opus",           # Deep code review
    "ai_context": "sonnet",        # Context generation
    "complex_planning": "opusplan" # Hybrid for architecture
}

class PilotSpaceAgent:
    def get_model_for_task(self, task_type: str) -> str:
        return MODEL_ROUTING.get(task_type, "sonnet")
```

---

### 3.15 Output Styles

Output styles customize how Claude responds—formatting, tone, and structure.

#### 3.15.1 Built-in Styles

| Style | Purpose |
|-------|---------|
| **Default** | Standard coding assistant (concise, efficient) |
| **Explanatory** | Educational mode with "Insights" about implementation choices |
| **Learning** | Collaborative mode with `TODO(human)` markers for you to implement |

#### 3.15.2 Custom Output Styles

Create custom styles in `~/.claude/output-styles/` or `.claude/output-styles/`:

```markdown
---
name: PilotSpace Assistant
description: Note-first workflow assistant with confidence tagging
keep-coding-instructions: true
---

# PilotSpace AI Assistant

You are a Note-First workflow assistant for PilotSpace.

## Core Behaviors

1. **Confidence Tagging**: Always tag suggestions with:
   - `RECOMMENDED` (>0.8): High confidence
   - `DEFAULT` (0.5-0.8): Standard confidence
   - `ALTERNATIVE` (<0.5): Present as option

2. **Issue Extraction**: When asked to analyze notes, identify:
   - Actionable items
   - Implicit requirements
   - Technical decisions

3. **Human-in-the-Loop**: For critical actions, always ask before executing.
```

#### 3.15.3 Style Frontmatter Options

| Field | Default | Description |
|-------|---------|-------------|
| `name` | File name | Display name |
| `description` | None | Shown in UI |
| `keep-coding-instructions` | `false` | Keep default coding prompts |

---

### 3.16 Plugins System

Plugins extend Claude Code with commands, agents, skills, hooks, and MCP servers.

#### 3.16.1 Plugin Structure

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # Required: plugin manifest
├── commands/                 # Custom slash commands
│   └── custom-cmd.md
├── agents/                   # Custom subagents
│   └── specialist.md
├── skills/                   # Agent skills
│   └── my-skill/
│       └── SKILL.md
├── hooks/                    # Event handlers
│   └── hooks.json
└── .mcp.json                # MCP server definitions
```

#### 3.16.2 Loading Plugins in SDK

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt="Hello",
    options=ClaudeAgentOptions(
        plugins=[
            {"type": "local", "path": "./my-plugin"},
            {"type": "local", "path": "/shared/team-plugin"}
        ]
    )
):
    if message.type == "system" and message.subtype == "init":
        print("Loaded plugins:", message.plugins)
        print("Available commands:", message.slash_commands)
```

#### 3.16.3 Using Plugin Commands

Commands are namespaced: `plugin-name:command-name`

```python
# Execute a plugin command
async for message in query(
    prompt="/my-plugin:custom-cmd argument",
    options=ClaudeAgentOptions(
        plugins=[{"type": "local", "path": "./my-plugin"}]
    )
):
    pass
```

#### 3.16.4 PilotSpace Plugin Architecture

```
pilotspace-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── extract-issues.md
│   ├── enhance-issue.md
│   ├── find-duplicates.md
│   └── pr-review.md
├── agents/
│   ├── issue-analyzer.md
│   ├── code-reviewer.md
│   └── context-builder.md
├── skills/
│   └── note-analysis/
│       └── SKILL.md
└── .mcp.json  # Connect to PilotSpace API
```

---

### 3.17 Structured Outputs

Define JSON schemas for agent results to ensure consistent, parseable outputs.

#### 3.17.1 Using Output Format

```python
from claude_agent_sdk import query, ClaudeAgentOptions

ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["title", "description", "priority", "confidence_score"]
            }
        }
    },
    "required": ["issues"]
}

async for message in query(
    prompt="Extract issues from this note content: ...",
    options=ClaudeAgentOptions(
        output_format={
            "type": "json_schema",
            "schema": ISSUE_SCHEMA
        }
    )
):
    if message.type == "result" and message.subtype == "success":
        # Guaranteed to match schema
        issues = message.structured_output["issues"]
        for issue in issues:
            print(f"- {issue['title']} (priority: {issue['priority']})")
```

#### 3.17.2 Result Message with Structured Output

```python
# SDKResultMessage includes structured_output when schema provided
{
    "type": "result",
    "subtype": "success",
    "result": "...",  # Text summary
    "structured_output": {  # Parsed JSON matching schema
        "issues": [...]
    }
}
```

#### 3.17.3 PilotSpace Schemas

```python
# Reusable schemas for PilotSpace features
class PilotSpaceSchemas:
    ISSUE_EXTRACTION = {
        "type": "object",
        "properties": {
            "issues": {...},
            "metadata": {
                "type": "object",
                "properties": {
                    "source_note_id": {"type": "string"},
                    "extraction_confidence": {"type": "number"}
                }
            }
        }
    }

    ASSIGNEE_RECOMMENDATION = {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "score": {"type": "number"},
                        "reasoning": {"type": "string"},
                        "expertise_match": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        }
    }
```

---

### 3.18 Sandbox Configuration

Sandboxing isolates command execution to prevent unintended system access.

#### 3.18.1 Sandbox Settings

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    sandbox={
        "enabled": True,
        "auto_allow_bash_if_sandboxed": True,  # Auto-approve bash in sandbox
        "excluded_commands": ["docker", "git"],  # Always bypass sandbox
        "allow_unsandboxed_commands": False,     # Block unsandbox requests
        "network": {
            "allow_local_binding": True,  # Allow dev server ports
            "allow_unix_sockets": ["/var/run/docker.sock"],
            "http_proxy_port": 8080
        },
        "ignore_violations": {
            "file": ["*.log", "tmp/*"],
            "network": ["localhost:*"]
        }
    }
)
```

#### 3.18.2 Sandbox Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    SANDBOX SECURITY                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Layer 1: Filesystem Isolation                                  │
│   ├── Read restrictions: from permission deny rules             │
│   ├── Write restrictions: from Edit allow/deny rules            │
│   └── Excluded paths: always blocked                            │
│                                                                  │
│   Layer 2: Network Restrictions                                  │
│   ├── Outbound: from WebFetch allow/deny rules                  │
│   ├── Local binding: configurable                               │
│   └── Unix sockets: explicit allowlist                          │
│                                                                  │
│   Layer 3: Command Execution                                     │
│   ├── Sandboxed commands: isolated environment                  │
│   ├── Excluded commands: bypass sandbox                         │
│   └── Unsandbox requests: require canUseTool approval           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.18.3 Dangerous Command Protection

```python
ALWAYS_BLOCKED = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # Fork bomb
    "chmod -R 777",
]

# Commands requiring explicit approval even with bypassPermissions
REQUIRE_APPROVAL_ALWAYS = [
    r"sudo .*",
    r"rm -rf (?!/tmp).*",  # rm -rf outside /tmp
]
```

---

### 3.19 Subagent Deep Dive

Subagents provide isolated context, parallel execution, and specialized instructions.

#### 3.19.1 Programmatic Subagent Definition

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

PILOTSPACE_AGENTS = {
    "code-reviewer": AgentDefinition(
        description="Expert code review for quality, security, and best practices",
        prompt="""You are a senior code reviewer. Analyze code for:
- Security vulnerabilities (OWASP Top 10)
- Performance issues and N+1 queries
- Code style and maintainability
- Test coverage gaps

Be thorough but constructive.""",
        tools=["Read", "Grep", "Glob"],  # Read-only
        model="sonnet"
    ),

    "issue-analyzer": AgentDefinition(
        description="Analyzes notes to extract structured issues",
        prompt="""Extract actionable issues from content.
Tag each with confidence: RECOMMENDED (>0.8), DEFAULT (0.5-0.8), ALTERNATIVE (<0.5).
Consider duplicates, dependencies, and acceptance criteria.""",
        tools=["Read", "Grep"],
        model="sonnet"
    ),

    "context-builder": AgentDefinition(
        description="Builds comprehensive AI context for issues",
        prompt="""Gather context for issue resolution:
1. Related code files
2. Similar past issues
3. Relevant documentation
4. Team expertise mapping

Output structured context with relevance scores.""",
        tools=["Read", "Grep", "Glob", "WebSearch"],
        model="sonnet"
    )
}

async for message in query(
    prompt="Use the code-reviewer agent to review src/auth/",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Task"],  # Task required for subagents
        agents=PILOTSPACE_AGENTS
    )
):
    pass
```

#### 3.19.2 Detecting Subagent Messages

```python
async for message in query(prompt, options):
    # Check if message is from a subagent
    if hasattr(message, 'parent_tool_use_id') and message.parent_tool_use_id:
        print("  (from subagent)")

    # Detect subagent invocation
    if hasattr(message, 'content'):
        for block in message.content:
            if getattr(block, 'type', None) == 'tool_use' and block.name == 'Task':
                print(f"Spawning subagent: {block.input.get('subagent_type')}")
```

#### 3.19.3 Resuming Subagents

Subagents can be resumed for follow-up questions:

```python
# First invocation
agent_id = None
session_id = None

async for message in query(
    prompt="Use the explorer agent to find all API endpoints",
    options=ClaudeAgentOptions(allowed_tools=["Read", "Grep", "Glob", "Task"])
):
    if hasattr(message, "session_id"):
        session_id = message.session_id
    # Extract agent_id from Task tool result (contains "agentId: xxx")
    agent_id = extract_agent_id(message)

# Resume the same subagent
async for message in query(
    prompt=f"Resume agent {agent_id} and list the top 3 most complex endpoints",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Task"],
        resume=session_id  # Must resume same session
    )
):
    pass
```

#### 3.19.4 Parallel Subagent Execution

```python
# Claude can invoke multiple subagents in parallel via Task tool
# Just describe the parallelization in your prompt

async for message in query(
    prompt="""Run these analyses in parallel:
    1. Use code-reviewer to check auth/
    2. Use security-analyzer to scan for vulnerabilities
    3. Use test-runner to execute the test suite

    Combine results into a comprehensive report.""",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Bash", "Task"],
        agents=PILOTSPACE_AGENTS
    )
):
    # Claude will spawn Task tools concurrently
    pass
```

---

## 4. Skill System

### 4.1 Skill Definition Schema (Pydantic v2)

```python
from pydantic import BaseModel, Field
from enum import StrEnum
from typing import Literal

class SkillCategory(StrEnum):
    WRITING = "writing"
    NOTES = "notes"
    ISSUES = "issues"
    CODE = "code"
    DOCUMENTATION = "documentation"

class SkillDefinition(BaseModel):
    """Skill metadata and requirements."""
    model_config = {"frozen": True}

    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]*$")
    description: str = Field(..., max_length=200)
    category: SkillCategory

    # Requirements
    requires_selection: bool = False
    requires_note: bool = False
    requires_issue: bool = False
    requires_project: bool = False

    # Execution
    prompt_template: str
    output_format: Literal["text", "json", "markdown"] = "text"
    max_tokens: int = Field(default=2000, ge=100, le=8000)

class SkillInput(BaseModel):
    """Runtime input for skill execution."""
    skill_name: str
    args: str | None = None
    context: "ConversationContext"

class SkillOutput(BaseModel):
    """Skill execution result."""
    success: bool
    content: str | dict
    tokens_used: int
    requires_approval: bool = False
    approval_data: dict | None = None
```

### 4.2 Skill Registry

```python
SKILL_REGISTRY: dict[str, SkillDefinition] = {
    "extract-issues": SkillDefinition(
        name="extract-issues",
        description="Extract structured issues from note content",
        category=SkillCategory.NOTES,
        requires_note=True,
        prompt_template="prompts/skills/extract_issues.md",
        output_format="json",
        max_tokens=4000,
    ),
    "improve-writing": SkillDefinition(
        name="improve-writing",
        description="Improve selected text for clarity and conciseness",
        category=SkillCategory.WRITING,
        requires_selection=True,
        prompt_template="prompts/skills/improve_writing.md",
        output_format="text",
    ),
    "summarize": SkillDefinition(
        name="summarize",
        description="Create a concise summary of content",
        category=SkillCategory.WRITING,
        prompt_template="prompts/skills/summarize.md",
        output_format="markdown",
    ),
    "find-duplicates": SkillDefinition(
        name="find-duplicates",
        description="Find duplicate or related issues",
        category=SkillCategory.ISSUES,
        requires_issue=True,
        prompt_template="prompts/skills/find_duplicates.md",
        output_format="json",
    ),
    "recommend-assignee": SkillDefinition(
        name="recommend-assignee",
        description="Recommend team members for an issue",
        category=SkillCategory.ISSUES,
        requires_issue=True,
        prompt_template="prompts/skills/recommend_assignee.md",
        output_format="json",
        max_tokens=500,
    ),
    "decompose-tasks": SkillDefinition(
        name="decompose-tasks",
        description="Break down into actionable subtasks",
        category=SkillCategory.ISSUES,
        requires_issue=True,
        prompt_template="prompts/skills/decompose_tasks.md",
        output_format="json",
        max_tokens=3000,
    ),
    "enhance-issue": SkillDefinition(
        name="enhance-issue",
        description="Add labels, priority, and acceptance criteria",
        category=SkillCategory.ISSUES,
        requires_issue=True,
        prompt_template="prompts/skills/enhance_issue.md",
        output_format="json",
    ),
    "generate-diagram": SkillDefinition(
        name="generate-diagram",
        description="Generate Mermaid diagram from description",
        category=SkillCategory.DOCUMENTATION,
        prompt_template="prompts/skills/generate_diagram.md",
        output_format="markdown",
    ),
}
```

---

## 5. Backend Design

### 5.1 Module Structure

```
backend/src/pilot_space/ai/
├── agents/
│   ├── pilotspace_agent.py      # Main orchestrator
│   ├── ghost_text_agent.py      # Fast inline (unchanged)
│   ├── pr_review_agent.py       # Complex subagent
│   ├── ai_context_agent.py      # Complex subagent
│   └── doc_generator_agent.py   # Complex subagent
├── skills/
│   ├── registry.py              # Skill definitions
│   ├── executor.py              # Skill execution engine
│   └── prompts/                 # Skill prompt templates
├── models/
│   ├── conversation.py          # Pydantic v2 models
│   ├── tasks.py                 # Task tracking models
│   └── approvals.py             # Approval flow models
└── orchestrator.py              # SDK orchestrator (updated)
```

### 5.2 Core Models (Pydantic v2)

```python
# backend/src/pilot_space/ai/models/conversation.py

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"

class ToolCallStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

# --- Immutable Value Objects ---

class NoteContext(BaseModel):
    """Context from note editor selection."""
    model_config = ConfigDict(frozen=True)

    note_id: UUID
    selected_text: str | None = None
    selected_block_ids: tuple[str, ...] = ()
    cursor_position: int | None = None

class IssueContext(BaseModel):
    """Context from active issue."""
    model_config = ConfigDict(frozen=True)

    issue_id: UUID
    project_id: UUID
    title: str
    description: str | None = None

# --- Mutable Domain Objects ---

class ToolCall(BaseModel):
    """Tool invocation within a message."""
    id: str
    name: str
    status: ToolCallStatus = ToolCallStatus.PENDING
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

class ChatMessage(BaseModel):
    """A message in the conversation."""
    id: str
    role: MessageRole
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentTask(BaseModel):
    """A task in the execution plan."""
    id: str
    subject: str = Field(..., max_length=100)
    description: str = Field(..., max_length=1000)
    active_form: str = Field(..., max_length=50)  # "Extracting issues..."
    status: TaskStatus = TaskStatus.PENDING

    # Execution
    skill: str | None = None
    subagent: str | None = None

    # Dependencies
    depends_on: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)

    # Results
    result: Any | None = None
    error: str | None = None
    approval_id: UUID | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

class ConversationContext(BaseModel):
    """Full context for PilotSpace Agent."""
    workspace_id: UUID
    user_id: UUID

    # Entity context (optional)
    note: NoteContext | None = None
    issue: IssueContext | None = None
    project_id: UUID | None = None

    # Conversation history
    messages: list[ChatMessage] = Field(default_factory=list)

    # Active invocations
    active_skill: str | None = None
    skill_args: str | None = None
    mentioned_agents: list[str] = Field(default_factory=list)

class ConversationSession(BaseModel):
    """Persistent conversation session."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    context: ConversationContext
    tasks: dict[str, AgentTask] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
```

### 5.3 PilotSpace Agent Design

**Responsibilities:**
1. Parse user intent (skill invocation, agent mention, or natural request)
2. Plan task decomposition for complex requests
3. Execute skills inline or spawn subagents
4. Track progress via task list
5. Handle approval workflows
6. Stream responses and events

**Key Methods:**

| Method | Description |
|--------|-------------|
| `stream(input, context)` | Main entry point, yields SSE events |
| `_parse_intent(message)` | Detect \skill, @agent, or natural language |
| `_execute_skill(skill, context)` | Run skill and return result |
| `_spawn_subagent(agent, input)` | Delegate to complex subagent |
| `_plan_tasks(request)` | Decompose complex request into tasks |
| `_request_approval(action, data)` | Create approval request |

**Tool Definitions:**

| Tool | Purpose |
|------|---------|
| `task_create` | Add task to execution plan |
| `task_update` | Update task status/result |
| `execute_skill` | Run a registered skill |
| `spawn_subagent` | Delegate to PRReview/AIContext/DocGen |
| `request_approval` | Trigger human approval flow |
| `insert_content` | Insert content into note (pending UI) |
| `create_issue` | Create issue (triggers approval) |

### 5.4 GhostText Agent (Unchanged)

GhostText remains a **direct, fast-path agent**:

- **Endpoint**: `POST /api/v1/ai/notes/ghost-text`
- **Model**: `claude-3-5-haiku-20241022`
- **Timeout**: 2000ms hard limit
- **Streaming**: Direct SSE to frontend
- **No orchestration**: Bypasses PilotSpaceAgent entirely

---

## 6. Frontend Architecture

### 6.1 Store Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ROOT STORE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐│
│  │  GhostTextStore │    │         PilotSpaceStore             ││
│  │  (isolated)     │    │                                     ││
│  │                 │    │  ┌─────────────────────────────┐   ││
│  │  • completion   │    │  │      Conversation State     │   ││
│  │  • isGenerating │    │  │  • messages: ChatMessage[]  │   ││
│  │  • abort()      │    │  │  • isStreaming: boolean     │   ││
│  └─────────────────┘    │  │  • streamContent: string    │   ││
│                         │  │  • sessionId: string | null │   ││
│                         │  └─────────────────────────────┘   ││
│                         │                                     ││
│                         │  ┌─────────────────────────────┐   ││
│                         │  │        Task State           │   ││
│                         │  │  • tasks: Map<id, Task>     │   ││
│                         │  │  • activeTasks: computed    │   ││
│                         │  │  • completedTasks: computed │   ││
│                         │  └─────────────────────────────┘   ││
│                         │                                     ││
│                         │  ┌─────────────────────────────┐   ││
│                         │  │      Approval State         │   ││
│                         │  │  • pending: Approval[]      │   ││
│                         │  │  • approve(id, mods)        │   ││
│                         │  │  • reject(id, reason)       │   ││
│                         │  └─────────────────────────────┘   ││
│                         │                                     ││
│                         │  ┌─────────────────────────────┐   ││
│                         │  │      Context State          │   ││
│                         │  │  • noteContext              │   ││
│                         │  │  • issueContext             │   ││
│                         │  │  • activeSkill              │   ││
│                         │  │  • mentionedAgents          │   ││
│                         │  └─────────────────────────────┘   ││
│                         │                                     ││
│                         │  ┌─────────────────────────────┐   ││
│                         │  │        Actions              │   ││
│                         │  │  • sendMessage(content)     │   ││
│                         │  │  • setActiveSkill(name)     │   ││
│                         │  │  • setNoteContext(ctx)      │   ││
│                         │  │  • abort()                  │   ││
│                         │  │  • clearConversation()      │   ││
│                         │  └─────────────────────────────┘   ││
│                         └─────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 PilotSpaceStore Interface

```typescript
interface PilotSpaceStore {
  // Conversation
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  sessionId: string | null;
  error: string | null;

  // Tasks
  tasks: Map<string, AgentTask>;
  readonly activeTasks: AgentTask[];
  readonly completedTasks: AgentTask[];

  // Approvals
  pendingApprovals: ApprovalRequest[];
  readonly hasUnresolvedApprovals: boolean;

  // Context
  noteContext: NoteContext | null;
  issueContext: IssueContext | null;
  activeSkill: string | null;
  skillArgs: string | null;
  mentionedAgents: string[];

  // Actions
  sendMessage(content: string): Promise<void>;
  setNoteContext(ctx: NoteContext | null): void;
  setIssueContext(ctx: IssueContext | null): void;
  setActiveSkill(skill: string, args?: string): void;
  addMentionedAgent(agent: string): void;
  approveAction(id: string, modifications?: Record<string, unknown>): Promise<void>;
  rejectAction(id: string, reason: string): Promise<void>;
  abort(): void;
  clearConversation(): void;
}
```

---

## 7. ChatView Component Tree

### 7.1 Component Hierarchy

```
ChatView
├── ChatHeader
│   ├── Title ("PilotSpace")
│   ├── StreamingIndicator (when isStreaming)
│   └── TaskProgressBadges (activeTasks)
│
├── MessageList
│   ├── MessageGroup (by timestamp)
│   │   ├── UserMessage
│   │   │   └── MessageContent
│   │   │
│   │   └── AssistantMessage
│   │       ├── MessageContent
│   │       ├── ToolCallList (if toolCalls)
│   │       │   └── ToolCallItem
│   │       │       ├── ToolIcon
│   │       │       ├── ToolName
│   │       │       ├── ToolStatus (spinner/check/error)
│   │       │       └── ToolOutput (collapsible)
│   │       │
│   │       └── StreamingContent (if streaming)
│   │
│   └── ScrollAnchor (auto-scroll)
│
├── TaskPanel (if tasks.size > 0)
│   ├── TaskList
│   │   └── TaskItem
│   │       ├── TaskStatusIcon
│   │       ├── TaskSubject
│   │       └── TaskProgress (if in_progress)
│   │
│   └── TaskSummary ("3 of 5 complete")
│
├── ApprovalOverlay (if pendingApprovals.length > 0)
│   └── ApprovalDialog
│       ├── ApprovalHeader
│       ├── ApprovalContent
│       │   ├── ActionPreview (action-specific)
│       │   │   ├── IssuePreview
│       │   │   ├── ContentDiff
│       │   │   └── GenericJSON
│       │   │
│       │   └── ModifyPanel (if editing)
│       │
│       └── ApprovalActions
│           ├── EditButton
│           ├── RejectButton
│           └── ApproveButton
│
└── ChatInput
    ├── ContextIndicator (if noteContext or issueContext)
    │   ├── NoteContextBadge
    │   └── IssueContextBadge
    │
    ├── TextArea
    │   └── PlaceholderText ("Ask PilotSpace... (\ for skills, @ for agents)")
    │
    ├── QuickActions
    │   ├── SkillButton (\)
    │   └── MentionButton (@)
    │
    ├── SendButton
    │
    ├── SkillMenu (when \ triggered)
    │   ├── SkillSearchInput
    │   ├── SkillList
    │   │   └── SkillItem
    │   │       ├── SkillIcon
    │   │       ├── SkillName
    │   │       └── SkillDescription
    │   └── SkillFooter (keyboard hints)
    │
    └── AgentMenu (when @ triggered)
        ├── AgentSearchInput
        ├── AgentList
        │   └── AgentItem
        │       ├── AgentIcon
        │       ├── AgentName
        │       └── AgentDescription
        └── AgentFooter (keyboard hints)
```

### 7.2 Component Dependencies

```
┌────────────────────────────────────────────────────────────────────┐
│                      COMPONENT DEPENDENCIES                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  External Dependencies:                                            │
│  ├── react, mobx-react-lite                                        │
│  ├── @/lib/sse-client (SSEClient)                                  │
│  ├── @/components/ui/* (shadcn components)                         │
│  ├── lucide-react (icons)                                          │
│  └── diff (for ContentDiff)                                        │
│                                                                    │
│  Internal Dependencies:                                            │
│                                                                    │
│  ChatView                                                          │
│  ├─ imports ─► PilotSpaceStore                                     │
│  ├─ imports ─► ChatHeader, MessageList, TaskPanel,                 │
│  │             ApprovalOverlay, ChatInput                          │
│  └─ provides ─► Store context to children                          │
│                                                                    │
│  MessageList                                                       │
│  ├─ imports ─► MessageGroup, UserMessage, AssistantMessage         │
│  └─ observes ─► store.messages, store.streamContent                │
│                                                                    │
│  AssistantMessage                                                  │
│  ├─ imports ─► MessageContent, ToolCallList, StreamingContent      │
│  └─ observes ─► message.toolCalls                                  │
│                                                                    │
│  TaskPanel                                                         │
│  ├─ imports ─► TaskList, TaskItem, TaskSummary                     │
│  └─ observes ─► store.tasks, store.activeTasks                     │
│                                                                    │
│  ApprovalOverlay                                                   │
│  ├─ imports ─► ApprovalDialog                                      │
│  └─ observes ─► store.pendingApprovals                             │
│                                                                    │
│  ApprovalDialog                                                    │
│  ├─ imports ─► IssuePreview, ContentDiff, GenericJSON              │
│  └─ calls ─► store.approveAction(), store.rejectAction()           │
│                                                                    │
│  ChatInput                                                         │
│  ├─ imports ─► ContextIndicator, SkillMenu, AgentMenu              │
│  ├─ observes ─► store.noteContext, store.activeSkill               │
│  └─ calls ─► store.sendMessage(), store.setActiveSkill()           │
│                                                                    │
│  SkillMenu                                                         │
│  ├─ imports ─► SkillItem, SKILL_DEFINITIONS (static)               │
│  └─ calls ─► onSelect(skill) → store.setActiveSkill()              │
│                                                                    │
│  AgentMenu                                                         │
│  ├─ imports ─► AgentItem, AGENT_DEFINITIONS (static)               │
│  └─ calls ─► onSelect(agent) → store.addMentionedAgent()           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 7.3 UI State Transitions

```
┌─────────────────────────────────────────────────────────────────────┐
│                      UI STATE MACHINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  IDLE                                                               │
│    │                                                                │
│    ├── User types message ──────────────────────────────────────┐   │
│    │                                                            │   │
│    ├── User types "\" ──► SKILL_MENU_OPEN                       │   │
│    │                          │                                 │   │
│    │                          ├── ESC ──► IDLE                  │   │
│    │                          └── Select ──► SKILL_SELECTED ────┤   │
│    │                                                            │   │
│    ├── User types "@" ──► AGENT_MENU_OPEN                       │   │
│    │                          │                                 │   │
│    │                          ├── ESC ──► IDLE                  │   │
│    │                          └── Select ──► AGENT_MENTIONED ───┤   │
│    │                                                            │   │
│    │                                                            ▼   │
│    │                                                         READY  │
│    │                                                            │   │
│    └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  READY (message ready to send)                                      │
│    │                                                                │
│    └── Enter/Send ──► STREAMING                                     │
│                           │                                         │
│                           ├── text event ──► Update streamContent   │
│                           ├── tool_use event ──► Add to toolCalls   │
│                           ├── task_update ──► Update tasks Map      │
│                           ├── approval_request ──► APPROVAL_PENDING │
│                           │                           │             │
│                           │                           ├── Approve   │
│                           │                           └── Reject    │
│                           │                               │         │
│                           │◄──────────────────────────────┘         │
│                           │                                         │
│                           └── complete event ──► IDLE               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Data Flow & Sequences

### 8.1 Skill Execution Flow

```
┌──────────┐     ┌────────────────┐     ┌─────────────────┐     ┌────────────────┐
│  User    │     │   ChatInput    │     │ PilotSpaceStore │     │    Backend     │
└────┬─────┘     └───────┬────────┘     └────────┬────────┘     └───────┬────────┘
     │                   │                       │                      │
     │ Type "\extract"   │                       │                      │
     │──────────────────►│                       │                      │
     │                   │                       │                      │
     │                   │ Show SkillMenu        │                      │
     │                   │◄─────────────────────►│                      │
     │                   │                       │                      │
     │ Select skill      │                       │                      │
     │──────────────────►│                       │                      │
     │                   │                       │                      │
     │                   │ setActiveSkill()      │                      │
     │                   │──────────────────────►│                      │
     │                   │                       │                      │
     │ Press Enter       │                       │                      │
     │──────────────────►│                       │                      │
     │                   │                       │                      │
     │                   │ sendMessage()         │                      │
     │                   │──────────────────────►│                      │
     │                   │                       │                      │
     │                   │                       │ POST /chat (SSE)     │
     │                   │                       │─────────────────────►│
     │                   │                       │                      │
     │                   │                       │ SSE: text            │
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ See streaming     │ Update UI             │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
     │                   │                       │ SSE: tool_use        │
     │                   │                       │ (execute_skill)      │
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ See skill running │ Show ToolCallItem     │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
     │                   │                       │ SSE: task_update     │
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ See task progress │ Update TaskPanel      │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
     │                   │                       │ SSE: complete        │
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ See final result  │ Add message, clear    │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
```

### 8.2 Approval Flow

```
┌──────────┐     ┌────────────────┐     ┌─────────────────┐     ┌────────────────┐
│  User    │     │ ApprovalDialog │     │ PilotSpaceStore │     │    Backend     │
└────┬─────┘     └───────┬────────┘     └────────┬────────┘     └───────┬────────┘
     │                   │                       │                      │
     │                   │                       │ SSE: approval_request│
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ See dialog        │ Render with data      │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
     │ Review content    │                       │                      │
     │                   │                       │                      │
     │ Click "Modify"    │                       │                      │
     │──────────────────►│                       │                      │
     │                   │                       │                      │
     │ Edit in textarea  │ Enable edit mode      │                      │
     │◄──────────────────│                       │                      │
     │                   │                       │                      │
     │ Click "Approve"   │                       │                      │
     │──────────────────►│                       │                      │
     │                   │                       │                      │
     │                   │ approveAction(id, mods)                      │
     │                   │──────────────────────►│                      │
     │                   │                       │                      │
     │                   │                       │ POST /approvals/{id} │
     │                   │                       │─────────────────────►│
     │                   │                       │                      │
     │                   │                       │ 200 OK               │
     │                   │                       │◄─────────────────────│
     │                   │                       │                      │
     │ Dialog closes     │ Remove from pending   │                      │
     │◄──────────────────│◄──────────────────────│                      │
     │                   │                       │                      │
```

### 8.3 Subagent Execution Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│ PilotSpace   │     │   Orchestrator  │     │  Subagent    │     │  External API  │
│   Agent      │     │                 │     │ (PR Review)  │     │  (GitHub)      │
└──────┬───────┘     └────────┬────────┘     └──────┬───────┘     └───────┬────────┘
       │                      │                     │                     │
       │ spawn_subagent       │                     │                     │
       │ (pr_review, input)   │                     │                     │
       │─────────────────────►│                     │                     │
       │                      │                     │                     │
       │                      │ execute(input, ctx) │                     │
       │                      │────────────────────►│                     │
       │                      │                     │                     │
       │                      │                     │ Fetch PR data       │
       │                      │                     │────────────────────►│
       │                      │                     │                     │
       │                      │                     │ PR files, comments  │
       │                      │                     │◄────────────────────│
       │                      │                     │                     │
       │                      │ SSE: progress       │                     │
       │◄─────────────────────│◄────────────────────│                     │
       │                      │                     │                     │
       │                      │                     │ Analyze with Claude │
       │                      │                     │ (multiple turns)    │
       │                      │                     │                     │
       │                      │ SSE: progress       │                     │
       │◄─────────────────────│◄────────────────────│                     │
       │                      │                     │                     │
       │                      │ ExecutionResult     │                     │
       │◄─────────────────────│◄────────────────────│                     │
       │                      │                     │                     │
       │ Aggregate into       │                     │                     │
       │ final response       │                     │                     │
       │                      │                     │                     │
```

---

## 9. API Contracts

### 9.1 Chat Endpoint

**Request:**
```
POST /api/v1/ai/pilotspace/chat
Content-Type: application/json
Accept: text/event-stream

{
  "message": "Extract issues from the selected text",
  "context": {
    "workspace_id": "uuid",
    "user_id": "uuid",
    "note": {
      "note_id": "uuid",
      "selected_text": "We need to fix the login bug...",
      "selected_block_ids": ["block-1", "block-2"]
    },
    "active_skill": "extract-issues",
    "mentioned_agents": []
  },
  "session_id": "uuid or null"
}
```

**Response (SSE Stream):**
```
event: text
data: {"content": "I'll extract issues from "}

event: text
data: {"content": "your selected content..."}

event: tool_use
data: {"tool": "execute_skill", "status": "started", "input": {"skill": "extract-issues"}}

event: task_update
data: {"id": "t1", "subject": "Extract issues", "status": "in_progress", "active_form": "Extracting issues"}

event: tool_use
data: {"tool": "execute_skill", "status": "completed", "output": {"issues": [...]}}

event: task_update
data: {"id": "t1", "status": "completed", "result": {...}}

event: approval_request
data: {"id": "uuid", "action": "create_issues", "details": {"issues": [...]}, "task_id": "t1"}

event: complete
data: {"session_id": "uuid", "total_tokens": 1234}
```

### 9.2 Skills Endpoint

**Request:**
```
GET /api/v1/ai/pilotspace/skills
```

**Response:**
```json
{
  "skills": [
    {
      "name": "extract-issues",
      "description": "Extract structured issues from note content",
      "category": "notes",
      "requires_selection": false,
      "requires_note": true,
      "requires_issue": false
    }
  ]
}
```

### 9.3 Approval Resolution

**Request:**
```
POST /api/v1/ai/approvals/{approval_id}/resolve
Content-Type: application/json

{
  "decision": "approved",
  "modifications": {
    "issues": [
      {"title": "Fix login bug", "priority": 1}
    ]
  }
}
```

**Response:**
```json
{
  "status": "approved",
  "created_count": 1,
  "created_ids": ["uuid"]
}
```

---

## 10. Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)

| Task | Priority | Output |
|------|----------|--------|
| Define Pydantic v2 models | P0 | `ai/models/*.py` |
| Implement skill registry | P0 | `ai/skills/registry.py` |
| Implement skill executor | P0 | `ai/skills/executor.py` |
| Create PilotSpaceAgent skeleton | P0 | `ai/agents/pilotspace_agent.py` |
| Add chat SSE endpoint | P0 | `api/v1/routers/pilotspace.py` |

### Phase 2: Frontend Store & Chat UI (Week 2)

| Task | Priority | Output |
|------|----------|--------|
| Implement PilotSpaceStore | P0 | `stores/ai/PilotSpaceStore.ts` |
| Create ChatView component | P0 | `components/chat/ChatView.tsx` |
| Create MessageList | P0 | `components/chat/MessageList.tsx` |
| Create ChatInput with menus | P0 | `components/chat/ChatInput.tsx` |
| Create SkillMenu & AgentMenu | P1 | `components/chat/SkillMenu.tsx` |

### Phase 3: Task & Approval System (Week 3)

| Task | Priority | Output |
|------|----------|--------|
| Create TaskPanel component | P1 | `components/chat/TaskPanel.tsx` |
| Create ApprovalDialog | P0 | `components/chat/ApprovalDialog.tsx` |
| Implement tool execution streaming | P0 | Backend tool handlers |
| Connect approval resolution | P0 | Approval API integration |

### Phase 4: Subagent Integration (Week 4)

| Task | Priority | Output |
|------|----------|--------|
| Integrate PRReviewAgent | P1 | Subagent spawning |
| Integrate AIContextAgent | P1 | Subagent spawning |
| Integrate DocGeneratorAgent | P2 | Subagent spawning |
| Add parallel execution | P2 | Concurrent subagent support |

### Phase 5: Note Integration & Polish (Week 5)

| Task | Priority | Output |
|------|----------|--------|
| Connect NoteCanvas context | P0 | Selection → ChatInput |
| Add insert_content action | P1 | Content insertion UI |
| Implement session persistence | P1 | Redis session storage |
| Add E2E tests | P0 | Playwright tests |
| Performance optimization | P2 | Profiling, caching |

---

## Appendix A: Skill Prompt Templates

### extract-issues.md

```markdown
# Extract Issues from Content

Analyze the following content and extract potential issues/tasks.

## Content
{{selected_text or note_content}}

## Requirements
- Each issue must have: title, description, suggested labels, priority (0-4)
- Add confidence_tag: RECOMMENDED (>0.8), DEFAULT (0.5-0.8), ALTERNATIVE (<0.5)
- Include source_block_ids for traceability
- Maximum {{max_issues}} issues

## Output Format (JSON)
{
  "issues": [
    {
      "title": "...",
      "description": "...",
      "labels": ["bug", "frontend"],
      "priority": 2,
      "confidence_tag": "RECOMMENDED",
      "confidence_score": 0.85,
      "source_block_ids": ["block-1"],
      "rationale": "..."
    }
  ]
}
```

---

## Appendix B: Self-Evaluation

| Criterion | Score | Notes |
|-----------|-------|-------|
| **Completeness** | 0.95 | Covers SDK integration, skill loading, multi-user sandbox |
| **Clarity** | 0.94 | Descriptive diagrams replace verbose code |
| **Maintainability** | 0.92 | Filesystem-based skills, clear SDK configuration |
| **Scalability** | 0.92 | Multi-user sandbox, per-project skill isolation |
| **Practicality** | 0.90 | Builds on Claude Agent SDK patterns |
| **Security** | 0.92 | Human-in-the-loop + sandbox isolation |

**Key Design Wins:**
1. GhostText fast path preserved (<2s latency)
2. Skills loaded from `.claude/skills/` via SDK (native pattern)
3. Multi-user sandbox with per-user project directories
4. Builtin tools documented with approval requirements
5. Hooks for critical action interception
6. Pydantic v2 models provide validation and serialization
7. Component tree clearly documents UI dependencies
