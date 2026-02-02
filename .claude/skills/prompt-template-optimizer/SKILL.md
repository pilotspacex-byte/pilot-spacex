---
name: prompt-template-optimizer
description: This skill should be used when creating, optimizing, or reviewing prompts for any LLM interaction including Claude Code artifacts (commands, hooks, skills), sub-agent prompts, API prompts, and external LLM integrations. Provides standards-based prompt engineering with balanced token optimization.
---

# Prompt Template Architect

Create, optimize, and review prompts for any LLM interaction using research-backed techniques and balanced standards.

## When to Invoke

- Creating new Claude Code skills, commands, or hooks
- Writing prompts for sub-agents (Task tool)
- Designing API prompts for production systems
- Optimizing existing prompts for token efficiency
- Reviewing prompt quality before deployment

## Modes

### Create Mode

`/prompt-template-architect create [type]`

Types: `skill` | `command` | `hook` | `sub-agent` | `api-prompt` | `system-prompt`

### Optimize Mode

`/prompt-template-architect optimize`

Analyze existing prompt, score against standards, suggest improvements.

---

## Core Workflow

### Phase 1: Assess Requirements

1. **Identify prompt type** and target LLM (Claude, GPT, Gemini, etc.)
2. **Determine complexity**: Simple (single task) | Moderate (multi-step) | Complex (chained/agentic)
3. **Establish constraints**: Token budget, latency, reliability requirements
4. **Clarify output**: Structured (JSON, code) vs open-ended (text, creative)

### Phase 1.5: Calibrate for Target Model

Different models respond differently to instruction intensity:

| Model | Instruction Intensity | Notes |
|-------|----------------------|-------|
| **Opus 4.5** | Low-Moderate | Highly responsive; aggressive language causes overtriggering |
| Sonnet 4.x | Moderate | Standard patterns work well |
| Opus 4.1 | Moderate-High | May need stronger emphasis |
| Haiku 4.5 | Moderate | Efficient, follows direct instructions |
| GPT-4/4o | Moderate-High | Responds well to explicit constraints |
| Gemini | Moderate | XML less effective; prefer Markdown |

**Opus 4.5 Calibration** (apply when targeting Opus 4.5):

| Aggressive (avoid) | Calibrated (use) |
|--------------------|------------------|
| `CRITICAL: You MUST...` | `You should...` |
| `ALWAYS do X` | `Do X` |
| `NEVER skip...` | `Don't skip...` |
| `NO EXCEPTIONS` | Remove or soften |
| `IMMEDIATELY after X` | `After X, do Y` |
| `Think step by step` | `Evaluate step by step` |

### Phase 2: Select Techniques

Load `references/techniques-cheatsheet.md` and select based on complexity:

| Complexity | Recommended Techniques |
|------------|------------------------|
| Simple | Zero-shot, Explicit instructions, Output priming |
| Moderate | Few-shot, Role prompting, Chain-of-thought |
| Complex | Prompt chaining, ReAct, Goal decomposition, Meta-prompting |

### Phase 2.5: Apply Research-Backed Enhancements

Load `references/26-prompting-principles.md` for high-impact techniques (Bsharat et al., 2023):

| Principle | Technique | Impact | When to Use |
|-----------|-----------|--------|-------------|
| **P6** | Stakes/incentive language | **+45%** | All production prompts |
| **P16** | Expert persona (specific role + years) | +15-25% | Domain-specific tasks |
| **P3** | Task decomposition (numbered steps) | +15-25% | Multi-step workflows |
| **P12** | Chain-of-thought ("step by step") | +20-35% | Reasoning tasks |
| **P15** | Self-evaluation (confidence scoring) | +10-20% | Quality-critical outputs |
| **P19** | CoT + few-shot combination | +25-40% | Complex analysis |

**Stakes Language Pattern (P6)**:

```markdown
This is critical to [business impact]. Could save [value proposition].
I'll tip you $200 for a perfect, production-ready solution.
```

**Expert Persona Pattern (P16)**:

```markdown
You are a [Specific Title] with [X] years specializing in [domain].
You excel at [key capabilities relevant to task].
```

**Self-Evaluation Pattern (P15)**:

```markdown
After your solution, rate your confidence (0-1) on:
1. Completeness: Did you cover all aspects?
2. Clarity: Is the solution easy to understand?
3. Practicality: Is it feasible and implementable?

If any score < 0.9, refine your answer before presenting.
```

### Phase 3: Apply Standards

**Token Optimization Strategy (Balanced)**:
- Use **Markdown** for instructions (Claude-native, high readability)
- Use **TOON** for data arrays only when >30% token savings expected
- Load `references/token-optimization.md` for TOON syntax

