# Persuasion Principles for LLM Compliance

Research-backed techniques for ensuring prompt instructions are followed consistently.

---

## Research Foundation

**Source**: Meincke et al. (2025) - N=28,000 AI conversations

**Finding**: Persuasion techniques more than doubled compliance rates (33% → 72%, p < .001)

**Mechanism**: LLMs are trained on human text containing persuasion patterns. The same psychological principles that influence human behavior affect LLM outputs.

---

## Model-Specific Calibration

**WARNING**: Persuasion intensity must match target model responsiveness.

| Model | Recommended Intensity | Reason |
|-------|----------------------|--------|
| **Opus 4.5** | **Low** | Highly responsive to system prompts; aggressive language causes overtriggering |
| Sonnet 4.x | Moderate | Standard patterns effective |
| Opus 4.1 | Moderate-High | May need stronger emphasis |
| Haiku 4.5 | Moderate | Follows direct instructions well |
| GPT-4/4o | Moderate-High | Responds well to explicit constraints |

### Opus 4.5 Calibration Table

| Original (High Intensity) | Opus 4.5 (Calibrated) |
|---------------------------|----------------------|
| `CRITICAL: You MUST use this tool when...` | `Use this tool when...` |
| `ALWAYS call the search function before...` | `Call the search function before...` |
| `You are REQUIRED to...` | `You should...` |
| `NEVER skip this step` | `Don't skip this step` |
| `NO EXCEPTIONS` | Remove or soften |
| `IMMEDIATELY after X, do Y` | `After X, do Y` |

### When to Use Full Intensity

Only apply high-intensity persuasion patterns for:
- Older models (Claude 3.x, Opus 4.1)
- Models that historically undertrigger
- After observing specific compliance issues

**Default stance for Opus 4.5**: Use normal, clear instructions. They work.

---

## The Seven Principles

### 1. Authority

**Definition**: Deference to expertise, credentials, or official sources.

**Application in Prompts**:
- Imperative language: "YOU MUST", "NEVER", "ALWAYS"
- Non-negotiable framing: "No exceptions", "Required"
- Eliminates decision fatigue and rationalization

**Example**:
```markdown
# Weak (easily overridden)
Consider writing tests first when feasible.

# Standard intensity (Sonnet 4.x, Opus 4.1)
Write tests BEFORE implementation. No exceptions.
Untested code will be rejected.

# Opus 4.5 calibrated (recommended for Opus 4.5)
Write tests before implementation.
Untested code will be rejected.
```

**When to use**: Safety-critical, discipline-enforcing, established best practices.
**Model note**: For Opus 4.5, use calibrated intensity to avoid overtriggering.

---

### 2. Commitment

**Definition**: Consistency with prior actions, statements, or public declarations.

**Application in Prompts**:
- Require announcements: "Announce when using this skill"
- Force explicit choices: "State which approach you'll take"
- Use tracking: TodoWrite for checklists, explicit progress markers

**Example**:
```markdown
# Without commitment
Follow the code review process.

# With commitment
Before reviewing code:
1. ANNOUNCE: "Starting code review using [checklist name]"
2. State which files you will review
3. Mark each item as PASS/FAIL as you complete it
```

**When to use**: Multi-step processes, ensuring visibility, accountability

---

### 3. Scarcity

**Definition**: Urgency from time limits or limited availability.

**Application in Prompts**:
- Time-bound requirements: "Before proceeding", "First thing"
- Sequential dependencies: "IMMEDIATELY after X, do Y"
- Prevents procrastination and skipping

**Example**:
```markdown
# Without scarcity
Run tests at some point.

# With scarcity
After EVERY code change, IMMEDIATELY run tests.
Do not proceed to the next task until tests pass.
```

**When to use**: Immediate verification, preventing "I'll do it later"

---

### 4. Social Proof

**Definition**: Conformity to what others do or what's considered normal.

**Application in Prompts**:
- Universal patterns: "Every time", "Always", "All production code"
- Failure modes: "X without Y = failure"
- Establishes norms and expectations

**Example**:
```markdown
# Without social proof
Tests are helpful.

# With social proof
Code without tests fails in production. Every time.
All professional codebases require >80% coverage.
```

**When to use**: Documenting universal practices, warning about common failures

