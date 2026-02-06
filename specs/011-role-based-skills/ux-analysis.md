# UX Analysis: Role-Based Skills (Feature 011)

**Author**: UX Designer
**Date**: 2026-02-06
**Status**: Revised (v2 -- UI Design Spec compliance)
**Blocks**: Task #7 (frontend onboarding flow), Task #8 (skills settings page)

---

## Executive Summary

This document provides a detailed UX analysis for integrating role-based skills into the existing Pilot Space frontend. It covers four areas:

1. **Role Selection Step** -- integration into the existing 3-step onboarding checklist
2. **Skill Generation Wizard** -- three-path flow with AI generation
3. **Skills Settings Tab** -- CRUD operations in workspace settings
4. **Accessibility Review** -- WCAG 2.2 AA compliance for all flows

The analysis is based on reading the existing code (`OnboardingChecklist.tsx`, `OnboardingStepItem.tsx`, `settings/layout.tsx`, `ai-settings-page.tsx`, `invite-member-dialog.tsx`) and the wireframes in `specs/011-role-based-skills/wireframes.md`.

---

## 1. Role Selection Step -- Onboarding Integration

### 1.1 Current State Analysis

**File**: `frontend/src/features/onboarding/components/OnboardingChecklist.tsx`

The existing onboarding is a **parallel checklist** (Dialog modal) with 3 steps:
- `ai_providers` -- Navigate to settings/ai-providers
- `invite_members` -- Navigate to settings/members
- `first_note` -- Create a guided note

Key observations:
- `OnboardingStep` type defined at `frontend/src/services/api/onboarding.ts:14` only includes 3 values
- `STEP_CONFIG` at `OnboardingChecklist.tsx:43-70` is a `Record<OnboardingStep, {...}>` with icon types limited to `'key' | 'users' | 'note'`
- Steps rendered in fixed order at line 169: `['ai_providers', 'invite_members', 'first_note']`
- `handleStepAction` at line 126 switches on step type -- each step either navigates away or triggers an action

### 1.2 Integration Design

**Step ordering**: `ai_providers` -> `invite_members` -> `role_setup` -> `first_note`

The `role_setup` step is unique because it does NOT navigate away from the dialog. Instead, it opens a **sub-flow within the dialog**. This requires a state machine to track which view is active.

#### Required Type Changes

**`frontend/src/services/api/onboarding.ts`**:
```typescript
// Line 14: Add 'role_setup' to the union
export type OnboardingStep = 'ai_providers' | 'invite_members' | 'role_setup' | 'first_note';

// Line 19-23: Add to steps interface
export interface OnboardingSteps {
  ai_providers: boolean;
  invite_members: boolean;
  role_setup: boolean;
  first_note: boolean;
}
```

**`OnboardingChecklist.tsx`**: Add to `STEP_CONFIG`:
```typescript
role_setup: {
  title: 'Set Up Your Role',
  description: 'Personalize your AI assistant for your SDLC role',
  actionLabel: 'Set Up',
  icon: 'wand', // Wand2 from lucide-react
},
```

**`OnboardingStepItem.tsx`**: Add `'wand'` to icon type union and map:
```typescript
// Line 36-40: Add Wand2
import { Check, Key, Users, FileText, ArrowRight, Wand2 } from 'lucide-react';
const ICON_MAP = { key: Key, users: Users, note: FileText, wand: Wand2 };
```

#### Sub-flow State Machine

The `role_setup` step click does NOT navigate away. It transitions the dialog content to a sub-flow. This needs a `roleSetupView` state:

```
checklist (default)
  |
  click "Set Up"
  |
  v
role_grid  -->  skill_wizard_path_select  -->  skill_wizard_describe
  |                     |                            |
  [Skip]            [Use Default]              [Generate]
  |                     |                            |
  v                     v                            v
checklist         skill_preview  <----------  skill_generating
                       |
                  [Save & Activate]
                       |
                       v
                  checklist (role_setup marked complete)
```

**Implementation approach**: Add state to `OnboardingChecklist`:
- `roleSetupView: 'checklist' | 'role_grid' | 'path_select' | 'describe' | 'generating' | 'preview' | 'examples'`
- When `roleSetupView !== 'checklist'`, render the sub-flow component instead of the checklist
- Back button returns to previous sub-flow step or back to checklist

#### Component Hierarchy

