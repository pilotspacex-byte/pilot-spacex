# UI Design Specification: Pilot Space MVP

**Version**: 4.0.0
**Created**: 2026-01-20
**Updated**: 2026-02-01
**Status**: Final - Synced with DD-001 to DD-056, US-01 to US-18, pilotspace-agent-architecture v1.5.0
**Major Change**: Complete page catalog, ChatView system, component inventory, responsive matrix, animation system
**Design System**: `/design-system/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Design Philosophy](#2-design-philosophy)
3. [Visual Identity](#3-visual-identity)
4. [Design Foundation](#4-design-foundation)
5. [Component Library](#5-component-library)
6. [Complete Component Catalog](#6-complete-component-catalog)
7. [Page Catalog](#7-page-catalog)
8. [ChatView System](#8-chatview-system)
9. [Note Canvas (Editor)](#9-note-canvas-editor)
10. [AI Collaborative Features](#10-ai-collaborative-features)
11. [Navigation & Search](#11-navigation--search)
12. [Interaction Patterns](#12-interaction-patterns)
13. [Animation & Motion System](#13-animation--motion-system)
14. [State Management Architecture (UI Perspective)](#14-state-management-architecture-ui-perspective)
15. [Responsive Design Matrix](#15-responsive-design-matrix)
16. [Dark Mode](#16-dark-mode)
17. [Empty States](#17-empty-states)
18. [Error States & Edge Cases](#18-error-states--edge-cases)
19. [Accessibility Deep Dive](#19-accessibility-deep-dive)
20. [Implementation Notes](#20-implementation-notes)

---

## 1. Overview

### Purpose

This document defines the complete UI/UX specifications for Pilot Space MVP, an AI-Augmented SDLC Platform. It serves as the authoritative reference for implementing every page, component, interaction, and visual treatment in the frontend application.

### Design Goals

| Goal | Description | Metric |
|------|-------------|--------|
| **Thought-First** | Users brainstorm before structuring | Note-to-Issue conversion rate > 60% |
| **Warmth** | Interface feels approachable and human | User satisfaction > 4.5/5 |
| **Collaboration** | AI feels like a teammate, not a tool | AI acceptance rate > 70% |
| **Efficiency** | Power users complete tasks quickly | Issue creation < 2 min |
| **Clarity** | AI contributions always attributable | 100% AI content labeled |
| **Accessibility** | Usable by all team members | WCAG 2.2 AA compliant |
| **Performance** | Fast, responsive interface | Page load < 3s, interactions < 100ms |

### Technology Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Framework | React 18 + TypeScript | Strict mode enabled |
| Styling | TailwindCSS 3.4+ | JIT compilation |
| Components | shadcn/ui | Radix UI primitives |
| Icons | Lucide React | 1.5px stroke, rounded caps |
| Fonts | Geist (UI), Geist Mono (code) | Vietnamese support |
| Animation | CSS transitions | Minimal, functional only |
| Drag & Drop | dnd-kit | Accessible by default |
| Rich Text | TipTap | ProseMirror-based |
| State | MobX + TanStack Query | UI + server state split |
| Charts | Recharts | Burndown, velocity, cost |

### User Stories Covered

| Priority | Stories | Pages Affected |
|----------|---------|----------------|
| **P0** | US-01 | Note Canvas, Note Editor, Notes List |
| **P1** | US-02 | Issue Board, Issue Detail, Issue Modal |
| **P1** | US-03 | PR Review, GitHub Integration |
| **P1** | US-04 | Cycles List, Cycle Detail, Burndown/Velocity |
| **P1** | US-12 | AI Context Panel, Claude Code Prompt |
| **P1** | US-18 | GitHub Integration Settings, Commit Activity |
| **P2-P3** | US-05 to US-17 | Settings, Search, Notifications, Templates |

---

## 2. Design Philosophy

### Core Principles

Pilot Space embodies three adjectives: **Warm, Capable, Collaborative**

| Principle | Meaning | Implementation |
|-----------|---------|----------------|
| **Warm** | Interface feels inviting, not clinical | Warm off-white backgrounds, soft shadows, natural colors |
| **Capable** | Powerful without being intimidating | Spacious layouts, progressive disclosure, clear hierarchy |
| **Collaborative** | AI is a teammate, not a system | "You + AI" attribution, friendly visual voice, co-pilot metaphor |

### Inspirations

| Product | What We Take |
|---------|--------------|
| **Craft** | Rich layered surfaces, beautiful typography, calm sophistication |
| **Apple** | Squircle corners, frosted glass, tinted shadows, material depth |
| **Things 3** | Natural color accents, spacious calm, delightful minimalism |

### What Pilot Space Is NOT

- Cold, clinical enterprise software
- Generic shadcn/ui defaults (Inter, orange accent, pure white)
- AI as a separate "system" bolted onto the UI
- Dense, overwhelming information displays

---

## 3. Visual Identity

### Brand Personality

> **Pilot Space feels like a well-designed workspace crafted by people who care about your focus. It's warm without being casual, sophisticated without being cold. AI isn't a feature bolted on -- it's a friendly teammate whose suggestions appear naturally in your workflow.**

### The Pilot Metaphor

The name "Pilot Space" evokes navigation and guidance. The AI is your **co-pilot**:

- **Pilot Avatar**: A compass/navigation star icon represents AI contributions
- **Guidance, not control**: AI suggests; humans decide
- **Shared journey**: "You + AI" attribution for collaborative work

### Visual Elements

| Element | Treatment |
|---------|-----------|
| **Surfaces** | Layered with subtle depth, warm off-white base |
| **Shadows** | Soft, diffused, slightly tinted |
| **Corners** | Apple-style squircles (high border-radius) |
| **Textures** | Subtle noise overlay for warmth |
| **Effects** | Frosted glass for modals and overlays |

---

## 4. Design Foundation

### Color System

#### Base Palette (Warm Neutrals)

| Token | Light Mode | Dark Mode | Description |
|-------|------------|-----------|-------------|
| `--background` | `#FDFCFA` | `#1A1A1A` | Warm off-white / Soft dark |
| `--background-subtle` | `#F7F5F2` | `#1F1F1F` | Secondary surfaces |
| `--foreground` | `#171717` | `#EDEDED` | Near-black / Soft white |
| `--foreground-muted` | `#737373` | `#999999` | Secondary text |
| `--border` | `#E5E2DD` | `#2E2E2E` | Borders |
| `--border-subtle` | `#EBE8E4` | `#262626` | Subtle borders |

#### Primary Accent (Teal-Green)

| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#29A386` | Fresh teal-green for primary actions |
| `--primary-hover` | `#238F74` | Hover state |
| `--primary-muted` | `#29A38615` | Subtle backgrounds |

#### AI Teammate Color (Dusty Blue)

| Token | Value | Usage |
|-------|-------|-------|
| `--ai` | `#6B8FAD` | Calm dusty blue for AI elements |
| `--ai-muted` | `#6B8FAD15` | AI annotation backgrounds |
| `--ai-border` | `#6B8FAD30` | AI element borders |

#### Issue State Colors

| State | Color | Icon | Description |
|-------|-------|------|-------------|
| Backlog | Warm Gray `#9C9590` | Circle (empty) | Unstarted, low priority |
| Todo | Soft Blue `#5B8FC9` | Circle (dotted) | Ready to start |
| In Progress | Amber `#D9853F` | Half circle | Actively being worked |
| In Review | Soft Purple `#8B7EC8` | Circle (three-quarter) | Awaiting review |
| Done | Teal-Green `#29A386` | Check circle | Completed (matches primary) |
| Cancelled | Warm Red `#D9534F` | X circle | Abandoned/rejected |

#### Priority Colors

| Priority | Color | Indicator |
|----------|-------|-----------|
| Urgent | Warm Red `#D9534F` | 4 vertical bars |
| High | Amber `#D9853F` | 3 vertical bars |
| Medium | Gold `#C4A035` | 2 vertical bars |
| Low | Soft Blue `#5B8FC9` | 1 vertical bar |
| None | Warm Gray `#9C9590` | Horizontal line |

### Typography

#### Font Stack

| Type | Font Family | Fallback |
|------|-------------|----------|
| UI Text | Geist | system-ui, -apple-system, sans-serif |
| Code | Geist Mono | SF Mono, Monaco, monospace |

#### Type Scale

| Name | Size | Line Height | Weight | Usage |
|------|------|-------------|--------|-------|
| `text-xs` | 11px | 16px | 400 | Labels, badges, captions |
| `text-sm` | 13px | 20px | 400 | Body text, descriptions |
| `text-base` | 15px | 24px | 400 | Primary content |
| `text-lg` | 17px | 26px | 500 | Card titles, emphasis |
| `text-xl` | 20px | 28px | 600 | Section headers |
| `text-2xl` | 24px | 32px | 600 | Page titles |
| `text-3xl` | 30px | 38px | 700 | Hero text |

#### Typography Rules

- Use `text-balance` on headings for better line breaks
- Use `tabular-nums` for metrics, counters, and tables
- Use curly quotes, not straight quotes
- Use proper ellipsis, not three periods
- AI voice uses regular weight with italic style

### Spacing System

Based on 4px grid with generous whitespace:

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight spacing, icon gaps |
| `space-2` | 8px | Element gaps |
| `space-3` | 12px | Component internal padding |
| `space-4` | 16px | Standard padding |
| `space-6` | 24px | Section spacing |
| `space-8` | 32px | Large gaps |
| `space-12` | 48px | Major section breaks |
| `space-16` | 64px | Page-level spacing |

### Border Radius (Apple Squircle Style)

| Token | Value | Usage |
|-------|-------|-------|
| `rounded-sm` | 6px | Small elements, badges |
| `rounded` | 10px | Buttons, inputs |
| `rounded-lg` | 14px | Cards, containers |
| `rounded-xl` | 18px | Modals, large cards |
| `rounded-2xl` | 24px | Hero elements |
| `rounded-full` | 9999px | Avatars, pills |

### Shadows

| Level | Behavior | Usage |
|-------|----------|-------|
| Shadow SM | Minimal lift, warm-tinted | Subtle elevation |
| Shadow | Standard card depth | Cards, containers |
| Shadow MD | Medium lift | Dropdowns, popovers |
| Shadow LG | Strong depth | Modals |
| Shadow Elevated | Maximum lift | Hover states on interactive cards |

All shadows use warm-tinted black with layered approach for natural depth.

### Visual Textures

#### Noise Overlay

- Subtle grain texture for warmth and tactile quality
- 2% opacity, multiply blend mode
- Applied to major surface areas

#### Frosted Glass

- Used for modals, popovers, and overlays
- 20px blur with 180% saturation
- 72% background opacity
- 50% opacity border

---

## 5. Component Library

### Buttons

#### Variants

| Variant | Background | Text | Border | Usage |
|---------|------------|------|--------|-------|
| `default` | Primary teal | White | None | Primary actions |
| `secondary` | Muted | Foreground | None | Secondary actions |
| `outline` | Transparent | Foreground | Border | Tertiary actions |
| `ghost` | Transparent | Foreground | None | Subtle actions |
| `destructive` | Warm red | White | None | Delete/remove |
| `ai` | AI blue 10% | AI blue | AI blue 20% | AI-related actions |

#### Sizes

| Size | Height | Padding | Font | Icon |
|------|--------|---------|------|------|
| `sm` | 32px | 12px | 13px | 16px |
| `default` | 38px | 16px | 14px | 18px |
| `lg` | 44px | 24px | 15px | 20px |
| `icon` | 38px | -- | -- | 18px |
| `icon-sm` | 32px | -- | -- | 16px |

#### Interaction States

| State | Behavior |
|-------|----------|
| Hover | Scale up 2%, elevated shadow |
| Active | Scale back 2%, deeper shadow |
| Focus | 3px teal ring at 30% opacity |

### Cards

#### Variants

| Variant | Shadow | Hover | Usage |
|---------|--------|-------|-------|
| `default` | Shadow SM | None | Static content |
| `elevated` | Shadow | None | Prominent content |
| `interactive` | Shadow SM | Scale + shadow | Clickable cards |
| `glass` | None | None | Overlay content |

#### Interactive Card Behavior

- Hover: Translate up 2px, scale 1%, medium shadow
- Active: Return to baseline, scale down 1%
- Transition: 200ms ease

### Badges

| Variant | Background | Text | Usage |
|---------|------------|------|-------|
| `default` | Primary 10% | Primary | Primary status |
| `secondary` | Muted | Foreground | Generic tags |
| `outline` | Transparent | Foreground | Subtle tags |
| State variants | State color 10% | State color | Issue states |
| `ai` | AI blue 10% | AI blue | AI indicators |

### Inputs

| Property | Value |
|----------|-------|
| Height | 38px |
| Padding | 0 12px |
| Border Radius | 10px (rounded) |
| Border | 1px solid border color |
| Font Size | 14px |
| Focus | Primary border, 3px primary ring at 10% |
| Transition | 150ms border and shadow |

