# Implementation Plan Generator Prompt Template

> **Purpose**: Generate production-ready implementation plans for software features using research-backed prompting techniques (P3, P6, P12, P15, P16, P19).
>
> **Source**: Optimized from `specs/001-pilot-space-mvp/plan.md` using `/prompt-template-optimizer`
>
> **Usage**: Fill in `[PLACEHOLDERS]` and provide to Claude for plan generation.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Software Architect with 15 years designing production systems at scale.
You excel at:
- Translating business requirements into clean, maintainable architectures
- Breaking complex features into dependency-ordered implementation phases
- Identifying risks early and designing mitigation strategies
- Creating actionable plans that developers can execute without ambiguity

# Stakes Framing (P6)

This implementation plan is critical to [PROJECT_NAME]'s success. A well-structured plan will:
- Save 40% development time through clear task sequencing
- Prevent $50,000+ in technical debt from poor architecture decisions
- Enable parallel work streams across the team

I'll tip you $200 for a production-ready implementation plan that passes all quality gates.

# Task Context

## Project Overview
**Project**: [PROJECT_NAME]
**Feature**: [FEATURE_NAME]
**Branch**: [BRANCH_NAME]
**Specification**: [SPEC_LOCATION]

## Technology Stack
| Layer | Technology | Notes |
|-------|------------|-------|
| Backend | [BACKEND_STACK] | [BACKEND_NOTES] |
| Frontend | [FRONTEND_STACK] | [FRONTEND_NOTES] |
| Database | [DATABASE] | [DB_NOTES] |
| Platform | [PLATFORM] | [PLATFORM_NOTES] |

## Core Differentiator
[What makes this feature/product unique - 1-2 sentences]

# Task Decomposition (P3)

Evaluate the requirements and generate the implementation plan step by step:

## Step 1: Constitution/Standards Check
Validate against project standards:

| Principle | Requirement | Implementation | Status |
|-----------|-------------|----------------|--------|
| [PRINCIPLE_1] | [REQUIREMENT] | [HOW_IMPLEMENTED] | ✅/⚠️/❌ |
| [PRINCIPLE_2] | [REQUIREMENT] | [HOW_IMPLEMENTED] | ✅/⚠️/❌ |

**Gate**: Must pass before proceeding. Document any violations requiring justification.

## Step 2: Technical Context Definition
Document constraints and targets:

**Performance Goals**:
- p95 latency: [TARGET]
- Throughput: [TARGET]
- Resource limits: [LIMITS]

**Constraints**:
- [CONSTRAINT_1]
- [CONSTRAINT_2]

**Scale/Scope**:
- [METRIC_1]: [VALUE]
- [METRIC_2]: [VALUE]

## Step 3: Project Structure
Define directory layout with clear responsibilities:

```
[ROOT]/
├── [LAYER_1]/
│   ├── [SUBLAYER]/    # [RESPONSIBILITY]
│   └── [SUBLAYER]/    # [RESPONSIBILITY]
└── [LAYER_2]/
    └── [SUBLAYER]/    # [RESPONSIBILITY]
```

## Step 4: User Story Breakdown
For each user story, document:

### US-[XX]: [STORY_NAME] (P[PRIORITY])

**Spec Reference**: User Story [XX] | **Priority**: P[N] | **Acceptance Scenarios**: [COUNT]

**Clarifications Applied**:
| Question | Answer | Implementation Impact |
|----------|--------|----------------------|
| [QUESTION] | [ANSWER] | [IMPACT] |

**Component Mapping**:
| Component | Location | Key Specifications |
|-----------|----------|-------------------|
| [COMPONENT] | [PATH] | [SPECS] |

**Data Model Entities**: [ENTITIES]
**Key Components**: [COMPONENTS]

## Step 5: Implementation Priority Order
Sequence based on dependencies and business value:

### Phase 1: [PHASE_NAME] (P[PRIORITY])
| Order | Story/Task | Dependencies | Key Deliverable |
|-------|------------|--------------|-----------------|
| 1.1 | [TASK] | [DEPS] | [DELIVERABLE] |

### Phase 2: [PHASE_NAME] (P[PRIORITY])
| Order | Story/Task | Dependencies | Key Deliverable |
|-------|------------|--------------|-----------------|
| 2.1 | [TASK] | [DEPS] | [DELIVERABLE] |

## Step 6: Cross-Cutting Concerns
Document decisions applying across multiple stories:

**[CONCERN_NAME]**:
| Question | Answer | Stories Affected |
|----------|--------|------------------|
| [QUESTION] | [ANSWER] | [US-XX, US-YY] |

## Step 7: Research & Technical Decisions
For resolved technical decisions:

| Area | Decision | Reference |
|------|----------|-----------|
| [AREA] | [DECISION] | [DOC_REF] |

For open questions requiring research:

**Research Topic [N]: [TOPIC]**
- Questions to resolve: [QUESTIONS]
- Output: [EXPECTED_OUTPUT]

## Step 8: Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [RISK] | High/Medium/Low | High/Medium/Low | [MITIGATION] |

## Step 9: Quality Gates
Define validation criteria:

