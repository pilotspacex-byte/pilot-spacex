'use client';

/**
 * PRLinkBadge - Display linked pull request status badge.
 *
 * T190: Shows PR number, status (open/merged/closed), and links to GitHub.
 *
 * @example
 * ```tsx
 * <PRLinkBadge
 *   number={123}
 *   state="merged"
 *   title="Add new feature"
 *   url="https://github.com/org/repo/pull/123"
 * />
 * ```
 */

import * as React from 'react';
import { GitPullRequest, GitMerge, XCircle, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { GitHubPullRequest } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

export type PRState = 'open' | 'closed' | 'merged';

export interface PRLinkBadgeProps {
  /** PR number */
  number: number;
  /** PR state */
  state: PRState;
  /** PR title for tooltip */
  title?: string;
  /** GitHub URL */
  url: string;
  /** Show full PR info (not just badge) */
  expanded?: boolean;
  /** Additional class name */
  className?: string;
}

export interface PRLinkBadgeFromDataProps {
  /** Pull request data object */
  pullRequest: GitHubPullRequest;
  /** Show full PR info (not just badge) */
  expanded?: boolean;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// State Configuration
// ============================================================================

interface StateConfig {
  icon: React.ElementType;
  label: string;
  badgeClass: string;
  iconClass: string;
}

const stateConfig: Record<PRState, StateConfig> = {
  open: {
    icon: GitPullRequest,
    label: 'Open',
    badgeClass:
      'bg-green-100 text-green-700 border-green-200 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
    iconClass: 'text-green-600 dark:text-green-400',
  },
  merged: {
    icon: GitMerge,
    label: 'Merged',
    badgeClass:
      'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800',
    iconClass: 'text-purple-600 dark:text-purple-400',
  },
  closed: {
    icon: XCircle,
    label: 'Closed',
    badgeClass:
      'bg-red-100 text-red-700 border-red-200 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
    iconClass: 'text-red-600 dark:text-red-400',
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

function getTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}y ago`;
}

// ============================================================================
// Compact Badge Component
// ============================================================================

export function PRLinkBadge({
  number,
  state,
  title,
  url,
  expanded = false,
  className,
}: PRLinkBadgeProps) {
  const config = stateConfig[state];
  const Icon = config.icon;

  const badge = (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn('inline-flex', className)}
      onClick={(e) => e.stopPropagation()}
    >
      <Badge
        variant="outline"
        className={cn('cursor-pointer transition-colors gap-1.5', config.badgeClass)}
      >
        <Icon className={cn('size-3', config.iconClass)} />
        <span className="font-medium">#{number}</span>
        {expanded && <ExternalLink className="size-3 ml-1 opacity-50" />}
      </Badge>
    </a>
  );

  if (!title) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-1">
            <p className="font-medium line-clamp-2">{title}</p>
            <p className="text-xs text-muted-foreground">{config.label} pull request</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Expanded Card Component
// ============================================================================

export function PRLinkCard({ pullRequest, className }: PRLinkBadgeFromDataProps) {
  const config = stateConfig[pullRequest.state];
  const Icon = config.icon;

  const statusDate =
    pullRequest.state === 'merged'
      ? pullRequest.mergedAt
      : pullRequest.state === 'closed'
        ? pullRequest.closedAt
        : pullRequest.updatedAt;

  const statusAction =
    pullRequest.state === 'merged'
      ? 'Merged'
      : pullRequest.state === 'closed'
        ? 'Closed'
        : 'Updated';

  return (
    <a
      href={pullRequest.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn('block rounded-lg border p-3 transition-colors hover:bg-muted/50', className)}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'rounded-full p-1.5 mt-0.5',
            pullRequest.state === 'open' && 'bg-green-100 dark:bg-green-900/30',
            pullRequest.state === 'merged' && 'bg-purple-100 dark:bg-purple-900/30',
            pullRequest.state === 'closed' && 'bg-red-100 dark:bg-red-900/30'
          )}
        >
          <Icon className={cn('size-4', config.iconClass)} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm">#{pullRequest.number}</span>
            <Badge variant="secondary" className="text-xs">
              {config.label}
            </Badge>
          </div>

          <p className="text-sm font-medium line-clamp-2 mb-2">{pullRequest.title}</p>

          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>
              {pullRequest.headBranch} &rarr; {pullRequest.baseBranch}
            </span>
            {statusDate && (
              <span>
                {statusAction} {getTimeAgo(statusDate)}
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="flex items-center gap-3 mt-2 text-xs">
            <span className="text-green-600">+{pullRequest.additions}</span>
            <span className="text-red-600">-{pullRequest.deletions}</span>
            <span className="text-muted-foreground">{pullRequest.changedFiles} files</span>
          </div>
        </div>

        <ExternalLink className="size-4 text-muted-foreground shrink-0" />
      </div>
    </a>
  );
}

// ============================================================================
// From Data Component
// ============================================================================

export function PRLinkBadgeFromData({
  pullRequest,
  expanded = false,
  className,
}: PRLinkBadgeFromDataProps) {
  if (expanded) {
    return <PRLinkCard pullRequest={pullRequest} className={className} />;
  }

  return (
    <PRLinkBadge
      number={pullRequest.number}
      state={pullRequest.state}
      title={pullRequest.title}
      url={pullRequest.url}
      className={className}
    />
  );
}

// ============================================================================
// List of PR Badges
// ============================================================================

export interface PRLinkBadgeListProps {
  pullRequests: GitHubPullRequest[];
  maxDisplay?: number;
  expanded?: boolean;
  className?: string;
}

export function PRLinkBadgeList({
  pullRequests,
  maxDisplay = 3,
  expanded = false,
  className,
}: PRLinkBadgeListProps) {
  if (pullRequests.length === 0) {
    return null;
  }

  const displayed = pullRequests.slice(0, maxDisplay);
  const remaining = pullRequests.length - maxDisplay;

  if (expanded) {
    return (
      <div className={cn('space-y-2', className)}>
        {pullRequests.map((pr) => (
          <PRLinkCard key={pr.id} pullRequest={pr} />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {displayed.map((pr) => (
        <PRLinkBadgeFromData key={pr.id} pullRequest={pr} />
      ))}
      {remaining > 0 && (
        <Badge variant="outline" className="text-muted-foreground">
          +{remaining} more
        </Badge>
      )}
    </div>
  );
}

export default PRLinkBadge;
