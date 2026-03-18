'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { AlertTriangle, ArrowUp, Minus, ArrowDown, CircleDashed, Inbox } from 'lucide-react';
import { useIssueViewStore } from '@/stores/RootStore';
import { ListGroup } from '../list/ListGroup';
import { BulkActionsBar } from '../list/BulkActionsBar';
import type { Issue, IssueState, IssuePriority } from '@/types';

const PRIORITY_GROUPS = [
  { key: 'urgent', label: 'Urgent', icon: AlertTriangle, iconClass: 'text-priority-urgent' },
  { key: 'high', label: 'High', icon: ArrowUp, iconClass: 'text-priority-high' },
  { key: 'medium', label: 'Medium', icon: Minus, iconClass: 'text-priority-medium' },
  { key: 'low', label: 'Low', icon: ArrowDown, iconClass: 'text-priority-low' },
  { key: 'none', label: 'No Priority', icon: CircleDashed, iconClass: 'text-muted-foreground' },
] as const;

interface PriorityViewProps {
  issues: Issue[];
  isLoading: boolean;
  onIssueClick?: (issue: Issue) => void;
  onStateChange?: (issueId: string, state: IssueState) => void;
  onPriorityChange?: (issueId: string, priority: IssuePriority) => void;
  onBulkStateChange?: (issueIds: string[], state: IssueState) => void;
  onBulkPriorityChange?: (issueIds: string[], priority: IssuePriority) => void;
  onBulkDelete?: (issueIds: string[]) => void;
}

export const PriorityView = observer(function PriorityView({
  issues,
  isLoading,
  onIssueClick,
  onStateChange,
  onPriorityChange,
  onBulkStateChange,
  onBulkPriorityChange,
  onBulkDelete,
}: PriorityViewProps) {
  const viewStore = useIssueViewStore();

  const groupedIssues = React.useMemo(() => {
    const groups: Record<string, Issue[]> = {};
    for (const g of PRIORITY_GROUPS) groups[g.key] = [];
    for (const issue of issues) {
      const priorityKey = issue.priority ?? 'none';
      if (groups[priorityKey] !== undefined) {
        groups[priorityKey]!.push(issue);
      } else {
        groups['none']!.push(issue);
      }
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
      <div className="flex flex-col">
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
      <div className="flex flex-col items-center justify-center py-16">
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
    <div className="relative flex flex-col">
      {PRIORITY_GROUPS.map((group) => {
        const groupIssues = groupedIssues[group.key] ?? [];
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
