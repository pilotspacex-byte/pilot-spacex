# UI Design Specification: Pilot Space MVP

**Version**: 3.3.0
**Created**: 2026-01-20
**Updated**: 2026-01-22
**Status**: Final - Synced with DD-001 to DD-056 (complete)
**Major Change**: Note Canvas as primary home interface (thought-first workflow)
**Design System**: `/design-system/`
**Additions v3.1**: Rich Note Header, Auto-TOC, Resizable Margin, Progressive Tooltips, AI Confidence Tags, Pinned Notes
**Additions v3.2**: AI-Prioritized Notification Center, Similar Notes with AI Guidance
**Additions v3.3**: Frontend Architecture Decisions (State Management, Virtualization, SSE, Testing)

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [Visual Identity](#visual-identity)
4. [Design Foundation](#design-foundation)
5. [Component Library](#component-library)
6. [Page Layouts](#page-layouts)
7. [Note Canvas (Home Interface)](#note-canvas-home-interface)
8. [AI Collaborative Features](#ai-collaborative-features)
9. [Navigation & Search](#navigation--search)
10. [Interaction Patterns](#interaction-patterns)
11. [Accessibility Requirements](#accessibility-requirements)
12. [Responsive Design](#responsive-design)
13. [Implementation Notes](#implementation-notes)

---

## Overview

### Purpose

This document defines the UI/UX specifications for Pilot Space MVP, an AI-Augmented SDLC Platform. It serves as the authoritative reference for implementing the frontend application.

### Design Goals

| Goal | Description | Metric |
|------|-------------|--------|
| **Thought-First** | Users brainstorm before structuring | Note → Issue conversion rate > 60% |
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

---

## Design Philosophy

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

- ❌ Cold, clinical enterprise software
- ❌ Generic shadcn/ui defaults (Inter, orange accent, pure white)
- ❌ AI as a separate "system" bolted onto the UI
- ❌ Dense, overwhelming information displays

---

## Visual Identity

### Brand Personality

> **Pilot Space feels like a well-designed workspace crafted by people who care about your focus. It's warm without being casual, sophisticated without being cold. AI isn't a feature bolted on—it's a friendly teammate whose suggestions appear naturally in your workflow.**

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

## Design Foundation

### Color System

#### Base Palette (Warm Neutrals)

| Token | Light Mode | Dark Mode | Description |
|-------|------------|-----------|-------------|
| Background | `#FDFCFA` | `#1A1A1A` | Warm off-white / Soft dark |
| Background Subtle | Slightly darker warm | Elevated dark `#1F1F1F` | Secondary surfaces |
| Foreground | `#171717` | `#EDEDED` | Near-black / Soft white |
| Foreground Muted | `#737373` | `#999999` | Secondary text |

#### Primary Accent (Teal-Green)

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#29A386` | Fresh teal-green for primary actions |
| Primary Hover | Darker teal | Hover state |
| Primary Muted | Light tint | Subtle backgrounds |

#### AI Teammate Color (Dusty Blue)

| Token | Value | Usage |
|-------|-------|-------|
| AI | `#6B8FAD` | Calm dusty blue for AI elements |
| AI Muted | Light blue tint | AI annotation backgrounds |
| AI Border | Soft blue | AI element borders |

#### Issue State Colors

| State | Color | Description |
|-------|-------|-------------|
| Backlog | Warm Gray | Unstarted, low priority |
| Todo | Soft Blue | Ready to start |
| In Progress | Amber | Actively being worked |
| In Review | Soft Purple | Awaiting review |
| Done | Teal-Green | Completed (matches primary) |
| Cancelled | Warm Red | Abandoned/rejected |

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
- Use curly quotes (`""`), not straight quotes
- Use proper ellipsis (`…`), not three periods
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

## Component Library

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
| `icon` | 38px | — | — | 18px |
| `icon-sm` | 32px | — | — | 16px |

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

#### Issue Card Anatomy

```
╭──────────────────────────────────────╮
│                                      │
│  ◐ PS-123              ☆ You + AI   │  ← State icon, AI attribution
│                                      │
│  Implement user authentication       │  ← Title (Geist, medium weight)
│  flow for OAuth providers            │
│                                      │
│  ╭────╮ ╭──────────╮                │
│  │bug │ │ frontend │                │  ← Rounded pill badges
│  ╰────╯ ╰──────────╯                │
│                                      │
│  ▰▰▰▱  💬 2  📎 1      ◯◯          │  ← Priority, meta, avatars
│                                      │
╰──────────────────────────────────────╯
```

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

## Page Layouts

### Application Shell

```
╭────────────────────────────────────────────────────────────────╮
│ [Skip to main content]                                         │
├────────────┬───────────────────────────────────────────────────┤
│            │                                                   │
│  SIDEBAR   │  [🔍 Search...  ⌘K]          [+ New] [🔔] [👤]   │
│ (distinct  ├───────────────────────────────────────────────────┤
│  surface)  │                                                   │
│            │                                                   │
│  Workspace │               MAIN CONTENT                        │
│  ─────────│                                                   │
│  🏠 Home   │           (warm off-white background)             │
│  📋 Issues │            (spacious, breathable)                 │
│            │                                                   │
│  Projects  │                                                   │
│  ─────────│                                                   │
│  📁 Alpha  │                                                   │
│  📁 Beta   │                                                   │
│            │                                                   │
├────────────┴───────────────────────────────────────────────────┤
│ [GitHub ↗] [Slack ↗]                    Pilot Space v1.0      │
╰────────────────────────────────────────────────────────────────╯
```

### Sidebar Specifications

| Property | Value |
|----------|-------|
| Width (expanded) | 260px |
| Width (collapsed) | 60px |
| Background | Subtle background color |
| Border | 1px right border |
| Dark Mode | Darker background for distinction |

### Layout Dimensions

| Element | Value |
|---------|-------|
| Header Height | 56px |
| Content Max Width | 1200px |
| Content Padding | 32px |

---

## Note Canvas (Home Interface)

The Note Canvas is the **primary entry point** for Pilot Space. Unlike traditional issue trackers that start with forms, Pilot Space starts with **collaborative thinking**.

### Philosophy

> **"Think first, structure later"** - Users brainstorm with AI in a living document. Issues emerge naturally from refined thoughts, not forced forms.

### Layout Architecture

```
╭─────────────────────────────────────────────────────────────────────────────╮
│ ◀ ▶  Pilot Space                              🔍 Search    [+]  🔔  👤     │
├────────────────┬────────────────────────────────────────────────────────────┤
│                │                                                            │
│  OUTLINE       │  DOCUMENT CANVAS                          MARGIN          │
│  (Tree)        │                                           (AI Notes)      │
│                │                                                            │
│  📄 Notes      │  # Authentication Refactor                     ┌────────┐ │
│  ├─ Auth       │                                                │ ☆ AI   │ │
│  │  Refactor ◀─┼──────────────────────────────────────────────▶│        │ │
│  ├─ API Design │  ┌─────────────────────────────────────────┐  │ Consider│ │
│  └─ Sprint     │  │ We need to rethink how users log in.   │  │ OAuth2  │ │
│     Goals      │  │ Current flow has too many steps...     │  │ PKCE    │ │
│                │  └─────────────────────────────────────────┘  │ flow... │ │
│  📋 Issues     │                      │                        └────────┘ │
│  ├─ PS-123     │                      │ AI thread                         │
│  └─ PS-124     │                      ▼                                   │
│                │  ┌─ You + AI ────────────────────────────┐               │
│  🗂️ Projects   │  │ What specific pain points are users   │               │
│                │  │ experiencing?                         │               │
│                │  │                                       │               │
│                │  │ > Password reset is confusing         │               │
│                │  │ > Social login fails silently         │               │
│                │  │ > Session expires too quickly         │  ┌────────┐  │
│                │  └───────────────────────────────────────┘  │ ☆ AI   │  │
│                │                                              │        │  │
│                │                                              │ 3 issues│  │
│                │                                              │ detected│  │
│                │                                              │         │  │
│                │                                              │ [Review]│  │
│                │                                              └────────┘  │
│                │                                                          │
└────────────────┴──────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Outline Tree (Left Sidebar)

VS Code-inspired tree navigation for workspace content.

| Property | Value |
|----------|-------|
| Width | 220px |
| Background | Subtle background |
| Border | 1px right |
| Font Size | 13px (text-sm) |
| Item Padding | 4px vertical, 8px horizontal |
| Item Hover | Muted background |
| Item Active | Primary 10% background, primary text |

**Content Types:**
- 📄 Notes (primary)
- 📋 Issues (linked from notes)
- 🗂️ Projects
- 📊 Cycles

#### 2. Document Canvas (Center)

| Property | Value |
|----------|-------|
| Max Width | 720px |
| Margin | Auto-centered |
| Padding | 32px |
| Background | Main background |

**Block Properties:**
| Property | Value |
|----------|-------|
| Padding | 16px |
| Margin Bottom | 12px |
| Border Radius | 14px (rounded-lg) |
| Hover | 50% muted background |
| Active | Muted background, small shadow |

**Block Features:**
- Each block is a discrete thought unit
- Blocks can spawn AI discussion threads
- Blocks can be collapsed/expanded
- Blocks link to extracted issues

#### 3. Margin Annotations (Right Side)

| Property | Value |
|----------|-------|
| Width | 200px |
| Padding | 16px |
| Background | AI muted color |
| Border Left | 3px solid AI color |
| Default Opacity | 40% |
| Active/Hover Opacity | 100% |
| Font Size | 11px (text-xs) |

**Visibility Behavior:**
- Active block's margin notes are fully visible
- Other margin notes fade to 40% opacity
- Hover reveals full note
- Click expands to full AI discussion

#### 4. Threaded AI Discussions

```
╭─ You + AI ─────────────────────────────────────────╮
│                                                     │
│  ☆ "What authentication method are you considering?│
│     OAuth2 with PKCE is common for SPAs..."        │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  > We want Google and GitHub OAuth                 │
│  > Also magic link for enterprise users            │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  ☆ "Great choices. For enterprise, consider        │
│     SAML/OIDC in addition to magic links..."       │
│                                                     │
│  [Collapse thread]                         [v1.2]  │
│                                                     │
╰─────────────────────────────────────────────────────╯
```

**Thread Persistence:**
- Threads are saved as part of note history
- Collapsed by default after session
- Expandable to view full discussion
- Version indicator shows thread updates

### Issue Extraction Flow

AI automatically identifies actionable items and wraps them with rainbow-bordered issue boxes.

#### Visual Anatomy

```
╭──────────────────────────────────────────────────────────────────╮
│                                                                  │
│  So the core problems are:                                       │
│                                                                  │
│  1. ╭─🐛 PS-201 Simplify password reset ─╮  ← Rainbow border    │
│     │  UX clarity - password reset...    │                       │
│     ╰────────────────────────────────────╯                       │
│                                                                  │
│  2. ╭─🔧 PS-202 Handle social login errors╮                      │
│     │  Error handling - social login...   │                      │
│     ╰─────────────────────────────────────╯                      │
│                                                                  │
│  3. ╭─⚡ PS-203 Extend session timeout ───╮                      │
│     │  Session management - expires...    │                      │
│     ╰─────────────────────────────────────╯                      │
│                                                                  │
╰──────────────────────────────────────────────────────────────────╯
```

#### Issue Box Specifications

| Property | Value |
|----------|-------|
| Display | Inline-flex |
| Padding | 4px vertical, 8px horizontal |
| Border Radius | 10px |
| Border | 2px rainbow gradient (primary → blue → purple → pink → primary) |
| Hover | Scale 2%, medium shadow |
| New Issue Animation | Rainbow pulse (hue-rotate 30deg over 2s) |

**Issue Box Content:**
- Issue type icon (🐛 bug, 🔧 improvement, ⚡ performance)
- Issue ID (e.g., PS-201)
- Shortened title (truncated to ~30 chars)
- Source text wrapped inside (visible)

#### Hover Modal Card

```
╭─────────────────────────────────────────────────────╮
│                                                     │
│  🐛 PS-201                              [Open ↗]   │
│  Simplify password reset flow                       │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  State: 🔵 Todo          Priority: ▰▰▱▱ Medium    │
│  Assignee: Unassigned    Due: Not set              │
│                                                     │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  Source: Auth Refactor Note                        │
│  Created: You + AI • 2 hours ago                   │
│                                                     │
│  ╭─────────────────────────────────────────────╮   │
│  │ bug │ ux │ authentication │                 │   │
│  ╰─────────────────────────────────────────────╯   │
│                                                     │
╰─────────────────────────────────────────────────────╯
```

#### 5. Rich Note Header

Displays metadata above note title:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│  📄 Auth Refactor                                     [≡] [⋯]  │
│  ─────────────────────────────────────────────────────────────  │
│  Created Jan 20 • Last edited 2h ago by You                     │
│  1,234 words • ~5 min read • Topics: authentication, security   │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

| Property | Value |
|----------|-------|
| Font Size | 11px (text-xs) |
| Color | Foreground muted |
| Spacing | 4px between items |
| AI Reading Time | Based on 200 WPM adjusted for technical content |
| Topic Tags | AI-generated, max 3 displayed |

#### 6. Auto-Generated Table of Contents

Floating sidebar TOC for long notes:

```
╭─────────────────────────────────╮
│  CONTENTS                   [×] │
│  ──────────────────────────────│
│                                 │
│  ● Overview                     │ ← Current section highlighted
│  ○ Authentication Flow          │
│    ○ OAuth2 Setup               │
│    ○ Token Management           │
│  ○ Security Considerations      │
│  ○ Implementation Notes         │
│                                 │
╰─────────────────────────────────╯
```

| Property | Value |
|----------|-------|
| Position | Fixed right, below margin panel |
| Width | 200px |
| Background | Subtle background |
| Border | 1px left |
| Current Section | Primary color dot (●), bold text |
| Other Sections | Muted dot (○), regular text |
| Hover | Muted background |
| Click | Smooth scroll to heading |
| Auto-collapse | Collapses on mobile (< 1024px) |

#### 7. Resizable Margin Panel

Drag handle for adjusting margin panel width:

| Property | Value |
|----------|-------|
| Min Width | 150px |
| Max Width | 350px |
| Default | 200px |
| Drag Handle | 4px invisible zone on left edge |
| Hover Cursor | `col-resize` |
| Resize Feedback | Subtle border highlight |
| Persistence | Width saved per user |

### Bidirectional Sync

Notes and issues stay connected with automatic bidirectional sync:

**Sync Behavior:**
- Issue state changes → Note displays updated badge
- Note edits → Issue description sync (requires approval)
- Issue completion → Rainbow border becomes state color (green for done)
- Issue deletion → Text remains, box removed, marker left

### Workflow Summary

```
1. CAPTURE     → Open Pilot Space → Start typing in note canvas (Home)
2. BRAINSTORM  → AI joins via inline suggestions + margin annotations
3. REFINE      → Threaded discussions clarify each thought block
4. EXTRACT     → AI automatically identifies actionable items
5. WRAP        → Rainbow-bordered boxes wrap source text inline
6. APPROVE     → User reviews and approves issue creation
7. TRACK       → Issues link back to source note (bidirectional)
8. EVOLVE      → Note continues as living documentation
```

---

## AI Collaborative Features

### New Note AI Prompt Flow

When creating a new note, Pilot greets the user with contextual suggestions:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│              ☆                                                  │
│                                                                 │
│       What would you like to work on?                           │
│                                                                 │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ Describe your idea, problem, or topic...              ▏ │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                 │
│  Based on your recent work:                                     │
│                                                                 │
│  ╭─────────────────╮  ╭─────────────────╮  ╭─────────────────╮ │
│  │ 📋 Sprint Plan  │  │ 🐛 Bug Analysis │  │ 📄 Feature Spec │ │
│  │ Continue Q4...  │  │ Auth issues...  │  │ New API design  │ │
│  ╰─────────────────╯  ╰─────────────────╯  ╰─────────────────╯ │
│                                                                 │
│                    [Start with blank note]                      │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

**Features:**
- AI greeting based on user work history summary
- Recommended templates and topics from recent context
- User can type prompt → AI seeds initial document structure
- Option to start blank for freeform thinking

### Ghost Text Autocomplete

AI provides inline suggestions as you type:

```
The authentication flow needs to be|simplified to reduce user friction
                                    ─────────────────────────────────
                                    ↑ Ghost text (faded)
```

| Property | Value |
|----------|-------|
| Color | Foreground muted at 40% |
| Style | Italic |
| Animation | 150ms fade-in, slight left translation |
| Trigger Delay | ~500ms after typing pause |

**Interaction:**
| Key | Action |
|-----|--------|
| Tab | Accept entire suggestion |
| → (Right Arrow) | Accept word by word |
| Any other key | Dismiss and continue typing |
| Escape | Dismiss suggestion |

### Selection Toolbar (Rich + AI)

Text selection reveals formatting and AI action toolbar:

```
                    ╭───────────────────────────────────────────────╮
                    │ B  I  U  S  🔗  •  │  ☆ Improve │ Simplify │ │
                    │                    │  Expand │ Ask │ Extract │ │
                    ╰───────────────────────────────────────────────╯
                                         ▲
                                         │
                    "Users report confusion during password reset"
```

**Toolbar Sections:**
1. **Formatting**: Bold, Italic, Underline, Strikethrough, Link, List
2. **AI Actions**:
   - **Improve**: Enhance clarity and readability
   - **Simplify**: Make text more concise
   - **Expand**: Add more detail
   - **Ask**: Open AI thread for this selection
   - **Extract**: Create issue from selection

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

### Version History Panel

Sidebar panel showing document versions (Claude Code-style snapshots):

```
╭─────────────────────────────────────╮
│  VERSION HISTORY                [×] │
│  ────────────────────────────────── │
│                                     │
│  ╭─────────────────────────────────╮│
│  │ ● Current                       ││
│  │   Just now                      ││
│  ╰─────────────────────────────────╯│
│                                     │
│  │ ○ AI extracted 3 issues         │ ← Collapsible
│  │   10 minutes ago                │
│  │   ╭─ AI reasoning ────────────╮ │
│  │   │ Identified actionable...  │ │
│  │   ╰───────────────────────────╯ │
│                                     │
│  │ ○ Added OAuth section           │
│  │   25 minutes ago                │
│                                     │
│  │ ○ Initial draft                 │
│  │   1 hour ago                    │
│                                     │
│  ────────────────────────────────── │
│  [Restore selected version]         │
│                                     │
╰─────────────────────────────────────╯
```

| Property | Value |
|----------|-------|
| Width | 280px |
| Background | Subtle background |
| Border | 1px left |
| Item Padding | 12px |
| Current Item | 3px primary left border |
| AI Reasoning Block | AI muted background, small padding, text-xs |

**Features:**
- Timestamps for each snapshot
- Brief description of changes
- AI-made changes show collapsible reasoning
- Click to preview version
- Restore to any previous version

### @ Mention System

Inline dropdown for linking notes, issues, and AI agents:

```
Type @auth to see:

╭─────────────────────────────────────────────╮
│                                             │
│  │ 📄 Auth Refactor Note                │   │ ← Selected
│  │ 📄 Authentication Overview           │   │
│  │ 🐛 PS-201 Auth simplification        │   │
│  │ 🐛 PS-202 OAuth error handling       │   │
│  │ ☆ @pilot (AI assistant)              │   │
│                                             │
│  ↑↓ Navigate  ⏎ Insert  ⎋ Close            │
│                                             │
╰─────────────────────────────────────────────╯
```

**Features:**
- Triggered by typing `@`
- Different icons per content type:
  - 📄 Notes
  - 🐛 Issues (with type indicator)
  - 📁 Projects
  - ☆ AI agent mentions
  - 📎 Artifact references
- Arrow key navigation (Up/Down)
- Top 10 matches shown
- Fuzzy search matching

| Property | Value |
|----------|-------|
| Min Width | 280px |
| Max Width | 400px |
| Max Height | 300px |
| Item Padding | 8px vertical, 12px horizontal |
| Hover/Selected | Muted background |
| Link Style | Primary color, 1px underline at 30% opacity |

### Collapsible AI Panel

Bottom toggle panel for AI assistance:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│  ─────────────────── [●] ───────────────────  ← Thin bar + pulse│
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯

Expanded:
╭─────────────────────────────────────────────────────────────────╮
│  AI ASSISTANT                                              [▼]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ Ask anything or select an action...                      │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                 │
│  ╭────────╮ ╭──────────╮ ╭──────────╮ ╭──────────────╮        │
│  │Summarize│ │Generate  │ │Extract   │ │Find similar  │        │
│  │         │ │diagram   │ │tasks     │ │notes         │        │
│  ╰────────╯ ╰──────────╯ ╰──────────╯ ╰──────────────╯        │
│                                                                 │
│  Status: Searching codebase for patterns...                     │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

**Features:**
- Thin bar with pulse dot (●) when collapsed
- Click to expand full panel
- Free-form question input
- Static + dynamic action chips
- Claude Code-style status ("Searching codebase...", "Generating diagram...")
- Full keyboard navigation: Arrow keys, Tab, number keys for chip selection

### Floating Action Button (FAB) with AI Search

Bottom-right button opens AI-enabled search bar:

| Property | Value |
|----------|-------|
| Position | Fixed, bottom-right (24px margin) |
| Size | 56px diameter |
| Background | Primary color |
| Icon | AI star or search icon |
| Shadow | Medium shadow |
| Hover | Scale 105%, elevated shadow |

**Search Bar Features:**
- Keyword + semantic search combined
- AI answer appears first, search results as rows
- Recent searches when empty
- Content type filters

---

## Navigation & Search

### Command Palette (Cmd+P)

Full-featured command palette with smart AI suggestions:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ 🔍 Type a command or search...                          │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  AI SUGGESTIONS (based on current context)                      │
│                                                                 │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ ☆ Extract issues from selection          ⏎              │   │ ← Selected
│  ╰─────────────────────────────────────────────────────────╯   │
│  │ ☆ Summarize this note                                   │   │
│  │ ☆ Generate diagram from description                     │   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  NAVIGATION                                                     │
│  │ 🏠 Go to Home                           G H             │   │
│  │ 📋 Go to Issues                         G I             │   │
│  │ 📊 Go to Cycles                         G C             │   │
│                                                                 │
│  ACTIONS                                                        │
│  │ ➕ Create new note                      Cmd+N           │   │
│  │ ➕ Create new issue                     C               │   │
│  │ 🔍 Search everything                    Cmd+K           │   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ↑↓ Navigate  ⏎ Select  ⎋ Close                               │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

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

**Features:**
- Smart AI suggestions based on current context
- Categorized commands (Navigation, Actions, AI, Settings)
- Fuzzy search across all commands
- Keyboard shortcut hints
- Recent commands section

### Search Modal (Cmd+K)

Full-page spotlight-style search:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│  ╭─────────────────────────────────────────────────────────╮   │
│  │ 🔍 Search notes, issues, projects...                    │   │
│  ╰─────────────────────────────────────────────────────────╯   │
│                                                                 │
│  ╭────────╮ ╭────────╮ ╭────────╮ ╭────────╮                   │
│  │  All   │ │ Notes  │ │ Issues │ │Projects│                   │
│  ╰────────╯ ╰────────╯ ╰────────╯ ╰────────╯                   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  RECENT                                                         │
│                                                                 │
│  │ 📄 Auth Refactor Note                  2 hours ago      │   │
│  │ 🐛 PS-201 Simplify password reset      Yesterday        │   │
│  │ 📁 Authentication Project              3 days ago       │   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  ↑↓ Navigate  ⏎ Open  ⇥ Preview  ⎋ Close                      │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

**Features:**
- Full-page modal (not small dropdown)
- Content type filters (All, Notes, Issues, Projects)
- Recent items when no search query
- Preview on Tab key
- Fuzzy matching with highlighted results

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd+P | Open command palette |
| Cmd+K | Open search |
| Cmd+N | Create new note |
| C | Create new issue (when not in text input) |
| G H | Go to Home |
| G I | Go to Issues |
| G C | Go to Cycles |
| ? | Show keyboard shortcut guide (when not in text input) |
| / | Open slash command menu (in editor) |

---

## Interaction Patterns

### Drag and Drop

**Issue Board Cards:**
- Cards lift with elevated shadow on pickup
- 4px indicator shows drop zone
- Smooth 200ms transitions
- Haptic feedback where supported

**List Reordering:**
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

### Error States

| Type | Visual |
|------|--------|
| Field Error | Red border, error message below |
| Toast Error | Red background, white text, dismiss button |
| Page Error | Centered error with retry button |
| Network Error | Banner at top with retry |

### Progressive Tooltips

Two-stage tooltips for better discoverability:

| Stage | Trigger | Content |
|-------|---------|---------|
| Stage 1 | Instant on hover | Brief label (1-3 words) |
| Stage 2 | After 1 second | Detailed help + keyboard shortcut |

```
Stage 1 (instant):          Stage 2 (after 1s):
╭─────────────╮             ╭──────────────────────────────╮
│   Search    │    →        │   Search                     │
╰─────────────╯             │   ─────────────────────────  │
                            │   Find notes, issues, and    │
                            │   projects across workspace  │
                            │                              │
                            │   ⌘K                         │
                            ╰──────────────────────────────╯
```

| Property | Value |
|----------|-------|
| Stage 1 Padding | 4px 8px |
| Stage 2 Padding | 12px |
| Max Width | 240px |
| Animation | 150ms fade |
| Shortcut Style | Mono font, muted background |

### AI Confidence Tags

Visual treatment for AI suggestion confidence:

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│  Suggested Labels:                                              │
│                                                                 │
│  ╭────────────────╮  ╭────────────────╮  ╭────────────────╮    │
│  │ ★ Recommended  │  │   Default      │  │   Alternative  │    │
│  │    bug         │  │    frontend    │  │    backend     │    │
│  ╰────────────────╯  ╰────────────────╯  ╰────────────────╯    │
│                                                                 │
│  Hover on "Recommended" shows: "92% confidence"                 │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

| Tag | Background | Border | Icon |
|-----|------------|--------|------|
| Recommended | Primary 10% | Primary 30% | ★ (filled star) |
| Default | Muted | Border | None |
| Current | AI blue 10% | AI blue 30% | None |
| Alternative | Transparent | Border dashed | None |

| Property | Value |
|----------|-------|
| Padding | 4px 8px |
| Border Radius | 6px |
| Font Size | 12px |
| Hover | Show percentage tooltip |

### Pinned Notes Indicator

Visual treatment for pinned notes in sidebar:

```
╭────────────────────╮
│  📌 PINNED         │
│  ├─ 📄 Auth Notes  │  ← Pin icon, subtle background
│  └─ 📄 API Design  │
│                    │
│  📄 RECENT         │
│  ├─ 📄 Sprint 12   │
│  └─ 📄 Bug Triage  │
╰────────────────────╯
```

| Property | Value |
|----------|-------|
| Section Label | 10px uppercase, muted |
| Pinned Item | Subtle primary background |
| Pin Action | Right-click or ⋯ menu |
| Unpin | Same menu, or drag out |
| Max Pinned | 5 notes |

### AI-Prioritized Notification Center

Notification center in sidebar with smart inbox:

```
╭────────────────────────────────────────────────╮
│  🔔 NOTIFICATIONS              3 new           │
│  ─────────────────────────────────────────     │
│                                                │
│  ╭──────────────────────────────────────────╮ │
│  │ ⚠️ URGENT                                 │ │ ← Priority tag (red)
│  │ PR #234 has merge conflicts               │ │
│  │ 5 min ago                                 │ │
│  ╰──────────────────────────────────────────╯ │
│                                                │
│  ╭──────────────────────────────────────────╮ │
│  │ ⭐ IMPORTANT                              │ │ ← Priority tag (amber)
│  │ Alice assigned you to AUTH-456            │ │
│  │ 1 hour ago                                │ │
│  ╰──────────────────────────────────────────╯ │
│                                                │
│  ╭──────────────────────────────────────────╮ │
│  │ 💬 FYI                                    │ │ ← Priority tag (muted)
│  │ Bob commented on your note                │ │   (subtle background)
│  │ 3 hours ago                               │ │
│  ╰──────────────────────────────────────────╯ │
│                                                │
│  [View All]                                   │
╰────────────────────────────────────────────────╯
```

| Priority | Background | Icon | Color |
|----------|------------|------|-------|
| Urgent | Red 10% | ⚠️ | Red |
| Important | Amber 10% | ⭐ | Amber |
| FYI | Muted | 💬 | Gray |

| Property | Value |
|----------|-------|
| Max Preview | 3-5 notifications |
| Mark-as-Read Delay | 2-3 seconds viewing |
| Unread Indicator | Subtle background tint |
| Badge Style | Primary color, count text |
| Animation | Fade in new notifications |

### Similar Notes with AI Guidance

After note creation, show similar existing notes:

```
╭────────────────────────────────────────────────╮
│  ✨ Similar Notes Found                        │
│  ─────────────────────────────────────────     │
│                                                │
│  AI found 2 notes related to your new content  │
│                                                │
│  ╭──────────────────────────────────────────╮ │
│  │ 📄 Authentication Flow Notes              │ │
│  │    Created Jan 15 • 82% similar           │ │
│  │                                           │ │
│  │  💡 "This note covers OAuth basics,       │ │
│  │     yours adds PKCE implementation"       │ │
│  │                                           │ │
│  │  [View] [Link] [Merge]                    │ │
│  ╰──────────────────────────────────────────╯ │
│                                                │
│  ╭──────────────────────────────────────────╮ │
│  │ 📄 API Security Patterns                  │ │
│  │    Created Dec 28 • 65% similar           │ │
│  │                                           │ │
│  │  💡 "Consider linking for cross-reference"│ │
│  │                                           │ │
│  │  [View] [Link]                            │ │
│  ╰──────────────────────────────────────────╯ │
│                                                │
│  [Dismiss]                                    │
╰────────────────────────────────────────────────╯
```

| Property | Value |
|----------|-------|
| Trigger | After new note save |
| Position | Sidebar panel or modal |
| AI Guidance | 1-2 line explanation per note |
| Actions | View, Link, Merge (if appropriate) |
| Dismiss | Close and don't show again for this note |
| Similarity Threshold | Show notes > 60% similar |

---

## Accessibility Requirements

### WCAG 2.2 AA Compliance

| Requirement | Implementation |
|-------------|----------------|
| Color Contrast | Minimum 4.5:1 for text, 3:1 for UI components |
| Focus Visibility | 3px ring on all interactive elements |
| Keyboard Navigation | All features accessible via keyboard |
| Screen Reader | ARIA labels, roles, live regions |
| Motion | Respects prefers-reduced-motion |
| Touch Targets | Minimum 44x44px |

### Semantic HTML

- Use proper heading hierarchy (h1 → h2 → h3)
- Use button for actions, links for navigation
- Use lists for groups of related items
- Use tables for tabular data with proper headers

### ARIA Patterns

| Component | ARIA Pattern |
|-----------|--------------|
| Modal | `role="dialog"`, `aria-modal="true"` |
| Dropdown | `aria-expanded`, `aria-haspopup` |
| Tabs | `role="tablist"`, `role="tab"`, `role="tabpanel"` |
| Toast | `role="alert"`, `aria-live="polite"` |
| Loading | `aria-busy="true"`, `aria-describedby` |

### Skip Links

- "Skip to main content" link at top of page
- Visible on focus
- Links to main content area

---

## Responsive Design

### Breakpoints

| Name | Value | Usage |
|------|-------|-------|
| sm | 640px | Mobile landscape |
| md | 768px | Tablet portrait |
| lg | 1024px | Tablet landscape |
| xl | 1280px | Desktop |
| 2xl | 1536px | Large desktop |

### Mobile Adaptations (< 768px)

| Element | Adaptation |
|---------|------------|
| Sidebar | Hidden, accessible via hamburger menu |
| Note Canvas | Full width, margin annotations below |
| Command Palette | Full screen modal |
| Cards | Stack vertically |
| Tables | Horizontal scroll or card view |

### Touch Optimizations

- Minimum 44px touch targets
- Swipe gestures for common actions
- Pull to refresh where appropriate
- No hover-dependent interactions

---

## Implementation Notes

### Performance Targets

| Metric | Target |
|--------|--------|
| First Contentful Paint | < 1.5s |
| Largest Contentful Paint | < 2.5s |
| Time to Interactive | < 3s |
| Cumulative Layout Shift | < 0.1 |
| Interaction Latency | < 100ms |

### Virtual Scroll

For notes with 1000+ blocks:
- Implement windowed rendering
- Only render visible blocks + buffer
- Maintain scroll position on content changes

### Code Organization

```
/components
  /ui           # Base shadcn/ui components
  /features     # Feature-specific components
  /layouts      # Page layouts
  /patterns     # Reusable interaction patterns

/styles
  /tokens       # Design tokens
  /utilities    # Utility classes
```

### Testing Requirements

| Type | Coverage |
|------|----------|
| Visual Regression | All components |
| Accessibility | axe-core automated |
| Responsive | All breakpoints |
| Keyboard | All interactions |

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
| Key Conflicts (Tab) | Context-aware priority: 1) code block → indent, 2) ghost text visible → accept, 3) default behavior. |
| Content Diff | Block-level tracking via TipTap transaction. >20% blocks changed → trigger embedding refresh. |
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
| Error Display | Context-specific: Ghost text → inline muted. AI Panel → panel error state. PR review → toast. |
| Command Palette Context | Minimal: selection text + entity type + title. Cache 30s. |

#### Accessibility

| Decision | Implementation |
|----------|----------------|
| Focus Management | Explicit escape pattern. Tab in editor. Escape → sidebar. F6 cycles regions. |
| Motion | CSS `@media (prefers-reduced-motion: reduce)`. Tailwind `motion-safe:` / `motion-reduce:` variants. |

#### Testing

| Decision | Implementation |
|----------|----------------|
| TipTap Testing | Integration tests with real editor in Vitest (jsdom). |
| SSE Mocking | MSW handlers for streaming responses. |
| Accessibility | axe-core in CI + manual screen reader testing. |
| E2E | Playwright for critical user flows (note creation, issue extraction). |

---

*Document Version: 3.3.0*
*Last Updated: 2026-01-22*
*Author: Pilot Space Team*
*Changes v3.3: Added Frontend Architecture Decisions section with 15 implementation clarifications (State Management, Virtualization, SSE, Testing)*
*Changes v3.2: Added AI-Prioritized Notification Center (DD-038) and Similar Notes with AI Guidance (DD-036) UI specifications*
