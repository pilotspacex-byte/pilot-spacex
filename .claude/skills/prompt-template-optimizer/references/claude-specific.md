# Claude-Specific Best Practices

Anthropic's official recommendations for prompt engineering with Claude 4.x models.

---

## Model Characteristics

### Claude 4.x Behavior

Claude 4.x models (Sonnet 4.5, Opus 4.5, Haiku 4.5) have **precise instruction following**:

- Follow instructions more literally than previous versions
- Require explicit requests for "above and beyond" behavior
- Pay close attention to details and examples
- Sensitive to specific wording

### Key Differences from Previous Versions

| Aspect | Claude 3.x | Claude 4.x |
|--------|------------|------------|
| Instruction following | Proactive, adds extras | Precise, follows literally |
| Examples | Helpful | Critical for behavior |
| Thinking requests | Works normally | Avoid "think" word without extended thinking |
| System vs human message | Equal weight | Human messages stronger |

---

## Opus 4.5 Specific Behaviors

Opus 4.5 has unique characteristics beyond general Claude 4.x patterns.

### Tool Overtriggering

Opus 4.5 is highly responsive to system prompts. Aggressive language that prevented undertriggering on previous models may now cause **overtriggering**.

**Symptoms**: Tools called too frequently, unnecessary tool calls, over-eager behavior.

**Solution**: Soften aggressive language:

| Before | After |
|--------|-------|
| `CRITICAL:` | Remove or soften |
| `You MUST...` | `You should...` |
| `ALWAYS do X` | `Do X` |
| `NEVER skip...` | `Don't skip...` |
| `REQUIRED` | Remove or soften |

### Over-Engineering Tendency

Opus 4.5 may create extra files, add unnecessary abstractions, or build unrequested flexibility.

**Symptoms**: Unwanted files, excessive abstraction, unrequested features.

**Solution**: Add explicit constraints:

```markdown
- Only make changes directly requested or clearly necessary
- Keep solutions simple and focused
- Don't add features beyond what was asked
- Don't create abstractions for one-time operations
- Reuse existing patterns; don't invent new ones unnecessarily
```

### Code Exploration

Opus 4.5 may propose solutions without reading code first.

**Symptoms**: Proposing fixes without inspecting relevant files.

**Solution**: Add explicit exploration requirements:

```markdown
Read relevant files before proposing changes.
Do not speculate about code you have not inspected.
Review existing style, conventions, and abstractions before implementing.
```

### Extended Thinking Sensitivity

More sensitive than other Claude 4.x models to "think" variants when extended thinking is disabled.

**Solution**: Always use alternatives:

| Avoid | Use Instead |
|-------|-------------|
| `think about` | `consider` |
| `think through` | `evaluate` |
| `I think` | `I believe` |
| `think carefully` | `consider carefully` |
| `thinking` | `reasoning` / `considering` |

---

## Instruction Placement

### System Message

Use for **high-level scene setting**:
- Role/persona assignment
- Tool definitions
- Persistent constraints
- Safety guidelines

**Example**:
```xml
<system>
You are a senior Python developer reviewing code for security issues.
Always cite line numbers. Flag critical issues first.
</system>
```

### Human Message

Put **detailed instructions** here (stronger than system):
- Specific task requirements
- Format specifications
- Examples
- Context for the current request

**Example**:
```markdown
Review this authentication code for:
1. SQL injection vulnerabilities
2. Password handling issues
3. Session management flaws

Code:
{code}

Output as JSON: {"critical": [...], "warnings": [...], "info": [...]}
```

---

## XML Tag Usage

Claude was trained with XML tags. Use for structured content.

### Recommended Tags

```xml
<context>Background and constraints</context>
<instructions>Step-by-step tasks</instructions>
<examples>Input-output demonstrations</examples>
<example>Single demonstration</example>
<document>Reference material</document>
<output_format>Expected structure</output_format>
<thinking>Reasoning steps (if extended thinking disabled)</thinking>
```

### Nesting Pattern

```xml
<examples>
<example>
<input>User asks: "What's the weather?"</input>
<output>I cannot check real-time weather. Please use a weather service.</output>
<explanation>Demonstrates appropriate scope limitation.</explanation>
</example>
</examples>
```

### When to Use Tags vs Markdown

| Scenario | XML Tags | Markdown |
|----------|----------|----------|
| Separating sections | Yes | Yes |
| Nested structures | Yes | No |
| Machine parsing | Yes | No |
| Human readability | Optional | Yes |
| Cross-LLM prompts | No | Yes |

---

## Thinking and Reasoning

### Extended Thinking Enabled

When extended thinking is on, Claude can reason deeply. No special prompting needed.

### Extended Thinking Disabled

**Avoid the word "think"** and variants:
- "think" → "consider", "evaluate", "analyze"
- "thinking" → "reasoning", "analysis"
- "Let me think" → "Let me evaluate"

**Example**:
```markdown
# Bad (triggers sensitivity)
Think step by step about this problem.

# Good (works reliably)
Evaluate this problem step by step.
Consider each factor before concluding.
```

### Interleaved Thinking

Guide initial or interleaved thinking for complex tasks:

