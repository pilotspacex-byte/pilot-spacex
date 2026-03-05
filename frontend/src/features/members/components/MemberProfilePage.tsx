/**
 * MemberProfilePage — Full profile view with tabs (Timeline | Issues).
 *
 * Used by the /[workspaceSlug]/members/[userId] App Router page.
 * Fetches all data client-side; parent page.tsx is a thin server component wrapper.
 * Resolves workspaceId from WorkspaceStore using the slug.
 */

'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useStore } from '@/stores';
import { useMemberProfile } from '../hooks/useMemberProfile';
import { useMemberIssueDigest } from '../hooks/useMemberIssueDigest';
import { MemberProfileHeader } from './MemberProfileHeader';
import { MemberContributionStats } from './MemberContributionStats';
import { MemberActivityFeed } from './MemberActivityFeed';

interface MemberProfilePageProps {
  workspaceSlug: string;
  userId: string;
}

interface MemberProfileContentProps {
  workspaceId: string;
  workspaceSlug: string;
  userId: string;
}

function MemberProfileContent({ workspaceId, workspaceSlug, userId }: MemberProfileContentProps) {
  const { data: member, isLoading, isError } = useMemberProfile(workspaceId, userId);
  const { data: issueDigestItems = [] } = useMemberIssueDigest(workspaceId, userId);

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-sm text-muted-foreground">
          Member not found or you don&apos;t have access.
        </p>
        <Button asChild variant="ghost" className="mt-4">
          <Link href={`/${workspaceSlug}/members`}>Back to members</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
      {/* Back nav */}
      <Button asChild variant="ghost" size="sm" className="-ml-2 mb-4">
        <Link href={`/${workspaceSlug}/members`} className="flex items-center gap-1.5">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Members
        </Link>
      </Button>

      <h1 className="sr-only">
        {isLoading
          ? 'Loading member profile'
          : member
            ? `${member.fullName ?? member.email} — Member Profile`
            : 'Member profile'}
      </h1>

      {/* Profile header */}
      {isLoading ? (
        <div className="flex items-start gap-4">
          <Skeleton className="h-16 w-16 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
      ) : member ? (
        <MemberProfileHeader member={member} />
      ) : null}

      <Separator className="my-6" />

      {/* Contribution stats */}
      <section aria-label="Contribution statistics">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Contributions
        </h3>
        <MemberContributionStats stats={member?.stats} isLoading={isLoading} />
      </section>

      <Separator className="my-6" />

      {/* Activity feed + issue digest */}
      <section aria-label="Activity and issues">
        <MemberActivityFeed
          workspaceId={workspaceId}
          userId={userId}
          workspaceSlug={workspaceSlug}
          issueDigestItems={issueDigestItems}
        />
      </section>
    </div>
  );
}

export function MemberProfilePage({ workspaceSlug, userId }: MemberProfilePageProps) {
  const { workspaceStore } = useStore();
  const workspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = workspace?.id;

  if (!workspaceId) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
        <Skeleton className="mb-4 h-8 w-24" />
        <div className="flex items-start gap-4">
          <Skeleton className="h-16 w-16 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <MemberProfileContent workspaceId={workspaceId} workspaceSlug={workspaceSlug} userId={userId} />
  );
}
