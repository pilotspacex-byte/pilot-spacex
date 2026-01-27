/**
 * TaskList - List of tasks with filtering
 */

import { memo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { AgentTask } from '../types';
import { TaskItem } from './TaskItem';

interface TaskListProps {
  tasks: AgentTask[];
  activeTasks: AgentTask[];
  completedTasks: AgentTask[];
  className?: string;
}

export const TaskList = memo<TaskListProps>(({ tasks, activeTasks, completedTasks, className }) => {
  const pendingTasks = tasks.filter((t) => t.status === 'pending');

  return (
    <Tabs defaultValue="active" className={className}>
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="active" className="text-xs">
          Active ({activeTasks.length})
        </TabsTrigger>
        <TabsTrigger value="pending" className="text-xs">
          Pending ({pendingTasks.length})
        </TabsTrigger>
        <TabsTrigger value="completed" className="text-xs">
          Done ({completedTasks.length})
        </TabsTrigger>
      </TabsList>

      <TabsContent value="active" className="mt-3">
        <ScrollArea className="h-[300px]">
          {activeTasks.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              No active tasks
            </div>
          ) : (
            <div className="space-y-2 pr-4">
              {activeTasks.map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
            </div>
          )}
        </ScrollArea>
      </TabsContent>

      <TabsContent value="pending" className="mt-3">
        <ScrollArea className="h-[300px]">
          {pendingTasks.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              No pending tasks
            </div>
          ) : (
            <div className="space-y-2 pr-4">
              {pendingTasks.map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
            </div>
          )}
        </ScrollArea>
      </TabsContent>

      <TabsContent value="completed" className="mt-3">
        <ScrollArea className="h-[300px]">
          {completedTasks.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              No completed tasks
            </div>
          ) : (
            <div className="space-y-2 pr-4">
              {completedTasks.map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
            </div>
          )}
        </ScrollArea>
      </TabsContent>
    </Tabs>
  );
});

TaskList.displayName = 'TaskList';
