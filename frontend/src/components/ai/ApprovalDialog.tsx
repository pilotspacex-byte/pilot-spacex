'use client';

import * as React from 'react';
import { AlertTriangle, CheckCircle2, XCircle, Clock, Shield, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CountdownTimer } from './CountdownTimer';
import type { PendingApproval, ApprovalUrgency } from '@/types';

export interface ApprovalDialogProps {
  /** The pending approval to display */
  approval: PendingApproval;
  /** Called when user approves the action */
  onApprove: () => Promise<void>;
  /** Called when user rejects the action */
  onReject: () => Promise<void>;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Called when dialog open state changes */
  onOpenChange?: (open: boolean) => void;
  /** Optional note/reason input for rejection */
  showReasonInput?: boolean;
}

const APPROVAL_EXPIRY_DURATION = 24 * 60 * 60 * 1000; // 24 hours in ms

function getUrgencyIcon(urgency: ApprovalUrgency) {
  switch (urgency) {
    case 'critical':
      return <AlertTriangle className="size-5 text-destructive" />;
    case 'high':
      return <AlertTriangle className="size-5 text-amber-500" />;
    case 'medium':
      return <Shield className="size-5 text-blue-500" />;
    case 'low':
    default:
      return <Clock className="size-5 text-muted-foreground" />;
  }
}

function getUrgencyLabel(urgency: ApprovalUrgency): string {
  switch (urgency) {
    case 'critical':
      return 'Critical Action';
    case 'high':
      return 'High Impact';
    case 'medium':
      return 'Moderate Impact';
    case 'low':
    default:
      return 'Low Impact';
  }
}

function getUrgencyAlertVariant(urgency: ApprovalUrgency): 'warning' | 'destructive' | 'info' {
  switch (urgency) {
    case 'critical':
      return 'destructive';
    case 'high':
      return 'warning';
    default:
      return 'info';
  }
}

