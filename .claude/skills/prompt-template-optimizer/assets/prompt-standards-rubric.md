# Prompt Standards Rubric

Scoring system for evaluating and optimizing prompts.

---

## Research-Backed Enhancement Checklist

Before scoring, verify high-impact principles are applied (Bsharat et al., 2023):

| Principle | Check | Impact |
|-----------|-------|--------|
| **P6: Stakes** | [ ] Includes business impact + incentive language | +45% |
| **P16: Persona** | [ ] Specific expert role with years + domain | +15-25% |
| **P3: Decomposition** | [ ] Numbered sequential steps | +15-25% |
| **P12: CoT** | [ ] "Step by step" reasoning guidance | +20-35% |
| **P15: Self-Eval** | [ ] Confidence scoring with refinement trigger | +10-20% |

**Quick enhancement template**:

```markdown
You are a [Title] with [X] years in [domain]. (P16)
This is critical to [impact]. I'll tip $200 for a perfect solution. (P6)
Take a deep breath and work through this step by step: (P12)
[numbered steps] (P3)
Rate confidence (0-1) on completeness/clarity/practicality. If <0.9, refine. (P15)
```

---

## Scoring Criteria

### 1. Clarity (25%)

**Definition**: Instructions are unambiguous and actionable.

| Score | Description |
|-------|-------------|
| 5 | Crystal clear, no possible misinterpretation |
| 4 | Clear with minor ambiguity in edge cases |
| 3 | Mostly clear, some vague requirements |
| 2 | Multiple interpretations possible |
| 1 | Confusing, contradictory, or missing key instructions |

