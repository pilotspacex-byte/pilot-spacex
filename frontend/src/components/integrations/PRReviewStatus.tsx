'use client';

/**
 * PRReviewStatus - Display AI-powered PR review status and results.
 *
 * T200: Shows review status (pending/processing/completed/failed),
 * progress indicator, summary with counts by severity, expandable
 * comments grouped by file, and re-run action.
 *
 * @example
 * ```tsx
 * <PRReviewStatus
 *   integrationId={integration.id}
 *   prNumber={123}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  RefreshCw,
  ExternalLink,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  FileCode,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ReviewCommentCard, type ReviewComment, type ReviewCategory } from './ReviewCommentCard';
import { ReviewSummary, type ApprovalRecommendation } from './ReviewSummary';
import { usePRReview, usePRReviewStatus } from '@/features/integrations/hooks';

// ============================================================================
// Types
// ============================================================================

export type ReviewStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ReviewResult {
  /** Review status */
  status: ReviewStatus;
  /** Processing progress (0-100) */
  progress?: number;
  /** Summary text */
  summary?: string;
  /** Review comments */
  comments: ReviewComment[];
  /** Approval recommendation */
  approvalRecommendation?: ApprovalRecommendation;
  /** Error message if failed */
  errorMessage?: string;
  /** GitHub PR URL */
  prUrl?: string;
}

