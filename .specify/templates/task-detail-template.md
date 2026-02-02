# Task Detail Template v4.4

<!-- description: AI agent task execution template with TOON-optimized definitions and hints -->
<!-- version: 4.4.0 -->

## Definitions (TOON Format)

<!-- REF: TOON format: name[count]{fields}: rows -->

```toon
# Language Commands (use {LANG} placeholder, replace with lang.id)
lang[4]{id,lint,type,test,import,debug_import,debug_test,coverage}:
  py,uv run ruff check {path},uv run pyright {path},uv run pytest {path} -v --cov-fail-under={cov},uv run python -c "from {mod} import {sym}; print('OK')",uv run python -c "from {mod} import {sym}; print(type({sym}))",uv run pytest {file}::{cls}::{method} -vvs,uv run pytest --cov={mod} --cov-report=term-missing {file}
  ts,pnpm lint {path},pnpm type-check,pnpm test {path} --coverage,node -e "require('{mod}')",node -e "console.log(typeof require('{mod}'))",pnpm test {file} -- --testNamePattern="{name}",pnpm test {file} --coverage --collectCoverageFrom="{src}"
  go,golangci-lint run,go vet ./...,go test ./... -cover,go build ./...,go list -m all | grep {mod},go test -v -run {Test} ./...,go test -coverprofile=cov.out ./... && go tool cover -func=cov.out
  rs,cargo clippy,cargo check,cargo test --all-features,cargo build,cargo tree -p {crate},cargo test {name} -- --nocapture,cargo tarpaulin --out Html

# Roles by Task Type
role[5]{type,name,do,dont,quality}:
  SETUP,Senior Module Architect,"clean structure|proper init|plan expansion","add implementation|over-abstract",Module imports without errors
  TEST,TDD Practitioner & QA Engineer,"tests first|cover all paths|test interface","write implementation|skip edges",Tests fail meaningfully
  IMPL,Domain Expert + Clean Code Advocate,"follow patterns exactly|implement all AC|type safety","over-engineer|deviate from spec",All tests pass with coverage
  REFACTOR,Legacy Code Specialist,"preserve behavior|test before/after|incremental","change API|modify tests",Existing tests pass unchanged
  EXPORT,API Surface Designer,"clean public API|support import paths","change implementation|create cycles",All import paths work

# Complexity Thresholds (4-level system, sum of 4 factors each 1-5)
complexity[4]{range,emoji,level,approach}:
  1-5,🟢,Simple,Direct execution
  6-10,🟡,Moderate,Consider agent delegation
  11-15,🟠,Complex,Agent with planning phase
  16-20,🔴,Critical,Agent with full context + review

# Stakeholder Codes
stakeholder[4]{code,name,focus}:
  SI,System Integrators,API stability and maintainability
  TD,Technical Developers,Implementation accuracy
  OPS,Platform Operators,Observability and deployment
  SEC,Security Team,Auth and encryption

# Architecture Tiers
tier[4]{id,name,scope}:
  1,Edge,Camera/edge devices and K3s clusters
  2,Worker,ML inference workers and GPU nodes
  3,Data Center,Backend services and databases
  Lib,Library,Shared libraries used across all tiers

# Safety Levels
safety[3]{level,risk,action}:
  Critical,Breaking changes possible,Full review required
  Warning,Important changes,Testing required
  Info,Low-risk changes,Standard review

# Agent Selection
agent[6]{trigger,agent_type,when}:
  TEST,Test automation,Writing test files
  IMPL,Domain developer,Feature implementation
  Unfamiliar,Explore (quick/medium),Need codebase context first
  Multiple approaches,Plan,Architecture decisions needed
  After impl,Code review,Validate patterns and quality
  Refactor,Component tracer,Trace dependencies first

# AI Hint Syntax (simplified): <!-- TYPE: content -->
# MUST = hard constraint, GUIDE = suggestion, AVOID = anti-pattern, REF = cross-reference
hint[4]{type,use,example}:
  MUST,Hard constraints that cannot be skipped,"<!-- MUST: Action verb | ≤25 words -->"
  GUIDE,Soft suggestions and best practices,"<!-- GUIDE: Use active voice -->"
  AVOID,Anti-patterns to prevent,"<!-- AVOID: impl code | pseudocode -->"
  REF,Cross-references to other sections,"<!-- REF: role[] complexity[] -->"
```

