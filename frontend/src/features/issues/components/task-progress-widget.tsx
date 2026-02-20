'use client';

import { observer } from 'mobx-react-lite';
import { Sparkles } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { useTaskStore } from '@/stores';

export interface TaskProgressWidgetProps {
  issueId: string;
  onViewAll: () => void;
}

export const TaskProgressWidget = observer(function TaskProgressWidget({
  issueId,
  onViewAll,
}: TaskProgressWidgetProps) {
  const taskStore = useTaskStore();
  const tasks = taskStore.getTasksForIssue(issueId);
  const completedCount = taskStore.getCompletedCount(issueId);
  const totalCount = tasks.length;

  if (totalCount === 0) return null;

  const percentage = Math.round((completedCount / totalCount) * 100);

  return (
    <div
      className="rounded-xl border border-ai/20 bg-ai/5 p-4"
      aria-label={`Implementation tasks: ${completedCount} of ${totalCount} complete`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Sparkles className="size-4 text-ai" aria-hidden="true" />
          Implementation Tasks
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {completedCount}/{totalCount} completed
        </span>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Progress value={percentage} className="h-1.5 flex-1" />
        <button
          type="button"
          onClick={onViewAll}
          className="shrink-0 text-xs font-medium text-ai hover:text-ai/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
        >
          View all &rarr;
        </button>
      </div>
    </div>
  );
});
