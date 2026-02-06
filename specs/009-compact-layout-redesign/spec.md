# Feature Specification: Compact Layout Redesign

**Feature Number**: 009
**Branch**: `009-compact-layout-redesign`
**Created**: 2026-02-04
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All Pilot Space users (Architects, Tech Leads, PMs, Developers)

**Problem**: The current app layout wastes vertical space with a 56px header containing redundant controls (search bar duplicated by keyboard shortcut, AI button accessible from note context, +New dropdown duplicated in sidebar). Header right-side actions (notifications, user avatar) occupy premium horizontal space that could serve page context. Font sizes and spacing are generous but reduce content density, forcing more scrolling on standard laptop screens.

**Impact**: Users see fewer note blocks, issues, and content per viewport. The duplicated creation controls (header +New vs sidebar +New Note) create decision friction. The prominent search bar is redundant for power users who use keyboard shortcuts. Overall, the layout feels spacious but inefficient for productivity-focused workflows.

**Success**: Users see 15-20% more content per viewport. The layout feels compact and professional. All controls remain accessible but consolidated in logical locations. The sidebar becomes the single control hub for navigation, creation, notifications, and user settings.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Architect / Owner | Clean, efficient layout that maximizes content area | Final approval on visual changes | Spec review + acceptance |
| End Users | Daily users | Faster workflows, less scrolling, familiar controls | Feedback on compactness comfort | Acceptance test |

---

## User Scenarios & Testing

### User Story 1 — Consolidated Sidebar Controls (Priority: P1)

Users access notifications and user account controls from the sidebar bottom instead of the header. The sidebar bottom section shows notification bell (with unread badge) and user avatar menu, alongside the existing collapse toggle and settings link. In collapsed mode, these render as stacked icons.

**Why this priority**: Core layout change that moves controls from header to sidebar. All other changes depend on the header being freed from these elements.

**Independent Test**: Navigate to any workspace page. Verify notification bell and user avatar appear in sidebar bottom. Click notification bell to see dropdown. Click avatar to see user menu with Profile, Settings, Keyboard shortcuts, Sign out. Verify header no longer contains these elements.

**Acceptance Scenarios**:

1. **Given** sidebar is expanded, **When** user views the sidebar bottom, **Then** notification bell (with unread count badge) and user avatar are displayed in a horizontal row above the collapse toggle
2. **Given** sidebar is collapsed, **When** user views the sidebar bottom, **Then** notification bell and user avatar are displayed as stacked icons with tooltips
3. **Given** user has 3 unread notifications, **When** user clicks the notification bell in sidebar, **Then** notification dropdown appears with the 3 notifications and "Mark all read" option
4. **Given** user clicks the avatar in sidebar, **When** the dropdown menu opens, **Then** it shows user name, email, Profile, Settings, Keyboard shortcuts, and Sign out options

---

### User Story 2 — Minimal Header Bar (Priority: P1)

The header bar is reduced to 40px height and contains only page breadcrumbs/context information (e.g., "Notes > Auth Refactor Jan 21 183 words") and page-specific actions (share, history, more menu). Search bar, AI Assistant button, +New dropdown, notifications, and user avatar are removed from the header.

**Why this priority**: Directly delivers the 16px vertical space savings and cleaner visual hierarchy. Tied to Story 1 (controls must move before header can slim down).

**Independent Test**: Navigate to a note page. Verify header shows only breadcrumb and page actions. Verify header height is visually compact (40px). Verify no search bar, AI button, +New, notification, or avatar controls in header.

**Acceptance Scenarios**:

1. **Given** user is on a note page, **When** viewing the header, **Then** only breadcrumb path and page-specific actions (history, share, more) are visible
2. **Given** user is on any workspace page, **When** measuring the header, **Then** height is 40px (h-10)
3. **Given** search bar is removed from header, **When** user presses the keyboard shortcut, **Then** search modal still opens normally
4. **Given** user is on a page with the AI chat panel open, **When** viewing the header, **Then** no AI-related buttons appear in the header

---

### User Story 3 — Aggressive Font & Spacing Compaction (Priority: P1)

All text across the application is reduced by approximately 2px. Body text goes from 14px to 12px, label/meta text from 12px to 10px, navigation items from 14px to 12px. Padding and gaps are proportionally reduced to maintain visual balance at the smaller sizes.

**Why this priority**: Maximizes content density gain. Combined with header reduction, delivers the 15-20% viewport efficiency target.

