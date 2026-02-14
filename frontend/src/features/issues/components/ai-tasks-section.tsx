'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  ChevronDown,
  ChevronRight,
  Sparkles,
  ListChecks,
  FileCode,
  Clock,
  Loader2,
  Wand2,
  GripVertical,
} from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useTaskStore, useWorkspaceStore } from '@/stores';
import { PromptBlock } from './prompt-block';
import { TaskDependencyGraph } from './task-dependency-graph';
import type { ContextTask, ContextPrompt } from '@/stores/ai/AIContextStore';
import type { Task } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface AITasksSectionProps {
  /** Legacy AI context tasks (from AIContextStore) */
  tasks: ContextTask[];
  /** Ready-to-use prompts */
  prompts: ContextPrompt[];
  /** Callback for legacy task toggle */
  onTaskToggle?: (taskId: number, completed: boolean) => void;
  /** Issue ID to load persistent tasks from TaskStore */
  issueId?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

interface TaskProgressBarProps {
  completed: number;
  total: number;
}

function TaskProgressBar({ completed, total }: TaskProgressBarProps) {
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100);

  return (
    <div className="flex items-center gap-3">
      <Progress
        value={percent}
        className="h-2 flex-1"
        role="progressbar"
        aria-valuenow={completed}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-label={`Task progress: ${completed} of ${total} completed`}
      />
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {completed}/{total}
      </span>
    </div>
  );
}

// ============================================================================
// Persistent task item (from TaskStore)
// ============================================================================

interface PersistentTaskItemProps {
  task: Task;
  workspaceId: string;
  issueId: string;
  isDragging: boolean;
  isDragOver: boolean;
  editingTaskId: string | null;
  editValue: string;
  onEditStart: (taskId: string, title: string) => void;
  onEditChange: (value: string) => void;
  onEditSave: () => void;
  onEditCancel: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onDragEnd: () => void;
}

