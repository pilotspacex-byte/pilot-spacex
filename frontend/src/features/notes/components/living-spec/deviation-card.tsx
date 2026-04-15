'use client';

/**
 * DeviationCard - Amber-bordered AI deviation annotation card
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { AlertTriangle } from 'lucide-react';

export interface DeviationCardProps {
  content: string;
  issueId: string | null;
  createdAt: string;
  prUrl: string | null;
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

export const DeviationCard = React.memo(function DeviationCard({
  content,
  issueId: _issueId,
  createdAt,
  prUrl,
}: DeviationCardProps) {
  return (
    <article
      role="article"
      className="rounded-md bg-card p-3"
      style={{ borderLeft: '3px solid hsl(var(--warning))' }}
    >
      {/* Header row */}
      <div className="flex items-center gap-1.5 mb-1.5">
        <AlertTriangle
          aria-hidden="true"
          className="h-3.5 w-3.5 shrink-0"
          style={{ color: 'hsl(var(--warning))' }}
        />
        <span className="text-[12px] font-semibold leading-[1.4] text-foreground">
          Deviation detected:
        </span>
      </div>

      {/* Content */}
      <p className="text-[14px] font-normal leading-[1.5] text-foreground mb-2">{content}</p>

      {/* Footer: timestamp + PR link */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <time
          dateTime={createdAt}
          className="font-mono text-[12px] font-semibold leading-[1.4] text-muted-foreground"
        >
          {formatTimestamp(createdAt)}
        </time>
        {prUrl && (
          <a
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[12px] font-semibold text-primary hover:underline leading-[1.4]"
          >
            View PR
          </a>
        )}
      </div>
    </article>
  );
});

DeviationCard.displayName = 'DeviationCard';
