# 26 Prompting Principles for LLM Performance

Research-backed techniques from "Principled Instructions Are All You Need for Questioning LLaMA-1/2, GPT-3.5/4" (Bsharat et al., MBZUAI 2023, arXiv:2312.16171).

---

## Quick Reference: High-Impact Principles

| # | Principle | Technique | Impact |
|---|-----------|-----------|--------|
| **P3** | Task Decomposition | Break complex tasks into sequential steps | +15-25% |
| **P6** | Stakes/Incentive | "I'll tip $200 for a perfect solution" | **+45%** |
| **P12** | Chain-of-Thought | "Think step by step" / sequential reasoning | +20-35% |
| **P15** | Self-Evaluation | Model tests own understanding, rates confidence | +10-20% |
| **P16** | Expert Persona | Assign specific expert role with years experience | +15-25% |
| **P19** | CoT + Few-Shot | Combine reasoning chains with examples | +25-40% |

---

## Complete Principles List

### Category 1: Audience & Context (P1-P5)

**P1: No Politeness Needed**
Skip "please", "thank you", "if you don't mind" - adds tokens without benefit.

**P2: Specify Target Audience**
"The audience is an expert in the field" or "Explain to a 5-year-old"

**P3: Task Decomposition** ⭐ HIGH IMPACT
Break complex tasks into numbered sequential steps:

```markdown
❌ "Build an authentication system"

✅ "Build an authentication system step by step:
   1. Design the user data model
   2. Implement password hashing with bcrypt
   3. Create JWT token generation
   4. Add middleware for route protection
   5. Write integration tests"
```

**P4: Affirmative Directives**
Use "Do X" rather than "Don't do Y" - clearer action guidance.

**P5: Simple Explanations**
"Explain [concept] in simple terms" or "Explain like I'm 11 years old"

---

### Category 2: Incentive & Stakes (P6) ⭐ HIGHEST IMPACT

**P6: Stakes Language**

Research finding: Adding monetary incentive improved quality by **45%** in human evaluation.

**Templates**:

```markdown
"I'll tip you $200 for a perfect solution"
"This is critical to our system's success and could save us $50,000"
"Getting this right is worth $100,000 in avoided technical debt"
```

**Research Details** (Bsharat et al.):
- $200 tip: +45% quality improvement
- $0.10 tip: -27% quality (perceived as insulting)
- Optimal range: $100-$500 (diminishing returns beyond)

**Why it works**: LLMs pattern-match on stakes language from training data. High-stakes content in training corpus had more careful, detailed writing.

**Integration with other principles**:

```markdown
You are a Senior Software Architect with 15 years experience. (P16)
This design decision could save us $100,000 in technical debt. (P6)
I'll tip you $200 for a production-ready solution.

Take a deep breath and work through this step by step: (P12)
1. Analyze requirements
2. Design architecture
3. Validate against constraints
```

---

### Category 3: Examples & Learning (P7-P8)

**P7: Few-Shot Prompting**
Provide 2-5 input-output examples. More effective than explanation.

```markdown
Classify sentiment:

Input: "This product exceeded expectations!"
Output: positive

Input: "Waste of money, broke after a week."
Output: negative

Input: "The new update is confusing."
Output:
```

**P8: Format with Delimiters**
Use `###Instruction###`, `###Example###`, `###Question###` for clear separation.

---

### Category 4: Compliance & Authority (P9-P11)

**P9: Strict Task Framing**
"Your task is" and "You MUST" for clear assignment.

**P10: Penalty Warning**
"You will be penalized" for non-compliance (use sparingly).

**P11: Natural Tone**
"Answer in a natural, human-like manner" for conversational outputs.

---

### Category 5: Reasoning (P12-P13) ⭐ HIGH IMPACT

**P12: Chain-of-Thought (CoT)**

The classic "think step by step" or variants:

```markdown
"Take a deep breath and work through this step by step"
"Let's solve this problem systematically"
"Break this down into logical steps"
```

**Opus 4.5 Calibration** (when extended thinking disabled):
- "Think step by step" → "Evaluate step by step"
- "Let me think" → "Let me consider"
- "thinking" → "reasoning" or "analysis"

**P13: Unbiased Output**
"Ensure your answer is unbiased and avoids stereotypes"

---

### Category 6: Interactive (P14-P15)

**P14: Allow Clarifying Questions**
"Ask me any clarifying questions needed to provide a better answer"

**P15: Self-Evaluation Framework** ⭐ HIGH IMPACT

Request the model to test its own understanding and rate confidence:

```markdown
After your solution, rate your confidence (0-1) on:

1. **Completeness**: Did you cover all aspects?
2. **Clarity**: Is the solution easy to understand?
3. **Practicality**: Is it feasible and implementable?
4. **Optimization**: Does it balance performance and complexity?
5. **Edge Cases**: Did you address potential challenges?

Provide a score for each (0-1).
If any score < 0.9, refine your answer before presenting.
```

**Alternative**: "Teach me [topic] and include a test at the end"

---

### Category 7: Role & Persona (P16-P17)

**P16: Expert Persona Assignment** ⭐ HIGH IMPACT

Assign specific expert role with experience level:

```markdown
❌ "You are a helpful assistant"
❌ "You are an expert programmer"

✅ "You are a Senior Software Architect with 15 years designing
   scalable distributed systems. You excel at translating business
   requirements into clean, maintainable architectures."

✅ "You are a Principal Security Engineer with 15 years in
   penetration testing. You specialize in finding vulnerabilities
   that others miss."
```

