'use client';

/**
 * CycleBoard - Sprint/Cycle Kanban board with drag-drop support.
 *
 * T165: Displays issues in a cycle grouped by state with drag-drop
 * for state transitions.
 *
 * @example
 * ```tsx
 * <CycleBoard
 *   issuesByState={cycleStore.issuesByState}
 *   onIssueClick={(issue) => openIssueModal(issue)}
 *   onIssueDrop={(issueId, newState) => handleStateChange(issueId, newState)}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  CircleDashed,
  Circle,
  PlayCircle,
  CircleDot,
  CheckCircle2,
  XCircle,
  Plus,
  Users,
  GripVertical,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { IssueCard } from '@/components/issues/IssueCard';
import type { Issue, IssueState, UserBrief } from '@/types';
import type { CycleIssue } from '@/stores/features/cycles';

// ============================================================================
// Types
// ============================================================================

export interface CycleBoardProps {
  /** Issues grouped by state */
  issuesByState: Record<IssueState, CycleIssue[]>;
  /** Called when an issue is clicked */
  onIssueClick?: (issue: Issue) => void;
  /** Called when an issue is dropped on a column (state change) */
  onIssueDrop?: (issueId: string, newState: IssueState) => void;
  /** Called when creating a new issue in a column */
  onCreateIssue?: (state: IssueState) => void;
  /** Called to add issue from backlog */
  onAddIssue?: () => void;
  /** Whether the board is loading */
  isLoading?: boolean;
  /** Show swimlanes grouped by assignee */
  showSwimlanes?: boolean;
  /** Exclude certain columns */
  excludeColumns?: IssueState[];
  className?: string;
}

interface ColumnConfig {
  state: IssueState;
  label: string;
  icon: React.ElementType;
  iconClass: string;
  bgClass: string;
}

// ============================================================================
// Constants
// ============================================================================

const defaultColumns: ColumnConfig[] = [
  {
    state: 'backlog',
    label: 'Backlog',
    icon: CircleDashed,
    iconClass: 'text-muted-foreground',
    bgClass: 'bg-background-subtle',
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

// ============================================================================
// Helper Functions
// ============================================================================

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// ============================================================================
// Sortable Issue Card
// ============================================================================

interface SortableIssueCardProps {
  issue: CycleIssue;
  onClick?: (issue: Issue) => void;
  isOverlay?: boolean;
}

function SortableIssueCard({ issue, onClick, isOverlay = false }: SortableIssueCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: issue.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'group relative',
        isDragging && !isOverlay && 'opacity-30',
        isOverlay && 'shadow-lg rotate-2'
      )}
    >
      {/* Drag handle */}
      <div
        {...attributes}
        {...listeners}
        className={cn(
          'absolute left-0 top-0 bottom-0 w-6 flex items-center justify-center',
          'opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing',
          'rounded-l-lg hover:bg-muted/50 transition-opacity',
          isOverlay && 'opacity-100'
        )}
      >
        <GripVertical className="size-4 text-muted-foreground" />
      </div>

      <div className="pl-4">
        <IssueCard issue={issue} onClick={onClick} isDragging={isDragging} compact />
      </div>
    </div>
  );
}

// ============================================================================
// Board Column
// ============================================================================

interface BoardColumnProps {
  column: ColumnConfig;
  issues: CycleIssue[];
  onIssueClick?: (issue: Issue) => void;
  onCreateIssue?: (state: IssueState) => void;
  isDropTarget: boolean;
  isLoading: boolean;
}

const BoardColumn = React.memo(function BoardColumn({
  column,
  issues,
  onIssueClick,
  onCreateIssue,
  isDropTarget,
  isLoading,
}: BoardColumnProps) {
  const Icon = column.icon;

  return (
    <div
      className={cn(
        'flex w-72 shrink-0 flex-col rounded-lg border transition-all',
        column.bgClass,
        isDropTarget && 'ring-2 ring-primary ring-offset-2'
      )}
      data-column={column.state}
    >
      {/* Column header */}
      <div className="flex items-center justify-between border-b p-2">
        <div className="flex items-center gap-1.5">
          <Icon className={cn('size-3.5', column.iconClass)} />
          <span className="text-xs font-medium">{column.label}</span>
          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium">
            {issues.length}
          </span>
        </div>
        {onCreateIssue && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onCreateIssue(column.state)}
            className="size-6 opacity-0 group-hover:opacity-100 hover:opacity-100"
          >
            <Plus className="size-4" />
          </Button>
        )}
      </div>

      {/* Column content */}
      <ScrollArea className="flex-1">
        <SortableContext items={issues.map((i) => i.id)} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-1.5 p-1.5 min-h-[200px]">
            {isLoading ? (
              // Loading skeleton
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
              ))
            ) : issues.length > 0 ? (
              issues.map((issue) => (
                <SortableIssueCard key={issue.id} issue={issue} onClick={onIssueClick} />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <p className="text-xs text-muted-foreground">No issues</p>
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
          </div>
        </SortableContext>
      </ScrollArea>
    </div>
  );
});

