# Prompt Engineering Techniques Cheatsheet

17 research-backed techniques organized by complexity and use case.

**Research Foundation**: Based on "Principled Instructions Are All You Need" (Bsharat et al., MBZUAI 2023) which tested 26 prompting strategies and found improvements up to 45%.

See `references/26-prompting-principles.md` for the complete 26 principles with impact data.

---

## High-Impact Quick Reference

| Technique | Principle | Impact | Primary Use |
|-----------|-----------|--------|-------------|
| Stakes/Incentive | P6 | **+45%** | All production prompts |
| Expert Persona | P16 | +15-25% | Domain-specific tasks |
| Task Decomposition | P3 | +15-25% | Multi-step workflows |
| Chain-of-Thought | P12 | +20-35% | Reasoning tasks |
| Self-Evaluation | P15 | +10-20% | Quality-critical outputs |
| CoT + Few-Shot | P19 | +25-40% | Complex analysis |

---

## Beginner Techniques

### 1. Zero-Shot Prompting

**Concept**: Direct request without examples. Relies on model's pre-trained knowledge.

**When to use**: Straightforward tasks, well-defined outputs, model has domain knowledge.

**Example**:
```markdown
Explain photosynthesis to a 5-year-old in 2 sentences.
```

**Token cost**: Minimal (+0 overhead)

---

### 2. Few-Shot Prompting

**Concept**: Provide 2-5 input-output examples demonstrating expected pattern.

**When to use**: Formatting requirements, classification tasks, domain-specific outputs.

**Example**:
```markdown
Classify sentiment as positive, negative, or neutral:

Input: "This product exceeded my expectations!"
Output: positive

Input: "Waste of money, broke after a week."
Output: negative

Input: "It works as described."
Output: neutral

Input: "The delivery was late but the item is great."
Output:
```

**Token cost**: +100-500 tokens per example
**Accuracy improvement**: +15-30%

---

### 3. Role Prompting (P16) ⭐ HIGH IMPACT

**Concept**: Assign specific expert persona with years of experience and domain specialization.

**When to use**: Domain expertise needed, specific communication style, consistent voice.

**Research Impact**: +15-25% accuracy improvement (Bsharat et al., 2023)

**Example**:
```markdown
# Weak (generic)
You are an expert programmer.

# Strong (specific - P16)
You are a Senior Security Engineer with 15 years in penetration testing.
You specialize in finding vulnerabilities that others miss.

Review this code for SQL injection vulnerabilities:
{code}
```

**Key elements**:
- Specific title (not generic "expert")
- Years of experience
- Domain specialization
- Key capabilities

**Token cost**: +10-30 tokens
**Note**: Keep roles concise (1-2 sentences max)

---

### 3.5. Stakes/Incentive Language (P6) ⭐ HIGHEST IMPACT

**Concept**: Add business stakes and monetary incentive to motivate quality.

**When to use**: All production prompts where quality matters.

**Research Impact**: **+45% quality improvement** (Bsharat et al., 2023)

**Examples**:
```markdown
# Stakes framing
This is critical to our system's success and could save us $50,000.
I'll tip you $200 for a perfect, production-ready solution.

# Combined with other techniques
You are a Senior Architect with 15 years experience. (P16)
This decision could save us $100,000 in technical debt. (P6)
Take a deep breath and work through this step by step: (P12)
```

**Research Details**:
- $200 tip: +45% quality improvement
- $0.10 tip: -27% quality (perceived as insulting)
- Optimal range: $100-$500

**Why it works**: LLMs pattern-match on stakes language from training data. High-stakes content in training corpus had more careful, detailed writing.

**Token cost**: +15-30 tokens
**ROI**: Highest—dramatic quality improvement for minimal tokens

---

### 4. Style Prompting

**Concept**: Direct output toward specific tone, formality, or format.

**When to use**: Customer-facing content, documentation, creative writing.

**Example**:
```markdown
Write a product description in a conversational, friendly tone.
Avoid jargon. Use short sentences. Target audience: non-technical users.
```

**Token cost**: +15-40 tokens

---

### 5. Explicit Instructions Prompting

**Concept**: Unambiguous specification of format, length, scope, and constraints.

**When to use**: Always. This is foundational.

**Example**:
```markdown
## Task
Write a bug report summary.

## Constraints
- Maximum 3 sentences
- Include: affected component, steps to reproduce, severity
- Exclude: speculation, proposed fixes
- Format: Plain text, no markdown
```

**Token cost**: +30-60 tokens
**ROI**: Highest—prevents most output issues

---

## Intermediate Techniques

### 6. Chain-of-Thought (CoT)

**Concept**: Request step-by-step reasoning before final answer.

**When to use**: Math, logic, multi-step analysis, debugging.

**Zero-shot CoT**:
```markdown
Solve this problem step by step:
{problem}
```

**Few-shot CoT** (more reliable):
```markdown
Problem: A store has 50 apples. 20 are sold, then 15 more arrive.
Reasoning:
1. Start with 50 apples
2. After selling: 50 - 20 = 30
3. After arrival: 30 + 15 = 45
Answer: 45 apples

Problem: {new_problem}
Reasoning:
```

