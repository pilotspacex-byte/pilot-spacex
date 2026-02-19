/**
 * ownership-styles — CSS for block-level ownership indicators (T-108, M6b)
 *
 * AI blocks: 3px solid left border using --ai (#6B8FAD), muted background
 * Shared blocks: 3px dashed left border using --primary at 50%, muted background
 *
 * Gutter icons are rendered via ::before pseudo-elements using data-owner attr.
 * Tooltips use title attribute (native browser) for accessibility.
 */

export const ownershipStyles = `
/* ── AI block treatment ──────────────────────────────────────────────── */
.ownership-block.ownership-ai {
  position: relative;
  border-left: 3px solid var(--ai, #6B8FAD);
  background-color: color-mix(in srgb, var(--ai, #6B8FAD) 8%, transparent);
  padding-left: 0.75rem;
  /* AI-M6: reserve space on the right for the skill label */
  padding-right: 5rem;
  margin-left: 0;
  border-radius: 0 6px 6px 0;
  /* AI-C2: indicate non-editable state */
  cursor: not-allowed;
}

/* Dark mode: slightly more visible background */
@media (prefers-color-scheme: dark) {
  .ownership-block.ownership-ai {
    background-color: color-mix(in srgb, var(--ai, #7DA4C4) 12%, transparent);
  }
}

/* Skill label — top-right of AI block group first element */
.ownership-block.ownership-ai::after {
  content: attr(data-skill);
  position: absolute;
  top: 0.25rem;
  right: 0.5rem;
  font-size: 0.6875rem; /* 11px / text-xs */
  font-family: ui-monospace, 'Cascadia Code', 'Roboto Mono', monospace;
  color: var(--ai, #6B8FAD);
  opacity: 0.8;
  pointer-events: none;
}

/* ── Shared block treatment ──────────────────────────────────────────── */
.ownership-block.ownership-shared {
  position: relative;
  border-left: 3px dashed color-mix(in srgb, var(--primary, #29A386) 50%, transparent);
  background-color: color-mix(in srgb, var(--primary, #29A386) 6%, transparent);
  padding-left: 0.75rem;
  margin-left: 0;
  border-radius: 0 6px 6px 0;
}

/* ── Selection: allow copy but cursor indicates protected ───────────── */
.ownership-block.ownership-ai *::selection {
  background-color: color-mix(in srgb, var(--ai, #6B8FAD) 25%, transparent);
}

/* ── Hover: subtle highlight to indicate interactivity ─────────────── */
.ownership-block.ownership-ai:hover {
  background-color: color-mix(in srgb, var(--ai, #6B8FAD) 12%, transparent);
}

.ownership-block.ownership-shared:hover {
  background-color: color-mix(in srgb, var(--primary, #29A386) 10%, transparent);
}

/* ── Focus mode: hide AI blocks ─────────────────────────────────────── */
.editor-focus-mode .ownership-block.ownership-ai {
  display: none;
}

/* ── Reduced motion ──────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .ownership-block {
    transition: none !important;
  }
}
`;

export default ownershipStyles;
