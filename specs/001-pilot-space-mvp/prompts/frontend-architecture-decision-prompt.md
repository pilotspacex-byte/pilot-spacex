# Frontend Architecture Decision Prompt Template

> **Purpose**: Resolve ambiguous frontend architecture decisions with structured analysis and clear implementation guidance.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` Session 2026-01-22 Frontend Architecture Decisions pattern
>
> **Usage**: Use when facing frontend architecture ambiguities requiring technical decision-making.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Principal Frontend Architect with 15 years building complex React applications at scale.
You excel at:
- State management architecture decisions (MobX, Zustand, TanStack Query, Context)
- Real-time data synchronization and optimistic updates
- Performance optimization (virtualization, code splitting, bundle size)
- Accessibility-first component design
- Testing strategies for complex UI interactions

# Stakes Framing (P6)

This frontend architecture decision impacts [PROJECT_NAME]'s long-term maintainability.
Getting it right will:
- Reduce bugs by 60% through clear data flow patterns
- Enable 50% faster feature development with established conventions
- Prevent costly rewrites from scalability issues

I'll tip you $200 for a thorough analysis with clear implementation guidance.

# Decision Context

## Question
[STATE THE SPECIFIC ARCHITECTURE QUESTION]

## Relevant Context
- **Current Stack**: [FRONTEND_STACK]
- **Related Patterns**: [EXISTING_PATTERNS]
- **Constraints**: [PERFORMANCE/BUNDLE/ACCESSIBILITY_CONSTRAINTS]
- **Affected Components**: [COMPONENT_LIST]

# Task Decomposition (P3)

Evaluate this decision step by step:

## Step 1: Problem Framing
| Aspect | Details |
|--------|---------|
| **What problem are we solving?** | [PROBLEM_STATEMENT] |
| **Why does this matter?** | [BUSINESS_IMPACT] |
| **What are the constraints?** | [TECHNICAL_CONSTRAINTS] |
| **What does success look like?** | [SUCCESS_CRITERIA] |

## Step 2: Options Analysis
Identify at least 3 viable options:

### Option A: [OPTION_NAME]
**Description**: [HOW_IT_WORKS]

**Pros**:
- [PRO_1]
- [PRO_2]

**Cons**:
- [CON_1]
- [CON_2]

**Implementation Example**:
```typescript
// Code example showing pattern
```

### Option B: [OPTION_NAME]
[Same structure as Option A]

### Option C: [OPTION_NAME]
[Same structure as Option A]

## Step 3: Decision Matrix
| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Performance | [1-5] | [1-5] | [1-5] | [1-5] |
| Maintainability | [1-5] | [1-5] | [1-5] | [1-5] |
| Developer Experience | [1-5] | [1-5] | [1-5] | [1-5] |
| Bundle Impact | [1-5] | [1-5] | [1-5] | [1-5] |
| Testing Ease | [1-5] | [1-5] | [1-5] | [1-5] |
| **Weighted Total** | | **[SCORE]** | **[SCORE]** | **[SCORE]** |

## Step 4: Decision
| Aspect | Details |
|--------|---------|
| **Chosen Option** | [OPTION_NAME] |
| **Rationale** | [WHY_THIS_WINS] |
| **Trade-offs Accepted** | [ACKNOWLEDGED_CONS] |
| **Reversibility** | [HOW_TO_CHANGE_LATER] |

## Step 5: Implementation Guidance
Provide specific, actionable implementation details:

**Pattern**:
```typescript
// Show the recommended code pattern
```

**Anti-Pattern** (what NOT to do):
```typescript
// Show the pattern to avoid
```

**Edge Cases**:
| Scenario | Handling |
|----------|----------|
| [EDGE_CASE_1] | [HOW_TO_HANDLE] |
| [EDGE_CASE_2] | [HOW_TO_HANDLE] |

**Testing Approach**:
```typescript
// Show how to test this pattern
```

# Self-Evaluation Framework (P15)

Rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All options considered | ___ | |
| **Clarity**: Decision is unambiguous | ___ | |
| **Practicality**: Implementable with current stack | ___ | |
| **Consistency**: Aligns with existing patterns | ___ | |
| **Edge Cases**: Failure modes addressed | ___ | |

If any < 0.9, refine before presenting.

# Output Format

```markdown
### [N]. [DECISION_TITLE]