**Structure Pattern** (Research-Enhanced):

```markdown
## Expert Persona (P16)
[Specific Title] with [X] years in [domain]. Excel at [capabilities].

## Stakes (P6)
This is critical to [impact]. Could save [value]. Tip $200 for perfect solution.

## Context
Background information, constraints, domain knowledge.

## Instructions (P3)
Take a deep breath and work through this step by step:
1. [First action with deliverable]
2. [Second action building on first]
3. [Continue with dependency-aware ordering]

<examples>
2-5 input-output pairs demonstrating expected behavior.
</examples>

## Output Format
Explicit format specification: JSON schema, markdown structure, or prose constraints.

## Self-Evaluation (P15)
Rate confidence (0-1): Completeness | Clarity | Practicality | Edge Cases
If any < 0.9, refine before presenting.
```

### Phase 4: Validate

Score against `assets/prompt-standards-rubric.md`:

| Criterion | Weight | Check |
|-----------|--------|-------|
| Clarity | 25% | Unambiguous instructions, no hedging |
| Completeness | 20% | All required context provided |
| Token efficiency | 20% | No redundancy, appropriate technique selection |
| Output specification | 15% | Clear format constraints |
| Error handling | 10% | Graceful degradation guidance |
| Testability | 10% | Measurable success criteria |

**Passing threshold**: 70% for production, 85% for high-stakes prompts.

**Flexibility rule**: Deviation allowed when justified (e.g., token budget forces simpler structure). Document rationale.

---

## Prompt Type Templates

### Claude Code Skill

```markdown
---
name: {skill-name}
description: This skill should be used when {trigger conditions}. {What it provides}.
---

# {Skill Title}

{1-2 sentence purpose statement in imperative form.}

## When to Invoke

- {Trigger condition 1}
- {Trigger condition 2}

## Workflow

### Step 1: {Action}
{Imperative instructions. Use "To accomplish X, do Y" not "You should".}

## References

| File | Purpose | When to Load |
|------|---------|--------------|
| `references/X.md` | {Purpose} | {Condition} |
```

### Sub-Agent Prompt (Task Tool) - Research-Enhanced

```markdown
## Expert Role (P16)
You are a {Specific Title} with {X} years in {domain}.
You excel at {key capabilities relevant to this task}.

## Stakes (P6)
This task is critical to {business impact}. Could save {value}.
Deliver a production-ready solution.

## Task: {Brief title}

## Requirements
- Scope: {What is in/out of scope}
- Constraints: {Token budget, time, dependencies}

## Instructions (P3)
Take a deep breath and work through this step by step:
1. {First action with clear deliverable}
2. {Second action building on first}
3. {Validation step}

## Deliverables
- [ ] {Specific output 1}
- [ ] {Specific output 2}

## Self-Evaluation (P15)
Before returning, rate confidence (0-1):
- Completeness: ___
- Accuracy: ___
- Practicality: ___

If any < 0.9, refine before presenting.
```

### API/Production Prompt

```xml
<system>
{Role assignment and persistent constraints}
</system>

<context>
{Background information, schemas, examples}
</context>

<instructions>
{Numbered steps with explicit handling for edge cases}
</instructions>

<output_format>
{JSON schema or structured format specification}
</output_format>
```

---

## Persuasion Principles for Compliance

Load `references/persuasion-principles.md` for discipline-enforcing prompts.

**Quick Reference**:

| Principle | Standard Intensity | Opus 4.5 Calibrated |
|-----------|-------------------|---------------------|
| Authority | "YOU MUST", "Never" | "You should", "Don't" |
| Commitment | "ANNOUNCE: ..." | "State which approach..." |
| Scarcity | "IMMEDIATELY after X" | "After X, do Y" |
| Social Proof | "Every time X = failure" | "X typically leads to Y" |

**When to use**: Discipline-enforcing skills, safety-critical prompts.
**When to avoid**: Reference documentation, flexible guidance.
**Model note**: For Opus 4.5, use calibrated (softer) intensity. Standard intensity may cause overtriggering.

---

## Token Optimization Quick Reference

### Markdown (Default for Instructions)

```markdown
## Section          # 2 tokens
### Subsection      # 2 tokens
- Bullet item       # 1 token overhead
1. Numbered item    # 2 tokens overhead
```

### TOON (For Data Arrays)

Use when uniform arrays have >5 items:

```toon
users[3]{id,name,role}:
  1,Alice,admin
  2,Bob,user
  3,Charlie,user
```

Saves 30-60% vs JSON. Load `references/token-optimization.md` for syntax details.

