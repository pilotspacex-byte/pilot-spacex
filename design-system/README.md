# Pilot Space Design System v2.0

A comprehensive design system for Pilot Space - AI-Augmented SDLC Platform.

**Design Direction**: Warm, Capable, Collaborative

## Visual Identity

- **Font**: Geist (sans) + Geist Mono (code)
- **Icons**: Lucide
- **Primary**: Teal-green (#29A386) - fresh, capable, approachable
- **AI Partner**: Dusty blue (#6B8FAD) - calm, trustworthy collaborator
- **Backgrounds**: Warm off-white (#FDFCFA)
- **Corners**: Apple-style squircles (rounded-xl/2xl)
- **Motion**: Minimal & functional, scale + shadow on hover

## Foundation

- **Framework**: React 18 + TypeScript
- **Styling**: TailwindCSS + shadcn/ui (customized)
- **Primitives**: Radix UI

## Structure

```text
design-system/
├── tokens/           # Design tokens (colors, spacing, typography)
│   ├── design-tokens.ts    # TypeScript design tokens
│   ├── tailwind.config.ts  # Tailwind configuration
│   └── globals.css         # CSS custom properties
├── components/       # Reusable UI components
│   ├── button.tsx          # Button with AI variant
│   ├── input.tsx           # Input with FormField, AI variant
│   ├── card.tsx            # Card with interactive/AI variants
│   ├── badge.tsx           # Badge, AIBadge, AIAttribution, PilotIcon
│   ├── avatar.tsx          # Avatar, UserAvatar, AIAvatar
│   ├── select.tsx          # Select dropdown
│   ├── dialog.tsx          # Modal/Dialog, AIDialog
│   ├── toast.tsx           # Toast with AI variant
│   ├── skeleton.tsx        # Loading skeletons, AILoadingSkeleton
│   └── index.ts            # Component exports
├── layouts/          # Page layouts and shells
│   └── app-shell.tsx       # Main app layout with sidebar
├── views/            # Complete view compositions
│   ├── issue-card.tsx      # Issue card and row
│   ├── issue-create-modal.tsx  # Issue creation with AI
│   ├── board-view.tsx      # Kanban board with drag-drop
│   ├── cycle-board.tsx     # Sprint board with metrics
│   ├── ai-pr-review.tsx    # AI code review display
│   ├── page-editor.tsx     # Documentation editor
│   ├── settings.tsx        # Settings screens
│   └── index.ts            # View exports
├── patterns/         # Interaction patterns and recipes
│   ├── accessibility.md    # A11y patterns and checklist
│   └── ai-ui-patterns.md   # AI collaborative partner guidelines
└── assets/           # Static assets
    └── pilot-icon.svg      # AI partner icon (compass)
```

## Quick Start

```bash
# Initialize with design system preset
pnpm dlx shadcn@latest init

# Add Geist fonts
pnpm add @geist/font

# Add Lucide icons
pnpm add lucide-react
```

## Design Principles

1. **Warm & Approachable** - Soft colors, warm backgrounds, friendly interactions
2. **AI as Collaborative Partner** - "You + AI" attribution, Pilot persona
3. **Apple-Inspired Polish** - Squircle corners, subtle shadows, refined typography
4. **Accessibility First** - WCAG 2.2 AA compliance
5. **Minimal Motion** - Scale + shadow hover, respects reduced-motion
6. **Keyboard Navigation** - Full keyboard support

## Component Overview

### Core Components

| Component | Description |
|-----------|-------------|
| `Button` | Primary action button with variants (default, destructive, outline, ghost, ai, ai-subtle) |
| `Input` | Text input with FormField wrapper, AI variant for suggestions |
| `Card` | Container component with interactive/ai/frosted variants |
| `Badge` | Status and label badges including AI indicators |
| `AIBadge` | AI suggestion/generated badge with confidence |
| `AIAttribution` | "You + AI" collaborative attribution |
| `PilotIcon` | AI partner compass icon |
| `Avatar` | User avatars with warm fallback colors |
| `AIAvatar` | AI partner avatar (compass in dusty blue) |
| `Select` | Dropdown select with keyboard navigation |
| `Dialog` | Modal dialogs with blur backdrop |
| `AIDialog` | AI approval dialog with Pilot styling |
| `Toast` | Notification toasts with AI variant |
| `Skeleton` | Loading placeholders with AI variant |

### Views

| View | Description |
|------|-------------|
| `IssueCard` | Compact issue display with AI indicator |
| `IssueCreateModal` | Issue creation with Pilot suggestions |
| `BoardView` | Kanban board with drag-and-drop |
| `CycleBoard` | Sprint board with metrics/burndown |
| `AIPRReview` | AI code review results display |
| `PageEditor` | Rich text documentation editor |
| `SettingsPage` | Workspace configuration screens |

## Color System

### Base Colors

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `background` | Warm off-white | Soft dark | Main background |
| `foreground` | Warm charcoal | Off-white | Text color |
| `primary` | Teal-green | Teal-green | CTAs, active states |
| `ai` | Dusty blue | Dusty blue | AI collaborative partner |

### Issue States

| State | Color | Usage |
|-------|-------|-------|
| Backlog | Slate | Unstarted issues |
| Todo | Sky blue | Ready to start |
| In Progress | Teal | Actively worked |
| In Review | Purple | Awaiting review |
| Done | Emerald | Completed |
| Cancelled | Rose | Abandoned |

### Priority Levels

| Priority | Color | Usage |
|----------|-------|-------|
| Urgent | Coral red | Critical blockers |
| High | Warm amber | High importance |
| Medium | Soft gold | Normal priority |
| Low | Sky blue | Low importance |
| None | Muted gray | Unprioritized |

### AI Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--ai` | Dusty blue | AI partner primary |
| `--ai-muted` | Light blue | AI backgrounds |
| `--ai-border` | Medium blue | AI container borders |
| `--ai-confidence-high` | Teal | High confidence |
| `--ai-confidence-medium` | Amber | Medium confidence |
| `--ai-confidence-low` | Coral | Low confidence |

## AI Collaborative Partner

The AI is personified as "Pilot" - a collaborative partner that guides and navigates alongside the user.

### Visual Language

- **Icon**: Compass (guidance, navigation)
- **Color**: Dusty blue (calm, trustworthy)
- **Container**: Soft left border + tinted background
- **Attribution**: "You + AI" style

### Components

```tsx
import { AIBadge, AIAttribution, PilotIcon, AIAvatar } from '@/components/badge';
import { AICard, IssueCard } from '@/components/card';
import { AIDialog } from '@/components/dialog';
import { AILoadingSkeleton } from '@/components/skeleton';

// AI suggestion badge
<AIBadge type="suggestion" confidence={85}>Suggested</AIBadge>

// Collaborative attribution
<AIAttribution /> // "You + AI"

// AI avatar
<AIAvatar size="lg" />

// AI content container
<AICard>
  {aiGeneratedContent}
</AICard>

// AI approval dialog
<AIDialog
  title="Review Tasks"
  description="Pilot has generated tasks for you to review"
  onApprove={approve}
  onReject={reject}
>
  {content}
</AIDialog>
```

## Interaction Patterns

### Hover States

Interactive elements use scale + shadow on hover:

```css
.interactive:hover {
  transform: scale(1.02);
  box-shadow: var(--shadow-elevated);
}
```

### Focus States

Visible focus rings using the primary teal color:

```css
:focus-visible {
  outline: none;
  ring: 2px solid hsl(var(--ring));
  ring-offset: 2px;
}
```

### Reduced Motion

All animations respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Web Interface Guidelines Compliance

This design system follows [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines):

- **Accessibility**: Semantic HTML, ARIA labels, keyboard navigation, focus management
- **Forms**: Proper autocomplete, clickable labels, inline errors, never prevent paste
- **Motion**: Respects `prefers-reduced-motion`, only animates transform/opacity
- **Typography**: Tabular numbers for metrics, proper quotation marks, ellipsis
- **Touch**: `touch-action: manipulation`, proper tap targets (44px minimum)
- **Performance**: Explicit image dimensions, virtualized lists, no layout shift

## Specification Alignment

Implements UI requirements from `specs/001-pilot-space-mvp/spec.md`:

- **FR-020**: AI content clearly labeled with visual indicators
- **FR-021**: Human approval required for AI create/modify/delete actions
- **FR-007**: Autosave within 5 seconds for documentation pages
- **User Stories 1-10**: All P1/P2 feature UIs designed

## Migration from v1.0

Key changes from v1.0:

1. **Icons**: Tabler Icons → Lucide
2. **Font**: Inter → Geist
3. **Primary color**: Orange → Teal-green
4. **AI color**: Purple → Dusty blue
5. **Backgrounds**: Pure white → Warm off-white
6. **Corners**: rounded-md → rounded-xl (squircle)
7. **AI persona**: System → Collaborative partner (Pilot)
8. **Attribution**: "AI-generated" → "You + AI"
