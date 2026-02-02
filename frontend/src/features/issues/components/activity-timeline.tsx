/**
 * ActivityTimeline - Composition component combining ActivityEntry + CommentInput
 * with infinite scroll pagination.
 *
 * @see T037 - Issue Detail Page activity timeline
 */
'use client';

import * as React from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ActivityEntry } from './activity-entry';
import { CommentInput } from './comment-input';
import { useActivities } from '../hooks/use-activities';
import { useAddComment } from '../hooks/use-add-comment';

export interface ActivityTimelineProps {
  issueId: string;
  workspaceId: string;
  disabled?: boolean;
}

export function ActivityTimeline({
  issueId,
  workspaceId,
  disabled = false,
}: ActivityTimelineProps) {
  const sentinelRef = React.useRef<HTMLDivElement>(null);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError, refetch } =
    useActivities(workspaceId, issueId);

  const addComment = useAddComment(workspaceId, issueId);

  const activities = React.useMemo(
    () => data?.pages.flatMap((page) => page.activities) ?? [],
    [data]
  );

  React.useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleCommentSubmit = React.useCallback(
    (content: string) => {
      addComment.mutate(content);
    },
    [addComment]
  );

  if (isLoading) {
    return (
      <section aria-label="Activity timeline" className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground">Activity</h3>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
          <span className="sr-only">Loading activities</span>
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section aria-label="Activity timeline" className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground">Activity</h3>
        <div className="flex flex-col items-center gap-3 py-8">
          <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">Failed to load activities</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Activity timeline" className="space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Activity</h3>

      {activities.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No activity yet</p>
      ) : (
        <div role="list" aria-label="Activity entries">
          {activities.map((activity, index) => (
            <div role="listitem" key={activity.id}>
              <ActivityEntry activity={activity} isLast={index === activities.length - 1} />
            </div>
          ))}
        </div>
      )}

      <div ref={sentinelRef} aria-hidden="true" />

      {isFetchingNextPage && (
        <div className="flex items-center justify-center gap-2 py-3">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
          <span className="text-xs text-muted-foreground">Loading more...</span>
        </div>
      )}

      <CommentInput
        onSubmit={handleCommentSubmit}
        isSubmitting={addComment.isPending}
        disabled={disabled}
      />
    </section>
  );
}
