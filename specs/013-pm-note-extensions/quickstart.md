# Quickstart Validation: PM Note Extensions

**Feature**: 013-pm-note-extensions
**Source**: `specs/013-pm-note-extensions/plan.md` — Quickstart Validation section

---

## Scenario 1: Diagram Block — Happy Path (P1)

1. Open a note in the editor
2. Type `/diagram` and press Enter
3. Select "Flowchart" from the type dropdown
4. Type: `flowchart TD\n  A[Start] --> B[Process]\n  B --> C[End]`
5. **Verify**: Live preview shows flowchart with 3 nodes + 2 arrows
6. Toggle "Edit Source" → see source editor. Toggle back → see rendered diagram
7. Close and reopen the note
8. **Verify**: Diagram persists with identical source and renders correctly
9. **Verify**: Auto-save triggered within 2s of changes

## Scenario 2: Agent Diagram Auto-Insertion (P1)

1. Open a note and start chat with AI Agent
2. Type: "Can you draw the architecture of our authentication flow?"
3. **Verify**: Agent inserts a diagram block (sequence or flowchart) into the note
4. Press Ctrl+Z
5. **Verify**: The diagram block is completely removed (single undo step)

## Scenario 3: Smart Checklist (P2)

1. Type `/checklist` in a note
2. Add item: "Review PR" — set priority: high, assignee: self, due: tomorrow
3. Add item: "Update docs" — set as optional
4. Check "Review PR"
5. **Verify**: Progress bar shows 100% (optional "Update docs" excluded from denominator)
6. **Verify**: Due date badge visible next to "Review PR"
7. **Verify**: Priority "high" badge visible
8. Uncheck "Review PR"
9. **Verify**: Progress bar returns to 0%

## Scenario 4: Invalid Diagram Syntax — Error Path (P1)

1. Insert a diagram block via `/diagram`
2. Type valid syntax first: `flowchart TD\n  A --> B`
3. **Verify**: Diagram renders correctly
4. Change to invalid: `flowchartTD\nA-->>`
5. **Verify**: Inline error message appears below the block with parse error
6. **Verify**: Last valid render (A→B flowchart) is still displayed

## Scenario 5: Decision Record (P2)

1. Type `/decision` in a note
2. Fill title: "Redis vs Memcached for caching"
3. Add option "Redis" — pros: "Rich data structures", cons: "Higher memory"
4. Add option "Memcached" — pros: "Simple, fast", cons: "No persistence"
5. Click "Decide" and select "Redis"
6. Enter rationale: "Need pub/sub and persistence for session management"
7. **Verify**: Status changes to "Decided", summary banner shows "Redis" selected
8. Click "Create Issue"
9. **Verify**: New issue created with decision context in description
10. **Verify**: Issue ID linked back to decision record

## Scenario 6: Form Block (P3)

1. Type `/form` in a note
2. Add fields: "What went well?" (long text, required), "Satisfaction" (rating 1-5), "Priority" (dropdown: low/medium/high)
3. Fill in: "Good CI/CD pipeline", 4 stars, "medium"
4. Click away from form
5. **Verify**: No validation errors (all required fields filled)
6. Reload page
7. **Verify**: All responses persist exactly as entered

## Scenario 7: Risk Register (P3)

1. Type `/risk-register` in a note
2. Add risk: "API latency spike during peak hours"
3. Set probability: 4, impact: 3
4. **Verify**: Score auto-calculates to 12, row background is yellow
5. Change impact to 5
6. **Verify**: Score updates to 20, row background turns red
7. Set strategy: "Mitigate", owner: self, trigger: "P95 latency > 500ms"
8. **Verify**: All fields persist after auto-save

## Scenario 8: Interactive Visualization — Sandbox (P4)

1. Type `/chart` and select "Force-directed graph"
2. Provide data: 5 nodes with 6 edges
3. **Verify**: Graph renders with physics simulation
4. Drag a node
5. **Verify**: Graph rebalances — connected nodes follow with physics
6. Open browser DevTools → Network tab
7. **Verify**: No network requests originate from the visualization iframe
8. **Verify**: `document.cookie` from within iframe returns empty (sandbox isolation)
