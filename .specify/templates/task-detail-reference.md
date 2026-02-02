# Task Detail Reference Guide

Extended guidance for filling task-detail-template.md. Load when generating complex tasks.

---

## Header Fields

### Task ID Format

```text
T{ID} [{PRIORITY}] [{USER_STORY}] {TITLE}
```

- **T{ID}**: Sequential (T001, T002, T083)
- **[{PRIORITY}]**: P1 (critical), P2 (high), P3 (medium), P4 (low)
- **[{USER_STORY}]**: US1, US2, INFRA (infrastructure)
- **[P]**: Add if task can run parallel (different files, no deps)
- **{TITLE}**: Action phrase (verb + noun): "Implement RequestParser"

### Stakeholder Codes

| Code | Cares About |
|------|-------------|
| SI | API stability, maintainability |
| TD | Implementation, accuracy |
| OPS | Observability, deployment |
| SEC | Auth, encryption |

### Tier Mapping

| Path Pattern | Tier |
|--------------|------|
| `libs/*` | Library (all tiers) |
| `apps/worker/*` | Tier 1/2 (Edge/Worker) |
| `apps/*-service/*` | Tier 3 (Data Center) |

### Safety Levels

| Task Type | Safety | Reason |
|-----------|--------|--------|
| SETUP | Info | Low-risk setup |
| TEST | Info | Non-breaking |
| IMPLEMENTATION | Critical | Core functionality |
| REFACTOR | Warning | Behavior change risk |
| EXPORT | Info | API surface only |

---

## Complexity Assessment

### Scoring Guide

| Factor | 1 | 2 | 3 | 4 | 5 |
|--------|---|---|---|---|---|
| Files | 1 file | 2-3 | 4-5 | 6-10 | 10+ |
| Dependencies | 0 blocking | 1-2 | 3-4 | 5-6 | 7+ |
| New Concepts | All familiar | Some new | Half new | Mostly new | All new |
| Test Coverage | Tests exist | Some exist | Need tests | Complex tests | Critical path |

### Approach by Score

| Score | Level | Approach |
|-------|-------|----------|
| 1-8 | Simple 🟢 | Direct execution |
| 9-14 | Medium 🟡 | Consider agent delegation |
| 15-20 | Complex 🔴 | Recommend planning + agent |

### LOC Estimates

| Type | Typical Lines |
|------|---------------|
| SETUP | ~20 |
| TEST | 50-150 |
| IMPLEMENTATION | 50-200 |
| REFACTOR | Reduces 30-50% |
| EXPORT | 20-50 |

---

## Role Assignment

### Primary Roles

| Type | Role | Behavioral Focus |
|------|------|------------------|
| SETUP | Senior Module Architect | Structure, conventions, future-proof |
| TEST | TDD Practitioner | Tests first, coverage, behavior docs |
| IMPLEMENTATION | Domain Expert | Pattern adherence, type safety |
| REFACTOR | Legacy Code Specialist | Zero behavior change, tests pass |
| EXPORT | API Surface Designer | Clean API, no circular deps |

### Context Modifiers

Add to role based on domain:

| Context | Add |
|---------|-----|
| ML/AI components | + ML Systems (memory, batching) |
| API/endpoint | + API Security (auth, validation) |
| Data access | + Database Performance (N+1, queries) |
| Workers/consumers | + Distributed Systems (idempotency) |
| Auth/encryption | + Security (OWASP, secrets) |

### Role Behavioral Templates

**SETUP:**

- Do: Clean structure, proper init patterns, plan for expansion
- Don't: Add implementation, create unnecessary abstractions
- Quality: Imports work, matches conventions

**TEST:**

- Do: Write tests before implementation, cover happy/error/edge, test interface compliance
- Don't: Write implementation, skip edge cases, assume behavior
- Quality: Tests fail meaningfully, coverage met

**IMPLEMENTATION:**

- Do: Follow patterns exactly, implement all criteria, maintain type safety
- Don't: Over-engineer, add untested features, deviate from spec
- Quality: Tests pass, coverage met, zero type/lint errors

**REFACTOR:**

- Do: Preserve all behavior, run tests before/after, incremental changes
- Don't: Change public API, modify test expectations, add new behavior
- Quality: Existing tests pass unchanged

**EXPORT:**

- Do: Clean public API, support import paths, update declarations
- Don't: Change implementation, create circular deps
- Quality: All imports work, no circular errors

---

## Objective Patterns

