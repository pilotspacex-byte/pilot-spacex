# Token Optimization Guide

Strategies for reducing token consumption while maintaining prompt effectiveness.

---

## TOON (Token-Oriented Object Notation)

### Overview

TOON is a compact, human-readable encoding of JSON data that minimizes tokens. Use for **uniform arrays of objects** (same fields per row).

**Token savings**: 30-60% vs formatted JSON
**Accuracy**: 74% vs JSON's 70% in benchmarks

### When to Use TOON

| Use TOON | Use JSON/Markdown |
|----------|-------------------|
| Uniform arrays (>5 items) | Nested/non-uniform data |
| Tabular data | Configuration objects |
| Batch processing | Single objects |
| API responses | Human-edited content |

### Syntax

**Header format**: `name[count]{field1,field2,...}:`

```text
users[3]{id,name,role,lastLogin}:
  1,Alice,admin,2025-01-15T10:30:00Z
  2,Bob,user,2025-01-14T15:22:00Z
  3,Charlie,user,2025-01-13T09:45:00Z
```

**Equivalent JSON** (more tokens):
```json
{
  "users": [
    {"id": 1, "name": "Alice", "role": "admin", "lastLogin": "2025-01-15T10:30:00Z"},
    {"id": 2, "name": "Bob", "role": "user", "lastLogin": "2025-01-14T15:22:00Z"},
    {"id": 3, "name": "Charlie", "role": "user", "lastLogin": "2025-01-13T09:45:00Z"}
  ]
}
```

### TOON Best Practices

1. **Show, don't describe**: Models learn syntax from examples, not explanations
2. **Use tabs for delimiters**: More token-efficient than commas
3. **Explicit lengths `[N]`**: Helps models track row count
4. **Validate output**: Use strict mode to catch truncation

### TOON in Prompts

**Input example**:
```markdown
Filter users with admin role from this data:

users[5]{id,name,role}:
  1,Alice,admin
  2,Bob,user
  3,Charlie,admin
  4,Dana,user
  5,Eve,admin

Output format:
admins[N]{id,name}:
```

**Expected output**:
```text
admins[3]{id,name}:
  1,Alice
  3,Charlie
  5,Eve
```

---

## Markdown Optimization

### Token Costs by Element

| Element | Tokens | Notes |
|---------|--------|-------|
| `## Heading` | 2 | Use for major sections |
| `### Subheading` | 2 | Sparingly in prompts |
| `- Bullet` | 1 | Efficient for lists |
| `1. Numbered` | 2 | Use for sequences |
| `**bold**` | 1 | Key terms only |
| `\`code\`` | 1 | Inline code |
| Code block | 2 | Opening + closing |

### Efficient Patterns

**Use headings for structure**:
```markdown
## Context
Brief background.

## Instructions
1. First step
2. Second step

## Output
Expected format.
```

**Avoid excessive nesting**:
```markdown
# Bad (too deep)
### Section
#### Subsection
##### Detail

## Good (flat)
## Section
**Detail**: explanation
```

### Delimiter Usage

Use delimiters to separate sections clearly:

```markdown
## Context
{background information}

---

## Task
{specific instructions}

---

## Examples
<example>
Input: X
Output: Y
</example>
```

---

## XML Tags for Claude

Claude was trained with XML tags. Use for structured sections.

### Common Tags

```xml
<context>Background information</context>
<instructions>Step-by-step tasks</instructions>
<examples>Input-output pairs</examples>
<document>Reference material</document>
<output_format>Expected structure</output_format>
<constraints>Limitations and rules</constraints>
```

### Nesting Pattern

```xml
<examples>
<example>
<input>User query</input>
<output>Expected response</output>
</example>
</examples>
```

### Tag vs Markdown Trade-off

| Scenario | Use Tags | Use Markdown |
|----------|----------|--------------|
| Claude-specific prompts | Yes | Optional |
| Cross-LLM compatibility | No | Yes |
| Nested structures | Yes | No |
| Human-readable docs | No | Yes |

---

## Token Reduction Techniques

### 1. Remove Redundancy

**Before** (wasteful):
```markdown
You are a helpful assistant. Your task is to help the user with their request.
Please carefully analyze the following code and provide feedback.
Make sure to be thorough and comprehensive in your analysis.
```

**After** (efficient):
```markdown
Analyze this code. Provide feedback on:
- Security vulnerabilities
- Performance issues
- Code style violations
```

### 2. Abbreviate After First Use

```markdown
## Context
Working with Large Language Models (LLMs) in production.
LLM token limits affect prompt design.
```

### 3. Use Lists Over Prose

**Before**:
```markdown
The output should include the error message, the line number where
the error occurred, the severity level which can be error, warning,
or info, and a suggested fix if one is available.
```

**After**:
```markdown
Output fields:
- error_message: string
- line_number: int
- severity: error|warning|info
- suggested_fix: string (optional)
```

### 4. Specify Format Concisely

**Before**:
```markdown
Please format your response as a JSON object with the following structure.
The object should have a "status" field that can be "success" or "error",
a "data" field containing the results, and optionally a "message" field
for any additional information.
```

**After**:
```markdown
Output JSON:
{"status": "success"|"error", "data": [...], "message"?: string}
```

### 5. Leverage Model Knowledge

**Don't explain** what the model knows:
```markdown
# Bad
JSON (JavaScript Object Notation) is a data format using key-value pairs...

# Good
Output as JSON.
```

---

## Token Budget Guidelines

| Prompt Type | Target Tokens | Max Tokens |
|-------------|---------------|------------|
| Simple task | 50-100 | 200 |
| Few-shot (3 examples) | 200-400 | 600 |
| Complex with context | 300-600 | 1000 |
| System prompt | 100-300 | 500 |
| Sub-agent prompt | 150-400 | 800 |

### Allocation Strategy

```
Total budget: 500 tokens

Context:     100 tokens (20%)
Instructions: 150 tokens (30%)
Examples:    200 tokens (40%)
Output spec:  50 tokens (10%)
```

---

## Measurement

### Estimating Token Count

- English: ~4 characters per token
- Code: ~3 characters per token
- JSON: ~2.5 characters per token (verbose)
- TOON: ~4 characters per token (compact)

### Quick Estimates

| Content | ~Tokens |
|---------|---------|
| 1 paragraph | 50-100 |
| 1 code block (20 lines) | 100-200 |
| 1 JSON object (5 fields) | 40-60 |
| 1 TOON row (5 fields) | 15-25 |

---

## Sources

- [TOON Official Documentation](https://toonformat.dev/)
- [TOON with LLMs Guide](https://toonformat.dev/guide/llm-prompts)
- [GitHub - TOON Format](https://github.com/toon-format/toon)
- [InfoQ - TOON Reduces LLM Costs](https://www.infoq.com/news/2025/11/toon-reduce-llm-cost-tokens/)
