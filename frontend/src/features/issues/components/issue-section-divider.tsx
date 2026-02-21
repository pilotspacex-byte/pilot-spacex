'use client';

/**
 * IssueSectionDivider - Centered divider with label for sections below the editor.
 */

export interface IssueSectionDividerProps {
  label: string;
  count?: number;
}

export function IssueSectionDivider({ label, count }: IssueSectionDividerProps) {
  return (
    <div className="flex items-center gap-2 pb-2 pt-4">
      <div className="h-px flex-1 bg-border" />
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
        {count != null && count > 0 && <span className="ml-1.5 tabular-nums">({count})</span>}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
