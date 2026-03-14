'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { CircleDashed, Circle, PlayCircle, CircleDot, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIssueViewStore } from '@/stores/RootStore';
import { DroppableColumn } from './DroppableColumn';
import { DraggableCard } from './DraggableCard';
import type { Issue, IssueState } from '@/types';

const BOARD_COLUMNS = [
  {
    state: 'backlog',
    label: 'Backlog',
    icon: CircleDashed,
    iconClass: 'text-[var(--color-state-backlog)]',
    bgClass: 'bg-[var(--color-state-backlog)]/8',
  },
  {
    state: 'todo',
    label: 'Todo',
    icon: Circle,
    iconClass: 'text-[var(--color-state-todo)]',
    bgClass: 'bg-[var(--color-state-todo)]/8',
  },
  {
    state: 'in_progress',
    label: 'In Progress',
    icon: PlayCircle,
    iconClass: 'text-[var(--color-state-in-progress)]',
    bgClass: 'bg-[var(--color-state-in-progress)]/8',
  },
  {
    state: 'in_review',
    label: 'In Review',
    icon: CircleDot,
    iconClass: 'text-[var(--color-state-in-review)]',
    bgClass: 'bg-[var(--color-state-in-review)]/8',
  },
  {
    state: 'done',
    label: 'Done',
    icon: CheckCircle2,
    iconClass: 'text-[var(--color-state-done)]',
    bgClass: 'bg-[var(--color-state-done)]/8',
  },
  {
    state: 'cancelled',
    label: 'Cancelled',
    icon: XCircle,
    iconClass: 'text-[var(--color-state-cancelled)]',
    bgClass: 'bg-[var(--color-state-cancelled)]/8',
  },
] as const;

function getIssueState(issue: Issue): string {
  return issue.state?.name?.toLowerCase().replace(/\s+/g, '_') ?? 'backlog';
}

interface BoardViewProps {
  issues: Issue[];
  isLoading: boolean;
  onIssueClick?: (issue: Issue) => void;
  onIssueDrop?: (issueId: string, newState: IssueState) => void;
  onCreateIssue?: (state: IssueState, name: string) => void;
  className?: string;
}

export const BoardView = observer(function BoardView({
  issues,
  isLoading,
  onIssueClick,
  onIssueDrop,
  onCreateIssue,
  className,
}: BoardViewProps) {
  const viewStore = useIssueViewStore();
  const [activeId, setActiveId] = React.useState<string | null>(null);

  const issuesByState = React.useMemo(() => {
    const map: Record<string, Issue[]> = {};
    for (const col of BOARD_COLUMNS) {
      map[col.state] = [];
    }
    for (const issue of issues) {
      const state = getIssueState(issue);
      const bucket = map[state] ?? map['backlog']!;
      bucket.push(issue);
    }
    return map;
  }, [issues]);

  const activeIssue = React.useMemo(() => {
    if (!activeId) return null;
    return issues.find((i) => i.id === activeId) ?? null;
  }, [activeId, issues]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    if (!over || !onIssueDrop) return;

    const draggedId = active.id as string;
    const overId = over.id as string;

    let targetState: IssueState | null = null;

    if (overId.startsWith('column-')) {
      targetState = overId.replace('column-', '') as IssueState;
    } else {
      for (const [state, stateIssues] of Object.entries(issuesByState)) {
        if (stateIssues.some((i) => i.id === overId)) {
          targetState = state as IssueState;
          break;
        }
      }
    }

    if (!targetState) return;

    const draggedIssue = issues.find((i) => i.id === draggedId);
    if (!draggedIssue) return;

    const currentState = getIssueState(draggedIssue);
    if (targetState !== currentState) {
      onIssueDrop(draggedId, targetState);
    }
  };

  if (isLoading) {
    return (
      <div className={cn('flex h-full gap-3 overflow-x-auto p-3', className)}>
        {BOARD_COLUMNS.map((col) => (
          <div
            key={col.state}
            className={cn('flex w-72 shrink-0 flex-col rounded-lg border p-2', col.bgClass)}
          >
            <div className="flex items-center gap-1.5 mb-2">
              <col.icon className={cn('size-3.5', col.iconClass)} />
              <span className="text-xs font-medium">{col.label}</span>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="mb-1.5 h-20 animate-pulse rounded-lg bg-muted" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="relative">
        <div className={cn('flex h-full gap-3 overflow-x-auto p-3', className)}>
          {BOARD_COLUMNS.map((col) => (
            <DroppableColumn
              key={col.state}
              column={col}
              issues={issuesByState[col.state] ?? []}
              density={viewStore.cardDensity}
              isCollapsed={viewStore.collapsedColumns.has(col.state)}
              wipLimit={viewStore.wipLimits.get(col.state)}
              isLoading={false}
              onToggleCollapse={() => viewStore.toggleColumnCollapsed(col.state)}
              onIssueClick={onIssueClick}
              onCreateIssue={
                onCreateIssue ? (name) => onCreateIssue(col.state as IssueState, name) : undefined
              }
            />
          ))}
        </div>
        {/* Right-edge fade indicator for horizontal scroll */}
        <div
          className="pointer-events-none absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-background to-transparent"
          aria-hidden="true"
        />
      </div>

      <DragOverlay>
        {activeIssue ? (
          <DraggableCard issue={activeIssue} density={viewStore.cardDensity} isOverlay />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
});