### Dialog / Modal

| Property | Value |
|----------|-------|
| Overlay | 40% black, 8px blur |
| Content | 95% background opacity, 20px blur |
| Border | 1px at 50% opacity |
| Border Radius | 18px (rounded-xl) |
| Shadow | Shadow LG |

### Skeleton / Loading

| Property | Value |
|----------|-------|
| Animation | Diagonal shimmer, 1.5s infinite |
| Background | Gradient from muted to lighter and back |
| Background Size | 200% width |
| Border Radius | 6px (rounded-sm) |

---

## 6. Complete Component Catalog

### 6.1 Layout Components

#### AppShell (`components/layout/app-shell.tsx`)

The root layout wrapper for all authenticated workspace pages.

```
+------------------------------------------------------------+
|  SIDEBAR  |  HEADER                        [Search] [+] [P] |
|           |----------------------------------------------- |
|  Logo     |                                                 |
|  -------  |                                                 |
|  Home     |              MAIN CONTENT                       |
|  Notes    |         (children rendered here)                |
|  Issues   |                                                 |
|  Projects |                                                 |
|  Chat     |                                                 |
|  -------  |                                                 |
|  Settings |                                                 |
|  User     |                                                 |
+------------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Sidebar Width (expanded) | 260px |
| Sidebar Width (collapsed) | 60px |
| Header Height | 56px |
| Content Max Width | 1200px (pages), unlimited (editor) |
| Content Padding | 32px (standard), 0 (editor pages) |

#### Sidebar

| Section | Content |
|---------|---------|
| Header | Workspace selector (dropdown), collapse toggle |
| Navigation | Home, Notes, Issues, Projects, AI Chat, Approvals, Costs |
| Projects List | Expandable project tree with cycles/modules |
| Footer | Settings link, User avatar + menu, Integration badges |

| Property | Value |
|----------|-------|
| Background | `--background-subtle` |
| Border | 1px right `--border` |
| Font Size | 13px (`text-sm`) |
| Item Height | 36px |
| Item Padding | 8px horizontal, 4px vertical |
| Active Item | `--primary-muted` background, `--primary` text |
| Hover Item | `--background-subtle` darker |
| Section Labels | 10px uppercase, `--foreground-muted`, 0.05em tracking |
| Collapse Transition | 200ms width ease-in-out |

#### Header

| Element | Specification |
|---------|---------------|
| Workspace Selector | Dropdown with workspace name + avatar, switch workspaces |
| Search | Input with Cmd+K hint, opens search modal |
| Create Button | `+` icon, dropdown: New Note, New Issue, New Project |
| Notifications Bell | Badge count, opens notification center |
| User Avatar | 32px circle, dropdown with profile/settings/logout |

### 6.2 Editor Components (13 TipTap Extensions)

All extensions located in `features/notes/editor/extensions/`.

| Extension | File | Purpose |
|-----------|------|---------|
| **BlockIdExtension** | `BlockIdExtension.ts` | Assigns and preserves unique block IDs (`<!-- block:uuid -->`) for each paragraph/heading. Required for margin annotations and issue linking. |
| **GhostTextExtension** | `GhostTextExtension.ts` | ProseMirror decoration plugin rendering AI autocomplete suggestions as faded inline text. Handles Tab (accept all), Right Arrow (accept word), Escape (dismiss). |
| **AnnotationMark** | `AnnotationMark.ts` | TipTap mark for highlighted text ranges linked to margin annotations. Renders as subtle AI-color background highlight. |
| **MarginAnnotationExtension** | `MarginAnnotationExtension.ts` | NodeView extension rendering margin annotation anchors. Uses CSS Anchor Positioning (Chrome 125+) with absolute positioning fallback. |
| **MarginAnnotationAutoTriggerExtension** | `MarginAnnotationAutoTriggerExtension.ts` | Watches editor transactions and auto-triggers margin annotation generation after significant content changes (>20% block delta). |
| **IssueLinkExtension** | `IssueLinkExtension.ts` | Mark extension for `[PS-123](issue:uuid)` inline links. Renders as clickable badges with issue state color. |
| **InlineIssueExtension** | `InlineIssueExtension.ts` | Node extension for full inline issue boxes with rainbow border. Renders `InlineIssueComponent.tsx` via NodeView. |
| **CodeBlockExtension** | `CodeBlockExtension.ts` | Enhanced code block with syntax highlighting, language selector, and copy button. |
| **MentionExtension** | `MentionExtension.ts` | `@` trigger for mentioning notes, issues, projects, and AI agents. Renders dropdown with fuzzy search. |
| **SlashCommandExtension** | `SlashCommandExtension.ts` | `/` trigger for block-level commands (heading, list, code, divider, image, diagram). |
| **ParagraphSplitExtension** | `ParagraphSplitExtension.ts` | Custom Enter key handling to maintain block IDs when splitting paragraphs. |
| **EditorToolbar** | `EditorToolbar.tsx` | Floating selection toolbar with formatting + AI actions. |
| **createEditorExtensions** | `createEditorExtensions.ts` | Factory function composing all extensions with configuration. |

### 6.3 Issue Components

| Component | Location | Description |
|-----------|----------|-------------|
| **IssueCard** | `components/issues/IssueCard.tsx` | Compact card for board/list views. Shows state icon, identifier (PS-123), title, labels (pill badges), priority bars, comment count, attachment count, assignee avatars, AI attribution badge. |
| **IssueBoard** | `components/issues/IssueBoard.tsx` | Kanban board with 6 state columns (Backlog, Todo, In Progress, In Review, Done, Cancelled). Uses dnd-kit for drag-and-drop. Column headers show count badge. |
| **IssueModal** | `components/issues/IssueModal.tsx` | Create/edit dialog. Fields: title, description (TipTap mini editor), state, priority, assignee, labels, cycle, module, estimate. AI enhancement button triggers IssueEnhancerAgent for label/priority suggestions. |
| **IssueStateSelect** | `components/issues/IssueStateSelect.tsx` | Dropdown with 6 states, each with colored icon matching state colors. Valid transitions enforced. |
| **IssuePrioritySelect** | `components/issues/IssuePrioritySelect.tsx` | Dropdown with 5 priority levels, each with colored vertical bar indicator. |
| **AssigneeSelector** | `components/issues/AssigneeSelector.tsx` | Combobox with workspace member search, avatar + name display, "Unassigned" option. |
| **LabelSelector** | `components/issues/LabelSelector.tsx` | Multi-select combobox with colored dot indicators, create-new inline. |
| **TaskChecklist** | `components/issues/TaskChecklist.tsx` | AI-generated subtask checklist within issue detail. Checkboxes with strike-through on complete. Reorderable via drag. |
| **DuplicateWarning** | `components/issues/DuplicateWarning.tsx` | Alert banner shown during issue creation when DuplicateDetectorAgent finds similar issues (>85% similarity). Shows matched issue cards with "Link Instead" action. |
| **AIContext** | `components/issues/AIContext.tsx` | Aggregated AI context panel for issue detail. Sections: Related Docs, Related Code, Task Breakdown, Claude Code Prompts. Manual refresh button. |
| **ContextChat** | `components/issues/ContextChat.tsx` | Embedded ChatView scoped to a specific issue context. Appears in issue detail sidebar. |
| **ContextItemList** | `components/issues/ContextItemList.tsx` | List of context items (notes, code files, related issues) with relevance score indicators. |
| **ClaudeCodePrompt** | `components/issues/ClaudeCodePrompt.tsx` | Pre-formatted prompt card for copy-paste into Claude Code. Monospace text, copy button with checkmark feedback. |
| **DeleteConfirmDialog** | `components/issues/DeleteConfirmDialog.tsx` | Destructive action confirmation with issue identifier display, type-to-confirm for batch operations. |

#### Issue Card Anatomy

```
+--------------------------------------+
|                                      |
|  O PS-123              * You + AI    |  <- State icon, AI attribution
|                                      |
|  Implement user authentication       |  <- Title (Geist, medium weight)
|  flow for OAuth providers            |
|                                      |
|  [bug] [frontend]                    |  <- Rounded pill badges
|                                      |
|  |||.  2 comments  1 attach    OO    |  <- Priority, meta, avatars
|                                      |
+--------------------------------------+
```

### 6.4 Cycle Components

| Component | Location | Description |
|-----------|----------|-------------|
| **CycleBoard** | `components/cycles/CycleBoard.tsx` | Sprint planning board. Shows cycle name, date range, progress bar, issue list grouped by state. Supports drag-to-assign issues. |
| **BurndownChart** | `components/cycles/BurndownChart.tsx` | Recharts area chart. X-axis: cycle days. Y-axis: remaining story points. Ideal line (dashed) vs actual line (solid primary). Tooltip shows date + points remaining. |
| **VelocityChart** | `components/cycles/VelocityChart.tsx` | Recharts bar chart. Last 6 cycles. Y-axis: completed story points. Average line overlay. Hover shows cycle name + completed/planned ratio. |
| **CycleRolloverModal** | `components/cycles/CycleRolloverModal.tsx` | End-of-cycle dialog. Shows incomplete issues with options: move to next cycle, move to backlog, or mark done. Bulk selection support. |

### 6.5 Integration Components (GitHub)

| Component | Location | Description |
|-----------|----------|-------------|
| **GitHubIntegration** | `components/integrations/GitHubIntegration.tsx` | Settings page for GitHub App installation. OAuth flow, repo selection checklist, webhook status indicators. |
| **PRReviewStatus** | `components/integrations/PRReviewStatus.tsx` | Badge showing AI review status (Pending, Reviewing, Complete, Failed). Colored dot + label. |
| **ReviewCommentCard** | `components/integrations/ReviewCommentCard.tsx` | Individual review comment with severity badge (info/warning/error), file path, line number, suggestion text, code diff. |
| **ReviewSummary** | `components/integrations/ReviewSummary.tsx` | Aggregated PR review summary card. Overall score, category breakdown (Architecture, Code Quality, Security, Performance, Documentation), finding counts by severity. |
| **BranchSuggestion** | `components/integrations/BranchSuggestion.tsx` | AI-suggested branch name based on issue title. Copy button, format: `type/PS-123-slug`. |
| **CommitList** | `components/integrations/CommitList.tsx` | Timeline of linked commits with hash, message preview, author, timestamp. Links to GitHub. |
| **PRLinkBadge** | `components/integrations/PRLinkBadge.tsx` | Inline badge showing linked PR number, status (open/merged/closed), links to GitHub PR. |

### 6.6 Approval Components

| Component | Location | Description |
|-----------|----------|-------------|
| **ApprovalCard** | `features/approvals/components/approval-card.tsx` | Card displaying pending approval with action type icon, description, affected entities preview, countdown timer, approve/reject buttons. |
| **ApprovalDetailModal** | `features/approvals/components/approval-detail-modal.tsx` | Full detail dialog with action description, consequences, affected entities list, proposed content diff, approve with optional modifications, reject with reason. |
| **ApprovalListItem** | `features/approvals/components/approval-list-item.tsx` | Compact list item for approval queue. Status badge (Pending/Approved/Rejected/Expired), timestamp, quick actions. |

### 6.7 Cost Components

| Component | Location | Description |
|-----------|----------|-------------|
| **CostSummaryCard** | `features/costs/components/cost-summary-card.tsx` | Metric card showing total cost, token usage, request count for a time period. Trend arrow (up/down) with percentage change. |
| **DateRangeSelector** | `features/costs/components/date-range-selector.tsx` | Date range picker with presets (Today, 7d, 30d, 90d, Custom). Calendar popover for custom ranges. |
| **CostByAgentChart** | `features/costs/components/cost-by-agent-chart.tsx` | Recharts horizontal bar chart. Each agent (GhostText, IssueExtractor, PRReview, etc.) with cost bar. Color-coded by agent type. |
| **CostTrendsChart** | `features/costs/components/cost-trends-chart.tsx` | Recharts line chart. X-axis: days. Y-axis: daily cost. Stacked by provider (Anthropic, OpenAI, Google). |
| **CostTableView** | `features/costs/components/cost-table-view.tsx` | Data table with columns: Date, Agent, Provider, Model, Input Tokens, Output Tokens, Cost. Sortable, filterable, paginated. |

### 6.8 Settings Components

| Component | Location | Description |
|-----------|----------|-------------|
| **APIKeyInput** | `features/settings/components/api-key-input.tsx` | Masked input field for API keys. Show/hide toggle. Validation indicator (green check / red x). "Test Connection" button. |
| **APIKeyForm** | `features/settings/components/api-key-form.tsx` | Form containing multiple APIKeyInput fields for each provider (Anthropic required, OpenAI required for search, Google optional). Save button with confirmation. |
| **AIFeatureToggles** | `features/settings/components/ai-feature-toggles.tsx` | Switch toggles for individual AI features: Ghost Text, Margin Annotations, Issue Enhancement, Duplicate Detection, PR Review. Each with description and enabled/disabled state. |
| **ProviderStatusCard** | `features/settings/components/provider-status-card.tsx` | Card per AI provider showing name, logo, connection status (Connected/Error/Not Configured), model info, last verified timestamp. |

### 6.9 AI Components

| Component | Location | Description |
|-----------|----------|-------------|
| **AIConfidenceTag** | `components/ai/AIConfidenceTag.tsx` | Visual badge for AI suggestion confidence. Four variants: Recommended (filled star, primary), Default (no icon, muted), Current (AI blue), Alternative (dashed border). Hover shows percentage tooltip. |
| **CountdownTimer** | `components/ai/CountdownTimer.tsx` | Circular countdown visualization for approval expiration. Shows remaining time in mm:ss. Color transitions from green to amber to red as time decreases. |

### 6.10 Navigation Components

| Component | Location | Description |
|-----------|----------|-------------|
| **OutlineTree** | `components/navigation/OutlineTree.tsx` | VS Code-inspired tree navigation in sidebar. Shows notes, issues, projects with expand/collapse. Active item highlighted. Keyboard navigable (arrow keys). |
| **PinnedNotesList** | `components/navigation/PinnedNotesList.tsx` | Sidebar section showing pinned notes (max 5). Pin icon, subtle primary background. Right-click or menu to unpin. |

### 6.11 Note-Specific Feature Components

| Component | Location | Description |
|-----------|----------|-------------|
| **margin-annotation-list** | `features/notes/components/margin-annotation-list.tsx` | Right-margin panel rendering annotation cards aligned to their source blocks. Virtualized for long notes. |
| **annotation-card** | `features/notes/components/annotation-card.tsx` | Individual margin annotation. AI avatar, suggestion text, accept/dismiss buttons, expand for detail. |
| **annotation-detail-popover** | `features/notes/components/annotation-detail-popover.tsx` | Expanded annotation with full AI reasoning, multiple suggestions, edit capability. |
| **ExtractedIssueCard** | `features/notes/components/ExtractedIssueCard.tsx` | Issue preview card within extraction approval flow. Shows title, priority, type with edit capability before creation. |
| **IssueExtractionPanel** | `features/notes/components/IssueExtractionPanel.tsx` | Side panel listing extracted issues from note content. Each with checkbox for selective creation. |
| **IssueExtractionApprovalModal** | `features/notes/components/IssueExtractionApprovalModal.tsx` | Modal for reviewing and approving batch issue extraction. Shows each issue with editable fields, select all/none, confirm creation. |

---

## 7. Page Catalog

### 7.1 Auth Pages

#### Login Page (`/login`)

**Route**: `(auth)/login/page.tsx`
**Layout**: Centered, minimal, no sidebar
**Reference**: US-11, Supabase Auth

```
+------------------------------------------+
|                                          |
|           [Pilot Space Logo]             |
|                                          |
|         Welcome to Pilot Space           |
|     AI-augmented project management      |
|                                          |
|  +------------------------------------+  |
|  | Email                              |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Password                           |  |
|  +------------------------------------+  |
|                                          |
|  [        Sign In with Email         ]   |
|                                          |
|  ---- or continue with ----             |
|                                          |
|  [G  Google]  [GH  GitHub]               |
|                                          |
|  Don't have an account? Sign up          |
|                                          |
+------------------------------------------+
```

| Property | Value |
|----------|-------|
| Container | Max width 400px, centered vertically and horizontally |
| Background | Warm off-white with subtle noise texture |
| Logo | 48px, centered |
| OAuth Buttons | Full width, secondary variant, provider icon + name |
| Form Validation | Inline field errors, Zod schema |
| Loading State | Button spinner, fields disabled |
| Error State | Alert banner above form with error message |

#### Callback Page (`/callback`)

**Route**: `(auth)/callback/page.tsx`

- Full-screen loading spinner with "Completing sign in..." text
- Handles OAuth redirect from Supabase
- On success: redirect to workspace home
- On error: redirect to login with error query param

### 7.2 Workspace Pages

#### Workspace Home (`/[workspaceSlug]`)

**Route**: `(workspace)/[workspaceSlug]/page.tsx`
**Layout**: AppShell (sidebar + header)

Redirects to Notes List (Note Canvas is the default home per DD-013).

#### Notes List Page (`/[workspaceSlug]/notes`)

**Route**: `(workspace)/[workspaceSlug]/notes/page.tsx`
**Reference**: US-01
**Layout**: AppShell

```
+------------------------------------------------------------+
|  SIDEBAR  |  Notes                 [Grid|List] [+ New Note] |
|           |----------------------------------------------- |
|           |  [Search notes...]   Sort: [Last edited v]     |
|           |  Filter: [All v]                               |
|           |                                                |
|           |  PINNED                                        |
|           |  +----------+  +----------+  +----------+      |
|           |  | Auth     |  | API      |  | Sprint   |      |
|           |  | Refactor |  | Design   |  | Goals    |      |
|           |  | 2h ago   |  | 1d ago   |  | 3d ago   |      |
|           |  | Pin icon |  | Pin icon |  | Pin icon |      |
|           |  +----------+  +----------+  +----------+      |
|           |                                                |
|           |  RECENT                                        |
|           |  +----------+  +----------+  +----------+      |
|           |  | Bug      |  | Feature  |  | Meeting  |      |
|           |  | Triage   |  | Spec     |  | Notes    |      |
|           |  +----------+  +----------+  +----------+      |
|           |  +----------+  +----------+  +----------+      |
|           |  | ...      |  | ...      |  | ...      |      |
|           |  +----------+  +----------+  +----------+      |
|           |                                                |
|           |         [Load more...]                         |
+------------------------------------------------------------+
```

| Feature | Specification |
|---------|---------------|
| View Toggle | Grid (3-column cards) / List (rows) |
| Search | Debounced 300ms, searches title + content via Meilisearch |
| Sort Options | Last edited (default), Created, Title (A-Z), Title (Z-A) |
| Filters | All, My Notes, Shared, AI-enhanced |
| Infinite Scroll | 20 notes per page, intersection observer trigger |
| Pin Indicators | Pin icon top-right of card, pinned section above recent |
| Card Content | Title, first 2 lines preview, last edited timestamp, word count, topic tags |
| Create Button | Opens new note editor directly |
| Keyboard | Enter on card opens editor, N creates new note |

#### Note Editor Page (`/[workspaceSlug]/notes/[noteId]`)

**Route**: `(workspace)/[workspaceSlug]/notes/[noteId]/page.tsx` (inferred from architecture)
**Reference**: US-01 (primary), DD-013
**Layout**: AppShell with no content max-width (full bleed)

This is the most important page in Pilot Space. See Section 9 for full Note Canvas specification.

```
+--------------------------------------------------------------------+
| SIDEBAR | Rich Note Header                                         |
|         |  Auth Refactor | Created Jan 20 | 1,234 words | 5 min   |
|         |----------------------------------------------------------|
|         |                                                          |
|  Outline|  DOCUMENT CANVAS (65%)          | CHAT VIEW (35%)        |
|  Tree   |                                 |                        |
|         |  # Authentication Refactor      | PilotSpace AI    [...]|
|         |                                 | ----------------------|
|         |  We need to rethink how         | [Messages scroll]     |
|         |  users log in. Current          |                       |
|         |  flow has too many steps.       | User: Help me improve |
|         |                                 | this section           |
|         |  [PS-201 Simplify reset]        |                       |
|         |                                 | AI: I can restructure |
|         |  ## Key Problems                | this into 3 subsections|
|         |  - Password reset confusing     | with decision criteria.|
|         |  - Social login fails silently  |                       |
|         |  - Session expires quickly      | [Tasks panel]          |
|         |                                 |                       |
|         |                                 | [Context: Auth Note]  |
|         |                                 | [Type message...]     |
|         |                                 |                       |
+---------+---------------------------------+-----------------------+
```

**Two-Column Layout**:

| Column | Width | Content |
|--------|-------|---------|
| Document Canvas | 65% (min 480px) | TipTap editor with all extensions, margin annotations |
| ChatView | 35% (min 320px) | Full ChatView component (see Section 8) |
| Resizable | Drag handle between columns | 4px invisible zone, `col-resize` cursor |

**Responsive Behavior** (see Section 15 for full matrix):

| Breakpoint | Behavior |
|------------|----------|
| Ultra-wide (>1920px) | Wider canvas (max 800px), ChatView fills remaining |
| Desktop (1280-1920px) | Standard 65/35 split |
| Tablet (768-1279px) | ChatView as collapsible overlay sidebar (slides from right) |
| Mobile (<768px) | ChatView as full-screen modal overlay (button to toggle) |

**Auto-Save**: 2-second debounce, status indicator top-right (Saved / Saving... / Error).

**Version History**: Side panel (280px) toggled from header menu. Shows snapshots with timestamps and AI reasoning.

#### Issues List Page (`/[workspaceSlug]/issues`)

**Route**: `(workspace)/[workspaceSlug]/issues/page.tsx`
**Reference**: US-02

```
+------------------------------------------------------------+
|  SIDEBAR  |  Issues              [Board|List|Table] [+ New] |
|           |----------------------------------------------- |
|           |  [Search issues...]                            |
|           |  State: [All v]  Priority: [All v]  Assignee:  |
|           |                                                |
|  BOARD VIEW:                                               |
|  +--------+  +--------+  +----------+  +---------+        |
|  |Backlog |  |Todo    |  |In Progres|  |In Review|  ...   |
|  |   (5)  |  |  (3)   |  |   (4)    |  |  (2)   |        |
|  |--------|  |--------|  |----------|  |---------|        |
|  |[Card]  |  |[Card]  |  |[Card]    |  |[Card]  |        |
|  |[Card]  |  |[Card]  |  |[Card]    |  |[Card]  |        |
|  |[Card]  |  |[Card]  |  |[Card]    |  |        |        |
|  |[Card]  |  |        |  |[Card]    |  |        |        |
|  |[Card]  |  |        |  |          |  |        |        |
|  +--------+  +--------+  +----------+  +---------+        |
+------------------------------------------------------------+
```

**Three View Modes**:

| View | Description |
|------|-------------|
| **Board** (default) | 6-column Kanban. Drag-and-drop between columns. Column headers with count. Scrollable columns. |
| **List** | Flat list sorted by sort selection. Each row: state icon, identifier, title, priority, assignee, labels, updated. |
| **Table** | Full data table with sortable columns, resizable, row selection for bulk actions. |

| Feature | Specification |
|---------|---------------|
| Filters | State (multi-select), Priority (multi-select), Assignee (multi-select), Label (multi-select), Cycle |
| Sort | Priority (default), Created, Updated, Title |
| Search | Debounced 300ms, title + description |
| Create | Opens IssueModal |
| Bulk Actions | Select multiple in Table view: change state, assign, add label, delete |
| Keyboard | C creates issue, J/K navigate list, Enter opens detail |

#### Issue Detail Page (`/[workspaceSlug]/issues/[issueId]`)

**Route**: `(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`
**Reference**: US-02, US-12

```
+------------------------------------------------------------+
| SIDEBAR |  < Back to Issues    PS-123                       |
|         |  -------------------------------------------------|
|         |                                                   |
|         |  MAIN CONTENT (70%)         | SIDEBAR (30%)       |
|         |                             |                     |
|         |  Implement user auth flow   | State: [Todo v]     |
|         |  ========================   | Priority: [High v]  |
|         |                             | Assignee: [Select]  |
|         |  [TipTap Description        | Labels: [bug] [ux]  |
|         |   Editor]                   | Cycle: Sprint 12    |
|         |                             | Estimate: 5 pts     |
|         |                             | Created: Jan 20     |
|         |  ----- AI Context -----     | Due: Feb 15         |
|         |  [Related Docs]             |                     |
|         |  [Related Code]             | -- Linked PRs --    |
|         |  [Task Breakdown]           | #234 (Open)         |
|         |  [Claude Code Prompts]      | #189 (Merged)       |
|         |                             |                     |
|         |  ----- Activity -----       | -- Source Notes --   |
|         |  [Timeline of changes,      | Auth Refactor        |
|         |   comments, state changes]  |                     |
|         |                             | [Generate Context]  |
+------------------------------------------------------------+
```

| Section | Description |
|---------|-------------|
| **Title** | Editable inline, text-2xl, auto-save on blur |
| **Description** | TipTap mini-editor, supports markdown, images, code blocks |
| **AI Context** | Collapsible section (US-12). Tabs: Related Docs, Related Code, Task Breakdown, Claude Code Prompts. "Generate Context" button triggers AIContextAgent. |
| **Activity Timeline** | Chronological feed: state changes, comments, AI actions, PR links, commits. Each with avatar, timestamp, action description. |
| **Right Sidebar** | Property panel with dropdowns/selectors for all issue fields. Always visible on desktop, collapses on mobile. |

#### Projects Page (`/[workspaceSlug]/projects`)

**Route**: `(workspace)/[workspaceSlug]/projects/page.tsx`
**Reference**: US-04, US-05

```
+------------------------------------------------------------+
| SIDEBAR |  Projects                           [+ New Project]|
|         |---------------------------------------------------  |
|         |                                                    |
|         |  +----------------+  +----------------+            |
|         |  | Alpha Project  |  | Beta Project   |            |
|         |  |                |  |                |            |
|         |  | 12 issues      |  | 8 issues       |            |
|         |  | [====----] 65% |  | [==------] 25% |            |
|         |  |                |  |                |            |
|         |  | Active Cycle:  |  | Active Cycle:  |            |
|         |  | Sprint 12      |  | Sprint 3       |            |
|         |  | 3d remaining   |  | 8d remaining   |            |
|         |  +----------------+  +----------------+            |
|         |                                                    |
|         |  +----------------+                                |
|         |  | Gamma Project  |                                |
|         |  | ...            |                                |
|         |  +----------------+                                |
+------------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Layout | 3-column responsive grid (2 on tablet, 1 on mobile) |
| Card Content | Project name, issue count, progress bar (done/total), active cycle info, last activity |
| Progress Bar | Segmented by state: green (done), amber (in progress), gray (remaining) |
| Click Action | Navigate to project detail with issues board |

#### Cycles List Page (`/[workspaceSlug]/projects/[projectId]/cycles`)

**Route**: `(workspace)/[workspaceSlug]/projects/[projectId]/cycles/page.tsx`
**Reference**: US-04

```
+------------------------------------------------------------+
| SIDEBAR |  Alpha > Cycles                     [+ New Cycle]  |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  ACTIVE CYCLE                                      |
|         |  +----------------------------------------------+  |
|         |  | Sprint 12          Jan 20 - Feb 3             |  |
|         |  | [============--------] 65% complete            |  |
|         |  | 8/12 issues done  |  Velocity: 24 pts         |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  UPCOMING                                          |
|         |  +----------------------------------------------+  |
|         |  | Sprint 13          Feb 3 - Feb 17             |  |
|         |  | 0 issues planned                               |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  COMPLETED                                         |
|         |  Sprint 11, Sprint 10, Sprint 9 ...               |
+------------------------------------------------------------+
```

| Feature | Specification |
|---------|---------------|
| Sections | Active (1 max), Upcoming, Completed (collapsed) |
| Active Card | Large card with progress bar, issue count, velocity, burndown mini chart |
| Create | Modal with name, date range, issue assignment |
| Click | Navigate to cycle detail page |

#### Cycle Detail Page (`/[workspaceSlug]/projects/[projectId]/cycles/[cycleId]`)

**Route**: `(workspace)/[workspaceSlug]/projects/[projectId]/cycles/[cycleId]/page.tsx`
**Reference**: US-04

```
+------------------------------------------------------------+
| SIDEBAR |  Alpha > Sprint 12    Jan 20 - Feb 3   [Complete] |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  +---BURNDOWN CHART---+  +--VELOCITY CHART---+    |
|         |  |    \               |  |  [|] [|] [|] [|]  |    |
|         |  |     \  .           |  |                    |    |
|         |  |      \ . .         |  |  Avg: 22 pts       |    |
|         |  |       \.   .       |  |                    |    |
|         |  +--------------------+  +--------------------+    |
|         |                                                    |
|         |  ISSUES IN CYCLE                                   |
|         |  [Board view of issues filtered to this cycle]     |
|         |                                                    |
+------------------------------------------------------------+
```

| Chart | Specification |
|-------|---------------|
| **Burndown** | Recharts AreaChart. Ideal line (dashed gray), actual line (solid primary). X: cycle days. Y: remaining points. Tooltip: date + points. |
| **Velocity** | Recharts BarChart. Last 6 cycles. Average line (dashed). Tooltip: cycle name + completed/planned. |

#### AI Chat Page (`/[workspaceSlug]/chat`)

**Route**: Inferred from sidebar navigation
**Reference**: DD-003, pilotspace-agent-architecture

Full-page ChatView without document canvas context. Used for workspace-wide AI interactions.

```
+------------------------------------------------------------+
| SIDEBAR |  PilotSpace AI                    [New] [Sessions] |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  [Full-height MessageList]                         |
|         |                                                    |
|         |  User: What are the open bugs in Sprint 12?        |
|         |                                                    |
|         |  AI: I found 3 open bugs in Sprint 12:             |
|         |  - PS-201: Password reset issue (High)             |
|         |  - PS-205: OAuth error handling (Medium)            |
|         |  - PS-210: Session timeout (Low)                    |
|         |                                                    |
|         |  [Task Panel - collapsed when no active tasks]     |
|         |                                                    |
|         |  [Context: Workspace] [Type message... ]  [Send]   |
+------------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Layout | Full height within AppShell, no max-width |
| Session List | Dropdown in header, shows recent 5 sessions |
| New Session | Clears conversation, starts fresh |
| Input | Fixed at bottom, full width |
| TaskPanel | Auto-opens when tasks exist, collapsible |

#### Approval Queue Page (`/[workspaceSlug]/approvals`)

**Route**: `features/approvals/pages/approval-queue-page.tsx`
**Reference**: DD-003

```
+------------------------------------------------------------+
| SIDEBAR |  Approvals                                         |
|         |-------------------------------------------------- |
|         |  [Pending] [Approved] [Rejected] [Expired] [All]   |
|         |                                                    |
|         |  +----------------------------------------------+  |
|         |  | CREATE ISSUE                    expires 4:32  |  |
|         |  | Create 3 issues from "Auth Refactor" note     |  |
|         |  |                                              |  |
|         |  | Affected: PS-201, PS-202, PS-203             |  |
|         |  |                                              |  |
|         |  | [View Details]  [Approve]  [Reject]          |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  +----------------------------------------------+  |
|         |  | UPDATE NOTE BLOCK               expires 2:15 |  |
|         |  | Enhance paragraph in "API Design" note        |  |
|         |  |                                              |  |
|         |  | [View Details]  [Approve]  [Reject]          |  |
|         |  +----------------------------------------------+  |
+------------------------------------------------------------+
```

| Feature | Specification |
|---------|---------------|
| Tabs | Pending (default, with count badge), Approved, Rejected, Expired, All |
| Card Content | Action type icon, description, affected entities, countdown timer, quick actions |
| Detail Modal | Full approval details with content diff, consequences, approve with modifications, reject with reason |
| Countdown | CircularTimer component, color transitions green->amber->red |
| Auto-Refresh | Poll every 10s for new approvals |
| Empty State | Green checkmark, "No pending approvals" |

#### AI Costs Page (`/[workspaceSlug]/costs`)

**Route**: `features/costs/pages/cost-dashboard-page.tsx`
**Reference**: DD-002

```
+------------------------------------------------------------+
| SIDEBAR |  AI Costs                     [7d] [30d] [Custom] |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  +--------+  +--------+  +--------+  +--------+   |
|         |  | Total  |  | Tokens |  |Requests|  | Avg/Req|   |
|         |  | $12.45 |  | 2.1M   |  | 847    |  | $0.015 |   |
|         |  | +5.2%  |  | +8.1%  |  | -2.3%  |  | +7.6%  |   |
|         |  +--------+  +--------+  +--------+  +--------+   |
|         |                                                    |
|         |  +-- COST BY AGENT -----+  +-- COST TRENDS -----+ |
|         |  | GhostText    [====]  |  |  /\    /\           | |
|         |  | IssueExtract [===]   |  | /  \  /  \  /       | |
|         |  | PRReview     [==]    |  |/    \/    \/        | |
|         |  | AIContext     [=]    |  |                     | |
|         |  +----------------------+  +---------------------+ |
|         |                                                    |
|         |  +-- DETAILED TABLE --------------------------------+
|         |  | Date | Agent | Provider | Tokens | Cost         |
|         |  |------|-------|----------|--------|------|        |
+------------------------------------------------------------+
```

| Feature | Specification |
|---------|---------------|
| Summary Cards | 4 cards: Total Cost, Total Tokens, Request Count, Average Cost/Request. Each with trend arrow and % change vs previous period. |
| Date Range | Preset buttons (7d, 30d, 90d) + custom date picker. Affects all charts and table. |
| Cost by Agent | Horizontal bar chart, one bar per agent type. Color-coded. |
| Cost Trends | Line chart, daily cost over time. Stacked by provider if multiple. |
| Table | Sortable data table with all usage records. Paginated (25 per page). Export CSV button. |
| User Breakdown | Filter by workspace member (admin only). |

#### Settings Hub (`/[workspaceSlug]/settings`)

**Route**: `(workspace)/[workspaceSlug]/settings/page.tsx`
**Reference**: US-11

```
+------------------------------------------------------------+
| SIDEBAR |  Settings                                          |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  General                                           |
|         |  +----------------------------------------------+  |
|         |  | Workspace Name: [Pilot Space     ]            |  |
|         |  | Workspace Slug: pilot-space                    |  |
|         |  | Description:    [AI-augmented SDLC]            |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  Members                                           |
|         |  AI Providers     >                                |
|         |  Integrations     >                                |
|         |  Billing          >                                |
+------------------------------------------------------------+
```

| Section | Route | Description |
|---------|-------|-------------|
| General | `/settings` | Workspace name, slug, description, timezone |
| Members | `/settings/members` | Member list, invite, role management |
| AI Providers | `/settings/ai` | BYOK API key management (see below) |
| Integrations | `/settings/integrations` | GitHub App, Slack (see below) |
| Billing | `/settings/billing` | Usage summary, plan management |

#### AI Providers Page (`/[workspaceSlug]/settings/ai`)

**Route**: `features/settings/pages/ai-settings-page.tsx`
**Reference**: US-11, DD-002

```
+------------------------------------------------------------+
| SIDEBAR |  Settings > AI Providers                           |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  API Keys                                          |
|         |  +----------------------------------------------+  |
|         |  | Anthropic (Required)                          |  |
|         |  | [sk-ant-***...***] [Test] [Connected]         |  |
|         |  +----------------------------------------------+  |
|         |  | OpenAI (Required for search)                  |  |
|         |  | [sk-***...***]     [Test] [Connected]         |  |
|         |  +----------------------------------------------+  |
|         |  | Google AI (Optional)                          |  |
|         |  | [Not configured]   [Add Key]                  |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  Feature Toggles                                   |
|         |  [x] Ghost Text Autocomplete                      |
|         |  [x] Margin Annotations                           |
|         |  [x] Issue Enhancement                            |
|         |  [x] Duplicate Detection                          |
|         |  [x] PR Review                                    |
+------------------------------------------------------------+
```

#### Integrations Page (`/[workspaceSlug]/settings/integrations`)

**Route**: `(workspace)/[workspaceSlug]/settings/integrations/page.tsx`
**Reference**: US-03, US-18

```
+------------------------------------------------------------+
| SIDEBAR |  Settings > Integrations                           |
|         |-------------------------------------------------- |
|         |                                                    |
|         |  GitHub                                            |
|         |  +----------------------------------------------+  |
|         |  | Status: Connected                             |  |
|         |  | Installation: pilot-space-org                 |  |
|         |  |                                              |  |
|         |  | Repositories:                                |  |
|         |  | [x] pilot-space/frontend                     |  |
|         |  | [x] pilot-space/backend                      |  |
|         |  | [ ] pilot-space/infrastructure               |  |
|         |  |                                              |  |
|         |  | Webhook: Active (last ping 2m ago)           |  |
|         |  | [Reconfigure]  [Disconnect]                  |  |
|         |  +----------------------------------------------+  |
|         |                                                    |
|         |  Slack (Coming Soon)                               |
|         |  +----------------------------------------------+  |
|         |  | [Install Slack App]                           |  |
|         |  +----------------------------------------------+  |
+------------------------------------------------------------+
```

---

## 8. ChatView System

The ChatView is the most complex UI subsystem in Pilot Space. It provides the conversational AI interface used in two contexts:
1. **Embedded in Note Editor** (35% width sidebar)
2. **Full-page AI Chat** (standalone page)

**Reference**: `features/ai/ChatView/`, pilotspace-agent-architecture v1.5.0, DD-003

### 8.1 Architecture

```
ChatView (coordinator)
  |
  +-- ChatHeader (title, session selector, streaming indicator)
  |
  +-- MessageList (scrollable message container)
  |     +-- MessageGroup (groups consecutive same-role messages)
  |     |     +-- UserMessage (user bubble with avatar)
  |     |     +-- AssistantMessage (AI bubble with pilot avatar)
  |     |           +-- StreamingContent (animated text during stream)
  |     |           +-- ToolCallList (expandable tool call details)
  |     +-- [auto-scroll to bottom on new messages]
  |
  +-- TaskPanel (collapsible active/completed tasks)
  |     +-- TaskItem (status badge, progress bar, step label)
  |     +-- TaskSummary (aggregate counts)
  |
  +-- ChatInput (message composition)
  |     +-- ContextIndicator (note/issue/project badges with block count)
  |     +-- SkillMenu (/ triggered, lists available skills)
  |     +-- AgentMenu (@ triggered, lists available agents)
  |
  +-- ApprovalOverlay (modal blocking chat during approval)
        +-- ApprovalDialog (action details, consequences, approve/reject)
              +-- IssuePreview (previews issues to be created)
              +-- ContentDiff (shows before/after for text changes)
              +-- GenericJSON (renders arbitrary JSON payloads)
```

### 8.2 ChatView Component (`ChatView.tsx`)

**Props**:

| Prop | Type | Description |
|------|------|-------------|
| `store` | `PilotSpaceStore` | MobX store managing all chat state |
| `userName` | `string?` | Display name for user messages |
| `userAvatar` | `string?` | Avatar URL for user messages |
| `autoFocus` | `boolean?` | Focus input on mount |
| `className` | `string?` | Additional CSS classes |

**Container Layout**:
- `flex flex-col h-full` -- fills available height
- Background: `--background`
- Error boundary wraps entire component

### 8.3 MessageList (`MessageList/MessageList.tsx`)

| Property | Value |
|----------|-------|
| Container | `flex-1 overflow-y-auto` |
| Scroll Behavior | Auto-scroll to bottom on new messages (unless user scrolled up) |
| Message Spacing | 16px between message groups |
| Padding | 16px horizontal, 24px vertical |

**Message Types**:

| Type | Visual Treatment |
|------|-----------------|
| **UserMessage** | Right-aligned bubble, `--background-subtle` background, user avatar (32px), username label |
| **AssistantMessage** | Left-aligned bubble, white/dark background, pilot star avatar (32px), "PilotSpace AI" label |
| **StreamingContent** | Animated text with blinking cursor. Renders markdown incrementally. |
| **ToolCallList** | Collapsible section below assistant message. Each tool call: name badge, arguments (collapsed JSON), result (collapsed JSON). Expandable via chevron. |

**MessageGroup**: Groups consecutive messages from the same role. Shows avatar once per group.

### 8.4 ChatInput (`ChatInput/ChatInput.tsx`)

```
+-----------------------------------------------------+
| [Note: Auth Refactor] [3 blocks]  [x]               |
|-----------------------------------------------------|
| Type a message...                            [Send]  |
|                                              [Stop]  |
+-----------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Container | Fixed at bottom, border-top, padding 12px |
| Input | Auto-expanding textarea, max 6 rows, min 1 row |
| Send Button | Primary variant when text present, disabled when streaming |
| Stop Button | Replaces Send during streaming, calls `store.abort()` |
| Disabled State | Grayed out when approval pending (`store.hasUnresolvedApprovals`) |
| Keyboard | Enter sends (unless Shift+Enter for newline), Escape clears input |

**ContextIndicator** (`ChatInput/ContextIndicator.tsx`):
- Shows active context as removable badges above input
- Note context: Note title + block count (e.g., "Auth Refactor | 3 blocks")
- Issue context: Issue identifier (e.g., "PS-123")
- Project context: Project name
- Each badge has X button to clear that context
- Tooltip on hover shows full context details

**SkillMenu** (`ChatInput/SkillMenu.tsx`):
- Triggered by typing `/` at start of message
- Dropdown list of available skills (extract-issues, enhance-issue, summarize, etc.)
- Arrow key navigation, Enter to select
- Selected skill prepends to message as `/skill-name`
- Fuzzy search within menu

**AgentMenu** (`ChatInput/AgentMenu.tsx`):
- Triggered by typing `@` in message
- Lists available AI agents (pilot, ghost-text, issue-enhancer, etc.)
- Similar UX to SkillMenu
- Selected agent prepends `@agent-name`

### 8.5 TaskPanel (`TaskPanel/TaskPanel.tsx`)

```
+-----------------------------------------------------+
| v Tasks (2 active, 3 completed)                      |
|-----------------------------------------------------|
| [*] Extracting issues from note          [====--] 67%|
|     Step 2/3: Creating issues                        |
|                                                      |
| [*] Searching for duplicates             [===---] 50%|
|     Comparing against 42 issues                      |
|-----------------------------------------------------|
| Completed:                                           |
| [v] Summarized note content              2 min ago   |
| [v] Enhanced paragraph                   5 min ago   |
| [v] Linked 2 existing issues            8 min ago   |
+-----------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Container | Collapsible panel, default open when tasks exist |
| Toggle | Chevron + summary text ("2 active, 3 completed") |
| Active Tasks | Sorted by creation time (newest first) |
| Completed Tasks | Sorted by completion time (newest first), collapsible section |

**TaskItem** (`TaskPanel/TaskItem.tsx`):

| Element | Description |
|---------|-------------|
| Status Badge | Colored dot: pending (gray), in_progress (amber pulse), completed (green check), error (red x) |
| Subject | Task name (e.g., "Extracting issues from note") |
| Progress Bar | Horizontal bar with percentage, animated fill |
| Step Label | Current step text (e.g., "Step 2/3: Creating issues") |
| Estimated Time | "~30s remaining" when available |

**TaskSummary** (`TaskPanel/TaskSummary.tsx`):
- Aggregate counts: X active, Y completed
- Shown in panel header

### 8.6 ApprovalOverlay (`ApprovalOverlay/ApprovalOverlay.tsx`)

The approval overlay is a modal that blocks the entire ChatView when an AI action requires human approval (per DD-003).

| Property | Value |
|----------|-------|
| Trigger | `store.hasUnresolvedApprovals === true` |
| Overlay | Semi-transparent backdrop over ChatView |
| Position | Centered within ChatView bounds |
| Dismissable | No (must approve or reject) |
| Multiple Approvals | Shown one at a time, queue indicator |

**ApprovalDialog** (`ApprovalOverlay/ApprovalDialog.tsx`):

```
+-----------------------------------------------------+
|  APPROVAL REQUIRED                                    |
|-----------------------------------------------------|
|                                                      |
|  Action: Create 3 Issues                             |
|                                                      |
|  Description:                                        |
|  Extract and create 3 issues from "Auth Refactor"    |
|  note based on identified action items.              |
|                                                      |
|  Consequences:                                       |
|  - 3 new issues will be created in project Alpha     |
|  - Issues will be linked to source note blocks       |
|  - Team members will be notified                     |
|                                                      |
|  Affected Entities:                                  |
|  +-- IssuePreview: PS-201 Simplify reset --+         |
|  +-- IssuePreview: PS-202 OAuth errors   --+         |
|  +-- IssuePreview: PS-203 Session timeout --+        |
|                                                      |
|  Expires in: [03:45] (countdown timer)               |
|                                                      |
|  [Reject with reason...]     [Approve]               |
|                                                      |
+-----------------------------------------------------+
```

**Sub-renderers**:

| Component | When Used | Description |
|-----------|-----------|-------------|
| **IssuePreview** | Action creates issues | Shows title, priority, type, description preview of each issue to be created |
| **ContentDiff** | Action modifies text | Side-by-side or inline diff view of before/after content changes |
| **GenericJSON** | Other action types | Formatted JSON tree of the proposed action payload |

### 8.7 SessionList (`SessionList/SessionList.tsx`)

| Property | Value |
|----------|-------|
| Location | Dropdown from ChatHeader |
| Items | Recent 5 sessions |
| Item Content | Session title (auto-generated from first message), last updated timestamp |
| Actions | Click to resume, New Session button |
| Resume | Loads session messages from backend, restores context |

### 8.8 UI State Machine

```
            +-------+
            | IDLE  |<------------------------------------------+
            +---+---+                                           |
                |                                               |
        [user types /]  [user types @]  [user sends message]   |
                |              |                |               |
        +-------v-----+  +----v--------+  +----v----+         |
        |SKILL_MENU   |  |AGENT_MENU   |  | READY   |         |
        |OPEN         |  |OPEN         |  |         |         |
        +------+------+  +------+------+  +----+----+         |
               |                |               |               |
        [select/dismiss] [select/dismiss]  [SSE starts]        |
               |                |               |               |
               +-------+-------+          +----v----+          |
                       |                  |STREAMING |          |
                       v                  +----+----+          |
                    +--+--+                    |               |
                    |IDLE |              [approval event]       |
                    +-----+                    |               |
                                         +----v---------+     |
                                         |APPROVAL      |     |
                                         |PENDING       |     |
                                         +----+---------+     |
                                              |               |
                                     [approve/reject]         |
                                              |               |
                                              +---------------+
```

| State | Input Enabled | Send Enabled | Overlay Visible |
|-------|--------------|-------------|----------------|
| IDLE | Yes | Yes (if text) | No |
| SKILL_MENU_OPEN | Yes (filtered) | No | No |
| AGENT_MENU_OPEN | Yes (filtered) | No | No |
| STREAMING | No | No (Stop visible) | No |
| APPROVAL_PENDING | No | No | Yes |

---

## 9. Note Canvas (Editor)

The Note Canvas is the **primary entry point** for Pilot Space. Unlike traditional issue trackers that start with forms, Pilot Space starts with **collaborative thinking**.

### Philosophy

> **"Think first, structure later"** -- Users brainstorm with AI in a living document. Issues emerge naturally from refined thoughts, not forced forms.

### Layout Architecture

```
+--------------------------------------------------------------------+
| < >  Pilot Space                     Search    [+]  Bell  Avatar    |
+------+-------------------------------------------------------------+
|      |                                                              |
| OUT- |  DOCUMENT CANVAS                        MARGIN               |
| LINE |                                         (AI Notes)           |
|      |                                                              |
| Notes|  # Authentication Refactor                   +--------+     |
| |- Au|                                              | * AI   |     |
|   th |  +---------------------------------------+   |        |     |
| |- AP|  | We need to rethink how users log in.  |   | Consider|    |
| |- Sp|  | Current flow has too many steps...    |   | OAuth2  |     |
|   rin|  +---------------------------------------+   | PKCE    |     |
|      |                                              | flow... |     |
| Issu |                     |                        +--------+     |
| |- PS|                     | AI thread                              |
| |- PS|                     v                                        |
|      |  +-- You + AI ---------------------------+                   |
| Proj |  | What specific pain points are users   |                   |
|      |  | experiencing?                         |                   |
|      |  |                                       |                   |
|      |  | > Password reset is confusing         |                   |
|      |  | > Social login fails silently         |                   |
|      |  | > Session expires too quickly         |   +--------+     |
|      |  +---------------------------------------+   | * AI   |     |
|      |                                              |        |     |
|      |                                              | 3 issues|    |
|      |                                              | detected|     |
|      |                                              |         |     |
|      |                                              | [Review]|     |
|      |                                              +--------+     |
+------+-------------------------------------------------------------+
```

### Core Components

#### Outline Tree (Left Sidebar)

VS Code-inspired tree navigation for workspace content.

| Property | Value |
|----------|-------|
| Width | 220px |
| Background | `--background-subtle` |
| Border | 1px right |
| Font Size | 13px (`text-sm`) |
| Item Padding | 4px vertical, 8px horizontal |
| Item Hover | Muted background |
| Item Active | Primary 10% background, primary text |

**Content Types**: Notes (primary), Issues (linked), Projects, Cycles

#### Document Canvas (Center)

| Property | Value |
|----------|-------|
| Max Width | 720px |
| Margin | Auto-centered within 65% column |
| Padding | 32px |
| Background | Main background |

**Block Properties**:

| Property | Value |
|----------|-------|
| Padding | 16px |
| Margin Bottom | 12px |
| Border Radius | 14px (`rounded-lg`) |
| Hover | 50% muted background |
| Active | Muted background, small shadow |

#### Margin Annotations (Right Side)

| Property | Value |
|----------|-------|
| Width | 200px |
| Padding | 16px |
| Background | AI muted color |
| Border Left | 3px solid AI color |
| Default Opacity | 40% |
| Active/Hover Opacity | 100% |
| Font Size | 11px (`text-xs`) |

**Visibility Behavior**:
- Active block's margin notes are fully visible
- Other margin notes fade to 40% opacity
- Hover reveals full note
- Click expands to full AI discussion

#### Threaded AI Discussions

```
+-- You + AI -----------------------------------------------+
|                                                            |
|  * "What authentication method are you considering?        |
|     OAuth2 with PKCE is common for SPAs..."                |
|                                                            |
|  --------------------------------------------------------  |
|                                                            |
|  > We want Google and GitHub OAuth                         |
|  > Also magic link for enterprise users                    |
|                                                            |
|  --------------------------------------------------------  |
|                                                            |
|  * "Great choices. For enterprise, consider                |
|     SAML/OIDC in addition to magic links..."               |
|                                                            |
|  [Collapse thread]                              [v1.2]     |
|                                                            |
+------------------------------------------------------------+
```

**Thread Persistence**:
- Threads are saved as part of note history
- Collapsed by default after session
- Expandable to view full discussion
- Version indicator shows thread updates

### Rich Note Header

```
+------------------------------------------------------------+
|                                                             |
|  Auth Refactor                                   [=] [...] |
|  --------------------------------------------------------- |
|  Created Jan 20 | Last edited 2h ago by You                |
|  1,234 words | ~5 min read | Topics: authentication, security |
|                                                             |
+------------------------------------------------------------+
```

| Property | Value |
|----------|-------|
| Font Size | 11px (`text-xs`) |
| Color | `--foreground-muted` |
| Spacing | 4px between items |
| AI Reading Time | Based on 200 WPM adjusted for technical content |
| Topic Tags | AI-generated, max 3 displayed |

### Auto-Generated Table of Contents

| Property | Value |
|----------|-------|
| Position | Fixed right, below margin panel |
| Width | 200px |
| Current Section | Primary color dot, bold text |
| Other Sections | Muted dot, regular text |
| Click | Smooth scroll to heading |
| Auto-collapse | Collapses below 1024px |

### Issue Extraction Flow

AI identifies actionable items and wraps them with rainbow-bordered issue boxes.

#### Issue Box Specifications

| Property | Value |
|----------|-------|
| Display | Inline-flex |
| Padding | 4px vertical, 8px horizontal |
| Border Radius | 10px |
| Border | 2px rainbow gradient (primary -> blue -> purple -> pink -> primary) |
| Hover | Scale 2%, medium shadow |
| New Issue Animation | Rainbow pulse (hue-rotate 30deg over 2s) |

#### Bidirectional Sync

- Issue state changes -> Note displays updated badge
- Note edits -> Issue description sync (requires approval)
- Issue completion -> Rainbow border becomes state color (green for done)
- Issue deletion -> Text remains, box removed, marker left

---

## 10. AI Collaborative Features

### New Note AI Prompt Flow

```
+------------------------------------------------------------+
|                                                             |
|              *                                              |
|                                                             |
|       What would you like to work on?                       |
|                                                             |
|  +------------------------------------------------------+  |
|  | Describe your idea, problem, or topic...              |  |
|  +------------------------------------------------------+  |
|                                                             |
|  Based on your recent work:                                 |
|                                                             |
|  [Sprint Plan]  [Bug Analysis]  [Feature Spec]             |
|                                                             |
|                    [Start with blank note]                  |
|                                                             |
+------------------------------------------------------------+
```

### Ghost Text Autocomplete

```
The authentication flow needs to be|simplified to reduce user friction
                                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                    Ghost text (faded, italic)
```

| Property | Value |
|----------|-------|
| Color | `--foreground-muted` at 40% |
| Style | Italic |
| Animation | 150ms fade-in, slight left translation |
| Trigger Delay | ~500ms after typing pause |

**Interaction**:

| Key | Action |
|-----|--------|
| Tab | Accept entire suggestion |
| Right Arrow | Accept word by word |
| Any other key | Dismiss and continue typing |
| Escape | Dismiss suggestion |

### Selection Toolbar (Rich + AI)

```
                    +-----------------------------------------------+
                    | B  I  U  S  Link  |  * Improve | Simplify |   |
                    |                   |  Expand | Ask | Extract |  |
                    +-----------------------------------------------+
```

| Property | Value |
|----------|-------|
| Display | Flex, centered |
| Gap | 4px |
| Background | Main background |
| Border | 1px solid border |
| Border Radius | 10px |
| Shadow | Medium shadow |
| AI Button Style | AI muted background, AI color text |
| AI Button Hover | AI color background, white text |

### AI Confidence Tags

| Tag | Background | Border | Icon |
|-----|------------|--------|------|
| Recommended | Primary 10% | Primary 30% | Filled star |
| Default | Muted | Border | None |
| Current | AI blue 10% | AI blue 30% | None |
| Alternative | Transparent | Border dashed | None |

### Version History Panel

| Property | Value |
|----------|-------|
| Width | 280px |
| Background | `--background-subtle` |
| Border | 1px left |
| Item Padding | 12px |
| Current Item | 3px primary left border |
| AI Reasoning Block | AI muted background, small padding, `text-xs` |

### Similar Notes with AI Guidance

| Property | Value |
|----------|-------|
| Trigger | After new note save |
| Position | Sidebar panel or modal |
| AI Guidance | 1-2 line explanation per note |
| Actions | View, Link, Merge (if appropriate) |
| Similarity Threshold | Show notes > 60% similar |

---

## 11. Navigation & Search

### Command Palette (Cmd+P)

| Property | Value |
|----------|-------|
| Width | 560px |
| Max Height | 70vh |
| Background | 95% background, 20px blur |
| Border Radius | 18px |
| Shadow | Large shadow |
| Section Title | 0.7rem, uppercase, 0.05em letter-spacing |
| Item Padding | 8px vertical, 16px horizontal |
| Selected Item | Muted background, AI icon highlight |
| Shortcut Text | Mono font, 0.75rem |

**Sections**: AI Suggestions (context-aware), Navigation, Actions, Recent Commands

### Search Modal (Cmd+K)

| Property | Value |
|----------|-------|
| Width | 640px |
| Max Height | 80vh |
| Filters | All, Notes, Issues, Projects |
| Results | Fuzzy matching with highlighted terms |
| Preview | Tab key shows preview panel |
| Recent | Shown when no search query |

### Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| Cmd+P | Open command palette | Global |
| Cmd+K | Open search | Global |
| Cmd+N | Create new note | Global |
| C | Create new issue | Not in text input |
| G H | Go to Home | Not in text input |
| G I | Go to Issues | Not in text input |
| G C | Go to Cycles | Not in text input |
| G S | Go to Settings | Not in text input |
| ? | Show keyboard shortcut guide | Not in text input |
| / | Open slash command menu | In editor |
| @ | Open mention menu | In editor |
| Tab | Accept ghost text | Ghost text visible |
| Escape | Dismiss ghost text / Close modal | Context-dependent |
| J / K | Navigate list items (down/up) | In list views |
| Enter | Open selected item | In list/board views |
| Cmd+S | Manual save (note editor) | In editor |
| Cmd+Z | Undo | In editor |
| Cmd+Shift+Z | Redo | In editor |
| F6 | Cycle focus regions | Global |

---

## 12. Interaction Patterns

### Drag and Drop

**Issue Board Cards**:
- Cards lift with elevated shadow on pickup
- 4px indicator shows drop zone
- Smooth 200ms transitions
- Haptic feedback where supported
- Cancel with Escape key

**List Reordering**:
- Items compress slightly when dragging over
- Insert line appears between items
- Cancel with Escape key

### Hover States

| Element | Hover Behavior |
|---------|----------------|
| Cards | Translate up 2px, medium shadow |
| Buttons | Scale 2%, elevated shadow |
| Links | Underline opacity increases |
| Icons | Background appears |
| List Items | Background highlight |

### Focus States

All interactive elements receive visible focus indicators:
- 3px ring in primary color at 30% opacity
- No outline (replaced by box-shadow)
- Skip to main content link visible on focus

### Loading States

| Type | Behavior |
|------|----------|
| Page Load | Skeleton placeholders with shimmer |
| Button Action | Spinner icon replaces button icon, disabled state |
| AI Generation | Status text with animated ellipsis |
| Data Fetch | Inline spinner with "Loading..." text |
| Streaming | Blinking cursor at end of text |

### Progressive Tooltips

| Stage | Trigger | Content |
|-------|---------|---------|
| Stage 1 | Instant on hover | Brief label (1-3 words) |
| Stage 2 | After 1 second | Detailed help + keyboard shortcut |

### Pinned Notes Indicator

| Property | Value |
|----------|-------|
| Section Label | 10px uppercase, muted |
| Pinned Item | Subtle primary background |
| Pin Action | Right-click or menu |
| Max Pinned | 5 notes |

### AI-Prioritized Notification Center

| Priority | Background | Icon | Color |
|----------|------------|------|-------|
| Urgent | Red 10% | Warning | Red |
| Important | Amber 10% | Star | Amber |
| FYI | Muted | Chat | Gray |

| Property | Value |
|----------|-------|
| Max Preview | 3-5 notifications |
| Mark-as-Read Delay | 2-3 seconds viewing |
| Unread Indicator | Subtle background tint |
| Badge Style | Primary color, count text |
| Animation | Fade in new notifications |

---

## 13. Animation & Motion System

### Animation Inventory

| Animation | Properties | Duration | Easing | Usage |
|-----------|------------|----------|--------|-------|
| **Button Hover** | `transform: scale(1.02)` | 150ms | ease-out | All buttons |
| **Button Active** | `transform: scale(0.98)` | 100ms | ease-in | All buttons |
| **Card Hover** | `transform: translateY(-2px)` | 200ms | ease | Interactive cards |
| **Ghost Text Appear** | `opacity: 0->0.4`, `translateX: -4px->0` | 150ms | ease-out | Ghost text suggestions |
| **Ghost Text Dismiss** | `opacity: 0.4->0` | 100ms | ease-in | On keystroke or Escape |
| **Loading Shimmer** | `background-position: -200% -> 200%` | 1.5s infinite | linear | Skeleton loaders |
| **Rainbow Pulse** | `filter: hue-rotate(0deg -> 30deg)` | 2s infinite | ease-in-out | New inline issue boxes |
| **Toast Enter** | `translateY: 100% -> 0`, `opacity: 0 -> 1` | 200ms | ease-out | Sonner toast notifications |
| **Toast Exit** | `translateY: 0 -> 100%`, `opacity: 1 -> 0` | 150ms | ease-in | Toast dismissal |
| **Sidebar Collapse** | `width: 260px -> 60px` | 200ms | ease-in-out | Sidebar toggle |
| **Modal Enter** | `scale: 0.95 -> 1`, `opacity: 0 -> 1` | 200ms | ease-out | All modal dialogs |
| **Modal Exit** | `scale: 1 -> 0.95`, `opacity: 1 -> 0` | 150ms | ease-in | Modal close |
| **Dropdown Enter** | `scale: 0.95 -> 1`, `opacity: 0 -> 1`, `translateY: -4px -> 0` | 150ms | ease-out | Popover/dropdown menus |
| **Approval Countdown** | CircularTimer fill animation | Per second | linear | ApprovalOverlay timer |
| **Streaming Cursor** | `opacity: 0 -> 1` | 500ms infinite | step-end | Blinking cursor during AI stream |
| **Progress Bar Fill** | `width: X% -> Y%` | 300ms | ease-out | TaskPanel progress bars |
| **Focus Ring** | `box-shadow: 0 0 0 3px primary/30` | 150ms | ease | All focusable elements |
| **Notification Slide** | `translateX: 100% -> 0` | 200ms | ease-out | Notification center items |

### Reduced Motion

When `prefers-reduced-motion: reduce` is active:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

All animations become instant state changes. Shimmer stops. Rainbow pulse becomes static border. Streaming cursor becomes static caret. Hover transforms are removed. Focus ring appears instantly without transition.

Tailwind utilities: `motion-safe:` prefix for animations, `motion-reduce:` prefix for static alternatives.

---

## 14. State Management Architecture (UI Perspective)

### RootStore Hierarchy

```
RootStore
  |
  +-- auth: AuthStore
  |     Session, user profile, Supabase auth state
  |
  +-- ui: UIStore
  |     Sidebar collapsed, theme, active modal, command palette
  |
  +-- workspace: WorkspaceStore
  |     Current workspace, members, settings
  |
  +-- notifications: NotificationStore
  |     Notification list, unread count, priority scoring
  |
  +-- notes: NoteStore
  |     Note list, active note, pinned notes, search/filter state
  |
  +-- issues: IssueStore
  |     Issue list, board view state, filters, selected issue
  |
  +-- cycles: CycleStore
  |     Cycle list, active cycle, burndown/velocity data
  |
  +-- ai: AIStore (root of 11 sub-stores)
        |
        +-- ghostText: GhostTextStore
        |     Current suggestion, abort controller, loading state
        |
        +-- aiContext: AIContextStore
        |     Generated context per issue, loading/error states
        |
        +-- approval: ApprovalStore
        |     Pending approvals list, approve/reject actions
        |
        +-- settings: AISettingsStore
        |     Provider configs, feature toggles, key validation
        |
        +-- prReview: PRReviewStore
        |     Review status, comments, summary, streaming
        |
        +-- issueExtraction: IssueExtractionStore
        |     Extracted issues, approval state, batch creation
        |
        +-- conversation: ConversationStore
        |     Legacy conversation state (pre-PilotSpaceStore)
        |
        +-- cost: CostStore
        |     Usage data, charts, date range, agent breakdown
        |
        +-- marginAnnotation: MarginAnnotationStore
        |     Annotation list per note, loading state, auto-trigger
        |
        +-- pilotSpace: PilotSpaceStore (primary chat store)
        |     Messages, streaming state, context, tasks,
        |     pending approvals, session management
        |
        +-- sessionList: SessionListStore
              Session history, resume capability
```

### PilotSpaceStore (Primary Chat State)

The PilotSpaceStore is the most complex store, managing all conversational AI state:

| Property | Type | Description |
|----------|------|-------------|
| `messages` | `ChatMessage[]` | Full message history for current session |
| `streamContent` | `string` | Accumulated streaming text during AI response |
| `isStreaming` | `boolean` | Whether SSE stream is active |
| `error` | `string \| null` | Current error message |
| `sessionId` | `string \| null` | Active session identifier |
| `tasks` | `Map<string, TaskState>` | Active and completed tasks |
| `pendingApprovals` | `ApprovalRequest[]` | Actions awaiting approval |
| `noteContext` | `NoteContext \| null` | Current note context (id, title, blocks) |
| `issueContext` | `IssueContext \| null` | Current issue context |
| `projectContext` | `ProjectContext \| null` | Current project context |

**Computed Properties**:

| Property | Derivation |
|----------|-----------|
| `hasUnresolvedApprovals` | `pendingApprovals.length > 0` |
| `activeTasks` | Tasks with status pending or in_progress |
| `messageCount` | `messages.length` |

### Data Flow Patterns

**Optimistic Updates** (Issues, Notes):
1. User action triggers MobX store update (immediate UI feedback)
2. TanStack Query mutation fires API request
3. On success: invalidate query cache, clear MobX pending state
4. On error: rollback MobX state, show toast error

**Auto-Save** (Note Editor):
1. Editor `onUpdate` fires on every change
2. 2-second debounce timer resets
3. After 2s quiet: trigger save mutation
4. Save indicator cycles: Saved -> Saving... -> Saved / Error

**SSE Event Handling** (ChatView):
1. `store.sendMessage()` opens EventSource to backend
2. Events arrive: `message_start`, `text_delta`, `tool_use`, `tool_result`, `task_progress`, `approval_request`, `content_update`, `message_stop`, `error`
3. Each event type has dedicated handler in PilotSpaceStore
4. `text_delta`: Appends to `streamContent`, triggers MessageList re-render
5. `task_progress`: Updates task in `tasks` Map
6. `approval_request`: Adds to `pendingApprovals`, shows ApprovalOverlay
7. `content_update`: Dispatched to NoteStore for editor updates
8. `message_stop`: Finalizes message, clears streaming state

**Server State (TanStack Query)**: Issues, notes, projects, cycles, members, settings. Source of truth for all server data. MobX stores only hold UI state (filters, selection, modals) and transient AI state.

---

## 15. Responsive Design Matrix

### Breakpoints

| Name | Value | Typical Device |
|------|-------|----------------|
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet portrait |
| `lg` | 1024px | Tablet landscape |
| `xl` | 1280px | Desktop |
| `2xl` | 1536px | Large desktop |
| `3xl` | 1920px | Ultra-wide |

### Per-Page Responsive Behavior

#### Note Editor

| Breakpoint | Layout | ChatView | Margin Annotations |
|------------|--------|----------|-------------------|
| 3xl (>1920px) | Canvas 800px max + ChatView fills rest | Side-by-side, wider | Full margin panel |
| xl-2xl (1280-1920px) | 65/35 split | Side-by-side, standard | Full margin panel |
| lg (1024-1279px) | Full-width canvas | Collapsible overlay (slides from right, 400px) | Collapsed to icons, expand on click |
| md (768-1023px) | Full-width canvas | Overlay sidebar (70% width) | Hidden, accessible via button |
| sm (<768px) | Full-width canvas, reduced padding | Full-screen modal overlay | Hidden completely |

ChatView toggle button: Fixed bottom-right FAB with AI star icon, shows unread count badge.

#### Issue Board

| Breakpoint | Layout |
|------------|--------|
| xl+ (>1280px) | All 6 columns visible, scrollable if needed |
| lg (1024-1279px) | 4 columns visible, horizontal scroll for rest |
| md (768-1023px) | 3 columns visible, horizontal scroll |
| sm (<768px) | Single column, accordion for each state. Tap to expand. |

#### Issue Detail

| Breakpoint | Layout |
|------------|--------|
| xl+ (>1280px) | Main content (70%) + right sidebar (30%) |
| lg (1024-1279px) | Main content (65%) + right sidebar (35%) |
| md (768-1023px) | Single column, properties above content |
| sm (<768px) | Single column, properties in collapsible section |

#### Notes List

| Breakpoint | Layout |
|------------|--------|
| xl+ (>1280px) | 4-column grid |
| lg (1024-1279px) | 3-column grid |
| md (768-1023px) | 2-column grid |
| sm (<768px) | Single column list |

#### Projects Page

| Breakpoint | Layout |
|------------|--------|
| lg+ (>1024px) | 3-column grid |
| md (768-1023px) | 2-column grid |
| sm (<768px) | Single column |

#### AI Chat (Full Page)

| Breakpoint | Layout |
|------------|--------|
| All | Full height within AppShell. Input fixed at bottom. MessageList scrollable. TaskPanel above input when open. |
| sm (<768px) | Sidebar hidden, full-width chat. Header simplified. |

#### Approval Queue

| Breakpoint | Layout |
|------------|--------|
| lg+ (>1024px) | Cards in 2-column grid |
| md (768-1023px) | Single column cards |
| sm (<768px) | Simplified cards, detail modal fullscreen |

#### Costs Dashboard

| Breakpoint | Layout |
|------------|--------|
| xl+ (>1280px) | Summary cards row + 2-column charts + table |
| lg (1024-1279px) | Summary cards row + stacked charts + table |
| md (768-1023px) | Summary cards 2x2 grid + stacked charts |
| sm (<768px) | Summary cards stacked + single chart + simplified table |

### Mobile-Specific Adaptations

| Element | Adaptation |
|---------|------------|
| Sidebar | Hidden, accessible via hamburger menu (Sheet component slides from left) |
| Command Palette | Full-screen modal |
| Modals | Full-screen on mobile |
| Touch Targets | Minimum 44px |
| Swipe Gestures | Left swipe on issue card for quick actions (state change) |
| Pull to Refresh | Notes list, issues list |
| Bottom Navigation | (future consideration, not MVP) |

---

## 16. Dark Mode

### Token Mapping

| Token | Light | Dark |
|-------|-------|------|
| `--background` | `#FDFCFA` | `#1A1A1A` |
| `--background-subtle` | `#F7F5F2` | `#1F1F1F` |
| `--foreground` | `#171717` | `#EDEDED` |
| `--foreground-muted` | `#737373` | `#999999` |
| `--border` | `#E5E2DD` | `#2E2E2E` |
| `--border-subtle` | `#EBE8E4` | `#262626` |
| `--primary` | `#29A386` | `#34B896` (slightly brighter for contrast) |
| `--primary-muted` | `#29A38615` | `#34B89620` |
| `--ai` | `#6B8FAD` | `#7DA4C4` (slightly brighter) |
| `--ai-muted` | `#6B8FAD15` | `#7DA4C420` |
| `--destructive` | `#D9534F` | `#E06560` |
| `--card` | `#FFFFFF` | `#222222` |
| `--card-hover` | `#FAFAFA` | `#2A2A2A` |
| `--popover` | `#FFFFFF` | `#252525` |
| `--input` | `#FFFFFF` | `#1E1E1E` |
| `--skeleton` | `#F0EDEA` | `#2A2A2A` |

### Dark Mode Behavior

| Component | Dark Mode Treatment |
|-----------|-------------------|
| **Sidebar** | Darker background (`#161616`) for visual distinction from content area |
| **Cards** | `--card` background, slightly elevated from `--background` |
| **Modals** | Frosted glass with darker backdrop, higher blur |
| **Code Blocks** | Dark syntax theme (VS Code Dark+) |
| **Ghost Text** | 30% opacity (reduced from 40% for dark backgrounds) |
| **Shadows** | Reduced opacity, no warm tint (shadows are less visible on dark) |
| **Noise Texture** | Removed in dark mode (grain is distracting on dark surfaces) |
| **Charts** | Light grid lines on dark background, brighter data colors |
| **Issue State Colors** | Slightly saturated for visibility on dark backgrounds |
| **AI Elements** | AI blue maintains contrast ratio >= 4.5:1 on dark card backgrounds |

### Implementation

- CSS custom properties in `:root` (light) and `.dark` (dark) selectors
- Toggle via `class="dark"` on `<html>` element
- Respects `prefers-color-scheme` system preference
- Manual override stored in `UIStore.theme` and localStorage
- Transition: 200ms on `background-color` and `color` properties

---

## 17. Empty States

Every page and section has a designed empty state to guide users toward action.

### Notes List Empty

```
+------------------------------------------+
|                                          |
|           [Notebook illustration]        |
|                                          |
|        Start your first note             |
|                                          |
|  Pilot Space is a thinking-first tool.   |
|  Begin with a note and let ideas         |
|  evolve into issues naturally.           |
|                                          |
|  [+ Create your first note]             |
|                                          |
|  Or try: "Help me plan a sprint"        |
|         "Brainstorm API design"          |
|                                          |
+------------------------------------------+
```

### Issues List Empty

```
+------------------------------------------+
|                                          |
|          [Clipboard illustration]        |
|                                          |
|         No issues yet                    |
|                                          |
|  Issues emerge from your notes.          |
|  Start writing and AI will help          |
|  identify actionable items.              |
|                                          |
|  [+ Create an issue]                    |
|  [Go to Notes]                          |
|                                          |
+------------------------------------------+
```

### Cycles Empty

```
+------------------------------------------+
|                                          |
|          [Calendar illustration]         |
|                                          |
|      Create your first sprint            |
|                                          |
|  Organize your work into time-boxed      |
|  cycles for better planning and          |
|  velocity tracking.                      |
|                                          |
|  [+ Create a cycle]                     |
|                                          |
+------------------------------------------+
```

### AI Context Empty (Issue Detail)

```
+------------------------------------------+
|                                          |
|  AI Context                              |
|                                          |
|  [Brain illustration]                    |
|                                          |
|  No context generated yet                |
|                                          |
|  Generate AI context to see related      |
|  docs, code files, and task breakdowns.  |
|                                          |
|  [Generate AI Context]                  |
|                                          |
+------------------------------------------+
```

### Chat Empty (No Messages)

```
+------------------------------------------+
|                                          |
|           [Pilot star icon]              |
|                                          |
|      How can I help you today?           |
|                                          |
|  Try asking:                             |
|                                          |
|  [Summarize my recent notes]            |
|  [What are the open bugs?]              |
|  [Help me plan Sprint 13]              |
|  [Extract issues from this note]        |
|                                          |
+------------------------------------------+
```

Suggested prompts are clickable and populate the chat input.

### Approvals Empty

```
+------------------------------------------+
|                                          |
|           [Green checkmark]              |
|                                          |
|      No pending approvals                |
|                                          |
|  All AI actions have been reviewed.      |
|  New approvals will appear here when     |
|  AI actions need your confirmation.      |
|                                          |
+------------------------------------------+
```

### Projects Empty

```
+------------------------------------------+
|                                          |
|          [Folder illustration]           |
|                                          |
|       Create your first project          |
|                                          |
|  Projects group issues, cycles, and      |
|  modules for organized tracking.         |
|                                          |
|  [+ Create a project]                   |
|                                          |
+------------------------------------------+
```

### Search No Results

```
+------------------------------------------+
|                                          |
|          [Magnifying glass]              |
|                                          |
|    No results for "query"                |
|                                          |
|  Try different keywords or check         |
|  your spelling.                          |
|                                          |
+------------------------------------------+
```

### Empty State Design Rules

| Property | Value |
|----------|-------|
| Illustration | 80px, muted color, simple line art |
| Heading | `text-lg`, `font-medium`, centered |
| Description | `text-sm`, `--foreground-muted`, centered, max 280px |
| CTA Button | Primary variant, centered below description |
| Secondary Action | Ghost variant or text link |
| Vertical Spacing | 16px between elements |
| Container Padding | 48px vertical |

---

## 18. Error States & Edge Cases

### Network Errors

```
+------------------------------------------------------------+
| [!] Connection lost. Retrying...                   [Retry] |
+------------------------------------------------------------+
|                                                             |
|  [Normal page content, slightly dimmed]                     |
|                                                             |
```

| Type | Treatment |
|------|-----------|
| **Network Offline** | Top banner (amber), "Connection lost. Retrying...", auto-retry with exponential backoff, manual retry button |
| **API 5xx** | Top banner (red), "Something went wrong. Please try again.", retry button |
| **API 401** | Redirect to login page, clear session |
| **API 403** | Inline error: "You don't have permission to access this resource" |
| **API 404** | Full-page 404 with back navigation |

### AI Provider Errors

| Error | Treatment |
|-------|-----------|
| **API Key Missing** | Banner: "AI features require API keys. [Go to Settings]" with link to AI providers page |
| **API Key Invalid** | Toast error: "Anthropic API key is invalid. Check your settings." |
| **Rate Limited (429)** | Toast with countdown: "Rate limited. Retry in 30s." CountdownTimer component. |
| **Provider Down** | Inline message in ChatView: "AI service temporarily unavailable. Try again shortly." |
| **Token Limit Exceeded** | Toast: "Message too long. Try shortening your prompt." |

### SSE Stream Errors

| Scenario | Treatment |
|----------|-----------|
| **Stream Disconnects** | Auto-reconnect (max 3 attempts, exponential backoff 1s/2s/4s). Inline "Reconnecting..." status. |
| **Heartbeat Timeout** | After 45s without heartbeat, close and reconnect. |
| **Stream Error Event** | Display error in ChatView inline: "Something went wrong. [Retry]" |
| **Max Retries Exceeded** | Persistent error: "Connection failed. Please refresh the page." |

### Note Editor Edge Cases

| Scenario | Treatment |
|----------|-----------|
| **Block Not Found** | AI tool returns gracefully: "I couldn't locate that block. Please select the text again." |
| **Concurrent Edit Conflict** | Toast: "This section was modified while processing. Changes may be overwritten." |
| **Large Notes (5000+ blocks)** | Virtual scroll via `@tanstack/react-virtual`. Only render visible blocks + 20-block buffer. Smooth scroll maintained. |
| **Auto-Save Failure** | Save indicator turns red: "Save failed". Retry every 5s. Data preserved in IndexedDB as fallback. |
| **Ghost Text in Code Block** | Ghost text disabled inside code blocks (Tab is used for indentation). |

### Issue Operations

| Scenario | Treatment |
|----------|-----------|
| **Duplicate Detection** | DuplicateWarning banner during creation with similar issue cards and "Link Instead" action |
| **State Transition Invalid** | IssueStateSelect only shows valid transitions, invalid options grayed with tooltip explanation |
| **Delete with Links** | DeleteConfirmDialog shows linked notes/PRs that will be affected, requires confirmation |
| **Bulk Delete** | Type-to-confirm pattern: user must type issue count to confirm |

### Form Validation

| Error Type | Visual |
|------------|--------|
| **Field Error** | Red border, red error text below field, `aria-describedby` linking |
| **Form Error** | Alert banner at top of form with summary |
| **Async Validation** | Spinner in field while validating, result after debounce |

---

## 19. Accessibility Deep Dive

### WCAG 2.2 AA Compliance

| Requirement | Implementation |
|-------------|----------------|
| Color Contrast | Minimum 4.5:1 for text, 3:1 for UI components and large text |
| Focus Visibility | 3px ring on all interactive elements, visible in both light and dark mode |
| Keyboard Navigation | All features accessible via keyboard, no mouse-only interactions |
| Screen Reader | ARIA labels, roles, live regions for dynamic content |
| Motion | Respects `prefers-reduced-motion` via CSS media query |
| Touch Targets | Minimum 44x44px on all interactive elements |
| Text Resizing | Content readable and functional up to 200% zoom |

### Focus Management

#### Focus Trap Patterns

| Component | Focus Trap Behavior |
|-----------|-------------------|
| **Modals** | Focus trapped within modal. First focusable element receives focus on open. Escape closes. Focus returns to trigger element on close. |
| **Dropdown Menus** | Focus trapped. Arrow keys navigate items. Escape closes, returns focus to trigger. |
| **Command Palette** | Focus trapped. Search input auto-focused. Arrow keys navigate results. |
| **ApprovalOverlay** | Focus trapped. Approve button focused by default. Tab cycles between reject and approve only. |
| **Sidebar (mobile)** | Focus trapped when open as Sheet. Escape or outside click closes. |

#### Focus Region Cycling (F6)

```
[Sidebar] -> [Header] -> [Main Content] -> [ChatView/Panel] -> [Sidebar]
```

F6 cycles focus between major landmarks. Shift+F6 cycles backward.

### Screen Reader Announcements

| Event | Announcement | ARIA Method |
|-------|-------------|-------------|
| **AI Streaming Start** | "PilotSpace AI is responding" | `aria-live="polite"` on MessageList |
| **AI Streaming Complete** | "PilotSpace AI response complete" | `aria-live="polite"` |
| **Task Progress Update** | "Task: [name], [X]% complete" | `aria-live="polite"` on TaskPanel |
| **Approval Required** | "Action approval required: [description]" | `aria-live="assertive"` on ApprovalOverlay |
| **Toast Notification** | Toast content | `role="alert"`, `aria-live="polite"` |
| **Issue State Change** | "Issue PS-123 moved to [state]" | `aria-live="polite"` |
| **Auto-Save Status** | "Note saved" / "Saving..." / "Save failed" | `aria-live="polite"` on save indicator |
| **Ghost Text Available** | "Suggestion available. Press Tab to accept." | `aria-live="polite"` |
| **Search Results** | "[N] results found" | `aria-live="polite"` on results container |

### ARIA Live Regions

| Region | Level | Location | Content |
|--------|-------|----------|---------|
| Toast Container | `polite` | Fixed bottom-right | Toast messages |
| Chat Messages | `polite` | MessageList | New AI messages |
| Task Panel | `polite` | TaskPanel | Task status changes |
| Approval Overlay | `assertive` | ApprovalOverlay | Approval requests |
| Save Indicator | `polite` | Note editor header | Save status |
| Error Banner | `assertive` | Top of page | Network/API errors |

### Semantic HTML & Landmarks

```html
<body>
  <a href="#main" class="sr-only focus:not-sr-only">Skip to main content</a>
  <nav aria-label="Sidebar navigation">...</nav>
  <header role="banner">...</header>
  <main id="main" role="main">...</main>
  <aside aria-label="Chat panel">...</aside>  <!-- ChatView when embedded -->
  <div role="complementary" aria-label="Notifications">...</div>
</body>
```

### Keyboard Shortcut Accessibility

- All keyboard shortcuts have menu alternatives (no keyboard-only actions)
- Shortcuts displayed in tooltips (Stage 2) and command palette
- `?` opens full keyboard shortcut reference sheet (modal)
- Shortcuts disabled when focus is in text input fields (except Cmd+ combinations)
- Screen reader users can access shortcut guide via command palette

### Skip Links

| Link | Target | Visibility |
|------|--------|------------|
| "Skip to main content" | `#main` | Visible on focus only |
| "Skip to navigation" | Sidebar | Visible on focus only |
| "Skip to chat" | ChatView input | Visible on focus only (when ChatView present) |

### Color Contrast Verification

All color combinations meet WCAG AA (4.5:1 for normal text, 3:1 for large text):

| Combination | Ratio | Pass |
|-------------|-------|------|
| Foreground on Background (light) | 14.5:1 | AA |
| Foreground Muted on Background (light) | 4.6:1 | AA |
| Primary on White | 4.5:1 | AA |
| AI Blue on White | 4.2:1 | AA (large text only, used with bold) |
| Foreground on Background (dark) | 13.8:1 | AA |
| Foreground Muted on Background (dark) | 5.1:1 | AA |
| Primary (dark) on Card (dark) | 5.2:1 | AA |

---

## 20. Implementation Notes

### Performance Targets

| Metric | Target |
|--------|--------|
| First Contentful Paint | < 1.5s |
| Largest Contentful Paint | < 2.5s |
| Time to Interactive | < 3s |
| Cumulative Layout Shift | < 0.1 |
| Interaction to Next Paint | < 200ms |
| Interaction Latency | < 100ms |

### Virtual Scroll

For notes with 1000+ blocks:
- `@tanstack/react-virtual` wrapping TipTap NodeView container
- Block heights measured via ResizeObserver
- Render visible blocks + 20-block buffer above and below
- Maintain scroll position on content changes
- Threshold for activation: 500+ blocks

### Code Splitting

| Category | Loading Strategy |
|----------|-----------------|
| **Static** | TipTap core, Command Palette, sidebar, header |
| **Dynamic** (`next/dynamic`) | Sigma.js (knowledge graph), Mermaid renderer, Recharts, AI Panel |
| **Threshold** | Lazy load components >50KB gzipped |
| **Barrel Files** | Feature-level only (`@/features/issues/index.ts`), no component-level barrels |

### Code Organization

```
frontend/src/
  components/
    ui/             # Base shadcn/ui components (button, card, badge, etc.)
    layout/         # AppShell, sidebar, header
    editor/         # TipTap editor wrappers, toolbar, annotations
    issues/         # IssueCard, IssueBoard, IssueModal, etc.
    cycles/         # BurndownChart, VelocityChart, CycleBoard
    integrations/   # GitHub, PR review components
    navigation/     # OutlineTree, PinnedNotesList
    ai/             # AIConfidenceTag, CountdownTimer

  features/
    ai/ChatView/    # Complete ChatView subsystem
    notes/          # Note-specific components and editor extensions
    issues/         # Issue feature components (AI context, conversation)
    approvals/      # Approval queue page and components
    costs/          # Cost dashboard page and components
    settings/       # Settings pages and forms
    github/         # GitHub integration feature pages

  stores/
    RootStore.ts    # Store aggregator and context
    AuthStore.ts    # Authentication state
    UIStore.ts      # UI state (theme, sidebar, modals)
    WorkspaceStore.ts
    NotificationStore.ts
    features/       # Domain-specific stores
    ai/             # 11 AI sub-stores + PilotSpaceStore
```

### Frontend Architecture Decisions

*Session 2026-01-22: Technical implementation clarifications*

#### State Management

| Decision | Implementation |
|----------|----------------|
| MobX vs TanStack Query | **MobX UI-only** - TanStack Query handles all server data (fetching, caching, mutations). MobX only for ephemeral UI state (selection, toggles, local drafts). |
| Realtime Updates | Optimistic merge via `queryClient.setQueryData()`. Skip Realtime update if local mutation pending. |

#### TipTap/ProseMirror Editor

| Decision | Implementation |
|----------|----------------|
| Virtualization | **@tanstack/react-virtual** - TipTap NodeView wraps virtualized container. Block heights via ResizeObserver. |
| Ghost Text Cancellation | **AbortController** per request. Previous controller aborted on new keystroke. |
| Key Conflicts (Tab) | Context-aware priority: 1) code block -> indent, 2) ghost text visible -> accept, 3) default behavior. |
| Content Diff | Block-level tracking via TipTap transaction. >20% blocks changed -> trigger embedding refresh. |
| Margin Positioning | **CSS Anchor Positioning API** (Chrome 125+). Fallback: absolute positioning for Safari/Firefox. |

