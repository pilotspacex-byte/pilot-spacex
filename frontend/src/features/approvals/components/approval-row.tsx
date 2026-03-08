/**
 * ApprovalRow — Expandable table row for a single AI approval request.
 *
 * Features:
 * - Collapsed: action type, description preview, agent name, time, action buttons
 * - Expanded: full metadata JSON payload + AI rationale text
 * - Approve button (green): calls resolve with action="approve"
 * - Reject button (destructive): opens dialog to capture optional reason
 *
 * Plain React component — NOT observer().
 */

'use client';

import * as React from 'react';
import { ChevronDown, ChevronRight, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { TableCell, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import type { PendingApproval } from '../hooks/use-approvals';
import type { useResolveApproval } from '../hooks/use-approvals';

// ---- Helpers ----

function formatRelativeTime(isoString: string): string {
  const ms = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function truncate(value: string, length: number): string {
  if (!value) return '—';
  return value.length > length ? value.slice(0, length) + '…' : value;
}

function urgencyVariant(
  urgency: PendingApproval['urgency']
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (urgency) {
    case 'critical':
      return 'destructive';
    case 'high':
      return 'default';
    case 'medium':
      return 'secondary';
    default:
      return 'outline';
  }
}

// ---- Reject Dialog ----

interface RejectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}

function RejectDialog({ open, onOpenChange, onConfirm, isPending }: RejectDialogProps) {
  const [reason, setReason] = React.useState('');

  const handleConfirm = () => {
    onConfirm(reason.trim());
    setReason('');
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setReason('');
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reject approval request</DialogTitle>
          <DialogDescription>
            Optionally provide a reason that will be recorded with the rejection.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="reject-reason" className="text-sm">
            Reason (optional)
          </Label>
          <Textarea
            id="reject-reason"
            placeholder="Explain why this action is being rejected…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="resize-none"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleConfirm} disabled={isPending}>
            {isPending ? 'Rejecting…' : 'Reject'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---- Expanded Content ----

function ExpandedContent({ approval }: { approval: PendingApproval }) {
  return (
    <div className="space-y-3 px-4 py-3 bg-muted/30 border-t">
      {/* Full description / context */}
      <div className="space-y-1">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Action Description
        </p>
        <p className="text-sm">{approval.actionDescription || '—'}</p>
      </div>

      {/* Metadata / payload */}
      {approval.metadata && Object.keys(approval.metadata).length > 0 ? (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Payload
          </p>
          <pre className="text-xs font-mono bg-muted rounded p-3 overflow-x-auto whitespace-pre-wrap break-words max-h-56">
            {JSON.stringify(approval.metadata, null, 2)}
          </pre>
        </div>
      ) : null}

      {/* Consequences */}
      {approval.consequences ? (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Consequences
          </p>
          <p className="text-sm text-muted-foreground">{approval.consequences}</p>
        </div>
      ) : null}

      {/* Affected entities */}
      {approval.affectedEntityIds.length > 0 && (
        <div className="space-y-1 pt-1 border-t">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Affected {approval.affectedEntityType}s ({approval.affectedEntityIds.length})
          </p>
          <p className="font-mono text-xs text-muted-foreground truncate">
            {approval.affectedEntityIds.slice(0, 5).join(', ')}
            {approval.affectedEntityIds.length > 5
              ? ` + ${approval.affectedEntityIds.length - 5} more`
              : ''}
          </p>
        </div>
      )}

      {/* Resolution note if present */}
      {approval.resolutionNote && (
        <div className="space-y-1 pt-1 border-t">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Resolution Note
          </p>
          <p className="text-sm">{approval.resolutionNote}</p>
        </div>
      )}
    </div>
  );
}

// ---- Main Component ----

interface ApprovalRowProps {
  approval: PendingApproval;
  resolveMutation: ReturnType<typeof useResolveApproval>;
}

export function ApprovalRow({ approval, resolveMutation }: ApprovalRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = React.useState(false);

  const isPending = resolveMutation.isPending;

  const handleApprove = () => {
    resolveMutation.mutate(
      { id: approval.id, action: 'approve' },
      {
        onSuccess: () => toast.success('Approval granted'),
        onError: () => toast.error('Failed to approve — please try again'),
      }
    );
  };

  const handleReject = (reason: string) => {
    resolveMutation.mutate(
      { id: approval.id, action: 'reject', reason },
      {
        onSuccess: () => {
          toast.success('Request rejected');
          setRejectDialogOpen(false);
        },
        onError: () => toast.error('Failed to reject — please try again'),
      }
    );
  };

  return (
    <>
      <TableRow
        className={cn('cursor-pointer hover:bg-muted/50 select-none', isExpanded && 'bg-muted/30')}
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        data-testid="approval-row"
      >
        {/* Expand chevron */}
        <TableCell className="w-8 pr-0">
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          )}
        </TableCell>

        {/* Action type */}
        <TableCell>
          <span className="font-mono text-xs">{approval.actionType}</span>
        </TableCell>

        {/* Description preview */}
        <TableCell className="max-w-xs">
          <span className="text-sm text-muted-foreground">
            {truncate(approval.actionDescription, 80)}
          </span>
        </TableCell>

        {/* Urgency badge */}
        <TableCell>
          <Badge variant={urgencyVariant(approval.urgency)} className="text-xs">
            {approval.urgency}
          </Badge>
        </TableCell>

        {/* Requested by */}
        <TableCell>
          <span className="font-mono text-xs text-muted-foreground">
            {truncate(approval.requestedById, 8)}
          </span>
        </TableCell>

        {/* Time */}
        <TableCell className="whitespace-nowrap">
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(approval.createdAt)}
          </span>
        </TableCell>

        {/* Actions — stop propagation so row click doesn't toggle expand */}
        <TableCell onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              variant="outline"
              className="h-7 border-green-500 text-green-700 hover:bg-green-50 hover:text-green-800 dark:text-green-400 dark:hover:bg-green-950"
              onClick={handleApprove}
              disabled={isPending}
              aria-label="Approve"
              data-testid="approve-button"
            >
              <Check className="h-3.5 w-3.5 mr-1" aria-hidden />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 border-destructive text-destructive hover:bg-destructive/10"
              onClick={() => setRejectDialogOpen(true)}
              disabled={isPending}
              aria-label="Reject"
              data-testid="reject-button"
            >
              <X className="h-3.5 w-3.5 mr-1" aria-hidden />
              Reject
            </Button>
          </div>
        </TableCell>
      </TableRow>

      {/* Expanded row */}
      {isExpanded && (
        <TableRow>
          <TableCell colSpan={7} className="p-0">
            <ExpandedContent approval={approval} />
          </TableCell>
        </TableRow>
      )}

      {/* Reject dialog */}
      <RejectDialog
        open={rejectDialogOpen}
        onOpenChange={setRejectDialogOpen}
        onConfirm={handleReject}
        isPending={isPending}
      />
    </>
  );
}
