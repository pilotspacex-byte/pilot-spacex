# Skills Settings Page -- Component Design Spec

**Feature**: 011-role-based-skills
**Source**: ux-analysis.md v2, Sections 3-4
**Target**: Task #8 (Skills Settings Page implementation)
**Design System**: Pilot Space UI Design Spec v4.0

---

## 1. Skills Settings Page Layout

### 1.1 Page Wireframe

```
+-----------------------------------------------------------------+
|  Settings Layout (existing)                                      |
|  +--------+ +---------------------------------------------------+
|  | Nav    | | max-w-3xl px-8 py-6                               |
|  |        | |                                                    |
|  | ...    | |  AI Skills                        [ + Add Role ]  |
|  | Skills*| |  Configure how the AI assistant    (1 slot left)  |
|  |        | |  adapts to your role.                             |
|  |        | |                                                    |
|  |        | |  +-----------------------------------------------+ |
|  |        | |  | PRIMARY  Developer          [icon] [icon]     | |
|  |        | |  |                                               | |
|  |        | |  | # Developer -- Full-Stack Engineer            | |
|  |        | |  | ## Focus Areas                                | |
|  |        | |  | - Clean architecture...                       | |
|  |        | |  | - TypeScript...               [Show more v]  | |
|  |        | |  |                                  847 words    | |
|  |        | |  |                                               | |
|  |        | |  | [Edit] [Regenerate AI] [Reset] [Remove]       | |
|  |        | |  +-----------------------------------------------+ |
|  |        | |                                                    |
|  |        | |  +-----------------------------------------------+ |
|  |        | |  | Tester                                        | |
|  |        | |  | ...                                           | |
|  |        | |  +-----------------------------------------------+ |
|  |        | |                                                    |
|  +--------+ +---------------------------------------------------+
+-----------------------------------------------------------------+
```

### 1.2 Container Classes

```tsx
// Page container (matches ai-settings-page.tsx pattern)
<div className="max-w-3xl px-8 py-6 md:px-6 sm:px-4">

// Header row
<div className="flex items-center justify-between">
  <div className="space-y-1">
    <h1 className="text-2xl font-semibold tracking-tight">AI Skills</h1>
    <p className="text-sm text-muted-foreground">
      Configure how the AI assistant adapts to your role.
    </p>
  </div>
  {/* Add Role button -- right side */}
</div>

// Cards container
<div className="mt-6 space-y-4">
  {/* RoleSkillCard components */}
</div>
```

**Responsive adjustments** (per ux-analysis Section 8.4):

| Breakpoint | Container | Padding |
|------------|-----------|---------|
| `xl+` | `max-w-3xl` | `px-8 py-6` |
| `lg` | `max-w-3xl` | `px-6 py-6` |
| `md` | `max-w-2xl` | `px-4 py-4` |
| `sm` | full-width | `px-4 py-4` |

### 1.3 "Add Role" Button

```tsx
<div className="flex flex-col items-end gap-1">
  <Button
    variant="outline"
    size="sm"
    disabled={roleCount >= 3}
    aria-disabled={roleCount >= 3}
    aria-describedby={roleCount >= 3 ? "max-roles-hint" : undefined}
    className="gap-1.5"
    onClick={onAddRole}
  >
    <Plus className="h-4 w-4" />
    Add Role
  </Button>
  <span
    id="max-roles-hint"
    className="text-xs text-muted-foreground"
  >
    {3 - roleCount} slot{3 - roleCount !== 1 ? 's' : ''} left
  </span>
</div>
```

### 1.4 Loading Skeleton

```
+-----------------------------------------------------------------+
|  [==========  h-8 w-48  ==========]                             |
|  [====  h-4 w-96  ====]                                         |
|                                                                  |
|  +-----------------------------------------------+              |
|  | [== h-5 w-32 ==]                    [h-5 w-20]|              |
|  |                                                |              |
|  | [=================== h-4 w-full =============] |              |
|  | [=================== h-4 w-full =============] |              |
|  | [============= h-4 w-3/4 ========]             |              |
|  |                                                |              |
|  | [h-8 w-16] [h-8 w-28] [h-8 w-16] [h-8 w-20]  |              |
|  +-----------------------------------------------+              |
|                                                                  |
|  +-----------------------------------------------+              |
|  | [== h-5 w-24 ==]                               |              |
|  | [=================== h-4 w-full =============] |              |
|  | [============= h-4 w-2/3 ======]               |              |
|  +-----------------------------------------------+              |
+-----------------------------------------------------------------+
```

