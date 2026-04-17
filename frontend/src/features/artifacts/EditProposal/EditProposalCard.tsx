'use client';

/**
 * EditProposalCard — unified approval / edit-proposal presentation component.
 *
 * Design spec: .planning/design.md v3 §Edit Proposal Card
 *
 * Consolidates the four historical approval surfaces into a single card:
 *   - `InlineApprovalCard`      (chat-stream, per-message)
 *   - `ApprovalCardGroup`       (batched, 3+ pending)
 *   - `SkillApprovalCard`       (skill-side, destructive/suggest)
 *   - `approval-row`            (approvals page table row)
 *
 * Each of those wrappers now delegates to EditProposalCard for the visual
 * shell, keeping their existing call sites intact (they still own the
 * MobX/TanStack data contracts). The new component owns:
 *
 *   - Header:  action-type badge + countdown + severity icon
 *   - Body:    reasoning / preview; optional Before/After diff via ContentDiff
 *   - Actions: Approve / Reject / optional Modify
 *   - Footer:  "Nothing saved until accepted · DD-003"
 *
 * Per DD-003: destructive actions delegate to `DestructiveApprovalModal`
 * (imported by the wrappers, not this card) — the inline form renders only
 * non-destructive proposals.
 *
 * NOT observer(). Consumers pass plain props.
 */

import * as React from 'react';
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  FileSearch,
  Link as LinkIcon,
  Loader2,
  Pencil,
  PlusCircle,
  Sparkles,
  Tag,
  Wand2,
  X,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { ContentDiff } from '@/features/ai/ChatView/ApprovalOverlay/ContentDiff';
import { GenericJSON } from '@/features/ai/ChatView/ApprovalOverlay/GenericJSON';
import { IssuePreview } from '@/features/ai/ChatView/ApprovalOverlay/IssuePreview';
import { IssueUpdatePreview } from '@/features/ai/ChatView/ApprovalOverlay/IssueUpdatePreview';
import { formatActionType, isDestructiveAction } from '@/features/ai/ChatView/utils';

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Normalized proposal model. Both chat-side `ApprovalRequest` and
 * approvals-page `PendingApproval` map cleanly to this shape; callers pass
 * one of those raw objects as `approval` and we normalise via an adapter.
 */
export interface NormalizedProposal {
  id: string;
  actionType: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  headline?: string;
  reasoning?: string;
  consequences?: string;
  /** Optional before/after for diff rendering. */
  before?: string;
  after?: string;
  /** Raw payload preview — routed to IssuePreview / ContentDiff / GenericJSON. */
  payload?: Record<string, unknown>;
  /** ISO string — when present, drives the countdown badge. */
  expiresAt?: string;
  /** Optional explicit agent label. */
  agentName?: string;
}

export type EditProposalVariant = 'inline' | 'row';

export interface EditProposalCardProps {
  /** Normalized proposal. Callers adapt ApprovalRequest / PendingApproval. */
  proposal: NormalizedProposal;
  /** Mark destructive regardless of actionType — defaults to heuristic. */
  isDestructive?: boolean;
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void> | void;
  onReject: (id: string, reason: string) => Promise<void> | void;
  /** Optional "Modify" button (e.g. opens richer editor). */
  onModify?: (id: string) => void;
  /** Visual variant — inline for chat stream, row for the approvals page. */
  variant?: EditProposalVariant;
  className?: string;
}

// ---------------------------------------------------------------------------
// Icon / label lookup
// ---------------------------------------------------------------------------

interface ActionBadge {
  icon: LucideIcon;
  label: string;
}

function actionBadgeFor(actionType: string): ActionBadge {
  switch (actionType) {
    case 'create_issue':
      return { icon: PlusCircle, label: 'Create Issue' };
    case 'update_issue':
    case 'enhance_issue':
      return { icon: Pencil, label: formatActionType(actionType) };
    case 'add_label':
      return { icon: Tag, label: 'Add Label' };
    case 'link_issue':
      return { icon: LinkIcon, label: 'Link Issue' };
    case 'extract_issues':
      return { icon: FileSearch, label: 'Extract Issues' };
    case 'improve_writing':
    case 'summarize':
    case 'decompose_tasks':
      return { icon: Wand2, label: formatActionType(actionType) };
    default:
      return { icon: Sparkles, label: formatActionType(actionType) };
  }
}

// ---------------------------------------------------------------------------
// Countdown — pure hook, no external deps
// ---------------------------------------------------------------------------

const URGENT_SECONDS = 30;

function useCountdown(expiresAt: string | undefined, active: boolean) {
  const [remaining, setRemaining] = React.useState(() => {
    if (!expiresAt) return null;
    return Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
  });

  React.useEffect(() => {
    if (!expiresAt || !active) return;
    const expiryMs = new Date(expiresAt).getTime();
    const id = window.setInterval(() => {
      const r = Math.max(0, Math.floor((expiryMs - Date.now()) / 1000));
      setRemaining(r);
      if (r <= 0) window.clearInterval(id);
    }, 1000);
    return () => window.clearInterval(id);
  }, [expiresAt, active]);

  if (remaining === null) return null;
  const urgent = remaining > 0 && remaining <= URGENT_SECONDS;
  const expired = remaining <= 0;
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return {
    remaining,
    urgent,
    expired,
    display: `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`,
  };
}