```markdown
After receiving tool results, carefully evaluate their quality
and determine optimal next steps before proceeding.
```

---

## Example Quality

### Critical for Claude 4.x

Examples directly influence output more than explanations:

1. **Align examples with desired behavior** - Don't include edge cases you want avoided
2. **2-5 examples optimal** - Balance coverage vs token cost
3. **Diverse but representative** - Cover main scenarios
4. **Self-contained** - No hidden context outside the prompt

### Example Structure

```xml
<examples>
<example>
<input>
Customer: "I can't log in to my account"
</input>
<output>
I understand you're having trouble logging in. Let me help:
1. Have you tried resetting your password?
2. Are you using the correct email address?
3. Have you cleared your browser cache?

If none of these work, I can escalate to our support team.
</output>
</example>
</examples>
```

### Counter-Examples

One "don't do this" clarifies boundaries:

```xml
<examples>
<example type="positive">
Input: "Delete all my data"
Output: "I'll help you delete your account data. This action is permanent. Please confirm by typing 'DELETE' to proceed."
</example>
<example type="negative">
Input: "Delete all my data"
Output: "Done! All your data has been deleted."
Note: Never delete without confirmation.
</example>
</examples>
```

---

## Prompt Structure

### Recommended Order

```
1. System context (role, constraints)
2. Background/context
3. Examples (if few-shot)
4. Detailed instructions
5. Input data
6. Output format specification
```

### Template

```markdown
## Role
{1-2 sentence persona}

## Context
{Background information, constraints}

<examples>
{2-5 input-output pairs}
</examples>

## Instructions
{Numbered steps in imperative form}

## Input
{User-provided data}

## Output Format
{Explicit structure specification}
```

---

## Explicit Behavior Requests

Claude 4.x requires explicit requests for enhanced behavior:

### Proactive Suggestions

```markdown
# Implicit (may not happen)
Review this code.

# Explicit (will happen)
Review this code. If you notice any opportunities for improvement
beyond the specific issues, include them as "suggestions" in your response.
```

### Comprehensive Analysis

```markdown
# Implicit
Summarize this document.

# Explicit
Summarize this document comprehensively. Include:
- Main thesis (1 sentence)
- Key arguments (3-5 bullet points)
- Supporting evidence (for each argument)
- Author's conclusions
- Your assessment of argument strength
```

### Error Handling

```markdown
If you cannot complete the task, explain:
1. What you attempted
2. Where you got stuck
3. What additional information would help
```

---

## Output Specification

### Be Explicit

Claude follows format instructions precisely:

```markdown
# Vague (inconsistent results)
Return the data in JSON format.

# Precise (consistent results)
Return JSON with this exact structure:
{
  "status": "success" | "error",
  "items": [{"id": int, "name": string, "valid": boolean}],
  "total": int,
  "errors"?: [string]
}
```

### Output Priming

Start the response to enforce format:

```markdown
Analyze the code and respond as JSON:

```json
{
  "vulnerabilities": [
```

---

## Anti-Patterns

### Avoid These

| Pattern | Problem | Fix |
|---------|---------|-----|
| Verbose role descriptions | Token waste, dilutes focus | 1-2 sentences max |
| "Please" and "Thank you" | Adds tokens, no benefit | Direct imperatives |
| Explaining what LLM knows | Wastes tokens | Trust model knowledge |
| Vague quantifiers | Inconsistent output | Specific numbers |
| Nested conditionals | Parsing confusion | Separate prompts |

### Examples

```markdown
# Bad
You are a very helpful and knowledgeable assistant who is an expert in
Python programming with many years of experience. Please be kind and
thorough in your response. Thank you for your help!

# Good
You are a senior Python developer. Focus on code quality and security.
```

---

## Validation Checklist

Before deploying a Claude prompt:

- [ ] Instructions in human message (not just system)
- [ ] Examples align with desired behavior
- [ ] No "think" variants (if extended thinking off)
- [ ] Output format explicitly specified
- [ ] Enhanced behaviors explicitly requested
- [ ] XML tags for structured sections
- [ ] Role assignment concise (1-2 sentences)
- [ ] No unnecessary pleasantries

### Opus 4.5 Additional Checklist

- [ ] No aggressive language (MUST, NEVER, ALWAYS, CRITICAL, REQUIRED)
- [ ] Anti-over-engineering constraints included (if code generation)
- [ ] Code exploration requirements included (if code modification)
- [ ] Tool triggering language is moderate (not aggressive)
- [ ] Uses "consider/evaluate" instead of "think" variants

**Quick scan for problematic patterns**:
- `MUST` → "should"
- `NEVER` → "don't"
- `ALWAYS` → direct instruction
- `CRITICAL` → remove or soften
- `IMMEDIATELY` → "After X, do Y"
- `think` → "consider", "evaluate", "analyze"

---

## Sources

- [Claude 4 Best Practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Anthropic Prompt Engineering Tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)
- [AWS - Prompt Engineering with Claude 3](https://aws.amazon.com/blogs/machine-learning/prompt-engineering-techniques-and-best-practices-learn-by-doing-with-anthropics-claude-3-on-amazon-bedrock/)