```
OnboardingChecklist (existing - modified)
  |-- OnboardingStepItem (existing - modified, add 'wand' icon)
  |-- RoleSetupFlow (NEW - sub-flow container)
      |-- RoleSelectionGrid (NEW)
      |   |-- RoleCard (NEW - reusable, shared with settings)
      |   |-- CustomRoleInput (NEW)
      |-- SkillGenerationWizard (NEW)
      |   |-- PathSelector (NEW)
      |   |-- ExpertiseInput (NEW)
      |   |-- GeneratingState (NEW)
      |   |-- SkillPreview (NEW)
      |   |-- ExamplesView (NEW)
      |   |-- ErrorFallback (NEW)
      |-- SkillPreviewPanel (NEW - shared with settings regeneration)
```

### 1.3 Role Grid Interaction Design

**Grid layout**: 3 columns x 3 rows = 9 items (8 predefined + 1 custom)

**Card dimensions**: `160px x 140px` per wireframe. Responsive: 3 cols on desktop/tablet, 2 cols on mobile.

**Card styling** (interactive card variant per Section 5):
- Border radius: `rounded-lg` (14px)
- Shadow: Shadow SM (default), Shadow Elevated (hover)
- Hover: `translateY(-2px)`, `scale(1.01)`, Shadow Elevated, 200ms ease transition
- Active: return to baseline, `scale(0.99)`
- Noise texture overlay: 2% opacity, multiply blend on card surface
- Focus ring: 3px `--primary` at 30% opacity (no outline)

**Selection behavior**:
1. Click a card to select (max 3)
2. First selected becomes PRIMARY (shown with `PRIMARY` label and number badge `(1)`)
3. Subsequent selections get number badges `(2)`, `(3)`
4. Clicking a selected card deselects it
5. If primary is deselected, the next selected becomes primary
6. At max (3 selected), remaining cards show `opacity-50` and `cursor-not-allowed`

**Pre-selection states** (mutually visible):
- **"Your default"** badge: `--primary` text, `--primary-muted` bg, star icon. Source: user's profile `default_sdlc_role`. Card has `--primary` border but is NOT auto-selected (just highlighted).
- **"Suggested by owner"** badge: `--ai` text, `--ai-muted` bg, user icon. Source: `WorkspaceInvitation.suggested_sdlc_role`. Card is pre-SELECTED (user can deselect).

**Custom Role**: Clicking "Custom Role" card transitions to a text area input view within the same dialog. No manual name input -- AI generates the name. A "Back to grid" link returns to the grid. The textarea has a 5000-character limit with counter.

**"Continue to Skill Setup" button**: Enabled only when >= 1 role is selected. Button text dynamically updates: "Continue to Skill Setup" (1 role) / "Set Up 2 Skills" (2 roles) / "Set Up 3 Skills" (3 roles).

### 1.4 Selection Summary Bar

Below the grid, a summary bar shows:
- Selected roles with primary designation: "Developer (primary) . Tester"
- Remaining slots: "1 more role available"
- This bar uses `--background-subtle` bg, `--border` border, `text-sm` (13px)

---

## 2. Skill Generation Wizard

### 2.1 Path Selection (Screen 2A from wireframes)

After clicking "Continue to Skill Setup", the dialog transitions to the path selection view.

**Header**: "Skill Setup . {RoleName}" with a `[Back]` button to return to role grid.

**Three path cards** (full-width, stacked, interactive card variant with hover translateY + shadow):
1. **Use Default {Role} Skill** -- instant, no AI call. Shows default template in preview.
2. **Describe Your Expertise** -- recommended path (marked with `REC` badge: `--primary-muted` bg, `--primary` text, `rounded-sm` pill, `text-xs font-semibold`). Opens textarea.
3. **Show Me Examples** -- educational, no generation. Shows before/after comparisons.

**Multi-role handling**: If user selected 2+ roles, the wizard processes them sequentially. Header shows "Skill Setup . Developer (1 of 2)". After completing the first role's skill, auto-advance to the next.

### 2.2 Describe Expertise Input (Screen 2B)

- Textarea: 5000 char limit, min 10 chars required
- Placeholder text: "Tell us about your experience, specializations, tools you use, and how you like to work..."
- Character counter: `{count} / 5000 characters`
- Helper text: "We'll also generate a personalized role name from this."
- "Generate Skill" button: disabled until min 10 chars. Uses AI button variant (`--ai` color).

### 2.3 Generating State (Screen 2C)

- Loading pattern: Status text with animated ellipsis (per Section 12 Loading States). Text: "Generating your {Role} skill..." with CSS-animated ellipsis (`...` cycling)
- Status text: `text-base` (15px) `--foreground`, centered
- Subtitle: `text-sm` (13px) `--foreground-muted`: "Our AI is crafting a personalized skill based on your expertise. This takes about 15-30 seconds."
- Progress bar: `--ai` fill, `--border` track, `h-1` (4px), `rounded-full`. Indeterminate initially, then fills based on SSE progress events if available. Fallback: animate from 0% to 90% over 25s, hold at 90% until complete.
- No back button during generation (prevent double-submission)

