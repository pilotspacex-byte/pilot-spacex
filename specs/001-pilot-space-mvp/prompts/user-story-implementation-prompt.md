# User Story Implementation Prompt Template

> **Purpose**: Generate detailed implementation specifications for individual user stories with clarifications, component mappings, and acceptance criteria.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/plan.md` User Story Implementation Breakdown pattern
>
> **Usage**: Use when implementing a specific user story from a feature specification.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Staff Software Engineer with 15 years implementing complex features in production systems.
You excel at:
- Translating user stories into precise technical specifications
- Identifying ambiguities and resolving them with stakeholder-aligned clarifications
- Mapping features to components, data models, and APIs
- Creating acceptance criteria that are testable and complete

# Stakes Framing (P6)

This user story implementation is critical to [PROJECT_NAME]'s [MILESTONE/RELEASE].
A well-specified story will:
- Enable developers to implement without ambiguity
- Reduce review cycles by 50% through clear acceptance criteria
- Prevent scope creep through explicit boundaries

I'll tip you $200 for a complete, unambiguous implementation specification.

# Task Context

## User Story
**ID**: US-[XX]
**Title**: [STORY_TITLE]
**Priority**: P[N] (P0=Critical, P1=High, P2=Medium, P3=Low)
**Acceptance Scenarios**: [COUNT]

## Story Statement
As a [USER_ROLE],
I want to [ACTION/CAPABILITY],
So that [BUSINESS_VALUE].

## Related Documentation
- Feature Spec: [SPEC_LOCATION]
- UI Design: [UI_SPEC_LOCATION]
- Data Model: [DATA_MODEL_LOCATION]
- API Contracts: [API_SPEC_LOCATION]

# Task Decomposition (P3)

Evaluate and specify this user story step by step:

## Step 1: UI/UX Requirements
Document visual and interaction specifications:

**UI Design References**:
- [SECTION_NAME]: [UI_SPEC_SECTION] ([KEY_SPECS])

**Component Layout**:
| Component | Location | Key Specifications |
|-----------|----------|-------------------|
| [COMPONENT_NAME] | [FILE_PATH] | [DIMENSIONS, BEHAVIOR, STYLING] |

**Visual Specifications**:
- Colors: [COLOR_TOKENS]
- Typography: [FONT_SPECS]
- Spacing: [SPACING_RULES]
- Animation: [MOTION_SPECS]

## Step 2: Clarifications Resolution
Identify and resolve ambiguities:

**Clarifications Applied**:
| Question | Answer | Implementation Impact |
|----------|--------|----------------------|
| [What triggers X?] | [Specific trigger] | [Code/component impact] |
| [How to handle Y?] | [Specific behavior] | [Edge case handling] |
| [What context for Z?] | [Data requirements] | [API/state impact] |

**Clarification Categories**:
- **Trigger Conditions**: When does this feature activate?
- **Data Requirements**: What inputs/context needed?
- **Edge Cases**: Error states, empty states, limits?
- **Integration Points**: What systems does this touch?

## Step 3: Data Model Mapping
Define entities and relationships:

**Data Model Entities**: [ENTITY_1], [ENTITY_2], [ENTITY_3]

**Entity Details**:
```
[ENTITY_NAME]:
  - [FIELD]: [TYPE] - [DESCRIPTION]
  - [FIELD]: [TYPE] - [DESCRIPTION]
  - Relationships: [RELATIONS]
```

**State Machine** (if applicable):
```
[STATE_1] → [STATE_2] → [STATE_3]
     ↓          ↓
[STATE_4]  [STATE_5]
```

## Step 4: Component Mapping
Map story to implementation components:

**Frontend Components**:
| Component | Location | Purpose |
|-----------|----------|---------|
| [COMPONENT] | `[PATH]` | [RESPONSIBILITY] |

**Backend Components**:
| Component | Location | Purpose |
|-----------|----------|---------|
| [SERVICE/ROUTER] | `[PATH]` | [RESPONSIBILITY] |

**AI Agents** (if applicable):
| Agent | Trigger | Output |
|-------|---------|--------|
| [AGENT_NAME] | [TRIGGER_CONDITION] | [OUTPUT_TYPE] |

## Step 5: API Contracts
Define request/response specifications:

**Endpoints**:
```
[METHOD] /api/v1/[RESOURCE]
  Request: { [FIELDS] }
  Response: { [FIELDS] }
  Errors: [ERROR_CODES]
