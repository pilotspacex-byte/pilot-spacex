/**
 * Shared Tailwind class strings for PM block renderers.
 *
 * Covers: general container, Smart Checklist (FR-013..FR-019),
 *         Decision Record (FR-020..FR-024), Form Block (FR-027..FR-029),
 *         RACI Matrix (FR-030..FR-031), Risk Register (FR-032..FR-033),
 *         Visualization (FR-036..FR-037), Timeline (FR-039..FR-040),
 *         KPI Dashboard (FR-041).
 *
 * Uses project CSS tokens:
 *   --primary (#29A386), --destructive (#D9534F),
 *   --priority-{urgent,high,medium,low,none} (globals.css)
 */

/* ------------------------------------------------------------------ */
/*  Shared PM block container                                         */
/* ------------------------------------------------------------------ */

const shared = {
  /** Outer block wrapper — matches mermaid-preview-styles pattern. */
  wrapper: [
    'group relative my-2 rounded-xl border border-border bg-background',
    'ring-1 ring-inset ring-black/[0.02]',
    'shadow-sm transition-shadow hover:shadow-md motion-reduce:transition-none',
    'focus-within:ring-2 focus-within:ring-primary/40 focus-within:outline-none',
    'dark:bg-card',
  ].join(' '),

  /** Block type label — top-left uppercase badge. */
  typeLabel: [
    'absolute -top-2.5 left-3 z-10 inline-flex items-center gap-1',
    'rounded-full bg-background px-2 py-0.5 text-[10px] font-semibold',
    'uppercase tracking-wider text-primary/70 border border-primary/20 dark:border-primary/15',
    'dark:bg-card',
  ].join(' '),

  /** Mobile read-only badge — hidden on md+. */
  mobileReadOnly: [
    'absolute top-2 right-2 z-20 inline-flex items-center gap-1',
    'rounded-full bg-muted px-2.5 py-1 text-[10px] font-medium text-muted-foreground',
    'md:hidden',
  ].join(' '),

  /** Inner content area with padding. */
  content: 'px-4 pb-4 pt-5',

  /** Container for renderer-level layout (used by Timeline, Dashboard). */
  container: 'flex flex-col gap-3',

  /** Header row with title. */
  header: 'flex items-center justify-between',

  /** Read-only title heading. */
  title: 'text-sm font-semibold text-foreground',

  /** Editable title input. */
  titleInput: [
    'text-sm font-semibold text-foreground bg-transparent border-none outline-none',
    'w-full placeholder:text-muted-foreground',
    'focus:ring-0',
  ].join(' '),

  /** Add item button — subtle text button. */
  addButton: [
    'mt-2 text-xs font-medium text-muted-foreground',
    'hover:text-foreground transition-colors motion-reduce:transition-none',
  ].join(' '),
} as const;

/** Shared focus-visible ring for interactive elements inside blocks. */
const focusRing =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1';

/** Shared inline input style for transparent editable fields. */
const inlineInput = [
  'bg-transparent border-none outline-none w-full',
  'focus-visible:ring-1 focus-visible:ring-primary/40 rounded',
].join(' ');

/* ------------------------------------------------------------------ */
/*  Smart Checklist (US-002)                                          */
/* ------------------------------------------------------------------ */

const checklist = {
  /** Progress bar track — thin rounded bar above items. */
  progressTrack: 'h-1 w-full overflow-hidden rounded-full bg-primary/20 mb-3',

  /** Progress bar fill — teal-green, animated width. */
  progressFill:
    'h-full rounded-full bg-primary transition-all duration-300 ease-out motion-reduce:transition-none',

  /** Scrollable item list container. */
  itemList: 'flex flex-col gap-1',

  /** Single checklist item row. */
  item: [
    'group/item flex items-start gap-2 rounded-lg px-2 py-1.5',
    'transition-colors hover:bg-accent/50 motion-reduce:transition-none',
  ].join(' '),

  /** Optional item modifier — dashed left border, reduced opacity. */
  itemOptional: 'border-l-2 border-dashed border-muted-foreground/30 opacity-70',

  /** Conditional grey-out — parent unchecked disables child. */
  itemDisabled: 'opacity-40 pointer-events-none select-none',

  /** Checkbox wrapper — aligns with first line of text. */
  checkbox: 'mt-0.5 shrink-0',

  /** Item text area — grows to fill row. */
  itemText: 'min-w-0 flex-1 text-sm leading-relaxed',

  /** Checked item text — strikethrough + muted. */
  itemTextChecked: 'line-through text-muted-foreground',

  /** Inline metadata badges row — right side of item. */
  metadata: 'flex shrink-0 items-center gap-1',

  /** Priority pill badge — base styles, color applied per priority. */
  priorityBadge: [
    'inline-flex items-center rounded-full px-1.5 py-0.5',
    'text-[10px] font-medium leading-none',
  ].join(' '),
} as const;

