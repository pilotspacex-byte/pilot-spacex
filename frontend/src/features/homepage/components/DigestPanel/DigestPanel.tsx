'use client';

/**
 * DigestPanel (H046) — AI Digest Panel (Zone 3) coordinator.
 * Checks AI provider status, manages loading/empty states, renders suggestion list.
 * Provides a refresh button to trigger on-demand digest regeneration.
 */

import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { queryKeys } from '@/lib/queryClient';
import { useWorkspaceStore } from '@/stores/RootStore';
import { useWorkspaceDigest } from '../../hooks/useWorkspaceDigest';
import { useDigestDismiss } from '../../hooks/useDigestDismiss';
import { homepageApi } from '../../api/homepage-api';
import type { DigestSuggestion, DismissSuggestionPayload } from '../../types';
import { DigestSuggestionCard } from './DigestSuggestionCard';
import { DigestEmptyState } from './DigestEmptyState';
import { DigestSkeleton } from './DigestSkeleton';

interface DigestPanelProps {
  /** Whether an AI provider is configured in workspace settings */
  aiConfigured?: boolean;
}

export const DigestPanel = observer(function DigestPanel({
  aiConfigured = true,
}: DigestPanelProps) {
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  const {
    data: digest,
    isLoading,
    isRefetching,
  } = useWorkspaceDigest({
    workspaceId,
    enabled: aiConfigured && !!workspaceId,
  });

  const queryClient = useQueryClient();
  const dismissMutation = useDigestDismiss({ workspaceId });

  const handleDismiss = useCallback(
    (suggestion: DigestSuggestion) => {
      const payload: DismissSuggestionPayload = {
        suggestion_id: suggestion.id,
        category: suggestion.category,
        entity_id: suggestion.entity_id,
        entity_type: suggestion.entity_type,
      };
      dismissMutation.mutate(payload);
    },
    [dismissMutation]
  );

  const handleRefresh = useCallback(async () => {
    if (!workspaceId) return;
    await homepageApi.refreshDigest(workspaceId);
    // Invalidate after a short delay to allow background job to start
    setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.homepage.digest(workspaceId) });
    }, 2000);
  }, [workspaceId, queryClient]);

  // No AI provider configured
  if (!aiConfigured) {
    return (
      <div className="rounded-lg border border-border-subtle bg-card">
        <div className="border-b border-border-subtle px-4 py-3">
          <h2 className="text-lg font-semibold text-foreground">AI Insights</h2>
        </div>
        <DigestEmptyState variant="no-provider" />
      </div>
    );
  }

  const suggestions = digest?.data.suggestions ?? [];
  const generatedAt = digest?.data.generated_at;

  // Format relative time for "Last updated"
  const lastUpdatedLabel = generatedAt ? formatRelativeTime(generatedAt) : null;

  return (
    <div className="rounded-lg border border-border-subtle bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">AI Insights</h2>
          {lastUpdatedLabel && (
            <p className="text-xs text-muted-foreground">Last updated {lastUpdatedLabel}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefetching}
          aria-label="Refresh AI digest"
          className="h-8 gap-1.5 text-xs"
        >
          <RefreshCw
            className={cn('h-3.5 w-3.5', isRefetching && 'animate-spin')}
            aria-hidden="true"
          />
          Refresh
        </Button>
      </div>

      {/* Content */}
      <div className="p-3">
        {isLoading ? (
          <DigestSkeleton />
        ) : suggestions.length === 0 ? (
          <DigestEmptyState variant="no-suggestions" />
        ) : (
          <div className="space-y-2" role="list" aria-label="AI suggestions">
            {suggestions.map((suggestion) => (
              <DigestSuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                onDismiss={handleDismiss}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

/** Formats an ISO timestamp to a relative string like "5 min ago" */
function formatRelativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;

  if (diffMs < 60_000) return 'just now';

  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 60) return `${diffMin} min ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}
