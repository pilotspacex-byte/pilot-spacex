---
name: software-prompt-maker
description: This skill transforms complex user requests into optimal software architecture prompts using research-backed techniques (26 Prompting Principles, Chain-of-Thought, incentive-based prompting). Use when designing systems, planning implementations, breaking down complex features, creating technical specifications, or when asked to "design", "architect", "plan implementation", or "break down this feature". Produces step-by-step reasoning, self-evaluating prompts with confidence scoring.
---

# Software Architect Prompt Engineer

## Overview

Transform complex software engineering requests into optimal, production-ready prompts using research-backed techniques from the "Principled Instructions" paper (Bsharat et al., MBZUAI 2023) that demonstrated up to 45% improvement in response quality.

## Core Principles Applied

This skill applies the most effective prompting principles from peer-reviewed research:

| Principle | Technique | Impact |
|-----------|-----------|--------|
| **P3** | Break down complex tasks into sequential steps | +15-25% accuracy |
| **P6** | Stakes language ("$200 tip", "critical to success") | +45% quality |
| **P12** | "Think step by step" / Chain-of-Thought | +20-35% reasoning |
| **P15** | Self-evaluation with test criteria | +10-20% completeness |
| **P16** | Assign expert persona/role | +15-25% domain accuracy |
| **P19** | Chain-of-thought with few-shot examples | +25-40% complex tasks |

## Prompt Generation Workflow

### Phase 1: Requirement Extraction

To transform a user request into an optimal prompt, first extract:

1. **Business Objective** - What outcome does the user need?
2. **Success Criteria** - How will success be measured?
3. **Constraints** - Technical, time, resource limitations
4. **Implicit Needs** - Unstated requirements inferred from context
5. **Edge Cases** - Potential failure scenarios to address

### Phase 2: Prompt Assembly

Assemble the optimal prompt using this structure:

```markdown
# Expert Persona (P16)
You are a [specific expert role] with 15 years specializing in [domain].
You excel at [key capabilities relevant to task].

# Stakes Framing (P6)
This is critical to [business impact]. Could save [value proposition].
I'll tip you $200 for a perfect, production-ready solution.

# Task Decomposition (P3)
Take a deep breath and work through this step by step:

1. [First logical step with clear deliverable]
2. [Second step building on first]
3. [Continue with dependency-aware ordering]
N. [Final step producing complete solution]

# Chain-of-Thought Guidance (P12, P19)
For each step:
- Consider alternatives and tradeoffs
- Identify edge cases and failure modes
- Validate assumptions before proceeding

# Self-Evaluation Framework (P15)
After your solution, rate your confidence (0-1) on:

1. **Completeness**: Did you cover all aspects?
2. **Clarity**: Is the solution easy to understand?
3. **Practicality**: Is it feasible and implementable?
4. **Optimization**: Does it balance performance, accuracy, complexity?
5. **Edge Cases**: Did you address potential challenges?
6. **Self-Evaluation**: Did you include refinement mechanisms?

Provide a score for each (0-1).
If any score < 0.9, refine your answer before presenting.
```

### Phase 3: Domain-Specific Enhancements

#### For System Architecture Tasks

Add to prompt:

```markdown
## Architecture Deliverables
- Component diagram with responsibilities
- Data flow between components
- API contracts (inputs/outputs/errors)
- Non-functional requirements addressed
- Technology selection with rationale
```

#### For Implementation Planning Tasks

Add to prompt:

```markdown
## Implementation Plan Requirements
- Dependency-ordered task sequence
- Parallel vs sequential task identification
- Risk assessment per phase
- Rollback strategy for each stage
- Quality gates between phases
```

#### For Code Design Tasks

Add to prompt:

```markdown
## Code Design Specifications
- Module/class structure with responsibilities
- Interface definitions with contracts
- Error handling strategy
- Testing approach (unit/integration/e2e)
- Documentation requirements
```

## Quick Reference Templates

### Template: Feature Design Prompt

