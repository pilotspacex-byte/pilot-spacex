# Wireframes: Role-Based Skills for PilotSpace Agent

**Feature**: 011-role-based-skills
**Created**: 2026-02-06
**Design System**: Warm, Capable, Collaborative (Pilot Space UI Design Spec v4.0)

---

## Design Tokens Reference

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#29A386` (teal-green) | Selected states, CTAs |
| AI accent | `#6B8FAD` (dusty blue) | AI generation elements |
| Background | `#FDFCFA` | Page background |
| Background subtle | `#F7F5F2` | Card surfaces |
| Border | `#E5E2DD` | Card borders |
| Foreground | `#171717` | Primary text |
| Muted | `#737373` | Secondary text |
| Destructive | `#D9534F` | Remove actions |
| Radius | `12px` | Cards, buttons |
| Font | Geist (UI), Geist Mono (code) | |

---

## Screen 1: Onboarding — Role Selection Step (US1)

**Route**: `/{workspaceSlug}` (onboarding overlay)
**Trigger**: 4th step in onboarding checklist after "Write First Note"
**States**: Default | With Default Role | With Owner Hint | Multi-select | Custom Role

### 1A. Default State — No Pre-selections

```
┌─────────────────────────────────────────────────────────────────┐
│  Onboarding  ·  Step 3 of 4                           [Skip →] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🎯  Set Up Your Role                                         │
│                                                                 │
│   Select your SDLC role to personalize your AI assistant.       │
│   Choose up to 3 roles. The first selected becomes primary.     │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │ 📋           │  │ 🎯           │  │ 💻           │        │
│   │ Business     │  │ Product      │  │ Developer    │        │
│   │ Analyst      │  │ Owner        │  │              │        │
│   │              │  │              │  │              │        │
│   │ Requirements │  │ Roadmap &    │  │ Code &       │        │
│   │ & analysis   │  │ priorities   │  │ architecture │        │
│   └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │ 🧪           │  │ 🏗️           │  │ 🔀           │        │
│   │ Tester       │  │ Architect    │  │ Tech Lead    │        │
│   │              │  │              │  │              │        │
│   │ Quality &    │  │ System       │  │ Technical    │        │
│   │ test plans   │  │ design       │  │ direction    │        │
│   └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │ 📊           │  │ 📦           │  │ ✏️           │        │
│   │ Project      │  │ DevOps       │  │ Custom       │        │
│   │ Manager      │  │              │  │ Role         │        │
│   │              │  │              │  │              │        │
│   │ Delivery &   │  │ CI/CD &      │  │ Define your  │        │
│   │ tracking     │  │ infra        │  │ own role     │        │
│   └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                 │
│                                                                 │
│                              [ Continue to Skill Setup → ]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Card Specs**:
- Size: `160px × 140px`
- Background: `--background-subtle` (#F7F5F2)
- Border: `1px solid --border` (#E5E2DD)
- Border radius: `12px`
- Hover: `translateY(-2px)`, shadow `0 4px 12px rgba(0,0,0,0.08)`
- Icon: Lucide, 24px, `--foreground-muted`
- Title: Geist 14px semibold `--foreground`
- Description: Geist 12px `--foreground-muted`

### 1B. Selected State — Developer (Primary) + Tester (Secondary)

```
┌─────────────────────────────────────────────────────────────────┐
│  Onboarding  ·  Step 3 of 4                           [Skip →] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🎯  Set Up Your Role                                         │
│                                                                 │
│   Select your SDLC role to personalize your AI assistant.       │
│   Choose up to 3 roles. The first selected becomes primary.     │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ╔══════════════╗        │
│   │ 📋           │  │ 🎯           │  ║ ✅ 💻  ①    ║        │
│   │ Business     │  │ Product      │  ║ Developer    ║        │
│   │ Analyst      │  │ Owner        │  ║  PRIMARY     ║        │
│   │              │  │              │  ║              ║        │
│   │ Requirements │  │ Roadmap &    │  ║ Code &       ║        │
│   │ & analysis   │  │ priorities   │  ║ architecture ║        │
│   └──────────────┘  └──────────────┘  ╚══════════════╝        │
│                                                                 │
│   ╔══════════════╗  ┌──────────────┐  ┌──────────────┐        │
│   ║ ✅ 🧪  ②    ║  │ 🏗️           │  │ 🔀           │        │
│   ║ Tester       ║  │ Architect    │  │ Tech Lead    │        │
│   ║              ║  │              │  │              │        │
│   ║ Quality &    ║  │ System       │  │ Technical    │        │
│   ║ test plans   ║  │ design       │  │ direction    │        │
│   ╚══════════════╝  └──────────────┘  └──────────────┘        │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  Selected: Developer (primary) · Tester          │          │
│   │  1 more role available                           │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
│                              [ Continue to Skill Setup → ]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Selected Card Specs**:
- Border: `2px solid --primary` (#29A386)
- Background: `--primary-muted` (#29A38615)
- Checkmark: `--primary`, 16px, top-left corner
- Number badge: `①②③`, top-right, indicates selection order
- "PRIMARY" label: 10px uppercase, `--primary`, below title on first selected

### 1C. With Default Role + Owner Hint

```
┌─────────────────────────────────────────────────────────────────┐
│  Onboarding  ·  Step 3 of 4                           [Skip →] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🎯  Set Up Your Role                                         │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ╔══════════════╗        │
│   │ 📋           │  │ 🎯           │  ║ 💻           ║        │
│   │ Business     │  │ Product      │  ║ Developer    ║        │
│   │ Analyst      │  │ Owner        │  ║──────────────║        │
│   │              │  │              │  ║ ⭐ Your      ║        │
│   │              │  │              │  ║   default    ║        │
│   └──────────────┘  └──────────────┘  ╚══════════════╝        │
│                                                                 │
│   ╔══════════════╗  ┌──────────────┐  ┌──────────────┐        │
│   ║ 🧪           ║  │ 🏗️           │  │ 🔀           │        │
│   ║ Tester       ║  │ Architect    │  │ Tech Lead    │        │
│   ║──────────────║  │              │  │              │        │
│   ║ 👤 Suggested ║  │              │  │              │        │
│   ║   by owner   ║  │              │  │              │        │
│   ╚══════════════╝  └──────────────┘  └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Badge Specs**:
- "Your default": `⭐` icon, `--primary` text, `--primary-muted` bg, pill shape
- "Suggested by owner": `👤` icon, `--ai` (#6B8FAD) text, `--ai-muted` bg, pill shape
- Both badges: 11px, border-radius 6px, padding 2px 8px

### 1D. Custom Role Input

```
┌─────────────────────────────────────────────────────────────────┐
│  Onboarding  ·  Step 3 of 4                           [Skip →] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ✏️  Custom Role                              [← Back to grid] │
│                                                                 │
│   Role Name                                                     │
│   ┌─────────────────────────────────────────────┐              │
│   │ Senior Security Engineer                     │              │
│   └─────────────────────────────────────────────┘              │
│                                                                 │
│   Describe your responsibilities and focus areas                │
│   ┌─────────────────────────────────────────────┐              │
│   │ I focus on application security, threat      │              │
│   │ modeling, secure code review, and compliance │              │
│   │ frameworks (SOC2, ISO 27001). I work closely │              │
│   │ with the dev team to integrate security into │              │
│   │ the SDLC pipeline.                           │              │
│   │                                              │              │
│   │                                              │              │
│   └─────────────────────────────────────────────┘              │
│                                           124 / 5000 characters │
│                                                                 │
│                              [ Continue to Skill Setup → ]      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Screen 2: Skill Generation Wizard (US2)

**Route**: Same overlay, step 2 of role setup sub-flow
**Trigger**: After clicking "Continue to Skill Setup" from role selection
**States**: Path Selection | Describe Expertise | Generating | Preview | Error Fallback

### 2A. Path Selection

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                      [← Back]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🪄  Generate Your AI Skill                                   │
│                                                                 │
│   How should we create your Developer skill?                    │
│   This shapes how the AI assistant helps you.                   │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  📄  Use Default Developer Skill                 │          │
│   │                                                   │          │
│   │  Start with the standard Developer template.      │          │
│   │  You can customize it later in Settings.          │          │
│   │                                          [Use →]  │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  ✨  Describe Your Expertise              ★ REC  │          │
│   │                                                   │          │
│   │  Tell us about your experience and the AI will    │          │
│   │  generate a personalized skill tailored to you.   │          │
│   │                                       [Start →]   │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  💡  Show Me Examples                            │          │
│   │                                                   │          │
│   │  See how the AI behaves with a Developer skill    │          │
│   │  before deciding.                                 │          │
│   │                                          [View →] │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Path Card Specs**:
- Background: `--background` (#FDFCFA)
- Border: `1px solid --border`
- Hover: border → `--primary`, bg → `--primary-muted`
- Recommended badge: `★ REC` in `--primary` bg, white text, pill
- Each card: full-width, 100px height, padding 20px

### 2B. Describe Expertise — Input

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                      [← Back]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ✨  Describe Your Expertise                                   │
│                                                                 │
│   Tell us about your experience, specializations, and how       │
│   you like to work. The more detail, the better the AI skill.   │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │ Full-stack engineer with 5 years experience.     │          │
│   │ TypeScript, React, Node.js, PostgreSQL.          │          │
│   │ Strong focus on clean architecture and testing.  │          │
│   │ I prefer reviewing PRs for security and          │          │
│   │ performance issues first, then code style.       │          │
│   │ I use TDD and write integration tests before     │          │
│   │ unit tests.                                      │          │
│   │                                                  │          │
│   │                                                  │          │
│   └─────────────────────────────────────────────────┘          │
│                                           198 / 5000 characters │
│                                  Min 10 characters required     │
│                                                                 │
│                                                                 │
│                    [ ✨ Generate Skill ]                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2C. Generating — Loading State

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                                                                 │
│                                                                 │
│                         ◌ ◌ ◌                                   │
│                                                                 │
│               Generating your Developer skill...                │
│                                                                 │
│           Our AI is crafting a personalized skill based         │
│           on your expertise. This takes about 15-30 seconds.    │
│                                                                 │
│                                                                 │
│                      ━━━━━━━━━━░░░░░  65%                       │
│                                                                 │
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Loading Specs**:
- Spinner: 3-dot pulse animation in `--ai` (#6B8FAD)
- Progress bar: `--ai` fill, `--border` track, 4px height, rounded
- Text: Geist 16px `--foreground`, Geist 14px `--foreground-muted`

### 2D. Preview — Generated Skill

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                      [← Back]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ✅  Your Developer Skill                  Generated by AI     │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  # Developer — Full-Stack Engineer               │  ▲      │
│   │                                                   │  │      │
│   │  ## Focus Areas                                   │  │      │
│   │  - Clean architecture (hexagonal, CQRS-lite)     │scroll   │
│   │  - TypeScript + React + Node.js ecosystem        │  │      │
│   │  - PostgreSQL query optimization                  │  │      │
│   │  - Security-first PR reviews                      │  │      │
│   │  - TDD with integration tests before unit tests  │  │      │
│   │                                                   │  │      │
│   │  ## Workflow Preferences                          │  │      │
│   │  - Review PRs: security → performance → style    │  │      │
│   │  - Suggest test coverage gaps proactively         │  │      │
│   │  - Flag N+1 queries and blocking I/O             │  │      │
│   │                                                   │  │      │
│   │  ## Vocabulary                                    │  │      │
│   │  - Use TypeScript-specific terminology            │  │      │
│   │  - Reference clean architecture patterns          │  │      │
│   │  - Cite OWASP when discussing security            │  │      │
│   └─────────────────────────────────────────────────┘          │
│                                          847 / 2000 words       │
│                                                                 │
│   ┌──────────┐  ┌──────────────┐  ┌────────────────┐          │
│   │ Save &   │  │ ✏️ Customize  │  │ 🔄 Retry       │          │
│   │ Activate │  │              │  │                │          │
│   └──────────┘  └──────────────┘  └────────────────┘          │
│    (primary)      (secondary)        (ghost)                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Preview Specs**:
- Skill preview: `--background-subtle` bg, `1px solid --border`, max-height `400px`, overflow scroll
- Markdown rendered with Geist 14px, code blocks in Geist Mono
- Word count: Geist 12px `--foreground-muted`, turns `--destructive` at 1800+
- "Generated by AI" badge: `--ai-muted` bg, `--ai` text, pill shape

### 2E. Error Fallback — AI Provider Unavailable

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                      [← Back]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  ⚠️  Skill generation unavailable                │          │
│   │                                                   │          │
│   │  We couldn't reach the AI provider. We've loaded  │          │
│   │  the default Developer template instead.          │          │
│   │                                                   │          │
│   │  Your experience description has been saved —     │          │
│   │  you can retry generation later from Settings.    │          │
│   │                                     [ Dismiss ]   │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
│   ┌─────────────────────────────────────────────────┐          │
│   │  # Developer (Default Template)                  │          │
│   │                                                   │          │
│   │  ## Focus Areas                                   │          │
│   │  - Code quality and maintainability              │          │
│   │  - Architecture patterns and design              │          │
│   │  - Testing strategies and coverage               │          │
│   │  ...                                              │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                 │
│   ┌────────────┐  ┌──────────────────┐                         │
│   │ Save       │  │ 🔄 Retry Generation │                      │
│   │ Default    │  │                    │                        │
│   └────────────┘  └──────────────────┘                         │
│    (primary)        (outline, --ai border)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Error Banner Specs**:
- Background: `#FEF3CD` (warm yellow)
- Border-left: `4px solid #D9853F` (warning orange)
- Icon: `⚠️` TriangleAlert, 20px
- Text: Geist 14px `--foreground`

---

## Screen 3: Onboarding Checklist — Updated with Role Step

**Route**: `/{workspaceSlug}` (home page sidebar)
**Context**: Existing checklist component updated from 3 to 4 steps

### 3A. Checklist with Role Step (In Progress)

```
┌───────────────────────────────────┐
│  🚀 Get Started        2/4  50%  │
│  ━━━━━━━━━━━━░░░░░░░░░░░░░      │
├───────────────────────────────────┤
│                                   │
│  ✅  Configure AI Providers       │
│      Connected Anthropic key      │
│                                   │
│  ○  Invite Team Members           │
│     Add your team to collaborate  │
│                     [ Invite → ]  │
│                                   │
│  ○  Set Up Your Role        NEW   │
│     Personalize your AI assistant │
│                   [ Set Up → ]    │
│                                   │
│  ✅  Write Your First Note        │
│      Created "Project Kickoff"    │
│                                   │
├───────────────────────────────────┤
│           [ Dismiss checklist ]   │
└───────────────────────────────────┘
```

**Checklist Specs**:
- "NEW" badge: `--primary` bg, white text, 10px uppercase, pill shape, pulse animation (subtle)
- Completed steps: `✅` checkmark, `--primary`, description in `--foreground-muted`
- Pending steps: `○` circle, `--border` color
- Progress bar: `--primary` fill, `--border` track

---

## Screen 4: Settings — Skills Tab (US6)

**Route**: `/{workspaceSlug}/settings/skills`
**States**: Has Roles | Empty | Editing | Regenerating | Guest View | Max Roles

### 4A. Skills Tab — Two Roles Configured

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Settings                                                             │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ General  │ │ Members  │ │ Integra- │ │ Profile  │ │ AI       │    │
│  │          │ │          │ │ tions    │ │          │ │ Providers│    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐                                                          │
│  │ 🪄Skills │  ← active tab                                           │
│  └──────────┘                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  AI Skills                                               [ + Add Role ] │
│  Configure how the AI assistant adapts to your role.     (1 slot left)  │
│                                                                         │
│  ╔═════════════════════════════════════════════════════════════════╗    │
│  ║  💻  Developer                                    ★ PRIMARY    ║    │
│  ║                                                                 ║    │
│  ║  ┌───────────────────────────────────────────────────────────┐ ║    │
│  ║  │  # Developer — Full-Stack Engineer                        │ ║    │
│  ║  │                                                           │ ║    │
│  ║  │  ## Focus Areas                                           │ ║    │
│  ║  │  - Clean architecture (hexagonal, CQRS-lite)             │ ║    │
│  ║  │  - TypeScript + React + Node.js ecosystem                │ ║    │
│  ║  │  - PostgreSQL query optimization                          │ ║    │
│  ║  │  - Security-first PR reviews                              │ ║    │
│  ║  │  ...                                                      │ ║    │
│  ║  └───────────────────────────────────────────────────────────┘ ║    │
│  ║                                                   847 words    ║    │
│  ║                                                                 ║    │
│  ║  ┌────────┐ ┌──────────────────┐ ┌─────────────┐ ┌──────────┐ ║    │
│  ║  │ ✏️ Edit │ │ ✨ Regenerate AI  │ │ ↩ Reset     │ │ 🗑 Remove│ ║    │
│  ║  └────────┘ └──────────────────┘ └─────────────┘ └──────────┘ ║    │
│  ║  (outline)    (outline, --ai)     (ghost)         (ghost,red) ║    │
│  ╚═════════════════════════════════════════════════════════════════╝    │
│                                                                         │
│  ┌═════════════════════════════════════════════════════════════════┐    │
│  │  🧪  Tester                                                     │    │
│  │                                                                  │    │
│  │  ┌───────────────────────────────────────────────────────────┐  │    │
│  │  │  # Tester — QA Automation Engineer                        │  │    │
│  │  │                                                           │  │    │
│  │  │  ## Focus Areas                                           │  │    │
│  │  │  - API testing and contract validation                    │  │    │
│  │  │  - Performance benchmarking                               │  │    │
│  │  │  - BDD scenario writing                                   │  │    │
│  │  │  ...                                                      │  │    │
│  │  └───────────────────────────────────────────────────────────┘  │    │
│  │                                                   623 words     │    │
│  │                                                                  │    │
│  │  ┌────────┐ ┌──────────────────┐ ┌─────────────┐ ┌──────────┐  │    │
│  │  │ ✏️ Edit │ │ ✨ Regenerate AI  │ │ ↩ Reset     │ │ 🗑 Remove│  │    │
│  │  └────────┘ └──────────────────┘ └─────────────┘ └──────────┘  │    │
│  └═════════════════════════════════════════════════════════════════┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Skills Card Specs**:
- Primary card: `2px solid --primary` border, `--primary-muted` bg
- Secondary card: `1px solid --border`
- "PRIMARY" badge: `--primary` bg, white text, 10px uppercase, top-right
- Skill content area: `--background` bg, `1px solid --border-subtle`, max-height `200px` collapsed, expandable
- Word count: Geist 12px `--foreground-muted`
- Action buttons: row of 4, spaced `gap: 8px`

### 4B. Skills Tab — Empty State

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Skills                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                                                                         │
│                         🪄                                              │
│                                                                         │
│                No roles configured                                      │
│                                                                         │
│          Set up your SDLC role to personalize how                       │
│          the AI assistant helps you in this workspace.                   │
│                                                                         │
│                  [ + Set Up Your Role ]                                  │
│                                                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Empty State Specs**:
- Icon: Wand2, 48px, `--foreground-muted` at 40% opacity
- Title: Geist 18px semibold `--foreground`
- Description: Geist 14px `--foreground-muted`, max-width 400px, centered
- CTA: Primary button variant

### 4C. Editing — Inline Skill Editor

```
┌═════════════════════════════════════════════════════════════════════╗
║  💻  Developer                              ★ PRIMARY   [Cancel]  ║
║                                                                    ║
║  ┌──────────────────────────────────────────────────────────────┐ ║
║  │  ┌─B─┐ ┌─I─┐ ┌─H1─┐ ┌─H2─┐ ┌─H3─┐ ┌─•─┐ ┌─<>─┐        │ ║
║  │  └───┘ └───┘ └────┘ └────┘ └────┘ └───┘ └────┘        │ ║
║  ├──────────────────────────────────────────────────────────────┤ ║
║  │  # Developer — Full-Stack Engineer                           │ ║
║  │                                                              │ ║
║  │  ## Focus Areas                                              │ ║
║  │  - Clean architecture (hexagonal, CQRS-lite)                │ ║
║  │  - TypeScript + React + Node.js ecosystem                   │ ║
║  │  - PostgreSQL query optimization                             │ ║
║  │  - Security-first PR reviews                                 │ ║
║  │  - **GraphQL API design** ← newly added                     │ ║
║  │                                                              │ ║
║  │  ## Workflow Preferences                                     │ ║
║  │  - Review PRs: security → performance → style               │ ║
║  │  - Suggest test coverage gaps proactively                    │ ║
║  │  │                                                           │ ║
║  └──────────────────────────────────────────────────────────────┘ ║
║                                                                    ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━░░░  862 / 2000      ║
║                                                                    ║
║  ┌──────────────┐  ┌──────────────┐                               ║
║  │ 💾 Save      │  │    Cancel    │                               ║
║  └──────────────┘  └──────────────┘                               ║
║   (primary)          (ghost)                                       ║
╚════════════════════════════════════════════════════════════════════╝
```

**Editor Specs**:
- Toolbar: Mini markdown toolbar with bold, italic, headings, list, code block
- Editor area: `--background` bg, min-height `300px`, monospace for markdown
- Word count bar: Progress bar showing `words / 2000`
  - Green (`--primary`): 0-1799 words
  - Orange (`#D9853F`): 1800-1999 words (warning)
  - Red (`--destructive`): 2000+ (blocked, cannot save)

### 4D. Regeneration — Diff Preview

```
┌─────────────────────── Modal ───────────────────────────────────┐
│                                                                  │
│  ✨  Regenerate Developer Skill                        [ × ]    │
│                                                                  │
│  Update your experience description:                             │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Full-stack engineer with 5 years experience.      │           │
│  │ TypeScript, React, Node.js, PostgreSQL, GraphQL.  │           │
│  │ Now also doing infrastructure and Terraform.      │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│                    [ ✨ Generate New Skill ]                     │
│                                                                  │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─           │
│                                                                  │
│  ┌─── Current ────────┐  ┌─── New (AI Generated) ────┐         │
│  │                     │  │                            │         │
│  │ ## Focus Areas      │  │ ## Focus Areas             │         │
│  │ - Clean arch...     │  │ - Clean arch...            │         │
│  │ - TypeScript...     │  │ - TypeScript...            │         │
│  │ - PostgreSQL...     │  │ - PostgreSQL...            │         │
│  │ - Security...       │  │ - Security...              │         │
│  │                     │  │ + **GraphQL API design**   │  green  │
│  │                     │  │ + **Terraform & IaC**      │  green  │
│  │                     │  │                            │         │
│  │ ## Workflow          │  │ ## Workflow                │         │
│  │ - Review PRs...     │  │ - Review PRs...            │         │
│  │                     │  │ + **Infra review checks**  │  green  │
│  └─────────────────────┘  └────────────────────────────┘         │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────┐                         │
│  │ Accept New Skill  │  │   Keep Current│                        │
│  └──────────────────┘  └──────────────┘                         │
│   (primary)              (outline)                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Diff Specs**:
- Side-by-side layout, each panel: `--background-subtle` bg
- Added lines: `#29A38620` bg, `+` prefix in `--primary`
- Removed lines: `#D9534F20` bg, `-` prefix in `--destructive`
- Panel headers: Geist 12px semibold uppercase `--foreground-muted`

### 4E. Max Roles Reached (3/3)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Skills                                          [ + Add Role ]     │
│  Configure how the AI assistant adapts to your role.   (disabled)      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  ⚠️  Maximum 3 roles per workspace reached.                  │       │
│  │  Remove an existing role to add a new one.                   │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  ╔═══╗  ┌───┐  ┌───┐                                                  │
│  ║ 💻║  │ 🧪│  │ 🏗️│                                                  │
│  ║Dev║  │Tes│  │Arc│                                                  │
│  ╚═══╝  └───┘  └───┘                                                  │
│  ...cards...                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4F. Guest View (Read-Only)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Skills                                                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  🔒  Role skill configuration requires Member or higher     │       │
│  │      access. Contact a workspace admin for permission.      │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  Skills are not configured for guest users.                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Screen 5: Invite Dialog — Role Hint (US5)

**Route**: `/{workspaceSlug}/settings/members` (modal overlay)
**Context**: Extended existing invite dialog with optional role suggestion

```
┌─────────────────────── Modal ───────────────────────────────────┐
│                                                                  │
│  Invite Member                                          [ × ]   │
│                                                                  │
│  Email address                                                   │
│  ┌──────────────────────────────────────────────────┐           │
│  │ jane.doe@company.com                              │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  Workspace Role                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Member                                        ▼   │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
│  Suggest SDLC Role (optional)                                    │
│  ┌──────────────────────────────────────────────────┐           │
│  │ Tester                                        ▼   │           │
│  └──────────────────────────────────────────────────┘           │
│  This role will be shown as a suggestion during                  │
│  the invitee's onboarding. They can choose differently.         │
│                                                                  │
│                                  ┌──────────────────┐           │
│                                  │  Send Invitation  │           │
│                                  └──────────────────┘           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Dropdown Options** for "Suggest SDLC Role":
```
┌──────────────────────────────────────────────────┐
│  — No suggestion —                                │
│  📋 Business Analyst                              │
│  🎯 Product Owner                                 │
│  💻 Developer                                     │
│  🧪 Tester                                  ← ✓  │
│  🏗️ Architect                                     │
│  🔀 Tech Lead                                     │
│  📊 Project Manager                               │
│  📦 DevOps                                        │
│  ✏️ Custom...                                      │
└──────────────────────────────────────────────────┘
```

---

## Screen 6: Profile Settings — Default Role (US4)

**Route**: `/{workspaceSlug}/settings/profile`
**Context**: New section added to existing profile page

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Profile Settings                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Display Name                                                           │
│  ┌───────────────────────────────────────┐                             │
│  │ Tin Dang                               │                             │
│  └───────────────────────────────────────┘                             │
│                                                                         │
│  Email                                                                  │
│  ┌───────────────────────────────────────┐                             │
│  │ tin@pilotspace.dev                     │   (read-only)              │
│  └───────────────────────────────────────┘                             │
│                                                                         │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─          │
│                                                                         │
│  Default SDLC Role                                                      │
│  Pre-selects this role when you join a new workspace.                   │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ╔══════════════╗                 │
│  │ 📋           │  │ 🎯           │  ║ ✅ 💻        ║                 │
│  │ Business     │  │ Product      │  ║ Developer    ║                 │
│  │ Analyst      │  │ Owner        │  ║   selected   ║                 │
│  └──────────────┘  └──────────────┘  ╚══════════════╝                 │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ 🧪           │  │ 🏗️           │  │ 🔀           │                 │
│  │ Tester       │  │ Architect    │  │ Tech Lead    │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐                                    │
│  │ 📊           │  │ 📦           │   Note: Only one default role.    │
│  │ Project Mgr  │  │ DevOps       │   Per-workspace roles are set     │
│  └──────────────┘  └──────────────┘   in workspace Settings > Skills. │
│                                                                         │
│                                                  ┌──────────────┐      │
│                                                  │  Save Changes │      │
│                                                  └──────────────┘      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Single-select grid**: Only 1 role selectable (unlike onboarding which allows up to 3). Smaller cards `120px × 100px`.

---

## Screen 7: Confirmation Dialogs

### 7A. Remove Role

```
┌─────────────────────── Dialog ──────────────────────────────────┐
│                                                                  │
│  Remove Tester Role?                                    [ × ]   │
│                                                                  │
│  This will deactivate the Tester skill for this workspace.      │
│  The AI assistant will no longer use Tester-specific             │
│  behavior in your conversations.                                 │
│                                                                  │
│  Your skill content will be permanently deleted.                 │
│                                                                  │
│              ┌──────────────┐  ┌──────────────┐                 │
│              │    Cancel     │  │ Remove Role  │                 │
│              └──────────────┘  └──────────────┘                 │
│               (outline)         (destructive)                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 7B. Reset to Default

```
┌─────────────────────── Dialog ──────────────────────────────────┐
│                                                                  │
│  Reset to Default Template?                             [ × ]   │
│                                                                  │
│  This will replace your custom Developer skill with the          │
│  default Developer template. All customizations will be lost.    │
│                                                                  │
│              ┌──────────────┐  ┌──────────────┐                 │
│              │    Cancel     │  │ Reset Skill  │                 │
│              └──────────────┘  └──────────────┘                 │
│               (outline)         (destructive)                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Screen 8: Show Examples (US2 — Path 3)

```
┌─────────────────────────────────────────────────────────────────┐
│  Skill Setup  ·  Developer                      [← Back]       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   💡  How a Developer Skill Changes AI Behavior                 │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  Example 1: Reviewing an Issue                         │     │
│  │                                                        │     │
│  │  You ask: "Review this issue about adding caching"     │     │
│  │                                                        │     │
│  │  ┌─ Without skill ──────────────────────────────────┐ │     │
│  │  │ Here are some thoughts on adding caching:        │ │     │
│  │  │ - Consider what data to cache                    │ │     │
│  │  │ - Think about cache invalidation                 │ │     │
│  │  │ - Review performance requirements                │ │     │
│  │  └──────────────────────────────────────────────────┘ │     │
│  │                                                        │     │
│  │  ┌─ With Developer skill ──── ✨ ────────────────────┐ │     │
│  │  │ Architecture recommendation for caching:          │ │     │
│  │  │ - Use Redis with read-through pattern            │ │     │
│  │  │ - Set TTL based on data volatility (30m hot,     │ │     │
│  │  │   7d cold) matching your existing patterns       │ │     │
│  │  │ - Add cache-aside for frequently queried         │ │     │
│  │  │   endpoints (GET /issues, GET /notes)            │ │     │
│  │  │ - ⚠️ Watch for N+1 in the repository layer      │ │     │
│  │  │ - Suggest: Add integration test for cache miss   │ │     │
│  │  └──────────────────────────────────────────────────┘ │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  Example 2: Writing a Note                             │     │
│  │  ...similar before/after comparison...                 │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│                      [ ← Back to Options ]                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Example Card Specs**:
- "Without skill" block: `--background-subtle` bg, `--border` border
- "With skill" block: `--ai-muted` bg, `--ai-border` border, `✨` sparkle icon
- Comparison layout: stacked (not side-by-side for readability)

---

## Interaction Flow Summary

```
                    ┌─────────────┐
                    │  Onboarding  │
                    │  Checklist   │
                    └──────┬──────┘
                           │
                    Click "Set Up Role"
                           │
                    ┌──────▼──────┐
                    │    Screen 1  │
                    │ Role Select  │◄──────── Default role badge
                    │  (grid)      │◄──────── Owner hint badge
                    └──────┬──────┘
                           │
                   Continue to Skill Setup
                           │
                    ┌──────▼──────┐
                    │    Screen 2A │
                    │ Path Select  │
                    └──┬───┬───┬──┘
                       │   │   │
           ┌───────────┘   │   └───────────┐
           │               │               │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
    │  Use Default │ │  Describe  │ │   Examples  │
    │  (instant)   │ │  Expertise │ │   (Screen 8)│
    └──────┬──────┘ └─────┬──────┘ └─────────────┘
           │              │
           │       ┌──────▼──────┐
           │       │  Screen 2C  │
           │       │  Generating │
           │       └──────┬──────┘
           │              │
           │       ┌──────▼──────┐
           │       │  Screen 2D  │
           └──────►│   Preview   │
                   └──────┬──────┘
                          │
                   Save & Activate
                          │
                   ┌──────▼──────┐
                   │  Screen 3   │
                   │  Checklist  │
                   │  (updated)  │
                   └──────┬──────┘
                          │
                   Later, from Settings
                          │
                   ┌──────▼──────┐
                   │  Screen 4   │
                   │  Skills Tab │
                   │  (CRUD)     │
                   └─────────────┘
```

---

## Responsive Breakpoints

| Breakpoint | Role Grid | Skill Preview | Settings Cards |
|------------|-----------|---------------|----------------|
| Desktop (>1024px) | 3 columns | Side-by-side diff | Full width |
| Tablet (768-1024px) | 3 columns | Stacked diff | Full width |
| Mobile (<768px) | 2 columns | Stacked diff | Full width, compact |

**Mobile Adaptations**:
- Role cards: `120px × 100px` (smaller icons, abbreviated descriptions)
- Skill editor: Full-screen modal instead of inline
- Diff view: Tabbed ("Current" / "New") instead of side-by-side

---

## Accessibility Checklist

| Element | Requirement | Implementation |
|---------|-------------|----------------|
| Role cards | Keyboard selectable | `role="checkbox"`, `aria-checked`, Space/Enter toggle |
| Multi-select | Announce count | `aria-live="polite"` region: "2 of 3 roles selected" |
| Primary badge | Screen reader | `aria-label="Primary role"` on first selected |
| Skill editor | Focus management | Focus trap in editor, Escape to cancel |
| Word count | Live region | `aria-live="polite"` for word count updates |
| Loading state | Announce progress | `role="progressbar"`, `aria-valuenow` |
| Diff preview | Labeled regions | `aria-label="Current skill"` / `"New skill"` |
| Dialogs | Focus trap | Modal focus management, Escape to close |
| Color contrast | WCAG 2.2 AA | All text meets 4.5:1 ratio minimum |
| Skip link | Navigation | "Skip to skill content" for settings page |
