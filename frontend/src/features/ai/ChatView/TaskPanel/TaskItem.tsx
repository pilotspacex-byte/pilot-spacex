/**
 * TaskItem - Individual task display with status and metadata
 * Follows shadcn/ui AI task component pattern
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CheckCircle2, Circle, XCircle, Loader2, Sparkles, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentTask } from '../types';

interface TaskItemProps {
  task: AgentTask;
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

export const TaskItem = memo<TaskItemProps>(({ task, className }) => {
  const Icon = StatusIcon[task.status];
  const color = statusColor[task.status];
  const label = statusLabel[task.status];

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

        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium leading-tight">{task.subject}</p>

            <Badge variant="secondary" className="shrink-0">
              {label}
            </Badge>
          </div>

          {task.description && (
            <p className="text-xs text-muted-foreground line-clamp-2">{task.description}</p>
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
});

TaskItem.displayName = 'TaskItem';
