'use client';

import * as React from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import { PromptBlock } from './prompt-block';
import type { ContextTask, ContextPrompt } from '@/stores/ai/AIContextStore';

// ============================================================================
// Types
// ============================================================================

export interface AITasksSectionProps {
  tasks: ContextTask[];
  prompts: ContextPrompt[];
  onTaskToggle?: (taskId: number, completed: boolean) => void;
}

// ============================================================================
// Main Component
// ============================================================================

export function AITasksSection({ tasks, prompts, onTaskToggle }: AITasksSectionProps) {
  const [completedTasks, setCompletedTasks] = React.useState<Set<number>>(
    () => new Set(tasks.filter((t) => t.completed).map((t) => t.id))
  );

  // Reset completed state when tasks prop changes (e.g., after regeneration)
  React.useEffect(() => {
    setCompletedTasks(new Set(tasks.filter((t) => t.completed).map((t) => t.id)));
  }, [tasks]);

  if (tasks.length === 0 && prompts.length === 0) {
    return null;
  }

  const toggleTask = (id: number) => {
    setCompletedTasks((prev) => {
      const next = new Set(prev);
      const wasCompleted = next.has(id);
      if (wasCompleted) next.delete(id);
      else next.add(id);
      onTaskToggle?.(id, !wasCompleted);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {tasks.length > 0 && (
        <section aria-label="Implementation checklist">
          <h4 className="text-sm font-medium mb-3">Implementation Checklist</h4>
          <ul className="space-y-2" role="list">
            {tasks.map((task) => {
              const isCompleted = completedTasks.has(task.id);
              return (
                <li key={task.id} className="flex items-start gap-2.5">
                  <Checkbox
                    checked={isCompleted}
                    onCheckedChange={() => toggleTask(task.id)}
                    aria-label={task.title}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'text-sm',
                          isCompleted && 'line-through text-muted-foreground'
                        )}
                      >
                        {task.title}
                      </span>
                      {task.estimate && (
                        <span className="text-xs bg-muted px-2 py-0.5 rounded shrink-0">
                          {task.estimate}
                        </span>
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
            })}
          </ul>
        </section>
      )}

      {prompts.length > 0 && (
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
}
