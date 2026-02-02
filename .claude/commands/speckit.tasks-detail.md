# Generate Task Details

---
description: Generate task detail files from tasks.md with implementation guidance for AI agents.
handoffs:
  - label: Implement Tasks
    agent: speckit.implement
    prompt: Start implementing tasks in order
    send: true
  - label: Analyze Consistency
    agent: speckit.analyze
    prompt: Run consistency analysis
    send: true
  - label: Review Tasks
    agent: code-review
    prompt: Review task detail files
    send: false
---

## User Input

```text
$ARGUMENTS
```

Consider user input before proceeding. Load `@docs/dev-pattern/README.md` for project rules.

## Purpose

Generate task detail files from `tasks.md`:
- **Grouped files** (`P{N}-{IDs}.md`) for simple, related tasks (complexity ≤6)
- **Individual files** (`T{ID}.md`) for complex tasks (complexity >6)

| Condition | Output |
|-----------|--------|
| Complexity ≤6 + Same Phase + Same Type + ≥2 tasks | `P{N}-{IDs}.md` |
| Complexity >6 OR single task of type | `T{ID}.md` |

## Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--incremental` | Generate only missing/changed tasks | false |
| `--validate-only` | Validate without generating | false |
| `--range T{START}-T{END}` | Generate task range | all |
| `--phase {N}` | Generate phase only | all |
| `--force` | Regenerate all | false |
| `--dry-run` | Preview without writing | false |
| `--no-group` | Disable grouping | false |
| `--group-threshold {N}` | Complexity threshold | 6 |

---

## Workflow

### Phase 1: Setup

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root. Parse JSON for `FEATURE_DIR` and `AVAILABLE_DOCS` (use absolute paths).

### Phase 2: Validation

Verify before generating:
- tasks.md format compliance (no duplicate IDs, valid P1-P4 priority)
- User story refs exist in spec.md
- Phase numbers sequential

**Stop and report if validation fails.**

### Phase 3: Load Context

**Required** (from FEATURE_DIR): `plan.md`, `spec.md`, `tasks.md`
**Optional**: `data-model.md`, `contracts/`, `research.md`
**Templates**: `.specify/templates/task-detail-template.md`

### Phase 4: Parse Tasks

Extract from tasks.md:
```text
- [ ] T{ID} [{PRIORITY}] [{USER_STORY}] [P?] {DESCRIPTION} in {FILE_PATH}
```

Build registry: Task ID, Priority, User Story, Parallel marker [P], Description, file path, phase, detected type, complexity score.

### Phase 5: Dependency Analysis

| Level | Rule |
|-------|------|
| Import-Based | Task A creates module, Task B imports it → B depends on A |
| Phase-Based | Phase N depends on Phase N-1; [P] tasks parallel within phase |
| File Conflicts | Same file → cannot parallel; Export tasks depend on implementation |

Build: `blocks`, `blocked_by`, `parallel_with` for each task.

### Phase 5.5: Group Detection

```text
For each phase P, for each task type T:
  candidates = tasks where phase==P AND type==T AND complexity<=threshold
  If len(candidates) >= 2:
    cluster by relatedness (same dir, import chain, same story)
    Groups with ≥2 tasks → P{N}-{IDs}.md
  Else: individual T{ID}.md
```

**Relatedness signals**: Same directory prefix (high), Import chain (high), Same user story (medium), Sequential IDs (low).

### Phase 6: Incremental Check (if --incremental)

For each task: check if `{FEATURE_DIR}/tasks/T{ID}.md` exists, compare definition hash, skip if unchanged and not --force. Report: new, changed, unchanged, forced counts.

### Phase 7: Generate

**Grouped tasks**: Create `P{N}-{IDs}.md` with shared context, sequential `## T{ID}` sections, combined AI prompt.
**Individual tasks**: Create `T{ID}.md` with full detail structure.

Use copy bash and then load structures from `.specify/templates/task-detail-template.md` to `{FEATURE_DIR}/tasks/T{ID}.md`

### Phase 8: Create Index

Generate `{FEATURE_DIR}/tasks/_INDEX.md`: Summary table, dependency graph (Mermaid), execution order, phase breakdown.

### Phase 9: Post-Validation

Verify: AC alignment, no dependency cycles, file paths valid, P1 not blocked by P2+, pattern refs resolve.

### Phase 10: Update tasks.md with Detail Links

After generating task detail files, update the source `tasks.md` to reference the generated files.

**Link Format**:
```markdown
# Individual task (T{ID}.md generated)
- [ ] T001 [P1] [US1] Task description → [T001](tasks/T001.md)

# Grouped task (P{N}-{IDs}.md generated)
- [ ] T001 [P1] [US1] Task description → [P1-T001-T002](tasks/P1-T001-T002.md)
- [ ] T002 [P1] [US1] Related task → [P1-T001-T002](tasks/P1-T001-T002.md)
```

