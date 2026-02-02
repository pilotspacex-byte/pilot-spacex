/**
 * Standard focus ring classes for interactive elements.
 * Uses 3px primary ring at 30% opacity per UI design spec (Section 5).
 */
export const focusRingClass =
  'focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/30';

/**
 * Focus ring classes for container elements that contain focusable children.
 * Applied via :focus-within pseudo-class.
 */
export const focusWithinRingClass =
  'focus-within:outline-none focus-within:ring-[3px] focus-within:ring-primary/30';

/**
 * Combines the focus ring with a border highlight on focus.
 * Useful for input-like elements that need both ring and border feedback.
 */
export const focusInputClass =
  'focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-primary/30 focus-visible:border-primary';