export interface PRReviewStatusProps {
  /** Integration ID (workspace GitHub integration) */
  integrationId: string;
  /** PR number */
  prNumber: number;
  /** GitHub repository full name (owner/repo) */
  repositoryFullName?: string;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Status Configuration
// ============================================================================

interface StatusConfig {
  icon: React.ElementType;
  label: string;
  badgeClass: string;
}

const statusConfig: Record<ReviewStatus, StatusConfig> = {
  pending: {
    icon: Clock,
    label: 'Pending',
    badgeClass: 'bg-muted text-muted-foreground border-border',
  },
  processing: {
    icon: Loader2,
    label: 'Processing',
    badgeClass:
      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
  },
  completed: {
    icon: CheckCircle2,
    label: 'Completed',
    badgeClass:
      'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
    badgeClass:
      'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  },
};

// ============================================================================
// File Group Component
// ============================================================================

interface FileGroupProps {
  filePath: string;
  comments: ReviewComment[];
  defaultOpen?: boolean;
}

function FileGroup({ filePath, comments, defaultOpen = false }: FileGroupProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  // Count severity levels
  const criticalCount = comments.filter((c) => c.severity === 'critical').length;
  const warningCount = comments.filter((c) => c.severity === 'warning').length;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex items-center justify-between w-full p-2 rounded-lg hover:bg-muted/50 transition-colors">
        <div className="flex items-center gap-2 min-w-0">
          {isOpen ? (
            <ChevronDown className="size-4 shrink-0" />
          ) : (
            <ChevronRight className="size-4 shrink-0" />
          )}
          <FileCode className="size-4 shrink-0 text-muted-foreground" />
          <span className="text-sm font-medium truncate">{filePath}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {criticalCount > 0 && (
            <Badge
              variant="outline"
              className="bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 text-xs"
            >
              {criticalCount}
            </Badge>
          )}
          {warningCount > 0 && (
            <Badge
              variant="outline"
              className="bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 text-xs"
            >
              {warningCount}
            </Badge>
          )}
          <Badge variant="secondary" className="text-xs">
            {comments.length}
          </Badge>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 space-y-2 pl-6">
        {comments
          .sort((a, b) => a.lineNumber - b.lineNumber)
          .map((comment, idx) => (
            <ReviewCommentCard
              key={`${comment.filePath}-${comment.lineNumber}-${idx}`}
              comment={comment}
              showFilePath={false}
            />
          ))}
      </CollapsibleContent>
    </Collapsible>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function PRReviewSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-5 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-8 w-24" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-6 w-20" />
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Empty State
// ============================================================================

interface EmptyStateProps {
  prNumber: number;
  onTriggerReview: () => void;
  isTriggering: boolean;
}

function EmptyState({ prNumber, onTriggerReview, isTriggering }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-8 text-center">
        <FileCode className="size-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground mb-4">
          No AI review has been run for PR #{prNumber} yet.
        </p>
        <Button onClick={onTriggerReview} disabled={isTriggering}>
          {isTriggering ? (
            <>
              <Loader2 className="size-4 mr-2 animate-spin" />
              Starting Review...
            </>
          ) : (
            <>
              <RefreshCw className="size-4 mr-2" />
              Run AI Review
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const PRReviewStatus = observer(function PRReviewStatus({
  integrationId,
  prNumber,
  repositoryFullName,
  className,
}: PRReviewStatusProps) {
  const [selectedCategory, setSelectedCategory] = React.useState<ReviewCategory | null>(null);

  // Hooks
  const { data: reviewResult, isLoading, error } = usePRReviewStatus(integrationId, prNumber);

  const { trigger: triggerReview, isTriggering } = usePRReview(integrationId, prNumber);

  // Group comments by file - must be called unconditionally
  const commentsByFile = React.useMemo(() => {
    if (!reviewResult) return new Map<string, ReviewComment[]>();

    const filtered = selectedCategory
      ? reviewResult.comments.filter((c) => c.category === selectedCategory)
      : reviewResult.comments;

    const grouped = new Map<string, ReviewComment[]>();
    filtered.forEach((comment) => {
      const existing = grouped.get(comment.filePath) || [];
      existing.push(comment);
      grouped.set(comment.filePath, existing);
    });
    return grouped;
  }, [reviewResult, selectedCategory]);

  // Loading state
  if (isLoading) {
    return <PRReviewSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-8 text-center">
          <XCircle className="size-12 text-destructive mb-4" />
          <p className="text-muted-foreground">Failed to load review status</p>
          <p className="text-xs text-muted-foreground mt-1">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  // No review yet
  if (!reviewResult) {
    return (
      <EmptyState prNumber={prNumber} onTriggerReview={triggerReview} isTriggering={isTriggering} />
    );
  }

  const status = statusConfig[reviewResult.status];
  const StatusIcon = status.icon;

  // Build GitHub PR URL
  const prUrl =
    reviewResult.prUrl ||
    (repositoryFullName ? `https://github.com/${repositoryFullName}/pull/${prNumber}` : null);

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-lg">PR #{prNumber} Review</CardTitle>
              <Badge variant="outline" className={cn('gap-1', status.badgeClass)}>
                <StatusIcon
                  className={cn('size-3', reviewResult.status === 'processing' && 'animate-spin')}
                />
                {status.label}
              </Badge>
            </div>
            <CardDescription>AI-powered code review analysis</CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {prUrl && (
              <Button variant="outline" size="sm" asChild>
                <a href={prUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="size-4 mr-1" />
                  View PR
                </a>
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={triggerReview}
              disabled={isTriggering || reviewResult.status === 'processing'}
            >
              {isTriggering ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              <span className="ml-1.5">Re-run</span>
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Progress bar for processing */}
        {reviewResult.status === 'processing' && reviewResult.progress !== undefined && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Analyzing...</span>
              <span className="font-medium">{reviewResult.progress}%</span>
            </div>
            <Progress value={reviewResult.progress} className="h-2" />
          </div>
        )}

        {/* Error message */}
        {reviewResult.status === 'failed' && reviewResult.errorMessage && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">{reviewResult.errorMessage}</p>
          </div>
        )}

        {/* Summary (only when completed) */}
        {reviewResult.status === 'completed' && reviewResult.summary && (
          <ReviewSummary
            summary={reviewResult.summary}
            comments={reviewResult.comments}
            approvalRecommendation={reviewResult.approvalRecommendation}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
          />
        )}

        {/* Comments grouped by file */}
        {reviewResult.status === 'completed' && reviewResult.comments.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Comments ({commentsByFile.size} files)</h3>
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {Array.from(commentsByFile.entries())
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([filePath, comments]) => (
                    <FileGroup
                      key={filePath}
                      filePath={filePath}
                      comments={comments}
                      defaultOpen={commentsByFile.size <= 3}
                    />
                  ))}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* No comments */}
        {reviewResult.status === 'completed' && reviewResult.comments.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle2 className="size-12 text-green-500 mb-4" />
            <p className="text-muted-foreground">No issues found in this PR.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default PRReviewStatus;