**Independent Test**: Compare any page before and after the change. Count visible content items (note blocks, issue rows) in the same viewport height. Verify at least 15% more items are visible. Verify text remains readable and maintains visual hierarchy.

**Acceptance Scenarios**:

1. **Given** user is viewing a notes list, **When** comparing content density, **Then** at least 15% more note items are visible in the same viewport
2. **Given** user is reading note content, **When** viewing body text, **Then** text is readable at the reduced size on standard laptop screens (13-16 inch)
3. **Given** sidebar is expanded, **When** viewing navigation items, **Then** labels are 12px and maintain clear readability
4. **Given** labels and metadata text exist, **When** viewing them, **Then** they render at 10px and remain legible

---

### Edge Cases

- What happens when notification dropdown opens from sidebar and sidebar is near screen edge? Dropdown MUST position to avoid overflow.
- What happens when user avatar menu opens from sidebar bottom? Menu MUST open upward or to the right to stay visible.
- What happens when text at 10px contains long words or labels? Text MUST truncate with ellipsis rather than overflow.
- What happens on screens smaller than 1280px wide? Layout MUST remain functional; sidebar collapse SHOULD auto-trigger.
- What happens when sidebar is collapsed and notification badge shows count > 99? Badge MUST show "99+" capped display.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST display notification controls in the sidebar bottom section instead of the header
- **FR-002**: System MUST display user avatar/account controls in the sidebar bottom section instead of the header
- **FR-003**: System MUST render sidebar bottom controls as icons with tooltips when sidebar is collapsed
- **FR-004**: System MUST render sidebar bottom controls in a horizontal row when sidebar is expanded
- **FR-005**: System MUST reduce header height to 40px and display only breadcrumb/page-context information
- **FR-006**: System MUST remove the search bar from the header (keyboard shortcut remains functional)
- **FR-007**: System MUST remove the AI Assistant button from the header
- **FR-008**: System MUST remove the +New dropdown from the header (sidebar +New Note button retained)
- **FR-009**: System MUST reduce body text from 14px to 12px globally
- **FR-010**: System MUST reduce label/metadata text from 12px to 10px globally
- **FR-011**: System MUST reduce navigation text from 14px to 12px
- **FR-012**: System MUST proportionally reduce padding and gaps to maintain visual balance at reduced font sizes
- **FR-013**: System MUST maintain all existing keyboard shortcuts (search, create note, create issue)
- **FR-014**: Notification and user avatar dropdowns in sidebar MUST position to avoid viewport overflow
- **FR-015**: System SHOULD maintain the existing sidebar +New Note button as note-only (no dropdown)

### Key Entities

- **Header**: Top bar component. Key attributes: height (40px), content (breadcrumb only). Relationships: AppShell, page-specific actions.
- **Sidebar**: Left navigation panel. Key attributes: width (60-260px), collapsed state. Relationships: AppShell, contains navigation + notes + creation + notifications + user controls.
- **SidebarBottomSection**: New logical section. Key attributes: notification bell, user avatar, collapse toggle, settings link. Relationships: Sidebar, NotificationStore, AuthStore.

---

## Success Criteria

- **SC-001**: Users see at least 15% more content items per viewport compared to current layout
- **SC-002**: Header height is exactly 40px (reduced from 56px)
- **SC-003**: All existing keyboard shortcuts function identically after layout change
- **SC-004**: Body text is 12px, labels are 10px, navigation items are 12px across the application
- **SC-005**: No visual overflow or clipping occurs at viewport widths 1280px and above
- **SC-006**: Notification and user menus in sidebar are accessible and position correctly

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | No | No AI behavior changes; layout only |
| II. Note-First | Yes | Note canvas gains more vertical space, reinforcing note-first workflow |
| III. Documentation-Third | No | No documentation changes |
| IV. Task-Centric | Yes | Stories are independently testable and decomposable |
| V. Collaboration | No | No collaboration feature changes |
| VI. Agile Integration | Yes | Stories fit sprint planning with clear acceptance criteria |
| VII. Notation Standards | No | No diagram/notation needs |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names anywhere in requirements
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P1 (all core, single sprint)
- [x] Functional requirements numbered sequentially (FR-001 through FR-015)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Next Phase

After this spec passes all checklists:

1. **Proceed to planning** — Create implementation plan with file-level change mapping
2. **Task breakdown** — Decompose into ordered tasks with dependencies
3. **Implementation** — Execute changes across header, sidebar, app-shell, and global CSS