**Update Rules**:
1. Add markdown link suffix to each task line that has a generated detail file
2. For grouped tasks, all tasks in the group link to the same group file
3. Preserve existing task format (checkbox, ID, priority, story, description)
4. Use relative paths from tasks.md location (`tasks/{filename}.md`)

**Verification**:
- All generated files have corresponding links in tasks.md
- Links resolve to existing files (validate paths)
- No broken links or orphaned detail files

---

## Error Handling

| Error | Response |
|-------|----------|
| Prerequisites script fails | Stop, report missing dependencies with install instructions |
| Invalid tasks.md format | List specific violations (line numbers), stop |
| Duplicate task IDs | List duplicates, stop |
| Circular dependencies | Show cycle path (T001→T003→T001), stop |
| No tasks match filter | Report filter criteria, suggest `--phase` or `--range` alternatives |
| Template file missing | Use inline fallback, warn user |
| User story ref not found | Warn (non-blocking), suggest adding to spec.md |
| tasks.md link update fails | Report tasks without links, provide manual fix instructions |
| Generated file missing for link | Warn, skip link for that task, report at end |

---

## Generation Rules

### Task Type Detection

| Keywords | Type |
|----------|------|
| "Create directory/package/structure" | SETUP |
| "Write test", "Test", "TDD" | TEST |
| "Implement", "Add", "Create model/service/endpoint" | IMPLEMENTATION |
| "Refactor", "Update to use", "Migrate" | REFACTOR |
| "Export", "Update exports", "Update init" | EXPORT |

### Role Derivation

| Type | Role | Context Modifiers |
|------|------|-------------------|
| SETUP | Senior Module Architect | - |
| TEST | TDD Practitioner | - |
| IMPLEMENTATION | Domain Expert | +ML, +API Security, +DB Performance, +Distributed Systems |
| REFACTOR | Legacy Code Specialist | - |
| EXPORT | API Surface Designer | - |

### Complexity Scoring (sum 4 factors, each 1-5)

| Factor | 1→5 progression |
|--------|-----------------|
| Files | 1 → 2-3 → 4-5 → 6-10 → 10+ |
| Dependencies | 0 → 1-2 → 3-4 → 5-6 → 7+ |
| New Concepts | Familiar → Some → Half → Mostly → All new |
| Test Coverage | Has → Some → Needs → Complex → Critical |

**Levels**: 🟢1-5 Simple | 🟡6-10 Moderate | 🟠11-15 Complex | 🔴16-20 Critical

### Header Derivation

| Field | Rule |
|-------|------|
| Stakeholders | SI (API/lib), TD (implementation), OPS (monitoring), SEC (auth/security) |
| Tier | `libs/` → Library, `apps/worker/` → Tier 2, `apps/*-service/` → Tier 3 |
| Safety | SETUP/EXPORT/TEST → Info, IMPLEMENTATION → Critical, REFACTOR → Warning |

### Pattern Mapping

| Task Context | Primary | Secondary |
|--------------|---------|-----------|
| Repository/Data | repository-pattern | database-optimization |
| Service Logic | service-layer | dependency-injection |
| API Endpoint | api-builder-pattern | api-auth-integration |
| Testing | testing-standards | validation-workflow |
| Type Safety | type-safety | language-essentials |
| Module Structure | language-essentials | shared-libraries |

### Validation Commands

```bash
{LANG_LINT_COMMAND}           # Lint
{LANG_TYPE_CHECK_COMMAND}     # Type check
{LANG_TEST_COMMAND}           # Test with coverage
{LANG_IMPORT_VERIFICATION}    # Import verification
```

---

## Templates

Load `.specify/templates/task-detail-template.md` for:
- Individual task structure (T{ID}.md)
- Grouped task structure (P{N}-{IDs}.md)
- Index file structure (_INDEX.md)
- Objective patterns by type
- Acceptance criteria templates
- Guidelines by type

---

## AI Prompt Template

### Prompt Engineering Principles

When generating AI implementation prompts, follow these principles:

| Principle | Application |
|-----------|-------------|
| **Clarity** | Use imperative verbs, avoid hedging ("might", "could") |
| **Specificity** | Reference exact file paths, pattern files, acceptance criteria |
| **Scoping** | Define what's in/out of scope explicitly |
| **Context First** | Load patterns and references before instructions |
| **Measurable Outcomes** | Every deliverable has a validation command |

### Unified Template Structure

Generate AI prompts using this parameterized template:

````markdown
## AI Implementation Prompt

