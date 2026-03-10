'use client';

/**
 * PR Review Panel - Main container for AI-powered PR review.
 *
 * T143: Displays Request Review button, streaming progress, and
 * 5 collapsible aspect cards when complete. Supports re-review.
 *
 * @example
 * ```tsx
 * <PRReviewPanel repoId={repo.id} prNumber={123} />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { Sparkles, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PRReviewStreaming } from './pr-review-streaming';
import { ReviewAspectCard } from './review-aspect-card';
import { PRReviewCostBadge } from './pr-review-cost-badge';
import { useStores } from '@/stores';

// ============================================================================
// Types
// ============================================================================

export interface PRReviewPanelProps {
  /** Repository UUID */
  repoId: string;
  /** Pull request number */
  prNumber: number;
  /** Additional class name */
  className?: string;
  /**
   * Whether workspace BYOK is configured (AIGOV-05).
   * When false, Request Review / Re-review buttons are disabled.
   * Defaults to true (enabled) when not provided, for backward compatibility.
   */
  byokConfigured?: boolean;
}

// ============================================================================
// Main Component
// ============================================================================

export const PRReviewPanel = observer(function PRReviewPanel({
  repoId,
  prNumber,
  className,
  byokConfigured = true,
}: PRReviewPanelProps) {
  const rootStore = useStores();
  const prReviewStore = rootStore.ai.prReview;

  const { isLoading, error, result, tokenUsage, aspects, isComplete } = prReviewStore;

  // Request review
  const handleRequestReview = React.useCallback(async () => {
    await prReviewStore.requestReview(repoId, prNumber);
  }, [prReviewStore, repoId, prNumber]);

  // Re-review (clears cache)
  const handleReReview = React.useCallback(async () => {
    await prReviewStore.reReview(repoId, prNumber);
  }, [prReviewStore, repoId, prNumber]);

  return (
    <Card className={cn('w-full', className)} data-testid="pr-review-panel">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-5 text-primary" />
              AI PR Review
            </CardTitle>
            <CardDescription>Unified review covering 5 aspects</CardDescription>
          </div>

          <div className="flex items-center gap-2">
            {tokenUsage && <PRReviewCostBadge tokenUsage={tokenUsage} />}

            {/* Re-review button (only show when result exists) */}
            {result && !isLoading && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleReReview}
                disabled={isLoading || !byokConfigured}
                title={
                  !byokConfigured
                    ? 'AI not available — configure an API key in Settings'
                    : undefined
                }
                className="gap-1.5"
              >
                <RefreshCw className="size-4" />
                Re-review
              </Button>
            )}

            {/* Request Review button (only show when no result and not loading) */}
            {!result && !isLoading && (
              <Button
                onClick={handleRequestReview}
                disabled={isLoading || !byokConfigured}
                title={
                  !byokConfigured
                    ? 'AI not available — configure an API key in Settings'
                    : undefined
                }
                className="gap-1.5"
              >
                <Sparkles className="size-4" />
                Request Review
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Error State */}
        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
            <AlertCircle className="size-5 text-destructive shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-destructive">Review Failed</p>
              <p className="text-sm text-destructive/80">{error}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRequestReview}
                className="mt-2 gap-1.5"
              >
                <RefreshCw className="size-4" />
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Loading State - Show streaming progress */}
        {isLoading && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span>Analyzing PR...</span>
            </div>
            <PRReviewStreaming aspects={aspects} />
          </div>
        )}

        {/* Complete State - Show 5 aspect cards */}
        {isComplete && result && (
          <div className="space-y-4" data-testid="review-result">
            {/* Summary */}
            <div className="rounded-lg bg-muted/50 p-4" data-testid="review-summary">
              <p className="text-sm text-muted-foreground">{result.summary}</p>
            </div>

            {/* Aspect Cards */}
            <div className="space-y-3">
              <ReviewAspectCard
                aspectName="architecture"
                findings={result.architecture}
                defaultOpen
              />
              <ReviewAspectCard aspectName="security" findings={result.security} defaultOpen />
              <ReviewAspectCard aspectName="quality" findings={result.quality} />
              <ReviewAspectCard aspectName="performance" findings={result.performance} />
              <ReviewAspectCard aspectName="documentation" findings={result.documentation} />
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !result && !error && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Sparkles className="size-12 text-muted-foreground/50 mb-4" />
            <p className="text-muted-foreground mb-4">No review has been run for this PR yet.</p>
            <Button
              onClick={handleRequestReview}
              disabled={!byokConfigured}
              title={
                !byokConfigured ? 'AI not available — configure an API key in Settings' : undefined
              }
              className="gap-1.5"
            >
              <Sparkles className="size-4" />
              Request AI Review
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default PRReviewPanel;