```

**Real-time Events** (if applicable):
```
Channel: [CHANNEL_NAME]
Event: [EVENT_TYPE]
Payload: { [FIELDS] }
```

## Step 6: Acceptance Criteria
Define testable success conditions:

**Scenario [N]: [SCENARIO_NAME]**
```gherkin
Given [PRECONDITION]
When [ACTION]
Then [EXPECTED_RESULT]
And [ADDITIONAL_VERIFICATION]
```

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| [EDGE_CASE] | [INPUT] | [BEHAVIOR] |

## Step 7: Testing Requirements
Define test coverage:

**Unit Tests**:
- [ ] [COMPONENT]: [TEST_CASE]

**Integration Tests**:
- [ ] [FLOW]: [TEST_CASE]

**E2E Tests**:
- [ ] [USER_FLOW]: [TEST_CASE]

**Accessibility Tests**:
- [ ] Keyboard navigation: [REQUIREMENTS]
- [ ] Screen reader: [ARIA_REQUIREMENTS]

# Chain-of-Thought Guidance (P12)

For each section, consider:
1. **What could go wrong?** - Error states, network failures, concurrent access
2. **What's missing?** - Implicit requirements, cross-cutting concerns
3. **What's the minimum viable?** - MVP scope vs nice-to-have
4. **What blocks this?** - Dependencies on other stories/infrastructure

# Self-Evaluation Framework (P15)

After specifying, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Completeness**: All scenarios covered | ___ | |
| **Clarity**: Developer can implement without questions | ___ | |
| **Testability**: Criteria are verifiable | ___ | |
| **Consistency**: Aligns with design system/patterns | ___ | |
| **Edge Cases**: Failure modes addressed | ___ | |
| **Accessibility**: WCAG 2.2 AA compliance | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
### US-[XX]: [STORY_TITLE] (P[N])

**Spec Reference**: User Story [XX] | **Priority**: P[N] | **Acceptance Scenarios**: [COUNT]

**UI Design References**: [SPEC] Sections [X-Y]
- [FEATURE_1]: Section [X] ([KEY_SPECS])
- [FEATURE_2]: Section [Y] ([KEY_SPECS])

**Clarifications Applied**:

| Question | Answer | Implementation Impact |
|----------|--------|----------------------|
| [Q1] | [A1] | [IMPACT_1] |
| [Q2] | [A2] | [IMPACT_2] |

**Component Mapping**:
| Component | Location | Key Specifications |
|-----------|----------|-------------------|
| `[Component.tsx]` | [SECTION] | [SPECS] |

**Data Model Entities**: [ENTITY_1], [ENTITY_2]
**Key Components**: `[Component1]`, `[Component2]`, `[Agent]`

---
```
```

---

## Example: US-01 Note-First Collaborative Writing

```markdown
### US-01: Note-First Collaborative Writing (P0)

**Spec Reference**: User Story 1 | **Priority**: P0 (Critical Path) | **Acceptance Scenarios**: 18

**UI Design References**: ui-design-spec.md Sections 7-8
- Note Canvas Layout: Section 7 (Layout Architecture)
- Document Canvas: Section 7.2 (720px max-width, 32px padding)
- Margin Annotations: Section 7.3 (200px width, 150-350px resizable, AI muted background)
- Ghost Text: Section 8.2 (40% opacity, italic, 150ms fade-in, 500ms trigger)
- Issue Extraction: Section 7.4 (Rainbow-bordered boxes, 2px gradient border)

**Clarifications Applied**:

| Question | Answer | Implementation Impact |
|----------|--------|----------------------|
| What triggers ghost text besides 500ms pause? | Typing pause only | Single trigger mechanism, no manual activation |
| How to position multiple margin annotations? | Vertical stack next to block, scroll if overflow | CSS flex column layout with overflow-y |
| What patterns trigger issue detection? | Action verbs + entities (e.g., "implement X", "fix Y") | NLP pattern matching in AI agent |
| Max ghost text length? | 1-2 sentences (~50 tokens) | Token limit in prompt config |
| Ghost text in code blocks? | Code-aware suggestions using code completion model | Provider routing for code context |

**Component Mapping**:
| Component | UI Spec Section | Key Specifications |
|-----------|-----------------|-------------------|
| `NoteCanvas.tsx` | 7.2 | 720px max, 32px padding, warm background |
| `OutlineTree.tsx` | 7.1 | 220px width, VS Code-inspired tree |
| `MarginAnnotations.tsx` | 7.3 | 200px default, AI muted bg, 3px left border |
| `GhostTextExtension.ts` | 8.2 | 40% opacity, italic, Tab/→ to accept |
| `IssueExtractionPanel.tsx` | 7.4 | Rainbow gradient border, hover scale 2% |

**Data Model Entities**: Note, NoteBlock, NoteAnnotation, NoteIssueLink
**Key Components**: `NoteCanvas.tsx`, `GhostText.ts` (TipTap extension), `MarginAnnotations.tsx`
```

---

## Validation Checklist

Before implementation, verify:

- [ ] All clarification questions have definitive answers
- [ ] Component paths match project structure
- [ ] UI specs are referenced with section numbers
- [ ] Data model entities exist in data-model.md
- [ ] Acceptance scenarios are testable (Given/When/Then)
- [ ] Edge cases have explicit handling
- [ ] Accessibility requirements documented

---

*Template Version: 1.0*
*Extracted from: plan.md v6.0 User Story Implementation Breakdown*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
