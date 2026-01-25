/**
 * AI PR Review Component
 *
 * Displays AI code review results with inline comments and severity indicators.
 * Follows Web Interface Guidelines:
 * - Clear AI-generated content labeling (FR-020)
 * - Accessible severity indicators
 * - Proper semantic structure for code display
 */

import * as React from 'react';
import {
  IconAlertTriangle,
  IconAlertCircle,
  IconInfoCircle,
  IconShieldCheck,
  IconCode,
  IconBug,
  IconRocket,
  IconGitPullRequest,
  IconExternalLink,
  IconCheck,
  IconX,
  IconRefresh,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '../components/card';
import { Badge, AIBadge } from '../components/badge';
import { Button } from '../components/button';
import { UserAvatar } from '../components/avatar';

// =============================================================================
// TYPES
// =============================================================================

export type ReviewSeverity = 'critical' | 'warning' | 'suggestion' | 'info';

export type ReviewCategory =
  | 'architecture'
  | 'security'
  | 'performance'
  | 'code-quality'
  | 'best-practice';

export interface ReviewComment {
  id: string;
  severity: ReviewSeverity;
  category: ReviewCategory;
  title: string;
  description: string;
  filePath: string;
  lineStart: number;
  lineEnd?: number;
  codeSnippet?: string;
  suggestedFix?: string;
  rationale?: string;
  documentationUrl?: string;
}

export interface PRReviewSummary {
  prId: number;
  prTitle: string;
  prUrl: string;
  repository: string;
  author: {
    name: string;
    avatarUrl?: string;
  };
  reviewedAt: Date;
  reviewDuration: number; // seconds
  overallScore: number; // 0-100
  comments: ReviewComment[];
  filesReviewed: number;
  linesAnalyzed: number;
}

export interface AIPRReviewProps {
  review: PRReviewSummary;
  onRerunReview: () => void;
  onCommentResolve: (commentId: string) => void;
  onCommentDismiss: (commentId: string) => void;
  onViewInGitHub: (comment: ReviewComment) => void;
  isRerunning?: boolean;
}

// =============================================================================
// SEVERITY CONFIG
// =============================================================================

const severityConfig: Record<
  ReviewSeverity,
  { icon: typeof IconAlertCircle; color: string; label: string; bgColor: string }
> = {
  critical: {
    icon: IconAlertCircle,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    label: 'Critical',
  },
  warning: {
    icon: IconAlertTriangle,
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-50 dark:bg-yellow-950/30',
    label: 'Warning',
  },
  suggestion: {
    icon: IconInfoCircle,
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
    label: 'Suggestion',
  },
  info: {
    icon: IconInfoCircle,
    color: 'text-gray-600 dark:text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-900/30',
    label: 'Info',
  },
};

const categoryConfig: Record<
  ReviewCategory,
  { icon: typeof IconCode; label: string }
> = {
  architecture: { icon: IconCode, label: 'Architecture' },
  security: { icon: IconShieldCheck, label: 'Security' },
  performance: { icon: IconRocket, label: 'Performance' },
  'code-quality': { icon: IconBug, label: 'Code Quality' },
  'best-practice': { icon: IconInfoCircle, label: 'Best Practice' },
};

// =============================================================================
// REVIEW HEADER
// =============================================================================

interface ReviewHeaderProps {
  review: PRReviewSummary;
  onRerun: () => void;
  isRerunning: boolean;
}

function ReviewHeader({ review, onRerun, isRerunning }: ReviewHeaderProps) {
  const scoreColor =
    review.overallScore >= 80
      ? 'text-green-600'
      : review.overallScore >= 60
        ? 'text-yellow-600'
        : 'text-red-600';

  return (
    <div className="flex items-start justify-between border-b pb-4">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-ai-suggestion/10">
          <IconGitPullRequest className="h-6 w-6 text-ai-suggestion" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{review.prTitle}</h2>
            <AIBadge type="generated">AI Review</AIBadge>
          </div>
          <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
            <span>#{review.prId}</span>
            <span>{review.repository}</span>
            <div className="flex items-center gap-1">
              <UserAvatar user={review.author} size="xs" />
              <span>{review.author.name}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Score */}
        <div className="text-right">
          <div className={cn('text-2xl font-bold tabular-nums', scoreColor)}>
            {review.overallScore}
          </div>
          <div className="text-xs text-muted-foreground">Quality Score</div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRerun}
            loading={isRerunning}
          >
            <IconRefresh className="mr-1 h-4 w-4" />
            Re-run Review
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href={review.prUrl} target="_blank" rel="noopener noreferrer">
              <IconExternalLink className="mr-1 h-4 w-4" />
              View PR
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// SUMMARY STATS
// =============================================================================

interface SummaryStatsProps {
  review: PRReviewSummary;
}

function SummaryStats({ review }: SummaryStatsProps) {
  const criticalCount = review.comments.filter((c) => c.severity === 'critical').length;
  const warningCount = review.comments.filter((c) => c.severity === 'warning').length;
  const suggestionCount = review.comments.filter(
    (c) => c.severity === 'suggestion' || c.severity === 'info'
  ).length;

  return (
    <div className="grid grid-cols-5 gap-4 py-4">
      <div className="text-center">
        <div className="text-2xl font-bold tabular-nums text-red-600">
          {criticalCount}
        </div>
        <div className="text-xs text-muted-foreground">Critical</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold tabular-nums text-yellow-600">
          {warningCount}
        </div>
        <div className="text-xs text-muted-foreground">Warnings</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold tabular-nums text-blue-600">
          {suggestionCount}
        </div>
        <div className="text-xs text-muted-foreground">Suggestions</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold tabular-nums">
          {review.filesReviewed}
        </div>
        <div className="text-xs text-muted-foreground">Files</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold tabular-nums">
          {review.linesAnalyzed.toLocaleString()}
        </div>
        <div className="text-xs text-muted-foreground">Lines</div>
      </div>
    </div>
  );
}

// =============================================================================
// REVIEW COMMENT CARD
// =============================================================================

interface ReviewCommentCardProps {
  comment: ReviewComment;
  onResolve: () => void;
  onDismiss: () => void;
  onViewInGitHub: () => void;
}

function ReviewCommentCard({
  comment,
  onResolve,
  onDismiss,
  onViewInGitHub,
}: ReviewCommentCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(
    comment.severity === 'critical' || comment.severity === 'warning'
  );
  const severity = severityConfig[comment.severity];
  const category = categoryConfig[comment.category];
  const SeverityIcon = severity.icon;
  const CategoryIcon = category.icon;

  return (
    <Card
      className={cn(
        'overflow-hidden border-l-4',
        comment.severity === 'critical' && 'border-l-red-500',
        comment.severity === 'warning' && 'border-l-yellow-500',
        comment.severity === 'suggestion' && 'border-l-blue-500',
        comment.severity === 'info' && 'border-l-gray-400'
      )}
    >
      <div className={cn('p-4', severity.bgColor)}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <SeverityIcon className={cn('h-5 w-5 flex-shrink-0', severity.color)} />
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-medium">{comment.title}</h4>
                <Badge variant="outline" className="text-xs">
                  <CategoryIcon className="mr-1 h-3 w-3" />
                  {category.label}
                </Badge>
                <Badge className={cn('text-xs', severity.color, severity.bgColor)}>
                  {severity.label}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {comment.filePath}:{comment.lineStart}
                {comment.lineEnd && comment.lineEnd !== comment.lineStart
                  ? `-${comment.lineEnd}`
                  : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onResolve}
              aria-label="Mark as resolved"
            >
              <IconCheck className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onDismiss}
              aria-label="Dismiss comment"
            >
              <IconX className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onViewInGitHub}
              aria-label="View in GitHub"
            >
              <IconExternalLink className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Expandable content */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-sm text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </button>
      </div>

      {isExpanded && (
        <CardContent className="space-y-4 pt-4">
          {/* Description */}
          <p className="text-sm">{comment.description}</p>

          {/* Code snippet */}
          {comment.codeSnippet && (
            <div className="rounded-md bg-muted p-3">
              <div className="mb-1 text-xs font-medium text-muted-foreground">
                Current Code
              </div>
              <pre className="overflow-x-auto text-sm">
                <code>{comment.codeSnippet}</code>
              </pre>
            </div>
          )}

          {/* Suggested fix */}
          {comment.suggestedFix && (
            <div className="rounded-md border border-green-200 bg-green-50 p-3 dark:border-green-900 dark:bg-green-950/30">
              <div className="mb-1 text-xs font-medium text-green-700 dark:text-green-300">
                Suggested Fix
              </div>
              <pre className="overflow-x-auto text-sm">
                <code>{comment.suggestedFix}</code>
              </pre>
            </div>
          )}

          {/* Rationale */}
          {comment.rationale && (
            <div className="rounded-md border-l-2 border-ai-suggestion bg-ai-suggestion/5 p-3">
              <div className="mb-1 flex items-center gap-1 text-xs font-medium text-ai-suggestion">
                <AIBadge type="generated" />
                Rationale
              </div>
              <p className="text-sm text-muted-foreground">{comment.rationale}</p>
            </div>
          )}

          {/* Documentation link */}
          {comment.documentationUrl && (
            <a
              href={comment.documentationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <IconExternalLink className="h-3 w-3" />
              Learn more
            </a>
          )}
        </CardContent>
      )}
    </Card>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function AIPRReview({
  review,
  onRerunReview,
  onCommentResolve,
  onCommentDismiss,
  onViewInGitHub,
  isRerunning = false,
}: AIPRReviewProps) {
  const [filterSeverity, setFilterSeverity] = React.useState<ReviewSeverity | 'all'>('all');
  const [filterCategory, setFilterCategory] = React.useState<ReviewCategory | 'all'>('all');

  const filteredComments = React.useMemo(() => {
    return review.comments.filter((comment) => {
      if (filterSeverity !== 'all' && comment.severity !== filterSeverity) {
        return false;
      }
      if (filterCategory !== 'all' && comment.category !== filterCategory) {
        return false;
      }
      return true;
    });
  }, [review.comments, filterSeverity, filterCategory]);

  // Group comments by file
  const commentsByFile = React.useMemo(() => {
    const grouped: Record<string, ReviewComment[]> = {};
    filteredComments.forEach((comment) => {
      if (!grouped[comment.filePath]) {
        grouped[comment.filePath] = [];
      }
      grouped[comment.filePath].push(comment);
    });
    return grouped;
  }, [filteredComments]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <ReviewHeader review={review} onRerun={onRerunReview} isRerunning={isRerunning} />

      {/* Summary Stats */}
      <SummaryStats review={review} />

      {/* Filters */}
      <div className="flex items-center gap-4 border-b pb-4">
        <span className="text-sm font-medium">Filter:</span>

        {/* Severity filter */}
        <div className="flex gap-1">
          {(['all', 'critical', 'warning', 'suggestion', 'info'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={cn(
                'rounded-md px-2 py-1 text-xs font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                filterSeverity === sev
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              )}
            >
              {sev === 'all' ? 'All' : severityConfig[sev].label}
            </button>
          ))}
        </div>

        {/* Category filter */}
        <div className="flex gap-1">
          {(['all', 'architecture', 'security', 'performance', 'code-quality', 'best-practice'] as const).map(
            (cat) => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={cn(
                  'rounded-md px-2 py-1 text-xs font-medium transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  filterCategory === cat
                    ? 'bg-secondary text-secondary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {cat === 'all' ? 'All Categories' : categoryConfig[cat].label}
              </button>
            )
          )}
        </div>
      </div>

      {/* Comments grouped by file */}
      <div className="space-y-6">
        {Object.entries(commentsByFile).map(([filePath, comments]) => (
          <div key={filePath}>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-medium">
              <IconCode className="h-4 w-4 text-muted-foreground" />
              {filePath}
              <Badge variant="outline">{comments.length}</Badge>
            </h3>
            <div className="space-y-3">
              {comments
                .sort((a, b) => a.lineStart - b.lineStart)
                .map((comment) => (
                  <ReviewCommentCard
                    key={comment.id}
                    comment={comment}
                    onResolve={() => onCommentResolve(comment.id)}
                    onDismiss={() => onCommentDismiss(comment.id)}
                    onViewInGitHub={() => onViewInGitHub(comment)}
                  />
                ))}
            </div>
          </div>
        ))}

        {filteredComments.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <IconCheck className="mb-2 h-12 w-12 text-green-500" />
            <h3 className="text-lg font-medium">No issues found</h3>
            <p className="text-sm text-muted-foreground">
              {review.comments.length === 0
                ? 'This PR looks good! No issues were detected.'
                : 'No issues match the current filters.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
