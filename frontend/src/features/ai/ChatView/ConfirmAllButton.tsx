/**
 * ConfirmAllButton — floating action above ChatInput for batch intent confirmation.
 *
 * Only shown when >= 2 eligible intents (confidence >= 70%) are pending.
 * Calls confirmAll API (max 10) and shows result summary.
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §5
 * T-059
 */
'use client';

import { useCallback, useState } from 'react';
import { CheckCheck, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { aiApi } from '@/services/api/ai';
import { toast } from 'sonner';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import { observer } from 'mobx-react-lite';

interface ConfirmAllButtonProps {
  store: PilotSpaceStore;
  className?: string;
}

interface ConfirmResult {
  confirmedCount: number;
  remainingCount: number;
  deduplicatingCount: number;
}

export const ConfirmAllButton = observer<ConfirmAllButtonProps>(function ConfirmAllButton({
  store,
  className,
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConfirmResult | null>(null);

  const eligibleCount = store.eligibleIntentCount;

  const handleConfirmAll = useCallback(async () => {
    if (!store.workspaceId || isLoading) return;
    setIsLoading(true);
    setResult(null);
    try {
      const response = await aiApi.confirmAllIntents(store.workspaceId, 0.7, 10);
      setResult({
        confirmedCount: response.confirmedCount,
        remainingCount: response.remainingCount,
        deduplicatingCount: response.deduplicatingCount,
      });
      // Update local intent states to confirmed
      for (const confirmed of response.confirmed) {
        store.updateIntentStatus(confirmed.id, 'confirmed');
      }
    } catch (err) {
      toast.error('Failed to confirm intents', {
        description: err instanceof Error ? err.message : 'Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  }, [store, isLoading]);

  const handleDismissResult = useCallback(() => {
    setResult(null);
  }, []);

  // Hidden when < 2 eligible intents
  if (eligibleCount < 2 && !result) return null;

  if (result) {
    return (
      <div
        className={cn(
          'mx-4 mb-2 rounded-[12px] border bg-primary/5 border-primary/20 px-4 py-2.5',
          'flex items-center justify-between gap-3 animate-fade-up',
          className
        )}
        aria-live="polite"
        role="status"
      >
        <div className="flex items-center gap-2 min-w-0">
          <CheckCheck className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
          <span className="text-sm font-medium text-primary">
            {result.confirmedCount} confirmed
          </span>
          {result.remainingCount > 0 && (
            <span className="text-sm text-muted-foreground">
              · {result.remainingCount} remaining
            </span>
          )}
          {result.deduplicatingCount > 0 && (
            <span className="text-xs text-muted-foreground">
              ({result.deduplicatingCount} deduplicating)
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleDismissResult}
          className="p-2 -m-2 text-muted-foreground hover:text-foreground shrink-0"
          aria-label="Dismiss confirmation result"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
    );
  }

  const moreInfo =
    eligibleCount > 10 ? ` (${eligibleCount} eligible — top 10 will be confirmed)` : '';

  return (
    <div className={cn('mx-4 mb-2', className)}>
      <Button
        variant="default"
        size="sm"
        className={cn('w-full gap-2', 'justify-center text-sm')}
        onClick={handleConfirmAll}
        disabled={isLoading}
        aria-label={`Confirm all ${eligibleCount} eligible intents`}
        aria-busy={isLoading}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <CheckCheck className="h-4 w-4" aria-hidden="true" />
        )}
        Confirm All ({eligibleCount}){moreInfo}
      </Button>
    </div>
  );
});