**Checklist**:
- [ ] No hedging language ("might", "perhaps", "could")
- [ ] Specific verbs (not "handle", "process", "deal with")
- [ ] Quantified requirements (numbers, not "some", "many")
- [ ] Clear scope boundaries (what's in/out)

---

### 2. Completeness (20%)

**Definition**: All necessary context and requirements provided.

| Score | Description |
|-------|-------------|
| 5 | All context provided, no external knowledge required |
| 4 | Nearly complete, minor details inferrable |
| 3 | Key context present, some gaps |
| 2 | Significant missing context |
| 1 | Critical information absent |

**Checklist**:
- [ ] Domain context explained (or safely assumed)
- [ ] Input format specified
- [ ] Constraints listed (length, format, scope)
- [ ] Edge cases addressed

---

### 3. Token Efficiency (20%)

**Definition**: Minimal tokens used without sacrificing quality.

| Score | Description |
|-------|-------------|
| 5 | Optimal—every token justified |
| 4 | Minor redundancy, mostly efficient |
| 3 | Some unnecessary content |
| 2 | Significant bloat |
| 1 | Wasteful—major redundancy |

**Checklist**:
- [ ] No unnecessary pleasantries
- [ ] No redundant explanations
- [ ] Appropriate format (TOON for data, Markdown for prose)
- [ ] Abbreviated after first use

---

### 4. Output Specification (15%)

**Definition**: Expected output format clearly defined.

| Score | Description |
|-------|-------------|
| 5 | Exact schema/structure specified |
| 4 | Format clear with minor flexibility |
| 3 | General format indicated |
| 2 | Vague output expectations |
| 1 | No output specification |

**Checklist**:
- [ ] Format type specified (JSON, Markdown, plain text)
- [ ] Structure defined (fields, sections, order)
- [ ] Constraints clear (length, required fields)
- [ ] Example output provided (for complex formats)

---

### 5. Error Handling (10%)

**Definition**: Graceful degradation guidance provided.

| Score | Description |
|-------|-------------|
| 5 | Complete error scenarios covered |
| 4 | Common errors addressed |
| 3 | Some error guidance |
| 2 | Minimal error handling |
| 1 | No error handling |

**Checklist**:
- [ ] "If you cannot..." instructions present
- [ ] Fallback behavior defined
- [ ] Uncertainty handling specified
- [ ] Escalation path clear

---

### 6. Testability (10%)

**Definition**: Success can be objectively measured.

| Score | Description |
|-------|-------------|
| 5 | Clear pass/fail criteria, measurable |
| 4 | Mostly measurable with minor subjectivity |
| 3 | Some testable criteria |
| 2 | Mostly subjective |
| 1 | No testable criteria |

**Checklist**:
- [ ] Success criteria stated
- [ ] Output can be validated programmatically
- [ ] Examples demonstrate expected behavior
- [ ] Edge cases have defined outcomes

---

### 7. Research Principles (Bonus +15%)

**Definition**: High-impact research-backed techniques applied.

| Score | Description |
|-------|-------------|
| 5 | All 5 high-impact principles applied (P3, P6, P12, P15, P16) |
| 4 | 4 principles applied including P6 (stakes) |
| 3 | 3 principles applied |
| 2 | 1-2 principles applied |
| 1 | No research principles applied |

**Checklist**:
- [ ] P6: Stakes/incentive language ("$200 tip", "critical to success")
- [ ] P16: Expert persona (specific title + years + domain)
- [ ] P3: Task decomposition (numbered sequential steps)
- [ ] P12: Chain-of-thought ("step by step")
- [ ] P15: Self-evaluation (confidence scoring + refinement trigger)

**Note**: This is a bonus criterion. Prompts can pass without it, but applying research principles significantly improves quality.

---

## Scoring Calculation

**Base Score** (max 100%):

```
Base Score = (Clarity × 0.25) + (Completeness × 0.20) +
             (Token Efficiency × 0.20) + (Output Spec × 0.15) +
             (Error Handling × 0.10) + (Testability × 0.10)

Base Percentage = (Base Score / 5) × 100
```

**With Research Principles Bonus** (max 115%):

```
Bonus = (Research Principles Score / 5) × 15
Total Percentage = Base Percentage + Bonus
```

**Example**: Base 80% + Research Bonus 12% = 92% (Excellent)

---

## Thresholds

| Score | Rating | Action |
|-------|--------|--------|
| 85-100% | Excellent | Production ready |
| 70-84% | Good | Acceptable for most uses |
| 50-69% | Needs Work | Improve before production |
| <50% | Poor | Major revision required |

---

## Quick Assessment Template

```markdown
## Prompt Assessment

**Prompt**: {name or brief description}
**Type**: {skill | command | sub-agent | api-prompt}
**Target**: {Claude | GPT | other}

### Research Principles Applied

| Principle | Applied | Notes |
|-----------|---------|-------|
| P6: Stakes | [ ] | {incentive language used?} |
| P16: Persona | [ ] | {specific expert role?} |
| P3: Decomposition | [ ] | {numbered steps?} |
| P12: CoT | [ ] | {step-by-step reasoning?} |
| P15: Self-Eval | [ ] | {confidence scoring?} |

### Scores

| Criterion | Score (1-5) | Weight | Weighted |
|-----------|-------------|--------|----------|
| Clarity | _ | 25% | _ |
| Completeness | _ | 20% | _ |
| Token Efficiency | _ | 20% | _ |
| Output Specification | _ | 15% | _ |
| Error Handling | _ | 10% | _ |
| Testability | _ | 10% | _ |
| **Base Total** | | | **__%** |
| Research Principles | _ | +15% | +_ |
| **Final Total** | | | **__%** |

### Strengths
- {What works well}

### Improvements Needed
- {Specific issues to address}

### Recommendations
1. {First priority fix}
2. {Second priority fix}
```

---

## Example Assessment

### Input Prompt

```
You are a helpful assistant. Please help me analyze this code and find any bugs.
Make sure to be thorough. Thanks!
```

### Assessment

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| Clarity | 2 | "analyze", "bugs", "thorough" are vague |
| Completeness | 1 | No code provided, no context |
| Token Efficiency | 2 | "helpful assistant" adds nothing |
| Output Specification | 1 | No format specified |
| Error Handling | 1 | No guidance for no bugs found |
| Testability | 1 | No success criteria |

**Total**: 25% - Poor

### Optimized Version (Without Research Principles)

```markdown
## Task
Find bugs in this Python function.

## Code
{code_block}

## Focus Areas
- Logic errors
- Edge cases (null, empty, overflow)
- Off-by-one errors

## Output
JSON array of bugs found:
[{"line": int, "issue": string, "severity": "critical"|"major"|"minor", "fix": string}]

If no bugs found: []
```

### Reassessment (Without Research Principles)

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| Clarity | 5 | Specific task, defined focus |
| Completeness | 4 | Context in focus areas |
| Token Efficiency | 5 | No waste |
| Output Specification | 5 | Exact JSON schema |
| Error Handling | 4 | Empty array case covered |
| Testability | 5 | JSON output verifiable |

**Base Total**: 93% - Excellent

---

### Research-Enhanced Version (With P3, P6, P12, P15, P16)

```markdown
## Expert Role (P16)
You are a Senior Software Engineer with 15 years in Python development.
You excel at finding subtle bugs that cause production incidents.

## Stakes (P6)
Finding these bugs could save us $10,000 in debugging time.
I'll tip you $200 for a thorough, production-ready analysis.

## Task
Find bugs in this Python function.

## Code
{code_block}

## Instructions (P3, P12)
Take a deep breath and analyze step by step:
1. Check control flow and logic paths
2. Identify edge cases (null, empty, overflow)
3. Look for off-by-one errors
4. Verify type handling

## Output
JSON array of bugs found:
[{"line": int, "issue": string, "severity": "critical"|"major"|"minor", "fix": string}]

If no bugs found: []

## Self-Evaluation (P15)
Rate your confidence (0-1) that you found all bugs:
- Completeness: ___
- Accuracy: ___

If any < 0.9, continue analysis before presenting.
```

### Final Assessment (Research-Enhanced)

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| Clarity | 5 | Specific task, defined focus |
| Completeness | 5 | Full context with expert framing |
| Token Efficiency | 4 | Slightly more tokens, justified by quality |
| Output Specification | 5 | Exact JSON schema |
| Error Handling | 5 | Empty array + self-eval refinement |
| Testability | 5 | JSON output + confidence scores |
| **Base Total** | | **95%** |
| Research Principles | 5 | All 5 high-impact principles applied |
| **Final Total** | | **110%** - Outstanding |

---

## Flexibility Guidelines

### When to Allow Lower Scores

| Situation | Acceptable Trade-off |
|-----------|---------------------|
| Token budget constraint | Lower completeness for efficiency |
| Simple one-off task | Skip error handling |
| Exploratory/creative | Reduce output specification |
| Internal tooling | Lower testability requirements |

### Document Rationale

When accepting a lower score, document why:

```markdown
**Accepted deviation**: Token Efficiency at 3/5
**Reason**: Few-shot examples required for accuracy,
            worth the token cost (+200 tokens)
**Justification**: Task accuracy improved from 70% to 95%
```

---

## Opus 4.5 Compatibility Checklist

Before deploying prompts targeting Opus 4.5:

### Required Checks

- [ ] No aggressive language (MUST, NEVER, ALWAYS, CRITICAL, REQUIRED)
- [ ] No "think" variants (if extended thinking disabled)
- [ ] Uses normal imperative form (not emphatic)
- [ ] Tool triggering language is moderate

### Conditional Checks

- [ ] Anti-over-engineering constraints included (if code generation)
- [ ] Code exploration requirements included (if code modification)
- [ ] Frontend aesthetics guidance included (if UI generation)

### Quick Scan for Problematic Patterns

Search prompt for these and replace:

| Pattern | Replace With |
|---------|--------------|
| `MUST` | "should" |
| `NEVER` | "don't" |
| `ALWAYS` | Direct instruction |
| `CRITICAL` | Remove or soften |
| `REQUIRED` | Remove or soften |
| `IMMEDIATELY` | "After X, do Y" |
| `think` | "consider", "evaluate", "analyze" |

### Opus 4.5 Snippets (Add When Needed)

**Anti-Over-Engineering** (for code generation):

```markdown
- Only make changes directly requested or clearly necessary
- Keep solutions simple and focused
- Don't add features beyond what was asked
- Don't create abstractions for one-time operations
```

**Code Exploration** (for code modification):

```markdown
Read relevant files before proposing changes.
Do not speculate about code you have not inspected.
Review existing style and conventions before implementing.
```

### Validation Result

| Check | Status |
|-------|--------|
| Aggressive language scan | Pass / Fail |
| Think variants scan | Pass / Fail |
| Conditional snippets | Added / N/A |
| **Overall Opus 4.5 Ready** | **Yes / No** |