// ============================================================================
// Swimlane Row
// ============================================================================

interface SwimlaneRowProps {
  assignee: UserBrief | null;
  assigneeId: string | null;
  columns: ColumnConfig[];
  issuesByState: Record<IssueState, CycleIssue[]>;
  onIssueClick?: (issue: Issue) => void;
  dropTarget: IssueState | null;
  isLoading: boolean;
}

const SwimlaneRow = React.memo(function SwimlaneRow({
  assignee,
  assigneeId,
  columns,
  issuesByState,
  onIssueClick,
  dropTarget,
  isLoading,
}: SwimlaneRowProps) {
  return (
    <div className="border-b last:border-b-0">
      {/* Swimlane header */}
      <div className="flex items-center gap-2 bg-muted/30 px-3 py-1.5 sticky left-0">
        {assignee ? (
          <>
            <Avatar className="size-5">
              <AvatarFallback className="text-[10px]">
                {getInitials(assignee.displayName ?? assignee.email)}
              </AvatarFallback>
            </Avatar>
            <span className="text-xs font-medium">{assignee.displayName ?? assignee.email}</span>
          </>
        ) : (
          <>
            <Users className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">Unassigned</span>
          </>
        )}
      </div>

      {/* Swimlane columns */}
      <div className="flex gap-3 p-3 overflow-x-auto">
        {columns.map((column) => {
          const issues = (issuesByState[column.state] ?? []).filter(
            (i) => (i.assigneeId ?? null) === assigneeId
          );
          return (
            <div key={column.state} className="w-64 shrink-0">
              <SortableContext
                items={issues.map((i) => i.id)}
                strategy={verticalListSortingStrategy}
              >
                <div
                  className={cn(
                    'flex flex-col gap-1.5 p-1.5 min-h-[100px] rounded-lg',
                    column.bgClass,
                    dropTarget === column.state && 'ring-2 ring-primary ring-offset-1'
                  )}
                >
                  {isLoading ? (
                    <div className="h-16 animate-pulse rounded-lg bg-muted" />
                  ) : issues.length > 0 ? (
                    issues.map((issue) => (
                      <SortableIssueCard key={issue.id} issue={issue} onClick={onIssueClick} />
                    ))
                  ) : (
                    <div className="flex items-center justify-center h-16 text-[10px] text-muted-foreground">
                      Drop here
                    </div>
                  )}
                </div>
              </SortableContext>
            </div>
          );
        })}
      </div>
    </div>
  );
});

// ============================================================================
// Main Component
// ============================================================================

