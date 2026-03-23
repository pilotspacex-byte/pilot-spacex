---
name: speckit-pm-guide
description: "Senior Project Manager skill for Specification-Driven Development (SDD). Combines structured PM methodology (stakeholder mapping, risk management, resource planning, progress tracking) with three fill-in-the-blank templates for spec/plan/task artifacts. Uses research-backed prompting techniques (Bsharat et al., 2023) for structured reasoning. Triggers on: \"PM guide\", \"project management\", \"spec template\", \"plan template\", \"task template\", \"SDD template\", \"manual speckit\", \"create a spec\", \"create a plan\", \"break down tasks\", \"risk assessment\", \"stakeholder mapping\", \"resource planning\", \"project kickoff\", \"sprint planning\", \"progress tracking\", \"RACI matrix\", \"WBS\", \"work breakdown\", or when the user wants to manage a software project end-to-end."
feature_module: projects
---

# Speckit PM Guide — Project Management & SDD Templates

Senior Project Manager methodology for software delivery, combining structured PM
practices with three SDD lifecycle templates. Each artifact is self-contained — no CLI
commands or automation required.

## Expert Persona

When executing this skill, operate as a Senior Project Manager with 15 years specializing
in software project delivery, stakeholder management, and agile/hybrid methodologies.
Capabilities: translating vague business needs into structured project plans with clear
milestones, risk mitigation, and resource allocation.

## When to Use

### SDD Lifecycle (Artifact Creation)
- User wants to create a feature specification manually
- User needs to write an implementation plan from scratch
- User wants to break down a plan into executable tasks

### Project Management (Orchestration)
- User needs a project kickoff or charter
- User wants stakeholder mapping or RACI matrix
- User needs risk assessment and mitigation planning
- User wants resource allocation or capacity planning
- User needs progress tracking setup (burndown, EVM)
- User wants sprint/iteration planning framework
- User asks for communication plan or status reporting
- User needs rollback/contingency planning
- User wants a full Work Breakdown Structure (WBS)

## Reasoning Approach

Apply structured reasoning for every deliverable:

1. **Decompose** — Break the request into sequential steps with clear deliverables
2. **Trace** — Every decision must reference a requirement (FR-NNN), constitution article, or business objective
3. **Validate** — After producing any artifact, self-evaluate on: Completeness, Clarity, Practicality, Optimization, Edge Cases (score 0-1 each; refine if any < 0.9)
4. **Consider alternatives** — For every significant decision, evaluate 2+ options with tradeoffs

## Templates

### SDD Artifact Templates

Load the template matching the user's current need:

| Template | Reference | Produces | Prerequisite |
|----------|-----------|----------|-------------|
| Specification | `references/template-specify.md` | `spec.md` + `checklists/requirements.md` | Feature idea |
| Plan | `references/template-plan.md` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` | Completed spec.md |
| Tasks | `references/template-tasks.md` | `tasks.md` | Completed plan.md |
| Implementation | `references/template-implement.md` | Production-ready code | Completed tasks.md |

### PM Artifact Templates

Generate these artifacts on demand when project management context is needed:

| Artifact | When to Produce | Key Sections |
|----------|----------------|-------------|
| **Project Charter** | Project kickoff | Objective, scope, stakeholders, success criteria, constraints |
| **RACI Matrix** | Stakeholder alignment | Deliverable x Stakeholder responsibility mapping (R/A/C/I) |
| **Risk Register** | Planning phase or on-demand | ID, description, probability (1-5), impact (1-5), score, response strategy, owner, trigger |
| **Resource Plan** | Team allocation | Skills-to-tasks mapping, capacity, key-person risk (bus factor), onboarding needs |
| **Communication Plan** | Stakeholder management | Stakeholder, info needed, format, frequency, owner |
| **WBS** | Detailed planning | Hierarchical decomposition, work packages (max 40h each), unique IDs, dependencies |
| **Budget Estimate** | When cost tracking needed | Bottom-up from WBS, direct + indirect costs, variance thresholds |
| **Sprint Plan** | Iteration planning | Iteration goals, Definition of Ready/Done, velocity tracking, backlog prioritization |
| **Status Report** | Progress tracking | Milestones, burndown/EVM metrics (SPI, CPI), blockers, risks, next actions |

## Workflow

### Prerequisites

- Defined specify name and feature description
- Clear feature idea or business need
- Access to stakeholders for input/validation
- Understanding of organizational PM practices

### Full Project Lifecycle

```
PROJECT KICKOFF
├── switch to {NNN}-{feature-name} branch
├── Project Charter
├── Stakeholder Map + RACI Matrix
├── Risk Register (initial)
├── Communication Plan
│
├── PHASE 1: Specification (template-specify.md)
│   ├── spec.md
│   └── checklists/requirements.md
│
├── PHASE 2: Planning (template-plan.md)
│   ├── plan.md
│   ├── research.md
│   ├── data-model.md
│   ├── quickstart.md
│   ├── contracts/
│   │   ├── rest-api.md
│   │   └── [domain-specific].md
│   ├── Resource Plan
│   └── WBS (derived from plan.md)
│
├── PHASE 3: Tasks (template-tasks.md)
│   ├── tasks.md
│   └── Sprint Plan(s)
│
├── PHASE 4: Execution (iterative)
│   └── Implement tasks (per tasks.md) by follow `implement.md`
│
├── EXECUTION
│   ├── Status Reports (per sprint/iteration)
│   ├── Risk Register (updated)
│   └── Progress Tracking (burndown/EVM)
│
└── CLOSURE
    ├── Acceptance validation (quickstart.md scenarios)
    └── Retrospective notes
