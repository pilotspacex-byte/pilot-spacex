'use client';

/**
 * LiveIssueCard — Per-issue live AI status card.
 *
 * Shows issue identifier + title, ImplementationStatusBadge, and current stage text.
 * Left border color varies by implementation status.
 * Uses React.memo (NOT observer) — safe for TipTap NodeView context.
 *
 * Phase 77 — Implementation Dashboard (DSH-02, UIX-04)
 */
import * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { ImplementationStatusBadge } from '@/features/issues/components/implementation-status-badge';
import type { DashboardIssueStatus } from '../types';
import { cn } from '@/lib/utils';

export interface LiveIssueCardProps {
  issue: DashboardIssueStatus;
  className?: string;
}

function getStatusBorderColor(status: string): string {
  switch (status) {
    case 'implementing':
    case 'cloning':
    case 'creating_pr':
      return 'hsl(var(--ai))';
    case 'done':
      return 'hsl(var(--primary))';
    case 'failed':
    case 'cancelled':
      return 'hsl(var(--destructive))';
    default:
      return 'hsl(var(--muted-foreground))';
  }
}

export const LiveIssueCard = React.memo(function LiveIssueCard({
  issue,
  className,
}: LiveIssueCardProps) {
  const borderColor = getStatusBorderColor(issue.status);
  const stageText = issue.currentStage ?? 'Waiting to start';

  return (
    <Card
      className={cn('border-l-[3px] rounded-lg shadow-none', className)}
      style={{ borderLeftColor: borderColor }}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3 min-w-0">
          {/* Issue identifier + title */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 min-w-0">
              {issue.issueIdentifier && (
                <span className="text-[12px] font-semibold text-muted-foreground shrink-0">
                  {issue.issueIdentifier}
                </span>
              )}
              {issue.issueTitle && (
                <span className="text-[14px] font-normal text-foreground truncate">
                  {issue.issueTitle}
                </span>
              )}
            </div>
            {/* Stage text */}
            <p className="text-[12px] font-semibold text-muted-foreground italic mt-0.5">
              {stageText}
            </p>
          </div>
          {/* Status badge */}
          <div className="shrink-0">
            <ImplementationStatusBadge status={issue.status} animated />
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

LiveIssueCard.displayName = 'LiveIssueCard';