function getActionTypeLabel(actionType: string): string {
  switch (actionType) {
    case 'issue_delete_bulk':
      return 'Bulk Delete Issues';
    case 'issue_merge_duplicate':
      return 'Merge Duplicate Issues';
    case 'ai_bulk_update':
      return 'AI Bulk Update';
    case 'ai_create_sub_issues':
      return 'Create Sub-Issues';
    case 'ai_archive_issues':
      return 'Archive Issues';
    case 'cycle_delete':
      return 'Delete Cycle';
    case 'module_delete':
      return 'Delete Module';
    default:
      return actionType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/**
 * ApprovalDialog displays a pending AI action requiring human confirmation.
 *
 * Features per DD-003 (Critical-only approval model):
 * - Shows action details and consequences
 * - Approve/Reject buttons with loading states
 * - 24h expiry countdown timer
 * - Keyboard accessible (Enter=approve, Escape=reject)
 * - Screen reader accessible with ARIA labels
 *
 * @example
 * ```tsx
 * <ApprovalDialog
 *   approval={pendingApproval}
 *   isOpen={isOpen}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 * />
 * ```
 */
export function ApprovalDialog({
  approval,
  onApprove,
  onReject,
  isOpen,
  onOpenChange,
  showReasonInput = false,
}: ApprovalDialogProps) {
  const [isApproving, setIsApproving] = React.useState(false);
  const [isRejecting, setIsRejecting] = React.useState(false);
  const [hasExpired, setHasExpired] = React.useState(false);
  const [rejectReason, setRejectReason] = React.useState('');

  const approveButtonRef = React.useRef<HTMLButtonElement>(null);

  // Check if already expired
  React.useEffect(() => {
    const expiryTime = new Date(approval.expiresAt).getTime();
    setHasExpired(Date.now() >= expiryTime);
  }, [approval.expiresAt]);

  // Memoized handlers to prevent useEffect re-runs
  const handleApprove = React.useCallback(async () => {
    if (isApproving || isRejecting || hasExpired) return;

    setIsApproving(true);
    try {
      await onApprove();
    } finally {
      setIsApproving(false);
    }
  }, [isApproving, isRejecting, hasExpired, onApprove]);

  const handleReject = React.useCallback(async () => {
    if (isApproving || isRejecting || hasExpired) return;

    setIsRejecting(true);
    try {
      await onReject();
    } finally {
      setIsRejecting(false);
    }
  }, [isApproving, isRejecting, hasExpired, onReject]);

  // Keyboard shortcuts
  React.useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle if loading or expired
      if (isApproving || isRejecting || hasExpired) return;

      // Don't handle if focus is in an input
      const activeElement = document.activeElement;
      if (activeElement?.tagName === 'INPUT' || activeElement?.tagName === 'TEXTAREA') {
        return;
      }

      if (event.key === 'Enter') {
        event.preventDefault();
        handleApprove();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        handleReject();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isApproving, isRejecting, hasExpired, handleApprove, handleReject]);

  // Focus approve button when dialog opens
  React.useEffect(() => {
    if (isOpen && approveButtonRef.current) {
      // Small delay to allow dialog animation
      const timer = setTimeout(() => {
        approveButtonRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleExpire = () => {
    setHasExpired(true);
  };

  const isLoading = isApproving || isRejecting;
  const affectedCount = approval.affectedEntityIds.length;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md"
        aria-describedby="approval-description"
        onInteractOutside={(e) => {
          // Prevent closing while loading
          if (isLoading) {
            e.preventDefault();
          }
        }}
        onEscapeKeyDown={(e) => {
          // Handle escape via our keyboard handler
          e.preventDefault();
        }}
      >
        <DialogHeader>
          <div className="flex items-center gap-2">
            {getUrgencyIcon(approval.urgency)}
            <DialogTitle>Approve AI Action</DialogTitle>
          </div>
          <DialogDescription>
            {getUrgencyLabel(approval.urgency)} - {getActionTypeLabel(approval.actionType)}
          </DialogDescription>
        </DialogHeader>

        <div id="approval-description" className="space-y-4">
          {/* Action description */}
          <div className="space-y-2">
            <p className="text-sm">
              <span className="text-muted-foreground">The AI wants to:</span>{' '}
              <strong className="text-foreground">{approval.actionDescription}</strong>
            </p>
            <p className="text-sm text-muted-foreground">
              Affecting {affectedCount} {approval.affectedEntityType}
              {affectedCount !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Consequences warning */}
          <Alert variant={getUrgencyAlertVariant(approval.urgency)}>
            <AlertTriangle className="size-4" />
            <AlertTitle>Consequences</AlertTitle>
            <AlertDescription>{approval.consequences}</AlertDescription>
          </Alert>

          {/* Expiry countdown */}
          {hasExpired ? (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <XCircle className="size-4" />
              <span>This approval has expired and can no longer be approved.</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="size-4" />
              <span>
                Expires in:{' '}
                <CountdownTimer
                  endTime={approval.expiresAt}
                  onExpire={handleExpire}
                  compact
                  showProgress
                  totalDuration={APPROVAL_EXPIRY_DURATION}
                />
              </span>
            </div>
          )}

          {/* Rejection reason input */}
          {showReasonInput && (
            <div className="space-y-2">
              <label htmlFor="reject-reason" className="text-sm font-medium">
                Reason (optional)
              </label>
              <textarea
                id="reject-reason"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Why are you rejecting this action?"
                rows={2}
                className={cn(
                  'flex w-full rounded-md border border-input bg-background px-3 py-2',
                  'text-sm placeholder:text-muted-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                  'resize-none'
                )}
                disabled={isLoading}
              />
            </div>
          )}

          {/* Keyboard hints */}
          <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
            <span>
              Press <kbd className="rounded border bg-muted px-1">Enter</kbd> to approve
            </span>
            <span>
              Press <kbd className="rounded border bg-muted px-1">Esc</kbd> to reject
            </span>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleReject}
            disabled={isLoading || hasExpired}
            aria-label="Reject this action"
          >
            {isRejecting ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Rejecting...
              </>
            ) : (
              <>
                <XCircle className="mr-2 size-4" />
                Reject
              </>
            )}
          </Button>
          <Button
            ref={approveButtonRef}
            onClick={handleApprove}
            disabled={isLoading || hasExpired}
            aria-label="Approve this action"
          >
            {isApproving ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Approving...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 size-4" />
                Approve
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