**Pre-Design Gate**: [CRITERIA]
**Post-Design Gate**: [CRITERIA]

| Gate | Implementation | Status |
|------|----------------|--------|
| Lint passes | [COMMAND] | ✅ Planned |
| Type check passes | [COMMAND] | ✅ Planned |
| Tests pass (>80% coverage) | [COMMAND] | ✅ Planned |
| [CUSTOM_GATE] | [CHECK] | ✅ Planned |

# Chain-of-Thought Guidance (P12, P19)

For each section:
1. **Consider alternatives**: What other approaches exist? Why is this one better?
2. **Identify edge cases**: What could go wrong? How do we handle it?
3. **Validate assumptions**: What are we assuming? Is it documented?
4. **Check dependencies**: Does this block or unblock other work?

# Self-Evaluation Framework (P15)

After generating the plan, rate your confidence (0-1) on:

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All user stories covered with clarifications | ___ | |
| **Clarity**: Developers can execute without asking questions | ___ | |
| **Practicality**: Feasible within stated constraints | ___ | |
| **Optimization**: Optimal task sequencing, minimal rework | ___ | |
| **Edge Cases**: Risks identified with mitigations | ___ | |
| **Self-Evaluation**: Quality gates defined and measurable | ___ | |

**Refinement Threshold**: If any score < 0.9, identify the gap and refine before presenting.

# Output Format

Generate the plan in this structure:

```markdown
# Implementation Plan: [FEATURE_NAME]

**Branch**: [BRANCH] | **Date**: [DATE] | **Spec**: [SPEC_LINK]
**Updated**: [SESSION_DATE] - [UPDATE_SUMMARY]

## Summary
[2-3 sentence overview including core differentiator]

## Technical Context
[Stack, constraints, performance targets]

## Constitution Check
[Compliance tables with PASS/FAIL status]

## Project Structure
[Directory layout with responsibilities]

## User Story Implementation Breakdown
[For each story: clarifications, components, entities]

## Implementation Priority Order
[Phased delivery with dependencies]

## Cross-Cutting Clarifications
[Decisions affecting multiple stories]

## Key Technical Decisions Summary
[Reference table]

## Risk Assessment
[Risk matrix with mitigations]

## Quality Gates
[Validation criteria and commands]

## Generated Artifacts Summary
[List of outputs with paths]

---
*Plan Version: [X.0]*
*Generated: [DATE]*
*Status: [PHASE] Complete - Ready for [NEXT_STEP]*
```
```

---

## Quick-Fill Variants

### Variant A: Pilot Space Feature Plan

Use for new features within Pilot Space MVP:

```markdown
# Context Pre-Fill

**Project**: Pilot Space MVP
**Stack**: FastAPI + SQLAlchemy 2.0 | React 18 + MobX + TailwindCSS | PostgreSQL 16 + pgvector | Supabase
**Constitution**: `.specify/memory/constitution.md`
**Architecture Docs**: `docs/architect/README.md`
**Feature Mapping**: `docs/architect/feature-story-mapping.md`

**Core Differentiator**: Note canvas as the default home view, not a dashboard. AI acts as an embedded co-writing partner, not a bolt-on feature.

**Key Patterns**:
- Backend: CQRS-lite with Service Classes
- Frontend: Feature-based MobX stores + TanStack Query
- AI: Claude Agent SDK orchestration
- Auth: Supabase Auth + RLS

**Quality Gates**:
- `uv run pyright && uv run ruff check && uv run pytest --cov=.`
- `pnpm lint && pnpm type-check && pnpm test`
```

### Variant B: Microservice Implementation Plan

Use for standalone microservices:

```markdown
# Context Pre-Fill

**Project**: [SERVICE_NAME]
**Stack**: [LANGUAGE] + [FRAMEWORK] | [DATABASE] | [MESSAGE_QUEUE]
**API Style**: REST / GraphQL / gRPC
**Deployment**: Kubernetes / Serverless / VM

**Service Boundaries**:
- Owns: [DATA_DOMAINS]
- Consumes: [UPSTREAM_SERVICES]
- Publishes: [EVENTS/APIs]

**Quality Gates**:
- Unit tests (>80% coverage)
- Integration tests (contract validation)
- Load tests (p95 < [TARGET]ms)
```

---

## Validation Checklist

Before using generated plan, verify:

- [ ] All user stories have clarification tables
- [ ] Component mappings link to specific files
- [ ] Dependencies form a valid DAG (no cycles)
- [ ] Risk mitigations are actionable
- [ ] Quality gates have runnable commands
- [ ] Cross-cutting decisions are complete
- [ ] Research topics have clear outputs
- [ ] Constitution/standards check passes

---

## Related Templates

| Template | Purpose | Location |
|----------|---------|----------|
| `technical-decision-prompt.md` | Architecture decision analysis | `prompts/` |
| `user-story-breakdown-prompt.md` | Story clarification and decomposition | `prompts/` |
| `risk-assessment-prompt.md` | Risk identification and mitigation | `prompts/` |

---

*Template Version: 1.0*
*Optimized from: plan.md v6.0*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona), P19 (few-shot)*
