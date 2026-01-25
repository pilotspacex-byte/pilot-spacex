'use client';

/**
 * TaskChecklist - Display AI-generated task checklist for an issue.
 *
 * T213: Shows checkbox list with descriptions, effort estimates,
 * dependency indicators, and actions to create as sub-issues.
 */

import * as React from 'react';
import { GripVertical, Plus, Link2, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// ============================================================================
// Types
// ============================================================================

export type EffortSize = 'S' | 'M' | 'L' | 'XL';

export interface TaskItem {
  /** Unique identifier */
  id: string;
  /** Task title */
  title: string;
  /** Task description */
  description?: string;
  /** Effort estimate */
  effort: EffortSize;
  /** Estimated hours */
  estimatedHours?: number;
  /** Whether task is completed */
  completed: boolean;
  /** Dependencies (task IDs) */
  dependsOn?: string[];
  /** Order index for sorting */
  order: number;
}

export interface TaskChecklistProps {
  /** List of tasks */
  tasks: TaskItem[];
  /** Called when task completion changes */
  onTaskToggle?: (taskId: string, completed: boolean) => void;
  /** Called when tasks are reordered */
  onReorder?: (tasks: TaskItem[]) => void;
  /** Called to create sub-issues from tasks */
  onCreateSubIssues?: (taskIds: string[]) => void;
  /** Whether the component is read-only */
  readOnly?: boolean;
  /** Whether the section is collapsible */
  collapsible?: boolean;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Effort Badge Configuration
// ============================================================================

interface EffortConfig {
  label: string;
  color: string;
  hours: string;
}

const effortConfig: Record<EffortSize, EffortConfig> = {
  S: {
    label: 'S',
    color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    hours: '1-2h',
  },
  M: {
    label: 'M',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    hours: '2-4h',
  },
  L: {
    label: 'L',
    color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    hours: '4-8h',
  },
  XL: {
    label: 'XL',
    color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    hours: '8h+',
  },
};

// ============================================================================
// Task Row Component
// ============================================================================

interface TaskRowProps {
  task: TaskItem;
  tasks: TaskItem[];
  onToggle?: (taskId: string, completed: boolean) => void;
  readOnly?: boolean;
  isDragging?: boolean;
}

function TaskRow({ task, tasks, onToggle, readOnly, isDragging }: TaskRowProps) {
  const effort = effortConfig[task.effort];
  const hasDependencies = task.dependsOn && task.dependsOn.length > 0;

  // Check if dependencies are met
  const dependenciesMet =
    !hasDependencies ||
    task.dependsOn!.every((depId) => tasks.find((t) => t.id === depId)?.completed);

  // Get dependency names
  const dependencyNames = task.dependsOn?.map(
    (depId) => tasks.find((t) => t.id === depId)?.title || depId
  );

  return (
    <div
      className={cn(
        'group flex items-start gap-3 rounded-lg border p-3 transition-colors',
        task.completed && 'bg-muted/30',
        !dependenciesMet && 'opacity-60',
        isDragging && 'shadow-lg bg-background'
      )}
    >
      {/* Drag handle */}
      {!readOnly && (
        <GripVertical className="size-4 shrink-0 mt-0.5 text-muted-foreground opacity-0 group-hover:opacity-100 cursor-grab transition-opacity" />
      )}

      {/* Checkbox */}
      <Checkbox
        checked={task.completed}
        onCheckedChange={(checked) => {
          if (!readOnly && dependenciesMet) {
            onToggle?.(task.id, !!checked);
          }
        }}
        disabled={readOnly || !dependenciesMet}
        className="mt-0.5"
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'text-sm font-medium',
              task.completed && 'line-through text-muted-foreground'
            )}
          >
            {task.title}
          </span>

          {/* Effort badge */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="outline" className={cn('text-xs', effort.color)}>
                  {effort.label}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>Estimated: {task.estimatedHours ? `${task.estimatedHours}h` : effort.hours}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Dependency indicator */}
          {hasDependencies && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className={cn(
                      'text-xs gap-1',
                      dependenciesMet
                        ? 'text-green-600 border-green-300 dark:text-green-400 dark:border-green-800'
                        : 'text-orange-600 border-orange-300 dark:text-orange-400 dark:border-orange-800'
                    )}
                  >
                    <Link2 className="size-3" />
                    {task.dependsOn!.length}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="space-y-1">
                    <p className="font-medium">
                      {dependenciesMet ? 'Dependencies met' : 'Waiting for:'}
                    </p>
                    <ul className="text-xs">
                      {dependencyNames?.map((name, i) => (
                        <li key={i}>- {name}</li>
                      ))}
                    </ul>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Description */}
        {task.description && (
          <p className={cn('mt-1 text-xs text-muted-foreground', task.completed && 'line-through')}>
            {task.description}
          </p>
        )}
      </div>

      {/* Estimated hours */}
      {task.estimatedHours && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
          <Clock className="size-3" />
          {task.estimatedHours}h
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function TaskChecklist({
  tasks,
  onTaskToggle,
  onReorder: _onReorder,
  onCreateSubIssues,
  readOnly = false,
  collapsible = true,
  defaultCollapsed = false,
  className,
}: TaskChecklistProps) {
  // onReorder is available for future drag-and-drop implementation with @dnd-kit
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [selectedTasks, setSelectedTasks] = React.useState<Set<string>>(new Set());

  // Sort tasks by order
  const sortedTasks = React.useMemo(() => [...tasks].sort((a, b) => a.order - b.order), [tasks]);

  // Calculate progress
  const completedCount = tasks.filter((t) => t.completed).length;
  const progressPercentage = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  // Calculate total estimated hours
  const totalHours = tasks.reduce((sum, t) => sum + (t.estimatedHours || 0), 0);
  const completedHours = tasks
    .filter((t) => t.completed)
    .reduce((sum, t) => sum + (t.estimatedHours || 0), 0);

  /* Future: Task selection for sub-issue creation
   * const toggleTaskSelection = (taskId: string) => {
   *   setSelectedTasks((prev) => {
   *     const next = new Set(prev);
   *     if (next.has(taskId)) next.delete(taskId);
   *     else next.add(taskId);
   *     return next;
   *   });
   * };
   */

  const handleCreateSubIssues = () => {
    if (selectedTasks.size > 0 && onCreateSubIssues) {
      onCreateSubIssues(Array.from(selectedTasks));
      setSelectedTasks(new Set());
    }
  };

  if (tasks.length === 0) {
    return null;
  }

  const header = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {collapsible &&
          (isCollapsed ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />)}
        <span className="text-sm font-medium">Tasks</span>
        <Badge variant="secondary" className="text-xs">
          {completedCount}/{tasks.length}
        </Badge>
      </div>

      {!isCollapsed && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="size-3" />
          {completedHours}/{totalHours}h
        </div>
      )}
    </div>
  );

  const content = (
    <div className="space-y-4 mt-3">
      {/* Progress bar */}
      <div className="space-y-1">
        <Progress value={progressPercentage} className="h-2" />
        <p className="text-xs text-muted-foreground text-right">
          {Math.round(progressPercentage)}% complete
        </p>
      </div>

      {/* Task list */}
      <div className="space-y-2">
        {sortedTasks.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            tasks={sortedTasks}
            onToggle={onTaskToggle}
            readOnly={readOnly}
          />
        ))}
      </div>

      {/* Actions */}
      {!readOnly && onCreateSubIssues && (
        <div className="flex items-center justify-between pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            {selectedTasks.size > 0
              ? `${selectedTasks.size} task${selectedTasks.size > 1 ? 's' : ''} selected`
              : 'Select tasks to create as sub-issues'}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCreateSubIssues}
            disabled={selectedTasks.size === 0}
          >
            <Plus className="size-4 mr-1" />
            Create Sub-Issues
          </Button>
        </div>
      )}
    </div>
  );

  if (collapsible) {
    return (
      <Collapsible
        open={!isCollapsed}
        onOpenChange={(open) => setIsCollapsed(!open)}
        className={className}
      >
        <CollapsibleTrigger className="w-full text-left">{header}</CollapsibleTrigger>
        <CollapsibleContent>{content}</CollapsibleContent>
      </Collapsible>
    );
  }

  return (
    <div className={className}>
      {header}
      {content}
    </div>
  );
}

export default TaskChecklist;
