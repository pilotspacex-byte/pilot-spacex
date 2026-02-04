'use client';

/**
 * Approval List Item - Compact row view for approval queue list.
 *
 * T192: Shows approval in a compact list format with quick actions.
 * Alternative to ApprovalCard for denser layouts.
 *
 * @example
 * ```tsx
 * <ApprovalListItem request={request} onSelect={handleSelect} />
 * ```
 */

import { formatDistanceToNow } from 'date-fns';
import { Check, X, Clock, User, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ApprovalRequest } from '@/services/api/ai';

// ============================================================================
// Types
// ============================================================================

export interface ApprovalListItemProps {
  request: ApprovalRequest;
  onSelect: (request: ApprovalRequest) => void;
  onQuickApprove?: (requestId: string) => Promise<void>;
  onQuickReject?: (requestId: string) => Promise<void>;
}

// ============================================================================
// Status Indicator Component
// ============================================================================

interface StatusIndicatorProps {
  status: ApprovalRequest['status'];
}

function StatusIndicator({ status }: StatusIndicatorProps) {
  const colors = {
    pending: 'bg-yellow-500',
    approved: 'bg-green-500',
    rejected: 'bg-red-500',
    expired: 'bg-gray-500',
  };

  return (
    <div
      className={cn('size-2 rounded-full shrink-0', colors[status])}
      title={status}
      aria-label={`Status: ${status}`}
    />
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ApprovalListItem({
  request,
  onSelect,
  onQuickApprove,
  onQuickReject,
}: ApprovalListItemProps) {
  const isPending = request.status === 'pending';
  const createdAt = new Date(request.created_at);
  const expiresAt = new Date(request.expires_at);
  const isExpired = isPending && expiresAt < new Date();

  const formatActionType = (actionType: string) => {
    return actionType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg border cursor-pointer',
        'hover:bg-muted/50 transition-colors',
        isPending && 'border-l-4 border-l-yellow-500'
      )}
      role="button"
      tabIndex={0}
      onClick={() => onSelect(request)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(request);
        }
      }}
      data-testid={`approval-list-item-${request.id}`}
    >
      {/* Status Indicator */}
      <StatusIndicator status={request.status} />

      {/* Content Section */}
      <div className="flex-1 min-w-0 grid grid-cols-12 gap-3 items-center">
        {/* Description (4 cols) */}
        <div className="col-span-4 min-w-0">
          <p className="text-sm font-medium truncate">{request.context_preview}</p>
        </div>

        {/* Action Type (2 cols) */}
        <div className="col-span-2">
          <Badge variant="outline" className="font-mono text-xs">
            {formatActionType(request.action_type)}
          </Badge>
        </div>

        {/* Agent (2 cols) */}
        <div className="col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="size-3 shrink-0" />
          <span className="truncate">{request.agent_name}</span>
        </div>

        {/* Requested By (2 cols) */}
        <div className="col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <User className="size-3 shrink-0" />
          <span className="truncate">{request.requested_by}</span>
        </div>

        {/* Time (2 cols) */}
        <div className="col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="size-3 shrink-0" />
          <span className={cn(isExpired && 'text-destructive font-medium')}>
            {isPending
              ? isExpired
                ? 'Expired'
                : formatDistanceToNow(expiresAt, { addSuffix: true })
              : formatDistanceToNow(createdAt, { addSuffix: true })}
          </span>
        </div>
      </div>

      {/* Quick Actions */}
      {isPending && !isExpired && onQuickApprove && onQuickReject && (
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="size-8 p-0"
            onClick={async (e) => {
              e.stopPropagation();
              try {
                await onQuickReject(request.id);
              } catch {
                toast.error('Failed to reject approval request');
              }
            }}
            title="Reject"
          >
            <X className="size-4" />
          </Button>
          <Button
            size="sm"
            className="size-8 p-0"
            onClick={async (e) => {
              e.stopPropagation();
              try {
                await onQuickApprove(request.id);
              } catch {
                toast.error('Failed to approve request');
              }
            }}
            title="Approve"
          >
            <Check className="size-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
