/**
 * SkillApprovalCard — inline approval card for destructive/suggest skill output.
 *
 * Extends InlineApprovalCard pattern for skill-specific approval workflow.
 * Renders TipTap-like read-only preview + countdown + Approve/Reject.
 *
 * Spec: specs/015-ai-workforce-platform/ui-design.md §3
 * T-054, T-058, T-061
 */
'use client';

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { ShieldAlert, Check, X, Loader2, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

interface SkillApprovalCardProps {
  intent: WorkIntentState;
  /** ISO timestamp when approval expires (24h) */
  expiresAt: Date;
  /** Approval action label (e.g., "Generate database migration") */
  actionLabel: string;
  onApprove: (intentId: string, approvalId: string) => Promise<void>;
  onReject: (intentId: string, approvalId: string, reason?: string) => Promise<void>;
  className?: string;
}

type CardState = 'idle' | 'rejecting' | 'loading' | 'approved' | 'rejected' | 'expired';

/** Live countdown timer. Returns formatted string and whether < 1 minute. */
/** Minute-scale thresholds per ApprovalCard spec (GAP-01 fix):
 *  >5min  → muted, MM:SS format
 *  1-5min → amber (nearExpiry), MM:SS format
 *  <1min  → red pulse (urgent), MM:SS format
 */
function useCountdown(expiresAt: Date): {
  display: string;
  urgent: boolean;
  nearExpiry: boolean;
  expired: boolean;
} {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const remaining = expiresAt.getTime() - now;
  if (remaining <= 0)
    return { display: 'Expired', urgent: false, nearExpiry: false, expired: true };

  const hours = Math.floor(remaining / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  const seconds = Math.floor((remaining % 60_000) / 1_000);

  const urgent = remaining < 60_000; // < 1 minute: red
  const nearExpiry = remaining < 300_000; // < 5 minutes: amber

  let display: string;
  if (hours > 0) {
    display = `${hours}h ${String(minutes).padStart(2, '0')}m`;
  } else {
    // For 0–59 minutes always show MM:SS (minute-scale, matching spec)
    display = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  return { display, urgent, nearExpiry, expired: false };
}

const MAX_REASON = 500;

export const SkillApprovalCard = memo<SkillApprovalCardProps>(function SkillApprovalCard({
  intent,
  expiresAt,
  actionLabel,
  onApprove,
  onReject,
  className,
}) {
  const { display, urgent, nearExpiry, expired } = useCountdown(expiresAt);
  const [terminalState, setTerminalState] = useState<
    'approved' | 'rejected' | 'loading' | 'rejecting' | null
  >(null);
  const [reason, setReason] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Derive cardState — expired is computed from countdown, not stored
  const cardState: CardState = terminalState ?? (expired ? 'expired' : 'idle');

  const handleApprove = useCallback(async () => {
    if (!intent.approvalId || cardState !== 'idle') return;
    setTerminalState('loading');
    try {
      await onApprove(intent.intentId, intent.approvalId);
      setTerminalState('approved');
    } catch {
      setTerminalState(null);
    }
  }, [intent.intentId, intent.approvalId, cardState, onApprove]);

  const handleStartReject = useCallback(() => {
    setTerminalState('rejecting');
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleCancelReject = useCallback(() => {
    setTerminalState(null);
    setReason('');
  }, []);

  const handleConfirmReject = useCallback(async () => {
    if (!intent.approvalId) return;
    setTerminalState('loading');
    try {
      await onReject(intent.intentId, intent.approvalId, reason.trim() || undefined);
      setTerminalState('rejected');
    } catch {
      setTerminalState('rejecting');
    }
  }, [intent.intentId, intent.approvalId, reason, onReject]);

  const onKeyDown = useCallback(
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
  if (cardState === 'approved') {
    return (
      <div
        role="region"
        aria-label={`Approval approved: ${actionLabel}`}
        className={cn(
          'mx-4 my-2 flex items-center gap-2 px-4 py-2.5 rounded-[14px]',
          'border border-primary/30 bg-primary/5 animate-fade-up',
          className
        )}
      >
        <Check className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-primary">Approved</span>
      </div>
    );
  }

  // Collapsed: rejected
  if (cardState === 'rejected') {
    return (
      <div
        role="region"
        aria-label={`Approval rejected: ${actionLabel}`}
        className={cn(
          'mx-4 my-2 flex items-center gap-2 px-4 py-2.5 rounded-[14px]',
          'border border-destructive/30 bg-destructive/5 animate-fade-up',
          className
        )}
      >
        <X className="h-4 w-4 text-destructive shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-destructive">Rejected</span>
      </div>
    );
  }

  const isActing = cardState === 'loading';
  const isRejecting = cardState === 'rejecting';
  const isExpired = cardState === 'expired';

  // Minute-scale color thresholds per spec (GAP-01):
  // >5min → muted, 1-5min → amber, <1min → red
  const countdownColor =
    urgent || expired ? 'text-[#D9534F]' : nearExpiry ? 'text-[#D9853F]' : 'text-muted-foreground';

  return (
    <div
      role="alertdialog"
      aria-label={`Approval required: ${actionLabel}`}
      className={cn(
        'mx-4 my-3 rounded-[18px] border-2 bg-background p-4 shadow',
        urgent ? 'animate-pulse border-[#D9534F]' : 'border-[#D9853F]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-[18px] w-[18px] text-[#D9853F] shrink-0" aria-hidden="true" />
          <span className="text-sm font-semibold text-foreground">Approval Required</span>
        </div>
        <span
          className={cn('text-xs tabular-nums font-medium', countdownColor)}
          aria-live={urgent ? 'assertive' : 'off'}
          aria-label={`Time remaining: ${display}`}
        >
          {display}
        </span>
      </div>

      {/* Action info */}
      <div className="mb-3 space-y-0.5">
        <p className="text-sm font-medium text-foreground">{actionLabel}</p>
        {intent.skillName && (
          <p className="text-xs font-mono text-muted-foreground">{intent.skillName}</p>
        )}
      </div>

      {/* Skill output preview (read-only) */}
      {intent.artifacts && intent.artifacts.length > 0 && (
        <div className="mb-4 rounded-[10px] border bg-muted/40 p-3 max-h-[200px] overflow-y-auto">
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <span className="text-xs font-medium text-muted-foreground">Preview</span>
          </div>
          <ul className="space-y-1">
            {intent.artifacts.map((a) => (
              <li key={a.id} className="text-xs font-mono text-foreground">
                {a.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Rejection textarea */}
      {isRejecting && (
        <div className="mb-3 space-y-2">
          <Textarea
            ref={textareaRef}
            value={reason}
            onChange={(e) => setReason(e.target.value.slice(0, MAX_REASON))}
            onKeyDown={onKeyDown}
            placeholder="Reason for rejection (optional)…"
            rows={3}
            className="resize-none text-sm"
            aria-label="Reason for rejection"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              {reason.length}/{MAX_REASON}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={handleCancelReject} className="text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleConfirmReject}
                disabled={isActing}
                className="text-xs gap-1.5"
              >
                {isActing && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
                Reject
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Action buttons */}
      {!isRejecting && (
        <div className="flex items-center justify-between mt-4">
          <Button
            size="sm"
            variant="outline"
            onClick={handleStartReject}
            disabled={isActing || isExpired}
            className="text-xs gap-1.5"
          >
            <X className="h-3 w-3" aria-hidden="true" />
            Reject
          </Button>
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isActing || isExpired}
            aria-busy={isActing}
            className="text-xs gap-1.5"
          >
            {isActing ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : (
              <Check className="h-3 w-3" aria-hidden="true" />
            )}
            {isExpired ? 'Expired' : 'Approve'}
          </Button>
        </div>
      )}
    </div>
  );
});
