'use client';

/**
 * LinkedIssuesPanel - Collapsible list of issues linked to this note
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { LinkedIssueResponse } from '@/services/api/notes';
import { IssueStatusRow } from './issue-status-row';

export interface LinkedIssuesPanelProps {
  issues: LinkedIssueResponse[] | undefined;
  isLoading: boolean;
}

const MAX_VISIBLE_WITHOUT_SCROLL = 8;

export const LinkedIssuesPanel = React.memo(function LinkedIssuesPanel({
  issues,
  isLoading,
}: LinkedIssuesPanelProps) {
  const [open, setOpen] = React.useState(true);

  const issueList = issues ?? [];
  const hasMany = issueList.length > MAX_VISIBLE_WITHOUT_SCROLL;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      {/* Section header */}
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between group"
          aria-label={open ? 'Collapse linked issues' : 'Expand linked issues'}
        >
          <span className="text-[12px] font-semibold leading-[1.4] uppercase tracking-wide text-muted-foreground">
            Linked Issues
          </span>
          <ChevronDown
            className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 motion-safe:ease-out ${open ? 'rotate-0' : '-rotate-90'}`}
            aria-hidden="true"
          />
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-2">
        {isLoading ? (
          /* Loading state — 3 skeleton rows */
          <div className="space-y-2" aria-label="Loading linked issues">
            <Skeleton className="h-[32px] w-full rounded" />
            <Skeleton className="h-[32px] w-full rounded" />
            <Skeleton className="h-[32px] w-4/5 rounded" />
          </div>
        ) : issueList.length === 0 ? (
          /* Empty state */
          <div className="py-2">
            <p className="text-[14px] font-normal leading-[1.5] text-foreground">
              No linked issues
            </p>
            <p className="text-[12px] font-normal leading-[1.4] text-muted-foreground mt-0.5">
              Issues created from this note will appear here.
            </p>
          </div>
        ) : hasMany ? (
          /* Scrollable list when > 8 items */
          <ScrollArea className="max-h-64">
            <div role="list">
              {issueList.map((issue) => (
                <IssueStatusRow
                  key={issue.id}
                  identifier={issue.identifier}
                  title={issue.title}
                  stateName={issue.stateName}
                  stateGroup={issue.stateGroup}
                  batchStatus={issue.batchStatus}
                />
              ))}
            </div>
          </ScrollArea>
        ) : (
          /* Plain list when <= 8 items */
          <div role="list">
            {issueList.map((issue) => (
              <IssueStatusRow
                key={issue.id}
                identifier={issue.identifier}
                title={issue.title}
                stateName={issue.stateName}
                stateGroup={issue.stateGroup}
                batchStatus={issue.batchStatus}
              />
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
});

LinkedIssuesPanel.displayName = 'LinkedIssuesPanel';
