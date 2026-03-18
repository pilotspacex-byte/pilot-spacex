'use client';

import * as React from 'react';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ColumnHeader } from './ColumnHeader';
import { CollapsedColumn } from './CollapsedColumn';
import { DraggableCard } from './DraggableCard';
import { QuickAddInput } from './QuickAddInput';
import type { Issue } from '@/types';
import type { IssueCardDensity } from '@/components/issues/IssueCard';

interface ColumnConfig {
  state: string;
  label: string;
  icon: React.ElementType;
  iconClass: string;
  bgClass: string;
}

interface DroppableColumnProps {
  column: ColumnConfig;
  issues: Issue[];
  density: IssueCardDensity;
  isCollapsed: boolean;
  wipLimit?: number;
  isLoading: boolean;
  onToggleCollapse: () => void;
  onIssueClick?: (issue: Issue) => void;
  onCreateIssue?: (name: string) => void;
}

export function DroppableColumn({
  column,
  issues,
  density,
  isCollapsed,
  wipLimit,
  isLoading,
  onToggleCollapse,
  onIssueClick,
  onCreateIssue,
}: DroppableColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: `column-${column.state}` });

  if (isCollapsed) {
    return (
      <CollapsedColumn
        icon={column.icon}
        iconClass={column.iconClass}
        label={column.label}
        count={issues.length}
        onExpand={onToggleCollapse}
      />
    );
  }

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'group flex w-72 shrink-0 flex-col rounded-lg border transition-all',
        column.bgClass,
        isOver && 'ring-2 ring-primary ring-offset-2'
      )}
      data-column={column.state}
    >
      <ColumnHeader
        icon={column.icon}
        iconClass={column.iconClass}
        label={column.label}
        count={issues.length}
        wipLimit={wipLimit}
        isCollapsed={false}
        onToggleCollapse={onToggleCollapse}
        onAdd={onCreateIssue ? () => {} : undefined}
      />

      <ScrollArea className="min-h-0 flex-1">
        <SortableContext items={issues.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-1.5 p-1.5 min-h-[200px]">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
              ))
            ) : issues.length > 0 ? (
              issues.map((issue) => (
                <DraggableCard
                  key={issue.id}
                  issue={issue}
                  density={density}
                  onClick={onIssueClick}
                />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-xs text-muted-foreground">
                <p>No issues in this column</p>
                <p className="mt-0.5 text-muted-foreground/50">
                  Drag issues here or create new ones
                </p>
              </div>
            )}
          </div>
        </SortableContext>
      </ScrollArea>

      {onCreateIssue && <QuickAddInput onSubmit={onCreateIssue} className="border-t" />}
    </div>
  );
}
