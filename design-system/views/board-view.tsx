/**
 * Board View Component
 *
 * Kanban-style board with drag-and-drop functionality.
 * Follows Web Interface Guidelines:
 * - touch-action: manipulation for touch devices
 * - Disable text selection during drag
 * - Mark dragging elements properly
 * - Keyboard accessible column navigation
 */

import * as React from 'react';
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
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { IconPlus } from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { Button } from '../components/button';
import { IssueCard, type Issue, type IssueState } from './issue-card';

// =============================================================================
// TYPES
// =============================================================================

export interface BoardColumn {
  id: IssueState;
  title: string;
  issues: Issue[];
  color?: string;
}

export interface BoardViewProps {
  columns: BoardColumn[];
  onIssueMove: (issueId: string, newState: IssueState, newIndex: number) => void;
  onIssueClick: (issue: Issue) => void;
  onCreateIssue: (state: IssueState) => void;
  isLoading?: boolean;
}

// =============================================================================
// COLUMN HEADER
// =============================================================================

interface ColumnHeaderProps {
  title: string;
  count: number;
  color?: string;
  onAddClick: () => void;
}

function ColumnHeader({ title, count, color, onAddClick }: ColumnHeaderProps) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {color && (
          <div
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: color }}
          />
        )}
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
          {count}
        </span>
      </div>
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onAddClick}
        aria-label={`Add issue to ${title}`}
      >
        <IconPlus className="h-4 w-4" />
      </Button>
    </div>
  );
}

// =============================================================================
// SORTABLE ISSUE CARD
// =============================================================================

interface SortableIssueCardProps {
  issue: Issue;
  onClick: () => void;
}

function SortableIssueCard({ issue, onClick }: SortableIssueCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: issue.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'touch-manipulation',
        isDragging && 'opacity-50'
      )}
      {...attributes}
      {...listeners}
    >
      <IssueCard
        issue={issue}
        isDragging={isDragging}
        showState={false}
        onClick={onClick}
      />
    </div>
  );
}

// =============================================================================
// BOARD COLUMN
// =============================================================================

interface BoardColumnComponentProps {
  column: BoardColumn;
  onIssueClick: (issue: Issue) => void;
  onCreateIssue: () => void;
  isOver?: boolean;
}

