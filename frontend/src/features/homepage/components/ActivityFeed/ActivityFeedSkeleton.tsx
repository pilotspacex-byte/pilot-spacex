/**
 * ActivityFeedSkeleton (H032) — Loading skeleton matching card dimensions.
 * Renders alternating note (160px) and issue (140px) skeleton cards.
 */

import { Skeleton } from '@/components/ui/skeleton';

interface ActivityFeedSkeletonProps {
  /** Number of skeleton cards to render */
  count?: number;
}

export function ActivityFeedSkeleton({ count = 6 }: ActivityFeedSkeletonProps) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading activity feed">
      {/* Day group header skeleton */}
      <div className="flex items-center gap-3">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-px flex-1" />
      </div>

      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          className={`rounded-md border border-border-subtle p-4 ${i % 2 === 0 ? 'h-[160px]' : 'h-[140px]'}`}
        >
          {/* Title row */}
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded" />
            <Skeleton className="h-4 w-2/3" />
          </div>

          {/* Meta row */}
          <div className="mt-3 flex items-center gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-12 rounded-full" />
          </div>

          {/* Bottom row */}
          <div className="mt-auto flex items-center justify-end pt-6">
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
      ))}

      <span className="sr-only">Loading activity feed</span>
    </div>
  );
}