### 2.4 Skill Preview (Screen 2D)

**Role name field**: Editable inline input pre-filled with AI-generated `suggested_role_name`.
- For predefined roles: AI enhances the name (e.g., "Developer" -> "Senior Full-Stack TypeScript Developer")
- For custom roles: AI generates the name entirely
- Input: `text-lg font-semibold` (17px), `--background` bg, `1px solid --border`, rounded (10px), pencil edit icon on right
- Focus state: `--primary` border, 3px primary ring at 30% opacity
- When edited, the `# heading` inside the skill content auto-updates to match

**Skill content preview**:
- Rendered markdown in a scrollable container (max-height 400px)
- `--background-subtle` bg, `1px solid --border`
- Word count: `text-xs` (11px), `--foreground-muted`. Turns `--destructive` at 1800+.
- "Generated by AI" badge: `--ai-muted` bg, `--ai` text, `rounded-full` pill, top-right

**Action buttons** (all buttons: hover scale 2% + elevated shadow, active scale back 2%, focus 3px `--primary` ring at 30%):
- **Save & Activate** (primary): Saves skill, marks role_setup step complete, returns to checklist
- **Customize** (secondary/outline): Opens the skill editor inline (same as settings edit mode)
- **Retry** (ghost): Re-runs generation with same inputs

### 2.5 Error Fallback (Screen 2E)

- Warning banner: `--warning-muted` bg (Amber at 10% opacity, `#D9853F1A`), `4px` left border `#D9853F`, TriangleAlert icon
- Message: "We couldn't reach the AI provider. We've loaded the default {Role} template instead."
- Reassurance: "Your experience description has been saved -- you can retry generation later from Settings."
- Shows default template in preview area
- Actions: **Save Default** (primary), **Retry Generation** (outline, `--ai` border)

### 2.6 Show Examples (Screen 8)

- 2-3 before/after comparison cards per role
- "Without skill" block: `--background-subtle` bg, `--border` border
- "With {Role} skill" block: `--ai-muted` bg, `--ai-border` border, sparkle icon
- Stacked layout (not side-by-side) for better readability in the dialog
- "Back to Options" button at bottom to return to path selection
- Optional: "Use Default Skill" CTA at bottom for users who are satisfied after seeing examples

---

## 3. Skills Settings Tab

### 3.1 Settings Navigation Integration

**File**: `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx`

Add "Skills" nav item to the "Account" section (lines 58-74):

```typescript
{
  label: 'Account',
  items: [
    { id: 'profile', label: 'Profile', icon: User, href: ... },
    { id: 'ai-providers', label: 'AI Providers', icon: Sparkles, href: ... },
    // NEW:
    { id: 'skills', label: 'Skills', icon: Wand2, href: (slug) => `/${slug}/settings/skills` },
  ],
},
```

**Rationale**: Skills are per-user-per-workspace, fitting the "Account" section alongside Profile and AI Providers.

**"NEW" badge**: Show a pulsing `--primary` badge next to "Skills" nav item if the user has no roles configured. Remove badge once at least one skill is saved.

### 3.2 Skills Page Layout

**Route**: `/{workspaceSlug}/settings/skills`
**File**: `frontend/src/features/settings/pages/skills-settings-page.tsx` (new)

Follows the `ai-settings-page.tsx` pattern:
- `observer()` wrapper
- `max-w-3xl px-8 py-6` container
- Header: "AI Skills" h1 + "Configure how the AI assistant adapts to your role." description
- `[+ Add Role]` button in header, right-aligned. Shows "(X slot(s) left)" below. Disabled at 3 roles.
- Loading: skeleton pattern matching ai-settings-page
- Error: Alert with destructive variant

### 3.3 Role Skill Cards

Each configured role renders as a card:

**Primary role card** (elevated card variant):
- Border: `2px solid --primary`
- Background: `--primary-muted`
- Border radius: `rounded-lg` (14px)
- Shadow: Shadow (standard card depth)
- Badge: "PRIMARY" in `--primary` bg, white text, `text-xs font-semibold`, `rounded-sm` pill, top-right

**Secondary role cards** (default card variant):
- Border: `1px solid --border`
- Background: `--card`
- Border radius: `rounded-lg` (14px)
- Shadow: Shadow SM

