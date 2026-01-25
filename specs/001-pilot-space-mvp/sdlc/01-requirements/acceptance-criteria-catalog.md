# Acceptance Criteria Catalog

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This catalog provides testable acceptance criteria for all 18 user stories in the Pilot Space MVP. Each criterion follows the Given-When-Then format for clear, automatable testing.

---

## P0: Foundation

### US-01: Note-First Collaborative Writing

**Priority**: P0 | **Scenarios**: 22 | **Status**: Planned

#### AC-01.01: Note Canvas as Home
```gherkin
Given a user is logged in
When the app loads
Then the note canvas is displayed as the default home view
And no dashboard is shown
```

#### AC-01.02: Ghost Text Trigger
```gherkin
Given a user is typing in the note canvas
When they pause typing for 500ms
Then AI ghost text suggestions appear inline as faded text
And the suggestion is 1-2 sentences maximum
```

#### AC-01.03: Ghost Text Accept Full
```gherkin
Given ghost text is displayed
When the user presses Tab
Then the entire suggestion is accepted into the document
And the ghost text disappears
```

#### AC-01.04: Ghost Text Accept Word
```gherkin
Given ghost text is displayed
When the user presses → (right arrow)
Then only the first word of the suggestion is accepted
And remaining ghost text stays visible
```

#### AC-01.05: Ghost Text Word Boundaries (DD-067)
```gherkin
Given ghost text is streaming from AI
When tokens are received
Then chunks are buffered until whitespace/punctuation
And only complete words are displayed
And no partial tokens appear
```

#### AC-01.06: Margin Annotations Display
```gherkin
Given a user writes ambiguous content
When AI detects implicit intent
Then margin annotations appear asking clarifying questions
And annotations are positioned next to the relevant block
```

#### AC-01.07: Threaded Discussion
```gherkin
Given a margin annotation exists
When the user clicks "Discuss"
Then a threaded AI discussion opens for that block
And the user can send messages to continue the conversation
```

#### AC-01.08: Issue Categorization
```gherkin
Given AI identifies root issues from user content
When presenting extracted issues
Then AI categorizes as:
  - 🔴 Explicit (what user directly stated)
  - 🟡 Implicit (what user meant but didn't say)
  - 🟢 Related (what user will also need)
```

#### AC-01.09: Issue Extraction Count
```gherkin
Given a user is writing actionable content
When AI detects potential issues
Then margin shows count "N issues detected"
And count updates as user continues writing
```

#### AC-01.10: Issue Review Rainbow Boxes
```gherkin
Given margin shows detected issues
When user clicks "Review"
Then rainbow-bordered boxes wrap source text inline
And each box shows proposed issue title and description
```

#### AC-01.11: Issue Accept/Skip
```gherkin
Given a proposed issue is displayed
When the user reviews it
Then they can:
  - Edit title/description before accepting
  - Accept to create the issue
  - Skip to move to next proposal
```

#### AC-01.12: Bidirectional Note-Issue Linking
```gherkin
Given an issue is accepted from a note
When the issue is created
Then the issue links back to the source note
And the note shows a link to the created issue
```

#### AC-01.13: Issue State Sync Badge
```gherkin
Given a note has linked issues
When a linked issue changes state
Then a sync indicator badge appears in the note
And badge shows the new state (e.g., "Completed")
```

#### AC-01.14: Selection Toolbar
```gherkin
Given a user selects text in the note
When selection is made
Then a toolbar appears with AI actions:
  - Improve
  - Simplify
  - Expand
  - Ask
  - Extract
```

#### AC-01.15: Virtualized Rendering
```gherkin
Given a note has 1000+ blocks
When the user scrolls
Then rendering maintains smooth 60fps
And only visible blocks are rendered
```

#### AC-01.16: Table of Contents
```gherkin
Given a note has multiple headings
When the user views the note
Then auto-generated TOC appears
And clicking a TOC item scrolls to that section
```

#### AC-01.17: Autosave
```gherkin
Given a user is editing a note
When they pause typing for 1-2 seconds
Then content saves automatically
And a subtle "Saved" indicator appears
```

#### AC-01.18: Extended Undo Stack
```gherkin
Given a user makes edits (text, AI changes, block moves)
When they press Cmd+Z
Then the most recent change is reverted
And undo history includes AI-generated changes
```

#### AC-01.19: Annotation Click Navigation
```gherkin
Given a margin annotation exists
When the user clicks the annotation
Then the linked content block highlights
And smooth scroll animation centers it
```

#### AC-01.20: Note Pinning
```gherkin
Given a frequently accessed note
When the user clicks "Pin"
Then the note appears at the top of the sidebar
```

#### AC-01.21: Resizable Margin Panel
```gherkin
Given the user needs more annotation space
When they drag the margin edge
Then the margin panel resizes between 150px and 350px
```

#### AC-01.22: Note Metadata Display
```gherkin
Given a note is open
When viewing the header
Then user sees:
  - Created date
  - Last edited date
  - Author
  - Word count
  - AI-estimated reading time
```

---

## P1: Core Workflow

### US-02: AI Issue Creation

**Priority**: P1 | **Scenarios**: 8 | **Status**: Planned

#### AC-02.01: AI Title Enhancement
```gherkin
Given a user is creating a new issue
When they type a brief title
Then AI suggests an enhanced, searchable title within 2 seconds
```

#### AC-02.02: AI Description Enhancement
```gherkin
Given a user has entered a description
When they request AI enhancement
Then AI expands with acceptance criteria and technical notes
```