---

## T{ID} [{PRIORITY}] [{USER_STORY}] {TITLE}

<!-- MUST: T001 [P1] [US1] Title | P1-critical P2-high P3-medium P4-low | [P] for parallel-safe -->

**Epic**: {EPIC_OR_PR_NAME}
**Stakeholders**: {STAKEHOLDER_CODES}
**Tier**: {TIER_LEVEL}
**Safety**: {SAFETY_LEVEL}

<!-- REF: stakeholder[] tier[] safety[] -->

---

## Complexity Assessment

| Factor | Score (1-5) | Notes |
|--------|-------------|-------|
| Files Affected | {N} | {COUNT} files |
| Dependencies | {N} | {BLOCKING_TASK_COUNT} blocking tasks |
| New Concepts | {N} | {NEW_PATTERNS_INTRODUCED} |
| Test Coverage | {N} | {EXISTING_TEST_AVAILABILITY} |
| **Total** | **{SUM}/20** | {COMPLEXITY_LEVEL} |

<!-- REF: complexity[] -->

**Estimated LOC**: ~{N} lines
**Parallel Opportunity**: {YES_NO_WITH_REASON}

---

## AI Role Assignment

**Primary Role**: {PRIMARY_ROLE}
**Context Modifiers**: {CONTEXT_MODIFIERS_OR_NONE}

<!-- REF: role[] | Modifiers: +ML Systems +API Security +Database Performance +Distributed Systems -->

### Behavioral Constraints

**Do**:

- {ROLE_DO_1}
- {ROLE_DO_2}
- {ROLE_DO_3}

**Don't**:

- {ROLE_DONT_1}
- {ROLE_DONT_2}

**Quality Bar**: {QUALITY_EXPECTATION}

<!-- REF: role[].do role[].dont role[].quality -->

---

## Execution Guidance

**Complexity**: {SCORE}/20 → {DIRECT | CONSIDER_AGENT | RECOMMEND_AGENT_WITH_PLANNING}

| Factor | Assessment | Approach |
|--------|------------|----------|
| Complexity | {LEVEL} | {APPROACH_HINT} |
| Files | {COUNT} | {SINGLE_OR_MULTI_FILE} |
| Familiarity | {HIGH/MEDIUM/LOW} | {CONTEXT_HINT} |
| Patterns Available | {YES/NO} | {PATTERN_HINT} |

<!-- REF: agent[] -->

---

## Context Loading

**Read before implementation:**

- `specs/{SPEC_ID}/spec.md` - {REQUIREMENT_REFS}
- `specs/{SPEC_ID}/plan.md` - {ARCHITECTURE_REFS}
- `{PATH_TO_RELATED_CODE}` - {PATTERN_DESCRIPTION}
- `specs/{SPEC_ID}/tasks/{DEPENDENT_TASK}.md` - {DEPENDENCY_REASON}

**Cross-References:**

| Artifact | Location | Relevance |
|----------|----------|-----------|
| User Story | `spec.md#{USER_STORY_ID}` | Requirements |
| Entity | `data-model.md#{ENTITY}` | Data structure |
| Endpoint | `contracts/{API}.yaml` | API contract |
| Test Scenario | `quickstart.md#{SCENARIO}` | Validation |

---

## Objective

{ONE_SENTENCE_OBJECTIVE}

<!-- MUST: Action verb (Implement|Create|Write|Refactor|Update) | ≤25 words -->

---

## Target Files

- **Implementation**: `{APP_OR_LIB}/{PATH_TO_SOURCE}/{FILE}{EXT}`
- **Tests**: `{APP_OR_LIB}/{PATH_TO_TESTS}/{TEST_FILE}{EXT}`

---

## Acceptance Criteria

- [ ] AC1: {FIRST_ACCEPTANCE_CRITERION}
- [ ] AC2: {SECOND_ACCEPTANCE_CRITERION}
- [ ] AC3: {THIRD_ACCEPTANCE_CRITERION}
- [ ] AC4: {FOURTH_ACCEPTANCE_CRITERION}
- [ ] AC5: {FIFTH_ACCEPTANCE_CRITERION}
- [ ] AC6: Tests pass ({TEST_TASK_REF}) / target coverage met

