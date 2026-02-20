# Requirements Validation Checklist — 018 Note Editor Enhancements

## Functional Requirements Traceability

| FR | Requirement | User Story | Acceptance Scenario | Testable? |
|----|------------|------------|--------------------:|:---------:|
| FR-001 | `[[` autocomplete for note links | US-1 | US-1.1, US-1.2 | Yes |
| FR-002 | Render-time title resolution | US-1 | US-1.3 | Yes |
| FR-003 | Backlinks sidebar panel | US-1 | US-1.5 | Yes |
| FR-004 | Vertical TOC dots in left gutter | US-2 | US-2.1 | Yes |
| FR-005 | Magnet snap effect on TOC | US-2 | US-2.2 | Yes |
| FR-006 | Heading text on hover/focus | US-2 | US-2.3 | Yes |
| FR-007 | Issue indicator dots in gutter | US-3 | US-3.1 | Yes |
| FR-008 | Issue details popover | US-3 | US-3.2 | Yes |
| FR-009 | Project picker dropdown | US-5 | US-5.1, US-5.2 | Yes |
| FR-010 | Deleted note graceful handling | US-1 | US-1.6 | Yes |
| FR-011 | Gutter hidden < 1024px | US-2 | US-2.5 | Yes |
| FR-012 | Keyboard navigation for gutter | US-2, US-3 | US-2.3, US-3.2 | Yes |
| FR-013 | Reduced motion support | US-2 | US-2.7 | Yes |
| FR-014 | 24px+ touch targets | US-2, US-3 | WCAG 2.2 SC 2.5.8 | Yes |
| FR-015 | `/link-note` slash command | US-4 | US-4.1, US-4.2 | Yes |
| FR-016 | Clickable inline issue text/nodes | US-3 | US-3.5 | Yes |
| FR-017 | Idempotent note link creation | US-1 | Edge case | Yes |
| FR-018 | Exclude self-links from autocomplete | US-1 | US-1.7 | Yes |
| FR-019 | Throttled gutter position recalculation | US-2 | SC-002 | Yes |

## Coverage Summary

- **Total FRs**: 19
- **MUST**: 17
- **SHOULD**: 2
- **MAY**: 0
- **Covered by user stories**: 19/19 (100%)
- **Independently testable**: 19/19 (100%)

## Risk Mitigation Status

| Risk | Status | Resolution |
|------|--------|------------|
| R-1 (animation tech) | Resolved in spec | Use existing motion library |
| R-2 (positioning) | Resolved in spec | Absolute positioning per review |
| R-3 (dot collision) | Accepted | Separate columns + count badge |
| R-4 (stale titles) | Resolved in spec | FR-002 mandates render-time resolution |
| R-7 (duplicate links) | Resolved in spec | FR-017 mandates idempotent creation |
| R-8 (accessibility) | Resolved in spec | FR-012, FR-013, FR-014 mandate keyboard/touch/motion support |
