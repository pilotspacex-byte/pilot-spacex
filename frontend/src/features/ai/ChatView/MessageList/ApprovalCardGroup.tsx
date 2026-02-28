/**
 * ApprovalCardGroup - Batches 3+ inline approval cards into a collapsible group.
 * Provides "Approve All" / "Reject All" bulk actions to reduce interruptions.
 * Shown in place of individual InlineApprovalCards when inlineApprovals.length >= 3.
 */
'use client';

import { memo, useCallback, useId, useState } from 'react';
import { Check, ChevronDown, ChevronUp, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { InlineApprovalCard } from './InlineApprovalCard';
import type { ApprovalRequest } from '../types';

interface ApprovalCardGroupProps {
  approvals: ApprovalRequest[];
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
}

export const ApprovalCardGroup = memo<ApprovalCardGroupProps>(function ApprovalCardGroup({
  approvals,
  onApprove,
  onReject,
}) {
  const listId = useId();
  const [isExpanded, setIsExpanded] = useState(true);
  const [isBatchLoading, setIsBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState<string | null>(null);

  const handleApproveAll = useCallback(async () => {
    setBatchError(null);
    setIsBatchLoading(true);
    try {
      const results = await Promise.allSettled(approvals.map((a) => onApprove(a.id)));
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0)
        setBatchError(`${failed} approval${failed === 1 ? '' : 's'} failed to process`);
    } finally {
      setIsBatchLoading(false);
    }
  }, [approvals, onApprove]);

  const handleRejectAll = useCallback(async () => {
    setBatchError(null);
    setIsBatchLoading(true);
    try {
      const results = await Promise.allSettled(
        approvals.map((a) => onReject(a.id, 'Batch rejected'))
      );
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (failed > 0)
        setBatchError(`${failed} rejection${failed === 1 ? '' : 's'} failed to process`);
    } finally {
      setIsBatchLoading(false);
    }
  }, [approvals, onReject]);

  return (
    <div
      className={cn(
        'mx-4 my-3 rounded-[12px] border-[1.5px] border-ai/30',
        'bg-[var(--color-ai-bg)] shadow-[0_2px_8px_rgba(0,0,0,0.06)] animate-fade-up'
      )}
      role="region"
      aria-label={`${approvals.length} pending approvals`}
    >
      {/* Group header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ai/10">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium text-ai hover:text-ai/80 transition-colors"
          aria-expanded={isExpanded}
          aria-controls={listId}
        >
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4" aria-hidden="true" />
          )}
          {approvals.length} Pending Approvals
        </button>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleRejectAll}
            disabled={isBatchLoading}
            className="gap-1.5 text-xs"
            aria-label="Reject all approvals"
          >
            {isBatchLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              <X className="h-3 w-3" aria-hidden="true" />
            )}
            Reject All
          </Button>
          <Button
            size="sm"
            onClick={handleApproveAll}
            disabled={isBatchLoading}
            className="gap-1.5 text-xs"
            aria-label="Approve all approvals"
          >
            {isBatchLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              <Check className="h-3 w-3" aria-hidden="true" />
            )}
            Approve All
          </Button>
        </div>
      </div>

      {/* Batch error feedback */}
      {batchError && (
        <div className="px-4 py-2 border-b border-ai/10">
          <p role="alert" className="text-xs text-destructive">
            {batchError}
          </p>
        </div>
      )}

      {/* Cards list */}
      {isExpanded && (
        <div id={listId} className="max-h-[50vh] overflow-y-auto">
          {approvals.map((approval, index) => (
            <InlineApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={onApprove}
              onReject={onReject}
              className={cn(
                'mx-0 my-0 rounded-none border-0 shadow-none animate-none',
                index < approvals.length - 1 && 'border-b border-ai/10'
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
});
