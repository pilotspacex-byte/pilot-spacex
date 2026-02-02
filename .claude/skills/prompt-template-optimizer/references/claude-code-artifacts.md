# Claude Code Artifacts Reference

Templates and syntax for creating commands, skills, hooks, sub-agents, and CLAUDE.md.

---

## Quick Reference: Artifact Types

| Artifact | Location | Format | Purpose |
|----------|----------|--------|---------|
| Command | `.claude/commands/*.md` | Markdown + YAML | Quick slash commands |
| Skill | `.claude/skills/*/SKILL.md` | Markdown + YAML | Comprehensive capabilities |
| Hook | `.claude/settings.json` | JSON | Event automation |
| Sub-agent | `.claude/agents/*.md` | Markdown + YAML | Specialized AI assistants |
| CLAUDE.md | `./CLAUDE.md` | Markdown | Project instructions |

---

## 1. Commands

### File Location

```
Project: .claude/commands/command-name.md
User:    ~/.claude/commands/command-name.md
```

### Template

```markdown
---
description: {Brief description for menu display}
allowed-tools: {Tool1, Tool2(pattern:*)}
argument-hint: {[arg1] [arg2]}
model: {sonnet|opus|haiku|inherit}
context: {fork}
agent: {general-purpose|Explore|Plan}
---

## {Command Title}

{Instructions for Claude in imperative form.}

### Arguments

- `$ARGUMENTS`: All arguments as single string
- `$1`, `$2`: Individual positional arguments

### Embedded Commands

Current status: !`git status --short`
```

### YAML Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `description` | No | string | Menu display text (max 1024 chars) |
| `allowed-tools` | No | string/list | Tools without permission prompts |
| `argument-hint` | No | string | Shows expected args in autocomplete |
| `model` | No | string | Model override |
| `context` | No | `fork` | Run in isolated context |
| `agent` | No | string | Subagent type when forked |

### Tool Permission Syntax

```yaml
# Exact match
allowed-tools: Read

# Prefix match
allowed-tools: Bash(git:*)

# Multiple tools
allowed-tools: Read, Grep, Bash(npm run:*)

# List format
allowed-tools:
  - Read
  - Grep
  - Bash(npm run:*)
```

### Examples

**Simple Command**:
```markdown
---
description: Run tests with coverage
allowed-tools: Bash(pytest:*)
---

Run tests: `pytest --cov --cov-report=term-missing`
```

**Command with Arguments**:
```markdown
---
description: Review a specific PR
argument-hint: [pr-number]
allowed-tools: Bash(gh pr:*)
---

## Review PR #$1

1. Fetch PR info: `gh pr view $1`
2. Check files changed: `gh pr diff $1 --name-only`
3. Analyze changes and provide feedback
```

**Forked Context Command**:
```markdown
---
description: Deep code exploration
context: fork
agent: Explore
---

Thoroughly explore the codebase to answer: $ARGUMENTS
```

---

## 2. Skills

### Directory Structure

```
.claude/skills/skill-name/
├── SKILL.md              # Required: Main instructions
├── references/           # Optional: Detailed docs
│   ├── api.md
│   └── examples.md
├── assets/               # Optional: Output resources
│   └── template.json
└── scripts/              # Optional: Executable code
    └── validate.py
```

### SKILL.md Template

```markdown
---
name: {lowercase-with-hyphens}
description: This skill should be used when {trigger conditions}. {What it provides}.
allowed-tools: {Read, Grep, Glob}
model: {sonnet|opus|haiku|inherit}
context: {fork}
agent: {general-purpose|Explore|Plan}
user-invocable: {true|false}
skills: {other-skill-1, other-skill-2}
---

# {Skill Title}

{1-2 sentence purpose in imperative form.}

## When to Invoke

- {Trigger condition 1}
- {Trigger condition 2}

## Workflow

### Step 1: {Action}

{Imperative instructions.}

## References

| File | Purpose | When to Load |
|------|---------|--------------|
| `references/X.md` | {Purpose} | {Condition} |

## Assets

| File | Purpose |
|------|---------|
| `assets/Y.json` | {Purpose} |
```

### YAML Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | **Yes** | string | Lowercase, hyphens, max 64 chars |
| `description` | **Yes** | string | When to use (max 1024 chars) |
| `allowed-tools` | No | string/list | Tool permissions |
| `model` | No | string | Model override |
| `context` | No | `fork` | Isolated execution |
| `agent` | No | string | Subagent type |
| `user-invocable` | No | boolean | Show in `/skill-name` menu |
| `skills` | No | string/list | Skills for subagents |

