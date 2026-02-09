/**
 * DayGroupHeader (H031) — "Today", "Yesterday", "This Week" sticky headers
 * with separator line for the activity feed day groups.
 */

interface DayGroupHeaderProps {
  label: string;
}

export function DayGroupHeader({ label }: DayGroupHeaderProps) {
  return (
    <div className="mt-4 mb-2 flex items-center gap-3 first:mt-0">
      <span className="shrink-0 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border-subtle" aria-hidden="true" />
    </div>
  );
}
