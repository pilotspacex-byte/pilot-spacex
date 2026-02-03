/**
 * TaskItem - Individual task display with status and metadata
 * Follows shadcn/ui AI task component pattern
 * T071-T074: Add progress tracking UI with progress bar
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle, XCircle, Loader2, Sparkles, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentTask } from '../types';

interface TaskItemProps {
  task: AgentTask;
  progress?: number;
  currentStep?: string;
  totalSteps?: number;
  estimatedSecondsRemaining?: number;
  className?: string;
}

const StatusIcon = {
  pending: Circle,
  in_progress: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
} as const;

const statusColor = {
  pending: 'text-muted-foreground',
  in_progress: 'text-blue-500',
  completed: 'text-green-500',
  failed: 'text-destructive',
} as const;

const statusLabel = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
} as const;

function formatTimeRemaining(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export const TaskItem = memo<TaskItemProps>(
  ({ task, progress, currentStep, totalSteps, estimatedSecondsRemaining, className }) => {
    const Icon = StatusIcon[task.status];
    const color = statusColor[task.status];
    const label = statusLabel[task.status];

    const showProgress = task.status === 'in_progress' && typeof progress === 'number';
    const showStepIndicator = task.status === 'in_progress' && currentStep && totalSteps;
    const showTimeEstimate = task.status === 'in_progress' && estimatedSecondsRemaining;

    return (
      <Card
        className={cn(
          'p-3 transition-colors',
          task.status === 'in_progress' && 'border-primary/50 bg-primary/5',
          className
        )}
      >
        <div className="flex items-start gap-3">
          <Icon
            className={cn(
              'h-4 w-4 shrink-0 mt-0.5',
              color,
              task.status === 'in_progress' && 'animate-spin'
            )}
          />

          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-tight">{task.subject}</p>

              <Badge variant="secondary" className="shrink-0">
                {label}
              </Badge>
            </div>

            {task.description && (
              <p className="text-xs text-muted-foreground line-clamp-2">{task.description}</p>
            )}

            {showProgress && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  {showStepIndicator && (
                    <span className="font-medium">
                      Step {currentStep} of {totalSteps}
                    </span>
                  )}
                  {showTimeEstimate && (
                    <span className="ml-auto">
                      ~{formatTimeRemaining(estimatedSecondsRemaining)} left
                    </span>
                  )}
                </div>
                <Progress value={progress} className="h-1.5" />
                <div className="flex justify-end">
                  <span className="text-xs font-medium text-muted-foreground">
                    {progress.toFixed(0)}%
                  </span>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 pt-1">
              {task.skill && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Sparkles className="h-3 w-3" />
                  <span className="font-mono">{task.skill}</span>
                </div>
              )}

              {task.subagent && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Brain className="h-3 w-3" />
                  <span className="font-mono">{task.subagent}</span>
                  {task.model && (
                    <Badge variant="outline" className="ml-1 h-4 px-1.5 text-[10px] font-normal">
                      {task.model}
                    </Badge>
                  )}
                </div>
              )}

              {task.completedAt && (
                <span className="text-xs text-muted-foreground ml-auto">
                  {new Date(task.completedAt).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>
          </div>
        </div>
      </Card>
    );
  }
);

TaskItem.displayName = 'TaskItem';
