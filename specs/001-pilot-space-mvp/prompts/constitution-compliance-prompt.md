# Constitution Compliance Prompt Template

> **Purpose**: Validate feature designs against project constitution and standards before implementation.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` Constitution Check pattern and `.specify/memory/constitution.md`
>
> **Usage**: Use as a quality gate before Phase 0 research and after Phase 1 design artifacts.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Software Architect with 15 years ensuring enterprise systems meet governance standards.
You excel at:
- Identifying compliance gaps before they become technical debt
- Translating abstract principles into concrete implementation requirements
- Balancing architectural purity with practical constraints
- Creating clear compliance matrices that teams can action

# Stakes Framing (P6)

This compliance check is critical to [PROJECT_NAME]'s architectural integrity.
A thorough review will:
- Prevent $100,000+ in rework from non-compliant implementations
- Ensure consistent patterns across the codebase
- Maintain stakeholder trust through principled design
- Avoid security and quality vulnerabilities

I'll tip you $200 for a comprehensive compliance assessment that identifies all gaps.

# Task Context

## Feature Overview
**Feature Name**: [FEATURE_NAME]
**Spec Location**: [SPEC_PATH]
**Design Artifacts**: [ARTIFACT_PATHS]

## Constitution Reference
**Constitution Path**: [CONSTITUTION_PATH]
**Version**: [CONSTITUTION_VERSION]

## Check Type
- [ ] **Pre-Design Gate**: Before Phase 0 research
- [ ] **Post-Design Gate**: After Phase 1 design artifacts
- [ ] **Pre-Implementation Gate**: Before coding begins
- [ ] **Pre-Merge Gate**: Before PR approval

# Task Decomposition (P3)

Evaluate compliance step by step:

## Step 1: Principle-by-Principle Assessment

For each constitution principle, evaluate compliance:

### Principle I: [PRINCIPLE_NAME]
| Requirement | Implementation | Status | Gap (if any) |
|-------------|----------------|--------|--------------|
| [REQUIREMENT_1] | [HOW_IMPLEMENTED] | ✅/⚠️/❌ | [GAP_DESCRIPTION] |
| [REQUIREMENT_2] | [HOW_IMPLEMENTED] | ✅/⚠️/❌ | [GAP_DESCRIPTION] |

**Status Legend**:
- ✅ Compliant: Fully meets requirement
- ⚠️ Partial/Deferred: Meets with caveats or planned for later phase
- ❌ Non-Compliant: Does not meet requirement

## Step 2: Technology Standards Check

Validate against mandated technologies:

| Category | Required | Implemented | Status |
|----------|----------|-------------|--------|
| Backend Framework | [REQUIRED] | [ACTUAL] | ✅/❌ |
| Frontend Framework | [REQUIRED] | [ACTUAL] | ✅/❌ |
| Database | [REQUIRED] | [ACTUAL] | ✅/❌ |
| Authentication | [REQUIRED] | [ACTUAL] | ✅/❌ |
| AI Orchestration | [REQUIRED] | [ACTUAL] | ✅/❌ |

## Step 3: Quality Gates Verification

Check that all quality gates are implementable:

| Gate | Implementation Plan | Runnable Command | Status |
|------|---------------------|------------------|--------|
| Lint passes | [TOOL_CONFIG] | [COMMAND] | ✅/❌ |
| Type check passes | [CONFIG] | [COMMAND] | ✅/❌ |
| Tests >80% coverage | [TEST_SETUP] | [COMMAND] | ✅/❌ |
| No N+1 queries | [MONITORING] | [COMMAND] | ✅/❌ |
| File size <700 lines | [ENFORCEMENT] | [HOOK] | ✅/❌ |

## Step 4: UI/UX Compliance

Verify accessibility and design system adherence:

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| WCAG 2.2 AA | [HOW_ACHIEVED] | ✅/⚠️/❌ |
| Color contrast 4.5:1 | [VERIFICATION] | ✅/❌ |
| Focus visibility | [IMPLEMENTATION] | ✅/❌ |
| Keyboard navigation | [COVERAGE] | ✅/⚠️/❌ |
| Screen reader support | [ARIA_PATTERNS] | ✅/⚠️/❌ |
| Touch targets 44x44px | [ENFORCEMENT] | ✅/❌ |
| Performance targets | [METRICS] | ✅/⚠️/❌ |

## Step 5: Gap Analysis

Summarize all identified gaps:

### Critical Gaps (Block Implementation)
| Gap | Principle | Impact | Resolution Required |
|-----|-----------|--------|---------------------|
| [GAP] | [PRINCIPLE_#] | [IMPACT] | [RESOLUTION] |

### Deferred Items (Acceptable for MVP)
| Item | Principle | Justification | Target Phase |
|------|-----------|---------------|--------------|
| [ITEM] | [PRINCIPLE_#] | [WHY_DEFERRED] | Phase [N] |

### Warnings (Monitor)
| Warning | Principle | Risk | Mitigation |
|---------|-----------|------|------------|
| [WARNING] | [PRINCIPLE_#] | [RISK] | [MITIGATION] |

## Step 6: Override Documentation

For any justified deviations:

| Deviation | Principle | Rationale | Approver |
|-----------|-----------|-----------|----------|
| [DEVIATION] | [PRINCIPLE_#] | [DETAILED_RATIONALE] | [WHO_APPROVED] |

**Override Template**:
```markdown
## Override: [DEVIATION_NAME]