**Card content**:
- Header row: Icon + Role name + badges (PRIMARY if applicable)
- Skill content area: `--background` bg, `1px solid --border-subtle`, max-height `200px` collapsed with "Show more" expand toggle
- Word count: `text-xs` (11px) `--foreground-muted`
- Action buttons row (`gap-2`, 8px):
  - **Edit** (outline): Opens inline editor
  - **Regenerate AI** (outline, `--ai` border): Opens regeneration modal
  - **Reset** (ghost): Confirmation dialog, then revert to default template
  - **Remove** (ghost, `--destructive`): Confirmation dialog, then delete role+skill

### 3.4 Inline Skill Editor (Screen 4C)

When "Edit" is clicked, the card transitions to edit mode:

**Editor toolbar**: Mini markdown toolbar (Bold, Italic, H1, H2, H3, List, Code Block).
- Use a simple toolbar, not full TipTap (skill content is stored as plain markdown, not TipTap JSON).
- Toolbar buttons: `h-8` (32px, `icon-sm` size), icon-only, `--border` border, `--background` bg, `rounded` (10px).

**Editor area**:
- Textarea or lightweight markdown editor
- `--background` bg, min-height `300px`
- Monospace font (Geist Mono) for markdown editing
- Auto-resize to content

**Word count progress bar** (`WordCountBar` component):
- Height: `h-1` (4px), `rounded-full`
- Green (`--primary`): 0-1799 words
- Orange (`--warning`, `#D9853F`): 1800-1999 words (warning state)
- Red (`--destructive`): 2000+ words (blocked, save button disabled)
- Label: `text-xs` (11px) `--foreground-muted`, "{count} / 2000 words"

**Actions**: **Save** (primary, disabled if >2000 words), **Cancel** (ghost)

### 3.5 Regeneration Flow (Screen 4D)

Opens as a **modal dialog** (not inline):

1. **Experience textarea**: Pre-filled with stored `experience_description`. User can update.
2. **"Generate New Skill" button**: Triggers AI generation. Shows loading spinner.
3. **Diff preview** (after generation completes):
   - Side-by-side on desktop (>1024px): "Current" panel left, "New (AI Generated)" panel right
   - Tabbed on mobile (<1024px): Two tabs "Current" / "New"
   - Added lines: `--primary-muted` bg, `+` prefix in `--primary`
   - Removed lines: `--destructive-muted` (`--destructive` at 12% opacity) bg, `-` prefix in `--destructive`
4. **Actions**: **Accept New Skill** (primary), **Keep Current** (outline)

### 3.6 Empty State (Screen 4B)

When no roles are configured (per Section 17 of UI Design Spec):
- Wand2 icon, 80px, `--foreground-muted` at 40% opacity
- "No roles configured" -- `text-lg` (17px) `font-medium`, centered
- "Set up your SDLC role to personalize how the AI assistant helps you in this workspace." -- `text-sm` (13px), `--foreground-muted`, centered, `max-w-[280px]`
- "Set Up Your Role" primary button CTA, centered below description
- Container padding: `py-12` (48px vertical)
- Vertical spacing between elements: `space-4` (16px)
- Clicking CTA opens the same role selection + skill generation flow as onboarding (reusing `RoleSetupFlow` component).

### 3.7 Confirmation Dialogs

**Remove Role** (Screen 7A):
- Title: "Remove {Role} Role?"
- Body: "This will deactivate the {Role} skill for this workspace. The AI assistant will no longer use {Role}-specific behavior in your conversations. Your skill content will be permanently deleted."
- Actions: Cancel (outline), Remove Role (destructive)

**Reset to Default** (Screen 7B):
- Title: "Reset to Default Template?"
- Body: "This will replace your custom {Role} skill with the default {Role} template. All customizations will be lost."
- Actions: Cancel (outline), Reset Skill (destructive)

### 3.8 Max Roles State (Screen 4E)

When 3 roles are configured:
- `[+ Add Role]` button is disabled
- Warning banner below header: "Maximum 3 roles per workspace reached. Remove an existing role to add a new one."
- Warning style: `--background-subtle` bg, `--border` border, info icon

### 3.9 Guest View (Screen 4F)

When the user has guest role:
- Lock icon + message: "Role skill configuration requires Member or higher access. Contact a workspace admin for permission."
- No action buttons visible
- No "Add Role" button

---

## 4. Invite Dialog Enhancement (US5)

### 4.1 Integration Point

**File**: `frontend/src/features/settings/components/invite-member-dialog.tsx`

Add an optional "Suggest SDLC Role" dropdown between the existing "Role" select and the submit button (after line 180).

### 4.2 Design

**New field**:
- Label: "Suggest SDLC Role (optional)"
- Select dropdown with options: "-- No suggestion --" (default), then all 8 predefined roles + "Custom..." option
- Helper text below: "This role will be shown as a suggestion during the invitee's onboarding. They can choose differently."
- When "Custom..." is selected, a text input appears below for a free-text role description.