<!-- GUIDE: Number consecutively | independently verifiable | active voice -->
<!-- MUST: Include edge cases and error scenarios | 4-8 criteria per task -->

---

## Functionality

<!-- GUIDE: WHAT not HOW | spec↔impl contract -->
<!-- MUST: 2-3 sentences | domain types | error strategy | document side effects -->
<!-- AVOID: impl code | pseudocode | how-to instructions -->

### Primary Function

{DESCRIBE_WHAT_THE_COMPONENT_DOES}

<!-- GUIDE: Example: "Parses Kafka bytes→InferenceRequest. Filters malformed with warnings. Batch for throughput." -->

### Input/Output

| Direction | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| Input | `{INPUT_TYPE}` | {INPUT_DESCRIPTION} | {SIZE_LIMITS_OR_VALIDATION} |
| Output | `{OUTPUT_TYPE}` | {OUTPUT_DESCRIPTION} | {GUARANTEES_OR_INVARIANTS} |

<!-- GUIDE: dataclass names | generics | Protocol | nullability explicit -->

### Error Handling

| Error Type | Behavior | Recovery | Logging |
|------------|----------|----------|---------|
| Invalid Input | {SKIP_OR_REJECT} | {CONTINUE_OR_FAIL} | {LOG_LEVEL}: {MESSAGE_PATTERN} |
| External Failure | {RETRY_OR_CIRCUIT_BREAK} | {FALLBACK_OR_PROPAGATE} | {LOG_LEVEL}: {MESSAGE_PATTERN} |
| Timeout | {CANCEL_OR_PARTIAL} | {DEFAULT_OR_ERROR} | {LOG_LEVEL}: {MESSAGE_PATTERN} |

<!-- GUIDE: Fail-Open→non-critical,best-effort | Fail-Closed→critical,integrity | Circuit Breaker→external deps | Retry→transient failures -->
<!-- MUST: <100ms P99: prefer fail-open over retries -->

### Side Effects

| Effect | Target | Format | When |
|--------|--------|--------|------|
| Logging | {LOGGER_NAME} | structlog JSON | {TRIGGER_CONDITION} |
| Metrics | {METRIC_NAME} | Prometheus {TYPE} | {TRIGGER_CONDITION} |
| Cache | {CACHE_KEY_PATTERN} | Redis/Memory | {TTL_AND_EVICTION} |
| Events | {TOPIC_OR_CHANNEL} | Kafka/Redis PubSub | {TRIGGER_CONDITION} |

<!-- GUIDE: Check: logging(correlation_id,tenant_id,camera_id) | prometheus(counter,histogram,gauge) | cache invalidation | event schema version | tracing spans -->

---

## Dependencies

- **Blocks**: {TASK_IDS} ({REASON})
- **Blocked by**: {TASK_IDS} ({REASON})
- **Parallel with**: {TASK_IDS_OR_NONE}

| Dependency Type | Related Task | Symbol | Reason |
|-----------------|--------------|--------|--------|
| Import | T{ID} | `{module}.{symbol}` | {USAGE} |
| Extends | T{ID} | `{BaseClass}` | {INHERITANCE} |
| Tests | T{ID} | `test_{function}` | {TDD} |

---

## Codebase Reference

**Status**: ⬜ NOT STARTED | 🔄 IN PROGRESS | ✅ COMPLETE

**Existing Code**: `{PATH}` - {DESCRIPTION}
**Test Files**: `{PATH}` - {STATUS}
**Contracts**: `{PATH}` - {DESCRIPTION}

---

## Dev Patterns

**Load before implementation:**

- Primary: `{PATTERN_PATH}` - {PURPOSE}
- Secondary: `{PATTERN_PATH}` - {PURPOSE}
- Reference: `{IMPL_PATH}` - {WHAT_TO_LEARN}

<!-- GUIDE: Repository/Data→access,query | Service/Logic→DI | API/Endpoint→auth | Testing→validation | Auth/Security→integration -->

**Rules:**

- [ ] Namespace: Follow project conventions
- [ ] File size: ≤{MAX_LINES} lines
- [ ] Types: All parameters and returns annotated
- [ ] Async: Use language-appropriate async patterns
- [ ] Coverage: {TARGET_COVERAGE}%
- [ ] Docs: Module, class, public method documentation

**Quality Gates:**

