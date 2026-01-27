/**
 * TaskPanel - Task tracking panel with summary and list
 * Follows shadcn/ui AI task component pattern
 */

import { observer } from 'mobx-react-lite';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { ChevronDown, ListChecks } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentTask } from '../types';
import { TaskSummary } from './TaskSummary';
import { TaskList } from './TaskList';

interface TaskPanelProps {
  tasks: AgentTask[];
  activeTasks: AgentTask[];
  completedTasks: AgentTask[];
  isOpen?: boolean;
  onToggle?: () => void;
  className?: string;
}

export const TaskPanel = observer<TaskPanelProps>(
  ({ tasks, activeTasks, completedTasks, isOpen = true, onToggle, className }) => {
    const total = tasks.length;
    const completed = completedTasks.length;
    const inProgress = activeTasks.length;
    const pending = total - completed - inProgress;

    if (total === 0) return null;

    return (
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <Card className={cn('border-l-4 border-l-primary/50', className)}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-accent/50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ListChecks className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm font-medium">Task Progress</CardTitle>
                </div>

                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <ChevronDown
                    className={cn('h-4 w-4 transition-transform', isOpen && 'rotate-180')}
                  />
                  <span className="sr-only">Toggle task panel</span>
                </Button>
              </div>
            </CardHeader>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <CardContent className="pt-0 space-y-4">
              <TaskSummary
                total={total}
                completed={completed}
                inProgress={inProgress}
                pending={pending}
              />

              <TaskList tasks={tasks} activeTasks={activeTasks} completedTasks={completedTasks} />
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    );
  }
);

TaskPanel.displayName = 'TaskPanel';
