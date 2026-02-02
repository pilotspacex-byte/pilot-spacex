---
description: Quick development workflow - clarify requirements, load context, plan implementation
---

# Development Workflow

## User Request

```text
$ARGUMENTS
```

---

## Execution Flow

```text
Parse → Discover → [Clarify?] → Load Patterns → Plan → Execute → Validate
```

---

## Step 1: Parse Request

Extract from `$ARGUMENTS`:

| Field | Values |
|-------|--------|
| **Type** | feature \| bugfix \| refactor \| test \| docs |
| **Target** | service/module/file affected |
| **Scope** | specific files or "discover" |
| **Flags** | `--ultrathink` `--expert` `--patterns` `--clarify` |

---

## Step 2: Codebase Discovery

**For complex tasks or large codebase exploration** (preferred):

Use `Task` tool with `component-tracer` agent to trace dependencies and understand components:

```markdown
Task(subagent_type="component-tracer", prompt="Trace [component/service name] and its dependencies")
```

The `component-tracer` agent will provide:

- Component summary with responsibilities
- Full dependency tree (what it imports, what imports it)
- Related tests and configurations
- Integration points with other services

**For simple/focused lookups**:

Use `mcp__serena` tools directly:

```text
mcp__serena__get_symbols_overview  → File structure
mcp__serena__find_symbol           → Locate classes/functions
mcp__serena__search_for_pattern    → Find usage patterns
mcp__serena__find_referencing_symbols → Trace dependencies
```

**Discovery strategy**:

| Scenario | Approach |
|----------|----------|
| Unknown component structure | `component-tracer` agent |
| Cross-service dependencies | `component-tracer` agent |
| Specific symbol lookup | `mcp__serena__find_symbol` |
| Pattern search in known files | `mcp__serena__search_for_pattern` |

**Report findings**:

```markdown
## Codebase Analysis
- **Related Files**: [discovered files]
- **Existing Patterns**: [similar implementations]
- **Dependencies**: [imports/services needed]
- **Integration Points**: [how component connects to others]
```

---

## Step 3: Clarify (If Needed)

**Clarify when ANY apply**:

- Scope boundaries unclear
- Multiple valid approaches exist
- Breaking changes possible
- Security implications unclear
- Missing technical details
- `--clarify` flag provided

**Skip when ALL true**:

- Requirements explicit and complete
- Single obvious implementation
- User said "just do it"

**To clarify**: Use `AskUserQuestion` tool with specific options:

```markdown
Before implementing [task], I need to clarify:

1. [Question]?
   - Option A: [description + tradeoff]
   - Option B: [description + tradeoff]
   - Recommended: [which and why]
```

Alternatively, invoke the `request-clarification-analyzer` skill if available.

---

## Step 4: Load Patterns

**Always load**: `docs/dev-pattern/README.md`

**Task-specific patterns**:

| Task Type | Pattern Files |
|-----------|---------------|
| Repository/Data | 07, 09, 25 |
| Service/Logic | 08, 26, 25 |
| API Endpoint | 27, 26, 13 |
| Database | 09, 05, 28 |
| Testing | 03, 06, 15 |
| Auth/Security | 13, 26, 17 |

**Check pitfalls**: `docs/dev-pattern/35-37-lessons-learned-*.md`

---

## Step 5: Create Plan

Use `TaskCreate` to create actionable tasks:

```markdown
## Implementation: [Task Name]

### Steps
1. [Specific action with file path]
2. [Next action]
3. [Validation step]

### Deliverables
- [ ] [Component/file 1]
- [ ] [Component/file 2]
- [ ] Tests (>95% coverage)
```

**Complexity → Execution**:

| Complexity | Criteria | Action |
|------------|----------|--------|
| **Simple** | 1-2 files, single layer | Execute directly |
| **Complex** | 3+ files, multi-layer, migrations | Use `Task` tool with agent |

**Agent selection**:

| Agent | Use When |
|-------|----------|
| `component-tracer` | **Preferred** for understanding components, tracing dependencies, large codebase |
| `python-pro` | Backend Python implementation |
| `python-architect-advisor` | Architecture decisions, design patterns |
| `database-schema-architect` | Schema design, migrations |
| `Explore` | Quick file pattern searches |
| `Plan` | Complex multi-phase implementation planning |

---

## Step 6: Validate

Run quality gates before completing:

```bash
uv run ruff check --fix . && uv run pyright && pytest --cov-fail-under=95
```

---

## Mode: --ultrathink

Add comprehensive analysis:

1. **Architecture Impact**: Ripple effects, scalability
2. **Edge Cases**: Error scenarios, boundary conditions
3. **Security Review**: Input validation, permissions, data exposure
4. **Performance**: N+1 queries, caching, response time

---

## Mode: --expert

Proactively suggest:

1. **Best Practices**: Industry standards, project conventions
2. **Enhancements**: Optional improvements, tech debt reduction
3. **Alternatives**: 2-3 approaches with tradeoffs and recommendation

---

## Validation Checklist

Before completing, verify:

- [ ] Requirements clarified (or confirmed clear)
- [ ] Related code discovered
- [ ] Patterns loaded
- [ ] Plan created with `TaskCreate`
- [ ] Complexity assessed
- [ ] Quality gates passed