```bash
{LANG_LINT_COMMAND}      # @:b lang[].lint
{LANG_TYPE_CHECK_COMMAND} # @:b lang[].type
{LANG_TEST_COMMAND}       # @:b lang[].test
```

---

## Implementation Guidelines

### Structure

1. **Class**: {CLASS_NAME} {EXTENDS_OR_IMPLEMENTS} {BASE}
2. **Dependencies**: {INJECTED_LIST}
3. **Methods**: {METHOD_LIST}

### Logic Flow

```text
{PSEUDOCODE}
```

### Type Mapping

| Parameter | Concrete Type | Purpose |
|-----------|---------------|---------|
| `{TYPE_VAR}` | `{CONCRETE}` | {PURPOSE} |

### Design Decisions

- **{AREA}**: {RATIONALE}

<!-- GUIDE: Error→fail-open vs fail-closed | Concurrency→async I/O | Caching→TTL expiry | Logging→structured JSON -->
<!-- GUIDE: Performance(<100ms P99): batch | lazy load | resource pool | best-effort | streaming | zero-copy -->

---

## Task-Type Specific

### TEST: Test Strategy

**Coverage Target**: {PERCENTAGE}%
**Categories**: Unit | Integration | E2E | Contract

**Fixtures**: `{NAME}` - {PURPOSE}

**Mocking:**

| Component | Mock Type | Reason |
|-----------|-----------|--------|
| {COMPONENT} | {MOCK_TYPE} | {WHY} |

**Test Cases:**

| Test Name | Scenario | Expected |
|-----------|----------|----------|
| `test_{method}_{scenario}` | {INPUT} | {OUTPUT} |

<!-- MUST (TEST): tests first | expect FAIL | independent | meaningful assertions -->

### REFACTOR: Migration Checklist

**Preserved Behavior:**

- {BEHAVIOR}: {DETAILS}

**Steps:**

- [ ] Capture before state
- [ ] Implement refactor
- [ ] Verify identical output
- [ ] Compare performance

**Rollback**: `git checkout HEAD~1 -- {FILE_PATH}`

<!-- MUST (REFACTOR): preserve behavior | test before/after | no API changes | no test modifications -->

### IMPLEMENTATION: Architecture Decision

- **Decision**: {WHAT}
- **Context**: {WHY}
- **Alternatives**: {OPTIONS}
- **Consequences**: {TRADEOFFS}

<!-- MUST (IMPL): make tests pass | follow patterns exactly | no test mods | type annotations | docs -->

---

## Reference Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| {NAME} | `{FILE}:{LINES}` | {WHAT_TO_LEARN} |

---

## Task Steps (Complex Tasks)

1. {STEP_1}
2. {STEP_2}
3. {STEP_3}
4. {VERIFICATION}

---

## Validation

```bash
cd {APP_OR_LIB}
{LANG_IMPORT_VERIFICATION}  # @:b lang[].import
{LANG_TEST_COMMAND}          # @:b lang[].test
{LANG_TYPE_CHECK_COMMAND}    # @:b lang[].type
{LANG_LINT_COMMAND}          # @:b lang[].lint
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Import error | Missing dependency | Complete blocking tasks |
| Type error | Wrong annotation | Verify type mapping |
| Test failure | Behavior change | Check preservation notes |
| Low coverage | Missing edge cases | Add error path tests |

**Debug:**

```bash
{LANG_IMPORT_DEBUG}  # @:b lang[].debug_import
{LANG_SINGLE_TEST}   # @:b lang[].debug_test
{LANG_COVERAGE}      # @:b lang[].coverage
```

---

## Recovery

**If fails:**

1. Revert: `git checkout HEAD -- {FILE_PATH}`
2. Review blocking tasks
3. Check logs: `{LANG_TEST_COMMAND} 2>&1 | tail -50`

**Checkpoint**: {SAFE_STOPPING_POINT}
**Resume from**: {HOW_TO_CONTINUE}

---

## Definition of Done

- [ ] {CRITERION_1}
- [ ] {CRITERION_2}
- [ ] {CRITERION_3}
- [ ] Type checker: zero errors
- [ ] Linter: zero violations

<!-- REF: role[].quality -->

---

## Grouped Task File Structure (P{N}-{TYPE}.md)

<!-- GUIDE: Use for simple related tasks (complexity ≤6) in same phase and type -->

```markdown
# Phase {N}: {TYPE} Tasks

