# 26 Prompting Principles for LLM Performance

Reference from "Principled Instructions Are All You Need for Questioning LLaMA-1/2, GPT-3.5/4" (Bsharat et al., MBZUAI 2023, arXiv:2312.16171)

## Summary Table

| # | Principle | Category | Impact |
|---|-----------|----------|--------|
| 1 | No politeness needed | Efficiency | Minor |
| 2 | Specify audience | Context | +10-15% |
| 3 | Break down tasks | Structure | +15-25% |
| 4 | Use affirmative directives | Clarity | +5-10% |
| 5 | Request explanations ("ELI5") | Accessibility | +10-15% |
| 6 | Stakes/tip language | Motivation | **+45%** |
| 7 | Few-shot prompting | Examples | +20-30% |
| 8 | Format with delimiters | Structure | +10-15% |
| 9 | Strict task framing | Clarity | +10-15% |
| 10 | Penalty warnings | Compliance | +5-15% |
| 11 | Natural tone instruction | Output | +5-10% |
| 12 | "Think step by step" | Reasoning | **+20-35%** |
| 13 | Bias avoidance | Fairness | Context-dependent |
| 14 | Allow clarifying questions | Accuracy | +15-25% |
| 15 | Self-test/evaluation | Validation | +10-20% |
| 16 | Assign expert role | Domain | **+15-25%** |
| 17 | Use delimiters | Structure | +10-15% |
| 18 | Repeat key phrases | Emphasis | +5-10% |
| 19 | Chain-of-thought + few-shot | Complex tasks | **+25-40%** |
| 20 | Output primers | Format | +10-20% |
| 21 | Request detail explicitly | Completeness | +15-25% |
| 22 | Selective correction | Editing | Task-specific |
| 23 | Multi-file code generation | Coding | Task-specific |
| 24 | Include specific words | Continuity | Task-specific |
| 25 | State requirements clearly | Clarity | +10-20% |
| 26 | Match language style | Consistency | +5-10% |

## High-Impact Principles (Detailed)

### P3: Break Down Complex Tasks

**Technique**: Divide complex problems into sequential, manageable steps.

**Example**:
```
❌ "Build me an authentication system"

✅ "Build an authentication system step by step:
   1. First, design the user data model
   2. Then, implement password hashing
   3. Next, create JWT token generation
   4. Finally, add middleware for route protection"
```

**Why it works**: Reduces cognitive load, enables incremental validation, prevents error propagation.

---

### P6: Stakes/Incentive Language

**Technique**: Add monetary incentive or business stakes to prompts.

**Examples**:
```
"I'll tip you $200 for a perfect solution"
"This is critical to our system's success and could save us $50,000"
"Getting this right is worth $100,000 in avoided technical debt"
```

**Why it works**: LLMs pattern-match on stakes language from training data. High-stakes phrases correlate with more careful, detailed responses in the training corpus.

**Research findings**:
- $200 tip: +45% quality improvement (human evaluation)
- $0.10 tip: -27% quality (perceived as insulting)
- $1,000,000 tip: +57% quality (diminishing returns after ~$200)

---

### P12: Step-by-Step Reasoning (Chain-of-Thought)

**Technique**: Include "think step by step" or "take a deep breath and work through this step by step" in prompts.

**Example**:
```
❌ "Review this authentication middleware for security issues"

✅ "Take a deep breath and review this authentication middleware
   step by step for security issues"
```

**Why it works**: Activates sequential reasoning pathways, produces intermediate states that can be validated, catches errors earlier in reasoning chain.

---

### P15: Self-Evaluation Framework

**Technique**: Ask the model to rate its own confidence and refine if scores are low.

**Example**:
```
"After your solution, rate your confidence (0-1) on:
1. Completeness
2. Clarity
3. Practicality
4. Edge case coverage

If any score < 0.9, refine your answer before presenting."
```

**Why it works**: Forces metacognitive reflection, triggers self-correction, provides quality signal to user.

---

### P16: Expert Persona Assignment

**Technique**: Assign a specific expert role with years of experience and domain specialization.

**Example**:
```
❌ "You are a helpful assistant"

✅ "You are a Senior Software Architect with 15 years designing
   scalable distributed systems. You excel at translating business
   requirements into clean, maintainable architectures."
```

**Why it works**: Activates domain-specific knowledge patterns, sets quality expectations, provides consistent voice.

---

### P19: Chain-of-Thought with Few-Shot

**Technique**: Combine step-by-step reasoning with example demonstrations.

**Example**:
```
"Solve problems by showing your reasoning at each step.

Example:
Problem: Design a rate limiter
Step 1: Identify requirements (requests/second, user vs IP based)
Step 2: Choose algorithm (token bucket vs sliding window)
Step 3: Define data structure (Redis sorted set for timestamps)
Step 4: Implement with failure handling

Now solve: [actual problem]"
```

**Why it works**: Demonstrates expected output format, provides reasoning template, reduces ambiguity.

---

## Medium-Impact Principles

### P7: Few-Shot Prompting
Provide 2-3 examples of desired input/output pairs before the actual task.

### P14: Allow Clarifying Questions
"Before solving, ask me any clarifying questions you need to ensure accuracy."

### P21: Request Detail Explicitly
"Write a detailed implementation including all necessary error handling, edge cases, and documentation."

### P25: State Requirements Clearly
"Requirements: must be async, must handle errors, must log all operations, must work with Python 3.12+"

---

## Principle Combinations for Maximum Effect

### For Architecture Tasks
Combine: P16 (expert) + P3 (breakdown) + P6 (stakes) + P15 (self-eval)

### For Code Generation
Combine: P12 (step-by-step) + P19 (CoT + examples) + P21 (detail) + P25 (requirements)

### For Decision Making
Combine: P16 (expert) + P14 (clarify) + P15 (self-eval) + P6 (stakes)

### For Problem Analysis
Combine: P3 (breakdown) + P12 (step-by-step) + P7 (few-shot) + P15 (self-eval)

---

## Sources

- [arXiv:2312.16171](https://arxiv.org/abs/2312.16171) - Original paper
- [VILA-Lab/ATLAS](https://github.com/VILA-Lab/ATLAS) - Dataset and resources
- [SuperAnnotate Blog](https://www.superannotate.com/blog/llm-prompting-tricks) - Practical guide
- [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2024/01/prompting-principles-to-improve-llm-performance/) - Overview