| Type | Pattern |
|------|---------|
| SETUP | "Create the `{directory}` package structure for {purpose}." |
| TEST | "Write comprehensive tests for {component} ensuring {behavior} (TDD red phase)." |
| IMPLEMENTATION | "Implement {component} that {primary_function}." |
| REFACTOR | "Refactor {component} to extend {base_class}, preserving behavior." |
| EXPORT | "Update exports in `{module}` to expose {components} publicly." |

---

## Acceptance Criteria Templates

### SETUP (4 criteria)

```markdown
- [ ] AC1: Create `{directory}` at correct location
- [ ] AC2: Create module init with docstring
- [ ] AC3: Create placeholder files for subsequent tasks
- [ ] AC4: Verify imports work without errors
```

### TEST (6 criteria)

```markdown
- [ ] AC1: Test {happy_path_scenario}
- [ ] AC2: Test {error_handling_scenario}
- [ ] AC3: Test {edge_case_scenario}
- [ ] AC4: Test protocol compliance (all methods)
- [ ] AC5: Tests fail before implementation (TDD red)
- [ ] AC6: Target coverage when implementation added
```

### IMPLEMENTATION (6 criteria)

```markdown
- [ ] AC1: Implement {protocol_or_interface}
- [ ] AC2: {Primary_functionality}
- [ ] AC3: {Error_handling_behavior}
- [ ] AC4: {Edge_case_handling}
- [ ] AC5: Tests pass ({TEST_TASK_REF})
- [ ] AC6: Target coverage met
```

### REFACTOR (6 criteria)

```markdown
- [ ] AC1: {Component} extends {BaseClass}
- [ ] AC2: Only implement required abstract methods
- [ ] AC3: Remove redundant method implementations
- [ ] AC4: Existing tests pass (no behavior change)
- [ ] AC5: {Preserved_pattern} preserved
- [ ] AC6: {Metrics_identical}
```

### EXPORT (5 criteria)

```markdown
- [ ] AC1: Export all {N} components from module init
- [ ] AC2: Re-export from parent module
- [ ] AC3: Update public API lists
- [ ] AC4: Verify both import paths work
- [ ] AC5: No circular import issues
```

---

## Pattern Mapping

| Task Context | Primary Pattern | Secondary |
|--------------|-----------------|-----------|
| Repository/Data | repository-pattern | database-optimization |
| Service Logic | service-layer | dependency-injection |
| API Endpoint | api-builder-pattern | api-auth-integration |
| Testing | testing-standards | validation-workflow |
| Auth/Security | api-auth-integration | dependency-injection |
| Type Safety | type-safety | language-essentials |
| Module Structure | language-essentials | shared-libraries |

---

## Implementation Guidelines

### Structure Overview Format

```markdown
1. **Class Definition**: {ClassName} implementing {Protocol}
2. **Dependencies**: {dependency1}, {dependency2} (injected)
3. **Properties**: input_type, output_type (runtime types)
4. **Core Methods**: {method_name}() with primary logic
```

### Logic Flow Format

Use pseudocode, not real code:

```text
for each item in input:
    result = process(item)
    if result is valid:
        add to success list
    else:
        log warning
        add to error list
return create_result(successes, errors)
```

### Type Mapping Format

For generic classes:

| Parameter | Concrete Type | Purpose |
|-----------|---------------|---------|
| `TInput` | `List<Bytes>` | Raw messages |
| `TOutput` | `ParsedBatch` | Parsed batch |

### Key Design Decisions Format

Document important choices:

- **Error handling**: Fail-open pattern, errors logged not blocking
- **Concurrency**: Async I/O for non-blocking
- **Caching**: TTL-based expiry
- **Logging**: Structured output
- **Performance**: Batch processing, lazy loading

---

## Validation Commands (Language Placeholders)

Use these placeholders in generated tasks. Replace with project-specific commands.

| Placeholder | Purpose | Examples |
|-------------|---------|----------|
| `{LANG_LINT_COMMAND}` | Linting | `eslint .`, `ruff check .`, `golint ./...` |
| `{LANG_TYPE_CHECK_COMMAND}` | Type checking | `tsc --noEmit`, `pyright`, `go vet ./...` |
| `{LANG_TEST_COMMAND}` | Test with coverage | `jest --coverage`, `pytest --cov`, `go test -cover` |
| `{LANG_IMPORT_VERIFICATION}` | Import check | Language-specific import test |
| `{LANG_IMPORT_DEBUG}` | Debug imports | Print type/module info |
| `{LANG_TYPE_DEBUG}` | Debug types | Verbose type checker output |
| `{LANG_SINGLE_TEST}` | Single test run | Test single file/function |
| `{LANG_COVERAGE}` | Coverage report | Detailed coverage output |

