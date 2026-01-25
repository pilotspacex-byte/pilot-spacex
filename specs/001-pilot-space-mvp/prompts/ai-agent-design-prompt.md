# AI Agent Design Prompt Template

> **Purpose**: Design production-ready AI agents with proper orchestration, provider routing, and human-in-the-loop patterns using Claude Agent SDK.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` AI layer specifications and `docs/AI_CAPABILITIES.md`
>
> **Usage**: Use when designing new AI agents for Pilot Space or similar BYOK platforms.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Senior AI Systems Engineer with 12 years designing production LLM applications.
You excel at:
- Designing agent architectures with proper orchestration patterns
- Implementing human-in-the-loop approval flows for critical actions
- Routing tasks to appropriate LLM providers based on cost/latency/capability
- Creating context windows that maximize relevance while minimizing tokens

# Stakes Framing (P6)

This AI agent design is critical to [PROJECT_NAME]'s user experience.
A well-designed agent will:
- Provide accurate, contextual responses within latency SLAs
- Maintain user trust through transparent AI behavior
- Optimize costs by routing to appropriate providers
- Prevent harmful or unintended actions via approval flows

I'll tip you $200 for a production-ready agent design that passes all quality gates.

# Task Context

## Agent Overview
**Agent Name**: [AGENT_NAME]
**Purpose**: [ONE_SENTENCE_PURPOSE]
**Trigger**: [WHAT_INITIATES_THIS_AGENT]
**Output**: [WHAT_THE_AGENT_PRODUCES]

## Platform Constraints
**Orchestration**: [e.g., Claude Agent SDK for multi-turn, direct SDK for one-shot]
**Provider Strategy**: [e.g., Anthropic for code, Gemini for latency, OpenAI for embeddings]
**BYOK Model**: Users provide API keys (Anthropic required, others optional)

## User Story Reference
**Story ID**: US-[XX]
**Acceptance Criteria**: [KEY_CRITERIA_FROM_SPEC]

# Task Decomposition (P3)

Design the AI agent step by step:

## Step 1: Agent Classification
Determine the agent type:

| Classification | Criteria | Example |
|----------------|----------|---------|
| **Agentic (Claude SDK)** | Multi-turn, tool use, complex reasoning | PR Review, Task Decomposition |
| **Direct SDK Call** | One-shot, latency-sensitive, simple output | Ghost Text, Annotations |
| **Embedding Pipeline** | Vector operations, search | Semantic Search, RAG |

**Classification Decision**:
- [ ] Agentic (Claude Agent SDK) - Requires: Anthropic API key
- [ ] Direct SDK (Provider-specific) - Specify: [PROVIDER]
- [ ] Embedding Pipeline (OpenAI) - Requires: OpenAI API key

## Step 2: Provider Routing
Define provider selection:

| Task Type | Primary Provider | Fallback | Rationale |
|-----------|-----------------|----------|-----------|
| [TASK_TYPE] | [PRIMARY] | [FALLBACK] | [REASON] |

**Routing Rules** (from DD-011):
- Code analysis/review → Anthropic Claude (best code understanding)
- Latency-sensitive (<2s) → Google Gemini Flash (fastest)
- Embeddings → OpenAI text-embedding-3 (best quality/cost)
- Fallback on error → Next-best provider automatically

## Step 3: Context Window Design
Define what context the agent receives:

**Context Components**:
| Component | Source | Token Budget | Priority |
|-----------|--------|--------------|----------|
| [CONTEXT_1] | [SOURCE] | [~TOKENS] | P0/P1/P2 |
| [CONTEXT_2] | [SOURCE] | [~TOKENS] | P0/P1/P2 |

**Total Context Budget**: [X] tokens (of [MAX] allowed)

**Context Aggregation Strategy**:
```
Priority order:
1. [HIGHEST_PRIORITY_CONTEXT]
2. [MEDIUM_PRIORITY_CONTEXT]
3. [LOWER_PRIORITY_CONTEXT]

