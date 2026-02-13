/**
 * Tailwind class strings for the MermaidPreview diagram block.
 *
 * Design system tokens used:
 *   --background (#FDFCFA light / #1A1A1A dark)
 *   --primary (#29A386) for focus rings
 *   --destructive (#D9534F) for error states
 *   --border (#E5E2DD light / #2E2E2E dark)
 *
 * FR-001: Render diagrams as interactive vector graphics.
 * FR-004: Live preview panel alongside source editor.
 * FR-005: Inline error messages (not toasts).
 * FR-006: Preserve last valid render on syntax errors.
 * FR-011: Read-only on mobile with pinch-to-zoom.
 */

/** Tailwind class map consumed by MermaidPreview component. */
export const mermaidPreviewStyles = {
  /** Outer wrapper — provides hover group and focus ring target.
   *  When preceded by .mermaid-unified-block, CSS in globals.css removes top
   *  border-radius and border-top to merge into a single card. */
  wrapper: [
    'group relative my-2 rounded-xl border border-border bg-background',
    'shadow-sm transition-shadow hover:shadow-md',
    'focus-within:ring-2 focus-within:ring-primary/40 focus-within:outline-none',
    'dark:bg-card',
  ].join(' '),

  /** SVG render area — scrollable with constrained height. */
  svg: ['w-full p-4', '[&>svg]:mx-auto [&>svg]:block'].join(' '),

  /** Floating toolbar — visible on hover/focus-within. */
  toolbar: [
    'absolute top-2 right-2 z-10 flex items-center gap-1 rounded-lg',
    'bg-background/80 backdrop-blur-sm border border-border/50 p-0.5',
    'opacity-0 transition-opacity duration-150',
    'group-hover:opacity-100 group-focus-within:opacity-100',
  ].join(' '),

  /** Ghost button used in toolbar (export, fullscreen). */
  toolbarButton: [
    'inline-flex items-center justify-center rounded-md p-1.5',
    'text-muted-foreground hover:text-foreground hover:bg-accent',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
    'transition-colors',
  ].join(' '),

  /** Source/Preview toggle — pill button pair in top-left. */
  toggleGroup: [
    'absolute top-2 left-2 z-10 flex items-center rounded-full',
    'border border-border bg-background/80 backdrop-blur-sm p-0.5',
  ].join(' '),

  /** Individual toggle option — ghost when inactive, filled when active. */
  toggleButton: [
    'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium',
    'text-muted-foreground transition-colors',
    'hover:text-foreground',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
  ].join(' '),

  /** Active state modifier — applied additively on the active toggle. */
  toggleButtonActive: 'bg-secondary text-secondary-foreground',

  /** Error state — replaces or overlays the SVG area on parse failure. */
  error: [
    'mt-0 rounded-b-xl border-t border-destructive/30 bg-destructive/5',
    'px-4 py-3 font-mono text-xs leading-relaxed text-destructive',
    'dark:bg-destructive/10',
  ].join(' '),

  /** Loading skeleton — pulsing placeholder inside the container. */
  loading: ['flex items-center justify-center p-8', 'motion-safe:animate-pulse'].join(' '),

  /** Skeleton bar inside loading state. */
  loadingSkeleton: ['h-48 w-full rounded-lg bg-muted'].join(' '),

  /** Mobile read-only badge — overlays top-right on narrow viewports. */
  mobileReadOnly: [
    'absolute top-2 right-2 z-20 inline-flex items-center gap-1',
    'rounded-full bg-muted px-2.5 py-1 text-[10px] font-medium text-muted-foreground',
    'md:hidden',
  ].join(' '),

  /** Diagram type indicator — subtle label in bottom-left. */
  diagramType: [
    'absolute bottom-2 left-3 text-[10px] font-medium uppercase tracking-wider',
    'text-muted-foreground/60 select-none',
  ].join(' '),
} as const;

export type MermaidPreviewStyleKey = keyof typeof mermaidPreviewStyles;