### Progressive Disclosure

Keep SKILL.md under 500 lines. Move details to references:

**SKILL.md** (essential):
```markdown
## Quick Reference

Basic usage: `command input.txt`

For detailed API, see `references/api.md`.
```

**references/api.md** (comprehensive):
```markdown
# Full API Reference

## Function: process()

Parameters:
- input: string - Input file path
- options: dict - Processing options
  - format: "json" | "csv"
  - validate: boolean
...
```

### Best Practices

1. **Description is critical** - Claude discovers skills by description
2. **Use third-person** - "This skill should be used when..."
3. **Keep SKILL.md lean** - Details in references
4. **Bundle scripts** - Execute without loading content
5. **Check into git** - Share with team

---

## 3. Hooks

### Configuration Location

```
Project: .claude/settings.json
User:    ~/.claude/settings.json
Local:   .claude/settings.local.json (git-ignored)
```

### Template

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolName",
        "hooks": [
          {
            "type": "command",
            "command": "bash-command",
            "timeout": 60,
            "once": true
          }
        ]
      }
    ]
  }
}
```

### Hook Events

| Event | Matcher | Purpose |
|-------|---------|---------|
| `PreToolUse` | Yes | Validate/block before tool runs |
| `PostToolUse` | Yes | Auto-format, log after tool |
| `PermissionRequest` | Yes | Auto-approve/deny |
| `UserPromptSubmit` | No | Add context to prompts |
| `Notification` | Yes | Custom alerts |
| `Stop` | No | Force continuation |
| `SubagentStop` | No | Subagent control |
| `SessionStart` | No | Environment setup |
| `SessionEnd` | No | Cleanup |

### Hook Input (stdin JSON)

**PreToolUse - Bash**:
```json
{
  "session_id": "abc123",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm run test",
    "description": "Run tests"
  }
}
```

**PreToolUse - Write**:
```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "..."
  }
}
```

**UserPromptSubmit**:
```json
{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "User's message"
}
```

### Hook Output

**Exit codes**:
- `0`: Success
- `2`: Block (stderr shown to Claude)
- Other: Warning (stderr shown to user)

**JSON Output** (exit 0):
```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow|deny|ask",
    "additionalContext": "Info for Claude"
  },
  "continue": true,
  "suppressOutput": false
}
```

### Examples

**Command Validation**:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/validate-bash.py"
          }
        ]
      }
    ]
  }
}
```

**validate-bash.py**:
```python
#!/usr/bin/env python3
import json, sys

data = json.load(sys.stdin)
cmd = data.get('tool_input', {}).get('command', '')

if 'rm -rf' in cmd:
    print("Blocked: destructive command", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

**Auto-format After Write**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs prettier --write"
          }
        ]
      }
    ]
  }
}
```

**Add Context to Prompts**:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Current branch: '$(git branch --show-current)"
          }
        ]
      }
    ]
  }
}
```

---

## 4. Sub-Agents

### File Location

```
Project: .claude/agents/agent-name.md
User:    ~/.claude/agents/agent-name.md
```

### Template

```markdown
---
name: {agent-name}
description: {When Claude should use this agent}
tools: {Read, Grep, Glob}
disallowedTools: {Write, Edit}
model: {sonnet|opus|haiku|inherit}
permissionMode: {default|acceptEdits|dontAsk|bypassPermissions|plan}
skills: {skill-1, skill-2}
---

{System prompt for the agent.}

## Role

