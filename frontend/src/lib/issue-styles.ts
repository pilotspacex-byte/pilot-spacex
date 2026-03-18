/**
 * Shared issue priority and confidence display styles.
 *
 * Uses design token CSS variables so colors adapt to light/dark theme.
 * Single source of truth — replaces duplicated maps in ExtractionPreviewModal,
 * ExtractionReviewPanel, and StructuredResultCard.
 */

/** Priority badge styles keyed by numeric priority (0=Urgent .. 4=None). */
export const PRIORITY_BADGE_STYLES: Record<number, { label: string; className: string }> = {
  0: {
    label: 'Urgent',
    className: 'bg-priority-urgent/10 text-[var(--priority-urgent)] border-transparent',
  },
  1: {
    label: 'High',
    className: 'bg-priority-high/10 text-[var(--priority-high)] border-transparent',
  },
  2: {
    label: 'Medium',
    className: 'bg-priority-medium/10 text-[var(--priority-medium)] border-transparent',
  },
  3: {
    label: 'Low',
    className: 'bg-priority-low/10 text-[var(--priority-low)] border-transparent',
  },
  4: {
    label: 'None',
    className: 'bg-priority-none/10 text-[var(--priority-none)] border-transparent',
  },
};

/** Priority styles keyed by name (for StructuredResultCard). */
export const PRIORITY_NAME_STYLES: Record<string, { textClass: string; dotClass: string }> = {
  urgent: {
    textClass: 'text-[var(--priority-urgent)]',
    dotClass: 'bg-[var(--priority-urgent)]',
  },
  high: {
    textClass: 'text-[var(--priority-high)]',
    dotClass: 'bg-[var(--priority-high)]',
  },
  medium: {
    textClass: 'text-[var(--priority-medium)]',
    dotClass: 'bg-[var(--priority-medium)]',
  },
  low: {
    textClass: 'text-[var(--priority-low)]',
    dotClass: 'bg-[var(--priority-low)]',
  },
  none: {
    textClass: 'text-muted-foreground',
    dotClass: 'bg-muted-foreground',
  },
};

const FALLBACK_PRIORITY_NAME = {
  textClass: 'text-muted-foreground',
  dotClass: 'bg-muted-foreground',
};

/** Resolve priority name styles with fallback. */
export function getPriorityNameStyle(name: string) {
  return PRIORITY_NAME_STYLES[name] ?? FALLBACK_PRIORITY_NAME;
}

/** Confidence badge styles keyed by tag name. */
export const CONFIDENCE_BADGE_STYLES: Record<string, { label: string; className: string }> = {
  explicit: {
    label: 'HIGH',
    className: 'bg-state-done/10 text-[var(--state-done)] border-transparent',
  },
  implicit: {
    label: 'MEDIUM',
    className: 'bg-priority-medium/10 text-[var(--priority-medium)] border-transparent',
  },
  related: {
    label: 'LOW',
    className: 'bg-priority-none/10 text-[var(--priority-none)] border-transparent',
  },
};

/** Confidence text color keyed by tag name (for ExtractionPreviewModal). */
export const CONFIDENCE_TEXT_STYLES: Record<string, string> = {
  explicit: 'text-[var(--state-done)]',
  implicit: 'text-[var(--priority-medium)]',
  related: 'text-muted-foreground',
};

/** Get confidence display from numeric score (for StructuredResultCard). */
export function getConfidenceFromScore(score: number): {
  label: string;
  className: string;
} {
  if (score >= 0.7)
    return {
      label: 'High',
      className: 'bg-state-done/10 text-[var(--state-done)]',
    };
  if (score >= 0.5)
    return {
      label: 'Medium',
      className: 'bg-priority-medium/10 text-[var(--priority-medium)]',
    };
  return {
    label: 'Low',
    className: 'bg-priority-none/10 text-[var(--priority-none)]',
  };
}

const FALLBACK_PRIORITY_BADGE = {
  label: 'Medium',
  className: 'bg-priority-medium/10 text-[var(--priority-medium)] border-transparent',
};

const FALLBACK_CONFIDENCE_BADGE = {
  label: 'LOW',
  className: 'bg-priority-none/10 text-[var(--priority-none)] border-transparent',
};

/** Resolve priority badge styles with fallback. */
export function getPriorityBadge(priority: number) {
  return PRIORITY_BADGE_STYLES[priority] ?? FALLBACK_PRIORITY_BADGE;
}

/** Resolve confidence badge styles with fallback. */
export function getConfidenceBadge(tag: string) {
  return CONFIDENCE_BADGE_STYLES[tag] ?? FALLBACK_CONFIDENCE_BADGE;
}

/** Resolve confidence text color with fallback. */
export function getConfidenceTextColor(tag: string) {
  return CONFIDENCE_TEXT_STYLES[tag] ?? 'text-muted-foreground';
}