```text
## Task{MODE=group ? " Group: Phase {N} {TYPE} Tasks" : ": {TASK_TITLE}"}

## Context
{MODE=group ? "This group contains {COUNT} related {TYPE} tasks for {FEATURE_NAME}." : "Task {TASK_ID} for {FEATURE_NAME}."}
Tech stack: {DETECTED_LANGUAGE} | Framework: {DETECTED_FRAMEWORK}

## Patterns to Load
{PATTERN_REFS_WITH_PATHS}

{MODE=group ? "## Tasks" : "## Requirements"}
{MODE=group ? TASK_LIST_WITH_SUBTASKS : AC_AS_BULLETS}

## Instructions
{TYPE_INSTRUCTIONS}

## Constraints
- File size: ≤700 lines
- Follow existing project conventions
- No placeholders or TODOs in deliverables

## Deliverables
{DELIVERABLE_CHECKLIST}

## Validation
{VALIDATION_COMMANDS}
```
````

### Type-Specific Instructions (Language-Agnostic)

| Type | Instructions |
|------|--------------|
| SETUP | 1. Create directory at `{PATH}` 2. Create module entry point with docstring 3. Create placeholder files: `{LIST}` 4. Verify imports/requires work |
| TEST | 1. Load testing standards from project docs 2. Create test file at `{PATH}` 3. Write tests: happy path, error handling, edge cases 4. Verify tests FAIL (TDD red phase) 5. Do NOT implement production code |
| IMPLEMENTATION | 1. Load patterns: `{PATTERN_PATHS}` 2. Follow reference implementation style 3. Implement all required methods/functions 4. Add type annotations/hints 5. Keep file ≤700 lines |
| REFACTOR | 1. Read original implementation 2. Extend/implement `{BASE_CLASS/INTERFACE}` 3. Remove methods provided by base 4. Implement only abstract/required methods 5. Verify existing tests pass |
| EXPORT | 1. Add exports for: `{COMPONENTS}` 2. Update public API surface 3. Re-export from parent module 4. Verify import paths work |

### Deliverable Patterns (Language-Agnostic)

| Type | Deliverables |
|------|--------------|
| SETUP | Module entry point, placeholder files, import verification |
| TEST | Test file(s), all tests written and failing (TDD red) |
| IMPLEMENTATION | Implementation file(s), tests pass, coverage target met |
| REFACTOR | Refactored file(s), existing tests pass, no new type errors |
| EXPORT | Updated exports, parent module updated, paths verified |

### Validation Command Placeholders

Use these placeholders; the generator resolves them based on detected project language:

| Placeholder | Purpose |
|-------------|---------|
| `{LINT_CMD}` | Lint check (ruff, eslint, golangci-lint, clippy) |
| `{TYPE_CHECK_CMD}` | Type check (pyright, tsc, go vet, cargo check) |
| `{TEST_CMD}` | Run tests (pytest, jest, go test, cargo test) |
| `{COVERAGE_CMD}` | Test with coverage threshold |
| `{IMPORT_CHECK_CMD}` | Verify imports/requires work |
| `{FORMAT_CMD}` | Format check (ruff format, prettier, gofmt, cargo fmt) |

** Note: Consider make command language-specific from project, package

### Prompt Quality Checklist

Before finalizing generated prompt, verify:

- [ ] Task objective is a single clear sentence
- [ ] All file paths are absolute or relative to project root
- [ ] Pattern references include full paths (`docs/dev-pattern/{NN}-{name}.md`)
- [ ] Acceptance criteria are measurable (not vague)
- [ ] Validation commands are copy-paste ready
- [ ] No language-specific assumptions if project is polyglot

---

## Output Format

```text
✅ Task detail generation complete

📁 Generated:
   {FEATURE_DIR}/tasks/
   ├── _INDEX.md
   ├── P1-T001-T002-T003.md  # 📦 Grouped (complexity 6 - T001, T002, T003)
   ├── T006.md          # 🟡 Individual (complexity 8)
   └── T009.md          # 🔴 Individual (complexity 16)

📊 Summary:
   - Total: {N} tasks in {M} files
   - Grouped: {G} files ({T} tasks) | Individual: {I} files
   - By type: Setup {N}, Test {N}, Impl {N}, Refactor {N}, Export {N}
   - By complexity: 🟢{N} 🟡{N} 🟠{N} 🔴{N}

✅ Consistency: AC alignment PASS, Dependencies PASS, Paths PASS

📝 tasks.md Updated:
   - Links added: {N} tasks
   - Link format: [T{ID}](tasks/T{ID}.md) or [P{N}-{IDs}](tasks/P{N}-{IDs}.md)
   - Verification: All links resolve ✅

🚀 Next: /speckit.implement or /speckit.analyze
```

### Incremental Mode Output

```text
📊 Incremental: Existing {N}, New {N}, Changed {N}, Skipped {N}
📝 Generated: {FILE_LIST}
⏭️ Skipped: {UNCHANGED_LIST}
```

### No-Group Mode Output

```text
✅ Task detail generation complete (grouping disabled)
📁 Generated: {N} individual files (T001.md - T{MAX}.md)
```