**Epic/PR**: {PHASE_NAME} - {PHASE_DESCRIPTION}
**Task Count**: {N} tasks
**Combined Complexity**: {LEVEL_EMOJI} {TOTAL}/20 (avg {AVG}/task)
**Type**: {SETUP|TEST|IMPLEMENTATION|REFACTOR|EXPORT}

## Shared Context

| Artifact | Location | Relevance |
|----------|----------|-----------|
| User Story | `spec.md#{US_ID}` | Requirements |
| Architecture | `plan.md#{SECTION}` | Design decisions |
| Reference | `{FILE_PATH}:{LINES}` | Pattern to follow |

## Dev Patterns (Shared)

| Pattern | File | Purpose |
|---------|------|---------|
| {Name} | `docs/dev-pattern/{NN}-{name}.md` | {What to apply} |

---

## T{ID1}: {TITLE1}

**Complexity**: {LEVEL_EMOJI} {N}/20 | **Priority**: {P1-P4} | **Story**: {US_ID}

### Objective

{Single sentence by task type}

### Acceptance Criteria

- [ ] AC1: {Measurable criterion}
- [ ] AC2: {Measurable criterion}

### Target Files

- `{FILE_PATH_1}`
- `{FILE_PATH_2}`

---

## T{ID2}: {TITLE2}

**Complexity**: {LEVEL_EMOJI} {N}/20 | **Priority**: {P1-P4} | **Story**: {US_ID}

### Objective

{Single sentence by task type}

### Acceptance Criteria

- [ ] AC1: {Measurable criterion}

### Target Files

- `{FILE_PATH_1}`

---

## Group Dependencies

| Task | Blocks | Blocked By | Parallel With |
|------|--------|------------|---------------|
| T{ID1} | T{X} | - | T{ID2} |
| T{ID2} | T{Y} | - | T{ID1} |

## Validation (All Tasks)

{Copy-paste ready commands for entire group}

## Error Handling

| Error | Task | Recovery |
|-------|------|----------|
| Import error | T{ID} | Complete blocking tasks first |
| Test failure | T{ID} | Check behavior preservation |
| Type error | T{ID} | Verify type mapping table |

**Rollback**: `git checkout HEAD -- {FILE_PATHS}`

## AI Implementation Prompt

{Generated from unified template with group mode}
```

---

## Index File Structure (_INDEX.md)

<!-- GUIDE: Generated summary of all task files with dependencies -->

```markdown
# Task Index: {FEATURE_NAME}

**Generated**: {TIMESTAMP}
**Total Tasks**: {COUNT}
**Source**: tasks.md

## Summary Table

| ID | Title | Priority | Story | Complexity | File | Blocks | Blocked By |
|----|-------|----------|-------|------------|------|--------|------------|
| T001 | {Title} | P1 | INFRA | {EMOJI} {N}/20 | `{FILE}.md` | T{X} | - |

## File Organization

| File | Type | Tasks | Combined Complexity |
|------|------|-------|---------------------|
| `P1-SETUP.md` | Grouped | T001, T002, T003 | {EMOJI} {N}/{MAX} (avg {AVG}) |
| `T006.md` | Individual | T006 | {EMOJI} {N}/20 |

## Complexity Distribution

| Level | Count | Tasks |
|-------|-------|-------|
| 🟢 Simple (1-5) | {N} | T001, T003 |
| 🟡 Moderate (6-10) | {N} | T002, T005 |
| 🟠 Complex (11-15) | {N} | T010 |
| 🔴 Critical (16-20) | {N} | T015 |

## Phase Breakdown

### Phase {N}: {PHASE_NAME}

| File | Tasks | Type | Execution |
|------|-------|------|-----------|
| `P{N}-{TYPE}.md` | T{IDS} | {TYPE} | Parallel/Sequential |

## Dependency Graph

```mermaid
graph TD
    subgraph Phase1[Phase 1]
        subgraph G1[P1-SETUP.md]
            T001[T001 {EMOJI}]
            T002[T002 {EMOJI}]
        end
        subgraph G2[P1-TEST.md]
            T003[T003 {EMOJI}]
            T004[T004 {EMOJI}]
        end
    end
    subgraph Phase2[Phase 2]
        T006[T006 {EMOJI}]
    end
    G1 --> G2
    G2 --> T006
```

