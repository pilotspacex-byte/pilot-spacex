const CODE_LINE_WIDTHS = [78, 92, 65, 88, 71, 95, 60, 83, 76, 90, 68, 85];

export function CodeSkeleton() {
  return (
    <div className="p-6 space-y-2 animate-pulse">
      <div className="h-3 w-24 rounded bg-muted" />
      {CODE_LINE_WIDTHS.map((w, i) => (
        <div key={i} className="h-3 rounded bg-muted" style={{ width: `${w}%` }} />
      ))}
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div className="p-6 space-y-3 animate-pulse">
      <div className="flex gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-4 flex-1 rounded bg-muted" />
        ))}
      </div>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: 4 }).map((_, j) => (
            <div key={j} className="h-3 flex-1 rounded bg-muted/60" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ProseSkeleton() {
  return (
    <div className="p-6 space-y-3 animate-pulse">
      <div className="h-5 w-48 rounded bg-muted" />
      <div className="h-3 w-full rounded bg-muted/60" />
      <div className="h-3 w-11/12 rounded bg-muted/60" />
      <div className="h-3 w-4/5 rounded bg-muted/60" />
      <div className="h-4 w-36 rounded bg-muted mt-4" />
      <div className="h-3 w-full rounded bg-muted/60" />
      <div className="h-3 w-3/4 rounded bg-muted/60" />
    </div>
  );
}
