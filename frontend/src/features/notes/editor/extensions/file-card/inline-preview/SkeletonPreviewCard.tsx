'use client';

/**
 * SkeletonPreviewCard — Loading state for the inline file preview card.
 *
 * Renders 8 shimmer bars with staggered widths matching the UI-SPEC.
 * Widths: [90, 72, 85, 55, 91, 63, 80, 48] (percent)
 */

const BAR_WIDTHS = [90, 72, 85, 55, 91, 63, 80, 48] as const;

export function SkeletonPreviewCard() {
  return (
    <div
      className="p-4 space-y-2"
      aria-busy="true"
      aria-label="Loading file preview"
    >
      {BAR_WIDTHS.map((w, i) => (
        <div
          key={i}
          className="h-3 rounded bg-border animate-pulse"
          style={{ width: `${w}%` }}
        />
      ))}
    </div>
  );
}
