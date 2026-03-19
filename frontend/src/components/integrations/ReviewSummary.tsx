'use client';

/**
 * ReviewSummary - Overview of PR review results with counts by severity.
 *
 * T200: Shows summary statistics, approval recommendation, and allows
 * filtering by category.
 */

import * as React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Lightbulb,
  CheckCircle2,
  XCircle,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import type { ReviewComment, ReviewSeverity, ReviewCategory } from './ReviewCommentCard';

// ============================================================================
// Types
// ============================================================================

export type ApprovalRecommendation = 'approve' | 'request_changes' | 'comment';

export interface ReviewSummaryProps {
  /** Summary text */
  summary: string;
  /** List of review comments */
  comments: ReviewComment[];
  /** Approval recommendation */
  approvalRecommendation?: ApprovalRecommendation;
  /** Currently selected category filter */
  selectedCategory?: ReviewCategory | null;
  /** Called when category filter changes */
  onCategoryChange?: (category: ReviewCategory | null) => void;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Severity Configuration
// ============================================================================

interface SeverityConfig {
  icon: React.ElementType;
  label: string;
  color: string;
  bgColor: string;
}

const severityConfig: Record<ReviewSeverity, SeverityConfig> = {
  critical: {
    icon: AlertCircle,
    label: 'Critical',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
  warning: {
    icon: AlertTriangle,
    label: 'Warning',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
  },
  suggestion: {
    icon: Lightbulb,
    label: 'Suggestion',
    color: 'text-blue-600 dark:text-blue-400',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
  },
  info: {
    icon: Info,
    label: 'Info',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted',
  },
};

// ============================================================================
// Approval Configuration
// ============================================================================

interface ApprovalConfig {
  icon: React.ElementType;
  label: string;
  badgeClass: string;
}

const approvalConfig: Record<ApprovalRecommendation, ApprovalConfig> = {
  approve: {
    icon: CheckCircle2,
    label: 'Approve',
    badgeClass:
      'bg-green-100 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800',
  },
  request_changes: {
    icon: XCircle,
    label: 'Request Changes',
    badgeClass:
      'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  },
  comment: {
    icon: MessageSquare,
    label: 'Comment',
    badgeClass: 'bg-muted text-muted-foreground border-border',
  },
};

// ============================================================================
// Category Configuration
// ============================================================================

const categoryLabels: Record<ReviewCategory, string> = {
  architecture: 'Architecture',
  security: 'Security',
  quality: 'Quality',
  performance: 'Performance',
  documentation: 'Documentation',
};

// ============================================================================
// Component
// ============================================================================

export function ReviewSummary({
  summary,
  comments,
  approvalRecommendation,
  selectedCategory,
  onCategoryChange,
  className,
}: ReviewSummaryProps) {
  // Calculate counts by severity
  const severityCounts = React.useMemo(() => {
    const counts: Record<ReviewSeverity, number> = {
      critical: 0,
      warning: 0,
      suggestion: 0,
      info: 0,
    };
    comments.forEach((comment) => {
      counts[comment.severity]++;
    });
    return counts;
  }, [comments]);

  // Calculate counts by category
  const categoryCounts = React.useMemo(() => {
    const counts: Record<ReviewCategory, number> = {
      architecture: 0,
      security: 0,
      quality: 0,
      performance: 0,
      documentation: 0,
    };
    comments.forEach((comment) => {
      counts[comment.category]++;
    });
    return counts;
  }, [comments]);

  const approval = approvalRecommendation ? approvalConfig[approvalRecommendation] : null;
  const ApprovalIcon = approval?.icon;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Approval recommendation */}
      {approval && ApprovalIcon && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Recommendation:</span>
          <Badge variant="outline" className={cn('gap-1.5', approval.badgeClass)}>
            <ApprovalIcon className="size-3.5" />
            {approval.label}
          </Badge>
        </div>
      )}

      {/* Summary text */}
      <p className="text-sm text-muted-foreground">{summary}</p>

      {/* Severity counts */}
      <div className="flex flex-wrap gap-3">
        {(Object.keys(severityCounts) as ReviewSeverity[]).map((severity) => {
          const config = severityConfig[severity];
          const count = severityCounts[severity];
          if (count === 0) return null;

          const Icon = config.icon;
          return (
            <div
              key={severity}
              className={cn('flex items-center gap-1.5 rounded-md px-2 py-1', config.bgColor)}
            >
              <Icon className={cn('size-4', config.color)} />
              <span className={cn('text-sm font-medium', config.color)}>
                {count} {config.label}
                {count !== 1 ? 's' : ''}
              </span>
            </div>
          );
        })}
      </div>

      {/* Category filters */}
      {onCategoryChange && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onCategoryChange(null)}
            className={cn(
              'rounded-md px-2 py-1 text-xs font-medium transition-colors',
              selectedCategory === null
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
          >
            All ({comments.length})
          </button>
          {(Object.keys(categoryCounts) as ReviewCategory[]).map((category) => {
            const count = categoryCounts[category];
            if (count === 0) return null;

            return (
              <button
                key={category}
                type="button"
                onClick={() => onCategoryChange(category)}
                className={cn(
                  'rounded-md px-2 py-1 text-xs font-medium transition-colors',
                  selectedCategory === category
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {categoryLabels[category]} ({count})
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ReviewSummary;