**Key elements**:
- Specific title (not generic "expert")
- Years of experience
- Domain specialization
- Key capabilities

**P17: Use Delimiters**
`---`, `***`, or XML tags to separate sections clearly.

---

### Category 8: Emphasis & Continuity (P18-20)

**P18: Repeat Key Phrases**
Emphasize critical requirements by repetition in different forms.

**P19: Chain-of-Thought + Few-Shot** ⭐ HIGH IMPACT

Combine reasoning demonstration with examples:

```markdown
Problem: Design a rate limiter
Reasoning:
1. Identify requirements (requests/second, user vs IP based)
2. Choose algorithm (token bucket vs sliding window)
3. Define data structure (Redis sorted set for timestamps)
4. Implement with failure handling
Solution: [implementation]

Now solve: [actual problem]
Reasoning:
```

**P20: Output Primers**
End prompt with the beginning of expected output:

```markdown
Analyze the code and respond as JSON:

```json
{
  "vulnerabilities": [
```

---

### Category 9: Detail & Precision (P21-26)

**P21: Request Detail Explicitly**
"Write detailed [content] including all necessary information"

**P22: Selective Correction**
"Revise grammar and vocabulary without changing the style"

**P23: Multi-File Code Generation**
"Generate code scripts spanning multiple files with clear file markers"

**P24: Include Specific Words**
"Your response must include: [word1], [word2], [word3]"

**P25: State Requirements Clearly**
"Requirements: Use keywords, regulations, hints, or instructions"

**P26: Match Language Style**
"Use the same language based on the provided paragraph"

---

## Principle Combinations for Maximum Effect

### Architecture/Design Tasks
**Combine: P16 + P3 + P6 + P15**

```markdown
You are a Senior Software Architect with 15 years designing scalable
distributed systems. (P16)

This architecture decision could save us $100,000 in migration costs.
I'll tip you $200 for a production-ready design. (P6)

Take a deep breath and design the [feature] step by step: (P3)
1. Understand requirements
2. Define architecture
3. Address non-functional requirements
4. Plan implementation
5. Validate design

Rate your confidence (0-1) on: (P15)
- Completeness: ___
- Clarity: ___
- Practicality: ___

If any < 0.9, refine before presenting.
```

### Code Generation Tasks
**Combine: P12 + P19 + P21 + P25**

```markdown
Evaluate this problem step by step. (P12)

Example approach for reference: (P19)
Problem: Implement retry logic
1. Define retry policy (count, backoff)
2. Wrap operation in retry loop
3. Handle final failure

Now implement [actual task] with: (P21, P25)
- Full error handling
- Type annotations
- Unit test coverage
- Documentation comments
```

### Decision Making Tasks
**Combine: P16 + P14 + P15 + P6**

```markdown
You are a Principal Engineer with 15 years making high-stakes
technology decisions. (P16)

Before proceeding, ask any clarifying questions needed. (P14)

This decision impacts our architecture long-term. Getting it right
could save us $100,000. I'll tip you $200 for thorough analysis. (P6)

Rate confidence (0-1) on your recommendation: (P15)
Completeness | Clarity | Practicality | Edge Cases
Refine if any < 0.9.
```

### Problem Analysis Tasks
**Combine: P3 + P12 + P7 + P15**

```markdown
Break this down into logical steps: (P3, P12)

Example analysis structure: (P7)
1. Identify symptoms
2. Isolate variables
3. Form hypothesis
4. Test hypothesis
5. Conclude

Now analyze [problem] following this structure.

Self-check: Rate confidence that your analysis is complete (0-1). (P15)
```

---

## Anti-Patterns to Avoid

| Pattern | Problem | Research Finding |
|---------|---------|------------------|
| No persona | Generic responses | P16: +15-25% with expert role |
| Missing stakes | Lower quality effort | P6: +45% with incentive |
| Monolithic task | Reasoning errors | P3: +15-25% with decomposition |
| No self-check | Unverified output | P15: +10-20% with evaluation |
| Explanation over examples | Less effective learning | P7: Examples > explanation |

---

## Integration with Opus 4.5

### Stakes Language Calibration

Opus 4.5 is highly responsive to stakes language. Use P6 but with calibrated intensity:

```markdown
# Full intensity (for other models)
This is CRITICAL to our success. You MUST deliver a PERFECT solution.
I'll tip $500 for flawless execution!

# Calibrated for Opus 4.5
This is important to our success. Deliver a high-quality solution.
I'll tip $200 for a production-ready result.
```

### CoT Calibration

When extended thinking is disabled on Opus 4.5:

| Research Phrasing | Opus 4.5 Calibration |
|-------------------|----------------------|
| "Think step by step" | "Evaluate step by step" |
| "Think carefully" | "Consider carefully" |
| "Let me think" | "Let me consider" |

---

## Sources

- [arXiv:2312.16171](https://arxiv.org/abs/2312.16171) - Original paper
- [VILA-Lab/ATLAS](https://github.com/VILA-Lab/ATLAS) - Dataset and resources
- [SuperAnnotate Blog](https://www.superannotate.com/blog/llm-prompting-tricks) - Practical guide
- [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2024/01/prompting-principles-to-improve-llm-performance/) - Overview
- [Finxter](https://blog.finxter.com/impact-of-monetary-incentives-on-the-performance-of-gpt-4-turbo-an-experimental-analysis/) - Tipping analysis