```markdown
You are a Senior Software Architect with 15 years designing scalable distributed systems.
You excel at translating business requirements into clean, maintainable architectures.

This feature design is critical to our platform's success and could save us $50,000
in technical debt if done right. I'll tip you $200 for a production-ready design.

Take a deep breath and design [FEATURE_NAME] step by step:

1. **Understand Requirements**
   - Core functionality needed
   - User personas and workflows
   - Integration points

2. **Define Architecture**
   - Component breakdown with clear responsibilities
   - Data model and relationships
   - API contracts

3. **Address Non-Functional Requirements**
   - Scalability approach
   - Security considerations
   - Performance targets

4. **Plan Implementation**
   - Phased delivery approach
   - Dependencies and risks
   - Quality gates

5. **Validate Design**
   - Review against requirements
   - Identify edge cases
   - Document assumptions

Rate your confidence (0-1) on:
- Completeness: ___
- Clarity: ___
- Practicality: ___
- Optimization: ___
- Edge Cases: ___
- Self-Evaluation: ___

If any < 0.9, refine before presenting.
```

### Template: Technical Decision Prompt

```markdown
You are a Principal Engineer with 15 years making high-stakes technology decisions.
You balance theoretical elegance with practical constraints expertly.

This decision impacts our architecture long-term. Getting it right could save us
$100,000 in migration costs. I'll tip you $200 for a thorough analysis.

Take a deep breath and analyze [DECISION_TOPIC] step by step:

1. **Frame the Decision**
   - What problem are we solving?
   - What are the constraints?
   - What does success look like?

2. **Identify Options** (minimum 3)
   - Option A: [Name] - Brief description
   - Option B: [Name] - Brief description
   - Option C: [Name] - Brief description

3. **Analyze Each Option**
   For each:
   - Pros (specific, measurable where possible)
   - Cons (specific, measurable where possible)
   - Risks and mitigations
   - Cost/effort estimate

4. **Make Recommendation**
   - Chosen option with rationale
   - Implementation approach
   - Reversibility assessment
   - Success metrics

Rate confidence (0-1): Completeness ___ | Clarity ___ | Practicality ___ | Optimization ___ | Edge Cases ___ | Self-Eval ___
Refine if any < 0.9.
```

### Template: Problem Breakdown Prompt

```markdown
You are a Staff Engineer with 15 years breaking down complex problems into actionable tasks.
You identify dependencies, parallelize where possible, and sequence work optimally.

Breaking this down correctly is critical - wrong sequencing could cost weeks of rework.
I'll tip you $200 for an optimal task breakdown.

Take a deep breath and decompose [PROBLEM] step by step:

1. **Understand the Whole**
   - What is the end state?
   - What are the boundaries?
   - What exists already?

2. **Identify Components**
   - List all distinct pieces of work
   - Classify: must-have vs nice-to-have
   - Estimate relative complexity (S/M/L)

3. **Map Dependencies**
   - Which tasks block others?
   - Which can run in parallel?
   - What external dependencies exist?

4. **Sequence Optimally**
   - Create dependency graph
   - Identify critical path
   - Optimize for parallel execution

5. **Define Deliverables**
   For each task:
   - Clear acceptance criteria
   - Definition of done
   - Estimated effort

Rate confidence (0-1): Completeness ___ | Clarity ___ | Practicality ___ | Optimization ___ | Edge Cases ___ | Self-Eval ___
Refine if any < 0.9.
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Better Approach |
|--------------|---------|-----------------|
| Vague persona | "You are helpful" lacks domain focus | "You are a [specific expert] with [years] in [domain]" |
| Missing stakes | No motivation for quality | Add business impact + monetary incentive |
| Monolithic task | Overwhelms reasoning | Break into numbered steps |
| No self-check | Unverified output quality | Add confidence scoring + refinement trigger |
| Generic output | "Give me a solution" | Specify deliverable format explicitly |

## Integration with Project Patterns

When using in pilot-space, reference:

- `docs/dev-pattern/45-pilot-space-patterns.md` for project-specific conventions
- `docs/architect/` for architecture documentation templates
- `specs/001-pilot-space-mvp/` for specification formats

## Research Sources

- Bsharat, S.M., Myrzakhan, A., & Shen, Z. (2023). "Principled Instructions Are All You Need for Questioning LLaMA-1/2, GPT-3.5/4". arXiv:2312.16171
- Analytics Vidhya (2024). "26 Prompting Principles to Improve LLM Performance"
- SuperAnnotate (2024). "26 Prompting Tricks to Improve LLMs"
