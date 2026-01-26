'use client';

/**
 * Approval Detail Modal - Full details and resolution for approval requests.
 *
 * T191: Shows full payload preview, risk assessment, and approve/reject actions.
 * Provides confirmation before executing actions.
 *
 * @example
 * ```tsx
 * <ApprovalDetailModal
 *   request={request}
 *   open={true}
 *   onOpenChange={setOpen}
 *   onApprove={handleApprove}
 *   onReject={handleReject}
 * />
 * ```
 */

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Check, X, AlertTriangle, Sparkles, User, Clock, Copy } from 'lucide-react';
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
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import type { ApprovalRequest } from '@/services/api/ai';

// ============================================================================
// Types
// ============================================================================

export interface ApprovalDetailModalProps {
  request: ApprovalRequest;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApprove: (note?: string) => Promise<void>;
  onReject: (note?: string) => Promise<void>;
}

// ============================================================================
// Payload Preview Component
// ============================================================================

interface PayloadPreviewProps {
  payload?: Record<string, unknown>;
}

function PayloadPreview({ payload }: PayloadPreviewProps) {
  const [copied, setCopied] = useState(false);

  if (!payload || Object.keys(payload).length === 0) {
    return <div className="text-sm text-muted-foreground italic">No payload data available</div>;
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>Action Payload</Label>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs" onClick={handleCopy}>
          <Copy className="size-3" />
          {copied ? 'Copied!' : 'Copy'}
        </Button>
      </div>
      <pre className="bg-muted p-3 rounded-md text-xs overflow-auto max-h-60 font-mono">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}

// ============================================================================
// Risk Assessment Component
// ============================================================================

interface RiskAssessmentProps {
  actionType: string;
}

function RiskAssessment({ actionType }: RiskAssessmentProps) {
  // Classify risk based on action type per DD-003
  const riskLevels = {
    delete_workspace: {
      level: 'critical',
      description: 'Permanent deletion of workspace and all data',
    },
    delete_project: {
      level: 'critical',
      description: 'Permanent deletion of project and all issues',
    },
    delete_issue: { level: 'high', description: 'Permanent deletion of issue and related data' },
    delete_note: { level: 'high', description: 'Permanent deletion of note' },
    merge_pr: { level: 'high', description: 'Merges pull request into main branch' },
    bulk_delete: { level: 'critical', description: 'Deletes multiple items at once' },
    create_sub_issues: { level: 'medium', description: 'Creates new sub-issues from parent' },
    extract_issues: { level: 'medium', description: 'Extracts and creates issues from note' },
    publish_docs: { level: 'low', description: 'Publishes documentation' },
    post_pr_comments: { level: 'low', description: 'Posts comments on pull request' },
  };

  const risk = riskLevels[actionType as keyof typeof riskLevels] || {
    level: 'medium',
    description: 'Action requires approval',
  };

  const riskColors = {
    critical: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
    high: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
    medium: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
    low: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
  };

  return (
    <Alert className={cn('border', riskColors[risk.level as keyof typeof riskColors])}>
      <AlertTriangle className="size-4" />
      <AlertDescription>
        <p className="font-semibold mb-1">
          Risk Level: {risk.level.charAt(0).toUpperCase() + risk.level.slice(1)}
        </p>
        <p className="text-sm">{risk.description}</p>
      </AlertDescription>
    </Alert>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ApprovalDetailModal({
  request,
  open,
  onOpenChange,
  onApprove,
  onReject,
}: ApprovalDetailModalProps) {
  const [note, setNote] = useState('');
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const isPending = request.status === 'pending';
  const createdAt = new Date(request.created_at);
  const expiresAt = new Date(request.expires_at);
  const isExpired = expiresAt < new Date();

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await onApprove(note || undefined);
      setNote('');
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject(note || undefined);
      setNote('');
    } finally {
      setIsRejecting(false);
    }
  };

  const formatActionType = (actionType: string) => {
    return actionType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Approval Request
            <Badge
              variant={isPending ? 'default' : 'secondary'}
              className={cn(isPending && 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400')}
            >
              {request.status}
            </Badge>
          </DialogTitle>
          <DialogDescription>{request.context_preview}</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Agent</Label>
              <div className="flex items-center gap-1.5">
                <Sparkles className="size-4 text-muted-foreground" />
                <span className="text-sm font-medium">{request.agent_name}</span>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Action Type</Label>
              <Badge variant="outline" className="font-mono text-xs">
                {formatActionType(request.action_type)}
              </Badge>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Requested By</Label>
              <div className="flex items-center gap-1.5">
                <User className="size-4 text-muted-foreground" />
                <span className="text-sm">{request.requested_by}</span>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Created</Label>
              <div className="flex items-center gap-1.5">
                <Clock className="size-4 text-muted-foreground" />
                <span className="text-sm">
                  {formatDistanceToNow(createdAt, { addSuffix: true })}
                </span>
              </div>
            </div>
          </div>

          <Separator />

          {/* Risk Assessment */}
          <RiskAssessment actionType={request.action_type} />

          {/* Expiration Warning */}
          {isPending && isExpired && (
            <Alert variant="destructive">
              <AlertTriangle className="size-4" />
              <AlertDescription>
                This approval request has expired and can no longer be approved.
              </AlertDescription>
            </Alert>
          )}

          {/* Payload Preview */}
          <PayloadPreview payload={request.payload} />

          {/* Resolution Note */}
          {isPending && !isExpired && (
            <div className="space-y-2">
              <Label htmlFor="note">Resolution Note (Optional)</Label>
              <Textarea
                id="note"
                placeholder="Add a note explaining your decision..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                maxLength={1000}
              />
              <p className="text-xs text-muted-foreground">{note.length}/1000 characters</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {isPending && !isExpired && (
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={handleReject}
              disabled={isApproving || isRejecting}
              className="gap-1.5"
            >
              <X className="size-4" />
              Reject
            </Button>
            <Button
              onClick={handleApprove}
              disabled={isApproving || isRejecting}
              className="gap-1.5"
            >
              {isApproving ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current" />
              ) : (
                <Check className="size-4" />
              )}
              Approve & Execute
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
