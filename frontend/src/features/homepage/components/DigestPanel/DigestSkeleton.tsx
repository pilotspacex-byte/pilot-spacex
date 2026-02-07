'use client';

/**
 * DigestSkeleton — Loading skeleton for the Digest Panel.
 * Renders 4 placeholder suggestion cards matching DigestSuggestionCard dimensions.
 */

import { Skeleton } from '@/components/ui/skeleton';

export function DigestSkeleton() {
  return (
    <div className="space-y-2" aria-label="Loading digest suggestions" role="status">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="flex gap-3 rounded-md bg-background-subtle p-3">
          <Skeleton className="h-4 w-4 shrink-0 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading digest suggestions</span>
    </div>
  );
}