const PersistentTaskItem = observer(function PersistentTaskItem({
  task,
  workspaceId,
  issueId,
  isDragging,
  isDragOver,
  editingTaskId,
  editValue,
  onEditStart,
  onEditChange,
  onEditSave,
  onEditCancel,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: PersistentTaskItemProps) {
  const taskStore = useTaskStore();
  const [expanded, setExpanded] = React.useState(false);
  const editInputRef = React.useRef<HTMLInputElement>(null);
  const isDone = task.status === 'done';
  const isEditing = editingTaskId === task.id;

  const handleToggle = React.useCallback(() => {
    const nextStatus = isDone ? 'todo' : 'done';
    void taskStore.updateStatus(workspaceId, task.id, issueId, nextStatus);
  }, [isDone, taskStore, workspaceId, task.id, issueId]);

  React.useEffect(() => {
    if (isEditing && editInputRef.current) {
      editInputRef.current.focus();
    }
  }, [isEditing]);

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        onEditSave();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onEditCancel();
      }
    },
    [onEditSave, onEditCancel]
  );

  const hasExpandableContent =
    task.description || task.acceptanceCriteria.length > 0 || task.codeReferences.length > 0;

  return (
    <li
      className={cn(
        'rounded-lg border border-border bg-background p-3 transition-all group',
        isDragging && 'shadow-md border-ai/60 opacity-70',
        isDragOver && 'border-t-2 border-t-ai'
      )}
      draggable
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onDragEnd={onDragEnd}
    >
      <div className="flex items-start gap-2.5">
        <GripVertical
          className="size-4 mt-0.5 text-muted-foreground/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab shrink-0"
          aria-hidden="true"
        />
        <Checkbox
          checked={isDone}
          onCheckedChange={handleToggle}
          aria-label={`Mark "${task.title}" as ${isDone ? 'incomplete' : 'complete'}`}
          className="mt-0.5"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isEditing ? (
              <input
                ref={editInputRef}
                type="text"
                value={editValue}
                onChange={(e) => onEditChange(e.target.value)}
                onBlur={onEditSave}
                onKeyDown={handleKeyDown}
                className="text-sm bg-transparent border-b-2 border-ai outline-none w-full py-0.5"
                aria-label="Edit task title"
              />
            ) : (
              <button
                type="button"
                onClick={() => onEditStart(task.id, task.title)}
                className={cn(
                  'text-sm text-left hover:underline cursor-text',
                  isDone && 'line-through text-muted-foreground'
                )}
              >
                {task.title}
              </button>
            )}
            {!isEditing && task.aiGenerated && (
              <Badge
                variant="secondary"
                className="gap-1 text-[10px] px-1.5 py-0 h-5 bg-ai/10 text-ai border-ai/20"
              >
                <Sparkles className="size-3" aria-hidden="true" />
                AI
              </Badge>
            )}
            {!isEditing && task.estimatedHours != null && (
              <span className="inline-flex items-center gap-1 text-xs bg-muted px-2 py-0.5 rounded shrink-0">
                <Clock className="size-3" aria-hidden="true" />
                {task.estimatedHours}h
              </span>
            )}
          </div>
          {task.dependencyIds.length > 0 && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Depends on: {task.dependencyIds.length} task{task.dependencyIds.length > 1 ? 's' : ''}
            </p>
          )}
        </div>
        {hasExpandableContent && (
          <Button
            variant="ghost"
            size="sm"
            className="size-7 p-0 shrink-0"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-label={`${expanded ? 'Collapse' : 'Expand'} details for "${task.title}"`}
          >
            {expanded ? (
              <ChevronDown className="size-4" aria-hidden="true" />
            ) : (
              <ChevronRight className="size-4" aria-hidden="true" />
            )}
          </Button>
        )}
      </div>

      {expanded && hasExpandableContent && (
        <div className="mt-3 ml-7 space-y-3 text-sm">
          {task.description && <p className="text-muted-foreground">{task.description}</p>}

          {task.acceptanceCriteria.length > 0 && (
            <div>
              <h5 className="text-xs font-medium text-muted-foreground mb-1">
                Acceptance Criteria
              </h5>
              <ul className="space-y-1 list-disc list-inside text-xs text-muted-foreground">
                {task.acceptanceCriteria.map((criterion, i) => (
                  <li key={i}>{criterion}</li>
                ))}
              </ul>
            </div>
          )}

          {task.codeReferences.length > 0 && (
            <div>
              <h5 className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                <FileCode className="size-3" aria-hidden="true" />
                Code References
              </h5>
              <ul className="space-y-1">
                {task.codeReferences.map((ref, i) => (
                  <li
                    key={i}
                    className="text-xs font-mono bg-muted rounded px-2 py-1 truncate"
                    title={`${ref.filePath}:${ref.lineStart}-${ref.lineEnd}`}
                  >
                    {ref.filePath}:{ref.lineStart}-{ref.lineEnd}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </li>
  );
});

// ============================================================================
// Legacy task item (from AIContextStore)
// ============================================================================

interface LegacyTaskItemProps {
  task: ContextTask;
  isCompleted: boolean;
  onToggle: () => void;
}

function LegacyTaskItem({ task, isCompleted, onToggle }: LegacyTaskItemProps) {
  return (
    <li className="flex items-start gap-2.5">
      <Checkbox
        checked={isCompleted}
        onCheckedChange={onToggle}
        aria-label={`Mark "${task.title}" as ${isCompleted ? 'incomplete' : 'complete'}`}
        className="mt-0.5"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('text-sm', isCompleted && 'line-through text-muted-foreground')}>
            {task.title}
          </span>
          {task.estimate && (
            <span className="text-xs bg-muted px-2 py-0.5 rounded shrink-0">{task.estimate}</span>
          )}
        </div>
        {task.dependencies.length > 0 && (
          <p className="text-xs text-muted-foreground mt-0.5">
            Depends on: {task.dependencies.map((depId) => `Task ${depId}`).join(', ')}
          </p>
        )}
      </div>
    </li>
  );
}

// ============================================================================
// Decompose skeleton
// ============================================================================

function DecomposeSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Decomposing tasks">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-start gap-2.5">
          <Skeleton className="size-4 mt-0.5 rounded" />
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const AITasksSection = observer(function AITasksSection({
  tasks,
  prompts,
  onTaskToggle,
  issueId,
}: AITasksSectionProps) {
  const taskStore = useTaskStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';

  // Drag-and-drop state
  const [dragIndex, setDragIndex] = React.useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = React.useState<number | null>(null);

  // Inline edit state
  const [editingTaskId, setEditingTaskId] = React.useState<string | null>(null);
  const [editValue, setEditValue] = React.useState('');

  // Load persistent tasks when issueId provided
  React.useEffect(() => {
    if (issueId && workspaceId) {
      void taskStore.fetchTasks(workspaceId, issueId);
    }
  }, [issueId, workspaceId, taskStore]);

  // Legacy local state for AIContext tasks
  const [completedTasks, setCompletedTasks] = React.useState<Set<number>>(
    () => new Set(tasks.filter((t) => t.completed).map((t) => t.id))
  );

  React.useEffect(() => {
    setCompletedTasks(new Set(tasks.filter((t) => t.completed).map((t) => t.id)));
  }, [tasks]);

  const handleDecompose = React.useCallback(async () => {
    if (!issueId || !workspaceId) return;
    await taskStore.decomposeTasks(workspaceId, issueId);
    if (taskStore.error) {
      toast.error('Failed to decompose tasks', {
        description: taskStore.error,
      });
    }
  }, [issueId, workspaceId, taskStore]);

  // Drag-and-drop handlers
  const handleDragStart = React.useCallback((index: number) => {
    return (e: React.DragEvent) => {
      setDragIndex(index);
      e.dataTransfer.effectAllowed = 'move';
    };
  }, []);

  const handleDragOver = React.useCallback((index: number) => {
    return (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      setDragOverIndex(index);
    };
  }, []);

  const handleDrop = React.useCallback(
    (targetIndex: number, currentTasks: Task[]) => {
      return (e: React.DragEvent) => {
        e.preventDefault();
        if (dragIndex === null || dragIndex === targetIndex) {
          setDragIndex(null);
          setDragOverIndex(null);
          return;
        }

        const reordered = [...currentTasks];
        const [moved] = reordered.splice(dragIndex, 1);
        if (moved) {
          reordered.splice(targetIndex, 0, moved);
          const newOrder = reordered.map((t) => t.id);
          if (issueId && workspaceId) {
            void taskStore.reorderTasks(workspaceId, issueId, newOrder);
          }
        }

        setDragIndex(null);
        setDragOverIndex(null);
      };
    },
    [dragIndex, issueId, workspaceId, taskStore]
  );

  const handleDragEnd = React.useCallback(() => {
    setDragIndex(null);
    setDragOverIndex(null);
  }, []);

  // Inline edit handlers
  const handleEditStart = React.useCallback((taskId: string, title: string) => {
    setEditingTaskId(taskId);
    setEditValue(title);
  }, []);

  const handleEditSave = React.useCallback(() => {
    if (!editingTaskId || !issueId || !workspaceId) {
      setEditingTaskId(null);
      return;
    }
    const trimmed = editValue.trim();
    if (trimmed.length > 0) {
      void taskStore.updateTask(workspaceId, editingTaskId, issueId, {
        title: trimmed,
      });
    }
    setEditingTaskId(null);
  }, [editingTaskId, editValue, issueId, workspaceId, taskStore]);

  const handleEditCancel = React.useCallback(() => {
    setEditingTaskId(null);
    setEditValue('');
  }, []);

  const persistentTasks = issueId ? taskStore.getTasksForIssue(issueId) : [];
  const hasPersistentTasks = persistentTasks.length > 0;
  const hasLegacyTasks = tasks.length > 0;
  const hasPrompts = prompts.length > 0;
  const canDecompose = !!issueId && !!workspaceId;

  // Dependency graph data
  const hasDependencies = persistentTasks.some((t) => t.dependencyIds.length > 0);
  const graphTasks = persistentTasks.map((t) => ({
    id: t.id,
    title: t.title,
    status: t.status as 'todo' | 'in_progress' | 'done',
    sortOrder: t.sortOrder,
    dependencyIds: t.dependencyIds,
  }));

  if (
    !hasPersistentTasks &&
    !hasLegacyTasks &&
    !hasPrompts &&
    !taskStore.isDecomposing &&
    !canDecompose
  ) {
    return null;
  }

  const toggleLegacyTask = (id: number) => {
    setCompletedTasks((prev) => {
      const next = new Set(prev);
      const wasCompleted = next.has(id);
      if (wasCompleted) next.delete(id);
      else next.add(id);
      onTaskToggle?.(id, !wasCompleted);
      return next;
    });
  };

  // Progress for persistent tasks
  const completedCount = issueId ? taskStore.getCompletedCount(issueId) : 0;
  const totalCount = persistentTasks.length;

  // Progress for legacy tasks
  const legacyCompleted = completedTasks.size;
  const legacyTotal = tasks.length;

  const showProgress = hasPersistentTasks || hasLegacyTasks;
  const progressCompleted = hasPersistentTasks ? completedCount : legacyCompleted;
  const progressTotal = hasPersistentTasks ? totalCount : legacyTotal;

  return (
    <div className="space-y-6">
      {/* Progress bar */}
      {showProgress && <TaskProgressBar completed={progressCompleted} total={progressTotal} />}

      {/* Dependency graph */}
      {hasPersistentTasks && hasDependencies && (
        <TaskDependencyGraph tasks={graphTasks} isLoading={taskStore.isDecomposing} />
      )}

      {/* Decompose button when no persistent tasks exist */}
      {canDecompose && !hasPersistentTasks && !taskStore.isDecomposing && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleDecompose}
          disabled={taskStore.isDecomposing}
          className="gap-1.5 w-full"
        >
          <Wand2 className="size-3.5" aria-hidden="true" />
          Decompose Tasks
        </Button>
      )}

      {/* Persistent tasks from TaskStore */}
      {hasPersistentTasks && (
        <section aria-label="Implementation tasks">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium flex items-center gap-1.5">
              <ListChecks className="size-4" aria-hidden="true" />
              Tasks
            </h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDecompose}
              disabled={taskStore.isDecomposing}
              className="gap-1 h-7 text-xs"
            >
              {taskStore.isDecomposing ? (
                <>
                  <Loader2 className="size-3 animate-spin" aria-hidden="true" />
                  Decomposing...
                </>
              ) : (
                <>
                  <Wand2 className="size-3" aria-hidden="true" />
                  Re-decompose
                </>
              )}
            </Button>
          </div>
          <ul className="space-y-2" role="list">
            {persistentTasks.map((task, index) => (
              <PersistentTaskItem
                key={task.id}
                task={task}
                workspaceId={workspaceId}
                issueId={issueId!}
                isDragging={dragIndex === index}
                isDragOver={dragOverIndex === index}
                editingTaskId={editingTaskId}
                editValue={editValue}
                onEditStart={handleEditStart}
                onEditChange={setEditValue}
                onEditSave={handleEditSave}
                onEditCancel={handleEditCancel}
                onDragStart={handleDragStart(index)}
                onDragOver={handleDragOver(index)}
                onDrop={handleDrop(index, persistentTasks)}
                onDragEnd={handleDragEnd}
              />
            ))}
          </ul>
        </section>
      )}

      {/* Decompose loading state */}
      {taskStore.isDecomposing && <DecomposeSkeleton />}

      {/* Legacy AI context tasks (backward compat) */}
      {hasLegacyTasks && !hasPersistentTasks && (
        <section aria-label="Implementation checklist">
          <h4 className="text-sm font-medium mb-3">Implementation Checklist</h4>
          <ul className="space-y-2" role="list">
            {tasks.map((task) => {
              const isCompleted = completedTasks.has(task.id);
              return (
                <LegacyTaskItem
                  key={task.id}
                  task={task}
                  isCompleted={isCompleted}
                  onToggle={() => toggleLegacyTask(task.id)}
                />
              );
            })}
          </ul>
        </section>
      )}

      {/* Prompts */}
      {hasPrompts && (
        <section aria-label="Ready-to-use prompts">
          <h4 className="text-sm font-medium mb-3">Ready-to-Use Prompts</h4>
          <div className="space-y-2">
            {prompts.map((prompt, index) => (
              <PromptBlock key={prompt.taskId} prompt={prompt} defaultExpanded={index === 0} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
});
