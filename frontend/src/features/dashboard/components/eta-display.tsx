'use client';

/**
 * EtaDisplay — Estimated time remaining for the sprint.
 *
 * Computes ETA from average completed issue duration × remaining count.
 * Wraps in a Tooltip showing the data basis.
 * Returns null when sprint is complete (all issues done/failed/cancelled).
 *
 * Phase 77 — Implementation Dashboard (DSH-01)
 */
import * as React from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { DashboardIssueStatus } from '../types';
import { cn } from '@/lib/utils';

export interface EtaDisplayProps {
  issues: DashboardIssueStatus[];
  className?: string;
}

const TERMINAL_STATUSES = new Set(['done', 'failed', 'cancelled']);

function computeEta(issues: DashboardIssueStatus[]): {
  text: string;
  tooltipText: string;
} | null {
  if (issues.length === 0) {
    return { text: 'Estimating time remaining...', tooltipText: 'No issues yet' };
  }

  // Check if all issues are terminal — sprint complete
  const allTerminal = issues.every((i) => TERMINAL_STATUSES.has(i.status));
  if (allTerminal) {
    return null; // Hidden when sprint is complete
  }

  // Find completed issues with valid start + end times
  const completedIssues = issues.filter(
    (i) => i.status === 'done' && i.startedAt && i.completedAt
  );

  if (completedIssues.length === 0) {
    return {
      text: 'Estimating time remaining...',
      tooltipText: 'No completed issues to estimate from yet',
    };
  }

  // Average duration in ms
  const totalDurationMs = completedIssues.reduce((sum, i) => {
    const start = new Date(i.startedAt!).getTime();
    const end = new Date(i.completedAt!).getTime();
    return sum + Math.max(0, end - start);
  }, 0);

  const avgDurationMs = totalDurationMs / completedIssues.length;

  // Remaining: not terminal
  const remainingCount = issues.filter((i) => !TERMINAL_STATUSES.has(i.status)).length;

  if (remainingCount === 0) {
    return null;
  }

  const etaMs = avgDurationMs * remainingCount;
  const etaMinutes = Math.ceil(etaMs / 60_000);

  return {
    text: `~${etaMinutes} min remaining`,
    tooltipText: `Based on average of ${completedIssues.length} completed issue${completedIssues.length === 1 ? '' : 's'}`,
  };
}

export const EtaDisplay = React.memo(function EtaDisplay({
  issues,
  className,
}: EtaDisplayProps) {
  const eta = computeEta(issues);

  if (!eta) return null;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <p
          className={cn(
            'text-[12px] font-semibold text-muted-foreground cursor-default',
            className
          )}
        >
          {eta.text}
        </p>
      </TooltipTrigger>
      <TooltipContent>
        <p className="text-[12px]">{eta.tooltipText}</p>
      </TooltipContent>
    </Tooltip>
  );
});

EtaDisplay.displayName = 'EtaDisplay';
