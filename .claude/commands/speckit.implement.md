---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
handoffs:
  - label: Code Review
    agent: code-review
    prompt: Review implemented changes
    send: false
  - label: Commit Changes
    agent: git-commit-wbs
    prompt: Commit implementation changes
    send: false
  - label: Run Analysis
    agent: speckit.analyze
    prompt: Analyze implementation consistency
    send: true
---

## User Input

```text
$ARGUMENTS
```

Consider user input before proceeding (if not empty). Load `@docs/dev-pattern/README.md` for project rules.

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--interactive` | Prompt for confirmations (checklist, failures) | false |
| `--stop-on-failure` | Halt on first task failure | false |
| `--skip-checklists` | Skip checklist validation entirely | false |
| `--phase {N}` | Execute specific phase only | all |
| `--task T{ID}` | Execute single task | all |
| `--dry-run` | Preview execution plan without changes | false |

---

## Workflow

### Phase 1: Prerequisites

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root.
Parse JSON for `FEATURE_DIR` and `AVAILABLE_DOCS` (use absolute paths).

For single quotes in args like "I'm Groot", use escape syntax: `'I'\''m Groot'` or double-quote.

### Phase 2: Checklist Validation

Skip this phase if `--skip-checklists` flag is set or `FEATURE_DIR/checklists/` does not exist.

**Scan checklist files**:
- Count total items: Lines matching `- [ ]` or `- [X]` or `- [x]`
- Count completed: Lines matching `- [X]` or `- [x]`
- Count incomplete: Lines matching `- [ ]`

**Display status table**:

```text
| Checklist   | Total | Completed | Incomplete | Status   |
|-------------|-------|-----------|------------|----------|
| ux.md       | 12    | 12        | 0          | PASS     |
| test.md     | 8     | 5         | 3          | FAIL     |
| security.md | 6     | 6         | 0          | PASS     |
```

**Behavior**:

| Condition | Default (automatic) | With `--interactive` |
|-----------|---------------------|----------------------|
| All checklists complete | Proceed to Phase 3 | Proceed to Phase 3 |
| Some checklists incomplete | Log warning, proceed | Ask user confirmation |

**Warning format** (automatic mode):
```text
Proceeding with incomplete checklists (use --interactive to prompt)
```

### Phase 3: Load Context

**Required** (from FEATURE_DIR):
- `tasks.md` - Complete task list and execution plan
- `plan.md` - Tech stack, architecture, file structure
- `tasks/*` - Individual task detail files

**Optional** (if exists):
- `data-model.md` - Entities and relationships
- `contracts/` - API specifications and test requirements
- `research.md` - Technical decisions and constraints
- `quickstart.md` - Integration scenarios

### Phase 4: Task Detail Files & Dependency Analysis

**Check for task detail directory** (`FEATURE_DIR/tasks/`):

**Read _INDEX.md** (if exists):
- Task summary table with complexity scores
- Dependency chain and execution order
- Parallel task groups (marked with [P])
- Blocking relationships

**Read _PATTERNS.md** (if exists):
- Pattern mappings per task
- Which `docs/dev-pattern/*.md` files to load before each task

**Task Detail File Structure** (`FEATURE_DIR/tasks/T{ID}.md`):

| Section | Purpose | Usage |
|---------|---------|-------|
| **Complexity Assessment** | Effort estimation (1-20 score) | Prioritize simpler tasks first within parallel groups |
| **Context Loading** | Cross-references to load | Read referenced files before implementing |
| **Objective** | Single sentence goal | Understand what to achieve |
| **Acceptance Criteria** | Measurable checkboxes | Verify each criterion is met |
| **Functionality** | Behavior specification | Understand expected behavior |
| **Dependencies** | blocks/blocked_by/parallel_with | Respect execution order |
| **Dev Patterns** | Pattern files to load | Load patterns before coding |
| **Implementation Guidelines** | Structure and logic flow | Follow the recommended approach |
| **Reference Patterns** | Existing code examples | Copy patterns from references |
| **Troubleshooting** | Common issues and solutions | Debug problems quickly |
| **Validation** | Bash commands to verify | Run validation after completion |
| **AI Implementation Prompt** | Ready-to-use prompt | Use directly for implementation |

### Phase 5: Project Setup Verification

Load ignore patterns from `.specify/references/ignore-patterns.md` based on detected tech stack.