| Question | [FULL_QUESTION] |
|----------|-----------------|
| **Decision** | [CHOSEN_APPROACH] - [BRIEF_DESCRIPTION] |
| **Implementation** | [KEY_IMPLEMENTATION_DETAIL] |
| **[ADDITIONAL_ASPECT]** | [DETAIL] |
| **[EDGE_CASE_ASPECT]** | [HANDLING] |
```
```

---

## Example Decisions (from plan.md)

### 1. State Management Responsibility Split

| Question | What is TanStack Query vs MobX boundary? |
|----------|------------------------------------------|
| **Decision** | MobX UI-only - TanStack Query handles ALL server data, MobX only for ephemeral UI state |
| **MobX Scope** | Selection state, UI mode toggles, local form drafts, temporary filters |
| **TanStack Scope** | All fetched data (notes, issues, projects), cache, mutations, optimistic updates |
| **Pattern** | No MobX store subscribes to TanStack Query - use `useQuery` hooks directly in components |

### 3. Ghost Text SSE Cancellation

| Question | How to cancel ghost text request when user continues typing? |
|----------|--------------------------------------------------------------|
| **Decision** | AbortController - Cancel previous SSE stream on new keystroke |
| **Implementation** | Each ghost text request creates new `AbortController`, signal passed to `fetch()` |
| **Cleanup** | On component unmount OR new keystroke → `controller.abort()` |
| **UI Behavior** | Previous suggestion fades out, new request starts |

### 7. SSE Connection Management

| Question | One SSE stream per AI feature or multiplexed? |
|----------|-----------------------------------------------|
| **Decision** | Separate streams + cookie auth - Each AI operation gets own EventSource |
| **Auth** | HttpOnly cookie for session, no token in URL |
| **Lifecycle** | EventSource created on operation start, closed on completion/abort |
| **Reconnect** | Browser auto-reconnect for network drops, custom retry for errors |

### 9. TipTap Extension Key Priority

| Question | How to handle Tab key conflicts between ghost text and code block? |
|----------|-------------------------------------------------------------------|
| **Decision** | Context-aware priority |
| **Ghost Text** | Tab accepts suggestion ONLY when ghost text is visible |
| **Code Block** | Tab inserts indent when cursor is inside code block |
| **Priority Order** | 1) Code block context → indent, 2) Ghost text visible → accept, 3) Default → next field |
| **Implementation** | Custom keymap extension with priority ordering |

### 14. Motion/Animation Handling

| Question | How to respect prefers-reduced-motion? |
|----------|----------------------------------------|
| **Decision** | CSS media query - All animations in CSS with `@media (prefers-reduced-motion: reduce)` fallback |
| **Implementation** | Tailwind `motion-safe:` and `motion-reduce:` variants |
| **JS Animations** | Check `window.matchMedia('(prefers-reduced-motion: reduce)')` before triggering |
| **Fallback** | Instant state changes, no transitions |

---

## Decision Categories

Use this template for these frontend architecture decisions:

### State Management
- Store boundaries (client vs server state)
- Cache invalidation strategies
- Optimistic update patterns
- Real-time data merging

### Performance
- Virtualization library selection
- Code splitting boundaries
- Bundle optimization strategies
- Lazy loading triggers

### Component Architecture
- Extension key priorities
- Focus management patterns
- Modal/overlay lifecycle
- Error boundary placement

### Accessibility
- Motion handling
- Keyboard navigation
- Screen reader announcements
- Focus restoration

### Testing
- Integration test boundaries
- Mock strategies for SSE/WebSocket
- Accessibility automation
- E2E test scope

---

## Validation Checklist

Before finalizing decision:

- [ ] At least 3 options analyzed
- [ ] Decision matrix completed with weighted scores
- [ ] Code examples for both pattern and anti-pattern
- [ ] Edge cases identified with handling
- [ ] Testing approach documented
- [ ] Reversibility path clear

---

*Template Version: 1.0*
*Extracted from: plan.md v6.0 Frontend Architecture Decisions*
*Techniques Applied: P3 (decomposition), P6 (stakes), P15 (self-eval), P16 (persona)*
