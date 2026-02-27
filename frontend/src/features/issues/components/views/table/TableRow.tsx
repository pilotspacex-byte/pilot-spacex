'use client';

import * as React from 'react';
import {
  Bug,
  Lightbulb,
  Wrench,
  CheckSquare,
  CircleDashed,
  Circle,
  PlayCircle,
  CircleDot,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowUp,
  Minus,
  ArrowDown,
  User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import type { Issue, IssuePriority, IssueType } from '@/types';
import type { TableColumnDef } from './TableColumn';

const stateIcons: Record<string, React.ElementType> = {
  backlog: CircleDashed,
  todo: Circle,
  in_progress: PlayCircle,
  in_review: CircleDot,
  done: CheckCircle2,
  cancelled: XCircle,
};
const stateColors: Record<string, string> = {
  backlog: 'text-[var(--color-state-backlog)]',
  todo: 'text-[var(--color-state-todo)]',
  in_progress: 'text-[var(--color-state-in-progress)]',
  in_review: 'text-[var(--color-state-in-review)]',
  done: 'text-[var(--color-state-done)]',
  cancelled: 'text-[var(--color-state-cancelled)]',
};
const priorityIcons: Record<IssuePriority, React.ElementType> = {
  urgent: AlertCircle,
  high: ArrowUp,
  medium: Minus,
  low: ArrowDown,
  none: Minus,
};
const priorityColors: Record<IssuePriority, string> = {
  urgent: 'text-[var(--color-priority-urgent)]',
  high: 'text-[var(--color-priority-high)]',
  medium: 'text-[var(--color-priority-medium)]',
  low: 'text-[var(--color-priority-low)]',
  none: 'text-[var(--color-priority-none)]',
};
const typeIcons: Record<IssueType, React.ElementType> = {
  bug: Bug,
  feature: Lightbulb,
  improvement: Wrench,
  task: CheckSquare,
};
const typeColors: Record<IssueType, string> = {
  bug: 'text-red-500',
  feature: 'text-purple-500',
  improvement: 'text-blue-500',
  task: 'text-gray-500',
};

function getStateName(issue: Issue): string {
  return issue.state?.name?.toLowerCase().replace(/\s+/g, '_') ?? 'backlog';
}

interface TableRowProps {
  issue: Issue;
  columns: TableColumnDef[];
  columnWidths: Map<string, number>;
  hiddenColumns: Set<string>;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onNavigate?: (issue: Issue) => void;
}

export function TableRow({
  issue,
  columns,
  columnWidths,
  hiddenColumns,
  isSelected,
  onToggleSelect,
  onNavigate,
}: TableRowProps) {
  const visibleColumns = columns.filter((c) => !hiddenColumns.has(c.key));
  const stateName = getStateName(issue);
  const StateIcon = stateIcons[stateName] ?? CircleDashed;
  const priority = issue.priority ?? 'none';
  const PriorityIcon = priorityIcons[priority];
  const issueType = (issue.type ?? 'task') as IssueType;
  const TypeIcon = typeIcons[issueType];

  const renderCell = (col: TableColumnDef) => {
    switch (col.key) {
      case 'identifier':
        return (
          <span className="font-mono text-[11px] text-muted-foreground">{issue.identifier}</span>
        );
      case 'name':
        return (
          <button
            onClick={() => onNavigate?.(issue)}
            className="truncate text-left text-sm hover:text-primary transition-colors"
          >
            {issue.name}
          </button>
        );
      case 'state':
        return (
          <span className="flex items-center gap-1.5 text-xs">
            <StateIcon className={cn('size-3.5', stateColors[stateName])} />
            <span className="truncate">{issue.state?.name ?? 'Backlog'}</span>
          </span>
        );
      case 'priority':
        return (
          <span className="flex items-center gap-1.5 text-xs">
            <PriorityIcon className={cn('size-3.5', priorityColors[priority])} />
          </span>
        );
      case 'type':
        return (
          <span className="flex items-center gap-1.5 text-xs">
            <TypeIcon className={cn('size-3.5', typeColors[issueType])} />
            <span className="capitalize truncate">{issueType}</span>
          </span>
        );
      case 'assignee':
        return issue.assignee ? (
          <span className="flex items-center gap-1.5 text-xs">
            <Avatar className="size-5">
              <AvatarFallback className="text-[9px]">
                {(issue.assignee.displayName ?? issue.assignee.email).charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <span className="truncate">{issue.assignee.displayName ?? issue.assignee.email}</span>
          </span>
        ) : (
          <User className="size-4 text-muted-foreground/40" />
        );
      case 'labels':
        return (
          <div className="flex items-center gap-1">
            {issue.labels.slice(0, 2).map((l) => (
              <Badge
                key={l.id}
                variant="secondary"
                className="h-4 px-1 text-[10px]"
                style={{ backgroundColor: `${l.color}20`, color: l.color }}
              >
                {l.name}
              </Badge>
            ))}
            {issue.labels.length > 2 && (
              <span className="text-[10px] text-muted-foreground">+{issue.labels.length - 2}</span>
            )}
          </div>
        );
      case 'estimate':
        return (
          <span className="text-xs text-muted-foreground">{issue.estimatePoints ?? '\u2014'}</span>
        );
      case 'dueDate':
        return issue.targetDate ? (
          <span className="text-xs text-muted-foreground">
            {new Date(issue.targetDate).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground/40">{'\u2014'}</span>
        );
      case 'createdAt':
        return (
          <span className="text-xs text-muted-foreground">
            {new Date(issue.createdAt).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        );
      case 'updatedAt':
        return (
          <span className="text-xs text-muted-foreground">
            {new Date(issue.updatedAt).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
            })}
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div
      className={cn(
        'flex min-h-[44px] items-center border-b hover:bg-accent/30 transition-colors',
        isSelected && 'bg-accent/20'
      )}
    >
      <div className="flex w-10 shrink-0 items-center justify-center border-r">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelect(issue.id)}
          className="size-4 rounded border accent-[#29A386]"
          aria-label={`Select ${issue.identifier}`}
        />
      </div>
      {visibleColumns.map((col) => (
        <div
          key={col.key}
          className="flex shrink-0 items-center border-r px-2"
          style={{ width: columnWidths.get(col.key) ?? col.defaultWidth }}
        >
          {renderCell(col)}
        </div>
      ))}
    </div>
  );
}