---

## Definition of Done Templates

### IMPLEMENTATION

- [ ] Protocol/interface fully implemented
- [ ] Tests pass (ref test task)
- [ ] Target coverage met
- [ ] Zero type errors
- [ ] Zero lint violations

### TEST

- [ ] Tests written first (TDD red)
- [ ] All AC covered
- [ ] Tests fail before implementation
- [ ] Tests pass after implementation

### SETUP

- [ ] Directory structure created
- [ ] Placeholder files with docs
- [ ] Imports verified
- [ ] No type/lint errors

### REFACTOR

- [ ] Existing tests pass unchanged
- [ ] No new type/lint errors
- [ ] Behavior identical
- [ ] Code reduction achieved

### EXPORT

- [ ] All components exported
- [ ] Both import paths work
- [ ] No circular deps
- [ ] Declarations updated

---

## AI Prompt Templates

### SETUP

```text
## Role: Senior Module Architect

## Task: {TASK_TITLE}

## Context
Creating module structure for {FEATURE}, task {ID}.

## Requirements
{AC_AS_BULLETS}

## Instructions
1. Create directory at {PATH}
2. Create module init with docstring
3. Create placeholders: {FILE_LIST}
4. Verify imports

## Deliverables
- [ ] {DIRECTORY} init file
- [ ] {PLACEHOLDERS}

## Validation
{LANG_IMPORT_VERIFICATION}
```

### TEST (TDD)

```text
## Role: TDD Practitioner

## Task: {TASK_TITLE}

## Context
Writing tests for {COMPONENT}, task {ID}. Tests should fail until implementation.

## Requirements
{AC_AS_BULLETS}

## TDD Instructions
1. Load testing patterns from dev-pattern docs
2. Create test file at {PATH}
3. Write tests that fail meaningfully
4. Do not implement production code

## Categories
- Happy path: {N} tests
- Error handling: {N} tests
- Edge cases: {N} tests

## Deliverables
- [ ] {TEST_FILE}
- [ ] All tests failing (red phase)

## Validation
{LANG_TEST_COMMAND}  # Should show failures
```

### IMPLEMENTATION

```text
## Role: Domain Expert

## Task: {TASK_TITLE}

## Context
Implementing {COMPONENT} for {FEATURE}, task {ID}.

## Requirements
{AC_AS_BULLETS}

## Patterns to Load
1. {PRIMARY_PATTERN}
2. {SECONDARY_PATTERN}
3. {REFERENCE_IMPL}

## Instructions
1. Load patterns before coding
2. Follow reference style exactly
3. Implement all criteria
4. Add type annotations
5. Keep file ≤{MAX_LINES} lines

## Deliverables
- [ ] {IMPL_FILE}
- [ ] Tests pass ({TEST_REF})
- [ ] Target coverage met

## Validation
{LANG_LINT_COMMAND} && {LANG_TYPE_CHECK_COMMAND} && {LANG_TEST_COMMAND}
```

### REFACTOR

```text
## Role: Legacy Code Specialist

## Task: {TASK_TITLE}

## Context
Refactoring {COMPONENT} to use {BASE_CLASS}, task {ID}.

## Requirements
{AC_AS_BULLETS}

## Migration Steps
1. Run tests (capture baseline)
2. Change class declaration to extend {BASE}
3. Remove methods now from base
4. Implement only: {ABSTRACT_METHODS}
5. Run tests (verify identical)

## Preserved Behavior
- {BEHAVIOR_1}
- {BEHAVIOR_2}

## Deliverables
- [ ] Refactored {FILE}
- [ ] Existing tests pass
- [ ] No new type errors

## Validation
{LANG_TEST_COMMAND} && {LANG_TYPE_CHECK_COMMAND}

## Rollback
git checkout HEAD -- {FILE}
```

### EXPORT

```text
## Role: API Surface Designer

## Task: {TASK_TITLE}

## Context
Updating exports for {MODULE}, task {ID}.

## Requirements
{AC_AS_BULLETS}

## Instructions
1. Add exports: {COMPONENT_LIST}
2. Update public API list (sorted)
3. Add re-exports to parent
4. Verify import paths

## Import Paths
- Short: {PATH_1}
- Full: {PATH_2}

## Deliverables
- [ ] {MODULE} init updated
- [ ] Parent updated
- [ ] Both paths verified

## Validation
{LANG_IMPORT_VERIFICATION}
```
