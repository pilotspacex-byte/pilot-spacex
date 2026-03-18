'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIssueViewStore } from '@/stores/RootStore';
import { TableHead } from './TableHead';
import { TableRow } from './TableRow';
import { ColumnVisibility } from './ColumnVisibility';
import { DEFAULT_COLUMNS, DEFAULT_VISIBLE, type SortDirection } from './TableColumn';
import type { Issue } from '@/types';

function getSortValue(issue: Issue, column: string): string | number {
  switch (column) {
    case 'identifier':
      return issue.identifier;
    case 'name':
      return issue.name;
    case 'state':
      return issue.state?.name ?? '';
    case 'priority': {
      const order: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3, none: 4 };
      return order[issue.priority ?? 'none'] ?? 4;
    }
    case 'type':
      return issue.type ?? 'task';
    case 'assignee':
      return issue.assignee?.displayName ?? issue.assignee?.email ?? '';
    case 'estimate':
      return issue.estimatePoints ?? 0;
    case 'dueDate':
      return issue.targetDate ?? '';
    case 'createdAt':
      return issue.createdAt;
    case 'updatedAt':
      return issue.updatedAt;
    default:
      return '';
  }
}

interface TableViewProps {
  issues: Issue[];
  isLoading: boolean;
  onIssueClick?: (issue: Issue) => void;
  className?: string;
}

export const TableView = observer(function TableView({
  issues,
  isLoading,
  onIssueClick,
  className,
}: TableViewProps) {
  const viewStore = useIssueViewStore();
  const parentRef = React.useRef<HTMLDivElement>(null);

  const [sortColumn, setSortColumn] = React.useState<string | null>(null);
  const [sortDirection, setSortDirection] = React.useState<SortDirection>(null);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      if (sortDirection === 'asc') setSortDirection('desc');
      else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      } else setSortDirection('asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const sortedIssues = React.useMemo(() => {
    if (!sortColumn || !sortDirection) return issues;
    return [...issues].sort((a, b) => {
      const aVal = getSortValue(a, sortColumn);
      const bVal = getSortValue(b, sortColumn);
      const cmp =
        typeof aVal === 'number' && typeof bVal === 'number'
          ? aVal - bVal
          : String(aVal).localeCompare(String(bVal));
      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [issues, sortColumn, sortDirection]);

  const virtualizer = useVirtualizer({
    count: sortedIssues.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 10,
  });

  const handleResetColumns = () => {
    for (const col of DEFAULT_COLUMNS) {
      if (DEFAULT_VISIBLE.includes(col.key)) {
        if (viewStore.hiddenColumns.has(col.key)) viewStore.toggleHiddenColumn(col.key);
      } else {
        if (!viewStore.hiddenColumns.has(col.key)) viewStore.toggleHiddenColumn(col.key);
      }
    }
  };

  const handleSelectAll = () => {
    if (viewStore.selectedIssueIds.size === sortedIssues.length) {
      viewStore.clearSelection();
    } else {
      viewStore.selectAll(sortedIssues.map((i) => i.id));
    }
  };

  if (isLoading) {
    return (
      <div className={cn('flex flex-col', className)}>
        <div className="flex h-8 border-b bg-muted/50">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex-1 border-r px-2 py-1">
              <div className="h-4 w-16 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex h-11 border-b">
            {Array.from({ length: 6 }).map((_, j) => (
              <div key={j} className="flex-1 border-r px-2 py-2">
                <div className="h-4 animate-pulse rounded bg-muted" />
              </div>
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
    <div className={cn('flex flex-col', className)}>
      <div className="flex items-center justify-end px-2 py-1 border-b">
        <ColumnVisibility
          hiddenColumns={viewStore.hiddenColumns}
          onToggle={(key) => viewStore.toggleHiddenColumn(key)}
          onReset={handleResetColumns}
        />
      </div>

      <div ref={parentRef} className="flex-1 overflow-auto">
        <div style={{ minWidth: '800px' }}>
          <TableHead
            columns={DEFAULT_COLUMNS}
            columnWidths={viewStore.columnWidths}
            hiddenColumns={viewStore.hiddenColumns}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onResize={(key, w) => viewStore.setColumnWidth(key, w)}
            allSelected={
              viewStore.selectedIssueIds.size === sortedIssues.length && sortedIssues.length > 0
            }
            onSelectAll={handleSelectAll}
          />

          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const issue = sortedIssues[virtualRow.index]!;
              return (
                <div
                  key={issue.id}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <TableRow
                    issue={issue}
                    columns={DEFAULT_COLUMNS}
                    columnWidths={viewStore.columnWidths}
                    hiddenColumns={viewStore.hiddenColumns}
                    isSelected={viewStore.selectedIssueIds.has(issue.id)}
                    onToggleSelect={(id) => viewStore.toggleSelectedIssue(id)}
                    onNavigate={onIssueClick}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
});
