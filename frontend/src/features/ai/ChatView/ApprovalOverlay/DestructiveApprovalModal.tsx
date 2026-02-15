/**
 * DestructiveApprovalModal - Blocking modal for destructive AI action approvals (DD-003)
 *
 * Handles: delete_issue, merge_pr, close_issue, archive_workspace,
 *          delete_note, delete_comment, unlink_issue_from_note, unlink_issues
 *
 * Escape key triggers Reject flow (per spec FR-12). No outside click dismiss.
 * 5-minute auto-cancel timer. Initial focus on Reject button for safety-first UX.
 */

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { AlertTriangle, Clock, CheckCircle2, XCircle } from 'lucide-react';
import type { ApprovalRequest } from '../types';
import { IssuePreview } from './IssuePreview';
import { ContentDiff } from './ContentDiff';
import { GenericJSON } from './GenericJSON';
import { cn } from '@/lib/utils';

const URGENT_THRESHOLD_SECONDS = 60;

type ModalState = 'default' | 'rejecting' | 'approving';

interface DestructiveApprovalModalProps {
  approval: ApprovalRequest | null;
  isOpen: boolean;
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
  onClose: () => void;
}

function formatActionType(actionType: string): string {
  return actionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export const DestructiveApprovalModal = memo<DestructiveApprovalModalProps>(
  ({ approval, isOpen, onApprove, onReject, onClose }) => {
    // Key-based reset: inner component re-mounts when approval.id changes,
    // resetting all state without needing refs during render.
    if (!approval) return null;

    return (
      <DestructiveApprovalModalInner
        key={approval.id}
        approval={approval}
        isOpen={isOpen}
        onApprove={onApprove}
        onReject={onReject}
        onClose={onClose}
      />
    );
  }
);

DestructiveApprovalModal.displayName = 'DestructiveApprovalModal';

/**
 * Inner component that resets all state via key-based remount when approval changes.
 */
const DestructiveApprovalModalInner = memo<
  Omit<DestructiveApprovalModalProps, 'approval'> & { approval: ApprovalRequest }
>(({ approval, isOpen, onApprove, onReject, onClose }) => {
  const [modalState, setModalState] = useState<ModalState>('default');
  const [rejectionReason, setRejectionReason] = useState('');
  const [timeRemaining, setTimeRemaining] = useState(() =>
    Math.max(0, Math.floor((approval.expiresAt.getTime() - Date.now()) / 1000))
  );
  const rejectButtonRef = useRef<HTMLButtonElement>(null);
  const hasAutoRejected = useRef(false);

  // Countdown timer with auto-reject
  useEffect(() => {
    if (!isOpen) return;

    const computeRemaining = () =>
      Math.max(0, Math.floor((approval.expiresAt.getTime() - Date.now()) / 1000));

    const interval = setInterval(() => {
      const remaining = computeRemaining();
      setTimeRemaining(remaining);

      if (remaining <= 0 && !hasAutoRejected.current) {
        hasAutoRejected.current = true;
        clearInterval(interval);
        void onReject(approval.id, 'Auto-rejected: approval timed out');
        onClose();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [approval, isOpen, onReject, onClose]);

  // Focus reject button on mount (safety-first)
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(() => {
      rejectButtonRef.current?.focus();
    }, 50);

    return () => clearTimeout(timer);
  }, [isOpen]);

  const handleApprove = useCallback(async () => {
    if (!approval) return;

    setModalState('approving');
    try {
      await onApprove(approval.id);
      onClose();
    } catch (error) {
      console.error('Failed to approve destructive action:', error);
      setModalState('default');
    }
  }, [approval, onApprove, onClose]);

  const handleReject = useCallback(async () => {
    if (!approval) return;

    setModalState('approving'); // reuse loading state to disable all buttons
    try {
      await onReject(approval.id, rejectionReason || 'Rejected by user');
      onClose();
      setRejectionReason('');
      setModalState('default');
    } catch (error) {
      console.error('Failed to reject destructive action:', error);
      setModalState('default');
    }
  }, [approval, rejectionReason, onReject, onClose]);

  if (!approval) return null;

  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const isUrgent = timeRemaining < URGENT_THRESHOLD_SECONDS;
  const isBusy = modalState === 'approving';

  return (
    <Dialog open={isOpen} onOpenChange={() => {}}>
      <DialogContent
        role="alertdialog"
        aria-labelledby="destructive-approval-title"
        aria-describedby="destructive-approval-description"
        showCloseButton={false}
        onEscapeKeyDown={(e) => {
          e.preventDefault();
          if (!isBusy) {
            void handleReject();
          }
        }}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        className="max-w-2xl max-h-[80vh] overflow-y-auto gap-0 p-0"
      >
        {/* Red warning header */}
        <div className="rounded-t-lg border-b border-destructive/20 bg-destructive/10 px-6 py-4">
          <DialogHeader className="gap-0">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-destructive/15">
                  <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden="true" />
                </div>
                <div className="space-y-1">
                  <DialogTitle
                    id="destructive-approval-title"
                    className="text-base font-semibold text-destructive"
                  >
                    Destructive Action — Approval Required
                  </DialogTitle>
                  <DialogDescription
                    id="destructive-approval-description"
                    className="text-sm text-destructive/70"
                  >
                    This action cannot be undone.
                  </DialogDescription>
                </div>
              </div>

              <Badge
                variant="outline"
                className={cn(
                  'shrink-0 gap-1.5 tabular-nums transition-colors duration-300',
                  isUrgent
                    ? 'border-destructive/50 text-destructive animate-pulse'
                    : 'border-orange-500/50 text-orange-600 dark:text-orange-400'
                )}
                aria-live="polite"
                aria-label={`${minutes} minutes and ${seconds} seconds remaining`}
              >
                <Clock className="h-3 w-3" aria-hidden="true" />
                <span>
                  {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
                </span>
              </Badge>
            </div>
          </DialogHeader>
        </div>

        {/* Body content */}
        <div className="space-y-4 px-6 py-5">
          {/* Agent + action */}
          <div className="space-y-1">
            <p className="text-sm">
              <span className="font-semibold">{approval.agentName}</span>
              {' wants to '}
              <span className="font-semibold text-destructive">
                {formatActionType(approval.actionType)}
              </span>
            </p>
          </div>

          {/* Context preview */}
          <div className="space-y-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Action Summary
            </span>
            <p className="text-sm text-muted-foreground">{approval.contextPreview}</p>
          </div>

          {/* Reasoning */}
          {approval.reasoning && (
            <div className="space-y-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Reasoning
              </span>
              <p
                className="text-sm text-muted-foreground"
                data-testid="destructive-approval-reasoning"
              >
                {approval.reasoning}
              </p>
            </div>
          )}

          {/* Payload preview */}
          {approval.payload && (
            <div className="space-y-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Affected Items
              </span>
              <PayloadPreview actionType={approval.actionType} payload={approval.payload} />
            </div>
          )}

          {/* Rejection reason form */}
          {modalState === 'rejecting' && (
            <div className="space-y-1.5">
              <label
                htmlFor="rejection-reason"
                className="text-xs font-medium uppercase tracking-wide text-muted-foreground"
              >
                Rejection Reason
              </label>
              <Textarea
                id="rejection-reason"
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Why are you rejecting this action? (optional)"
                rows={3}
                aria-describedby="rejection-reason-hint"
              />
              <p id="rejection-reason-hint" className="text-xs text-muted-foreground">
                Provide context so the AI agent can adjust its approach.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="border-t px-6 py-4">
          {modalState === 'rejecting' ? (
            <>
              <Button
                variant="ghost"
                onClick={() => {
                  setModalState('default');
                  setRejectionReason('');
                }}
                disabled={isBusy}
              >
                Back
              </Button>
              <Button
                variant="outline"
                onClick={handleReject}
                disabled={isBusy}
                data-testid="confirm-reject-button"
              >
                {isBusy ? (
                  'Rejecting...'
                ) : (
                  <>
                    <XCircle className="mr-2 h-4 w-4" aria-hidden="true" />
                    Confirm Rejection
                  </>
                )}
              </Button>
            </>
          ) : (
            <>
              <Button
                ref={rejectButtonRef}
                variant="outline"
                onClick={() => setModalState('rejecting')}
                disabled={isBusy}
                data-testid="reject-button"
              >
                <XCircle className="mr-2 h-4 w-4" aria-hidden="true" />
                Reject
              </Button>
              <Button
                variant="destructive"
                onClick={handleApprove}
                disabled={isBusy}
                data-testid="approve-button"
                aria-describedby="approve-warning"
              >
                {isBusy ? (
                  'Approving...'
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
                    Approve
                  </>
                )}
              </Button>
              <span id="approve-warning" className="sr-only">
                Warning: This will permanently execute the destructive action.
              </span>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

DestructiveApprovalModalInner.displayName = 'DestructiveApprovalModalInner';

/**
 * PayloadPreview - Renders specialized preview based on action type.
 * Delegates to IssuePreview, ContentDiff, or GenericJSON.
 */
const PayloadPreview = memo<{
  actionType: string;
  payload: Record<string, unknown>;
}>(({ actionType, payload }) => {
  // Issue-related actions with issue data
  if (
    actionType.includes('issue') &&
    payload.issue !== undefined &&
    typeof payload.issue === 'object' &&
    payload.issue !== null
  ) {
    return <IssuePreview issue={payload.issue as Record<string, unknown>} />;
  }

  // Content update actions with before/after
  if (
    actionType.includes('update') &&
    typeof payload.before === 'string' &&
    typeof payload.after === 'string'
  ) {
    return <ContentDiff before={payload.before} after={payload.after} />;
  }

  // Fallback: generic JSON display
  return <GenericJSON payload={payload} />;
});

PayloadPreview.displayName = 'PayloadPreview';
