'use client';

import * as React from 'react';
import { AlertTriangle, ExternalLink, X, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { AIConfidenceTag } from '@/components/ai/AIConfidenceTag';

export interface DuplicateCandidate {
  issueId: string;
  identifier: string;
  title: string;
  similarity: number;
  explanation: string | null;
}

export interface DuplicateWarningProps {
  /** Potential duplicate candidates */
  candidates: DuplicateCandidate[];
  /** Whether a likely duplicate was found (>85% similarity) */
  hasLikelyDuplicate: boolean;
  /** Highest similarity score */
  highestSimilarity: number;
  /** Called when user views a duplicate */
  onViewDuplicate?: (candidate: DuplicateCandidate) => void;
  /** Called when user dismisses the warning */
  onDismiss?: () => void;
  /** Called when user confirms to proceed despite duplicates */
  onProceed?: () => void;
  className?: string;
}

/**
 * DuplicateWarning shows potential duplicate issues.
 * Displays AI-detected similar issues with similarity scores.
 *
 * @example
 * ```tsx
 * <DuplicateWarning
 *   candidates={duplicates}
 *   hasLikelyDuplicate={true}
 *   highestSimilarity={0.92}
 *   onViewDuplicate={(c) => openIssue(c.issueId)}
 *   onDismiss={() => clearWarning()}
 * />
 * ```
 */
export function DuplicateWarning({
  candidates,
  hasLikelyDuplicate,
  highestSimilarity,
  onViewDuplicate,
  onDismiss,
  onProceed,
  className,
}: DuplicateWarningProps) {
  const [isExpanded, setIsExpanded] = React.useState(true);
  const [showAll, setShowAll] = React.useState(false);

  if (candidates.length === 0) {
    return null;
  }

  const displayedCandidates = showAll ? candidates : candidates.slice(0, 3);
  const hasMore = candidates.length > 3;

  const severityClass = hasLikelyDuplicate
    ? 'border-amber-500/50 bg-amber-500/10'
    : 'border-yellow-500/30 bg-yellow-500/5';

  const iconClass = hasLikelyDuplicate ? 'text-amber-500' : 'text-yellow-500';

  return (
    <div
      className={cn('rounded-lg border p-3 transition-colors', severityClass, className)}
      role="alert"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <AlertTriangle className={cn('size-5 shrink-0 mt-0.5', iconClass)} />
          <div>
            <h4 className="text-sm font-medium">
              {hasLikelyDuplicate ? 'Potential duplicate detected' : 'Similar issues found'}
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5">
              {candidates.length === 1
                ? '1 similar issue found'
                : `${candidates.length} similar issues found`}
              {' (highest: '}
              <span className="font-medium">{Math.round(highestSimilarity * 100)}%</span>
              {' similarity)'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-muted-foreground"
          >
            {isExpanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </Button>
          {onDismiss && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onDismiss}
              className="text-muted-foreground"
            >
              <X className="size-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Candidates list */}
      {isExpanded && (
        <div className="mt-3 space-y-2">
          {displayedCandidates.map((candidate) => (
            <div
              key={candidate.issueId}
              className="flex items-start justify-between gap-2 rounded-md border bg-background/50 p-2"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-muted-foreground shrink-0">
                    {candidate.identifier}
                  </span>
                  <AIConfidenceTag
                    confidence={candidate.similarity}
                    showIcon
                    className="shrink-0"
                  />
                </div>
                <p className="text-sm font-medium truncate mt-0.5">{candidate.title}</p>
                {candidate.explanation && (
                  <p className="text-xs text-muted-foreground mt-0.5">{candidate.explanation}</p>
                )}
              </div>
              {onViewDuplicate && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => onViewDuplicate(candidate)}
                  className="shrink-0"
                >
                  <ExternalLink className="size-4" />
                </Button>
              )}
            </div>
          ))}

          {/* Show more/less */}
          {hasMore && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAll(!showAll)}
              className="w-full text-xs"
            >
              {showAll ? 'Show less' : `Show ${candidates.length - 3} more`}
            </Button>
          )}

          {/* Action buttons */}
          {hasLikelyDuplicate && onProceed && (
            <div className="flex items-center justify-end gap-2 pt-2 border-t">
              <span className="text-xs text-muted-foreground">
                Still want to create this issue?
              </span>
              <Button variant="outline" size="sm" onClick={onProceed}>
                Proceed anyway
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DuplicateWarning;
