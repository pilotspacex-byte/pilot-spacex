'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  CircleDashed,
  Circle,
  PlayCircle,
  CircleDot,
  CheckCircle2,
  XCircle,
  Inbox,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIssueViewStore } from '@/stores/RootStore';
import { ListGroup } from './ListGroup';
import { BulkActionsBar } from './BulkActionsBar';
import type { Issue, IssueState, IssuePriority } from '@/types';

const STATE_GROUPS = [
  {
    key: 'backlog',
    label: 'Backlog',
    icon: CircleDashed,
    iconClass: 'text-[var(--color-state-backlog)]',
  },
  { key: 'todo', label: 'Todo', icon: Circle, iconClass: 'text-[var(--color-state-todo)]' },
  {
    key: 'in_progress',
    label: 'In Progress',
    icon: PlayCircle,
    iconClass: 'text-[var(--color-state-in-progress)]',
  },
  {
    key: 'in_review',
    label: 'In Review',
    icon: CircleDot,
    iconClass: 'text-[var(--color-state-in-review)]',
  },
  { key: 'done', label: 'Done', icon: CheckCircle2, iconClass: 'text-[var(--color-state-done)]' },
  {
    key: 'cancelled',
    label: 'Cancelled',
    icon: XCircle,
    iconClass: 'text-[var(--color-state-cancelled)]',
  },
];

function getIssueState(issue: Issue): string {
  return issue.state?.name?.toLowerCase().replace(/\s+/g, '_') ?? 'backlog';
}

interface ListViewProps {
  issues: Issue[];
  isLoading: boolean;
  onIssueClick?: (issue: Issue) => void;
  onStateChange?: (issueId: string, state: IssueState) => void;
  onPriorityChange?: (issueId: string, priority: IssuePriority) => void;
  onBulkStateChange?: (issueIds: string[], state: IssueState) => void;
  onBulkPriorityChange?: (issueIds: string[], priority: IssuePriority) => void;
  onBulkDelete?: (issueIds: string[]) => void;
  className?: string;
}

export const ListView = observer(function ListView({
  issues,
  isLoading,
  onIssueClick,
  onStateChange,
  onPriorityChange,
  onBulkStateChange,
  onBulkPriorityChange,
  onBulkDelete,
  className,
}: ListViewProps) {
  const viewStore = useIssueViewStore();

  const groupedIssues = React.useMemo(() => {
    const groups: Record<string, Issue[]> = {};
    for (const g of STATE_GROUPS) groups[g.key] = [];
    for (const issue of issues) {
      const state = getIssueState(issue);
      if (groups[state]) groups[state]!.push(issue);
      else groups['backlog']!.push(issue);
    }
    return groups;
  }, [issues]);

  const handleToggleSelect = (id: string) => {
    viewStore.toggleSelectedIssue(id);
  };

  const selectedIds = viewStore.selectedIssueIds;
  const selectedArray = Array.from(selectedIds);

  if (isLoading) {
    return (
      <div className={cn('flex flex-col', className)}>
        {Array.from({ length: 3 }).map((_, gi) => (
          <div key={gi} className="border-b p-3">
            <div className="mb-2 h-5 w-32 animate-pulse rounded bg-muted" />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="mb-1 h-11 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-16', className)}>
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-muted">
          <Inbox className="size-6 text-primary" />
        </div>
        <h3 className="mt-4 text-sm font-medium text-foreground">No issues yet</h3>
        <p className="mt-1 max-w-xs text-center text-xs text-muted-foreground">
          Issues track work across your team. Create one manually or let AI extract them from your
          notes.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('relative flex flex-col', className)}>
      {STATE_GROUPS.map((group) => {
        const groupIssues = groupedIssues[group.key] ?? [];
        if (groupIssues.length === 0) return null;
        return (
          <ListGroup
            key={group.key}
            groupKey={group.key}
            groupLabel={group.label}
            groupIcon={group.icon}
            groupIconClass={group.iconClass}
            issues={groupIssues}
            isCollapsed={viewStore.collapsedGroups.has(group.key)}
            onToggleCollapse={() => viewStore.toggleGroupCollapsed(group.key)}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onStateChange={onStateChange}
            onPriorityChange={onPriorityChange}
            onNavigate={onIssueClick}
          />
        );
      })}

      <BulkActionsBar
        selectedCount={selectedIds.size}
        onChangeState={onBulkStateChange ? (s) => onBulkStateChange(selectedArray, s) : undefined}
        onSetPriority={
          onBulkPriorityChange ? (p) => onBulkPriorityChange(selectedArray, p) : undefined
        }
        onDelete={onBulkDelete ? () => onBulkDelete(selectedArray) : undefined}
        onClearSelection={() => viewStore.clearSelection()}
      />
    </div>
  );
});