**No changes** to existing email/role fields. The SDLC role hint is stored separately from the workspace permission role.

---

## 5. Profile Default Role (US4)

### 5.1 Integration Point

**Route**: `/{workspaceSlug}/settings/profile`

Add a "Default SDLC Role" section below existing profile fields (Display Name, Email).

### 5.2 Design

- Section separator above
- Section title: "Default SDLC Role"
- Description: "Pre-selects this role when you join a new workspace."
- **Single-select** role grid (NOT multi-select like onboarding)
- Smaller cards: `120px x 100px`
- Only 8 predefined roles (no Custom option for default -- custom is per-workspace)
- Note text: "Only one default role. Per-workspace roles are set in workspace Settings > Skills."
- Save Changes button

---

## 6. Accessibility Review (WCAG 2.2 AA)

### 6.1 Role Selection Grid

| Element | Requirement | Implementation |
|---------|-------------|----------------|
| Grid container | Group semantics | `role="group"`, `aria-label="Select your SDLC roles"` |
| Role card | Checkable | `role="checkbox"`, `aria-checked={isSelected}`, `tabIndex={0}` |
| Multi-select count | Live announcement | `aria-live="polite"` region: "2 of 3 roles selected. Developer is primary." |
| Primary badge | Screen reader context | `aria-label="Primary role"` on the badge, or `aria-description` on the card |
| "Your default" badge | Informational | Include in card's `aria-label`: "Developer. Your default role." |
| "Suggested by owner" badge | Informational | Include in card's `aria-label`: "Tester. Suggested by workspace owner." |
| Disabled cards (at max) | Communicate state | `aria-disabled="true"`, `aria-label` includes "Maximum roles reached" |
| Grid navigation | Keyboard | Arrow keys navigate between cards, Space/Enter toggles selection |
| Custom Role textarea | Standard form | `aria-label="Describe your custom role"`, `aria-describedby` for char count |

### 6.2 Skill Generation Wizard

| Element | Requirement | Implementation |
|---------|-------------|----------------|
| Path cards | Navigable | `role="radio"`, `aria-checked`, within `role="radiogroup"` |
| Recommended badge | Announced | `aria-label` on card includes "Recommended" |
| Expertise textarea | Standard form | Label, describedby for char count and min chars |
| Generate button | Loading state | `aria-busy="true"`, `aria-disabled="true"` during generation |
| Progress indicator | Live region | `role="progressbar"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"` |
| Loading text | Announced | `aria-live="assertive"`: "Generating your Developer skill. Please wait." |
| Skill preview | Labeled | `aria-label="Generated skill preview"` |
| Role name input | Editable field | `aria-label="Role name. Auto-generated by AI. Click to edit."` |
| Word count | Live update | `aria-live="polite"` for count changes. `role="status"` for warning/error. |
| Error fallback | Alert | `role="alert"` on the warning banner |

### 6.3 Skills Settings Tab

| Element | Requirement | Implementation |
|---------|-------------|----------------|
| Tab navigation | Active tab | `aria-current="page"` on active Skills nav link (existing pattern) |
| "Add Role" button | Disabled state | `aria-disabled="true"` with `aria-describedby` explaining "Maximum 3 roles reached" |
| Role cards | Landmarks | Each card is an `<article>` with `aria-label="Developer role skill"` |
| Expand/collapse | Toggle | `aria-expanded`, `aria-controls` linking to content area |
| Inline editor | Focus trap | Focus moves to editor on open, Escape cancels, focus returns to Edit button |
| Word count bar | Semantic | `role="meter"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="2000"`, `aria-label="Word count"` |
| Diff preview | Regions | `aria-label="Current skill version"` / `aria-label="New skill version"` |
| Confirmation dialogs | Modal semantics | `role="alertdialog"`, `aria-describedby` linking to body text, focus trap |
| Guest read-only | Informational | `role="alert"` on the permission message |

### 6.4 Keyboard Navigation Summary

| Context | Key | Action |
|---------|-----|--------|
| Role grid | Tab | Move focus to grid |
| Role grid | Arrow keys | Navigate between cards |
| Role grid | Space/Enter | Toggle card selection |
| Role grid | Escape | Close dialog / return to checklist |
| Path selector | Tab | Move between path cards |
| Path selector | Enter | Select path |
| Skill editor | Tab | Move between toolbar buttons, then to editor |
| Skill editor | Escape | Cancel editing, return to view mode |
| Dialogs | Tab | Cycle through focusable elements (trapped) |
| Dialogs | Escape | Close dialog |