```tsx
function SkillsLoadingSkeleton() {
  return (
    <div className="max-w-3xl px-8 py-6 space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-96" />
      </div>
      {[1, 2].map((i) => (
        <div key={i} className="rounded-lg border border-border p-6 space-y-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-20" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-8 w-28" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-8 w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 1.5 Error State

```tsx
<div className="max-w-3xl px-8 py-6">
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Failed to load skills</AlertTitle>
    <AlertDescription>{error.message}</AlertDescription>
  </Alert>
</div>
```

---

## 2. Role Skill Card (Display Variant)

### 2.1 Component Interface

```tsx
interface RoleSkillCardProps {
  skill: UserRoleSkill;
  isPrimary: boolean;
  isEditing: boolean;
  onEdit: () => void;
  onRegenerate: () => void;
  onReset: () => void;
  onRemove: () => void;
}
```

### 2.2 Card Wireframe -- View Mode

```
Primary Card:
╔═══════════════════════════════════════════════════════════╗
║  [icon]  Developer                          * PRIMARY    ║
║                                                          ║
║  +------------------------------------------------------+║
║  | # Developer -- Full-Stack Engineer                    |║
║  |                                                       |║
║  | ## Focus Areas                                        |║
║  | - Clean architecture (hexagonal, CQRS-lite)           |║
║  | - TypeScript + React + Node.js ecosystem              |║
║  | - PostgreSQL query optimization                       |║
║  |                                        [Show more v]  |║
║  +------------------------------------------------------+║
║                                              847 words   ║
║                                                          ║
║  [Edit]  [Regenerate AI]  [Reset]  [Remove]              ║
╚══════════════════════════════════════════════════════════╝

Secondary Card:
+-----------------------------------------------------------+
|  [icon]  Tester                                            |
|                                                            |
|  +--------------------------------------------------------+|
|  | # Tester -- QA Automation Engineer                      ||
|  | ...                                      [Show more v]  ||
|  +--------------------------------------------------------+|
|                                                623 words   |
|                                                            |
|  [Edit]  [Regenerate AI]  [Reset]  [Remove]                |
+-----------------------------------------------------------+
```

### 2.3 Card Styling -- Tailwind Classes

**Primary card outer container:**
```tsx
<article
  className={cn(
    "rounded-lg p-6 space-y-4 transition-colors duration-200",
    "border-2 border-primary bg-primary/[0.06]",
    "shadow-sm"
  )}
  aria-label={`${skill.roleName} role skill`}
>
```

**Secondary card outer container:**
```tsx
<article
  className={cn(
    "rounded-lg border border-border bg-card p-6 space-y-4",
    "shadow-sm transition-colors duration-200"
  )}
  aria-label={`${skill.roleName} role skill`}
>
```

### 2.4 Card Header Row

```tsx
<div className="flex items-center justify-between">
  <div className="flex items-center gap-3">
    {/* Role icon */}
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
      <RoleIcon className="h-4 w-4 text-muted-foreground" />
    </div>
    {/* Role name */}
    <h3 className="text-lg font-semibold text-foreground">
      {skill.roleName}
    </h3>
  </div>

  {/* PRIMARY badge (conditional) */}
  {isPrimary && (
    <span
      className="rounded-sm bg-primary px-2 py-0.5 text-xs font-semibold uppercase text-primary-foreground"
      aria-label="Primary role"
    >
      Primary
    </span>
  )}