{Agent's expertise and personality.}

## Instructions

{Step-by-step process.}

## Output Format

{Expected response structure.}
```

### YAML Frontmatter Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | **Yes** | string | Agent identifier |
| `description` | **Yes** | string | When to use (trigger) |
| `tools` | No | string/list | Allowed tools (allowlist) |
| `disallowedTools` | No | string/list | Denied tools (denylist) |
| `model` | No | string | Model selection |
| `permissionMode` | No | string | Permission handling |
| `skills` | No | string/list | Skills to load |

### Permission Modes

| Mode | Behavior |
|------|----------|
| `default` | Standard prompts |
| `acceptEdits` | Auto-accept file changes |
| `dontAsk` | Auto-deny unpermitted |
| `bypassPermissions` | Skip all checks |
| `plan` | Read-only mode |

### Built-in Agents

| Agent | Model | Access | Purpose |
|-------|-------|--------|---------|
| `Explore` | Haiku | Read-only | Fast codebase search |
| `Plan` | Inherit | Read-only | Implementation planning |
| `general-purpose` | Inherit | Full | Complex multi-step tasks |

### Examples

**Code Reviewer**:
```markdown
---
name: code-reviewer
description: Expert code review. Use proactively after code changes.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: inherit
---

You are a senior code reviewer. Focus on:
- Security vulnerabilities
- Performance issues
- Code clarity
- Test coverage

## Process

1. Run `git diff` to see changes
2. Analyze each modified file
3. Provide categorized feedback

## Output Format

### Critical Issues
- [file:line] Issue description

### Suggestions
- [file:line] Improvement idea
```

**Test Runner**:
```markdown
---
name: test-runner
description: Run and fix failing tests
tools: Read, Edit, Bash, Grep
permissionMode: acceptEdits
---

You are a test specialist. When tests fail:
1. Identify the failure
2. Find the root cause
3. Fix the code or test
4. Verify the fix
```

---

## 5. CLAUDE.md (System Prompts)

### File Hierarchy

| Scope | Path | Priority |
|-------|------|----------|
| Enterprise | `/etc/claude-code/CLAUDE.md` | Highest |
| Project | `./CLAUDE.md` | High |
| Project Rules | `.claude/rules/*.md` | High |
| User | `~/.claude/CLAUDE.md` | Medium |
| Local | `./CLAUDE.local.md` | Lowest |

### Template

```markdown
# {Project Name}

## Overview

{Brief project description.}

## Architecture

{System design, tiers, communication patterns.}

## Stack

- Language: {Python 3.12+}
- Framework: {FastAPI}
- Database: {PostgreSQL, Redis}

## Code Standards

- {Standard 1}
- {Standard 2}

## Patterns

| Pattern | Usage |
|---------|-------|
| Repository | Data access |
| Service | Business logic |

## Commands

| Command | Purpose |
|---------|---------|
| `{cmd}` | {description} |

## When Stuck

1. {First step}
2. {Second step}
```

### Modular Rules

`.claude/rules/testing.md`:
```markdown
---
paths:
  - "tests/**/*.py"
---

# Testing Rules

- Use pytest
- >95% coverage
- Mock external services
```

### File Imports

```markdown
See @README for overview.
Git workflow: @docs/git-instructions.md
User prefs: @~/.claude/my-preferences.md
```

---

## Prompt Design by Artifact Type

### Command Prompts

**Characteristics**:
- Short, focused tasks
- Often include arguments
- May embed bash commands

**Template**:
```markdown
## Task
{Single clear objective}

## Process
1. {Step using $1 argument}
2. {Step with embedded command}

## Output
{Expected result format}
```

### Skill Prompts

**Characteristics**:
- Comprehensive workflows
- Progressive disclosure
- Multiple supporting files

**Template**:
```markdown
## When to Invoke
{Trigger conditions}

## Workflow
### Phase 1: {Name}
{Steps}

### Phase 2: {Name}
{Steps}

## References
{Links to detailed docs}
```

### Sub-Agent Prompts

**Characteristics**:
- Persona-driven
- Tool-restricted
- Focused expertise

**Template**:
```markdown
## Role
{Expert persona with specific focus}

## Capabilities
{What this agent can do}

## Limitations
{What this agent cannot/should not do}

## Process
{Step-by-step workflow}

## Output Format
{Structured response format}
```

### CLAUDE.md Prompts

**Characteristics**:
- Project-wide context
- Standards and patterns
- Reference material

**Template**:
```markdown
## Project Context
{Business domain, architecture}

## Technical Stack
{Languages, frameworks, tools}

## Standards
{Code quality, testing, docs}

## Patterns
{Common solutions, examples}

## Troubleshooting
{Common issues, solutions}
```

---

## Token Optimization by Artifact

| Artifact | Strategy | Rationale |
|----------|----------|-----------|
| Command | Minimal | Quick execution, low complexity |
| Skill | Progressive | Load details on demand |
| Hook | N/A | JSON config, not prompts |
| Sub-agent | Focused | Persona + process only |
| CLAUDE.md | Structured | Always loaded, keep essential |

### Recommended Lengths

| Artifact | Target | Max |
|----------|--------|-----|
| Command | 50-200 lines | 500 |
| SKILL.md | 100-300 lines | 500 |
| Sub-agent | 50-150 lines | 300 |
| CLAUDE.md | 100-500 lines | 1000 |

---

## Sources

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Claude Code Skills Guide](https://www.anthropic.com/engineering/claude-code-skills)
- [Hooks Reference](https://docs.anthropic.com/claude-code/hooks)