**Token cost**: +200-500 tokens (output)
**Accuracy improvement**: +30-50% on reasoning tasks

**Opus 4.5 Note**: When extended thinking is disabled, avoid "think" variants:
- "Think step by step" → "Evaluate step by step"
- "Let me think" → "Let me consider"
- "Thought:" → "Reasoning:" or "Analysis:"

---

### 7. Output Priming

**Concept**: Begin the model's response with formatting cues.

**When to use**: Structured outputs (JSON, lists, code), consistent formatting.

**Example**:
```markdown
List the top 5 security vulnerabilities in this code:

1.
```

The model continues from "1." ensuring list format.

**For JSON**:
```markdown
Extract user data as JSON:
{text}

```json
{
  "name":
```

**Token cost**: +5-15 tokens
**Reliability**: Highly effective for format enforcement

---

### 8. System Prompting

**Concept**: Persistent instructions in system-level message across conversation.

**When to use**: Consistent behavior, role maintenance, safety constraints.

**Example**:
```xml
<system>
You are a Python code reviewer.
- Focus on security and performance
- Use Pythonic patterns
- Always include code examples
- Never suggest deprecated libraries
</system>
```

**Note for Claude**: Put high-level scene setting in system; detailed instructions in human messages.

---

### 9. Contextual Prompting

**Concept**: Supply comprehensive background before the task.

**When to use**: Domain-specific tasks, personalized outputs, complex requirements.

**Example**:
```markdown
## Context
We are building a healthcare SaaS platform.
- Stack: Python/FastAPI, PostgreSQL, Redis
- Compliance: HIPAA required
- Team: 3 developers, 2 weeks until deadline
- Existing patterns: Repository pattern, async everywhere

## Task
Design the patient data export feature.
```

**Token cost**: +50-200 tokens
**Value**: Dramatically improves relevance

---

### 10. Rephrase and Respond (RaR)

**Concept**: Ask model to interpret the task before executing.

**When to use**: Complex multi-part requests, ambiguous requirements.

**Example**:
```markdown
First, rephrase the following task in your own words to confirm understanding.
Then, execute it.

Task: Create a data pipeline that handles real-time events and batch processing
with exactly-once semantics and automatic failover.
```

**Token cost**: +50-100 tokens
**Benefit**: Catches misunderstandings early

---

## Advanced Techniques

### 11. Prompt Chaining

**Concept**: Sequential prompts where output of one becomes input to next.

**When to use**: Multi-stage workflows, complex transformations, quality gates.

**Chain structure**:
```
Prompt 1: Extract key entities from document
    ↓
Prompt 2: Classify entities by type
    ↓
Prompt 3: Generate structured report
    ↓
Prompt 4: Validate against schema
```

**IBM methodology**:
1. Identify main objectives
2. Decompose into sub-tasks
3. Create individual prompts per action
4. Map inputs/outputs between prompts
5. Test comprehensively

**Token cost**: Distributed across prompts (often more efficient than one mega-prompt)

---

### 12. Goal Decomposition

**Concept**: Break large tasks into numbered sub-goals addressed sequentially.

**When to use**: Project planning, complex implementations, comprehensive analysis.

**Example**:
```markdown
## Goal
Implement user authentication for the API.

## Sub-goals
1. Design database schema for users and sessions
2. Implement password hashing with Argon2
3. Create JWT token generation and validation
4. Build login/logout endpoints
5. Add middleware for protected routes
6. Write integration tests

Execute each sub-goal in order. Show work for each before proceeding.
```

**Token cost**: +50-100 tokens
**Output improvement**: "Far more structured, comprehensive, and actionable"

---

### 13. ReAct (Reason + Act)

**Concept**: Alternate between reasoning phases and action/tool-use phases.

**When to use**: Tool-augmented tasks, information gathering, complex problem-solving.

**Pattern**:
```
Reasoning: I need to find the user's recent orders
Action: query_database("SELECT * FROM orders WHERE user_id = 123")
Observation: [results]
Reasoning: User has 3 orders, the most recent is pending
Action: get_order_status(order_id=456)
Observation: [status]
Reasoning: I can now answer the user's question
Answer: Your most recent order #456 is currently being processed...
```

**Opus 4.5 Note**: Use "Reasoning:" instead of "Thought:" when extended thinking is disabled.

**Token cost**: +300-800 tokens
**Use case**: Agentic workflows, multi-hop queries

---

### 14. Self-Critique & Refinement

**Concept**: Generate initial response, evaluate against criteria, then revise.

**When to use**: Quality-critical outputs, creative content, code review.

**Example**:
```markdown
## Task
Write a product description.

## Process
1. Write initial draft
2. Evaluate against these criteria:
   - Clarity (1-5)
   - Persuasiveness (1-5)
   - Accuracy (1-5)
3. Identify weaknesses
4. Revise to address weaknesses
5. Output final version only
```

**Token cost**: +200-400 tokens
**Quality improvement**: Significant for creative/subjective tasks

---

### 14.5. Self-Evaluation Framework (P15) ⭐ HIGH IMPACT

**Concept**: Request model to rate confidence and refine if scores are low.

**When to use**: Quality-critical outputs, production prompts, complex analysis.

**Research Impact**: +10-20% completeness improvement (Bsharat et al., 2023)

**Example**:
```markdown
## Self-Evaluation
After your solution, rate your confidence (0-1) on:

1. **Completeness**: Did you cover all aspects?
2. **Clarity**: Is the solution easy to understand?
3. **Practicality**: Is it feasible and implementable?
4. **Edge Cases**: Did you address potential challenges?

Provide a score for each (0-1).
If any score < 0.9, refine your answer before presenting.
```

**Compact version**:
```markdown
Rate confidence (0-1): Completeness | Clarity | Practicality | Edge Cases
If any < 0.9, refine before presenting.
```

**Why it works**: Forces metacognitive reflection, triggers self-correction, provides quality signal.

**Token cost**: +30-60 tokens
**ROI**: High—catches errors before delivery

---

### 15. Step-Back Prompting

**Concept**: Establish foundational principles before addressing specifics.

**When to use**: Questions with multiple valid interpretations, domain-specific terminology.

**Example**:
```markdown
Before answering, first explain the relevant principles:

Question: Is a tomato a fruit or vegetable?

Step 1: Define "fruit" botanically and "vegetable" culinarily
Step 2: Apply definitions to tomatoes
Step 3: Provide context-dependent answer
```

**Token cost**: +100-200 tokens
**Benefit**: Clearer, more nuanced answers

---

### 16. Meta-Prompting

**Concept**: Use LLM to generate or improve prompts.

**When to use**: Discovering optimal phrasing, prompt iteration, A/B testing.

**Example**:
```markdown
I need a prompt that will make an LLM extract meeting action items.
The output should be a JSON array with assignee, task, and deadline.

Generate 3 different prompt variations, each using a different technique:
1. Few-shot approach
2. Structured template approach
3. Chain-of-thought approach

Rate each on expected clarity, reliability, and token efficiency.
```

**Token cost**: +200-500 tokens
**Use case**: Prompt optimization workflows

---

### 17. Thread-of-Thought (ThoT)

**Concept**: Maintain logical coherence and narrative flow across extended responses.

**When to use**: Long-form content, essays, multi-turn conversations.

**Example**:
```markdown
Write a technical blog post about microservices.

Requirements:
- Maintain logical flow between sections
- Each section should reference the previous
- Build toward a coherent conclusion
- Use transition phrases between major points

Outline first, then write section by section, ensuring continuity.
```

**Token cost**: +50-100 tokens overhead
**Benefit**: Coherent long-form output

---

## Technique Selection Matrix

| Task Type | Primary Technique | Supporting Techniques | Research Boost |
|-----------|-------------------|----------------------|----------------|
| Simple factual | Zero-shot | Explicit instructions | P6: Stakes |
| Classification | Few-shot | Output priming | P6: Stakes |
| Reasoning/math | Chain-of-thought (P12) | Step-back | P15: Self-eval |
| Code generation | Few-shot + Role (P16) | Self-critique | P6, P15 |
| Tool use | ReAct | Goal decomposition (P3) | P6: Stakes |
| Complex workflow | Prompt chaining | Goal decomposition (P3) | P6, P15, P16 |
| Creative writing | Role (P16) + Style | Self-critique, ThoT | P15: Self-eval |
| Documentation | Explicit + Contextual | Few-shot | P6: Stakes |
| **Architecture/Design** | Role (P16) + CoT (P12) | Goal decomposition (P3) | **P6, P15, P16** |
| **Production API** | All above combined | P6, P12, P15, P16 | **+45% quality** |

### Recommended Combinations for Maximum Impact

| Complexity | Combine These | Expected Improvement |
|------------|---------------|---------------------|
| Simple | P6 (stakes) + explicit | +45% |
| Moderate | P6 + P16 (persona) + P12 (CoT) | +60-80% |
| Complex | P6 + P16 + P3 (decomposition) + P15 (self-eval) | +80-100% |
| Production | All 5 high-impact principles | +100%+ |

---

## Sources

- [Bsharat et al. (2023) - "Principled Instructions Are All You Need"](https://arxiv.org/abs/2312.16171) - 26 principles, +45% improvement
- [VILA-Lab/ATLAS](https://github.com/VILA-Lab/ATLAS) - Dataset and resources for prompting research
- [IBM - Prompt Chaining](https://www.ibm.com/think/topics/prompt-chaining)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [GitHub - Prompt Engineering Cheatsheet](https://github.com/FareedKhan-dev/prompt-engineering-cheatsheet)
- [Anthropic Claude Documentation](https://docs.anthropic.com)
- [SuperAnnotate - 26 Prompting Tricks](https://www.superannotate.com/blog/llm-prompting-tricks)