**Principle Affected**: [PRINCIPLE]
**Requirement**: [WHAT_WE'RE_DEVIATING_FROM]

**Rationale**:
[WHY_THIS_DEVIATION_IS_ACCEPTABLE]

**Mitigations**:
- [MITIGATION_1]
- [MITIGATION_2]

**Review Date**: [WHEN_TO_REVISIT]
**Approved By**: [APPROVER_NAME]
```

# Chain-of-Thought Guidance (P12)

For each compliance check:
1. **What's the intent?** - Understand why this principle exists
2. **What's the implementation?** - How does the design address it?
3. **What's the gap?** - Where does implementation fall short?
4. **What's the risk?** - If non-compliant, what could go wrong?
5. **What's the resolution?** - How to achieve compliance?

# Self-Evaluation Framework (P15)

After assessment, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All principles checked | ___ | |
| **Accuracy**: Assessments reflect reality | ___ | |
| **Actionability**: Gaps have clear resolutions | ___ | |
| **Fairness**: Deferred items properly justified | ___ | |
| **Risk Awareness**: Warnings properly flagged | ___ | |

**Refinement Threshold**: If any score < 0.9, re-examine that area.

# Output Format

```markdown
# Constitution Compliance Report

**Feature**: [FEATURE_NAME]
**Check Type**: [PRE/POST]-[GATE_TYPE] Gate
**Date**: [DATE]
**Assessor**: [NAME/AI]

## Executive Summary

| Category | Compliant | Partial | Non-Compliant |
|----------|-----------|---------|---------------|
| Principles | [N] | [N] | [N] |
| Technology | [N] | [N] | [N] |
| Quality Gates | [N] | [N] | [N] |
| UI/UX | [N] | [N] | [N] |

**Gate Status**: ✅ PASS / ⚠️ CONDITIONAL PASS / ❌ FAIL

## Detailed Assessment

[PRINCIPLE_BY_PRINCIPLE_TABLES]

## Gap Summary

### Blocking Issues (Must Resolve)
[LIST_OF_CRITICAL_GAPS]

### Deferred Items (Accepted)
[LIST_WITH_JUSTIFICATIONS]

### Warnings (Monitor)
[LIST_WITH_MITIGATIONS]

## Overrides

[DOCUMENTED_DEVIATIONS]

## Recommendations

1. [RECOMMENDATION_1]
2. [RECOMMENDATION_2]

---

*Report Version: 1.0*
*Constitution Version: [VERSION]*
*Next Review: [DATE]
```
```

---

## Quick-Fill Variants

### Variant A: Pilot Space MVP Pre-Design Gate

```markdown
## Constitution Reference
**Path**: `.specify/memory/constitution.md`
**Version**: 1.1.0

## Principles to Check

### Principle I: AI-Human Collaboration First
- AI suggestions presented for human approval
- Critical actions require explicit confirmation
- AI provides rationale and alternatives
- Configurable AI behavior per workspace/project

### Principle II: Note-Second Approach
- Quick capture via Stickies
- AI-assisted note-to-document conversion
- Related notes linked to issues

### Principle III: Documentation-Third Approach
- Auto-generated API documentation
- Living documentation updates with code
- Architecture diagram generation

### Principle IV: Task-Centric Workflow
- Feature decomposition into tasks
- AI-suggested acceptance criteria
- Task dependencies identified
- Traceability to parent feature

### Principle V: Collaboration & Knowledge Sharing
- Pattern Library
- ADR support (Phase 2 acceptable)
- Expertise mapping
- Knowledge Graph

### Principle VI: Agile Integration
- AI-enhanced sprint planning
- Retrospective insights (Phase 2 acceptable)
- Blocker detection

### Principle VII: Notation & Standards
- UML Generation (Mermaid + PlantUML)
- C4 Model support
- Mermaid integration

## Technology Standards
| Category | Required |
|----------|----------|
| Backend | FastAPI + SQLAlchemy 2.0 async |
| Frontend | Next.js 14+ + React 18 + TypeScript |
| State | MobX + TanStack Query |
| Styling | TailwindCSS |
| Database | PostgreSQL 16+ with pgvector |
| AI | BYOK only, Claude Agent SDK orchestration |
| Cache | Redis |
| Queue | Supabase Queues (pgmq) |
| Auth | Supabase Auth + RLS |
| Storage | Supabase Storage |
| Search | Meilisearch |
| Graph Viz | Sigma.js + react-sigma |
```

### Variant B: Quality Gate Checklist

```markdown
## Quality Gates (All Must Pass)

**Backend (Python)**:
```bash
uv run pyright && uv run ruff check && uv run pytest --cov=. --cov-fail-under=80
```

**Frontend (TypeScript)**:
```bash
pnpm lint && pnpm type-check && pnpm test --coverage
```

**Pre-Commit Hooks**:
- [ ] No TODOs/mocks in production paths
- [ ] File size <700 lines
- [ ] Secrets not in code
- [ ] No blocking I/O in async functions

**Security**:
- [ ] Input validation at API boundaries (Pydantic v2)
- [ ] OWASP Top 10 compliance
- [ ] RLS policies verified
```

---

## Validation Checklist

Before proceeding past gate, verify:

- [ ] All principles have status (✅/⚠️/❌)
- [ ] All ❌ items have resolution plans
- [ ] All ⚠️ items have justification
- [ ] Technology stack matches requirements
- [ ] Quality gate commands are runnable
- [ ] UI/UX accessibility requirements documented
- [ ] Any overrides are formally documented

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `.specify/memory/constitution.md` | Project constitution |
| `docs/DESIGN_DECISIONS.md` | Architecture decisions |
| `docs/architect/FEATURES_CHECKLIST.md` | Feature compliance tracker |
| `specs/001-pilot-space-mvp/validation_report.md` | Previous validation |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.1 Constitution Check pattern*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