function BoardColumnComponent({
  column,
  onIssueClick,
  onCreateIssue,
  isOver,
}: BoardColumnComponentProps) {
  const columnColors: Record<IssueState, string> = {
    backlog: 'hsl(240 5% 64.9%)',
    todo: 'hsl(217.2 91.2% 59.8%)',
    'in-progress': 'hsl(24.6 95% 53.1%)',
    'in-review': 'hsl(262.1 83.3% 57.8%)',
    done: 'hsl(142.1 76.2% 36.3%)',
    cancelled: 'hsl(0 84.2% 60.2%)',
  };

  return (
    <div
      className={cn(
        'flex w-board-column min-w-board-column max-w-board-column flex-shrink-0 flex-col',
        'rounded-lg bg-muted/50 p-2',
        isOver && 'ring-2 ring-primary ring-offset-2'
      )}
    >
      <ColumnHeader
        title={column.title}
        count={column.issues.length}
        color={column.color || columnColors[column.id]}
        onAddClick={onCreateIssue}
      />

      <SortableContext
        items={column.issues.map((i) => i.id)}
        strategy={verticalListSortingStrategy}
      >
        <div
          className={cn(
            'flex min-h-[200px] flex-1 flex-col gap-2 overflow-y-auto rounded-md p-1',
            isOver && 'bg-primary/5'
          )}
          role="list"
          aria-label={`${column.title} issues`}
        >
          {column.issues.map((issue) => (
            <SortableIssueCard
              key={issue.id}
              issue={issue}
              onClick={() => onIssueClick(issue)}
            />
          ))}

          {column.issues.length === 0 && (
            <div className="flex flex-1 items-center justify-center py-8">
              <p className="text-sm text-muted-foreground">No issues</p>
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// =============================================================================
// MAIN BOARD VIEW
// =============================================================================

export function BoardView({
  columns,
  onIssueMove,
  onIssueClick,
  onCreateIssue,
  isLoading,
}: BoardViewProps) {
  const [activeIssue, setActiveIssue] = React.useState<Issue | null>(null);
  const [overColumnId, setOverColumnId] = React.useState<IssueState | null>(null);

  // Sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Prevent accidental drags
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Find issue by ID across all columns
  const findIssue = (id: string): Issue | undefined => {
    for (const column of columns) {
      const issue = column.issues.find((i) => i.id === id);
      if (issue) return issue;
    }
    return undefined;
  };

  // Find column containing issue
  const findColumnByIssueId = (id: string): BoardColumn | undefined => {
    return columns.find((col) => col.issues.some((i) => i.id === id));
  };

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const issue = findIssue(event.active.id as string);
    if (issue) {
      setActiveIssue(issue);
      // Add class to body to disable text selection during drag
      document.body.classList.add('no-select');
    }
  };

  // Handle drag over (for visual feedback)
  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (over) {
      // Check if over a column or an issue in a column
      const overColumn = columns.find((col) => col.id === over.id);
      if (overColumn) {
        setOverColumnId(overColumn.id);
      } else {
        const column = findColumnByIssueId(over.id as string);
        setOverColumnId(column?.id || null);
      }
    } else {
      setOverColumnId(null);
    }
  };

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    setActiveIssue(null);
    setOverColumnId(null);
    document.body.classList.remove('no-select');

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Find source and destination
    const sourceColumn = findColumnByIssueId(activeId);
    let destColumn = columns.find((col) => col.id === overId);

    if (!destColumn) {
      destColumn = findColumnByIssueId(overId);
    }

    if (!sourceColumn || !destColumn) return;

    // Calculate new index
    const destIndex = destColumn.issues.findIndex((i) => i.id === overId);
    const newIndex = destIndex === -1 ? destColumn.issues.length : destIndex;

    // Trigger move callback
    onIssueMove(activeId, destColumn.id, newIndex);
  };

  // Handle drag cancel
  const handleDragCancel = () => {
    setActiveIssue(null);
    setOverColumnId(null);
    document.body.classList.remove('no-select');
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <div
        className="flex gap-4 overflow-x-auto pb-4"
        role="region"
        aria-label="Issue board"
      >
        {columns.map((column) => (
          <BoardColumnComponent
            key={column.id}
            column={column}
            onIssueClick={onIssueClick}
            onCreateIssue={() => onCreateIssue(column.id)}
            isOver={overColumnId === column.id}
          />
        ))}
      </div>

      {/* Drag overlay - follows cursor */}
      <DragOverlay>
        {activeIssue && (
          <IssueCard
            issue={activeIssue}
            isDragging
            showState={false}
            className="cursor-grabbing"
          />
        )}
      </DragOverlay>
    </DndContext>
  );
}

// =============================================================================
// BOARD VIEW HEADER
// =============================================================================

export interface BoardViewHeaderProps {
  viewType: 'board' | 'list' | 'calendar';
  onViewChange: (view: 'board' | 'list' | 'calendar') => void;
  filterCount?: number;
  onFilterClick?: () => void;
  onSearchChange?: (query: string) => void;
}

export function BoardViewHeader({
  viewType,
  onViewChange,
  filterCount,
  onFilterClick,
  onSearchChange,
}: BoardViewHeaderProps) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <div className="flex items-center gap-2">
        {/* View type toggle */}
        <div className="flex rounded-lg border bg-muted p-1">
          {(['board', 'list', 'calendar'] as const).map((view) => (
            <button
              key={view}
              onClick={() => onViewChange(view)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                viewType === view
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
              aria-pressed={viewType === view}
            >
              {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>

        {/* Filter button */}
        {onFilterClick && (
          <Button variant="outline" size="sm" onClick={onFilterClick}>
            Filters
            {filterCount !== undefined && filterCount > 0 && (
              <span className="ml-1 rounded-full bg-primary px-1.5 text-xs text-primary-foreground">
                {filterCount}
              </span>
            )}
          </Button>
        )}
      </div>

      {/* Search */}
      {onSearchChange && (
        <input
          type="search"
          placeholder="Search issues..."
          className={cn(
            'h-9 w-64 rounded-md border border-input bg-background px-3 text-sm',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
          )}
          onChange={(e) => onSearchChange(e.target.value)}
          aria-label="Search issues"
        />
      )}
    </div>
  );
}