**Detection logic**:
- Git repository: `git rev-parse --git-dir 2>/dev/null`
- Docker: `Dockerfile*` exists or Docker in plan.md
- ESLint: `.eslintrc*` or `eslint.config.*` exists
- Prettier: `.prettierrc*` exists
- Terraform: `*.tf` files exist
- Helm: Helm charts present

**Update rules**:
- If ignore file exists: Verify essential patterns, append missing critical patterns only
- If ignore file missing: Create with full pattern set for detected technology

### Phase 6: Parse Task Structure

Extract from tasks.md and task detail files:

| Field | Description |
|-------|-------------|
| **Task phases** | Setup, Tests, Core, Integration, Polish |
| **blocks** | Tasks that this task blocks |
| **blocked_by** | Tasks that must complete first |
| **parallel_with** | Tasks that can run concurrently (marked [P]) |
| **File paths** | Files to create/modify |
| **Validation criteria** | Acceptance checklists and bash commands |
| **AI prompts** | Implementation prompts for each task |

Use `component-tracer` agent to analyze related components if needed.

### Phase 7: Execute Implementation

**Phase-by-phase execution**:
- Complete each phase before moving to the next
- Respect dependencies: Run sequential tasks in order, parallel tasks [P] can run together
- Follow TDD approach: Execute test tasks before corresponding implementation tasks
- File-based coordination: Tasks affecting the same files run sequentially
- Validation checkpoints: Verify each phase completion before proceeding

**Task Execution Workflow**:

```text
1. CHECK: Does FEATURE_DIR/tasks/T{ID}.md exist?
     YES -> Read task detail file completely
     NO  -> Use task description from tasks.md

2. LOAD CONTEXT (from task detail file):
     Read all files in "Context Loading" table
     Load dev patterns from "Dev Patterns" section
     Review "Reference Patterns" for code examples

3. IMPLEMENT (using task detail guidance):
     Follow "Implementation Guidelines" structure
     Use "AI Implementation Prompt" as primary guide
     Check "Troubleshooting" if issues arise

4. VALIDATE:
     Run commands from "Validation" section
     Verify all "Acceptance Criteria" checkboxes
     Mark task as [X] in tasks.md
```

### Phase 8: Implementation Order

| Priority | Tasks |
|----------|-------|
| 1. Setup | Initialize project structure, dependencies, configuration |
| 2. Tests | Write tests for contracts, entities, integration scenarios (TDD) |
| 3. Core | Implement models, services, CLI commands, endpoints |
| 4. Integration | Database connections, middleware, logging, external services |
| 5. Polish | Unit tests, performance optimization, documentation |

### Phase 9: Completion Validation

- Verify all required tasks are completed
- Check implemented features match original specification
- Validate tests pass and coverage meets requirements
- Confirm implementation follows technical plan
- Mark completed tasks as `[X]` in tasks.md
- Report final status with summary

---

## Error Handling

| Error | Default Response | With `--stop-on-failure` |
|-------|------------------|--------------------------|
| Task execution fails | Log error, skip task, continue with independent tasks | Halt execution |
| Missing task detail file | Use tasks.md description, log warning | Same |
| Validation command fails | Log error, mark task incomplete, continue | Halt execution |
| Circular dependency detected | Log error, skip affected tasks | Halt execution |
| File conflict (parallel tasks) | Execute sequentially instead | Same |
| Pattern file not found | Log warning, continue without pattern | Same |

**Error Log Format**:
```text
T{ID} FAILED: {error_message}
   Skipping task, continuing with independent tasks
```

---

## Output Format

### Progress Updates (per task)

```text
T001 [P1] Creating module structure...
T001 [P1] DONE (2.3s)
T002 [P1] FAILED: Import error in dto.py
   Skipping, continuing with independent tasks
T003 [P1] [P] Running parallel task...
```

### Final Report

```text
Implementation complete

Summary:
   - Total: 15 tasks
   - Completed: 13
   - Failed: 1 (T002)
   - Skipped: 1 (T005 - depends on T002)

Failed Tasks:
   - T002: Import error in dto.py (line 45)

Warnings:
   - Incomplete checklists: test.md (3/8)

Modified Files:
   - src/ubits/feature/models.py (created)
   - src/ubits/feature/service.py (created)
   - tests/unit/test_feature.py (created)

Next: /code-review or /git-commit-wbs
```

---

## Notes

- This command assumes a complete task breakdown exists in tasks.md
- If tasks are incomplete or missing, run `/speckit.tasks` first to regenerate the task list
- For dry-run mode, no files are modified; only the execution plan is displayed
