'use client';

import { GitPullRequest, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IntegrationLink } from '@/types';

export interface LinkedPRsListProps {
  links: IntegrationLink[];
  className?: string;
}

const statusConfig: Record<
  NonNullable<IntegrationLink['prStatus']>,
  { label: string; className: string }
> = {
  open: {
    label: 'Open',
    className: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  },
  merged: {
    label: 'Merged',
    className: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  },
  closed: {
    label: 'Closed',
    className: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  },
};

/**
 * LinkedPRsList displays GitHub pull requests linked to an issue.
 * Shows PR number, title, status badge, and external link.
 *
 * @example
 * ```tsx
 * <LinkedPRsList links={issue.integrationLinks} />
 * ```
 */
export function LinkedPRsList({ links, className }: LinkedPRsListProps) {
  const prLinks = links.filter((link) => link.integrationType === 'github_pr');

  if (prLinks.length === 0) {
    return (
      <div className={cn('flex flex-col items-center gap-2 py-6 text-center', className)}>
        <GitPullRequest className="size-8 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">No linked pull requests</p>
      </div>
    );
  }

  return (
    <ul className={cn('space-y-1', className)} role="list" aria-label="Linked pull requests">
      {prLinks.map((link) => {
        const status = link.prStatus ? statusConfig[link.prStatus] : null;

        return (
          <li key={link.id}>
            <a
              href={link.externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                'hover:bg-accent',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
              )}
            >
              <GitPullRequest className="size-4 shrink-0 text-muted-foreground" />
              {link.prNumber != null && (
                <span className="shrink-0 font-mono text-xs text-muted-foreground">
                  #{link.prNumber}
                </span>
              )}
              <span className="truncate">{link.prTitle ?? link.externalId}</span>
              {status && (
                <span
                  className={cn(
                    'shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                    status.className
                  )}
                >
                  {status.label}
                </span>
              )}
              <ExternalLink className="ml-auto size-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-50" />
            </a>
          </li>
        );
      })}
    </ul>
  );
}

export default LinkedPRsList;