/** Priority badge color map — uses project CSS custom properties. */
const priorityColors = {
  urgent: 'bg-priority-urgent/15 text-priority-urgent',
  high: 'bg-priority-high/15 text-priority-high',
  medium: 'bg-priority-medium/15 text-priority-medium',
  low: 'bg-priority-low/15 text-priority-low',
  none: 'bg-priority-none/15 text-priority-none',
} as const;

/* ------------------------------------------------------------------ */
/*  Decision Record (US-003)                                          */
/* ------------------------------------------------------------------ */

const decision = {
  /** Status banner — full-width top bar inside wrapper. */
  statusBanner: [
    'flex items-center gap-2 rounded-t-xl px-4 py-2',
    'text-xs font-semibold uppercase tracking-wide',
  ].join(' '),

  /** Status color variants. */
  statusOpen: 'bg-[#5B8FC9]/10 text-[#5B8FC9] dark:text-[#7DA4C4]',
  statusDecided: 'bg-primary/10 text-primary',
  statusSuperseded: 'bg-[var(--warning)]/10 text-[var(--warning)]',

  /** Option cards grid — 1 column mobile, 2 columns desktop. */
  optionGrid: 'grid gap-3 sm:grid-cols-2',

  /** Single option card. */
  optionCard: [
    'rounded-lg border border-border bg-background p-3 transition-all',
    'hover:shadow-sm dark:bg-card motion-reduce:transition-none',
  ].join(' '),

  /** Selected option card — teal border + check icon. */
  optionCardSelected: ['ring-2 ring-primary border-primary'].join(' '),

  /** Option title row. */
  optionTitle: 'text-sm font-medium leading-snug',

  /** Option description. */
  optionDescription: 'mt-1 text-xs text-muted-foreground leading-relaxed',

  /** Pros list — green bullet prefix. */
  prosItem: 'flex items-start gap-1.5 text-xs text-primary dark:text-primary',

  /** Cons list — red bullet prefix. */
  consItem: 'flex items-start gap-1.5 text-xs text-destructive',

  /** Effort/risk inline badges on option cards. */
  optionBadge: [
    'inline-flex items-center rounded-full border px-1.5 py-0.5',
    'text-[10px] font-medium text-muted-foreground',
  ].join(' '),

  /** Rationale section — quote-style box. */
  rationale: [
    'mt-3 rounded-lg border-l-4 border-primary/40 bg-muted/50 px-4 py-3',
    'text-sm italic text-muted-foreground leading-relaxed',
  ].join(' '),

  /** Decision date + metadata row. */
  decisionMeta: 'mt-2 flex items-center gap-2 text-xs text-muted-foreground',

  /** "Create Issue" button wrapper — bottom right. */
  createIssueButton: 'mt-3 flex justify-end',
} as const;

/* ------------------------------------------------------------------ */
/*  Form Block (US-004)                                               */
/* ------------------------------------------------------------------ */

const form = {
  /** Vertical stack of form fields. */
  fieldGroup: 'space-y-4',

  /** Field label — matches shadcn/ui label with peer-disabled support. */
  fieldLabel: [
    'text-sm font-medium leading-none',
    'peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
  ].join(' '),

  /** Required field indicator (red asterisk). */
  fieldRequired: 'text-destructive ml-0.5',

  /** Standard input — matches shadcn/ui input appearance. */
  fieldInput: [
    'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1',
    'text-sm shadow-sm transition-colors placeholder:text-muted-foreground',
    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
  ].join(' '),

  /** Validation error text below a field. */
  fieldError: 'text-xs text-destructive mt-1',

  /** Rating stars row. */
  ratingStars: 'flex gap-1 items-center',

  /** Filled star — gold fill + stroke. */
  ratingStarFilled: 'text-amber-400 fill-amber-400',

  /** Empty star — muted outline. */
  ratingStarEmpty: 'text-muted-foreground/30',

  /** Bottom section — response count / submit info. */
  submitSection: 'flex items-center justify-between pt-4 border-t',
} as const;

/* ------------------------------------------------------------------ */
/*  RACI Matrix (US-005)                                              */
/* ------------------------------------------------------------------ */

const raci = {
  /** Scrollable grid wrapper — horizontal scroll on overflow. */
  grid: 'w-full overflow-auto',

  /** Header cell — muted bg, bold, centered, uppercase. */
  headerCell: 'bg-muted/50 font-medium text-center p-2 text-xs uppercase tracking-wider',

  /** First column (deliverable name) — bold, left-aligned, border-right. */
  deliverableCell: 'font-medium text-left p-2 text-sm border-r bg-muted/20',

  /** Standard RACI cell — clickable, centered. */
  cell: 'text-center p-2 cursor-pointer hover:bg-accent/50 transition-colors motion-reduce:transition-none',

  /** RACI role color variants. */
  cellR: 'bg-[#5B8FC9]/10 text-[#5B8FC9] dark:text-[#7DA4C4] font-semibold',
  cellA: 'bg-primary/10 text-primary font-bold',
  cellC: 'bg-[var(--warning)]/10 text-[var(--warning)]',
  cellI: 'bg-muted/30 text-muted-foreground',

  /** Row with missing exactly-one-A constraint. */
  validationError: 'ring-2 ring-destructive/50',

  /** Warning text below matrix. */
  validationWarning: 'text-xs text-amber-600 dark:text-amber-400 mt-1',
} as const;

