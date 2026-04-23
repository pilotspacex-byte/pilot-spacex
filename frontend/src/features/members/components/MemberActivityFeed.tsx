/**
 * MemberActivityFeed — Tabs: Activity Timeline | Issue Digest.
 *
 * Timeline uses infinite scroll via useMemberActivity.
 * Issue digest shows issues grouped by state (passed as prop from parent).
 */

'use client';

import * as React from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  Plus,
  ArrowRight,
  GitPullRequest,
  Pencil,
  Clock,
  Loader2,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useMemberActivity } from '../hooks/useMemberActivity';
import { MemberIssueDigest } from './MemberIssueDigest';
import type { MemberActivityItem, MemberIssueDigestItem } from '../types';

interface MemberActivityFeedProps {
  workspaceId: string;
  userId: string;
  workspaceSlug: string;
  /** Pre-fetched issues for the digest tab */
  issueDigestItems: MemberIssueDigestItem[];
}

const ACTIVITY_ICON: Record<string, { icon: React.ElementType; className: string }> = {
  comment: { icon: MessageSquare, className: 'text-blue-500' },
  issue_created: { icon: Plus, className: 'text-green-600' },
  state_change: { icon: ArrowRight, className: 'text-amber-600' },
  field_change: { icon: Pencil, className: 'text-muted-foreground' },
  field_update: { icon: Pencil, className: 'text-muted-foreground' },
  pr_linked: { icon: GitPullRequest, className: 'text-purple-600' },
};

const DEFAULT_ICON = { icon: Pencil, className: 'text-muted-foreground' };

function ActivityItemRow({ item }: { item: MemberActivityItem }) {
  const timeAgo = formatDistanceToNow(new Date(item.createdAt), { addSuffix: true });
  const { icon: Icon, className: iconClass } = ACTIVITY_ICON[item.activityType] ?? DEFAULT_ICON;

  const description = (() => {
    if (item.activityType === 'comment') return `Commented: "${item.comment?.slice(0, 80) ?? ''}"`;
    if (item.field && item.newValue) return `Changed ${item.field} to ${item.newValue}`;
    if (item.activityType === 'issue_created') return 'Created issue';
    return item.activityType.replace(/_/g, ' ');
  })();

  return (
    <div className="flex gap-3 py-2.5" role="listitem">
      <div
        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted"
        aria-hidden="true"
      >
        {React.createElement(Icon, { className: `h-3.5 w-3.5 ${iconClass}` })}
      </div>
      <div className="min-w-0 flex-1">
        {item.issueIdentifier && (
          <span className="font-mono text-xs text-muted-foreground">{item.issueIdentifier} </span>
        )}
        <span className="text-sm">{description}</span>
        <p className="mt-0.5 text-xs text-muted-foreground">{timeAgo}</p>
      </div>
    </div>
  );
}

const SKELETON_WIDTHS = ['w-3/4', 'w-1/2', 'w-2/3', 'w-4/5', 'w-3/5'];

function ActivitySkeleton() {
  return (
    <div className="space-y-3 py-2" aria-label="Loading activities" aria-busy="true">
      {SKELETON_WIDTHS.map((w, i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="mt-0.5 h-6 w-6 rounded-full" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className={`h-4 ${w}`} />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MemberActivityFeed({
  workspaceId,
  userId,
  workspaceSlug,
  issueDigestItems,
}: MemberActivityFeedProps) {
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } = useMemberActivity(
    workspaceId,
    userId
  );

  const allItems = React.useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data]);

  return (
    <Tabs defaultValue="timeline">
      <TabsList className="w-full">
        <TabsTrigger value="timeline" className="flex-1">
          Activity Timeline
        </TabsTrigger>
        <TabsTrigger value="issues" className="flex-1">
          Task Digest
        </TabsTrigger>
      </TabsList>

      <TabsContent value="timeline" className="mt-4">
        {isLoading ? (
          <ActivitySkeleton />
        ) : allItems.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <Clock className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
            </div>
            <p className="text-sm font-medium text-muted-foreground">No activity yet</p>
            <p className="max-w-[240px] text-xs text-muted-foreground/70">
              Activity will appear here as this member works on issues and leaves comments.
            </p>
          </div>
        ) : (
          <>
            <p className="mb-2 text-xs text-muted-foreground">
              Showing {allItems.length} of {data!.pages[0]!.total} activities
            </p>
            <div role="list" aria-label="Activity timeline">
              {allItems.map((item) => (
                <ActivityItemRow key={item.id} item={item} />
              ))}
            </div>
            {hasNextPage && (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => void fetchNextPage()}
                  disabled={isFetchingNextPage}
                  aria-label="Load more activity"
                >
                  {isFetchingNextPage ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : null}
                  Load more
                </Button>
              </div>
            )}
          </>
        )}
      </TabsContent>

      <TabsContent value="issues" className="mt-4">
        <MemberIssueDigest issues={issueDigestItems} workspaceSlug={workspaceSlug} />
      </TabsContent>
    </Tabs>
  );
}
