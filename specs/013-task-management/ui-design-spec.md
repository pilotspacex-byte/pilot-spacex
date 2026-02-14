# 013 - Task Management: UI/UX Design Specification

**Version**: 1.1
**Status**: Draft
**Author**: Tin Dang
**Date**: 2026-02-12
**Updated**: 2026-02-12 (v1.1 — aligned with production design system)
**Prototype Source**: `design-system/prototype/issue-detail-full.html` (structural reference only)
**Design System Source**: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 (authoritative)
**Feature Spec**: `specs/013-task-management/spec.md`

> **Note**: The prototype uses DM Sans/Fraunces/DM Mono fonts and hardcoded color values.
> This spec overrides those with the production design system (Geist/Geist Mono, opacity-based tokens).
> Prototype is used for **layout and structure** only, not for visual tokens.

---

## Table of Contents

1. [Design Tokens](#1-design-tokens)
2. [Component Specifications](#2-component-specifications)
3. [Interaction Patterns](#3-interaction-patterns)
4. [Layout & Composition](#4-layout--composition)
5. [Color Mapping](#5-color-mapping)
6. [Wireframe Descriptions](#6-wireframe-descriptions)

---

## 0. Design System Mood Compliance

### Pilot Space Mood: Warm, Capable, Collaborative

All components in this spec MUST adhere to these three pillars:

| Pillar | How This Feature Implements It |
|--------|-------------------------------|
| **Warm** | Warm off-white backgrounds (`#FDFCFA`), soft warm-tinted shadows, subtle noise texture, Geist font with natural spacing, generous whitespace between sections |
| **Capable** | Progressive disclosure (collapsed subsections, expand buttons), clear information hierarchy (summary → context → tasks → prompts), power-user keyboard shortcuts |
| **Collaborative** | AI as co-pilot — chat section uses "AI" avatar with *italic voice*, "You + AI" attribution, AI-generated badges on tasks, "Enhance Context" conversational interface |

### Key Mood Differentiators (vs generic UI)

| Element | Generic Approach | Pilot Space Mood |
|---------|-----------------|------------------|
| Font | Inter (cold, clinical) | **Geist** (warm, humanist) |
| Backgrounds | Pure white `#FFFFFF` | **Warm off-white** `#FDFCFA` |
| Shadows | Neutral black | **Warm-tinted** HSL(30, 10%, 10%) |
| Corners | 4-8px radius | **Squircle** 10-14px radius |
| AI indicators | Neon green/purple | **Dusty blue** `#6B8FAD` (calm, trustworthy) |
| Hover effects | Opacity change | **Scale 102% + shadow lift** (tactile, Apple-inspired) |
| Surfaces | Flat | **Layered** with noise overlay (2% opacity, multiply) |
| AI voice | Same as user text | ***Italic*** (distinct but not separate) |

### Inspirations Applied

- **Craft**: Layered surfaces in code snippet cards (dark code block nested in warm card)
- **Apple**: Squircle corners (10px buttons, 14px cards), scale + shadow hover micro-interactions
- **Things 3**: Calm color palette, spacious task checklist, satisfying checkbox toggle

---

## 1. Design Tokens

All values from the production design system (`specs/001-pilot-space-mvp/ui-design-spec.md` v4.0).
Prototype CSS values listed in parentheses where they differ, for cross-reference only.

### 1.1 Colors

#### Base Colors (production design system tokens)

| Token | Value | Tailwind Class | Usage in AI Context Tab |
|-------|-------|----------------|-------------------------|
| `--background` | `#FDFCFA` | `bg-background` | Page background, graph canvas fill |
| `--background-subtle` | `#F7F5F2` | `bg-muted/50` | Task item bg, file tree item bg, task graph bg, chat message bg |
| `--foreground` | `#171717` | `text-foreground` | Primary text, graph node labels |
| `--foreground-muted` | `#737373` | `text-muted-foreground` | Secondary text, meta text, file paths, dependency text |
| `--border` | `#E5E2DD` | `border-border` | Section borders, task item borders, code snippet borders |
| `--border-subtle` | `#EBE8E4` | `border-border/60` | Task item default border, context item border |

#### AI Colors (dusty blue — opacity-based tokens)

| Token | Value | Tailwind Class | Usage |
|-------|-------|----------------|-------|
| `--ai` | `#6B8FAD` | `text-ai` / `bg-ai` | AI Context header title, stat counts, task estimates, prompt title, chat avatar bg, graph root node |
| `--ai-hover` | `#5A7D9B` | `hover:bg-ai/85` | Button hover states (copy all, send) |
| `--ai-muted` | `#6B8FAD15` (15% opacity) | `bg-ai/[0.08]` | Context summary card gradient start, chat section bg, prompt header bg |
| `--ai-border` | `#6B8FAD30` (30% opacity) | `border-ai/20` | AI tab border, prompt block border, chat section border, graph dependency arrows |
| `--ai-foreground` | `#FFFFFF` | `text-white` | White text on AI-colored buttons |

#### Primary Colors (teal green — opacity-based tokens)

| Token | Value | Tailwind Class | Usage |
|-------|-------|----------------|-------|
| `--primary` | `#29A386` | `bg-primary` / `text-primary` | Completed task checkbox, graph nodes (non-root), success feedback, file badge "new" |
| `--primary-hover` | `#238F74` | `hover:bg-primary/85` | Primary button hover |
| `--primary-muted` | `#29A38615` (15% opacity) | `bg-primary/[0.08]` | File badge "new" bg, done status pill bg |

#### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--destructive` | `#D9534F` | "Blocks" relation badge text; badge bg at 10% opacity |
| `--warning` / `--amber` | `#D9853F` | "Blocked by" badge, folder icons, branch git-ref icon, file badge "modified" |
| `--success` | `#29A386` (same as primary) | Copy feedback checkmark, completed checkbox |

#### Context Item Badge Colors (from prototype lines 1289-1294)

| Badge Type | Background | Text Color |
|------------|------------|------------|
| `blocks` | `#FEE8E8` | `--destructive` (#D9534F) |
| `relates` | `--ai-muted` (#EEF3F7) | `--ai` (#6B8FAD) |
| `blocked-by` | `#FEF3E8` | `--warning` (#D9853F) |
| `doc` / `note` | `--primary-muted` (#E8F5F1) | `--primary` (#29A386) |
| `adr` | `#FEF3E8` | `--warning` (#D9853F) |
| `spec` | `--ai-muted` (#EEF3F7) | `--ai` (#6B8FAD) |

#### File Badge Colors (from prototype lines 1358-1368)

| Badge Type | Background | Text Color |
|------------|------------|------------|
| `modified` | `#FEF3E8` | `--warning` (#D9853F) |
| `new` | `--primary-muted` (#E8F5F1) | `--primary` (#29A386) |
| `reference` (default) | `bg-muted` | `text-muted-foreground` |

#### Git Reference Icon Colors (from prototype lines 1458-1460)

| Ref Type | Background | Icon Color |
|----------|------------|------------|
| `pr` | `--primary-muted` (#E8F5F1) | `--primary` (#29A386) |
| `commit` | `--ai-muted` (#EEF3F7) | `--ai` (#6B8FAD) |
| `branch` | `#FEF3E8` | `--warning` (#D9853F) |

#### Task Graph Node Colors (from prototype JS lines 2896-2901)

| Node Type | Fill Color |
|-----------|------------|
| Root task (first) | `--ai` (#6B8FAD) |
| Other tasks | `--primary` (#29A386) |
| Dependency arrows | `--ai-border` (#B8CCDB) |
| Background | `--background-subtle` (#F7F5F2) |
| Node label text | `--foreground` (#171717) |
| Node number text | `#FFFFFF` |

### 1.2 Typography

Uses Pilot Space production font stack: **Geist** (UI) and **Geist Mono** (code).
Mapped to the design system's named type scale (`text-xs` to `text-2xl`).

> **Note**: The prototype uses DM Sans / Fraunces / DM Mono. All references below use the production Geist stack.

| Element | Font | Size Token | Size (px) | Weight | Tailwind | Notes |
|---------|------|------------|-----------|--------|----------|-------|
| AI Context header title | Geist | `text-lg` | 17px | 500 | `text-lg font-medium` | Prototype uses Fraunces display — use Geist semibold instead |
| Context summary card h3 | Geist | `text-lg` | 17px | 500 | `text-lg font-medium` | |
| Context summary card p | Geist | `text-sm` | 13px | 400 | `text-sm` | line-height 1.6 |
| Context section title | Geist | `text-base` | 15px | 500 | `text-base font-medium` | |
| Context subsection title | Geist | `text-xs` | 11px | 600 | `text-xs font-semibold uppercase tracking-wider` | |
| Context item title | Geist | `text-sm` | 13px | 500 | `text-sm font-medium` | |
| Context item summary | Geist | `text-xs` | 11px | 400 | `text-xs` | line-height 1.5 |
| Context item badge | Geist | `text-xs` | 11px | 600 | `text-xs font-semibold` | Pill badge |
| Context item ID | Geist Mono | `text-xs` | 11px | 500 | `font-mono text-xs font-medium` | |
| Stat item label | Geist | `text-xs` | 11px | 400 | `text-xs text-muted-foreground` | |
| Stat item number | Geist | `text-xs` | 11px | 600 | `text-xs font-semibold text-ai` | |
| File tree item | Geist Mono | `text-xs` | 11px | 400 | `font-mono text-xs` | |
| File badge | Geist | `text-xs` | 11px | 400 | `text-xs` | Smaller padding variant |
| Code snippet file path | Geist Mono | `text-xs` | 11px | 400 | `font-mono text-xs` | |
| Code snippet content | Geist Mono | `text-sm` | 13px | 400 | `font-mono text-sm` | line-height 1.6 |
| Git ref title | Geist | `text-sm` | 13px | 500 | `text-sm font-medium` | |
| Git ref meta | Geist | `text-xs` | 11px | 400 | `text-xs text-muted-foreground` | |
| Task title | Geist | `text-sm` | 13px | 500 | `text-sm font-medium` | |
| Task meta | Geist | `text-xs` | 11px | 400 | `text-xs text-muted-foreground` | |
| Task estimate | Geist | `text-xs` | 11px | 400 | `text-xs text-ai` | |
| Prompt title | Geist | `text-sm` | 13px | 600 | `text-sm font-semibold` | |
| Prompt content | Geist Mono | `text-sm` | 13px | 400 | `font-mono text-sm` | line-height 1.6 |
| Chat content | Geist | `text-sm` | 13px | 400 | `text-sm` | line-height 1.6 |
| Chat input | Geist | `text-sm` | 13px | 400 | `text-sm` | |
| Context action button | Geist | `text-xs` | 11px | 500 | `text-xs font-medium` | |
| AI voice (chat responses) | Geist | `text-sm` | 13px | 400 *italic* | `text-sm italic` | AI text uses italic per design system |

### 1.3 Spacing

From prototype CSS custom properties (lines 63-71).

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `4px` | Badge inner padding, fine gaps |
| `--space-2` | `8px` | Button padding-y, checkbox margin-top, small gaps |
| `--space-3` | `12px` | Task item padding, git ref padding, button gaps, section header margin-bottom |
| `--space-4` | `16px` | Section padding, code snippet padding, context item padding, chat padding |
| `--space-5` | `20px` | Context section padding, context summary card padding/gap |
| `--space-6` | `24px` | Section margin-bottom between sections, tab header margin-bottom |
| `--space-8` | `32px` | Major section spacing (context-section margin-bottom), file tree indent level 1 padding-left |

### 1.4 Border Radius

From prototype CSS custom properties (lines 74-79).

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Copy buttons, file tree item hover, task expand button, code copy button |
| `--radius` | `10px` | Context items, code snippet container, chat input, task graph container, prompt block, git ref items |
| `--radius-lg` | `14px` | Context section containers, context summary card, AI thread |
| `--radius-full` | `9999px` | Pill badges (status, relation type) |

### 1.5 Shadows

From prototype CSS custom properties (lines 82-86).

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px hsl(30 10% 10% / 0.04)` | Subtle card lift |
| `--shadow` | `0 2px 4px hsl(30 10% 10% / 0.04), 0 4px 8px hsl(30 10% 10% / 0.04)` | Card default elevation |
| `--shadow-md` | `0 4px 8px hsl(30 10% 10% / 0.04), 0 8px 16px hsl(30 10% 10% / 0.06)` | Hover elevation |

### 1.6 Animation

From prototype CSS custom properties (lines 88-93).

| Token | Value | Usage |
|-------|-------|-------|
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Expand/collapse transitions |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Background color transitions |
| `--duration-fast` | `150ms` | Hover states, button transitions, checkbox toggle |
| `--duration-normal` | `200ms` | Section expand/collapse |
| `--duration-slow` | `300ms` | Graph animations |

---

## 2. Component Specifications

### 2.A AI Context Tab Header

**Prototype reference**: Lines 2162-2188 (HTML), lines 1080-1131 (CSS)

**Purpose**: Top bar of the AI Context tab containing title and action buttons.

#### Layout

```
┌─────────────────────────────────────────────────────────┐
│ [AI Icon] Full Context for AI Implementation   [Copy All] [Regenerate] │
├─────────────────────────────────────────────────────────┤
│ 1px solid --border (separator below)                     │
```

- **Container**: `display: flex; align-items: center; justify-content: space-between`
- **Padding-bottom**: `--space-4` (16px)
- **Margin-bottom**: `--space-6` (24px)
- **Border-bottom**: `1px solid var(--border)`

#### Title

- Font: Geist, `text-lg` (17px), weight 500 (`font-medium`)
- Color: `text-ai` (#6B8FAD)
- Icon: 18x18px Sparkles icon, same color (Lucide, 1.5px stroke, rounded caps)
- Gap between icon and text: `--space-3` (12px)

#### Action Buttons

- **Container**: `display: flex; gap: var(--space-2)` (8px)
- **"Copy All Context" (primary AI button)** — uses `ai` button variant:
  - Background: `--ai` (#6B8FAD)
  - Text: white, `text-xs` (11px), `font-medium`
  - Padding: 8px vertical, 16px horizontal (matches button `sm` size: 32px height)
  - Border-radius: `rounded` (10px)
  - Icon: 16px Copy icon, white (Lucide, 1.5px stroke)
  - Gap icon-to-text: `--space-2` (8px)
  - Hover: scale 102%, `--ai-hover` bg, elevated shadow
  - Active: scale back, deeper shadow
  - Focus: 3px `--ai` ring at 30% opacity
- **"Regenerate" (secondary outline button)**:
  - Background: transparent
  - Text: `text-ai` (#6B8FAD), `text-xs`, `font-medium`
  - Border: `1px solid var(--ai-border)` (ai at 30% opacity)
  - Padding/radius: same as primary
  - Icon: 16px RefreshCw icon (Lucide)
  - Hover: scale 102%, `bg-ai/[0.08]`, elevated shadow
  - Focus: 3px `--ai` ring at 30% opacity

#### States

| State | Visual Change |
|-------|---------------|
| Default | As described above |
| Copy loading | Button text changes to "Copying..." (optional spinner) |
| Copy success | Button text changes to "Copied!" for 1.5s, icon changes to Check |
| Regenerate loading | Button text changes to "Regenerating...", RefreshCw icon spins (`animate-spin`) |
| Regenerate disabled | opacity 0.5, `pointer-events: none` while loading |

#### Accessibility

- Title: `<h2>` semantic heading
- Copy button: `aria-label="Copy all context to clipboard"`
- Regenerate button: `aria-label="Regenerate AI context"`, `aria-disabled` when loading
- Copy success: Use `aria-live="polite"` region for "Copied!" announcement

#### Tailwind Mapping

```css
ai-context-header → flex items-center justify-between mb-6 pb-4 border-b border-border
ai-context-title → flex items-center gap-3 text-lg font-medium text-ai
context-action-btn-primary → flex items-center gap-2 px-4 py-2 h-8 bg-ai text-white rounded-[10px] text-xs font-medium hover:bg-ai/85 hover:scale-[1.02] hover:shadow-md active:scale-100 focus-visible:ring-2 focus-visible:ring-ai/30 transition-all duration-150
context-action-btn-outline → flex items-center gap-2 px-4 py-2 h-8 bg-transparent text-ai border border-ai/20 rounded-[10px] text-xs font-medium hover:bg-ai/[0.08] hover:scale-[1.02] hover:shadow-md active:scale-100 focus-visible:ring-2 focus-visible:ring-ai/30 transition-all duration-150
```

---

### 2.B Context Summary Card

**Prototype reference**: Lines 2190-2211 (HTML), lines 1134-1183 (CSS)

**Purpose**: Gradient card showing issue identifier, title, summary paragraph, and 4 stat counters.

#### Layout

```
┌──────────────────────────────────────────────────┐
│ [48px Icon]  PS-201: Simplify Password Reset     │
│              Summary paragraph text...           │
│              [4 Issues] [3 Docs] [8 Files] [5 Tasks] │
└──────────────────────────────────────────────────┘
```

- **Container**: `display: flex; gap: var(--space-5)` (20px)
- **Padding**: `--space-5` (20px)
- **Background**: `linear-gradient(135deg, var(--ai-muted) 0%, #E8F0F5 100%)`
- **Border**: `1px solid var(--ai-border)` (#B8CCDB)
- **Border-radius**: `--radius-lg` (14px)
- **Margin-bottom**: `--space-6` (24px)

#### Icon Block

- Size: 48x48px
- Background: `--ai` (#6B8FAD)
- Border-radius: `--radius` (10px)
- Icon: 24x24px FileText, white
- `flex-shrink: 0`

#### Content Block

- **Issue identifier**: Geist, `text-xs font-medium text-ai`
- **Title (h3)**: Geist, `text-lg font-medium`
- **Summary (p)**: Geist, `text-sm text-muted-foreground`, line-height 1.6
- **Stats row**: `display: flex; gap: var(--space-4)` (16px), padding-top `--space-1` (4px)

#### Stat Items

Each stat: `<Icon 14px> <strong count> <label>`
- Icon: 14x14px, `--foreground-muted`
- Count: `--ai` color, weight 600
- Label: `text-xs text-muted-foreground`

Stats: Related Issues (Link2), Documents (BookOpen), Files (Code), Tasks (ListChecks)

#### States

| State | Visual |
|-------|--------|
| Populated | All stats shown with counts |
| Zero counts | Show "0" — do not hide stat items |
| Loading | Skeleton: gradient shimmer over card area |

#### Existing Implementation Note

`context-summary-card.tsx` already implements this. Enhancement needed: ensure the `stats` object includes `filesCount` and `tasksCount` fields (currently present in the `ContextSummary` type).

#### Accessibility

- Card: `role="region"` with `aria-label="Context summary"`
- Each stat: `aria-label="{count} {label}"` (already implemented)

---

### 2.C Codebase Context Section (NEW)

**Prototype reference**: Lines 2294-2486 (HTML), lines 1186-1476 (CSS)

**Purpose**: Container section showing file tree, code snippets, and git references relevant to the issue.

#### Section Container

- Same pattern as other `context-section` blocks
- **Padding**: `--space-5` (20px)
- **Background**: `--background` (#FDFCFA)
- **Border**: `1px solid var(--border)` (#E8E6E3)
- **Border-radius**: `--radius-lg` (14px)
- **Margin-bottom**: `--space-8` (32px)

#### Section Header

```
┌──────────────────────────────────────────────────┐
│ [Code Icon] Codebase Context                [Copy] │
├──────────────────────────────────────────────────┤
```

- Same `context-section-header` pattern as Related Context
- Icon: 16px Code brackets icon (Lucide, 1.5px stroke), color `text-ai`
- Title: Geist, `text-base font-medium`
- Copy button: 28x28px, `--background-subtle` bg, `1px solid --border`, `--radius-sm`
- Header border-bottom: `1px solid var(--border-subtle)`, margin-bottom `--space-5`

#### 2.C.1 File Tree Subsection

**Prototype reference**: Lines 2312-2382 (HTML), lines 1326-1368 (CSS)

```
┌──────────────────────────────────────────┐
│ RELEVANT FILES (subsection title)        │
│ 📁 src/auth/                             │
│   📄 password_reset.py      [Modified]   │
│   📄 magic_link.py          [New]        │
│   📄 email_service.py       [Reference]  │
│ 📁 src/components/auth/                  │
│   📄 PasswordResetForm.tsx   [Modified]   │
│   📄 MagicLinkFlow.tsx       [New]        │
│ 📁 tests/auth/                           │
│   📄 test_password_reset.py  [Modified]   │
└──────────────────────────────────────────┘
```

**Subsection Title**: `text-xs font-semibold uppercase tracking-wider text-muted-foreground`, margin-bottom `--space-3`

**File Tree Container**:
- Font: Geist Mono, `font-mono text-xs`
- No border (contained within section)

**File Tree Item** (each row):
- Layout: `display: flex; align-items: center; gap: var(--space-2)` (8px)
- Padding: `--space-2` (8px) vertical, `--space-3` (12px) horizontal
- Border-radius: `--radius-sm` (6px)
- Cursor: pointer
- Hover: background `--background-muted` (#F3F2EF)
- Transition: `background var(--duration-fast)`

**Folder Item**:
- Icon: 14x14px Folder icon, color `--warning` (#D9853F)
- Text: folder path

**File Item** (indented):
- Padding-left: `--space-8` (32px) for indent level 1
- Icon: 14x14px File icon, color `--foreground-muted`
- Text: filename

**File Badge** (right-aligned):
- `margin-left: auto`
- Font: `text-xs` (11px)
- Padding: `2px 6px`
- Border-radius: `4px`
- Variants: see File Badge Colors in section 1.1

**States**:

| State | Visual |
|-------|--------|
| Default | File tree visible |
| Folder collapsed | Chevron rotated right, children hidden |
| Folder expanded | Chevron rotated down, children visible |
| File hover | Row bg changes to `--background-muted` |
| Empty | "No relevant files identified" message |

**Responsive**: On small screens (<640px), truncate long file paths with `text-overflow: ellipsis`.

**Accessibility**:
- Tree: `role="tree"`
- Folder: `role="treeitem"`, `aria-expanded="{true|false}"`
- File: `role="treeitem"`
- Badge: `aria-label="File status: {modified|new|reference}"`

#### 2.C.2 Code Snippet Cards

**Prototype reference**: Lines 2385-2437 (HTML), lines 1370-1425 (CSS)

```
┌──────────────────────────────────────────────────┐
│ KEY CODE SECTIONS (subsection title)             │
│ ┌──────────────────────────────────────────────┐ │
│ │ src/auth/password_reset.py:45-62    [Copy]   │ │
│ ├──────────────────────────────────────────────┤ │
│ │ async def initiate_password_reset(...):      │ │
│ │     """Current implementation..."""           │ │
│ │     user = await get_user_by_email(email)    │ │
│ │     ...                                      │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Snippet Container**:
- Border: `1px solid var(--border)` (#E8E6E3)
- Border-radius: `--radius` (10px)
- `overflow: hidden`
- Margin-bottom: `--space-4` (16px) between snippets

**Snippet Header**:
- Layout: `display: flex; align-items: center; justify-content: space-between`
- Padding: `--space-2` (8px) vertical, `--space-3` (12px) horizontal
- Background: `--background-muted` (#F3F2EF)
- Border-bottom: `1px solid var(--border)`

**File Path Text**:
- Font: Geist Mono, `font-mono text-xs text-muted-foreground`
- Format: `{filepath}:{startLine}-{endLine}`

**Copy Button**:
- Size: 24x24px
- Background: transparent
- Border: none
- Border-radius: `--radius-sm` (6px)
- Icon: 12x12px Copy icon, color `--foreground-muted`
- Hover: background `--background-subtle`, icon color `--foreground`

**Code Content Area**:
- Padding: `--space-4` (16px)
- Background: `#1E1E1E` (dark code theme — VS Code style)
- `overflow-x: auto` for horizontal scroll
- Code font: Geist Mono, `font-mono text-sm`, line-height 1.6, color `#D4D4D4`
- Rendered as `<pre><code>` block
- `white-space: pre` (preserve formatting)

**States**:

| State | Visual |
|-------|--------|
| Default | Code visible in dark block |
| Copy hover | Copy button bg `--background-subtle` |
| Copied | Copy icon changes to Check for 1.5s, button bg `--primary` briefly |
| Empty | "No code snippets available" message |

**Accessibility**:
- Code block: `role="region"`, `aria-label="Code from {filepath}"`
- Copy button: `aria-label="Copy code snippet"`, updates to "Copied" on success

#### 2.C.3 Git References

**Prototype reference**: Lines 2439-2484 (HTML), lines 1427-1476 (CSS)

```
┌──────────────────────────────────────────────────┐
│ GIT REFERENCES (subsection title)                │
│ [PR Icon] #142 - Add magic link authentication   │
│           Draft · Updated 2 days ago             │
│ [Commit]  feat(auth): initial password reset...  │
│           abc1234 · 3 days ago                   │
│ [Branch]  feature/ps-201-password-reset          │
│           Active branch · 5 commits ahead        │
└──────────────────────────────────────────────────┘
```

**Git Refs Container**: `display: flex; flex-direction: column; gap: var(--space-2)` (8px)

**Git Ref Item**:
- Layout: `display: flex; align-items: center; gap: var(--space-3)` (12px)
- Padding: `--space-3` (12px)
- Background: `--background-subtle` (#F8F7F5)
- Border-radius: `--radius` (10px)
- Cursor: pointer
- Hover: background `--background-muted` (#F3F2EF)
- Transition: `background var(--duration-fast)`

**Git Ref Icon**:
- Size: 28x28px container
- Border-radius: `--radius-sm` (6px)
- Icon: 14x14px inside, centered
- Variants: see Git Reference Icon Colors in section 1.1

**Git Ref Content**:
- Layout: `display: flex; flex-direction: column; gap: 2px`
- Title: Geist, `text-sm font-medium`
- Meta: Geist, `text-xs text-muted-foreground`

**States**:

| State | Visual |
|-------|--------|
| Default | As described |
| Hover | bg `--background-muted` |
| Link click | Navigates to GitHub URL (opens in new tab) |
| Empty | "No git references found" message |

**Accessibility**:
- Each ref: `role="link"` or `<a>` tag with `target="_blank" rel="noopener noreferrer"`
- `aria-label="{type}: {title}"`

---

### 2.D AI Tasks Section (Enhanced)

**Prototype reference**: Lines 2488-2661 (HTML), lines 1478-1631 (CSS), JS lines 2836-2915 and 3024-3029

**Purpose**: Task dependency graph, implementation checklist with CRUD, and ready-to-use prompts.

#### Section Container

Same `context-section` pattern. Header icon: CheckSquare, title "AI Tasks".

#### 2.D.1 Task Dependency Graph (NEW — Canvas)

**Prototype reference**: Lines 2506-2512 (HTML), lines 1478-1490 (CSS), JS lines 2836-2915

```
┌──────────────────────────────────────────────────┐
│ TASK DEPENDENCIES (subsection title)             │
│ ┌──────────────────────────────────────────────┐ │
│ │         ╭─── T2 ─── T4 ───╮                 │ │
│ │   T1 ──┤                  ├── T5             │ │
│ │         ╰─── T3 ──────────╯                 │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Container**:
- Background: `--background-subtle` (#F8F7F5)
- Border: `1px solid var(--border)` (#E8E6E3)
- Border-radius: `--radius` (10px)
- `overflow: hidden`

**Canvas**:
- Width: 100% of container
- Height: `200px` fixed
- `display: block`
- Retina rendering: canvas.width = offsetWidth * 2, then ctx.scale(2, 2)

**Layout Algorithm** (from prototype JS):
- Manual DAG positioning: tasks arranged left-to-right
- Root task at left center (`x=80, y=height/2`)
- Dependency children fan out horizontally at `x+140` intervals
- Vertical spread: tasks at same depth offset by `+/-50px` from center
- Final task at rightmost position, center Y

**Node Rendering**:
- Circle: radius `24px`
- Root node fill: `--ai` (#6B8FAD)
- Other nodes fill: `--primary` (#29A386)
- Node number: white, `600 12px 'Geist'`, centered
- Node description: `--foreground` (#171717), `500 10px 'Geist'`, below node at `y+38px`

**Edge Rendering**:
- Line from source node `(x+30, y)` to target node `(x-30, y)`
- Stroke: `--ai-border` (#B8CCDB), `lineWidth: 2`
- Arrow head: filled triangle at target end, 8px size, same color
- Arrow angle calculated from `Math.atan2(dy, dx)`

**States**:

| State | Visual |
|-------|--------|
| Populated | DAG rendered with nodes and arrows |
| Single task | Single node centered, no arrows |
| No tasks | Graph container hidden entirely |
| Loading | Skeleton shimmer over canvas area |

**Responsive**: On narrow screens (<500px), reduce canvas height to 150px and scale node positions proportionally.

**Accessibility**:
- Canvas: `role="img"`, `aria-label="Task dependency graph showing {N} tasks"`
- Include a visually-hidden text description of the dependency chain for screen readers
- Provide `<ul>` fallback below canvas listing dependencies in text form

#### 2.D.2 Implementation Checklist (Enhanced)

**Prototype reference**: Lines 2514-2593 (HTML), lines 1492-1572 (CSS), JS lines 3024-3029

```
┌──────────────────────────────────────────────────┐
│ IMPLEMENTATION CHECKLIST (subsection title)       │
│ ┌──────────────────────────────────────────────┐ │
│ │ [□] Create magic link service    ~2h    [▼]  │ │
│ │     No dependencies                          │ │
│ ├──────────────────────────────────────────────┤ │
│ │ [□] Update email templates       ~1h    [▼]  │ │
│ │     Depends on: Task 1                       │ │
│ ├──────────────────────────────────────────────┤ │
│ │ [✓] Write tests and docs         ~2h    [▼]  │ │
│ │     Depends on: Tasks 1-4                    │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [Progress bar: 1/5 tasks completed — 20%]        │
│                                                  │
│ [🤖 Decompose Tasks]                             │
└──────────────────────────────────────────────────┘
```

**Task Item**:
- Layout: `display: flex; align-items: flex-start; gap: var(--space-3)` (12px)
- Padding: `--space-3` (12px) vertical, `--space-4` (16px) horizontal
- Background: `--background-subtle` (#F8F7F5)
- Border: `1px solid var(--border-subtle)` (#F0EEEB)
- Border-radius: `--radius` (10px)
- Gap between items: `--space-2` (8px)
- Hover: `border-color: var(--border)` (#E8E6E3)
- Transition: `all var(--duration-fast)`

**Task Checkbox**:
- Size: `18x18px`
- Border: `2px solid var(--border)` (#E8E6E3)
- Border-radius: `4px`
- `flex-shrink: 0`
- Margin-top: `2px` (align with first line of text)
- Cursor: pointer
- Hover: `border-color: var(--primary)` (#29A386)
- Completed state: `background: var(--primary); border-color: var(--primary)` with white check icon inside

**Task Content**:
- `flex: 1`
- Title: Geist, `text-sm font-medium`, margin-bottom `--space-1` (4px)
- Completed title: `line-through text-muted-foreground`
- Meta row: `display: flex; gap: var(--space-3)` (12px), `text-xs text-muted-foreground`
- Estimate badge: `text-xs text-ai`, format "~Xh"
- Dependency text: `text-xs text-muted-foreground`, format "Depends on: Task X" or "No dependencies"

**Task Expand Button**:
- Size: `24x24px`
- Background: transparent
- Border: none
- Border-radius: `--radius-sm` (6px)
- Icon: 14x14px ChevronDown, color `--foreground-muted`
- Hover: background `--background-muted`, icon color `--foreground`
- Click: reveals task description, acceptance criteria, and code references

**Expanded Task Detail** (new — not in current prototype but specified in spec):

```
│ [□] Create magic link service    ~2h    [▲]  │
│     No dependencies                          │
│     ─────────────────────────────────────── │
│     Description: Create a new magic link...  │
│     Acceptance Criteria:                     │
│     - [ ] Token generation secure            │
│     - [ ] 15 min expiry                      │
│     Code References:                         │
│     • src/auth/email_service.py (Reference)  │
```

- Separator: `1px solid var(--border-subtle)`, margin `--space-2` (8px) top/bottom
- Description: Geist, `text-xs text-muted-foreground`, line-height 1.6
- Acceptance criteria: sub-checklist with smaller checkboxes
- Code references: list with file badges

**Progress Bar** (new):
- Height: `6px`
- Background: `--background-muted` (#F3F2EF)
- Fill: `--primary` (#29A386)
- Border-radius: `--radius-full` (9999px)
- Label below: `text-xs text-muted-foreground`, format "{completed}/{total} tasks completed"
- Margin-top: `--space-3` (12px)

**"Decompose Tasks" Button**:
- Same style as `context-action-btn` (AI primary)
- Icon: Sparkles 14x14px
- Text: "Decompose Tasks"
- Placement: below task list, centered or right-aligned
- Margin-top: `--space-4` (16px)

**States**:

| State | Visual |
|-------|--------|
| Default | Checklist with unchecked items |
| Task completed | Checkbox filled green, title strikethrough |
| Task hover | Border becomes `--border` |
| Task expanded | ChevronDown rotates up, detail section visible |
| Inline editing | Title becomes `<input>`, border-bottom highlight in `--ai` |
| Drag handle visible | On hover, grip dots appear left of checkbox |
| Dragging | Task item gets `--shadow-md` elevation, 2px `--ai-border` outline |
| Empty (no tasks) | "No tasks yet. Click Decompose to generate." centered message |
| Decompose loading | Button text "Decomposing...", spinner, shimmer skeleton for new tasks appearing |
| All tasks complete | Progress bar full, celebration micro-animation (confetti optional) |

**Accessibility**:
- Checklist: `role="list"`, each item `role="listitem"`
- Checkbox: native `<input type="checkbox">` or Radix Checkbox with `aria-label="{task title}"`
- Expand button: `aria-expanded="{true|false}"`, `aria-controls="task-detail-{id}"`
- Progress bar: `role="progressbar"`, `aria-valuenow={completed}`, `aria-valuemin={0}`, `aria-valuemax={total}`, `aria-label="Task completion progress"`
- Drag-and-drop: `aria-grabbed`, `aria-dropeffect` attributes; keyboard reorder with Arrow keys + Space

#### 2.D.3 Ready-to-Use Prompts (existing, enhanced)

**Prototype reference**: Lines 2596-2661 (HTML), lines 1574-1631 (CSS), JS lines 3000-3012

Already implemented in `prompt-block.tsx`. No visual changes needed.

**Enhancement**: Wire the `prompt.content` to come from `Task.ai_prompt` field instead of the current `ContextPrompt` type. The prompt block should display one per task that has an `ai_prompt` set.

---

### 2.E Enhance Context Chat (NEW)

**Prototype reference**: Lines 2664-2699 (HTML), lines 1632-1724 (CSS), JS lines 3031-3077

**Purpose**: Inline conversational interface for refining issue context with AI.

#### Section Container

- Same `context-section` pattern BUT with different styling:
- Background: `--ai-muted` (#EEF3F7) instead of `--background`
- Border: `1px solid var(--ai-border)` (#B8CCDB)
- Icon: MessageSquare 16x16px
- Title: "Enhance Context"

#### Chat Messages Area

```
┌──────────────────────────────────────────────────┐
│ [Enhance Context header]                         │
│ ┌──────────────────────────────────────────────┐ │
│ │ [AI]  I've compiled the context...           │ │
│ │       • Add more code snippets              │ │
│ │       • Expand on technical requirements     │ │
│ │                                              │ │
│ │ [You] Can you add API contract details?      │ │
│ │                                              │ │
│ │ [AI]  I've added more details about...       │ │
│ └──────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────┐ │
│ │ [Ask to enhance context...          ] [Send] │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Messages Container**:
- Layout: `display: flex; flex-direction: column; gap: var(--space-3)` (12px)
- `max-height: 300px`
- `overflow-y: auto`
- Scroll behavior: smooth scroll to bottom on new message

**Chat Message**:
- Layout: `display: flex; gap: var(--space-3)` (12px)

**Chat Avatar**:
- Size: `28x28px`
- Border-radius: `50%` (`rounded-full`)
- AI avatar: background `bg-ai`, white text "AI", `text-xs font-semibold`
- User avatar: background `bg-muted`, text `text-muted-foreground`, user initials

**Chat Content Bubble**:
- `flex: 1`
- Padding: `--space-3` (12px) vertical, `--space-4` (16px) horizontal
- Background: `bg-background` (#FDFCFA) — white bubble on AI-muted section bg
- Border-radius: `rounded` (10px)
- Font: Geist, `text-sm`, line-height 1.6
- **AI messages**: `text-sm italic` (AI voice uses italic per design system)
- Lists inside: margin `--space-2` top, `--space-4` left indent

**Chat Input Container**:
- Layout: `display: flex; gap: var(--space-2)` (8px)
- Margin-top: `--space-4` (16px)

**Chat Input Field**:
- `flex: 1`
- Padding: `--space-3` (12px) vertical, `--space-4` (16px) horizontal
- Background: `--background` (#FDFCFA)
- Border: `1px solid var(--border)` (#E8E6E3)
- Border-radius: `--radius` (10px)
- Font: Geist, `text-sm text-foreground`
- Placeholder: "Ask to enhance context..."
- Focus: `outline: none; border-color: var(--primary)` (#29A386) — uses primary ring, consistent with Input component
- Focus ring: `focus-visible:ring-2 focus-visible:ring-primary/30`

**Send Button**:
- Size: `40x40px`
- Background: `--ai` (#6B8FAD)
- Border: none
- Border-radius: `--radius` (10px)
- Icon: 16x16px Send icon, white
- Hover: `--ai-hover` (#5A7D9B)
- Disabled: `opacity: 0.5` when input is empty

**States**:

| State | Visual |
|-------|--------|
| Default | AI welcome message visible, input empty |
| Typing | Input has text, send button enabled |
| Sending | Send button shows spinner, input disabled |
| AI responding | Typing indicator (3 dots animation) in AI bubble |
| Message received | New message appended, scroll to bottom |
| Error | Error message in red bubble: "Failed to get response. Try again." |
| Empty (initial) | Single AI welcome message with suggestion list |

**Accessibility**:
- Messages region: `role="log"`, `aria-label="Chat messages"`, `aria-live="polite"`
- Input: `aria-label="Type a message to enhance context"`
- Send button: `aria-label="Send message"`, `aria-disabled` when empty
- Each message: timestamp available to screen readers

---

### 2.F Clone Context Panel (Popover)

**Replaces**: The original "Copy All Context" button (v1.0). Inspired by GitHub's green "Code" clone button.

**Purpose**: Export full issue context in multiple formats for use with Claude Code (AI coding tool).

#### 2.F.1 Trigger Button

**Placement**: In AI Context Tab header, replacing the "Copy All Context" button.

```
┌─────────────────────────────────────────────────────────────┐
│ [Sparkles] Full Context for AI Implementation   [Clone Context] [Regenerate] │
└─────────────────────────────────────────────────────────────┘
```

| Property | Value | Tailwind |
|----------|-------|----------|
| Background | `--ai` (#6B8FAD) | `bg-ai` |
| Text | White, 11px, medium | `text-white text-xs font-medium` |
| Icon | 14px Terminal (Lucide) | `size-3.5` |
| Padding | 8px 16px | `px-4 py-2` |
| Height | 32px | `h-8` |
| Radius | 10px (squircle) | `rounded-[10px]` |
| Hover | Scale 102%, bg `--ai-hover` | `hover:bg-ai/85 hover:scale-[1.02] hover:shadow-md` |
| Active | Scale 100% | `active:scale-100` |
| Focus | 3px ai ring at 30% | `focus-visible:ring-2 focus-visible:ring-ai/30` |
| Gap icon-to-text | 8px | `gap-2` |

**Why "Clone Context"**: The word "Clone" establishes the GitHub mental model. The Terminal icon signals developer tooling / CLI use. Distinct from section-level "Copy" buttons.

**States**:

| State | Visual |
|-------|--------|
| Default | Terminal icon + "Clone Context" |
| Popover open | Button stays pressed (bg `--ai-hover`, scale 100%) |
| Disabled (no context) | opacity 0.5, pointer-events none |

#### 2.F.2 Popover Layout

```
┌────────────────────────────────────────────────┐
│ Clone Context                            [X]   │  ← Header (40px)
├────────────────────────────────────────────────┤
│ [Markdown] [Claude Code] [Task List]           │  ← Tabs (36px)
├────────────────────────────────────────────────┤
│ Complete issue context as structured markdown   │  ← Description
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │ # PS-201: Simplify Password Reset       │  │  ← Dark preview
│  │ ## Summary                              │  │     (max 280px, scroll)
│  │ Reduce password reset from 5 steps...   │  │
│  │ ...                                     │  │
│  └──────────────────────────────────────────┘  │
│                                                │
├────────────────────────────────────────────────┤
│ 4 issues · 3 docs · 8 files · 5 tasks  [Copy] │  ← Footer (44px)
└────────────────────────────────────────────────┘
```

| Property | Value | Tailwind |
|----------|-------|----------|
| Width | 420px | `w-[420px]` |
| Background | `--background` (#FDFCFA) | `bg-background` |
| Border | 1px solid `--border` | `border border-border` |
| Radius | 14px | `rounded-[14px]` |
| Shadow | `--shadow-md` | `shadow-md` |
| Padding | 0 (internal sections manage) | `p-0` |
| Align | end (right-aligned to trigger) | `align="end"` |
| Side offset | 8px | `sideOffset={8}` |

#### 2.F.3 Tab Navigation

Three tabs using shadcn/ui `Tabs` (Radix TabsPrimitive):

| Tab | Icon (12px) | Description |
|-----|-------------|-------------|
| Markdown | FileText | "Complete issue context as structured markdown" |
| Claude Code | Terminal | "Optimized prompt for Claude Code with context sections" |
| Task List | ListChecks | "Ordered implementation tasks with individual prompts" |

| Property | Value | Tailwind |
|----------|-------|----------|
| Tab padding | 8px 12px | `px-3 py-2` |
| Tab font | 11px, medium | `text-xs font-medium` |
| Active color | `--ai` (#6B8FAD) | `text-ai` |
| Active indicator | 2px bottom border | `border-b-2 border-ai` |
| Inactive color | `--foreground-muted` | `text-muted-foreground` |
| Inactive hover | `--foreground` | `hover:text-foreground` |

#### 2.F.4 Preview Area

| Property | Value | Tailwind |
|----------|-------|----------|
| Background | `#1E1E1E` (VS Code dark) | `bg-[#1E1E1E]` |
| Text | #D4D4D4 | `text-[#D4D4D4]` |
| Font | Geist Mono, 12px | `font-mono text-xs` |
| Line height | 1.6 | `leading-relaxed` |
| White space | pre-wrap | `whitespace-pre-wrap` |
| Max-height | 280px | `max-h-[280px]` |
| Overflow | vertical scroll | `overflow-y-auto` |
| Margin | 0 16px | `mx-4` |
| Padding | 16px | `p-4` |
| Radius | 10px | `rounded-[10px]` |

**Content formats**: See spec section 7.3 for Markdown format. Claude Code format uses `# Context / # Tasks / # Constraints / # Acceptance Criteria / # Files` structure. Task List format shows each task with its `ai_prompt` separated by `---`.

#### 2.F.5 Footer

| Property | Value | Tailwind |
|----------|-------|----------|
| Padding | 12px 16px | `px-4 py-3` |
| Border-top | 1px solid `--border-subtle` | `border-t border-border/60` |
| Layout | flex, space-between | `flex items-center justify-between` |

**Stats**: `<count> <label>` separated by `·`. Count uses `font-semibold text-ai`, label uses `text-xs text-muted-foreground`.

**Copy button state machine**:

| State | Icon | Label | Background | Duration |
|-------|------|-------|------------|----------|
| Default | Copy | "Copy" | `--ai` | -- |
| Copying | Spinner | "Copying..." | `--ai` | Until clipboard resolves |
| Copied | Check | "Copied!" | `--primary` (#29A386) | 1.5s then revert |
| Failed | AlertCircle | "Failed" | `--destructive` | 3s then revert |

**Why green for "Copied!"**: Switching from dusty blue to teal-green provides unmistakable visual confirmation without reading the label.

#### 2.F.6 Responsive Behavior

| Breakpoint | Behavior |
|------------|----------|
| >= 768px | Full 420px popover |
| 640-767px | 360px width, preview max-height 240px |
| < 640px | Bottom sheet (slide up, top-only 14px radius, max-height 70vh) |

#### 2.F.7 Accessibility

- Trigger: `aria-haspopup="dialog"`, `aria-expanded`, `aria-controls="clone-context-panel"`
- Popover: Focus trap (Radix handles), focus returns to trigger on close
- Tabs: `role="tablist"` / `role="tab"` / `role="tabpanel"`
- Preview: `role="region"`, `aria-label="Content preview"`
- Copy feedback: `aria-live="polite"` announces "Context copied to clipboard"
- Stats: `aria-label="{count} {label}"` per stat

---

### 2.G Issue Form Additions

**Not in prototype** — specified in feature spec section 6.3.

#### 2.G.1 Acceptance Criteria Checklist

**Location**: Issue detail Description tab, below existing content sections.

```
┌──────────────────────────────────────────────────┐
│ Acceptance Criteria                              │
│ ┌──────────────────────────────────────────────┐ │
│ │ [□] Password reset completes in 3 steps      │ │
│ │ [□] Clear progress indicator                 │ │
│ │ [□] Error messages are actionable            │ │
│ │ [□] Magic link expires after 15 minutes      │ │
│ │ [□] User can resend link without restart     │ │
│ │ [+ Add criterion]                            │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Container**:
- Follows `document-section` pattern from existing issue detail
- Title: Geist, `text-xl font-semibold` (20px), margin-bottom `--space-4`

**Checklist Items**:
- Use existing Checkbox primitive from `components/ui/checkbox.tsx`
- Each item: `<Checkbox>` + inline editable text input
- Text: Geist, `text-sm`, padding `--space-2` vertical
- Hover: reveal drag handle (left) and delete button (right)
- Delete button: X icon, 20x20px, color `--foreground-muted`, hover `--destructive`

**Add Button**:
- Text: "+ Add criterion"
- Style: `text-sm text-muted-foreground hover:text-foreground`, no border/bg
- Click: appends empty text input, auto-focuses

**Interactions**:
- Click text to edit inline (focus selects all)
- Enter: save and add new item below
- Backspace on empty: delete item, focus previous
- Drag handle: reorder via drag-and-drop
- 2s debounce auto-save (consistent with issue title/description)

**States**:

| State | Visual |
|-------|--------|
| View mode | Checkbox + read-only text |
| Edit mode | Checkbox + `<input>` with border-bottom `--ai` |
| Saving | Brief fade animation |
| Empty | "No acceptance criteria defined. Click + to add." |

**Accessibility**:
- List: `role="list"`, `aria-label="Acceptance criteria"`
- Each item: `role="listitem"`
- Add button: `aria-label="Add acceptance criterion"`
- Drag: `aria-grabbed`, keyboard reorder with Ctrl+Arrow keys

#### 2.G.2 Technical Requirements Text Area

**Location**: Issue detail Description tab, below Acceptance Criteria.

```
┌──────────────────────────────────────────────────┐
│ Technical Requirements                           │
│ ┌──────────────────────────────────────────────┐ │
│ │ - Follow existing auth patterns              │ │
│ │ - Use Supabase Auth magic link API           │ │
│ │ - Maintain backwards compatibility           │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

- Title: same as Acceptance Criteria section title
- Use existing `Textarea` primitive from `components/ui/textarea.tsx`
- Styling: `min-h-[100px]`, auto-grow, Geist `text-sm`, line-height 1.7
- Placeholder: "Technical constraints, patterns to follow, non-functional requirements..."
- 2s debounce auto-save
- Save status indicator: reuse existing `SaveStatus` component pattern

---

## 3. Interaction Patterns

### 3.1 Tab Switching

**From prototype JS** (lines 2817-2834):
- Click tab button → remove `active` class from all tabs and tab-content
- Add `active` to clicked tab and corresponding `#tab-{id}` content
- AI Context tab: triggers `drawTaskDependencyGraph()` after 100ms delay
- No animation between tabs — instant swap (`display: none` → `display: block`)

**React implementation**: Use controlled state. When AI Context tab activates, trigger canvas draw via `useEffect`. Use `requestAnimationFrame` for canvas rendering.

### 3.2 Task Checkbox Toggle

**From prototype JS** (lines 3024-3029):
1. Click checkbox
2. Toggle `.completed` class on parent `.task-item`
3. Visual: checkbox fills green, title gets strikethrough

**React implementation**:
1. Click checkbox → `TaskStore.updateStatus(taskId, newStatus)`
2. Optimistic update: immediately toggle UI
3. API call: `PATCH /tasks/{taskId}/status` with `{ status: 'done' | 'todo' }`
4. On error: rollback to previous state, show toast error
5. On success: invalidate task queries

### 3.3 Copy Button Feedback

**From prototype JS** (lines 2917-2929, 2932-2941):
1. Click copy button
2. `navigator.clipboard.writeText(text)`
3. On success: button text changes to "Copied!" (or icon changes to Check)
4. Small copy buttons: `background: --primary; color: white` for 1.5s
5. Large "Copy All": text swap for 1.5s
6. After 1.5s: revert to original state

**React implementation**: Use existing `useCopyFeedback` hook. Returns `{ copied: boolean, handleCopy: (fn) => void }`.

### 3.4 Drag-and-Drop Task Reordering

**Not in prototype** — specified in feature spec (Phase 4).

1. Hover over task item → drag handle (grip dots) appears left of checkbox
2. Mouse down on handle → task item elevates (`--shadow-md`), border `2px solid --ai-border`
3. Drag vertically → other items shift with smooth animation (`200ms ease-out`)
4. Drop → API call `PUT /tasks/reorder` with new `task_ids` order
5. Optimistic: UI reorders immediately, rollback on error

**Keyboard alternative**: Focus task → Ctrl+Up/Down to move, Enter to confirm.

### 3.5 Inline Task Editing

**Not in prototype** — specified in feature spec (Phase 4).

1. Click task title → transforms to `<input>` element
2. Input: inherits same font styling, border-bottom `2px solid --ai`
3. Enter or blur: save via `PATCH /tasks/{taskId}` with `{ title: newTitle }`
4. Escape: cancel edit, revert to original
5. 2s debounce for auto-save (consistent with issue title)

### 3.6 Chat Send/Receive Flow

**From prototype JS** (lines 3031-3077):
1. User types in chat input
2. Press Enter or click Send button
3. User message appended immediately (client-side)
4. Input cleared
5. After 1s delay (simulated): AI response appended
6. Messages container scrolls to bottom

**React implementation**:
1. User submits message → add to local messages array (optimistic)
2. Call PilotSpace SSE endpoint with context refinement message
3. Stream AI response tokens into a new AI message bubble
4. On stream complete: message finalized
5. Auto-scroll with `scrollIntoView({ behavior: 'smooth' })`

### 3.7 Decompose Loading State

1. Click "Decompose Tasks" button
2. Button text: "Decomposing..." with spinner
3. Button disabled
4. Skeleton placeholders appear in checklist area (3-5 shimmer rows)
5. As tasks arrive (from API response): skeleton rows replace with real task items, staggered animation
6. When complete: progress bar updates, button reverts to "Decompose Tasks"
7. If tasks already exist: show confirmation dialog "This will replace existing AI-generated tasks. Continue?"

### 3.8 Section Collapse/Expand

Each context subsection (File Tree, Code Snippets, Git References) has collapsible headers:
1. Click subsection title → toggle child content visibility
2. Chevron icon rotates (right → down) with `200ms ease-out` rotation
3. Content uses `max-height` transition for smooth expand/collapse
4. Collapsed state persists per session (not across page loads)

### 3.9 Empty States

| Section | Empty State Message | Action |
|---------|---------------------|--------|
| Full AI Context tab | Sparkles icon (40% opacity), "No AI Context Yet", "Generate AI-powered context..." description, "Generate Context" CTA button | Click generates |
| Context Summary | Skeleton card with shimmer | Auto-generates |
| Related Issues | *Hidden entirely when empty* | -- |
| Related Documents | *Hidden entirely when empty* | -- |
| Codebase Context - File Tree | "No relevant files identified" centered text, muted | Regenerate |
| Codebase Context - Code Snippets | "No code snippets available" centered text, muted | Regenerate |
| Codebase Context - Git Refs | "No git references found" centered text, muted | Regenerate |
| Task Checklist | "No tasks yet. Click 'Decompose Tasks' to generate implementation steps." centered, with Sparkles icon | Decompose button |
| Prompts | *Hidden when no tasks have ai_prompt* | -- |
| Chat | Single AI welcome message: "I've compiled the context for this issue..." with suggestion bullets | Type message |
| Acceptance Criteria | "No acceptance criteria defined." with "+ Add" button | Click to add |
| Technical Requirements | Empty textarea with placeholder | Type to add |

---

## 4. Layout & Composition

### 4.1 AI Context Tab Overall Stack

The AI Context tab renders within the `document-area` container (max-width 800px, centered). Components stack vertically:

```
┌──────────────────────────────────────────────────────────┐
│ AI Context Header (sticky? see 4.3)                      │
│ ─ border-bottom ─────────────────────────────────────── │
│                                                          │
│ Context Summary Card                        (mb: 24px)   │
│                                                          │
│ ── Separator ──────────────────────────────────────────  │
│                                                          │
│ Related Context Section (border box)        (mb: 32px)   │
│   ├── Related Issues subsection                          │
│   └── Related Documents subsection                       │
│                                                          │
│ ── Separator ──────────────────────────────────────────  │
│                                                          │
│ Codebase Context Section (border box)       (mb: 32px)   │
│   ├── Relevant Files (file tree)                         │
│   ├── Key Code Sections (snippets)                       │
│   └── Git References                                     │
│                                                          │
│ ── Separator ──────────────────────────────────────────  │
│                                                          │
│ AI Tasks Section (border box)               (mb: 32px)   │
│   ├── Task Dependencies (canvas graph)                   │
│   ├── Implementation Checklist                           │
│   ├── Progress Bar                                       │
│   ├── Decompose Tasks Button                             │
│   └── Ready-to-Use Prompts                               │
│                                                          │
│ ── Separator ──────────────────────────────────────────  │
│                                                          │
│ Enhance Context Chat (AI-muted bg box)      (mb: 0)     │
│   ├── Chat Messages (max-height 300px, scrollable)       │
│   └── Chat Input + Send                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Section Spacing

| Between Elements | Spacing | CSS Token |
|------------------|---------|-----------|
| Header → Summary Card | `--space-6` (24px) | margin-bottom on header |
| Summary Card → next section | `--space-6` (24px) | margin-bottom on card |
| Section → Section | `--space-8` (32px) | context-section margin-bottom |
| Subsection → Subsection | `--space-5` (20px) | context-subsection margin-bottom |
| Within section (items) | `--space-3` (12px) | context-items gap |
| Section header → content | `--space-5` (20px) | context-section-header margin-bottom |
| Subsection title → content | `--space-3` (12px) | margin-bottom on subsection title |

### 4.3 Scroll Behavior

- The entire AI Context tab scrolls within `ScrollArea` (existing — see `ai-context-tab.tsx` line 156)
- The header is NOT sticky (it scrolls with content) — consistent with current implementation
- Chat messages area has independent scroll: `max-height: 300px; overflow-y: auto`
- Code snippets have `overflow-x: auto` for horizontal scroll on long lines
- The outer document-area already has `overflow-y: auto`

### 4.4 Maximum Heights / Overflow

| Element | Max Height | Overflow Behavior |
|---------|------------|-------------------|
| AI Context tab (total) | Fills available height via ScrollArea | Vertical scroll |
| Chat messages | `300px` | Vertical scroll, auto-scroll to bottom on new message |
| Code snippet content | No max-height | Horizontal scroll (`overflow-x: auto`) |
| Task dependency graph | Fixed `200px` | Canvas clips content |
| File tree | No max-height (collapses instead) | Folder collapse/expand controls height |
| Prompt content (expanded) | No max-height | Full content shown |

### 4.5 Responsive Behavior

| Breakpoint | Changes |
|------------|---------|
| >= 768px (default) | Full layout as specified |
| < 768px | Header buttons stack vertically. Context summary card: icon hidden, full-width text. Stats wrap to 2x2 grid. |
| < 640px | File tree: truncate paths. Code snippets: reduce padding. Chat input: send button becomes icon-only. |
| < 480px | Minimal padding `--space-3`. Section titles reduce to `text-sm`. Graph height reduces to 150px. |

---

## 5. Color Mapping

### 5.1 Prototype → Production Design System Mapping

The prototype uses hardcoded hex colors. The production system uses **opacity-based tokens** for AI and primary colors.
This table shows how prototype values translate to production Tailwind classes.

| Prototype CSS (reference only) | Production Token | Tailwind Class |
|-------------------------------|-----------------|----------------|
| `#FDFCFA` (background) | `--background` `#FDFCFA` | `bg-background` |
| `#F8F7F5` (background-subtle) | `--background-subtle` `#F7F5F2` | `bg-muted/50` |
| `#F3F2EF` (background-muted) | `--background-muted` (via `bg-muted`) | `bg-muted` |
| `#1A1918` (foreground) | `--foreground` `#171717` | `text-foreground` |
| `#6B6966` (foreground-muted) | `--foreground-muted` `#737373` | `text-muted-foreground` |
| `#E8E6E3` (border) | `--border` `#E5E2DD` | `border-border` |
| `#F0EEEB` (border-subtle) | `--border-subtle` `#EBE8E4` | `border-border/60` |
| `#6B8FAD` (ai) | `--ai` `#6B8FAD` | `text-ai` / `bg-ai` |
| `#5A7D9B` (ai-hover) | Derived | `hover:bg-ai/85` |
| `#EEF3F7` (ai-muted) | `--ai-muted` = `#6B8FAD15` | `bg-ai/[0.08]` |
| `#B8CCDB` (ai-border) | `--ai-border` = `#6B8FAD30` | `border-ai/20` |
| `#29A386` (primary) | `--primary` `#29A386` | `bg-primary` / `text-primary` |
| `#238F75` (primary-hover) | `--primary-hover` `#238F74` | `hover:bg-primary/85` |
| `#E8F5F1` (primary-muted) | `--primary-muted` = `#29A38615` | `bg-primary/[0.08]` |
| `#D9534F` (destructive) | `--destructive` `#D9534F` | `text-destructive` |
| `#D9853F` (warning) | `--warning` `#D9853F` | `text-amber-600` |
| `#FEE8E8` (blocks bg) | Derived | `bg-destructive/10` |
| `#FEF3E8` (warning bg) | Derived | `bg-amber-50` |
| `#E8F0F5` (gradient end) | Not tokenized | Inline gradient stop only |
| `#1E1E1E` (code dark bg) | Not tokenized | `bg-[#1E1E1E]` (VS Code theme) |
| `#D4D4D4` (code text) | Not tokenized | `text-[#D4D4D4]` |

### 5.2 New Tokens Needed

**None.** All colors compose from existing tokens with opacity modifiers. Non-tokenized inline values:

- `#E8F0F5` — context summary card gradient end (one-time inline usage)
- `#1E1E1E` / `#D4D4D4` — VS Code dark code block theme (standard, no tokenization needed)

### 5.3 Visual Texture Compliance

The prototype omits these production design system textures. Implementation MUST include:

| Texture | Spec | Where to Apply |
|---------|------|----------------|
| **Noise overlay** | 2% opacity, multiply blend, subtle grain | AI Context tab background |
| **Frosted glass** | 20px blur, 180% saturation, 72% bg opacity | Confirmation modals (decompose replace) |
| **Warm-tinted shadows** | HSL(30, 10%, 10%) base | All card elevations, hover states |

### 5.4 Dark Mode Considerations

Dark mode values from production design system:

| Light Token | Dark Mode | Notes |
|-------------|-----------|-------|
| `--background` #FDFCFA | `#1A1A1A` | Per design system |
| `--background-subtle` #F7F5F2 | `#1F1F1F` | |
| `--foreground` #171717 | `#EDEDED` | |
| `--foreground-muted` #737373 | `#999999` | |
| `--border` #E5E2DD | `#2E2E2E` | |
| `--ai-muted` (15% opacity) | Automatically adapts | Opacity tokens work in both modes |
| `--primary-muted` (15% opacity) | Automatically adapts | |
| Code block `#1E1E1E` | `#1E1E1E` | Same (already dark) |
| Code text `#D4D4D4` | `#D4D4D4` | Same |

---

## 6. Wireframe Descriptions

### 6.1 AI Context Tab — Fully Populated

```
╔══════════════════════════════════════════════════════════════╗
║ [Sparkles] Full Context for AI Implementation    [Copy All] [Regenerate] ║
║ ───────────────────────────────────────────────────────────── ║
║                                                              ║
║ ┌─ gradient card ──────────────────────────────────────────┐ ║
║ │ [FileText]  PS-201: Simplify Password Reset Flow         │ ║
║ │ 48x48 icon  Reduce password reset from 5 steps to 2-3   │ ║
║ │             using magic links. Target 30% improvement.   │ ║
║ │             [4 Issues] [3 Docs] [8 Files] [5 Tasks]     │ ║
║ └──────────────────────────────────────────────────────────┘ ║
║                                                              ║
║ ┌─ Related Context ────────────────────────────── [Copy] ──┐ ║
║ │ RELATED ISSUES                                           │ ║
║ │ ┌ [BLOCKS]  PS-202  Handle social login errors  [InProg]┐│ ║
║ │ │ OAuth error handling with retry logic...              ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ [RELATES] PS-203  Extend session timeout     [Done]  ┐│ ║
║ │ │ Configurable session duration...                     ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ [BLOCKED BY] PS-198 Email rate limiting     [InProg] ┐│ ║
║ │ │ Rate limiting for password reset emails...           ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │                                                          │ ║
║ │ RELATED DOCUMENTS                                        │ ║
║ │ ┌ [NOTE]  Auth Refactor                                ┐│ ║
║ │ │ Planning notes for authentication system overhaul... ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ [ADR]   ADR-0015: Error Handling in Auth Flows      ┐│ ║
║ │ │ Decision record for standardizing error messages...  ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ [SPEC]  Auth Module Spec v2                          ┐│ ║
║ │ │ Technical specification for the auth module...       ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ └──────────────────────────────────────────────────────────┘ ║
║                                                              ║
║ ┌─ Codebase Context ───────────────────────────── [Copy] ──┐ ║
║ │ RELEVANT FILES                                           │ ║
║ │ 📁 src/auth/                                             │ ║
║ │   📄 password_reset.py               [Modified]          │ ║
║ │   📄 magic_link.py                   [New]               │ ║
║ │   📄 email_service.py                [Reference]         │ ║
║ │ 📁 src/components/auth/                                  │ ║
║ │   📄 PasswordResetForm.tsx            [Modified]          │ ║
║ │   📄 MagicLinkFlow.tsx                [New]               │ ║
║ │ 📁 tests/auth/                                           │ ║
║ │   📄 test_password_reset.py           [Modified]          │ ║
║ │                                                          │ ║
║ │ KEY CODE SECTIONS                                        │ ║
║ │ ┌ password_reset.py:45-62 ──────────────────── [Copy] ─┐│ ║
║ │ │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓││ ║
║ │ │▓ async def initiate_password_reset(...):             ▓││ ║
║ │ │▓     user = await get_user_by_email(email)           ▓││ ║
║ │ │▓     code = generate_verification_code()             ▓││ ║
║ │ │▓▓▓▓▓▓▓▓▓▓▓▓ (dark bg code block) ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ PasswordResetForm.tsx:28-45 ─────────────── [Copy] ─┐│ ║
║ │ │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓││ ║
║ │ │▓ const PasswordResetForm: React.FC = () => {        ▓││ ║
║ │ │▓   const [step, setStep] = useState(1);             ▓││ ║
║ │ │▓▓▓▓▓▓▓▓▓▓▓▓ (dark bg code block) ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │                                                          │ ║
║ │ GIT REFERENCES                                           │ ║
║ │ [PR icon]     #142 - Add magic link authentication       │ ║
║ │               Draft · Updated 2 days ago                 │ ║
║ │ [Commit icon] feat(auth): initial password reset refactor│ ║
║ │               abc1234 · 3 days ago                       │ ║
║ │ [Branch icon] feature/ps-201-password-reset              │ ║
║ │               Active branch · 5 commits ahead            │ ║
║ └──────────────────────────────────────────────────────────┘ ║
║                                                              ║
║ ┌─ AI Tasks ───────────────────────────────────── [Copy] ──┐ ║
║ │ TASK DEPENDENCIES                                        │ ║
║ │ ┌──────────────────────────────────────────────────────┐│ ║
║ │ │       ╭── [2] ── [4] ──╮                             ││ ║
║ │ │  [1] ─┤                ├── [5]                       ││ ║
║ │ │       ╰── [3] ─────────╯                             ││ ║
║ │ │  (canvas DAG with colored nodes)                     ││ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │                                                          │ ║
║ │ IMPLEMENTATION CHECKLIST                                 │ ║
║ │ [□] Create magic link service        ~2h          [▼]   │ ║
║ │     No dependencies                                      │ ║
║ │ [□] Update email templates           ~1h          [▼]   │ ║
║ │     Depends on: Task 1                                   │ ║
║ │ [□] Simplify frontend flow           ~3h          [▼]   │ ║
║ │     Depends on: Task 1                                   │ ║
║ │ [□] Add retry logic for email        ~1h          [▼]   │ ║
║ │     Depends on: Task 2                                   │ ║
║ │ [□] Write tests and documentation    ~2h          [▼]   │ ║
║ │     Depends on: Tasks 1-4                                │ ║
║ │                                                          │ ║
║ │ ████░░░░░░░░░░░░░░░░  0/5 completed                     │ ║
║ │                                                          │ ║
║ │               [🤖 Decompose Tasks]                       │ ║
║ │                                                          │ ║
║ │ READY-TO-USE PROMPTS                                     │ ║
║ │ ┌ [▸] Task 1: Create Magic Link Service        [Copy] ┐│ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ │ ┌ [▸] Task 3: Simplify Frontend Flow           [Copy] ┐│ ║
║ │ └──────────────────────────────────────────────────────┘│ ║
║ └──────────────────────────────────────────────────────────┘ ║
║                                                              ║
║ ┌─ Enhance Context (AI-muted bg) ──────────────────────────┐ ║
║ │ [AI] I've compiled the context for PS-201...             │ ║
║ │      · Add more code snippets from related files         │ ║
║ │      · Expand on technical requirements                  │ ║
║ │      · Include API contract details                      │ ║
║ │      · Add testing strategy recommendations              │ ║
║ │                                                          │ ║
║ │ [Ask to enhance context...                    ] [Send]   │ ║
║ └──────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════╝
```

### 6.2 AI Context Tab — Empty State (No Context Generated)

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                                                              ║
║                                                              ║
║                    [Sparkles icon, 40% opacity]              ║
║                                                              ║
║                     No AI Context Yet                        ║
║                                                              ║
║           Generate AI-powered context to get                 ║
║           related issues, documentation references,          ║
║           implementation tasks, and ready-to-use             ║
║           Claude Code prompts.                               ║
║                                                              ║
║                  [✨ Generate Context]                       ║
║                                                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

- Vertically and horizontally centered
- Sparkles icon: 64x64px (size-16), color `--ai` at 40% opacity
- Title: `text-lg font-medium`, `--foreground`
- Description: `text-sm text-muted-foreground`, max-width 448px (md), centered
- Button: Primary variant, large size, Sparkles icon + "Generate Context"

### 6.3 AI Context Tab — Loading State (Context Being Generated)

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   [✓] Analyzing issue content...                  ✓ Done     ║
║   [⟳] Finding related issues...                  ⟳ Loading   ║
║   [○] Discovering relevant documents...           ○ Pending   ║
║   [○] Identifying codebase context...             ○ Pending   ║
║   [○] Generating implementation tasks...          ○ Pending   ║
║   [○] Creating Claude Code prompts...             ○ Pending   ║
║                                                              ║
║   ████████████░░░░░░░░░░░░░░░░  33%                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

- Uses existing `AIContextStreaming` component
- Phase list with status icons: Check (done, green), Spinner (loading, AI blue), Circle (pending, muted)
- Progress bar below phases
- Each phase transitions smoothly when status changes

### 6.4 Task Being Edited Inline

```
┌──────────────────────────────────────────────────┐
│ [□] ┃Create magic link service with token gen┃  [▼] │
│      ── border-bottom: 2px solid --ai ──           │
│     ~2h · No dependencies                          │
└──────────────────────────────────────────────────┘
```

- Task title replaced with `<input>` element
- Same font size/weight as display title
- Bottom border: `2px solid --ai` (#6B8FAD) indicating edit mode
- No outer border change (subtle edit state)
- Other tasks remain in view mode
- Auto-select text on focus

### 6.5 Decompose In Progress

```
╔══════════════════════════════════════════════════════════════╗
║ ┌─ AI Tasks ───────────────────────────────────── [Copy] ──┐ ║
║ │ IMPLEMENTATION CHECKLIST                                 │ ║
║ │ ┌─────────────────────────── shimmer ────────────────┐  │ ║
║ │ │ ████████████████████████████████████████████        │  │ ║
║ │ │ ████████████░░░░░░░░                               │  │ ║
║ │ └───────────────────────────────────────────────────┘  │ ║
║ │ ┌─────────────────────── shimmer ────────────────────┐  │ ║
║ │ │ ████████████████████████████████████                │  │ ║
║ │ │ ████████████████████░░░░                           │  │ ║
║ │ └───────────────────────────────────────────────────┘  │ ║
║ │ ┌─────────────────── shimmer ────────────────────────┐  │ ║
║ │ │ ██████████████████████████████                      │  │ ║
║ │ │ ████████░░░░░░░░░░░                                │  │ ║
║ │ └───────────────────────────────────────────────────┘  │ ║
║ │                                                          │ ║
║ │            [⟳ Decomposing...] (disabled)                 │ ║
║ │                                                          │ ║
║ └──────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════╝
```

- 3-5 skeleton rows with shimmer animation
- Each skeleton: task item shape (checkbox placeholder + 2 text lines)
- Shimmer: `linear-gradient` sweep animation, `1.5s infinite`
- "Decomposing..." button with spinner icon
- Task graph area shows skeleton rectangle
- Skeleton colors: `--background-muted` base with `--background-subtle` shimmer sweep

---

## Appendix A: Component-to-File Mapping

| Component | File (existing or new) | Status |
|-----------|----------------------|--------|
| AI Context Tab Header | `ai-context-tab.tsx` (enhance header section) | Enhance |
| Context Summary Card | `context-summary-card.tsx` | Exists (no visual change) |
| Codebase Context Section | `codebase-context-section.tsx` (NEW) | New |
| File Tree | `file-tree.tsx` (NEW) | New |
| Code Snippet Card | `code-snippet-card.tsx` (NEW) | New |
| Git References | `git-references.tsx` (NEW) | New |
| AI Tasks Section | `ai-tasks-section.tsx` (enhance) | Enhance |
| Task Dependency Graph | `task-dependency-graph.tsx` (NEW) | New |
| Task Checklist | Within `ai-tasks-section.tsx` (enhance) | Enhance |
| Prompt Block | `prompt-block.tsx` | Exists (no visual change) |
| Enhance Context Chat | `enhance-context-chat.tsx` (NEW) | New |
| Copy All Context Button | Within `ai-context-tab.tsx` header | Enhance |
| Acceptance Criteria | Within issue detail form (NEW sub-component) | New |
| Technical Requirements | Within issue detail form (NEW sub-component) | New |

## Appendix B: shadcn/ui Primitives Used

| Primitive | Usage |
|-----------|-------|
| `Button` | Copy buttons, Regenerate, Decompose, Send |
| `Card` / `CardContent` | Context Summary Card |
| `Checkbox` | Task checklist, Acceptance criteria |
| `ScrollArea` | AI Context tab scroll container |
| `Separator` | Between major sections |
| `Badge` | Relation type, status pills, file badges |
| `Collapsible` | Subsection expand/collapse, prompt blocks |
| `Skeleton` | Loading states |
| `Progress` | Task completion progress bar |
| `Input` | Inline task editing, chat input |
| `Textarea` | Technical requirements |
| `Tooltip` | Button tooltips (copy, expand, etc.) |

## Appendix C: Accessibility Summary

| Requirement | Implementation |
|-------------|---------------|
| **Keyboard Navigation** | All interactive elements focusable via Tab. Checkbox toggle via Space. Expand/collapse via Enter/Space. Chat submit via Enter. |
| **ARIA Roles** | `role="tree"` for file tree, `role="list"` for task checklist, `role="log"` for chat, `role="progressbar"` for completion bar, `role="img"` for canvas graph |
| **ARIA Labels** | All buttons have `aria-label`. Copy buttons announce success via `aria-live="polite"`. Progress bar has `aria-valuenow`/`aria-valuemin`/`aria-valuemax`. |
| **Focus Management** | Inline edit auto-focuses input. Chat auto-scrolls but does not steal focus. Modal confirmations trap focus. |
| **Reduced Motion** | Spinner animations: `motion-safe:animate-spin`. Graph rendering: skip animation. Shimmer: `motion-reduce:animate-none`. |
| **Color Contrast** | All text meets 4.5:1 ratio against backgrounds. Badge text verified against colored backgrounds. Code text (#D4D4D4) on dark (#1E1E1E) = 10.5:1. |
| **Screen Reader** | Canvas graph has text fallback describing dependencies. Empty states provide descriptive text. Status changes announced via live regions. |