### 6.5 Color Contrast Verification

| Element | Foreground | Background | Ratio | Pass? |
|---------|-----------|-----------|-------|-------|
| Primary text | #171717 | #FDFCFA | 15.3:1 | Yes |
| Muted text | #737373 | #FDFCFA | 4.9:1 | Yes (AA) |
| Primary on muted bg | #29A386 | #FDFCFA | 3.7:1 | Needs large text or non-text use only |
| AI text on AI bg | #6B8FAD | #FDFCFA | 3.5:1 | Use with icon + text (compound indicator) |
| Destructive | #D9534F | #FDFCFA | 4.1:1 | Borderline - pair with icon |
| Badge text (white on primary) | #FFFFFF | #29A386 | 3.7:1 | Large text only (badges are 10-11px, use bold) |

**Recommendations**:
- For `--primary` (#29A386) used as text, ensure it is paired with an icon or used as non-text indicator (border, background). The 3.7:1 ratio passes for large text (18px+ or 14px+ bold) but not for body text.
- For the "PRIMARY" badge (white on #29A386), increase badge font weight to bold/semibold at 11px. Alternatively, darken the primary to #1F8A6E for 4.5:1 ratio within badges.
- Destructive (#D9534F) at 4.1:1 -- always pair with an icon (trash icon + "Remove" text).

### 6.6 Focus Ring Styling

All new interactive elements use the unified focus ring style (per Section 12 Focus States):
- 3px ring in `--primary` at 30% opacity
- No default outline (`outline: none`)
- Applied via `focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none`
- Consistent across RoleCard, path cards, buttons, editor, inputs, and dialog elements

### 6.7 Motion and Animation

- All animations MUST respect `prefers-reduced-motion`
- Pulse animation on "NEW" badge: `motion-safe:animate-pulse`
- Card hover translateY: `motion-safe:hover:-translate-y-0.5`
- Button hover scale: `motion-safe:hover:scale-[1.02]`
- Status text animated ellipsis: CSS keyframe, essential animation, keep
- Progress bar fill: essential for feedback, keep
- Theme transition: 200ms on `background-color` and `color`

---

## 7. Dark Mode Support

All new components must support dark mode using CSS custom property tokens (Section 16 of UI Design Spec). Toggle via `class="dark"` on `<html>`, respects `prefers-color-scheme`.

### 7.1 Token Mapping for New Components

| Component | Light Token | Dark Token | Notes |
|-----------|-----------|-----------|-------|
| **RoleCard bg** | `--background-subtle` (#F7F5F2) | `--background-subtle` (#1F1F1F) | Auto via CSS vars |
| **RoleCard border** | `--border` (#E5E2DD) | `--border` (#2E2E2E) | Auto via CSS vars |
| **RoleCard selected bg** | `--primary-muted` (#29A38615) | `--primary-muted` (#34B89620) | Slightly higher opacity in dark |
| **RoleCard selected border** | `--primary` (#29A386) | `--primary` (#34B896) | Brighter in dark for contrast |
| **SkillPreview bg** | `--background-subtle` (#F7F5F2) | `--background-subtle` (#1F1F1F) | Scrollable content area |
| **SkillPreview border** | `--border-subtle` (#EBE8E4) | `--border-subtle` (#262626) | Auto via CSS vars |
| **WordCountBar track** | `--border` (#E5E2DD) | `--border` (#2E2E2E) | Auto via CSS vars |
| **WordCountBar fill (ok)** | `--primary` (#29A386) | `--primary` (#34B896) | Auto via CSS vars |
| **WordCountBar fill (warn)** | `#D9853F` | `#D9853F` | Same -- amber is visible on both |
| **WordCountBar fill (error)** | `--destructive` (#D9534F) | `--destructive` (#E06560) | Slightly brighter in dark |
| **Diff added bg** | `--primary-muted` | `--primary-muted` | Auto, higher opacity dark |
| **Diff removed bg** | `--destructive-muted` | `--destructive-muted` | Auto, higher opacity dark |
| **Warning banner bg** | `--warning-muted` (#D9853F1A) | `--warning-muted` (#D9853F26) | Higher opacity in dark for visibility |
| **Warning banner border** | `#D9853F` | `#D9853F` | Same -- amber visible on both |
| **"Generated by AI" badge** | `--ai-muted` bg, `--ai` text | `--ai-muted` bg, `--ai` text | Auto via CSS vars, brighter in dark |
| **"PRIMARY" badge** | `--primary` bg, white text | `--primary` bg, white text | Auto, brighter primary in dark |

### 7.2 Dark Mode Behavior for New Components

| Component | Dark Mode Treatment |
|-----------|-------------------|
| **RoleCard** | `--card` (#222222) bg, elevated slightly from `--background`. Shadows reduced opacity, no warm tint. |
| **SkillPreview** | `--background-subtle` (#1F1F1F). Markdown code blocks use dark syntax theme (VS Code Dark+). |
| **Generating State** | Progress bar `--ai` fill maintains contrast. Animated ellipsis uses `--foreground`. |
| **Diff Preview** | Added/removed line backgrounds use higher opacity (20% vs 15%) for visibility on dark surfaces. Panel headers use `--foreground-muted`. |
| **Skill Editor** | `--input` (#1E1E1E) bg. Toolbar buttons use `--card` bg. Monospace code in Geist Mono with dark theme. |
| **Empty State** | Icon at 40% opacity on both themes. No noise texture in dark mode (per Section 16). |
| **Dialogs/Modals** | Frosted glass with darker backdrop, higher blur (per Section 16). `--popover` (#252525) bg. |

### 7.3 Implementation Notes

- All new components MUST use CSS custom properties (`var(--token)`) for colors, never hardcoded hex values
- Noise texture overlay (2% opacity, multiply blend) is applied in light mode only; removed in dark mode
- Transition: 200ms on `background-color` and `color` properties when toggling themes
- Test contrast ratios for `--ai` (#7DA4C4) on `--card` (#222222) in dark mode: 5.8:1 (passes AA)
- Test contrast ratios for `--primary` (#34B896) on `--card` (#222222) in dark mode: 5.1:1 (passes AA)

---

## 8. Responsive Design

All new components follow the breakpoint system from Section 15 of the UI Design Spec.

### 8.1 Breakpoints Reference

| Name | Value | Typical Device |
|------|-------|----------------|
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet portrait |
| `lg` | 1024px | Tablet landscape |
| `xl` | 1280px | Desktop |

### 8.2 Onboarding Dialog (Role Setup Sub-flow)

| Breakpoint | Role Grid | Skill Wizard | Dialog Width |
|------------|-----------|-------------|--------------|
| `xl+` (>1280px) | 3 columns, 160x140 cards | Full-width path cards, side-by-side examples | `max-w-xl` (per existing checklist) |
| `lg` (1024-1279px) | 3 columns, 160x140 cards | Full-width path cards | `max-w-xl` |
| `md` (768-1023px) | 3 columns, smaller cards (140x120) | Full-width path cards | `max-w-lg` |
| `sm` (<768px) | 2 columns, compact cards (120x100), abbreviated descriptions | Stacked layout, full-screen dialog | Full-screen modal |

**Mobile adaptations**:
- Role card descriptions hidden below `sm`, only icon + title visible
- "Continue to Skill Setup" button becomes fixed to bottom of dialog
- Skill preview max-height reduced to 300px
- Touch targets: minimum 44px for all interactive elements

### 8.3 Skill Generation Wizard

| Breakpoint | Path Selection | Expertise Input | Preview | Generating |
|------------|---------------|----------------|---------|-----------|
| `lg+` | Stacked cards, 100px height | Textarea fills width | Scrollable 400px max-height | Centered with progress bar |
| `md` | Stacked cards, reduced padding | Textarea fills width | Scrollable 300px max-height | Centered |
| `sm` | Stacked cards, compact | Full-screen textarea | Full-screen preview with bottom actions | Full-screen centered |

### 8.4 Skills Settings Page

| Breakpoint | Layout | Skill Cards | Editor | Diff Preview |
|------------|--------|------------|--------|-------------|
| `xl+` | `max-w-3xl px-8 py-6` | Full-width cards, expanded content 200px | Inline with toolbar | Side-by-side panels |
| `lg` | `max-w-3xl px-6 py-6` | Full-width cards | Inline with toolbar | Side-by-side panels |
| `md` | `max-w-2xl px-4 py-4` | Full-width cards, collapsed content 150px | Full-width inline | Tabbed ("Current" / "New") |
| `sm` | Full-width `px-4 py-4` | Full-width cards, collapsed 100px | Full-screen modal editor | Tabbed, full-screen modal |

**Mobile adaptations**:
- Settings sidebar collapses to hamburger menu (existing pattern in `layout.tsx`)
- Skill editor opens as full-screen modal on mobile instead of inline
- Action buttons stack vertically (2 per row) instead of horizontal row
- Regeneration dialog becomes full-screen on mobile
- "Add Role" button moves into a FAB (floating action button) on mobile

### 8.5 Profile Default Role Grid

| Breakpoint | Layout |
|------------|--------|
| `lg+` | 4 columns, 120x100 cards |
| `md` | 3 columns |
| `sm` | 2 columns, 100x80 cards |

---

## 9. Component Reuse Matrix

| Component | Onboarding | Settings | Profile |
|-----------|-----------|----------|---------|
| `RoleCard` | Yes (multi-select, 160x140) | Yes (display-only with actions) | Yes (single-select, 120x100) |
| `RoleSelectionGrid` | Yes | Yes (via "Add Role") | Yes (single-select variant) |
| `SkillPreview` | Yes (read-only with actions) | Yes (collapsed/expandable) | No |
| `SkillEditor` | Yes (customize path) | Yes (inline edit) | No |
| `SkillGenerationWizard` | Yes (full flow) | Yes (via "Add Role" and "Regenerate") | No |
| `GeneratingState` | Yes | Yes (regeneration) | No |
| `DiffPreview` | No | Yes (regeneration modal) | No |
| `WordCountBar` | Yes (preview) | Yes (editor) | No |
| `ConfirmationDialog` | No | Yes (remove, reset) | No |

**Key reuse**: `RoleCard` must be designed as a flexible component with variants:
- `selectable` (onboarding/settings "Add Role"): clickable, shows checkbox state
- `display` (settings): shows content, action buttons
- `singleSelect` (profile): radio-like, smaller size

---

## 10. State Management Recommendations

### 10.1 New MobX Store: RoleSkillStore

Following the MobX-for-UI-state pattern (DD-065):

```typescript
class RoleSkillStore {
  // UI state only
  roleSetupView: RoleSetupView = 'checklist';
  selectedRoles: SelectedRole[] = [];
  currentWizardRoleIndex: number = 0;
  isGenerating: boolean = false;
  generationProgress: number = 0;
  editingSkillId: string | null = null;
  regenerationModalOpen: boolean = false;
}
```

### 10.2 TanStack Query Hooks

Server state via TanStack Query:

- `useUserRoleSkills(workspaceId)` -- GET skills for current user in workspace
- `useRoleTemplates()` -- GET all predefined role templates (cacheable, staleTime: 24h)
- `useGenerateSkill()` -- POST mutation for AI skill generation
- `useSaveSkill()` -- POST/PUT mutation for saving skill
- `useDeleteSkill()` -- DELETE mutation for removing role
- `useDefaultRole()` -- GET user's default role from profile
- `useUpdateDefaultRole()` -- PUT mutation for updating default role

---

## 11. File Structure Recommendation

```
frontend/src/features/settings/
  components/
    role-card.tsx                    (shared RoleCard component)
    role-selection-grid.tsx          (grid of RoleCards, multi/single select)
    skill-preview.tsx                (markdown-rendered skill preview)
    skill-editor.tsx                 (inline markdown editor with toolbar)
    word-count-bar.tsx               (progress bar with color states)
    diff-preview.tsx                 (side-by-side/tabbed diff view)
    skill-generation-wizard.tsx      (path select -> describe -> generate -> preview)
    generating-state.tsx             (loading animation with progress)
    role-setup-flow.tsx              (orchestrates grid -> wizard in dialog)
    skills-settings-page-content.tsx (skills tab content)
    regeneration-dialog.tsx          (modal for regenerating a skill)
    examples-view.tsx                (before/after comparison cards)
  pages/
    skills-settings-page.tsx         (route page component)
```

```
frontend/src/features/onboarding/
  components/
    OnboardingChecklist.tsx          (MODIFIED - add role_setup step)
    OnboardingStepItem.tsx           (MODIFIED - add wand icon)
    RoleSetupDialog.tsx              (NEW - wraps RoleSetupFlow in dialog context)
```

---

## 12. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sub-flow in dialog vs navigate away | Sub-flow in dialog | Role setup is a cohesive multi-step process. Navigating away breaks the onboarding flow. The dialog provides containment. |
| Sequential vs parallel multi-role skill gen | Sequential per role | Simpler UX (one thing at a time). Users can see each skill before moving to the next. |
| Markdown editor vs TipTap for skill editing | Lightweight markdown editor (textarea with toolbar) | Skills are stored as markdown text, not TipTap JSON. A full TipTap setup is overkill. A textarea with a mini toolbar (bold, italic, headings, list, code) is sufficient. |
| Diff in modal vs inline | Modal for regeneration, inline for edit | Regeneration is a disruptive action (replaces content) -- modal forces deliberate choice. Editing is incremental -- inline is more natural. |
| "NEW" badge persistence | Until first skill saved | Badge draws attention to unconfigured state. Once the user has at least one skill, the value is demonstrated. |
| Skills nav placement | Account section | Skills are per-user, not per-workspace-admin. Fits alongside Profile and AI Providers. |
