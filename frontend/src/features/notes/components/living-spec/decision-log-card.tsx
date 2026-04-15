'use client';

/**
 * DecisionLogCard - Dusty-blue-bordered approval/rejection decision record
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

export interface DecisionLogCardProps {
  action: string | null;
  issues: string[] | null;
  userId: string | null;
  createdAt: string;
  content: string;
}

function formatTimestamp(isoString: string): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

export const DecisionLogCard = React.memo(function DecisionLogCard({
  action,
  issues,
  userId: _userId,
  createdAt,
  content,
}: DecisionLogCardProps) {
  const isApproved = action === 'approved';
  const actionLabel = isApproved ? 'Approved' : 'Rejected';

  return (
    <article
      role="article"
      className="rounded-md bg-card p-3"
      style={{ borderLeft: '3px solid hsl(var(--ai))' }}
    >
      {/* Header row */}
      <div className="flex items-center gap-1.5 mb-1.5">
        {isApproved ? (
          <CheckCircle2
            aria-hidden="true"
            className="h-3.5 w-3.5 shrink-0"
            style={{ color: 'hsl(var(--ai))' }}
          />
        ) : (
          <XCircle
            aria-hidden="true"
            className="h-3.5 w-3.5 shrink-0 text-destructive"
          />
        )}
        <span className="text-[14px] font-semibold leading-[1.5] text-foreground">
          {actionLabel}
        </span>
        {issues && issues.length > 0 && (
          <span className="text-[12px] font-normal leading-[1.4] text-muted-foreground">
            ({issues.join(', ')})
          </span>
        )}
      </div>

      {/* Content */}
      {content && (
        <p className="text-[14px] font-normal leading-[1.5] text-foreground mb-2">{content}</p>
      )}

      {/* Timestamp */}
      <time
        dateTime={createdAt}
        className="font-mono text-[12px] font-semibold leading-[1.4] text-muted-foreground"
      >
        {formatTimestamp(createdAt)}
      </time>
    </article>
  );
});

DecisionLogCard.displayName = 'DecisionLogCard';
