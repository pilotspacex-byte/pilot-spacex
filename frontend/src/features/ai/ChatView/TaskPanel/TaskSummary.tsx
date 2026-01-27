/**
 * TaskSummary - Overview of task counts and progress
 */

import { memo } from 'react';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TaskSummaryProps {
  total: number;
  completed: number;
  inProgress: number;
  pending: number;
  className?: string;
}

export const TaskSummary = memo<TaskSummaryProps>(
  ({ total, completed, inProgress, pending, className }) => {
    const progress = total > 0 ? (completed / total) * 100 : 0;

    return (
      <div className={cn('space-y-3', className)}>
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">Task Progress</span>
          <span className="text-muted-foreground">
            {completed}/{total}
          </span>
        </div>

        <Progress value={progress} className="h-2" />

        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Circle className="h-3 w-3" />
            <span>{pending} pending</span>
          </div>

          <div className="flex items-center gap-1.5 text-blue-500">
            <Loader2 className="h-3 w-3" />
            <span>{inProgress} active</span>
          </div>

          <div className="flex items-center gap-1.5 text-green-500">
            <CheckCircle2 className="h-3 w-3" />
            <span>{completed} done</span>
          </div>
        </div>
      </div>
    );
  }
);

TaskSummary.displayName = 'TaskSummary';
