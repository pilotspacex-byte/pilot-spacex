/**
 * ApprovalDialog - Single approval request dialog
 * Follows shadcn/ui AI confirmation component pattern
 */

import { memo, useCallback, useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, XCircle, Clock, AlertTriangle } from 'lucide-react';
import type { ApprovalRequest } from '../types';
import { IssuePreview } from './IssuePreview';
import { ContentDiff } from './ContentDiff';
import { GenericJSON } from './GenericJSON';

interface ApprovalDialogProps {
  approval: ApprovalRequest | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (id: string, modifications?: Record<string, unknown>) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
}

export const ApprovalDialog = memo<ApprovalDialogProps>(
  ({ approval, isOpen, onClose, onApprove, onReject }) => {
    const [rejectionReason, setRejectionReason] = useState('');
    const [isApproving, setIsApproving] = useState(false);
    const [isRejecting, setIsRejecting] = useState(false);
    const [showRejectForm, setShowRejectForm] = useState(false);

    const handleApprove = useCallback(async () => {
      if (!approval) return;

      setIsApproving(true);
      try {
        await onApprove(approval.id);
        onClose();
      } catch (error) {
        console.error('Failed to approve:', error);
      } finally {
        setIsApproving(false);
      }
    }, [approval, onApprove, onClose]);

    const handleReject = useCallback(async () => {
      if (!approval) return;

      setIsRejecting(true);
      try {
        await onReject(approval.id, rejectionReason || 'Rejected by user');
        onClose();
        setRejectionReason('');
        setShowRejectForm(false);
      } catch (error) {
        console.error('Failed to reject:', error);
      } finally {
        setIsRejecting(false);
      }
    }, [approval, rejectionReason, onReject, onClose]);

    // Reactive countdown timer that ticks every second
    const [timeRemaining, setTimeRemaining] = useState(0);

    useEffect(() => {
      if (!approval) return;

      const computeRemaining = () =>
        Math.max(0, Math.floor((approval.expiresAt.getTime() - Date.now()) / 1000));

      setTimeRemaining(computeRemaining());

      const interval = setInterval(() => {
        setTimeRemaining(computeRemaining());
      }, 1000);

      return () => clearInterval(interval);
    }, [approval]);

    if (!approval) return null;

    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;

    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-2">
                <DialogTitle data-testid="approval-title">Approval Required</DialogTitle>
                <DialogDescription data-testid="approval-action">
                  {approval.actionType}
                </DialogDescription>
              </div>

              <Badge
                variant="outline"
                className="shrink-0 gap-1.5 border-orange-500/50 text-orange-600 dark:text-orange-400"
              >
                <Clock className="h-3 w-3" />
                <span>
                  {minutes}:{seconds.toString().padStart(2, '0')}
                </span>
              </Badge>
            </div>
          </DialogHeader>

          <div className="space-y-4">
            {/* Agent info */}
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <span className="font-medium">{approval.agentName}</span> is requesting permission
                to perform this action.
              </AlertDescription>
            </Alert>

            {/* Context preview */}
            <div className="space-y-2">
              <span className="text-sm font-medium">Action Summary</span>
              <p className="text-sm text-muted-foreground">{approval.contextPreview}</p>
            </div>

            {/* Reasoning */}
            {approval.reasoning && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Reasoning</span>
                <p className="text-sm text-muted-foreground" data-testid="approval-reasoning">
                  {approval.reasoning}
                </p>
              </div>
            )}

            {/* Payload preview */}
            {approval.payload && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Details</span>

                {/* Render specialized preview for known action types */}
                {approval.actionType.includes('issue') &&
                approval.payload.issue !== undefined &&
                typeof approval.payload.issue === 'object' &&
                approval.payload.issue !== null ? (
                  <IssuePreview issue={approval.payload.issue as Record<string, unknown>} />
                ) : null}

                {approval.actionType.includes('update') &&
                typeof approval.payload.before === 'string' &&
                typeof approval.payload.after === 'string' ? (
                  <ContentDiff before={approval.payload.before} after={approval.payload.after} />
                ) : null}

                {/* Fallback to generic JSON */}
                {!approval.actionType.includes('issue') &&
                !approval.actionType.includes('update') ? (
                  <GenericJSON payload={approval.payload} />
                ) : null}
              </div>
            )}

            {/* Rejection form */}
            {showRejectForm && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Rejection Reason</span>
                <Textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Why are you rejecting this action?"
                  rows={3}
                />
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            {showRejectForm ? (
              <>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setShowRejectForm(false);
                    setRejectionReason('');
                  }}
                  disabled={isRejecting}
                >
                  Cancel
                </Button>
                <Button variant="destructive" onClick={handleReject} disabled={isRejecting}>
                  {isRejecting ? (
                    'Rejecting...'
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 mr-2" />
                      Confirm Rejection
                    </>
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button
                  data-testid="reject-button"
                  variant="outline"
                  onClick={() => setShowRejectForm(true)}
                  disabled={isApproving || isRejecting}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Reject
                </Button>
                <Button
                  data-testid="approve-button"
                  onClick={handleApprove}
                  disabled={isApproving || isRejecting}
                >
                  {isApproving ? (
                    'Approving...'
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Approve
                    </>
                  )}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }
);

ApprovalDialog.displayName = 'ApprovalDialog';