// ---------------------------------------------------------------------------
// Payload preview — routes to the right renderer (same logic as before)
// ---------------------------------------------------------------------------

const PayloadPreview = React.memo(function PayloadPreview({
  proposal,
}: {
  proposal: NormalizedProposal;
}) {
  if (proposal.before !== undefined && proposal.after !== undefined) {
    return (
      <ContentDiff before={proposal.before} after={proposal.after} className="max-h-[220px]" />
    );
  }
  const payload = proposal.payload;
  if (!payload) return null;
  if (proposal.actionType === 'update_issue') return <IssueUpdatePreview payload={payload} />;
  if (proposal.actionType.includes('issue') && payload.issue) {
    return <IssuePreview issue={payload.issue as Record<string, unknown>} />;
  }
  if (
    proposal.actionType.includes('update') &&
    typeof payload.before === 'string' &&
    typeof payload.after === 'string'
  ) {
    return (
      <ContentDiff
        before={payload.before}
        after={payload.after}
        className="max-h-[220px]"
      />
    );
  }
  return <GenericJSON payload={payload} className="max-h-[220px]" />;
});

// ---------------------------------------------------------------------------
// Collapsed (terminal) states
// ---------------------------------------------------------------------------

function CollapsedTerminal({
  state,
  label,
  className,
}: {
  state: 'approved' | 'rejected' | 'expired';
  label: string;
  className?: string;
}) {
  const palette =
    state === 'approved'
      ? 'border-primary/30 bg-primary/5 text-primary'
      : state === 'rejected'
        ? 'border-destructive/30 bg-destructive/5 text-destructive'
        : 'border-muted-foreground/30 bg-muted/30 text-muted-foreground';
  const Icon = state === 'approved' ? Check : state === 'rejected' ? X : Clock;
  return (
    <div
      role="status"
      className={cn(
        'flex items-center gap-2 rounded-[14px] border px-4 py-2.5 text-sm font-medium',
        palette,
        className
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="truncate">{label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const MAX_REASON = 200;

export const EditProposalCard = React.memo(function EditProposalCard({
  proposal,
  onApprove,
  onReject,
  onModify,
  isDestructive: isDestructiveProp,
  variant = 'inline',
  className,
}: EditProposalCardProps) {
  const [cardState, setCardState] = React.useState<
    'idle' | 'rejecting' | 'loading' | 'approved' | 'rejected' | 'expired'
  >(() =>
    proposal.status === 'approved'
      ? 'approved'
      : proposal.status === 'rejected'
        ? 'rejected'
        : proposal.status === 'expired'
          ? 'expired'
          : 'idle'
  );
  const [reason, setReason] = React.useState('');
  const [savedReason, setSavedReason] = React.useState('');
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const countdown = useCountdown(proposal.expiresAt, cardState === 'idle' || cardState === 'rejecting');

  // Auto-expire when the countdown hits zero.
  React.useEffect(() => {
    if (countdown?.expired && cardState === 'idle') setCardState('expired');
  }, [countdown?.expired, cardState]);

  const destructive = isDestructiveProp ?? isDestructiveAction(proposal.actionType);

  const handleApprove = React.useCallback(async () => {
    setErrorMessage(null);
    setCardState('loading');
    try {
      await onApprove(proposal.id);
      setCardState('approved');
    } catch (err) {
      setCardState('idle');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to approve.');
    }
  }, [onApprove, proposal.id]);

  const handleStartReject = React.useCallback(() => {
    setCardState('rejecting');
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  const handleCancelReject = React.useCallback(() => {
    setCardState('idle');
    setReason('');
  }, []);

  const handleConfirmReject = React.useCallback(async () => {
    const trimmed = reason.trim() || 'Rejected';
    setErrorMessage(null);
    setCardState('loading');
    try {
      await onReject(proposal.id, trimmed);
      setSavedReason(trimmed);
      setCardState('rejected');
    } catch (err) {
      setCardState('rejecting');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to reject.');
    }
  }, [onReject, proposal.id, reason]);

  const onRejectKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancelReject();
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void handleConfirmReject();
      }
    },
    [handleCancelReject, handleConfirmReject]
  );

  // Collapsed terminal states take precedence over everything.
  if (cardState === 'approved') {
    return (
      <CollapsedTerminal
        state="approved"
        label={`Approved: ${formatActionType(proposal.actionType)}`}
        className={className}
      />
    );
  }
  if (cardState === 'rejected') {
    const base = `Rejected: ${formatActionType(proposal.actionType)}`;
    const label = savedReason && savedReason !== 'Rejected' ? `${base} — ${savedReason}` : base;
    return <CollapsedTerminal state="rejected" label={label} className={className} />;
  }
  if (cardState === 'expired') {
    return (
      <CollapsedTerminal state="expired" label="Approval expired" className={className} />
    );
  }

  const isLoading = cardState === 'loading';
  const isRejecting = cardState === 'rejecting';
  const { icon: ActionIcon, label: actionLabel } = actionBadgeFor(proposal.actionType);
  const SeverityIcon = destructive ? AlertTriangle : Sparkles;
  const severityTone = destructive ? 'text-destructive' : 'text-ai';
  const variantPadding = variant === 'row' ? 'p-3 md:p-4' : 'p-4';
  const variantRadius = variant === 'row' ? 'rounded-[14px]' : 'rounded-[18px]';

  return (
    <div
      data-testid="edit-proposal-card"
      role="region"
      aria-label={`AI proposal: ${actionLabel}`}
      className={cn(
        'flex flex-col gap-3 border bg-card text-card-foreground animate-fade-up',
        destructive ? 'border-destructive/40 bg-destructive/5' : 'border-ai/30 bg-[var(--color-ai-bg)]',
        'shadow-[var(--shadow-l1)]',
        variantRadius,
        variantPadding,
        className
      )}
    >
      {/* Header */}
      <header className="flex items-center gap-2">
        <SeverityIcon className={cn('h-4 w-4 shrink-0', severityTone)} aria-hidden="true" />
        <ActionIcon className={cn('h-4 w-4 shrink-0', severityTone)} aria-hidden="true" />
        <Badge
          variant="secondary"
          className={cn(
            'text-xs font-medium border-0',
            destructive ? 'bg-destructive/10 text-destructive' : 'bg-ai/10 text-ai'
          )}
        >
          {actionLabel}
        </Badge>
        {proposal.agentName ? (
          <span className="text-xs text-muted-foreground truncate">{proposal.agentName}</span>
        ) : null}
        {countdown ? (
          <Badge
            variant="outline"
            data-testid="edit-proposal-countdown"
            aria-live={countdown.urgent ? 'assertive' : 'off'}
            className={cn(
              'ml-auto gap-1.5 tabular-nums text-xs transition-colors duration-300 shrink-0',
              countdown.urgent
                ? 'border-destructive/50 text-destructive animate-pulse'
                : 'border-muted-foreground/30 text-muted-foreground'
            )}
          >
            <Clock className="h-3 w-3" aria-hidden="true" />
            <span>{countdown.display}</span>
          </Badge>
        ) : null}
      </header>

      {/* Body */}
      {proposal.headline ? (
        <p className="text-sm font-medium text-foreground leading-snug">{proposal.headline}</p>
      ) : null}
      {proposal.reasoning ? (
        <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">
          {proposal.reasoning}
        </p>
      ) : null}
      {proposal.consequences ? (
        <p className="text-xs text-muted-foreground italic">{proposal.consequences}</p>
      ) : null}

      {/* Diff / payload slot */}
      {proposal.before !== undefined || proposal.after !== undefined || proposal.payload ? (
        <details className="group" open={variant === 'row'}>
          <summary className="text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground">
            <span className="group-open:hidden">Show preview</span>
            <span className="hidden group-open:inline">Hide preview</span>
          </summary>
          <div className="mt-2">
            <PayloadPreview proposal={proposal} />
          </div>
        </details>
      ) : null}

      {/* Reject form */}
      {isRejecting ? (
        <div className="space-y-2 pt-1">
          <Textarea
            ref={textareaRef}
            value={reason}
            onChange={(e) => setReason(e.target.value.slice(0, MAX_REASON))}
            onKeyDown={onRejectKeyDown}
            placeholder="Reason for rejection (optional)…"
            maxLength={MAX_REASON}
            rows={2}
            className="resize-none text-sm"
            aria-label="Rejection reason"
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
                className="text-xs gap-1.5"
              >
                <XCircle className="h-3 w-3" aria-hidden="true" />
                Confirm reject
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isLoading}
            aria-busy={isLoading}
            aria-label="Approve proposal"
            data-testid="edit-proposal-approve"
            className="gap-1.5"
          >
            {isLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleStartReject}
            disabled={isLoading}
            aria-label="Reject proposal"
            data-testid="edit-proposal-reject"
            className="gap-1.5"
          >
            <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
            Reject
          </Button>
          {onModify ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onModify(proposal.id)}
              disabled={isLoading}
              className="gap-1.5 text-xs"
              data-testid="edit-proposal-modify"
            >
              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
              Modify
            </Button>
          ) : null}
        </div>
      )}

      {errorMessage ? (
        <p role="alert" className="text-xs text-destructive">
          {errorMessage}
        </p>
      ) : null}

      {/* Footer — DD-003 reassurance */}
      <p className="text-[11px] text-muted-foreground/80 border-t border-border/50 pt-2">
        Nothing saved until accepted · DD-003
      </p>
    </div>
  );
});

EditProposalCard.displayName = 'EditProposalCard';