</div>
```

**Spacing**: `gap-3` (12px) between icon and name. Header row uses `justify-between` for badge alignment.

### 2.5 Skill Content Preview (Collapsed/Expanded)

```tsx
<div className="relative">
  <div
    className={cn(
      "rounded-lg border border-border/50 bg-background p-4",
      "overflow-hidden transition-[max-height] duration-300 ease-in-out",
      isExpanded ? "max-h-none" : "max-h-[200px]"
    )}
    aria-label="Skill content preview"
  >
    {/* Rendered markdown */}
    <div className="prose prose-sm max-w-none text-sm text-foreground">
      <MarkdownRenderer content={skill.skillContent} />
    </div>
  </div>

  {/* Gradient fade + toggle (when collapsed) */}
  {!isExpanded && contentOverflows && (
    <div className="absolute inset-x-0 bottom-0 flex justify-center bg-gradient-to-t from-background via-background/80 to-transparent pb-2 pt-8">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded(true)}
        aria-expanded={false}
        aria-controls={`skill-content-${skill.id}`}
        className="text-xs text-muted-foreground hover:text-foreground"
      >
        Show more
        <ChevronDown className="ml-1 h-3 w-3" />
      </Button>
    </div>
  )}

  {/* Collapse toggle (when expanded) */}
  {isExpanded && (
    <div className="mt-2 flex justify-center">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsExpanded(false)}
        aria-expanded={true}
        aria-controls={`skill-content-${skill.id}`}
        className="text-xs text-muted-foreground hover:text-foreground"
      >
        Show less
        <ChevronUp className="ml-1 h-3 w-3" />
      </Button>
    </div>
  )}
</div>
```

**Collapsed state**: `max-h-[200px]` with gradient overlay from `bg-background` to transparent.
**Expanded state**: `max-h-none`, no gradient, "Show less" button below.
**Content area**: `rounded-lg border-border/50 bg-background p-4`. Markdown rendered at `text-sm`.

**Responsive collapsed heights**:
- `xl+`: `max-h-[200px]`
- `md`: `max-h-[150px]`
- `sm`: `max-h-[100px]`

### 2.6 Word Count

```tsx
<div className="text-right">
  <span className="text-xs text-muted-foreground tabular-nums">
    {wordCount} words
  </span>
</div>
```

### 2.7 Action Buttons Row

```tsx
<div className="flex flex-wrap items-center gap-2">
  <Button
    variant="outline"
    size="sm"
    onClick={onEdit}
    className="gap-1.5"
  >
    <Pencil className="h-3.5 w-3.5" />
    Edit
  </Button>

  <Button
    variant="outline"
    size="sm"
    onClick={onRegenerate}
    className="gap-1.5 border-[hsl(var(--ai))] text-[hsl(var(--ai))] hover:bg-[hsl(var(--ai))]/10"
  >
    <Sparkles className="h-3.5 w-3.5" />
    Regenerate AI
  </Button>

  <Button
    variant="ghost"
    size="sm"
    onClick={onReset}
    className="gap-1.5"
  >
    <RotateCcw className="h-3.5 w-3.5" />
    Reset
  </Button>

  <Button
    variant="ghost"
    size="sm"
    onClick={onRemove}
    className="gap-1.5 text-destructive hover:text-destructive hover:bg-destructive/10"
  >
    <Trash2 className="h-3.5 w-3.5" />
    Remove
  </Button>
</div>
```

**Button interaction states** (per UI spec Section 5):
- Hover: `scale-[1.02]` + elevated shadow (via `motion-safe:hover:scale-[1.02]`)
- Active: scale back to `scale-[0.98]`
- Focus: `focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none`

**Responsive**: On `sm`, buttons wrap to 2 per row via `flex-wrap`. Min touch target 44px maintained by `size="sm"` (32px height) + padding.

### 2.8 Dark Mode

All colors use CSS custom properties and auto-adapt:
- Primary card: `border-primary` brightens to `#34B896` in dark
- `bg-primary/[0.06]` adjusts automatically
- `bg-card` maps to `#222222` in dark
- `bg-background` for content area maps to `#1A1A1A`
- Shadows: reduced opacity in dark, no warm tint

---

## 3. Inline Skill Editor

### 3.1 Wireframe -- Edit Mode