Truncation rule: [HOW_TO_HANDLE_OVERFLOW]
```

## Step 4: Human-in-the-Loop Design
Define approval requirements (per DD-003):

| Action | Auto-Execute | Require Approval | Rationale |
|--------|--------------|------------------|-----------|
| [ACTION_1] | ✅/❌ | ✅/❌ | [WHY] |
| [ACTION_2] | ✅/❌ | ✅/❌ | [WHY] |

**Approval Flow**:
```
1. Agent generates suggestion
2. UI displays with confidence indicator
3. User: Accept / Modify / Reject
4. [If critical] Explicit confirmation dialog
```

**Confidence Display** (per DD-048):
- ≥80%: "Recommended" tag with ★ icon
- <80%: "Default" tag (no icon)
- Show percentage on hover

## Step 5: Prompt Engineering
Design the agent's system prompt:

```markdown
# System Prompt for [AGENT_NAME]

You are [ROLE_DESCRIPTION].

## Context
{context_variables}

## Task
[CLEAR_TASK_STATEMENT]

## Constraints
- [CONSTRAINT_1]
- [CONSTRAINT_2]
- [OUTPUT_FORMAT_REQUIREMENTS]

## Output Format
[STRUCTURED_OUTPUT_SPEC]
```

**Prompt Variables**:
| Variable | Source | Format |
|----------|--------|--------|
| `{variable_1}` | [SOURCE] | [FORMAT] |
| `{variable_2}` | [SOURCE] | [FORMAT] |

## Step 6: Streaming & Response Handling
Define response delivery:

**Streaming Strategy**:
- [ ] SSE (Server-Sent Events) - For real-time text generation
- [ ] Polling - For background jobs
- [ ] WebSocket - For bidirectional (future)

**Response Format**:
```json
{
  "status": "streaming|complete|error",
  "content": "[GENERATED_CONTENT]",
  "confidence": 0.85,
  "metadata": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet",
    "tokens_used": 1234
  }
}
```

**Error Handling**:
| Error Type | Behavior | User Feedback |
|------------|----------|---------------|
| Provider timeout | Retry with backoff → fallback | "AI is taking longer than expected..." |
| Rate limit | Queue with delay | "Request queued, processing shortly" |
| API key invalid | Fail gracefully | "Please check your API key in settings" |
| Content policy | Return sanitized | "Some content was filtered" |

## Step 7: Testing Requirements
Define agent test coverage:

**Unit Tests**:
- [ ] Prompt template rendering with variables
- [ ] Context aggregation logic
- [ ] Provider routing decisions
- [ ] Error handling paths

**Integration Tests**:
- [ ] End-to-end with mock LLM responses
- [ ] Streaming behavior verification
- [ ] Timeout and retry logic
- [ ] Approval flow UI integration

**Quality Metrics**:
| Metric | Target | Measurement |
|--------|--------|-------------|
| Latency (p95) | <[X]s | Response timing |
| Accuracy | >[X]% | Human evaluation sample |
| Cost per call | <$[X] | Token tracking |

# Chain-of-Thought Guidance (P12)

For each section, consider:
1. **What provider is best?** - Match task requirements to provider strengths
2. **What context is essential?** - Minimize tokens while maximizing relevance
3. **What could go wrong?** - API failures, rate limits, bad input
4. **What needs approval?** - Anything destructive or irreversible

# Self-Evaluation Framework (P15)

After designing, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Provider Fit**: Best provider for task requirements | ___ | |
| **Context Design**: Sufficient context within budget | ___ | |
| **Safety**: Proper approval for critical actions | ___ | |
| **Error Handling**: Graceful degradation paths | ___ | |
| **Testability**: Clear test criteria defined | ___ | |
| **UX**: Clear user feedback during operations | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
## AI Agent Design: [AGENT_NAME]

### Overview
| Attribute | Value |
|-----------|-------|
| **Purpose** | [ONE_LINER] |
| **Classification** | Agentic / Direct SDK / Embedding |
| **Primary Provider** | [PROVIDER] |
| **Trigger** | [EVENT/ACTION] |
| **Latency Target** | <[X]s |

### Provider Routing
| Task | Provider | Fallback | Rationale |
|------|----------|----------|-----------|
| [TASK] | [PRIMARY] | [FALLBACK] | [REASON] |

### Context Window
**Budget**: [X] tokens of [MAX]

| Component | Tokens | Priority |
|-----------|--------|----------|
| [COMPONENT] | ~[N] | P[X] |

### Human-in-the-Loop
| Action | Behavior | Approval Required |
|--------|----------|-------------------|
| [ACTION] | [BEHAVIOR] | Yes/No |

### System Prompt
\`\`\`
[FULL_SYSTEM_PROMPT]
\`\`\`

### API Contract
**Endpoint**: `POST /api/v1/ai/[agent-name]`
**Request**: `{ [FIELDS] }`
**Response**: `{ [FIELDS] }`

### Error Handling
| Scenario | Behavior | User Message |
|----------|----------|--------------|
| [SCENARIO] | [BEHAVIOR] | "[MESSAGE]" |

### Test Matrix
- Unit: [COUNT] tests covering [AREAS]
- Integration: [COUNT] tests covering [FLOWS]
- Quality metrics: Latency <[X]s, Accuracy >[Y]%

---
*Agent Design Version: 1.0*
*Story Reference: US-[XX]*
```
```

---

## Quick-Fill Variants

### Variant A: Ghost Text Agent (Latency-Sensitive)

```markdown
**Agent Name**: GhostTextAgent
**Purpose**: Provide inline writing suggestions during typing pause
**Trigger**: 500ms pause in typing within note editor
**Output**: 1-2 sentence continuation (~50 tokens)

