'use client';

/**
 * CommitList - Display commits linked to an issue.
 *
 * T191: Shows commit hash, message, author, date with links to GitHub.
 *
 * @example
 * ```tsx
 * <CommitList
 *   commits={commits}
 *   isLoading={isLoading}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { GitCommit, ExternalLink, Copy, Check, ChevronDown, ChevronUp, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { GitHubCommit } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

export interface CommitListProps {
  /** List of commits */
  commits: GitHubCommit[];
  /** Loading state */
  isLoading?: boolean;
  /** Maximum commits to show initially */
  maxDisplay?: number;
  /** Show in compact mode */
  compact?: boolean;
  /** Show as card */
  asCard?: boolean;
  /** Additional class name */
  className?: string;
}

export interface CommitRowProps {
  commit: GitHubCommit;
  compact?: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return formatDate(dateStr);
}

// ============================================================================
// Copy SHA Button
// ============================================================================

interface CopySHAButtonProps {
  sha: string;
}

function CopySHAButton({ sha }: CopySHAButtonProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    try {
      await navigator.clipboard.writeText(sha);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="icon" className="size-6" onClick={handleCopy}>
            {copied ? <Check className="size-3 text-green-500" /> : <Copy className="size-3" />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{copied ? 'Copied!' : 'Copy full SHA'}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Commit Row Component
// ============================================================================

const CommitRow = React.memo(function CommitRow({ commit, compact = false }: CommitRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const hasMultilineMessage = commit.message !== commit.messageHeadline;

  return (
    <div
      className={cn(
        'group flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/30',
        compact && 'p-2'
      )}
    >
      {/* Commit icon */}
      <div className={cn('rounded-full bg-muted p-1.5 shrink-0', compact && 'p-1')}>
        <GitCommit className={cn('size-4 text-muted-foreground', compact && 'size-3')} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* SHA and message headline */}
        <div className="flex items-start gap-2 mb-1">
          <div className="flex items-center gap-1">
            <a
              href={commit.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-primary hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {commit.shortSha}
            </a>
            <CopySHAButton sha={commit.sha} />
          </div>
        </div>

        {/* Message */}
        <div className="space-y-1">
          <p className={cn('text-sm font-medium', compact && 'text-xs')}>
            {commit.messageHeadline}
          </p>

          {/* Expandable full message */}
          {hasMultilineMessage && (
            <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
              <CollapsibleTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="size-3 mr-1" />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="size-3 mr-1" />
                      Show more
                    </>
                  )}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <pre className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground bg-muted rounded p-2 font-mono">
                  {commit.message}
                </pre>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>

        {/* Author and date */}
        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            {commit.authorAvatarUrl ? (
              <Avatar className="size-4">
                <AvatarImage src={commit.authorAvatarUrl} />
                <AvatarFallback className="text-[8px]">
                  {getInitials(commit.authorName)}
                </AvatarFallback>
              </Avatar>
            ) : (
              <User className="size-3" />
            )}
            <span>{commit.authorName}</span>
          </div>

          <span>&middot;</span>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>{formatTimeAgo(commit.committedAt)}</span>
              </TooltipTrigger>
              <TooltipContent>{new Date(commit.committedAt).toLocaleString()}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* External link */}
      <a
        href={commit.url}
        target="_blank"
        rel="noopener noreferrer"
        className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <ExternalLink className="size-4 text-muted-foreground hover:text-foreground" />
      </a>
    </div>
  );
});

// ============================================================================
// Loading Skeleton
// ============================================================================

function CommitListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 rounded-lg border p-3">
          <Skeleton className="size-8 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function CommitListEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <GitCommit className="size-12 text-muted-foreground/30 mb-3" />
      <p className="text-sm text-muted-foreground">No commits linked</p>
      <p className="text-xs text-muted-foreground/60 mt-1">
        Commits mentioning this issue will appear here
      </p>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const CommitList = observer(function CommitList({
  commits,
  isLoading = false,
  maxDisplay = 5,
  compact = false,
  asCard = false,
  className,
}: CommitListProps) {
  const [showAll, setShowAll] = React.useState(false);

  const displayedCommits = showAll ? commits : commits.slice(0, maxDisplay);
  const hasMore = commits.length > maxDisplay;

  const content = (
    <>
      {isLoading ? (
        <CommitListSkeleton count={3} />
      ) : commits.length === 0 ? (
        <CommitListEmpty />
      ) : (
        <div className="space-y-2">
          {displayedCommits.map((commit) => (
            <CommitRow key={commit.sha} commit={commit} compact={compact} />
          ))}

          {hasMore && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(!showAll)}
              className="w-full"
            >
              {showAll ? (
                <>
                  <ChevronUp className="size-4 mr-2" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="size-4 mr-2" />
                  Show {commits.length - maxDisplay} more commits
                </>
              )}
            </Button>
          )}
        </div>
      )}
    </>
  );

  if (asCard) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <GitCommit className="size-4" />
                Commits
              </CardTitle>
              <CardDescription>
                {commits.length} commit{commits.length !== 1 ? 's' : ''} linked
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>{content}</CardContent>
      </Card>
    );
  }

  return <div className={className}>{content}</div>;
});

export default CommitList;