#### AC-02.03: AI Metadata Suggestions
```gherkin
Given issue content is entered
When the user views suggestions
Then AI recommends:
  - Relevant labels
  - Priority level
  - Potential assignees based on expertise
```

#### AC-02.04: Duplicate Detection
```gherkin
Given a new issue is being created
When similar issues exist with >70% similarity
Then the system flags potential duplicates
And shows similarity score and link to existing issue
```

#### AC-02.05: Suggestion Independence
```gherkin
Given AI makes multiple suggestions
When the user reviews them
Then they can accept, modify, or reject each independently
```

#### AC-02.06: Confidence Tags Display
```gherkin
Given AI suggests labels or priorities
When displaying confidence
Then contextual tags appear:
  - "Recommended" for >= 80% confidence
  - Percentage shown on hover
```

#### AC-02.07: Bulk AI Actions
```gherkin
Given multiple issues are selected
When the user invokes AI bulk action
Then AI can summarize or extract common themes
```

#### AC-02.08: AI Context Menu
```gherkin
Given a user right-clicks on an issue
When the context menu opens
Then an AI section shows suggestions:
  - "Find related issues"
  - "Suggest assignee"
  - "Generate subtasks"
```

---

### US-03: AI PR Review

**Priority**: P1 | **Scenarios**: 5 | **Status**: Planned

#### AC-03.01: Auto-Trigger Review
```gherkin
Given a GitHub repository is linked
When a PR is opened
Then AI automatically reviews within 5 minutes
```

#### AC-03.02: Inline Comments
```gherkin
Given AI completes a review
When issues are found
Then comments are posted inline on the PR
With specific line references
```

#### AC-03.03: Unified Review Coverage
```gherkin
Given a PR with code changes
When AI reviews it
Then review covers:
  - Architecture compliance
  - Security vulnerabilities
  - Code quality
  - Performance concerns
```

#### AC-03.04: Severity Markers
```gherkin
Given AI review identifies an issue
When the review is posted
Then issue is marked with severity:
  - 🔴 Critical (must fix)
  - 🟡 Warning (should fix)
  - 🔵 Suggestion (nice to have)
```

#### AC-03.05: Rationale and Links
```gherkin
Given a PR author reviews AI feedback
When they want more context
Then each comment includes:
  - Rationale for the finding
  - Relevant documentation links
```

---

### US-04: Sprint Planning

**Priority**: P1 | **Scenarios**: 5 | **Status**: Planned

#### AC-04.01: Create Cycle
```gherkin
Given a user is a project admin
When they create a new cycle
Then they can set:
  - Start date
  - End date
  - Sprint goals
```

#### AC-04.02: Add Issues to Cycle
```gherkin
Given a cycle exists
When a user adds issues to it
Then issues appear on the sprint board organized by state
```

#### AC-04.03: Drag-and-Drop State Change
```gherkin
Given issues are in a cycle
When a user drags an issue to a new column
Then the issue state updates immediately
```

#### AC-04.04: Cycle Metrics
```gherkin
Given a cycle is active
When a user views the cycle
Then they see:
  - Completion percentage
  - Velocity (story points completed)
  - Burndown chart
```

#### AC-04.05: Cycle Rollover
```gherkin
Given a cycle ends with incomplete issues
When the cycle closes
Then user can:
  - Roll issues over to next cycle
  - Return issues to backlog
```

---

## P2: Enhanced Features

### US-05 - US-09 (Modules, Pages, Task Decomp, Diagrams, Slack)

*See [spec.md](../../spec.md) for complete acceptance scenarios.*

Summary counts:
- US-05 Modules/Epics: 4 scenarios
- US-06 Documentation Pages: 7 scenarios
- US-07 Task Decomposition: 5 scenarios
- US-08 Architecture Diagrams: 5 scenarios
- US-09 Slack Integration: 5 scenarios

---

## P3: Supporting Features

### US-10 - US-18 (Search, Settings, AI Context, Command Palette, etc.)

*See [spec.md](../../spec.md) for complete acceptance scenarios.*

Summary counts:
- US-10 Semantic Search: 4 scenarios
- US-11 Workspace Settings: 4 scenarios
- US-12 AI Context: 4 scenarios
- US-13 Command Palette: 4 scenarios
- US-14 Knowledge Graph: 4 scenarios
- US-15 Templates: 3 scenarios
- US-16 Sample Project: 3 scenarios
- US-17 Notifications: 3 scenarios
- US-18 GitHub Integration: 5 scenarios

---

## Test Coverage Summary

| Priority | User Stories | Total Scenarios | Automated | Manual |
|----------|--------------|-----------------|-----------|--------|
| P0 | 1 | 22 | 18 | 4 |
| P1 | 3 | 18 | 15 | 3 |
| P2 | 5 | 26 | 20 | 6 |
| P3 | 9 | 34 | 28 | 6 |
| **Total** | **18** | **100** | **81** | **19** |

---

## Test Automation Strategy

### Automated (81 scenarios)
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical flows

### Manual (19 scenarios)
- Visual verification (UI appearance)
- AI response quality assessment
- Accessibility with screen readers
- Performance perception testing

---

## References

- [spec.md](../../spec.md) - Full user story details
- [testing-strategy.md](../05-development/testing-strategy.md) - Test implementation
- [requirements-traceability.md](./requirements-traceability.md) - RTM
