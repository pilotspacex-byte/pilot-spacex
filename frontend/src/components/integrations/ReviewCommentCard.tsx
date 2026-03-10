'use client';

/**
 * ReviewCommentCard - Individual PR review comment display.
 *
 * T200: Shows a single review comment with severity badge, category, message,
 * and optional code suggestion.
 */

import * as React from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Lightbulb,
  Code,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

// ============================================================================
// Types
// ============================================================================

export type ReviewSeverity = 'critical' | 'warning' | 'suggestion' | 'info';

export type ReviewCategory =
  | 'architecture'
  | 'security'
  | 'quality'
  | 'performance'
  | 'documentation';

export interface ReviewComment {
  /** File path where the comment applies */
  filePath: string;
  /** Line number in the file */
  lineNumber: number;
  /** Severity of the issue */
  severity: ReviewSeverity;
  /** Category of the review */
  category: ReviewCategory;
  /** The review message */
  message: string;
  /** Optional code suggestion */
  suggestion?: string;
  /** AI reasoning for this comment (AIGOV-07). Present when backend includes audit rationale. */
  ai_rationale?: string;
}

export interface ReviewCommentCardProps {
  /** The review comment to display */
  comment: ReviewComment;
  /** Whether to show the file path */
  showFilePath?: boolean;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Configuration
// ============================================================================

interface SeverityConfig {
  icon: React.ElementType;
  label: string;
  badgeClass: string;
  borderClass: string;
}

const severityConfig: Record<ReviewSeverity, SeverityConfig> = {
  critical: {
    icon: AlertCircle,
    label: 'Critical',
    badgeClass:
      'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
    borderClass: 'border-l-red-500',
  },
  warning: {
    icon: AlertTriangle,
    label: 'Warning',
    badgeClass:
      'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800',
    borderClass: 'border-l-yellow-500',
  },
  suggestion: {
    icon: Lightbulb,
    label: 'Suggestion',
    badgeClass:
      'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
    borderClass: 'border-l-blue-500',
  },
  info: {
    icon: Info,
    label: 'Info',
    badgeClass:
      'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700',
    borderClass: 'border-l-gray-400',
  },
};

interface CategoryConfig {
  label: string;
  color: string;
}

const categoryConfig: Record<ReviewCategory, CategoryConfig> = {
  architecture: { label: 'Architecture', color: 'text-purple-600 dark:text-purple-400' },
  security: { label: 'Security', color: 'text-red-600 dark:text-red-400' },
  quality: { label: 'Quality', color: 'text-blue-600 dark:text-blue-400' },
  performance: { label: 'Performance', color: 'text-orange-600 dark:text-orange-400' },
  documentation: { label: 'Documentation', color: 'text-green-600 dark:text-green-400' },
};

// ============================================================================
// Component
// ============================================================================

export function ReviewCommentCard({
  comment,
  showFilePath = true,
  className,
}: ReviewCommentCardProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [isRationaleOpen, setIsRationaleOpen] = React.useState(false);
  const severity = severityConfig[comment.severity];
  const category = categoryConfig[comment.category];
  const SeverityIcon = severity.icon;

  return (
    <div
      className={cn(
        'rounded-lg border bg-card border-l-4 transition-colors',
        severity.borderClass,
        className
      )}
    >
      <div className="p-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className={cn('gap-1', severity.badgeClass)}>
              <SeverityIcon className="size-3" />
              {severity.label}
            </Badge>
            <span className={cn('text-xs font-medium', category.color)}>{category.label}</span>
          </div>
          <div className="text-xs text-muted-foreground shrink-0">L{comment.lineNumber}</div>
        </div>

        {/* File path */}
        {showFilePath && (
          <p className="text-xs text-muted-foreground font-mono mb-2 truncate">
            {comment.filePath}
          </p>
        )}

        {/* Message */}
        <p className="text-sm">{comment.message}</p>

        {/* Suggestion (collapsible) */}
        {comment.suggestion && (
          <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-3">
            <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
              {isOpen ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
              <Code className="size-3" />
              View suggestion
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <pre className="bg-muted rounded-md p-3 text-xs overflow-x-auto font-mono">
                <code>{comment.suggestion}</code>
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* AI Reasoning (collapsible — AIGOV-07). Conditionally rendered when backend provides rationale. */}
        {comment.ai_rationale && (
          <Collapsible open={isRationaleOpen} onOpenChange={setIsRationaleOpen} className="mt-2">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {isRationaleOpen ? (
                  <ChevronDown className="size-3" />
                ) : (
                  <ChevronRight className="size-3" />
                )}
                AI reasoning
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <p className="text-xs text-muted-foreground p-2 bg-muted/50 rounded mt-1">
                {comment.ai_rationale}
              </p>
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

export default ReviewCommentCard;