```
╔═══════════════════════════════════════════════════════════╗
║  [icon]  Developer                * PRIMARY    [Cancel]  ║
║                                                          ║
║  +------------------------------------------------------+║
║  | [B] [I] [H1] [H2] [H3] [*] [<>]                     |║
║  |------------------------------------------------------|║
║  | # Developer -- Full-Stack Engineer                    |║
║  |                                                       |║
║  | ## Focus Areas                                        |║
║  | - Clean architecture (hexagonal, CQRS-lite)           |║
║  | - TypeScript + React + Node.js ecosystem              |║
║  | - PostgreSQL query optimization                       |║
║  | - Security-first PR reviews                           |║
║  | - **GraphQL API design**                              |║
║  |                                                       |║
║  | ## Workflow Preferences                               |║
║  | - Review PRs: security -> performance -> style        |║
║  | ...                                                   |║
║  +------------------------------------------------------+║
║                                                          ║
║  [========================================----]  862 / 2000 ║
║                                                          ║
║  [ Save ]  [ Cancel ]                                    ║
╚══════════════════════════════════════════════════════════╝
```

### 3.2 Edit Mode Transition

When "Edit" is clicked:
1. Card outer container gains: `ring-2 ring-primary ring-offset-2`
2. Skill preview area is replaced by the editor
3. Action buttons row is replaced by Save/Cancel
4. Focus moves to the textarea
5. Cancel button also appears in the header row (for quick access)

```tsx
// Card in edit mode -- outer container
<article
  className={cn(
    "rounded-lg p-6 space-y-4 transition-all duration-200",
    isPrimary
      ? "border-2 border-primary bg-primary/[0.06]"
      : "border border-border bg-card",
    "ring-2 ring-primary ring-offset-2"
  )}
>
```

### 3.3 Markdown Toolbar

```tsx
<div className="flex items-center gap-1 rounded-t-lg border border-b-0 border-border bg-muted/50 p-1">
  {[
    { icon: Bold, label: "Bold", action: "bold" },
    { icon: Italic, label: "Italic", action: "italic" },
    { icon: Heading1, label: "Heading 1", action: "h1" },
    { icon: Heading2, label: "Heading 2", action: "h2" },
    { icon: Heading3, label: "Heading 3", action: "h3" },
    { icon: List, label: "Bullet list", action: "list" },
    { icon: Code, label: "Code block", action: "code" },
  ].map((item) => (
    <Button
      key={item.action}
      variant="ghost"
      size="icon-sm"
      onClick={() => applyFormat(item.action)}
      aria-label={item.label}
      className={cn(
        "h-8 w-8 rounded border border-transparent",
        "hover:border-border hover:bg-background",
        "focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:outline-none"
      )}
    >
      <item.icon className="h-4 w-4" />
    </Button>
  ))}
</div>
```

**Toolbar styling**:
- Container: `bg-muted/50`, `border border-b-0 border-border`, `rounded-t-lg`, `p-1`
- Buttons: `h-8 w-8` (icon-sm), `rounded` (10px), ghost variant with hover border
- Dark mode: `bg-muted/50` auto-maps. Toolbar on `--card` bg.

### 3.4 Textarea / Editor Area

```tsx
<textarea
  ref={editorRef}
  value={editContent}
  onChange={handleChange}
  className={cn(
    "w-full resize-none rounded-b-lg border border-t-0 border-border",
    "bg-background p-4 font-mono text-sm text-foreground",
    "min-h-[300px]",
    "placeholder:text-muted-foreground",
    "focus:outline-none",
    "dark:bg-input"
  )}
  aria-label="Edit skill content"
  aria-describedby="word-count-status"
  style={{ height: autoHeight }}
/>
```

