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
  Plus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { IssueCard } from './IssueCard';
import type { Issue, IssueState } from '@/types';

export interface IssueBoardProps {
  /** Issues grouped by state */
  issuesByState: Record<IssueState, Issue[]>;
  /** Called when an issue is clicked */
  onIssueClick?: (issue: Issue) => void;
  /** Called to navigate to issue detail page */
  onOpenIssue?: (issue: Issue) => void;
  /** Called when an issue is dropped on a column */
  onIssueDrop?: (issueId: string, newState: IssueState) => void;
  /** Called when creating a new issue in a column */
  onCreateIssue?: (state: IssueState) => void;
  /** Whether the board is loading */
  isLoading?: boolean;
  className?: string;
}

interface ColumnConfig {
  state: IssueState;
  label: string;
  icon: React.ElementType;
  iconClass: string;
  bgClass: string;
}

const columns: ColumnConfig[] = [
  {
    state: 'backlog',
    label: 'Backlog',
    icon: CircleDashed,
    iconClass: 'text-gray-500',
    bgClass: 'bg-gray-50 dark:bg-gray-900/50',
  },
  {
    state: 'todo',
    label: 'Todo',
    icon: Circle,
    iconClass: 'text-blue-500',
    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
  },
  {
    state: 'in_progress',
    label: 'In Progress',
    icon: PlayCircle,
    iconClass: 'text-yellow-500',
    bgClass: 'bg-yellow-50 dark:bg-yellow-900/20',
  },
  {
    state: 'in_review',
    label: 'In Review',
    icon: CircleDot,
    iconClass: 'text-purple-500',
    bgClass: 'bg-purple-50 dark:bg-purple-900/20',
  },
  {
    state: 'done',
    label: 'Done',
    icon: CheckCircle2,
    iconClass: 'text-green-500',
    bgClass: 'bg-green-50 dark:bg-green-900/20',
  },
  {
    state: 'cancelled',
    label: 'Cancelled',
    icon: XCircle,
    iconClass: 'text-red-500',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
  },
];

/**
 * IssueBoard displays issues in a Kanban-style board.
 * Supports drag-and-drop for changing issue states.
 *
 * @example
 * ```tsx
 * <IssueBoard
 *   issuesByState={issueStore.issuesByState}
 *   onIssueClick={(issue) => openIssueModal(issue)}
 *   onIssueDrop={(id, state) => issueStore.updateIssueState(workspaceId, id, state)}
 * />
 * ```
 */
export const IssueBoard = observer(function IssueBoard({
  issuesByState,
  onIssueClick,
  onOpenIssue,
  onIssueDrop,
  onCreateIssue,
  isLoading = false,
  className,
}: IssueBoardProps) {
  const [draggedIssue, setDraggedIssue] = React.useState<Issue | null>(null);
  const [dropTarget, setDropTarget] = React.useState<IssueState | null>(null);

  const handleDragStart = (e: React.DragEvent, issue: Issue) => {
    setDraggedIssue(issue);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', issue.id);
  };

  const handleDragOver = (e: React.DragEvent, state: IssueState) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dropTarget !== state) {
      setDropTarget(state);
    }
  };

  const handleDragLeave = () => {
    setDropTarget(null);
  };

  const handleDrop = (e: React.DragEvent, state: IssueState) => {
    e.preventDefault();
    const issueId = e.dataTransfer.getData('text/plain');
    if (issueId && onIssueDrop && draggedIssue?.state !== state) {
      onIssueDrop(issueId, state);
    }
    setDraggedIssue(null);
    setDropTarget(null);
  };

  return (
    <div className={cn('flex h-full gap-4 overflow-x-auto p-4', className)}>
      {columns.map((column) => {
        const Icon = column.icon;
        const issues = issuesByState[column.state] || [];
        const isDropTarget = dropTarget === column.state;
        const canDrop = draggedIssue && draggedIssue.state !== column.state;

        return (
          <div
            key={column.state}
            className={cn(
              'flex w-72 shrink-0 flex-col rounded-lg border transition-colors',
              column.bgClass,
              isDropTarget && canDrop && 'ring-2 ring-primary ring-offset-2'
            )}
            onDragOver={(e) => handleDragOver(e, column.state)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, column.state)}
          >
            {/* Column header */}
            <div className="flex items-center justify-between border-b p-3">
              <div className="flex items-center gap-2">
                <Icon className={cn('size-4', column.iconClass)} />
                <span className="text-sm font-medium">{column.label}</span>
                <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">
                  {issues.length}
                </span>
              </div>
              {onCreateIssue && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => onCreateIssue(column.state)}
                  className="opacity-0 group-hover:opacity-100 hover:opacity-100"
                >
                  <Plus className="size-4" />
                </Button>
              )}
            </div>

            {/* Column content */}
            <ScrollArea className="flex-1">
              <div className="flex flex-col gap-2 p-2">
                {isLoading ? (
                  // Loading skeleton
                  Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
                  ))
                ) : issues.length > 0 ? (
                  issues.map((issue) => (
                    <IssueCard
                      key={issue.id}
                      issue={issue}
                      onClick={onIssueClick}
                      onOpenIssue={onOpenIssue}
                      onDragStart={handleDragStart}
                      isDragging={draggedIssue?.id === issue.id}
                      compact
                    />
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <p className="text-sm text-muted-foreground">No issues</p>
                    {onCreateIssue && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onCreateIssue(column.state)}
                        className="mt-2"
                      >
                        <Plus className="mr-1 size-4" />
                        Add issue
                      </Button>
                    )}
                  </div>
                )}

                {/* Drop indicator */}
                {isDropTarget && canDrop && (
                  <div className="flex h-20 items-center justify-center rounded-lg border-2 border-dashed border-primary bg-primary/5">
                    <span className="text-sm text-primary">Drop to move here</span>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        );
      })}
    </div>
  );
});

export default IssueBoard;