```

### Artifacts Directory Structure

```
specs/{NNN}-{feature-name}/
├── charter.md                    # Project charter (optional)
├── spec.md                       # Feature specification
├── checklists/requirements.md    # Requirements validation
├── plan.md                       # Implementation plan
├── research.md                   # Technical decisions
├── data-model.md                 # Entity definitions
├── quickstart.md                 # Smoke test scenarios
├── contracts/
│   ├── rest-api.md
│   └── [domain-specific].md
├── implement.md                  # Implementation guidelines
├── tasks.md                      # Task breakdown
├── risk-register.md              # Risk tracking (optional)
└── status/                       # Status reports (optional)
    └── sprint-{N}.md
```

### Generate Artifacts

## How to Use

1. **Determine scope** — Does the user need a single artifact or full PM orchestration?
2. **For single artifacts** — Load the corresponding template, fill placeholders, validate
3. **For project orchestration** — Start with Project Charter + RACI, then flow through phases
4. **Walk through sections** — Each section has `{PLACEHOLDER}` fields and instructions
5. **Fill placeholders** — Replace all `{PLACEHOLDER}` values with concrete content
6. **Run validation** — Check all embedded checklists (every `- [ ]` item)
7. **Self-evaluate** — Score deliverable on completeness, clarity, practicality, optimization, edge cases
8. **Write output** — Save completed artifacts to the feature directory

## PM Artifact Guidelines

### Risk Register Format

| ID | Risk | Probability (1-5) | Impact (1-5) | Score | Response | Owner | Trigger |
|----|------|--------------------|--------------|-------|----------|-------|---------|
| R-001 | {description} | {1-5} | {1-5} | {P×I} | {Avoid/Mitigate/Transfer/Accept}: {action} | {name} | {condition} |

**Response strategies:**
- **Avoid** — Eliminate the threat by changing the plan
- **Mitigate** — Reduce probability or impact through proactive action
- **Transfer** — Shift impact to a third party (insurance, outsource)
- **Accept** — Acknowledge and prepare contingency if triggered

### RACI Matrix Format

| Deliverable | {Stakeholder 1} | {Stakeholder 2} | {Stakeholder 3} | {Stakeholder 4} |
|-------------|-----------------|-----------------|-----------------|-----------------|
| {artifact} | R | A | C | I |

- **R** = Responsible (does the work)
- **A** = Accountable (approves/owns the outcome — exactly one per row)
- **C** = Consulted (provides input before decision)
- **I** = Informed (notified after decision)

### Progress Tracking Metrics

| Metric | Formula | Healthy Range | Action if Out of Range |
|--------|---------|---------------|----------------------|
| **SPI** (Schedule Performance Index) | EV / PV | 0.9 - 1.1 | Re-sequence tasks, add resources, or cut scope |
| **CPI** (Cost Performance Index) | EV / AC | 0.9 - 1.1 | Review burn rate, optimize resource allocation |
| **Burndown** | Remaining work / Sprint days | Linear trend | Adjust sprint scope at midpoint |

### Rollback & Contingency

For each phase, define:
1. **Rollback trigger** — What condition activates rollback
2. **Rollback procedure** — Exact steps to reverse changes
3. **Contingency plan** — Alternative path if primary approach fails
4. **Decision authority** — Who approves rollback vs. contingency

## Key Principles

- **WHAT/WHY before HOW**: Spec defines outcomes; plan defines architecture; tasks define work
- **Constitution compliance**: Check `memory/constitution.md` at every phase gate
- **Traceability**: Every decision traces to a requirement (FR-NNN) or constitution article
- **Independent testability**: Every user story can be demo'd in isolation
- **No placeholders in output**: All `{PLACEHOLDER}` values must be replaced before completion
- **Design for failure**: Every plan includes rollback triggers, contingency paths, and risk owners
- **Stakeholder alignment**: RACI defined before execution; communication plan active throughout
- **Measurable progress**: Burndown or EVM metrics tracked per iteration; variance triggers defined
