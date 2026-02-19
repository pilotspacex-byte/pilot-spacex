/**
 * CSS styles for DensityExtension (M8, Feature 016).
 *
 * T-129: Collapsed block — single-line summary via ::before pseudo-element
 * T-133: Focus Mode — hides AI blocks (density-focus-hidden)
 * T-132: AI group indicator — grouped blocks with summary header
 */

export const DENSITY_STYLES = `
/* ── Collapsed blocks (T-129/T-130/T-131) ────────────────────────── */
.density-collapsed {
  overflow: hidden;
  max-height: 1.75rem;
  cursor: pointer;
  border-radius: 4px;
  background: var(--muted, rgba(0,0,0,0.04));
  margin-block: 2px;
  position: relative;
  user-select: none;
  transition: background 0.1s;
}

.density-collapsed:hover {
  background: var(--muted-foreground, rgba(0,0,0,0.08));
}

/* Show the data-summary as a single-line pill */
.density-collapsed::before {
  content: attr(data-summary);
  display: block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--muted-foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: inherit;
  line-height: 1.25rem;
}

/* Hide actual content when collapsed */
.density-collapsed > * {
  visibility: hidden;
  pointer-events: none;
}

/* ── Focus Mode (T-133) ───────────────────────────────────────────── */
.density-focus-hidden {
  display: none !important;
}

/* Focus Mode indicator on editor root */
.editor-focus-mode .density-focus-hidden {
  display: none !important;
}

/* Focus Mode active badge on editor (optional visual cue) */
[data-focus-mode="true"] .ProseMirror::before {
  content: "Focus Mode";
  display: block;
  position: sticky;
  top: 0;
  z-index: 10;
  padding: 2px 8px;
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ai, #6B8FAD);
  background: var(--ai-muted, rgba(107,143,173,0.08));
  border-bottom: 1px solid var(--ai-border, rgba(107,143,173,0.2));
  text-align: center;
}
` as const;

export default DENSITY_STYLES;
