'use client';

/**
 * IssueStatusRow - Single row in the linked issues panel
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from '@/components/ui/tooltip';
import { ImplementationStatusBadge } from '@/features/issues/components/implementation-status-badge';

export interface IssueStatusRowProps {
  identifier: string;
  title: string;
  stateName: string;
  stateGroup: string;
  batchStatus: string | null;
}

/** Maps issue state group → colored dot hex value */
const STATE_GROUP_DOT: Record<string, string> = {
  backlog: '#9c9590',
  unstarted: '#5b8fc9',
  started: '#d9853f',
  in_review: '#8b7ec8',
  completed: '#29a386',
  cancelled: '#d9534f',
};

/** Human-readable state label from group */
const STATE_GROUP_LABEL: Record<string, string> = {
  backlog: 'Backlog',
  unstarted: 'Todo',
  started: 'In Progress',
  in_review: 'In Review',
  completed: 'Done',
  cancelled: 'Cancelled',
};

export const IssueStatusRow = React.memo(function IssueStatusRow({
  identifier,
  title,
  stateName,
  stateGroup,
  batchStatus,
}: IssueStatusRowProps) {
  const dotColor = STATE_GROUP_DOT[stateGroup] ?? '#9c9590';
  const stateLabel = STATE_GROUP_LABEL[stateGroup] ?? stateName;

  return (
    <TooltipProvider>
      <div
        role="listitem"
        className="flex items-center gap-2 py-1 min-h-[32px]"
      >
        {/* Identifier chip */}
        <span
          className="font-mono text-[12px] font-semibold leading-[1.4] text-muted-foreground shrink-0"
          aria-label={`Issue ${identifier}`}
        >
          {identifier}
        </span>

        {/* Title — truncates with full title in tooltip */}
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex-1 text-[14px] font-normal leading-[1.5] truncate min-w-0 cursor-default">
              {title}
            </span>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-[240px] text-xs">
            {title}
          </TooltipContent>
        </Tooltip>

        {/* Status badge */}
        <div className="shrink-0">
          {batchStatus ? (
            <ImplementationStatusBadge status={batchStatus} animated={false} />
          ) : (
            <span
              className={cn(
                'inline-flex items-center gap-1 text-[12px] font-semibold leading-[1.4]',
                'text-muted-foreground'
              )}
            >
              <span
                aria-hidden="true"
                className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                style={{ backgroundColor: dotColor }}
              />
              {stateLabel}
            </span>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
});

IssueStatusRow.displayName = 'IssueStatusRow';
