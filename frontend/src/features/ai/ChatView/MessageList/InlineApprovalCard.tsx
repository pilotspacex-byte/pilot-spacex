/**
 * InlineApprovalCard - Inline approval card for non-destructive AI suggestions.
 * Renders within the chat message stream. Replaces SuggestionCard.
 * Per DD-003: non-destructive suggestions appear inline, destructive actions
 * still use ApprovalOverlay modal.
 */
'use client';

import { memo, useCallback, useRef, useState } from 'react';
import { Check, Loader2, Sparkles, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { IssuePreview } from '../ApprovalOverlay/IssuePreview';
import { ContentDiff } from '../ApprovalOverlay/ContentDiff';
import { GenericJSON } from '../ApprovalOverlay/GenericJSON';
import type { ApprovalRequest } from '../types';

type CardState = 'idle' | 'rejecting' | 'loading' | 'approved' | 'rejected';
const MAX_REASON_LEN = 200;

interface InlineApprovalCardProps {
  approval: ApprovalRequest;
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
  className?: string;
}

function PayloadPreview({
  actionType,
  payload,
}: {
  actionType: string;
  payload?: Record<string, unknown>;
}) {
  if (!payload) return null;
  if (actionType.includes('issue') && payload.issue)
    return (
      <IssuePreview issue={payload.issue as Record<string, unknown>} className="border-ai/20" />
    );
  if (
    actionType.includes('update') &&
    typeof payload.before === 'string' &&
    typeof payload.after === 'string'
  )
    return <ContentDiff before={payload.before} after={payload.after} className="max-h-[200px]" />;
  return <GenericJSON payload={payload} className="max-h-[200px]" />;
}

const collapsedCn = 'mx-4 my-2 flex items-center gap-2 rounded-[12px] px-4 py-2.5 animate-fade-up';

export const InlineApprovalCard = memo<InlineApprovalCardProps>(function InlineApprovalCard({
  approval,
  onApprove,
  onReject,
  className,
}) {
  const [state, setState] = useState<CardState>(
    approval.status === 'approved'
      ? 'approved'
      : approval.status === 'rejected'
        ? 'rejected'
        : 'idle'
  );
  const [reason, setReason] = useState('');
  const [savedReason, setSavedReason] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const regionLabel = `AI suggestion: ${approval.actionType}`;

  const handleApprove = useCallback(async () => {
    setState('loading');
    try {
      await onApprove(approval.id);
      setState('approved');
    } catch {
      setState('idle');
    }
  }, [approval.id, onApprove]);

  const handleStartReject = useCallback(() => {
    setState('rejecting');
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleCancelReject = useCallback(() => {
    setState('idle');
    setReason('');
  }, []);

  const handleConfirmReject = useCallback(async () => {
    const r = reason.trim() || 'Rejected';
    setState('loading');
    try {
      await onReject(approval.id, r);
      setSavedReason(r);
      setState('rejected');
    } catch {
      setState('rejecting');
    }
  }, [approval.id, onReject, reason]);

  const onRejectKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancelReject();
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleConfirmReject();
      }
    },
    [handleCancelReject, handleConfirmReject]
  );

  // Collapsed: approved
  if (state === 'approved') {
    return (
      <div
        data-testid="inline-approval-card"
        role="region"
        aria-label={regionLabel}
        className={cn(collapsedCn, 'border border-primary/30 bg-primary/5', className)}
      >
        <Check className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-primary">Approved</span>
      </div>
    );
  }

  // Collapsed: rejected
  if (state === 'rejected') {
    return (
      <div
        data-testid="inline-approval-card"
        role="region"
        aria-label={regionLabel}
        className={cn(collapsedCn, 'border border-destructive/30 bg-destructive/5', className)}
      >
        <X className="h-4 w-4 text-destructive shrink-0" aria-hidden="true" />
        <span className="text-sm text-destructive truncate">
          <span className="font-medium">Rejected</span>
          {savedReason && savedReason !== 'Rejected' && (
            <span className="font-normal">: {savedReason}</span>
          )}
        </span>
      </div>
    );
  }

  const isLoading = state === 'loading';
  const isRejecting = state === 'rejecting';
  const hasPayload = approval.payload && Object.keys(approval.payload).length > 0;

  return (
    <div
      data-testid="inline-approval-card"
      role="region"
      aria-label={regionLabel}
      className={cn(
        'mx-4 my-3 rounded-[12px] p-4 border-[1.5px] border-ai/30',
        'bg-[var(--color-ai-bg)] shadow-[0_2px_8px_rgba(0,0,0,0.06)] animate-fade-up',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-ai" aria-hidden="true" />
        <Badge variant="secondary" className="bg-ai/10 text-ai border-0 text-xs font-medium">
          AI Suggestion
        </Badge>
      </div>

      {/* Context */}
      <p className="text-sm text-foreground leading-relaxed mb-3">
        {approval.contextPreview || approval.reasoning || 'AI suggestion'}
      </p>

      {/* Payload preview */}
      {hasPayload && (
        <div className="mb-3">
          <PayloadPreview actionType={approval.actionType} payload={approval.payload} />
        </div>
      )}

      {/* Rejection input */}
      {isRejecting && (
        <div className="mb-3 space-y-2">
          <Textarea
            ref={textareaRef}
            value={reason}
            onChange={(e) => setReason(e.target.value.slice(0, MAX_REASON_LEN))}
            onKeyDown={onRejectKeyDown}
            placeholder="Reason for rejection (optional)..."
            maxLength={MAX_REASON_LEN}
            rows={2}
            className="resize-none text-sm"
            aria-label="Rejection reason"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {reason.length}/{MAX_REASON_LEN}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={handleCancelReject} className="text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleConfirmReject}
                className="text-xs"
              >
                Confirm Reject
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {!isRejecting && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isLoading}
            aria-busy={isLoading}
            aria-label="Approve suggestion"
            data-testid="approval-approve"
            className="gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleStartReject}
            disabled={isLoading}
            aria-label="Reject suggestion"
            data-testid="approval-reject"
            className="gap-1.5"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Reject
          </Button>
        </div>
      )}
    </div>
  );
});
