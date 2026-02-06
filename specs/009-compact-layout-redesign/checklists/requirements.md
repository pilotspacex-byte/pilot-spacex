# Requirements Validation Checklist — 009 Compact Layout Redesign

## FR Traceability Matrix

| FR | Description | Story | Testable | Verified |
|----|------------|-------|----------|----------|
| FR-001 | Notification controls in sidebar bottom | US-1 | Yes | [ ] |
| FR-002 | User avatar in sidebar bottom | US-1 | Yes | [ ] |
| FR-003 | Collapsed sidebar: icons with tooltips | US-1 | Yes | [ ] |
| FR-004 | Expanded sidebar: horizontal row layout | US-1 | Yes | [ ] |
| FR-005 | Header reduced to 40px, breadcrumb only | US-2 | Yes | [ ] |
| FR-006 | Search bar removed from header | US-2 | Yes | [ ] |
| FR-007 | AI Assistant button removed from header | US-2 | Yes | [ ] |
| FR-008 | +New dropdown removed from header | US-2 | Yes | [ ] |
| FR-009 | Body text 14px -> 12px | US-3 | Yes | [ ] |
| FR-010 | Label/meta text 12px -> 10px | US-3 | Yes | [ ] |
| FR-011 | Navigation text 14px -> 12px | US-3 | Yes | [ ] |
| FR-012 | Proportional padding/gap reduction | US-3 | Yes | [ ] |
| FR-013 | Keyboard shortcuts preserved | US-2 | Yes | [ ] |
| FR-014 | Dropdown overflow prevention | US-1 | Yes | [ ] |
| FR-015 | Sidebar +New Note remains note-only | US-2 | Yes | [ ] |

## Files Affected

| File | Changes |
|------|---------|
| `components/layout/header.tsx` | Remove search, AI, +New, notifications, avatar; reduce height to h-10 |
| `components/layout/sidebar.tsx` | Add notification bell + user avatar to bottom section |
| `components/layout/app-shell.tsx` | Adjust sidebar header height alignment if needed |
| `app/globals.css` | Reduce base font sizes, adjust spacing scale |

## Smoke Test Scenarios

- [ ] Navigate to Notes list — verify compact layout, more items visible
- [ ] Open a note — verify header is 40px, breadcrumb only
- [ ] Click notification bell in sidebar — dropdown opens, positioned correctly
- [ ] Click user avatar in sidebar — menu opens with all options
- [ ] Collapse sidebar — notifications and avatar show as icons
- [ ] Press Cmd+K — search modal opens (keyboard shortcut preserved)
- [ ] Press Cmd+N — new note created (keyboard shortcut preserved)
- [ ] Verify text sizes: body 12px, labels 10px, nav 12px
- [ ] Test at 1280px viewport width — no overflow or clipping