**Editor area styling**:
- Font: `font-mono` (Geist Mono)
- Background: `bg-background` (light), `dark:bg-input` (#1E1E1E dark)
- Border: `border border-t-0 border-border` (continues from toolbar)
- Corners: `rounded-b-lg` (bottom only, toolbar has top)
- Min height: `min-h-[300px]`
- Auto-resize: Calculate height from `scrollHeight`, set via inline style

### 3.5 WordCountBar Component

```tsx
interface WordCountBarProps {
  current: number;
  max: number;
  warnAt?: number; // default 1800
}

function WordCountBar({ current, max = 2000, warnAt = 1800 }: WordCountBarProps) {
  const percentage = Math.min((current / max) * 100, 100);
  const state: 'ok' | 'warning' | 'error' =
    current >= max ? 'error' : current >= warnAt ? 'warning' : 'ok';

  return (
    <div className="space-y-1.5">
      {/* Progress bar */}
      <div
        className="h-1 w-full overflow-hidden rounded-full bg-border"
        role="meter"
        aria-valuenow={current}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label="Word count"
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            state === 'ok' && "bg-primary",
            state === 'warning' && "bg-[#D9853F]",
            state === 'error' && "bg-destructive"
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Label */}
      <div className="flex justify-end">
        <span
          id="word-count-status"
          role="status"
          className={cn(
            "text-xs tabular-nums",
            state === 'ok' && "text-muted-foreground",
            state === 'warning' && "text-[#D9853F]",
            state === 'error' && "text-destructive font-medium"
          )}
        >
          {current} / {max} words
          {state === 'error' && " — limit reached"}
        </span>
      </div>
    </div>
  );
}
```

**WordCountBar specs**:
- Track: `h-1 rounded-full bg-border` (auto dark mode via CSS var)
- Fill: `rounded-full`, transition `duration-300`
- Green: `bg-primary` (0-1799)
- Orange: `bg-[#D9853F]` (1800-1999) -- amber is same in both themes
- Red: `bg-destructive` (2000+)
- Label: `text-xs tabular-nums`, right-aligned

### 3.6 Save/Cancel Buttons

```tsx
<div className="flex items-center gap-2">
  <Button
    variant="default"
    size="sm"
    onClick={onSave}
    disabled={wordCount > 2000 || isSaving}
    aria-busy={isSaving}
    className="gap-1.5"
  >
    {isSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
    Save
  </Button>
  <Button
    variant="ghost"
    size="sm"
    onClick={onCancel}
    disabled={isSaving}
  >
    Cancel
  </Button>
</div>
```

### 3.7 Focus Trap Behavior

1. When entering edit mode, focus moves to the textarea
2. Tab cycles through: toolbar buttons -> textarea -> word count (read-only) -> Save -> Cancel -> (loop)
3. Escape calls `onCancel`, returns focus to the "Edit" button
4. Implemented via `useFocusTrap` or radix `FocusScope`

**Keyboard shortcuts in editor**:
- `Cmd+B` / `Ctrl+B`: Bold
- `Cmd+I` / `Ctrl+I`: Italic
- `Cmd+S` / `Ctrl+S`: Save (prevent default)
- `Escape`: Cancel editing

---

## 4. Regeneration Dialog

### 4.1 Modal Wireframe

```
+---------------------------------------------------------------+
|                                                                |
|  Regenerate Developer Skill                           [ x ]   |
|                                                                |
|  Update your experience description:                           |
|  +-----------------------------------------------------------+|
|  | Full-stack engineer with 5 years experience.               ||
|  | TypeScript, React, Node.js, PostgreSQL, GraphQL.           ||
|  | Now also doing infrastructure and Terraform.               ||
|  +-----------------------------------------------------------+|
|                                                                |
|                      [ Generate New Skill ]                    |
|                                                                |
|  - - - - - - - - - - - - - - - - - - - - - - - - - - - - -   |
|                                                                |
|  +--- Current -----------+ +--- New (AI Generated) ----------+|
|  |                        | |                                 ||
|  | ## Focus Areas         | | ## Focus Areas                  ||
|  | - Clean arch...        | | - Clean arch...                 ||
|  | - TypeScript...        | | - TypeScript...                 ||
|  | - PostgreSQL...        | | - PostgreSQL...                 ||
|  |                        | | + **GraphQL API design**     +  ||
|  |                        | | + **Terraform & IaC**        +  ||
|  |                        | |                                 ||
|  +------------------------+ +---------------------------------+|
|                                                                |
|  [ Accept New Skill ]  [ Keep Current ]                        |
|                                                                |
+---------------------------------------------------------------+
```

### 4.2 Modal Container

```tsx
<Dialog open={isOpen} onOpenChange={onClose}>
  <DialogContent
    className="sm:max-w-2xl lg:max-w-3xl"
    aria-label={`Regenerate ${roleName} skill`}
  >
    <DialogHeader>
      <DialogTitle className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[hsl(var(--ai))]" />
        Regenerate {roleName} Skill
      </DialogTitle>
    </DialogHeader>

    {/* Content sections */}

  </DialogContent>
</Dialog>
```

### 4.3 Experience Textarea

```tsx
<div className="space-y-2">
  <Label htmlFor="regen-experience" className="text-sm font-medium">
    Update your experience description:
  </Label>
  <textarea
    id="regen-experience"
    value={experience}
    onChange={(e) => setExperience(e.target.value)}
    className={cn(
      "w-full rounded-lg border border-border bg-background p-3",
      "text-sm text-foreground placeholder:text-muted-foreground",
      "min-h-[100px] resize-none",
      "focus:border-primary focus:ring-[3px] focus:ring-primary/30 focus:outline-none",
      "dark:bg-input"
    )}
    placeholder="Describe your experience, specializations, and preferences..."
    disabled={isGenerating}
  />
</div>
```

### 4.4 Generate Button

```tsx
<div className="flex justify-center">
  <Button
    onClick={onGenerate}
    disabled={isGenerating || !experience.trim()}
    aria-busy={isGenerating}
    className="gap-1.5 bg-[hsl(var(--ai))]/10 text-[hsl(var(--ai))] border border-[hsl(var(--ai))]/20 hover:bg-[hsl(var(--ai))]/20"
  >
    {isGenerating ? (
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
    ) : (
      <Sparkles className="h-4 w-4" />
    )}
    {isGenerating ? "Generating..." : "Generate New Skill"}
  </Button>
</div>
```

### 4.5 Diff Preview

**Desktop (lg+): Side-by-side**

```tsx
<div className="hidden lg:grid lg:grid-cols-2 lg:gap-4">
  {/* Current panel */}
  <div className="space-y-2">
    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      Current
    </h4>
    <div
      className="max-h-[400px] overflow-y-auto rounded-lg border border-border bg-muted/30 p-4"
      aria-label="Current skill version"
    >
      <DiffContent lines={currentLines} side="current" />
    </div>
  </div>

  {/* New panel */}
  <div className="space-y-2">
    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      New (AI Generated)
    </h4>
    <div
      className="max-h-[400px] overflow-y-auto rounded-lg border border-border bg-muted/30 p-4"
      aria-label="New skill version"
    >
      <DiffContent lines={newLines} side="new" />
    </div>
  </div>
</div>
```

**Mobile (<lg): Tabbed**

```tsx
<div className="lg:hidden">
  <Tabs defaultValue="current">
    <TabsList className="w-full">
      <TabsTrigger value="current" className="flex-1">Current</TabsTrigger>
      <TabsTrigger value="new" className="flex-1">New (AI Generated)</TabsTrigger>
    </TabsList>
    <TabsContent value="current">
      <div className="max-h-[300px] overflow-y-auto rounded-lg border border-border bg-muted/30 p-4">
        <DiffContent lines={currentLines} side="current" />
      </div>
    </TabsContent>
    <TabsContent value="new">
      <div className="max-h-[300px] overflow-y-auto rounded-lg border border-border bg-muted/30 p-4">
        <DiffContent lines={newLines} side="new" />
      </div>
    </TabsContent>
  </Tabs>
</div>
```

### 4.6 Diff Line Styling

```tsx
function DiffLine({ line, type }: { line: string; type: 'added' | 'removed' | 'unchanged' }) {
  return (
    <div
      className={cn(
        "px-2 py-0.5 font-mono text-xs leading-relaxed",
        type === 'added' && "bg-primary/[0.08] text-foreground",
        type === 'removed' && "bg-destructive/[0.08] text-foreground line-through opacity-70"
      )}
    >
      {type === 'added' && <span className="mr-2 text-primary font-medium">+</span>}
      {type === 'removed' && <span className="mr-2 text-destructive font-medium">-</span>}
      {type === 'unchanged' && <span className="mr-2 text-muted-foreground">&nbsp;</span>}
      {line}
    </div>
  );
}
```

**Dark mode**: `bg-primary/[0.08]` and `bg-destructive/[0.08]` auto-adjust as `--primary` and `--destructive` change in dark mode. Opacity increases slightly for visibility on dark surfaces -- use `dark:bg-primary/[0.12]` and `dark:bg-destructive/[0.12]`.

### 4.7 Accept/Keep Buttons

```tsx
<DialogFooter className="flex-row gap-2 sm:justify-start">
  <Button
    variant="default"
    onClick={onAcceptNew}
  >
    Accept New Skill
  </Button>
  <Button
    variant="outline"
    onClick={onKeepCurrent}
  >
    Keep Current
  </Button>
</DialogFooter>
```

---

## 5. Confirmation Dialogs

### 5.1 Remove Role Dialog

```tsx
<AlertDialog open={isOpen} onOpenChange={onClose}>
  <AlertDialogContent role="alertdialog" aria-describedby="remove-role-desc">
    <AlertDialogHeader>
      <AlertDialogTitle>
        Remove {roleName} Role?
      </AlertDialogTitle>
      <AlertDialogDescription id="remove-role-desc">
        This will deactivate the {roleName} skill for this workspace.
        The AI assistant will no longer use {roleName}-specific behavior
        in your conversations. Your skill content will be permanently deleted.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction
        onClick={onConfirmRemove}
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
      >
        Remove Role
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**Focus behavior**: When dialog opens, focus moves to "Cancel" button (safer default). Tab cycles between Cancel and Remove Role. Escape closes.

### 5.2 Reset to Default Dialog

```tsx
<AlertDialog open={isOpen} onOpenChange={onClose}>
  <AlertDialogContent role="alertdialog" aria-describedby="reset-skill-desc">
    <AlertDialogHeader>
      <AlertDialogTitle>
        Reset to Default Template?
      </AlertDialogTitle>
      <AlertDialogDescription id="reset-skill-desc">
        This will replace your custom {roleName} skill with the default
        {roleName} template. All customizations will be lost.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction
        onClick={onConfirmReset}
        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
      >
        Reset Skill
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### 5.3 Dialog Styling Notes

Both dialogs use shadcn/ui `AlertDialog` which provides:
- `role="alertdialog"` on content
- Focus trap (built-in)
- Escape to close
- Overlay: 40% black, 8px blur
- Content: `rounded-xl` (18px), Shadow LG
- Dark mode: `--popover` (#252525) bg, frosted glass with higher blur

---

## 6. Edge States

### 6.1 Empty State (No Roles)

```
+-----------------------------------------------------------+
|                                                            |
|                                                            |
|                        [Wand2 icon]                        |
|                         (80px, 40%)                        |
|                                                            |
|                  No roles configured                       |
|                                                            |
|          Set up your SDLC role to personalize              |
|          how the AI assistant helps you in                 |
|          this workspace.                                   |
|                                                            |
|               [ + Set Up Your Role ]                       |
|                                                            |
|                                                            |
+-----------------------------------------------------------+
```

```tsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <Wand2
    className="h-20 w-20 text-muted-foreground/40"
    aria-hidden="true"
  />
  <h2 className="mt-4 text-lg font-medium text-foreground">
    No roles configured
  </h2>
  <p className="mt-2 max-w-[280px] text-sm text-muted-foreground">
    Set up your SDLC role to personalize how the AI assistant helps you
    in this workspace.
  </p>
  <Button
    variant="default"
    className="mt-6"
    onClick={onSetUpRole}
  >
    <Plus className="mr-1.5 h-4 w-4" />
    Set Up Your Role
  </Button>
</div>
```

**Per Section 17 of UI Design Spec**:
- Icon: 80px (`h-20 w-20`), `text-muted-foreground/40`
- Heading: `text-lg font-medium` (17px, weight 500)
- Description: `text-sm text-muted-foreground`, `max-w-[280px]`
- Spacing: `mt-4` (heading), `mt-2` (description), `mt-6` (CTA)
- Container: `py-12` (48px vertical)
- Dark mode: no noise texture, icon stays at 40% opacity

### 6.2 Max Roles State (3 Configured)

```tsx
{roleCount >= 3 && (
  <div
    className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4"
    role="status"
  >
    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
    <p className="text-sm text-muted-foreground">
      Maximum 3 roles per workspace reached. Remove an existing role to add a new one.
    </p>
  </div>
)}
```

The "Add Role" button uses `disabled` and `aria-disabled="true"` per Section 2 above.

### 6.3 Guest View (Read-Only)

```tsx
<div className="max-w-3xl px-8 py-6">
  <div className="space-y-1">
    <h1 className="text-2xl font-semibold tracking-tight">AI Skills</h1>
  </div>

  <div
    className="mt-6 flex items-start gap-3 rounded-lg border border-border bg-muted/50 p-4"
    role="alert"
  >
    <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
    <div>
      <p className="text-sm font-medium text-foreground">
        Role skill configuration requires Member or higher access.
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Contact a workspace admin for permission.
      </p>
    </div>
  </div>
</div>
```

No "Add Role" button rendered. No action buttons on cards. Page header still visible for context.

---

## 7. Component File Map

| File | Component | Props |
|------|-----------|-------|
| `pages/skills-settings-page.tsx` | `SkillsSettingsPage` | -- (route page, uses hooks) |
| `components/role-skill-card.tsx` | `RoleSkillCard` | skill, isPrimary, onEdit, onRegenerate, onReset, onRemove |
| `components/skill-editor.tsx` | `SkillEditor` | content, onChange, onSave, onCancel, wordCount |
| `components/word-count-bar.tsx` | `WordCountBar` | current, max, warnAt |
| `components/regeneration-dialog.tsx` | `RegenerationDialog` | isOpen, skill, onAccept, onKeepCurrent, onClose |
| `components/diff-preview.tsx` | `DiffPreview` | currentContent, newContent |
| `components/skills-empty-state.tsx` | `SkillsEmptyState` | onSetUpRole |

---

## 8. ARIA Attribute Summary

| Component | Attribute | Value |
|-----------|-----------|-------|
| Card | `role` | implicit (`<article>`) |
| Card | `aria-label` | `"{roleName} role skill"` |
| Show more/less | `aria-expanded` | `true` / `false` |
| Show more/less | `aria-controls` | `"skill-content-{id}"` |
| WordCountBar | `role` | `"meter"` |
| WordCountBar | `aria-valuenow` | `{current}` |
| WordCountBar | `aria-valuemax` | `{max}` |
| WordCountBar label | `role` | `"status"` |
| Editor textarea | `aria-label` | `"Edit skill content"` |
| Editor textarea | `aria-describedby` | `"word-count-status"` |
| Diff current panel | `aria-label` | `"Current skill version"` |
| Diff new panel | `aria-label` | `"New skill version"` |
| Confirmation dialogs | `role` | `"alertdialog"` |
| Confirmation dialogs | `aria-describedby` | links to description |
| Disabled Add Role | `aria-disabled` | `"true"` |
| Disabled Add Role | `aria-describedby` | `"max-roles-hint"` |
| Guest alert | `role` | `"alert"` |
| Max roles banner | `role` | `"status"` |

---

## 9. Keyboard Interaction Summary

| Context | Key | Action |
|---------|-----|--------|
| Skill card | Tab | Focus moves through action buttons |
| Show more/less | Enter/Space | Toggle expanded state |
| Edit button | Enter | Enter edit mode, focus moves to textarea |
| Editor | Cmd+B / Ctrl+B | Toggle bold |
| Editor | Cmd+I / Ctrl+I | Toggle italic |
| Editor | Cmd+S / Ctrl+S | Save (prevent browser default) |
| Editor | Escape | Cancel editing, focus returns to Edit button |
| Editor | Tab | Cycle through toolbar -> textarea -> Save -> Cancel |
| Regeneration dialog | Tab | Cycle through textarea -> Generate -> diff panels -> Accept -> Keep |
| Regeneration dialog | Escape | Close dialog |
| Confirmation dialog | Tab | Cycle between Cancel and action button |
| Confirmation dialog | Escape | Close (same as Cancel) |
| Add Role button | Enter/Space | Open role selection flow |
