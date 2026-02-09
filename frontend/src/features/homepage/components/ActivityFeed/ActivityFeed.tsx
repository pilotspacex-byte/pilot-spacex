'use client';

/**
 * ActivityFeed (H033) — Container with infinite scroll, day grouping, empty state.
 * Renders ActivityDayGroups for each time bucket (Today, Yesterday, This Week).
 */

import { useEffect, useMemo, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWorkspaceStore } from '@/stores/RootStore';
import { useHomepageActivity } from '../../hooks/useHomepageActivity';
import { DAY_GROUP_ORDER, DAY_GROUP_LABELS, MAX_RENDERED_ACTIVITY_ITEMS } from '../../constants';
import type { ActivityCard } from '../../types';
import { DayGroupHeader } from './DayGroupHeader';
import { NoteActivityCard } from './NoteActivityCard';
import { IssueActivityCard } from './IssueActivityCard';
import { ActivityFeedSkeleton } from './ActivityFeedSkeleton';

interface ActivityFeedProps {
  workspaceSlug: string;
}

function renderCard(card: ActivityCard, workspaceSlug: string) {
  if (card.type === 'note') {
    return <NoteActivityCard key={card.id} card={card} workspaceSlug={workspaceSlug} />;
  }
  return <IssueActivityCard key={card.id} card={card} workspaceSlug={workspaceSlug} />;
}

export const ActivityFeed = observer(function ActivityFeed({ workspaceSlug }: ActivityFeedProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError, refetch } =
    useHomepageActivity({ workspaceId });

  // Flatten pages into grouped data
  const dayGroups = useMemo(() => {
    if (!data?.pages) return [];

    // Merge all pages' data buckets (capped at MAX_RENDERED_ACTIVITY_ITEMS)
    const merged: Record<string, ActivityCard[]> = {};
    const seen = new Set<string>();
    let totalItems = 0;
    for (const page of data.pages) {
      for (const [key, cards] of Object.entries(page.data)) {
        if (!merged[key]) merged[key] = [];
        for (const card of cards) {
          if (totalItems >= MAX_RENDERED_ACTIVITY_ITEMS) break;
          if (!seen.has(card.id)) {
            seen.add(card.id);
            merged[key].push(card);
            totalItems++;
          }
        }
        if (totalItems >= MAX_RENDERED_ACTIVITY_ITEMS) break;
      }
      if (totalItems >= MAX_RENDERED_ACTIVITY_ITEMS) break;
    }

    // Return ordered groups with items
    return DAY_GROUP_ORDER.filter((key) => (merged[key]?.length ?? 0) > 0).map((key) => ({
      key,
      label: DAY_GROUP_LABELS[key],
      items: merged[key] ?? [],
    }));
  }, [data]);

  // IntersectionObserver for infinite scroll
  useEffect(() => {
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

  if (isLoading) {
    return <ActivityFeedSkeleton />;
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-12">
        <p className="text-sm text-muted-foreground">Failed to load activity</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  if (dayGroups.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <FileText className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">
          Your workspace is quiet. Start a note to get going!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {dayGroups.map((group) => (
        <div key={group.key}>
          <DayGroupHeader label={group.label} />
          <div className="space-y-2">
            {group.items.map((card) => renderCard(card, workspaceSlug))}
          </div>
        </div>
      ))}

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-px" aria-hidden="true" />

      {isFetchingNextPage && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
          <span className="sr-only">Loading more activity</span>
        </div>
      )}
    </div>
  );
});