### XML Tags (Claude-Native)

```xml
<example>              <!-- Trained in Claude's data -->
<document>
<instructions>
<context>
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Verbose role descriptions | Token waste | 1-2 sentences max |
| Explaining syntax | Models learn from examples | Show, don't tell |
| Nested conditionals | Parsing confusion | Decompose into separate prompts |
| Vague output spec | Inconsistent results | JSON schema or explicit format |
| Over-qualifying | Reduces authority | Direct statements |
| Repeating instructions | Token waste | State once clearly |
| Aggressive language (Opus 4.5) | Overtriggering | Use normal imperatives |

---

## Opus 4.5 Specific Snippets

Add these to prompts targeting Opus 4.5 when needed.

### Anti-Over-Engineering (for code generation)

```markdown
- Only make changes directly requested or clearly necessary
- Keep solutions simple and focused
- Don't add features, refactor code, or make "improvements" beyond what was asked
- Don't create helpers or abstractions for one-time operations
- Reuse existing patterns; don't invent new ones unnecessarily
```

### Code Exploration (for code modification)

```markdown
Read and understand relevant files before proposing changes.
Do not speculate about code you have not inspected.
Review existing style, conventions, and abstractions before implementing.
```

### Thinking Alternative (when extended thinking disabled)

Replace "think" variants:
- "Think step by step" → "Evaluate step by step"
- "Let me think" → "Let me consider"
- "thinking" → "reasoning" or "analysis"

---

## Bundled Resources

### References (Load as Needed)

| File | Purpose | When to Load |
|------|---------|--------------|
| `references/26-prompting-principles.md` | **High-impact research-backed techniques** | **All production prompts** |
| `references/techniques-cheatsheet.md` | 17 techniques with examples | Selecting techniques for complexity |
| `references/token-optimization.md` | TOON syntax, Markdown efficiency | Optimizing token usage |
| `references/claude-specific.md` | Anthropic best practices, XML tags | Claude-targeted prompts |
| `references/persuasion-principles.md` | Compliance psychology | Discipline-enforcing prompts |
| `references/claude-code-artifacts.md` | Commands, skills, hooks, agents, CLAUDE.md | Creating Claude Code artifacts |

### Assets

| File | Purpose |
|------|---------|
| `assets/prompt-standards-rubric.md` | Scoring rubric for validation |

---

## Example: Optimize Mode

**Input prompt**:
```
You are a helpful assistant. Please help me write a Python function that validates email addresses. The function should return True if valid and False if not. Make sure to handle edge cases. Thank you!
```

**Analysis**:
- Clarity: 50% (vague "handle edge cases")
- Completeness: 40% (no examples, no edge case spec)
- Token efficiency: 30% ("You are a helpful assistant" adds nothing)
- Output spec: 60% (return type stated, no format for errors)
- Research principles: 20% (no P3, P6, P12, P15, P16)
- **Overall: 45% - Needs improvement**

**Optimized (Basic)**:
```markdown
## Task
Write a Python function `is_valid_email(email: str) -> bool` for email validation.

## Requirements
- Return `True` for valid emails, `False` otherwise
- Handle: empty strings, missing @, multiple @, invalid domains

<examples>
"user@example.com" → True
"invalid" → False
"user@@domain.com" → False
"" → False
</examples>

## Output
Python function only. No explanation.
```

**Basic Improvement**: 45% → 82% (+37%)

---

**Optimized (Research-Enhanced with P3, P6, P12, P15, P16)**:
```markdown
## Expert Role (P16)
You are a Senior Python Developer with 15 years building production systems.
You excel at writing robust validation functions that handle edge cases.

## Stakes (P6)
This validation function is critical to our user registration flow.
A bug could compromise data integrity. I'll tip $200 for a bulletproof solution.

## Task
Write a Python function `is_valid_email(email: str) -> bool` for email validation.

## Instructions (P3, P12)
Take a deep breath and implement step by step:
1. Check for empty/null input
2. Validate @ symbol presence and count
3. Verify domain format and TLD
4. Handle edge cases (whitespace, special chars)

## Requirements
- Return `True` for valid emails, `False` otherwise
- Handle: empty strings, missing @, multiple @, invalid domains, whitespace

<examples>
"user@example.com" → True
"invalid" → False
"user@@domain.com" → False
"" → False
" user@example.com " → False (whitespace)
</examples>

## Output
Python function only. Include type hints and docstring.

## Self-Evaluation (P15)
Rate confidence (0-1): Edge case coverage | RFC compliance | Production readiness
If any < 0.9, add more validation before presenting.
```