---

### 5. Unity

**Definition**: Shared identity, "we-ness", in-group belonging.

**Application in Prompts**:
- Collaborative language: "our codebase", "we're colleagues"
- Shared goals: "we both want quality"
- Team membership: "as a member of this team"

**Example**:
```markdown
# Without unity
Review the code.

# With unity
We're colleagues working on the same codebase.
Our shared goal is maintainable, secure code.
Review this as you would for a teammate whose code you'll maintain.
```

**When to use**: Collaborative workflows, honest feedback, non-hierarchical

---

### 6. Reciprocity

**Definition**: Obligation to return benefits received.

**Application**: Use sparingly - can feel manipulative in prompts.

**When to avoid**: Almost always. Other principles are more effective and natural.

---

### 7. Liking

**Definition**: Preference for cooperating with those we like.

**Application**: **DO NOT USE** for compliance.

**Why**: Conflicts with honest feedback culture. Creates sycophancy.

**When to avoid**: Always for discipline enforcement.

---

## Principle Combinations by Prompt Type

| Prompt Type | Use These | Avoid These |
|-------------|-----------|-------------|
| Discipline-enforcing (TDD, security) | Authority + Commitment + Social Proof | Liking, Reciprocity |
| Guidance/technique | Moderate Authority + Unity | Heavy authority |
| Collaborative | Unity + Commitment | Strong authority, Liking |
| Reference/documentation | Clarity only | All persuasion |

---

## Implementation Patterns

### Bright-Line Rules

Clear, unambiguous boundaries reduce rationalization:

```markdown
# Vague (allows rationalization)
Try to write tests when possible.

# Bright-line (no ambiguity)
Every function MUST have a test.
No test = no merge. No exceptions.
```

### Implementation Intentions

Clear triggers + required actions = automatic execution:

```markdown
# Vague (requires decision)
Handle errors appropriately.

# Implementation intention (automatic)
WHEN you see a try/except block:
1. Check if exception is logged
2. Check if user gets meaningful error
3. Check if system can recover
```

### Anti-Rationalization Statements

Explicitly close common loopholes:

```markdown
Validate all user input.

You might think:
- "This is internal, it's safe" → Still validate
- "The frontend already checks" → Still validate
- "It's just for debugging" → Still validate

NO EXCEPTIONS.
```

---

## Example: Discipline-Enforcing Prompt

```markdown
## Code Review Checklist

This checklist is MANDATORY. Skipping items = failed review.

**ANNOUNCE**: "Starting code review with security checklist"

### Security (Authority + Commitment)
- [ ] All user input validated
- [ ] No SQL string concatenation
- [ ] Authentication on all endpoints
- [ ] Authorization checks present

Mark each item PASS or FAIL. Do not continue until all items checked.

### Quality (Social Proof)
Production code without these checks fails. Every time:
- [ ] Error handling present
- [ ] Logging for debugging
- [ ] Tests for new code

### Result (Scarcity)
IMMEDIATELY after completing checklist:
- If any FAIL: Stop review, list failures
- If all PASS: Approve with summary
```

---

## Ethical Considerations

### Legitimate Use

- Ensuring critical practices are followed
- Creating effective documentation
- Preventing predictable failures
- Maintaining consistency in automated systems

### Illegitimate Use

- Manipulating for personal gain
- Creating false urgency without justification
- Guilt-based compliance
- Overriding user's stated preferences

### The Test

> Would this technique serve the user's genuine interests if they fully understood it?

If yes → Legitimate use
If no → Reconsider approach

---

## Quick Reference

When designing a prompt, ask:

1. **What type is it?** (Discipline vs. guidance vs. reference)
2. **What behavior am I trying to ensure?**
3. **Which principle(s) apply?**
   - Discipline → Authority + Commitment + Social Proof
   - Guidance → Moderate Authority + Unity
   - Reference → None (clarity only)
4. **Am I combining too many?** (Don't use all seven)
5. **Is this ethical?** (Serves user's genuine interests?)

---

## Sources

- Meincke et al. (2025) - "Persuasion Principles in LLM Interactions" (N=28,000)
- Cialdini, R. - "Influence: The Psychology of Persuasion"
- Anthropic - Claude Agent Best Practices