## Recommended Execution Order

1. **Group P1-SETUP.md**: T001, T002 (parallel within group)
2. **Group P1-TEST.md**: T003, T004 (parallel, depends on P1-SETUP)
3. **Individual T006.md**: Complex task (sequential)

## Index Validation

- [ ] All task files exist in tasks/ directory
- [ ] No orphaned dependencies (all referenced tasks exist)
- [ ] No circular dependencies in graph
- [ ] Mermaid graph renders without errors
- [ ] Complexity totals match individual scores
- [ ] Phase numbers are sequential
```

---

## Quick Reference Tables

### Objective Patterns by Type

| Type | Pattern |
|------|---------|
| SETUP | "Create the `{directory}` package structure for {purpose}." |
| TEST | "Write tests for {component} ensuring {behavior} (TDD red phase)." |
| IMPLEMENTATION | "Implement {component} that {primary_function}." |
| REFACTOR | "Refactor {component} to extend {base_class}, preserving behavior." |
| EXPORT | "Update exports in `{module}` to expose {components} publicly." |

### Guidelines by Type

| Type | Focus |
|------|-------|
| SETUP | Directory structure, placeholder files, import paths to support |
| TEST | Test categories (happy/error/edge), TDD workflow (write failing → verify RED → stop) |
| IMPLEMENTATION | Structure overview (class hierarchy), logic flow, type mapping |
| REFACTOR | Behavior preservation checklist (cache keys, error types, return format, side effects) |
| EXPORT | Component list, import paths to verify, public API updates |

### Acceptance Criteria Templates

| Type | Criteria |
|------|----------|
| SETUP | Create directory, module init with docstring, placeholder files, verify imports |
| TEST | Happy path, error handling, edge cases, protocol compliance, tests fail (TDD red) |
| IMPLEMENTATION | Implement interface, primary functionality, error handling, edge cases, tests pass |
| REFACTOR | Extends base, implements abstracts only, removes redundant, existing tests pass |
| EXPORT | Export components, re-export from parent, update public API, verify paths, no cycles |

---

## AI Prompts by Task Type

<!-- GUIDE: Select ONE prompt matching task type | ready-to-use with role + constraints -->
<!-- NOTE: These are ready-to-use execution prompts. For condensed lookup, see Quick Reference Tables above. -->

### SETUP Task Prompt

```text
## Role: Senior Module Architect
You create structure, NOT implementation. You follow project conventions exactly.

## Task: {TASK_TITLE}

## Context
Creating module structure for {FEATURE_NAME}, task {TASK_ID}.

## Requirements
{ACCEPTANCE_CRITERIA_AS_BULLETS}

## Instructions
1. Create directory/module at {PATH}
2. Create initialization file with module documentation (NO implementation)
3. Create placeholder files: {FILE_LIST}
4. Verify imports work

## Deliverables
- [ ] {DIRECTORY}/ structure created
- [ ] {PLACEHOLDER_FILES}

## Validation
{LANG_IMPORT_VERIFICATION_COMMAND}
```

### TEST Task Prompt (TDD)

```text
## Role: TDD Practitioner & QA Engineer
You write tests FIRST, implementation NEVER. You hunt for edge cases.

## Task: {TASK_TITLE}

## Context
Writing tests for {COMPONENT} following TDD (task {TASK_ID}).
These tests MUST FAIL until implementation is complete.

## Requirements
{ACCEPTANCE_CRITERIA_AS_BULLETS}

## TDD Instructions
1. Load test patterns from {TEST_PATTERN_DOC}
2. Create test file at {TEST_PATH}
3. For each behavior, write a test that:
   - Documents expected behavior
   - Fails with meaningful assertion message
   - Is independent of other tests

## Test Categories
- Happy path: {N} tests
- Error handling: {N} tests
- Edge cases: {N} tests
- Interface compliance: {N} tests

## Deliverables
- [ ] {TEST_FILE}
- [ ] All tests FAILING (red phase)

## Validation
{LANG_TEST_COMMAND}  # Should show {N} FAILED
```

### IMPLEMENTATION Task Prompt

```text
## Role: Domain Expert + Clean Code Advocate
You follow existing patterns EXACTLY. You implement ALL acceptance criteria, nothing more.

