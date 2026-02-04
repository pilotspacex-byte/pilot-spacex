# Requirements Validation Checklist — 008: Enhanced Thinking & Tool Call Visualization

## Functional Requirements Traceability

| FR | Description | User Story | Priority | Testable |
|----|-------------|-----------|----------|----------|
| FR-001 | Thinking indicator within 100ms | US-1 | P1 | Yes — measure time from SSE event to DOM render |
| FR-002 | Stream thinking with cursor effect | US-1 | P1 | Yes — observe typewriter animation during thinking |
| FR-003 | Elapsed time on thinking blocks | US-1 | P1 | Yes — verify counter increments every second |
| FR-004 | Auto-collapse on thinking completion | US-1 | P1 | Yes — verify collapse transition after last thinking event |
| FR-005 | Tool call cards with name/status/time | US-2 | P1 | Yes — trigger tool and verify card elements |
| FR-006 | Tool card status transitions | US-2 | P1 | Yes — verify pending→running→completed/failed |
| FR-007 | Streaming state banner | US-3 | P1 | Yes — observe banner phase transitions |
| FR-008 | Collapsible tool input/output with formatting | US-2 | P1 | Yes — expand tool card, verify syntax highlighting |
| FR-009 | Parallel tool call grouping | US-2 | P1 | Yes — trigger parallel tools, verify visual grouping |
| FR-010 | Independent interleaved thinking blocks | US-1 | P1 | Yes — verify G-07 multi-block independence |
| FR-011 | Frosted-glass thinking block design | US-4 | P2 | Yes — visual inspection of AI accent styling |
| FR-012 | Token estimate on thinking blocks | US-4 | P2 | Yes — verify badge shows ~N tokens |
| FR-013 | Timeline/waterfall for 3+ tool calls | US-5 | P2 | Yes — trigger 3+ tools, toggle timeline view |
| FR-014 | Token budget indicator | US-6 | P3 | Yes — verify progress bar updates with usage |
| FR-015 | prefers-reduced-motion support | All | P1 | Yes — enable reduced-motion, verify no continuous animations |
| FR-016 | Dark mode support | All | P1 | Yes — toggle dark mode, verify all new components |
| FR-017 | Preserve partial content on interruption | US-1, US-2 | P1 | Yes — abort stream, verify content preserved |

## Coverage Summary

- **P1 Requirements**: 12 (FR-001 through FR-010, FR-015 through FR-017)
- **P2 Requirements**: 3 (FR-011 through FR-013)
- **P3 Requirements**: 1 (FR-014)
- **Total**: 17
- **All testable**: Yes

## Edge Case Coverage

| Edge Case | Related FR | Covered By |
|-----------|-----------|------------|
| Very long thinking (>2000 tokens) | FR-002 | US-1 edge case — scrollable max-height |
| Tool call >30s | FR-005, FR-007 | US-2/US-3 edge case — persistent elapsed time |
| SSE connection drop | FR-017 | Edge case — "Interrupted" state |
| Empty thinking events | FR-001 | Edge case — skip empty blocks |
| Scroll during streaming | FR-007 | Edge case — banner stays visible |
| Dark mode | FR-016 | Edge case — all components |
| Reduced motion | FR-015 | Edge case — static fallbacks |
