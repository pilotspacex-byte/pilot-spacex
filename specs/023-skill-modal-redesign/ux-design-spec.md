# Skill Modal Redesign -- UX Design Specification

**Version**: 1.0.0
**Created**: 2026-03-18
**Status**: Draft
**Scope**: Replace `SkillGeneratorModal` with dual-mode "Add Skill" modal supporting both manual input and AI generation.
**Branch**: `feat/improve-patchs`

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Design Goals](#2-design-goals)
3. [Information Architecture](#3-information-architecture)
4. [Modal Shell Specification](#4-modal-shell-specification)
5. [Tab 1: Manual Input Mode](#5-tab-1-manual-input-mode)
6. [Tab 2: AI Generate Mode](#6-tab-2-ai-generate-mode)
7. [Component Structure](#7-component-structure)
8. [Interaction Patterns](#8-interaction-patterns)
9. [Responsive Behavior](#9-responsive-behavior)
10. [Accessibility](#10-accessibility)
11. [Implementation Guide](#11-implementation-guide)

---

## 1. Problem Statement

### Current State

The existing `SkillGeneratorModal` (`skill-generator-modal.tsx`) has two UX issues:

1. **Cramped layout.** The modal uses `sm:max-w-3xl` (48rem / 768px) with a two-panel grid (`1fr | 280px`). After the 280px guide panel and 24px padding on each side, the primary content area is only ~440px wide. The textarea (`min-h-[200px]`) and the 460px minimum height leave little breathing room, especially in the preview step where the skill name input, content textarea, word count, and action buttons are stacked vertically.

2. **AI-only creation path.** The only way to create a skill is: describe experience --> AI generates content --> preview/edit --> save. Users who already have skill markdown (pasted from a template, written externally, or copied from another workspace) must go through the AI pipeline unnecessarily. There is no way to directly type a skill name, write content, and save.

### Impact

- **Productivity loss**: Power users with pre-written skills waste 15-30 seconds on AI generation they don't need.
- **Cognitive friction**: Users who just want a quick manual skill feel forced into an opinionated flow.
- **Cramped editing**: The preview step textarea (`max-h-[220px]`) is too small for reviewing 200-500 word skill content comfortably.

---

## 2. Design Goals

| Goal | Metric | Rationale |
|------|--------|-----------|
| **Dual-mode creation** | Manual + AI Generate accessible within 1 click | Users choose their preferred path |
| **Spacious layout** | Content area >= 560px wide, textarea >= 320px tall | Comfortable reading/editing for 500-word skills |
| **Zero-friction manual path** | Name + content + save in 3 fields, no AI required | Power user efficiency |
| **AI path preserved** | Existing generate flow intact with same UX quality | No regression for AI users |
| **Design system coherence** | Uses shadcn/ui Tabs, Dialog, Input, Textarea, Button | Consistent with rest of settings pages |
| **Accessibility** | WCAG 2.1 AA, keyboard navigable tabs, focus management | Non-negotiable per project spec |

---

## 3. Information Architecture

### Entry Points (unchanged)

The modal is opened from the same sources:

1. **"Add Skill" button** on Skills settings page --> opens with Manual tab active (new default)
2. **"Use This" on a template card** --> opens with AI Generate tab active, template pre-seeded
3. Programmatic open from onboarding flow --> AI Generate tab active

### Data Model (unchanged)

The `UserSkillCreate` payload accepted by `POST /workspaces/:slug/user-skills`:

```typescript
interface UserSkillCreate {
  template_id?: string;       // optional link to workspace template
  skill_content?: string;     // the markdown skill content
  experience_description?: string; // free-text experience input
  skill_name?: string;        // display name
}
```

For **manual mode**, the required fields are `skill_name` and `skill_content`. For **AI generate mode**, the required field is `experience_description` (skill_content is produced by AI).

### User Flows

```text
Manual Flow:
  Open Modal --> Manual tab --> type name + content --> Save
                                                    --> (optional) switch to AI tab

AI Generate Flow:
  Open Modal --> AI Generate tab --> describe experience --> Generate
             --> Generating... spinner --> Preview (editable name + content) --> Save
                                       --> Retry
                                       --> Back to edit description
```

---

## 4. Modal Shell Specification

### Sizing

| Property | Current | New | Rationale |
|----------|---------|-----|-----------|
| `max-width` | `sm:max-w-3xl` (768px) | `sm:max-w-4xl` (896px) | 128px more horizontal space; still fits 1024px screens with margins |
| `max-height` | implicit via `min-h-[460px]` | `max-h-[85vh]` | Prevents overflow on smaller screens, matches `SkillDetailModal` pattern |
| Inner padding | `p-6` | `p-0` on DialogContent, `p-6` on inner sections | Allows tabs to sit edge-to-edge under header |
| Guide panel | `280px` right column | **Removed** | Tips move inline; reclaim 280px for content |

### Tailwind Classes on `<DialogContent>`

```tsx
<DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
```

### Layout Structure

```text
+----------------------------------------------------------+
| Header: "Add Skill" title + mode toggle (personal/ws)    |
|   [Close X]                                               |
+----------------------------------------------------------+
| [Manual]  [AI Generate]    <-- shadcn Tabs triggers       |
+----------------------------------------------------------+
|                                                            |
|  Tab Content Area (flex-1, overflow-y-auto)               |
|                                                            |
|  ...varies by active tab...                               |
|                                                            |
+----------------------------------------------------------+
| Footer: action buttons (sticky bottom)                    |
+----------------------------------------------------------+
```

The header, tab triggers, and footer are **fixed** (not scrollable). Only the tab content area scrolls when content overflows.

### Design Tokens Applied

```css
/* Modal shell */
--modal-radius: 12px;          /* rounded-xl, matches card radius */
--modal-border: 1px solid var(--border);
--modal-shadow: var(--shadow-lg);

/* Section spacing */
--section-padding-x: 1.5rem;   /* px-6 */
--section-padding-y: 1.25rem;  /* py-5 */

/* Tab bar */
--tab-bar-bg: var(--muted);
--tab-bar-height: 40px;
--tab-trigger-font: 13px font-medium;
```

---

## 5. Tab 1: Manual Input Mode

This is the **new** capability. Direct form entry without AI generation.

### Wireframe

```text
+------------------------------------------------------+
| Skill Name *                                          |
| [________________________ text input _____________]   |
|                                                       |
| Description (optional)                                |
| [________________________ text input _____________]   |
| Brief description of what this skill covers           |
|                                                       |
| Skill Content *                   [toolbar: B I H1...]|
| +--------------------------------------------------+ |
| |                                                    | |
| | # Senior Backend Developer                        | |
| |                                                    | |
| | ## Expertise                                       | |
| | - Python, FastAPI, PostgreSQL                      | |
| | - Clean architecture, async patterns               | |
| |                                                    | |
| | ## Communication Style                             | |
| | Concise code reviews, security-first mindset       | |
| |                                                    | |
| +--------------------------------------------------+ |
| ================================================ bar  |
| 127 / 2000 words                                      |
|                                                       |
| Tip: The more specific your skill, the better the    |
| AI personalizes responses.                            |
+------------------------------------------------------+
| [Cancel]                              [Save Skill]   |
+------------------------------------------------------+
```

### Field Specifications

#### Skill Name (required)

| Property | Value |
|----------|-------|
| Component | `<Input>` from shadcn/ui |
| id | `"manual-skill-name"` |
| placeholder | `"e.g. Senior Backend Developer"` |
| maxLength | `200` |
| Validation | Non-empty after trim. Show inline error on blur if empty. |

#### Description (optional)

| Property | Value |
|----------|-------|
| Component | `<Input>` from shadcn/ui |
| id | `"manual-skill-description"` |
| placeholder | `"Brief description of what this skill covers"` |
| maxLength | `500` |
| Maps to | `experience_description` in the API payload |

This field serves dual purpose: it becomes the `experience_description` stored on the skill, and provides context if the user later wants to regenerate via AI.

#### Skill Content (required)

| Property | Value |
|----------|-------|
| Component | `<SkillEditor>` (existing component) |
| Minimum height | `min-h-[320px]` (up from 300px) |
| maxWords | `2000` |
| Toolbar | Reuse existing `SkillEditor` markdown toolbar (Bold, Italic, H1-H3, List, Code) |
| Validation | Non-empty, word count <= 2000 |

#### Inline Tip

A small hint at the bottom of the form, replacing the removed guide panel:

```tsx
<div className="rounded-md bg-primary/5 border border-primary/10 p-3">
  <p className="text-xs text-muted-foreground leading-relaxed">
    <span className="font-medium text-foreground">Tip:</span> Include your
    role, tech stack, focus areas, and work style for best AI personalization.
  </p>
</div>
```

### Save Behavior

On save, call `useCreateUserSkill` with:

```typescript
{
  skill_name: trimmedName,
  skill_content: editorContent,
  experience_description: description || undefined,
}
```

On success: close modal, toast "Skill created", query cache invalidated automatically by the mutation hook.

---

## 6. Tab 2: AI Generate Mode

This preserves the existing generation flow but with improved layout.

### Step 1: Form (experience input)

The current `FormStep` component, with these modifications:

| Change | Current | New |
|--------|---------|-----|
| Guide panel | 280px right column with tips | Removed; tip inlined below textarea |
| Textarea height | `min-h-[200px]` | `min-h-[260px]` -- more room to describe experience |
| Mode toggle | Inside header next to title | Moved to modal header (shared across tabs) |
| Layout | `grid sm:grid-cols-[1fr_280px]` | Single column, full width |

### Step 2: Generating (loading state)

Unchanged from current implementation. The bouncing dots, progress bar, and status text remain as-is. The wider modal gives this step more visual breathing room naturally.

### Step 3: Preview (review and edit)

Modified from current `PreviewStep`:

| Change | Current | New |
|--------|---------|-----|
| Content textarea | `max-h-[220px]` | `min-h-[280px] max-h-[400px]` -- substantially more reading room |
| Name input | Custom styled `<input>` | shadcn `<Input>` with `<Label>` for consistency |
| Word count | Plain text right-aligned | `<WordCountBar>` component (consistent with SkillEditor) |
| "Back to edit" | Inline text button | `<Button variant="ghost" size="sm">` with ArrowLeft icon |
| Save / Retry buttons | Bottom left, `size="sm"` | Footer area, standard button sizes |

### Preview Layout

```text
+------------------------------------------------------+
| <- Back to description                                |
|                                                       |
|  [Generated by AI badge]                              |
|                                                       |
| Skill Name                                            |
| [_Senior Backend Developer_________ ] [pencil icon]  |
|                                                       |
| Generated Content                                     |
| +--------------------------------------------------+ |
| | # Senior Backend Developer                        | |
| |                                                    | |
| | ## Context                                         | |
| | ...                                                | |
| |                                                    | |
| | ## Expertise                                       | |
| | ...                                                | |
| +--------------------------------------------------+ |
| ================================================ bar  |
| 342 / 2000 words                                      |
+------------------------------------------------------+
| [Retry]                         [Save & Activate]    |
+------------------------------------------------------+
```

---

## 7. Component Structure

### File: `skill-add-modal.tsx` (new file, replaces `skill-generator-modal.tsx`)

```text
SkillAddModal (props: SkillAddModalProps)
  |
  +-- Dialog > DialogContent
  |     |
  |     +-- ModalHeader
  |     |     +-- DialogTitle ("Add Skill")
  |     |     +-- ModeToggle (personal | workspace) -- conditional
  |     |
  |     +-- Tabs (value: "manual" | "ai-generate")
  |     |     |
  |     |     +-- TabsList
  |     |     |     +-- TabsTrigger "Manual"
  |     |     |     +-- TabsTrigger "AI Generate"
  |     |     |
  |     |     +-- TabsContent "manual"
  |     |     |     +-- ManualSkillForm
  |     |     |           +-- Input (name)
  |     |     |           +-- Input (description)
  |     |     |           +-- SkillEditor (content)
  |     |     |           +-- InlineTip
  |     |     |
  |     |     +-- TabsContent "ai-generate"
  |     |           +-- (step === 'form')     --> AIFormStep
  |     |           +-- (step === 'generating') --> GeneratingStep (reuse)
  |     |           +-- (step === 'preview')  --> AIPreviewStep
  |     |
  |     +-- ModalFooter (actions depend on active tab + step)
```

### Props Interface

```typescript
export interface SkillAddModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Initial tab selection: "manual" | "ai-generate" */
  defaultTab?: 'manual' | 'ai-generate';
  /** Initial mode -- user can switch inside the modal. */
  defaultMode?: 'personal' | 'workspace';
  /** Hide mode toggle (e.g. non-admin users can only create personal). */
  showModeToggle?: boolean;
  workspaceId: string;
  workspaceSlug?: string;
  /** Pre-seed from a template -- opens AI Generate tab with description pre-filled. */
  template?: {
    id: string;
    name: string;
    description: string;
    skill_content: string;
  } | null;
}
```

### Key Design Decisions

1. **Tabs over separate modals.** A single modal with two tabs is lower friction than two separate modals. Users can switch modes mid-task without losing context.

2. **Tabs sit inside the modal, below the header.** This follows the pattern established in the `SkillsSettingsPage` itself (which uses Tabs for Skills / Plugins / Action Buttons). Users are already trained on this navigation pattern.

3. **Footer stays outside tab content.** Action buttons (Cancel, Save, Generate) are always at the same vertical position. This prevents layout shift when switching tabs and keeps the primary CTA always visible without scrolling.

4. **Template pre-seed opens AI tab.** When a user clicks "Use This" on a template, the modal opens directly to the AI Generate tab with the template's description pre-filled. The manual tab remains accessible if they change their mind.

5. **`SkillEditor` reuse.** The manual tab reuses the existing `SkillEditor` component (toolbar + textarea + word count). No new editor component needed.

---

## 8. Interaction Patterns

### Tab Switching

- Switching from Manual to AI Generate: manual form state is **preserved** (not reset). User can switch back.
- Switching from AI Generate (preview step) to Manual: AI preview state is **preserved**. User can switch back.
- Switching from AI Generate (generating step): **blocked**. Tab triggers are disabled during generation to prevent state corruption.

### Footer Button Matrix

| Tab | Step | Left Side | Right Side |
|-----|------|-----------|------------|
| Manual | -- | Cancel (outline) | Save Skill (primary, disabled until name + content valid) |
| AI Generate | form | Cancel (outline) | Generate (primary, disabled until description >= 10 chars) |
| AI Generate | generating | -- | -- (no footer, progress indicator is the content) |
| AI Generate | preview | Retry (outline, RefreshCw icon) | Save & Activate (primary) |

### Close Behavior

- Clicking X or overlay: close modal, reset all state after 200ms exit animation.
- If user has unsaved content (manual tab has text, or AI tab is in preview): no confirmation dialog for MVP. Content is ephemeral by design. Future iteration can add "Discard changes?" if user demand warrants it.

### Keyboard Navigation

| Key | Behavior |
|-----|----------|
| Tab | Move focus through fields within active tab |
| Arrow Left/Right | Switch between tab triggers (Radix built-in) |
| Enter | Submit form in AI Generate tab; no-op in Manual tab (textarea needs Enter for newlines) |
| Escape | Close modal |
| Cmd+S | Save skill (both tabs) |

### Error States

| Error | Behavior |
|-------|----------|
| AI generation fails | Show amber alert in AI tab (existing pattern), step reverts to form |
| Network error on save | Toast error via sonner, form stays open |
| Word count exceeded | Save button disabled, `WordCountBar` turns red, aria-live announces |
| Name field empty on blur | Inline error text below input: "Skill name is required" |

---

## 9. Responsive Behavior

### Breakpoints

| Breakpoint | Modal Width | Layout Changes |
|------------|-------------|----------------|
| `< 640px` (mobile) | `max-w-[calc(100%-2rem)]` (default from Dialog) | Single column, stacked. Tab triggers become full-width. Textarea min-height reduced to `min-h-[200px]`. Footer buttons stack vertically. |
| `>= 640px` (sm) | `max-w-4xl` (896px) | Full layout as specified. |
| `>= 1024px` (lg) | `max-w-4xl` (same, centered) | No change; 896px is comfortable at 1024+. |

### Mobile Considerations

- Touch targets: all buttons and tab triggers are >= 44px tall (WCAG).
- Textarea: `resize-none` on mobile to prevent accidental resizing.
- Footer: `position: sticky; bottom: 0` so save button is always reachable.

---

## 10. Accessibility

### ARIA

| Element | ARIA | Notes |
|---------|------|-------|
| Tab list | `role="tablist"` (Radix built-in) | |
| Tab triggers | `role="tab"`, `aria-selected` (Radix built-in) | |
| Tab panels | `role="tabpanel"`, `aria-labelledby` (Radix built-in) | |
| Mode toggle | `role="radiogroup"`, each option `role="radio"` + `aria-checked` | Existing pattern |
| Word count bar | `role="meter"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | Existing pattern |
| Name validation | `aria-invalid="true"` + `aria-describedby` linking to error message | |
| Generation progress | `role="progressbar"` + `aria-live="assertive"` for screen reader | Existing pattern |

### Focus Management

1. On modal open: focus moves to first focusable element in active tab (name input for Manual, description textarea for AI Generate).
2. On tab switch: focus moves to first focusable element in newly activated tab.
3. On AI generation complete (form --> preview): focus moves to skill name input in preview.
4. On save success + modal close: focus returns to the trigger button that opened the modal (Radix built-in).

### Color Contrast

All text/background combinations meet WCAG AA (4.5:1 for normal text, 3:1 for large text):

- Muted foreground text on background: verified per design system notes.
- Primary button text on primary background: verified.
- Error text (destructive): verified.

---

## 11. Implementation Guide

### File Changes

| Action | File | Notes |
|--------|------|-------|
| **Create** | `frontend/src/features/settings/components/skill-add-modal.tsx` | New component |
| **Create** | `frontend/src/features/settings/components/__tests__/skill-add-modal.test.tsx` | Unit tests |
| **Modify** | `frontend/src/features/settings/pages/skills-settings-page.tsx` | Replace `SkillGeneratorModal` import with `SkillAddModal` |
| **Modify** | `frontend/src/features/settings/components/index.ts` | Export new component |
| **Deprecate** | `frontend/src/features/settings/components/skill-generator-modal.tsx` | Keep file until migration verified; add `@deprecated` JSDoc |

### Tailwind Class Cheat Sheet

```tsx
// Modal shell
<DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">

// Header section
<DialogHeader className="px-6 pt-6 pb-4 border-b shrink-0">

// Tab bar
<div className="px-6 border-b shrink-0">
  <TabsList className="w-full justify-start">

// Tab content (scrollable)
<TabsContent className="flex-1 overflow-y-auto px-6 py-5">

// Footer (sticky)
<div className="px-6 py-4 border-t shrink-0 flex items-center justify-between gap-3 bg-background">

// Manual form textarea container
<div className="min-h-[320px]">

// AI generate textarea
<Textarea className="resize-none min-h-[260px]" />

// AI preview content textarea
<Textarea className="min-h-[280px] max-h-[400px] font-mono text-xs leading-relaxed resize-y" />

// Inline tip
<div className="rounded-md bg-primary/5 border border-primary/10 p-3 mt-4">
```

### State Management

The modal manages its own local state (React `useState`). No MobX store needed -- this is a transient creation form.

```typescript
// Top-level state
const [activeTab, setActiveTab] = useState<'manual' | 'ai-generate'>(defaultTab);

// Manual tab state
const [manualName, setManualName] = useState('');
const [manualDescription, setManualDescription] = useState('');
const [manualContent, setManualContent] = useState('');
const [manualNameError, setManualNameError] = useState(false);

// AI Generate tab state (migrated from current SkillGeneratorModal)
const [aiStep, setAiStep] = useState<'form' | 'generating' | 'preview'>('form');
const [aiDescription, setAiDescription] = useState('');
const [aiPreview, setAiPreview] = useState<SkillPreview | null>(null);
const [aiEditableName, setAiEditableName] = useState('');
const [aiEditableContent, setAiEditableContent] = useState('');
const [aiShowError, setAiShowError] = useState(false);

// Shared state
const [mode, setMode] = useState<'personal' | 'workspace'>(defaultMode);
```

### Mutation Hooks (reused)

- `useCreateUserSkill(workspaceSlug)` -- for manual save
- `useGenerateSkill({ workspaceId })` -- for personal AI generation
- `useGenerateWorkspaceSkill({ workspaceId })` -- for workspace AI generation

### Template Pre-seed Logic

When `template` prop is provided:
1. Set `activeTab` to `'ai-generate'`
2. Pre-fill `aiDescription` with `template.description`
3. Show template name badge in AI Generate tab header

### Integration with Settings Page

In `skills-settings-page.tsx`, replace:

```tsx
// Before
<SkillGeneratorModal
  open={generatorOpen}
  onOpenChange={(v) => { ... }}
  defaultMode="personal"
  showModeToggle={isAdmin}
  workspaceId={workspaceId}
  workspaceSlug={workspaceSlug}
  template={selectedTemplate}
/>

// After
<SkillAddModal
  open={generatorOpen}
  onOpenChange={(v) => { ... }}
  defaultTab={selectedTemplate ? 'ai-generate' : 'manual'}
  defaultMode="personal"
  showModeToggle={isAdmin}
  workspaceId={workspaceId}
  workspaceSlug={workspaceSlug}
  template={selectedTemplate}
/>
```

### Testing Requirements

1. **Manual tab renders** -- name input, description input, skill editor, save button visible.
2. **Manual save** -- fills name + content, clicks Save, `createUserSkill.mutateAsync` called with correct payload.
3. **Manual validation** -- Save disabled when name empty or content empty.
4. **AI tab renders** -- description textarea, generate button visible.
5. **Tab switching preserves state** -- type in manual, switch to AI, switch back, manual content preserved.
6. **Template pre-seed** -- when template provided, AI tab is active, description pre-filled.
7. **AI generation flow** -- mock generate mutation, verify form --> generating --> preview transitions.
8. **Tab disabled during generation** -- manual tab trigger disabled when AI step is 'generating'.
9. **Modal close resets state** -- close modal, reopen, all fields empty.
10. **Keyboard** -- Escape closes modal, tab navigation works through fields.

---

## Appendix: Visual Comparison

### Current Modal (768px, two-panel)

```text
+-----------------------------------+----------------+
| Generate Skill            [mode]  | Writing Guide  |
| Describe your expertise...        |                |
|                                   | Role & Senior. |
| [___________________________]     | Tech Stack     |
| [___________________________]     | Focus Areas    |
| [___________________________]     | Work Style     |
| [___________________________]     |                |
| [___________________________]     | Tip: The more  |
|                                   | specific...    |
| 0 words                           |                |
|           [Cancel] [Generate]     |                |
+-----------------------------------+----------------+
```

### New Modal (896px, tabbed, single column)

```text
+------------------------------------------------------+
| Add Skill                                    [mode]  |
+------------------------------------------------------+
| [Manual]  [AI Generate]                               |
+------------------------------------------------------+
|                                                       |
| Skill Name *                                          |
| [Senior Backend Developer___________________________] |
|                                                       |
| Description (optional)                                |
| [Python/FastAPI expert, clean architecture focus_____] |
|                                                       |
| Skill Content *                    [B][I][H1][H2]... |
| +--------------------------------------------------+ |
| | # Senior Backend Developer                        | |
| |                                                    | |
| | ## Expertise                                       | |
| | - Python, FastAPI, PostgreSQL                      | |
| | - Clean architecture, async patterns               | |
| | ...                                                | |
| +--------------------------------------------------+ |
| ============================================== bar    |
| 127 / 2000 words                                      |
|                                                       |
| Tip: Include your role, tech stack, focus areas...    |
+------------------------------------------------------+
| [Cancel]                               [Save Skill]  |
+------------------------------------------------------+
```

The new layout provides approximately **30% more content area** (560px vs 440px effective width) and removes the cognitive overhead of a split-panel layout for what is fundamentally a single-column form.