## Task: {TASK_TITLE}

## Context
Implementing {COMPONENT} for {FEATURE_NAME} (task {TASK_ID}).
Tests already exist in {TEST_TASK_REF} - make them pass.

## Requirements
{ACCEPTANCE_CRITERIA_AS_BULLETS}

## Patterns to Load (REQUIRED)
1. {PRIMARY_PATTERN_PATH} - Primary pattern
2. {SECONDARY_PATTERN_PATH} - Supporting pattern
3. {REFERENCE_IMPLEMENTATION} - Follow this style

## Instructions
1. Read ALL pattern files before writing code
2. Study reference implementation for style
3. Implement to make tests pass (don't modify tests)
4. Add type annotations to ALL public APIs
5. Add documentation to classes and public methods

## Deliverables
- [ ] {IMPLEMENTATION_FILE}
- [ ] Tests pass ({TEST_TASK_REF})
- [ ] >{COVERAGE_TARGET}% coverage
- [ ] Zero type/lint errors

## Validation
{LANG_LINT_COMMAND}
{LANG_TYPE_CHECK_COMMAND}
{LANG_TEST_COMMAND}
```

### REFACTOR Task Prompt

```text
## Role: Legacy Code Specialist
You NEVER change observable behavior. You run tests BEFORE and AFTER every change.

## Task: {TASK_TITLE}

## Context
Refactoring {COMPONENT} to use {BASE_CLASS_OR_PATTERN} (task {TASK_ID}).
All existing tests MUST continue to pass without modification.

## Requirements
{ACCEPTANCE_CRITERIA_AS_BULLETS}

## Before Starting
1. Run: `{LANG_TEST_COMMAND}` (capture baseline)
2. Document current behavior
3. Identify all callers of this component

## Migration Steps
1. Change declaration to extend/use {BASE_CLASS_OR_PATTERN}
2. Remove methods now provided by base
3. Implement ONLY required abstract methods: {METHOD_LIST}
4. Run tests after EACH step

## Behavior Preservation
- [ ] Error messages identical
- [ ] Return types identical
- [ ] Side effects identical

## Deliverables
- [ ] Refactored {FILE}
- [ ] All existing tests pass (unchanged)
- [ ] Code reduction: ~{N}% fewer lines

## Validation
{LANG_TEST_COMMAND}
{LANG_TYPE_CHECK_COMMAND}

## Rollback
git checkout HEAD -- {FILE_PATH}
```

### EXPORT Task Prompt

```text
## Role: API Surface Designer
You ONLY modify exports, NEVER implementation. You prevent circular dependencies.

## Task: {TASK_TITLE}

## Context
Updating exports for {MODULE} (task {TASK_ID}).

## Requirements
{ACCEPTANCE_CRITERIA_AS_BULLETS}

## Instructions
1. Add exports for: {COMPONENT_LIST}
2. Update public API declarations (sorted alphabetically)
3. Add re-exports to parent module if needed
4. Verify all import paths work
5. Check for circular dependency issues

## Import Paths to Support
- Short: `{SHORT_IMPORT_PATH}`
- Full: `{FULL_IMPORT_PATH}`

## Deliverables
- [ ] {MODULE} exports updated
- [ ] Parent module exports updated (if applicable)
- [ ] All import paths verified
- [ ] No circular dependencies

## Validation
{LANG_IMPORT_VERIFICATION_COMMAND_1}
{LANG_IMPORT_VERIFICATION_COMMAND_2}
```

---

## Template Examples (Reference Only)

| Task Type | Example Header | Key Focus |
|-----------|----------------|-----------|
| SETUP | `T001 [P1] [INFRA] Create runnable/ module directory` | Structure only, no implementation |
| TEST | `T083 [P1] [US7] [P] Write RequestParser tests` | Tests first, must fail initially |
| IMPL | `T089 [P1] [US7] Implement RequestParser` | Make tests pass, follow patterns |
| REFACTOR | `T112 [P2] [US8] Refactor to use ParserRunnable` | Preserve behavior, existing tests unchanged |
| EXPORT | `T097 [P1] [US7] Update module exports` | Public API only, no implementation changes |

<!-- GUIDE: LOC estimates: SETUP~20 | TEST~50-150 | IMPL~50-200 | REFACTOR~-30-50% | EXPORT~20-50 -->
