'use client';

/**
 * IssueDetailSheet — Slide-over panel showing issue detail from homepage.
 *
 * Opens when clicking an issue in the "Working On" section.
 * Shows identifier, title, state, priority, assignee, linked PRs, and cycle.
 */

import { ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { getIssueStateKey } from '@/lib/issue-helpers';
import { issuesApi } from '@/services/api/issues';
import { useIssueLinks } from '@/features/issues/hooks/use-issue-links';
import { LinkedPRsList } from '@/features/issues/components/linked-prs-list';
import { STATE_COLORS } from './BriefEntries';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface IssueDetailSheetProps {
  issueId: string | null;
  workspaceId: string;
  workspaceSlug: string;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IssueDetailSheet({
  issueId,
  workspaceId,
  workspaceSlug,
  onClose,
}: IssueDetailSheetProps) {
  const isOpen = !!issueId;

  const {
    data: issue,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['homepage', 'issue-detail', workspaceId, issueId],
    queryFn: () => issuesApi.get(workspaceId, issueId!),
    enabled: isOpen && !!workspaceId,
    staleTime: 30_000,
  });

  // issueId is guaranteed non-null when isOpen is true; the hook's enabled guard
  // (!!issueId) prevents any query execution when the sheet is closed.
  const { pullRequests, isLoading: linksLoading } = useIssueLinks(
    workspaceId,
    issueId ?? '' // '' is safe: enabled guard blocks the query when issueId is null
  );

  const stateKey = issue ? getIssueStateKey(issue.state) : 'backlog';
  const stateInfo = STATE_COLORS[stateKey] ?? { dot: 'bg-muted-foreground/40', label: 'Backlog' };

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="flex flex-col">
        <SheetHeader>
          {isLoading ? (
            <>
              <div className="h-4 w-16 animate-pulse rounded bg-muted/30" />
              <div className="h-6 w-48 animate-pulse rounded bg-muted/30" />
            </>
          ) : issue ? (
            <>
              <SheetDescription className="font-mono text-xs text-muted-foreground">
                {issue.identifier}
              </SheetDescription>
              <SheetTitle className="text-lg font-semibold leading-tight">{issue.name}</SheetTitle>
            </>
          ) : isError ? (
            <SheetTitle className="text-destructive">Failed to load issue</SheetTitle>
          ) : (
            <SheetTitle>Issue not found</SheetTitle>
          )}
        </SheetHeader>

        {issue && (
          <div className="flex-1 space-y-4 overflow-y-auto px-4">
            {/* State + Priority */}
            <div className="flex items-center gap-2">
              <span
                className={cn('h-2 w-2 shrink-0 rounded-full', stateInfo.dot)}
                aria-hidden="true"
              />
              <Badge variant="outline" className="text-xs">
                {stateInfo.label}
              </Badge>
              {issue.priority && (
                <Badge variant="secondary" className="text-xs capitalize">
                  {issue.priority}
                </Badge>
              )}
            </div>

            {/* Assignee */}
            {issue.assignee && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="text-xs font-medium text-foreground">Assignee:</span>
                <span>{issue.assignee.displayName ?? issue.assignee.email}</span>
              </div>
            )}

            {/* Linked PRs */}
            <div>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Pull Requests
              </h3>
              {linksLoading ? (
                <div className="h-10 animate-pulse rounded bg-muted/30" />
              ) : (
                <LinkedPRsList links={pullRequests} />
              )}
            </div>

            {/* Cycle info — omitted: Issue type only carries cycleId (UUID), no name.
                 Add cycle name once Issue type includes embedded cycle.name. */}
          </div>
        )}

        <SheetFooter className="border-t border-border-subtle pt-2">
          {issueId && (
            <Button variant="outline" size="sm" asChild className="w-full gap-1.5">
              <Link href={`/${workspaceSlug}/issues/${issueId}`}>
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Open full page
              </Link>
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
