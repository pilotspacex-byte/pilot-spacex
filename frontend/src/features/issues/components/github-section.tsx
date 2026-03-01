'use client';

/**
 * GitHubSection - Collapsible GitHub activity panel for the issue detail canvas.
 * Pure presentational — data is passed as props (no observer wrapper needed).
 */

import { Github, GitPullRequest, GitCommit, GitBranch, ExternalLink } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { CollapsibleSection } from './collapsible-section';
import { CreateBranchPopover } from './create-branch-popover';
import type { IntegrationLink } from '@/types';

export interface GitHubSectionProps {
  /** Links filtered to link_type === 'pull_request' */
  pullRequests: IntegrationLink[];
  /** Links filtered to link_type === 'commit' */
  commits: IntegrationLink[];
  /** Links filtered to link_type === 'branch' */
  branches: IntegrationLink[];
  isLoading?: boolean;
  /** Active GitHub integration ID — required to show Create Branch button. */
  integrationId?: string;
  workspaceId?: string;
  issueId?: string;
}

const PR_STATE: Record<string, string> = {
  open: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  merged: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  closed: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
};

const LINK_CLS =
  'group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';
const EXT_ICO = 'size-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-50';

export function GitHubSection({
  pullRequests,
  commits,
  branches,
  isLoading = false,
  integrationId,
  workspaceId,
  issueId,
}: GitHubSectionProps) {
  const total = pullRequests.length + commits.length + branches.length;
  const showCreateBranch = branches.length === 0 && !isLoading;
  const canCreateBranch = !!(integrationId && workspaceId && issueId);

  return (
    <CollapsibleSection
      title="GitHub"
      icon={<Github className="size-3.5" />}
      defaultOpen={total > 0}
      count={total > 0 ? total : undefined}
    >
      {isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-2 px-2 py-1.5">
              <Skeleton className="size-4 rounded-full shrink-0" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="ml-auto h-4 w-12 rounded-full" />
            </div>
          ))}
        </div>
      ) : total === 0 ? (
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <Github className="size-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">No linked GitHub activity</p>
          {showCreateBranch && (
            <CreateBranchAction
              canCreate={canCreateBranch}
              integrationId={integrationId}
              workspaceId={workspaceId}
              issueId={issueId}
            />
          )}
        </div>
      ) : (
        <div>
          {pullRequests.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Pull Requests</p>
              <ul role="list" aria-label="Linked pull requests">
                {pullRequests.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitPullRequest className="size-4 shrink-0 text-muted-foreground" />
                      {link.prNumber != null && (
                        <span className="shrink-0 font-mono text-xs text-muted-foreground">
                          #{link.prNumber}
                        </span>
                      )}
                      <span className="truncate">
                        {link.prTitle ?? link.title ?? link.externalId}
                      </span>
                      {link.prStatus && (
                        <span
                          className={cn(
                            'ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                            PR_STATE[link.prStatus]
                          )}
                        >
                          {link.prStatus.charAt(0).toUpperCase() + link.prStatus.slice(1)}
                        </span>
                      )}
                      <ExternalLink className={cn(EXT_ICO, !link.prStatus && 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
          {pullRequests.length > 0 && commits.length > 0 && <hr className="border-border my-2" />}
          {commits.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Recent Commits</p>
              <ul role="list" aria-label="Linked commits">
                {commits.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitCommit className="size-4 shrink-0 text-muted-foreground" />
                      <span className="truncate">{link.title ?? link.externalId}</span>
                      {link.authorName && (
                        <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                          {link.authorName}
                        </span>
                      )}
                      <ExternalLink className={cn(EXT_ICO, !link.authorName && 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
          {(pullRequests.length > 0 || commits.length > 0) && branches.length > 0 && (
            <hr className="border-border my-2" />
          )}
          {branches.length > 0 && (
            <>
              <p className="px-2 mb-1 text-xs font-medium text-muted-foreground">Branches</p>
              <ul role="list" aria-label="Linked branches">
                {branches.map((link) => (
                  <li key={link.id}>
                    <a
                      href={link.externalUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={LINK_CLS}
                    >
                      <GitBranch className="size-4 shrink-0 text-muted-foreground" />
                      <span className="truncate font-mono text-xs">{link.externalId}</span>
                      <ExternalLink className={cn(EXT_ICO, 'ml-auto')} />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
          {showCreateBranch && (
            <div className="mt-3 px-2">
              <CreateBranchAction
                canCreate={canCreateBranch}
                integrationId={integrationId}
                workspaceId={workspaceId}
                issueId={issueId}
              />
            </div>
          )}
        </div>
      )}
    </CollapsibleSection>
  );
}

// ---------------------------------------------------------------------------
// Internal helper — renders Create Branch button or disabled tooltip variant
// ---------------------------------------------------------------------------

interface CreateBranchActionProps {
  canCreate: boolean;
  integrationId?: string;
  workspaceId?: string;
  issueId?: string;
}

function CreateBranchAction({
  canCreate,
  integrationId,
  workspaceId,
  issueId,
}: CreateBranchActionProps) {
  if (canCreate) {
    return (
      <CreateBranchPopover
        integrationId={integrationId!}
        workspaceId={workspaceId!}
        issueId={issueId!}
      />
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="outline" size="sm" disabled aria-label="Create GitHub branch">
          <GitBranch className="size-3.5" />
          Create branch
        </Button>
      </TooltipTrigger>
      <TooltipContent>Connect GitHub first</TooltipContent>
    </Tooltip>
  );
}
