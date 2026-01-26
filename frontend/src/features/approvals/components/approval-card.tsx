'use client';

/**
 * Approval Card - Displays an approval request in the queue.
 *
 * T190: Shows action type, description, agent, timestamp, and expiration countdown.
 * Provides quick approve/reject buttons for pending requests.
 *
 * @example
 * ```tsx
 * <ApprovalCard request={request} onSelect={handleSelect} />
 * ```
 */

import { formatDistanceToNow } from 'date-fns';
import { AlertCircle, Check, X, Clock, User, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ApprovalRequest } from '@/services/api/ai';

// ============================================================================
// Types
// ============================================================================

export interface ApprovalCardProps {
  request: ApprovalRequest;
  onSelect: (request: ApprovalRequest) => void;
  onQuickApprove?: (requestId: string) => Promise<void>;
  onQuickReject?: (requestId: string) => Promise<void>;
}

// ============================================================================
// Status Badge Component
// ============================================================================

interface StatusBadgeProps {
  status: ApprovalRequest['status'];
}

function StatusBadge({ status }: StatusBadgeProps) {
  const config = {
    pending: {
      variant: 'default' as const,
      className: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
      icon: Clock,
      label: 'Pending',
    },
    approved: {
      variant: 'default' as const,
      className: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
      icon: Check,
      label: 'Approved',
    },
    rejected: {
      variant: 'default' as const,
      className: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
      icon: X,
      label: 'Rejected',
    },
    expired: {
      variant: 'default' as const,
      className: 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20',
      icon: AlertCircle,
      label: 'Expired',
    },
  };

  const statusConfig = config[status];
  const Icon = statusConfig.icon;

  return (
    <Badge variant={statusConfig.variant} className={cn('gap-1', statusConfig.className)}>
      <Icon className="size-3" />
      {statusConfig.label}
    </Badge>
  );
}

// ============================================================================
// Action Type Badge Component
// ============================================================================

interface ActionTypeBadgeProps {
  actionType: string;
}

function ActionTypeBadge({ actionType }: ActionTypeBadgeProps) {
  // Format action type for display
  const formatted = actionType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <Badge variant="outline" className="font-mono text-xs">
      {formatted}
    </Badge>
  );
}

// ============================================================================
// Expiration Indicator Component
// ============================================================================

interface ExpirationIndicatorProps {
  expiresAt: string;
  status: ApprovalRequest['status'];
}

function ExpirationIndicator({ expiresAt, status }: ExpirationIndicatorProps) {
  if (status !== 'pending') return null;

  const expiryDate = new Date(expiresAt);
  const now = new Date();
  const isExpired = expiryDate < now;
  const timeLeft = isExpired
    ? 'Expired'
    : `Expires ${formatDistanceToNow(expiryDate, { addSuffix: true })}`;

  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <Clock className="size-3" />
      <span className={cn(isExpired && 'text-destructive font-medium')}>{timeLeft}</span>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ApprovalCard({
  request,
  onSelect,
  onQuickApprove,
  onQuickReject,
}: ApprovalCardProps) {
  const isPending = request.status === 'pending';
  const createdAt = new Date(request.created_at);

  return (
    <Card
      className={cn(
        'cursor-pointer hover:bg-muted/50 transition-colors',
        isPending && 'border-l-4 border-l-yellow-500'
      )}
      onClick={() => onSelect(request)}
      data-testid={`approval-card-${request.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Left Section: Content */}
          <div className="flex-1 min-w-0 space-y-2">
            {/* Header: Status + Action Type */}
            <div className="flex items-center gap-2 flex-wrap">
              <StatusBadge status={request.status} />
              <ActionTypeBadge actionType={request.action_type} />
            </div>

            {/* Description */}
            <p className="font-medium text-sm line-clamp-2">{request.context_preview}</p>

            {/* Metadata */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
              {/* Agent */}
              <div className="flex items-center gap-1.5">
                <Sparkles className="size-3" />
                <span>{request.agent_name}</span>
              </div>

              {/* Requested By */}
              <div className="flex items-center gap-1.5">
                <User className="size-3" />
                <span>{request.requested_by}</span>
              </div>

              {/* Created At */}
              <div className="flex items-center gap-1.5">
                <Clock className="size-3" />
                <span>{formatDistanceToNow(createdAt, { addSuffix: true })}</span>
              </div>
            </div>

            {/* Expiration */}
            <ExpirationIndicator expiresAt={request.expires_at} status={request.status} />
          </div>

          {/* Right Section: Quick Actions */}
          {isPending && onQuickApprove && onQuickReject && (
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={async (e) => {
                  e.stopPropagation();
                  await onQuickReject(request.id);
                }}
              >
                <X className="size-4" />
                Reject
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={async (e) => {
                  e.stopPropagation();
                  await onQuickApprove(request.id);
                }}
              >
                <Check className="size-4" />
                Approve
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