#### Performance & Bundle

| Decision | Implementation |
|----------|----------------|
| Code Splitting | Dynamic import (`next/dynamic`): Sigma.js, Mermaid, AI Panel. Static: TipTap, Command Palette. Threshold: >50KB gzipped. |
| Barrel Files | Feature-level only (`@/features/issues/index.ts`). No component-level barrels. Named exports only. |

#### SSE & AI Streaming

| Decision | Implementation |
|----------|----------------|
| Connection Model | Separate EventSource per AI operation. HttpOnly cookie for auth. |
| Error Display | Context-specific: Ghost text -> inline muted. AI Panel -> panel error state. PR review -> toast. |
| Command Palette Context | Minimal: selection text + entity type + title. Cache 30s. |
| Reconnection | Exponential backoff (1s, 2s, 4s), max 3 attempts, token refresh before reconnect. |
| Heartbeat | Server sends every 30s, client reconnects if none received for 45s. |

#### Accessibility

| Decision | Implementation |
|----------|----------------|
| Focus Management | Explicit escape pattern. Tab in editor. Escape -> sidebar. F6 cycles regions. |
| Motion | CSS `@media (prefers-reduced-motion: reduce)`. Tailwind `motion-safe:` / `motion-reduce:` variants. |

#### Testing

| Decision | Implementation |
|----------|----------------|
| TipTap Testing | Integration tests with real editor in Vitest (jsdom). |
| SSE Mocking | MSW handlers for streaming responses. |
| Accessibility | axe-core in CI + manual screen reader testing. |
| E2E | Playwright for critical user flows (note creation, issue extraction). |

### Testing Requirements

| Type | Coverage | Tool |
|------|----------|------|
| Visual Regression | All components | Chromatic / Playwright screenshots |
| Accessibility | Automated + manual | axe-core, screen reader testing |
| Responsive | All breakpoints | Playwright viewport testing |
| Keyboard | All interactions | Manual + E2E |
| Component | Critical paths | Vitest + React Testing Library |
| E2E | User flows | Playwright |

---

*Document Version: 4.0.0*
*Last Updated: 2026-02-01*
*Author: Pilot Space Team*
*Changes v4.0: Complete rewrite. Added complete page catalog (17 pages), ChatView system specification, full component catalog (80+ components), responsive design matrix per page, animation system with 16 named animations, state management architecture, dark mode token mapping, empty states for all pages, error states and edge cases, accessibility deep dive with ARIA patterns.*
*Changes v3.3: Added Frontend Architecture Decisions section with 15 implementation clarifications (State Management, Virtualization, SSE, Testing)*
*Changes v3.2: Added AI-Prioritized Notification Center (DD-038) and Similar Notes with AI Guidance (DD-036) UI specifications*