**Classification**: Direct SDK (NOT Claude Agent SDK - latency requirement)
**Primary Provider**: Google Gemini Flash (fastest)
**Latency Target**: <2 seconds

**Context Window** (minimal for speed):
- Current block text (~100 tokens)
- 3 previous blocks (~300 tokens)
- Section summary (~100 tokens)
Total: ~500 tokens

**Human-in-the-Loop**:
- Auto-generate suggestion (no approval)
- User: Tab to accept, Escape to dismiss
- Word-by-word acceptance with Right Arrow
```

### Variant B: PR Review Agent (Agentic)

```markdown
**Agent Name**: PRReviewAgent
**Purpose**: Comprehensive code review for pull requests
**Trigger**: PR opened/updated via GitHub webhook
**Output**: Structured review comments with severity ratings

**Classification**: Agentic (Claude Agent SDK)
**Primary Provider**: Anthropic Claude (best code analysis)
**Latency Target**: <5 minutes (async job)

**Context Window** (comprehensive):
- PR diff (~2000 tokens)
- Related issues (~500 tokens)
- Codebase patterns (~500 tokens)
- Test coverage (~300 tokens)
Total: ~3300 tokens

**Human-in-the-Loop**:
- Review posted as draft comments
- User reviews before publishing
- "Request Changes" requires explicit approval
```

### Variant C: Semantic Search (Embedding Pipeline)

```markdown
**Agent Name**: SemanticSearchAgent
**Purpose**: Find semantically related content across workspace
**Trigger**: Search query with "AI" toggle enabled
**Output**: Ranked list of related documents/issues

**Classification**: Embedding Pipeline
**Primary Provider**: OpenAI text-embedding-3-large (3072 dims)
**Latency Target**: <2 seconds

**Context Window**: N/A (embeddings don't use context window)

**Pipeline**:
1. Embed query → OpenAI
2. Vector search → pgvector (HNSW)
3. Re-rank results → Cosine similarity
4. Return top K

**Human-in-the-Loop**:
- Results displayed with relevance scores
- No approval needed (read-only operation)
```

---

## Validation Checklist

Before implementing agent, verify:

- [ ] Classification matches task requirements (agentic vs direct)
- [ ] Provider routing aligns with DD-011 guidelines
- [ ] Context window fits within token limits
- [ ] Critical actions require explicit approval (DD-003)
- [ ] Confidence display follows DD-048 patterns
- [ ] Error handling covers all failure modes
- [ ] Streaming strategy matches latency requirements
- [ ] Tests cover unit, integration, and quality metrics

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `docs/AI_CAPABILITIES.md` | Full AI capabilities spec |
| `docs/architect/ai-layer.md` | AI architecture details |
| `docs/DESIGN_DECISIONS.md` | DD-002, DD-003, DD-011, DD-048 |
| `specs/001-pilot-space-mvp/research.md` | Provider research |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.1 AI layer specifications*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
