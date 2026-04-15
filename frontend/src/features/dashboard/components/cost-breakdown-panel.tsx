'use client';

/**
 * CostBreakdownPanel — Sprint and per-issue cost tracking panel.
 *
 * Displays sprint total and monthly running total in Geist Mono font.
 * Per-issue table sorted by cost (descending).
 * Tooltip on cost figures explains data source.
 *
 * Phase 77 — Implementation Dashboard (DSH-04, UIX-04)
 */
import * as React from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { DashboardIssueStatus } from '../types';
import { cn } from '@/lib/utils';

export interface CostBreakdownPanelProps {
  sprintCostCents: number;
  monthlyCostCents: number;
  issues: DashboardIssueStatus[];
  className?: string;
}

function formatCost(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

const CostTooltip = React.memo(function CostTooltip({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>
        <p className="text-[12px]">Calculated from batch_run_issues.cost_cents</p>
      </TooltipContent>
    </Tooltip>
  );
});

CostTooltip.displayName = 'CostTooltip';

export const CostBreakdownPanel = React.memo(function CostBreakdownPanel({
  sprintCostCents,
  monthlyCostCents,
  issues,
  className,
}: CostBreakdownPanelProps) {
  // Sort issues by cost descending
  const sortedIssues = React.useMemo(
    () => [...issues].sort((a, b) => b.costCents - a.costCents),
    [issues]
  );

  const sprintFormatted = formatCost(sprintCostCents);
  const monthlyFormatted = formatCost(monthlyCostCents);

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Sprint total */}
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">
          Sprint cost
        </p>
        <CostTooltip>
          <span
            className="font-mono text-[14px] font-semibold text-[hsl(var(--primary-text))] cursor-default"
            aria-label={sprintFormatted}
          >
            {sprintFormatted}
          </span>
        </CostTooltip>
      </div>

      {/* Per-issue table */}
      {sortedIssues.length > 0 && (
        <div className="flex flex-col gap-1">
          {sortedIssues.map((issue) => {
            const costFormatted = formatCost(issue.costCents);
            return (
              <div
                key={issue.id}
                className="flex items-center justify-between gap-2 py-0.5"
              >
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
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
                <CostTooltip>
                  <span
                    className="font-mono text-[12px] font-semibold text-muted-foreground shrink-0 text-right cursor-default"
                    aria-label={costFormatted}
                  >
                    {costFormatted}
                  </span>
                </CostTooltip>
              </div>
            );
          })}
        </div>
      )}

      {/* Monthly running total */}
      <div className="flex items-center justify-between border-t border-border pt-3">
        <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide">
          This month
        </p>
        <CostTooltip>
          <span
            className="font-mono text-[14px] font-semibold text-[hsl(var(--primary-text))] cursor-default"
            aria-label={monthlyFormatted}
          >
            {monthlyFormatted}
          </span>
        </CostTooltip>
      </div>
    </div>
  );
});

CostBreakdownPanel.displayName = 'CostBreakdownPanel';
