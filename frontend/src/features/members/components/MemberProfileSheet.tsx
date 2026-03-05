/**
 * MemberProfileSheet — Quick-peek slide-in panel for member profile.
 *
 * Opens from member row click in MembersPage.
 * Shows profile header + contribution stats + condensed 5-item activity timeline.
 * Footer: "View full profile" link.
 */

'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  ExternalLink,
  ArrowRight,
  MessageSquare,
  Plus,
  Pencil,
  GitPullRequest,
} from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { useMemberProfile } from '../hooks/useMemberProfile';
import { useMemberActivity } from '../hooks/useMemberActivity';
import { MemberProfileHeader } from './MemberProfileHeader';
import { MemberContributionStats } from './MemberContributionStats';
import type { MemberActivityItem } from '../types';

export interface MemberProfileSheetProps {
  userId: string | null;
  workspaceId: string;
  workspaceSlug: string;
  onClose: () => void;
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

function ActivityLine({ item }: { item: MemberActivityItem }) {
  const { icon: Icon, className: iconClass } = ACTIVITY_ICON[item.activityType] ?? DEFAULT_ICON;

  const description =
    item.activityType === 'comment'
      ? `Commented: "${item.comment?.slice(0, 60) ?? ''}"`
      : item.field && item.newValue
        ? `Changed ${item.field} \u2192 ${item.newValue?.slice(0, 60) ?? ''}`
        : item.activityType.replace(/_/g, ' ');

  return (
    <div className="flex items-start gap-2 py-1.5 text-sm">
      <div
        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted"
        aria-hidden="true"
      >
        {React.createElement(Icon, { className: `h-3 w-3 ${iconClass}` })}
      </div>
      <div className="min-w-0">
        {item.issueIdentifier && (
          <span className="font-mono text-xs text-muted-foreground">{item.issueIdentifier} </span>
        )}
        <span className="text-muted-foreground">{description}</span>
      </div>
    </div>
  );
}

export function MemberProfileSheet({
  userId,
  workspaceId,
  workspaceSlug,
  onClose,
}: MemberProfileSheetProps) {
  const isOpen = !!userId;

  const {
    data: member,
    isLoading: memberLoading,
    isError: memberError,
  } = useMemberProfile(workspaceId, userId ?? '');

  const { data: activityData, isLoading: activityLoading } = useMemberActivity(
    workspaceId,
    userId ?? ''
  );

  const recentItems = activityData?.pages[0]?.items.slice(0, 5) ?? [];

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="flex w-full flex-col sm:max-w-md">
        <SheetHeader>
          {memberLoading ? (
            <>
              <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-48" />
                </div>
              </div>
              <SheetTitle className="sr-only">Loading member profile</SheetTitle>
              <SheetDescription className="sr-only">Loading</SheetDescription>
            </>
          ) : memberError ? (
            <>
              <SheetTitle>Failed to load profile</SheetTitle>
              <SheetDescription>
                This member could not be loaded. They may have been removed from the workspace.
              </SheetDescription>
            </>
          ) : member ? (
            <>
              <SheetTitle className="sr-only">
                {member.fullName ?? member.email} — Member Profile
              </SheetTitle>
              <SheetDescription className="sr-only">
                Profile details for {member.email}
              </SheetDescription>
              <MemberProfileHeader member={member} compact />
            </>
          ) : null}
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {memberError ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center px-4">
              <p className="text-sm text-muted-foreground">
                Try closing and reopening this panel, or contact a workspace admin.
              </p>
            </div>
          ) : (
            <>
              {/* Stats */}
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Contributions
              </p>
              <MemberContributionStats stats={member?.stats} isLoading={memberLoading} />

              {/* Recent activity (condensed 5 items) */}
              <div className="mt-5">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Recent Activity
                </p>
                {activityLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-8 w-full" />
                    ))}
                  </div>
                ) : recentItems.length === 0 ? (
                  <p className="py-6 text-center text-xs text-muted-foreground/70">
                    No recent activity to show.
                  </p>
                ) : (
                  <div>
                    {recentItems.map((item) => (
                      <ActivityLine key={item.id} item={item} />
                    ))}
                    {userId && (
                      <Link
                        href={`/${workspaceSlug}/members/${userId}`}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                      >
                        See all activity
                        <ArrowRight className="h-3 w-3" aria-hidden="true" />
                      </Link>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <Separator />
        <SheetFooter className="pt-3">
          {userId && (
            <Button asChild variant="outline" className="w-full">
              <Link
                href={`/${workspaceSlug}/members/${userId}`}
                className="flex items-center justify-center gap-2"
              >
                View full profile
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