/* ------------------------------------------------------------------ */
/*  Risk Register (US-006)                                            */
/* ------------------------------------------------------------------ */

const risk = {
  /** Full-width table with alternating row shading. */
  table: 'w-full text-sm [&_tr:nth-child(even)]:bg-muted/30',

  /** Header row — muted background, uppercase. */
  headerRow: 'bg-muted/50 text-xs uppercase tracking-wider',

  /** Score cell — bold, centered. */
  scoreCell: 'font-bold text-center',

  /** Score severity colors (probability x impact). */
  scoreGreen: 'bg-primary/15 text-primary dark:text-primary',
  scoreYellow: 'bg-[var(--warning)]/15 text-[var(--warning)]',
  scoreRed: 'bg-destructive/15 text-destructive dark:text-destructive',

  /** Mitigation strategy pill badge. */
  strategyBadge: 'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-muted',
} as const;

/* ------------------------------------------------------------------ */
/*  Visualization / ECharts Sandbox (US-007)                           */
/* ------------------------------------------------------------------ */

const visualization = {
  /** Iframe wrapper — isolated sandbox with loading state support. */
  sandboxContainer: [
    'relative w-full overflow-hidden rounded-lg border border-border',
    'bg-background dark:bg-card',
  ].join(' '),

  /** Sandboxed iframe — fills container, transparent background. */
  sandboxIframe: 'w-full border-0 bg-transparent',

  /** Timeout overlay — shown when 5s execution limit is exceeded (FR-037). */
  timeoutOverlay: [
    'absolute inset-0 z-10 flex flex-col items-center justify-center gap-2',
    'bg-background/80 backdrop-blur-sm',
    'text-sm font-medium text-destructive',
  ].join(' '),

  /** Chart type label — bottom-left, matches mermaid diagramType pattern. */
  chartTypeLabel: [
    'absolute bottom-2 left-3 text-[10px] font-medium uppercase tracking-wider',
    'text-muted-foreground/60 select-none',
  ].join(' '),
} as const;

/* ------------------------------------------------------------------ */
/*  Timeline / Milestone (US-008)                                      */
/* ------------------------------------------------------------------ */

const timeline = {
  /** Horizontal scrollable SVG canvas. */
  svgContainer: 'w-full overflow-x-auto overscroll-x-contain py-4',

  /** Milestone marker — circle + label, keyboard focusable. */
  milestone: [
    'flex flex-col items-center gap-1 text-xs',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded',
  ].join(' '),

  /** Status color fills for milestone markers. */
  milestoneOnTrack: 'fill-primary text-primary dark:text-primary',
  milestoneAtRisk: 'fill-[var(--warning)] text-[var(--warning)]',
  milestoneBlocked: 'fill-destructive text-destructive',

  /** Dashed dependency arrow between milestones. */
  dependencyArrow: 'stroke-muted-foreground/50 stroke-1 [stroke-dasharray:4_3]',

  /** Drag handle — grab cursor, scale on hover (desktop only, FR-040). */
  dragHandle:
    'cursor-grab active:cursor-grabbing md:hover:scale-110 transition-transform motion-reduce:transition-none',
} as const;

/* ------------------------------------------------------------------ */
/*  KPI Dashboard (US-009)                                             */
/* ------------------------------------------------------------------ */

const dashboard = {
  /** Widget grid — 2 columns desktop, 1 column mobile. */
  widgetGrid: 'grid gap-3 sm:grid-cols-2',

  /** Single widget card. */
  widget: 'rounded-lg border border-border bg-background p-4 shadow-sm dark:bg-card',

  /** Widget title — small uppercase label. */
  widgetTitle: 'text-[10px] font-medium uppercase tracking-wider text-muted-foreground',

  /** Primary metric value — large bold number. */
  widgetValue: 'mt-1 text-2xl font-bold tabular-nums text-foreground',

  /** Trend indicators with arrow icon gap. */
  trendUp: 'inline-flex items-center gap-0.5 text-xs font-medium text-primary dark:text-primary',
  trendDown: 'inline-flex items-center gap-0.5 text-xs font-medium text-destructive',
  trendFlat: 'inline-flex items-center gap-0.5 text-xs font-medium text-muted-foreground',

  /** Circular gauge wrapper for SPI/CPI metrics. */
  gaugeContainer: 'relative flex items-center justify-center',

  /** Auto-refresh indicator — "Auto-refresh: 30s" badge. */
  refreshBadge: [
    'inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5',
    'text-[10px] font-medium text-muted-foreground',
  ].join(' '),
} as const;

/* ------------------------------------------------------------------ */
/*  Aggregated export                                                  */
/* ------------------------------------------------------------------ */

export const pmBlockStyles = {
  shared,
  focusRing,
  inlineInput,
  checklist,
  decision,
  priorityColors,
  form,
  raci,
  risk,
  visualization,
  timeline,
  dashboard,
} as const;

export type PMBlockStyleSection = keyof typeof pmBlockStyles;