export const CycleBoard = observer(function CycleBoard({
  issuesByState,
  onIssueClick,
  onIssueDrop,
  onCreateIssue,
  onAddIssue,
  isLoading = false,
  showSwimlanes = false,
  excludeColumns = [],
  className,
}: CycleBoardProps) {
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [dropTarget, setDropTarget] = React.useState<IssueState | null>(null);

  // Get active item for drag overlay
  const activeItem = React.useMemo(() => {
    if (!activeId) return null;
    for (const issues of Object.values(issuesByState)) {
      const found = issues.find((i) => i.id === activeId);
      if (found) return found;
    }
    return null;
  }, [activeId, issuesByState]);

  // Filter columns
  const columns = React.useMemo(
    () => defaultColumns.filter((c) => !excludeColumns.includes(c.state)),
    [excludeColumns]
  );

  // Get unique assignees for swimlane view
  const assignees = React.useMemo(() => {
    if (!showSwimlanes) return [];

    const allIssues = Object.values(issuesByState).flat();
    const assigneeMap = new Map<string | null, UserBrief | null>();

    allIssues.forEach((issue) => {
      const id = issue.assigneeId ?? null;
      if (!assigneeMap.has(id)) {
        assigneeMap.set(id, issue.assignee ?? null);
      }
    });

    // Sort: assigned users first, then unassigned
    return Array.from(assigneeMap.entries()).sort((a, b) => {
      if (a[0] === null && b[0] !== null) return 1;
      if (a[0] !== null && b[0] === null) return -1;
      return (a[1]?.displayName ?? a[1]?.email ?? '').localeCompare(
        b[1]?.displayName ?? b[1]?.email ?? ''
      );
    });
  }, [showSwimlanes, issuesByState]);

  // Sensors for drag-drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Handlers
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (!over) {
      setDropTarget(null);
      return;
    }

    // Determine which column we're over
    const overElement = document.querySelector(`[data-column]`);
    if (overElement) {
      const column = overElement.getAttribute('data-column') as IssueState;
      setDropTarget(column);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setDropTarget(null);

    if (!over || !onIssueDrop) return;

    const activeId = active.id as string;

    // Find the target state based on where the item was dropped
    let targetState: IssueState | null = null;

    // Check if dropped on another issue
    for (const [state, issues] of Object.entries(issuesByState)) {
      if (issues.some((i) => i.id === over.id)) {
        targetState = state as IssueState;
        break;
      }
    }

    // If dropped on column itself (check container ID)
    if (!targetState && typeof over.id === 'string') {
      const overId = over.id as string;
      const state = columns.find((c) => overId.includes(c.state));
      if (state) {
        targetState = state.state;
      }
    }

    // Find current state of the dragged issue
    let currentState: IssueState | null = null;
    for (const [state, issues] of Object.entries(issuesByState)) {
      if (issues.some((i) => i.id === activeId)) {
        currentState = state as IssueState;
        break;
      }
    }

    // Only trigger if state changed
    if (targetState && currentState && targetState !== currentState) {
      onIssueDrop(activeId, targetState);
    }
  };

  // Render swimlane view
  if (showSwimlanes) {
    return (
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className={cn('flex flex-col h-full overflow-auto', className)}>
          {/* Column headers */}
          <div className="flex items-center gap-3 px-3 py-1.5 border-b bg-background sticky top-0 z-10">
            <div className="w-40 shrink-0" />
            {columns.map((column) => {
              const Icon = column.icon;
              const count = issuesByState[column.state]?.length ?? 0;
              return (
                <div key={column.state} className="w-64 shrink-0 flex items-center gap-1.5">
                  <Icon className={cn('size-3.5', column.iconClass)} />
                  <span className="text-xs font-medium">{column.label}</span>
                  <span className="text-[10px] text-muted-foreground">({count})</span>
                </div>
              );
            })}
          </div>

          {/* Swimlane rows */}
          {assignees.map(([assigneeId, assignee]) => (
            <SwimlaneRow
              key={assigneeId ?? 'unassigned'}
              assignee={assignee}
              assigneeId={assigneeId}
              columns={columns}
              issuesByState={issuesByState}
              onIssueClick={onIssueClick}
              dropTarget={dropTarget}
              isLoading={isLoading}
            />
          ))}

          {assignees.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-muted-foreground">No issues in this cycle</p>
              {onAddIssue && (
                <Button variant="outline" className="mt-4" onClick={onAddIssue}>
                  <Plus className="mr-2 size-4" />
                  Add issues to cycle
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Drag overlay */}
        <DragOverlay>
          {activeItem ? <SortableIssueCard issue={activeItem} isOverlay /> : null}
        </DragOverlay>
      </DndContext>
    );
  }

  // Standard column view
  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className={cn('flex h-full gap-3 overflow-x-auto p-3', className)}>
        {columns.map((column) => (
          <BoardColumn
            key={column.state}
            column={column}
            issues={issuesByState[column.state] ?? []}
            onIssueClick={onIssueClick}
            onCreateIssue={onCreateIssue}
            isDropTarget={dropTarget === column.state}
            isLoading={isLoading}
          />
        ))}
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activeItem ? <SortableIssueCard issue={activeItem} isOverlay /> : null}
      </DragOverlay>
    </DndContext>
  );
});

export default CycleBoard;
