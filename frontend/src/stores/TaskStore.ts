import { makeAutoObservable, runInAction } from 'mobx';
import { tasksApi } from '@/services/api';
import type { Task, TaskCreate, TaskUpdate, TaskStatus, ContextExportResponse } from '@/types';

export class TaskStore {
  tasksByIssue: Map<string, Task[]> = new Map();
  isLoading = false;
  isDecomposing = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // Computed helpers

  getTasksForIssue(issueId: string): Task[] {
    return this.tasksByIssue.get(issueId) ?? [];
  }

  getCompletionPercent(issueId: string): number {
    const tasks = this.getTasksForIssue(issueId);
    if (tasks.length === 0) return 0;
    return Math.round((tasks.filter((t) => t.status === 'done').length / tasks.length) * 100);
  }

  getCompletedCount(issueId: string): number {
    return this.getTasksForIssue(issueId).filter((t) => t.status === 'done').length;
  }

  // Actions

  async fetchTasks(workspaceId: string, issueId: string): Promise<void> {
    this.isLoading = true;
    this.error = null;
    try {
      const response = await tasksApi.list(workspaceId, issueId);
      runInAction(() => {
        this.tasksByIssue.set(issueId, response.tasks);
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load tasks';
        this.isLoading = false;
      });
    }
  }

  async createTask(workspaceId: string, issueId: string, data: TaskCreate): Promise<Task | null> {
    this.error = null;
    try {
      const task = await tasksApi.create(workspaceId, issueId, data);
      runInAction(() => {
        const existing = this.tasksByIssue.get(issueId) ?? [];
        this.tasksByIssue.set(issueId, [...existing, task]);
      });
      return task;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to create task';
      });
      return null;
    }
  }

  async updateTask(
    workspaceId: string,
    taskId: string,
    issueId: string,
    data: TaskUpdate
  ): Promise<Task | null> {
    this.error = null;
    try {
      const updated = await tasksApi.update(workspaceId, taskId, data);
      runInAction(() => {
        const tasks = this.tasksByIssue.get(issueId) ?? [];
        const idx = tasks.findIndex((t) => t.id === taskId);
        if (idx !== -1) {
          tasks[idx] = updated;
          this.tasksByIssue.set(issueId, [...tasks]);
        }
      });
      return updated;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update task';
      });
      return null;
    }
  }

  async deleteTask(workspaceId: string, taskId: string, issueId: string): Promise<boolean> {
    this.error = null;
    try {
      await tasksApi.delete(workspaceId, taskId);
      runInAction(() => {
        const tasks = this.tasksByIssue.get(issueId) ?? [];
        this.tasksByIssue.set(
          issueId,
          tasks.filter((t) => t.id !== taskId)
        );
      });
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to delete task';
      });
      return false;
    }
  }

  async updateStatus(
    workspaceId: string,
    taskId: string,
    issueId: string,
    status: TaskStatus
  ): Promise<Task | null> {
    // Optimistic update
    const tasks = this.tasksByIssue.get(issueId) ?? [];
    const idx = tasks.findIndex((t) => t.id === taskId);
    const previousStatus = idx !== -1 ? tasks[idx]!.status : null;

    if (idx !== -1) {
      tasks[idx] = { ...tasks[idx]!, status };
      this.tasksByIssue.set(issueId, [...tasks]);
    }

    try {
      const updated = await tasksApi.updateStatus(workspaceId, taskId, status);
      runInAction(() => {
        const current = this.tasksByIssue.get(issueId) ?? [];
        const i = current.findIndex((t) => t.id === taskId);
        if (i !== -1) {
          current[i] = updated;
          this.tasksByIssue.set(issueId, [...current]);
        }
      });
      return updated;
    } catch (err) {
      // Rollback
      runInAction(() => {
        if (previousStatus !== null && idx !== -1) {
          const current = this.tasksByIssue.get(issueId) ?? [];
          const i = current.findIndex((t) => t.id === taskId);
          if (i !== -1) {
            current[i] = { ...current[i]!, status: previousStatus };
            this.tasksByIssue.set(issueId, [...current]);
          }
        }
        this.error = err instanceof Error ? err.message : 'Failed to update status';
      });
      return null;
    }
  }

  async reorderTasks(workspaceId: string, issueId: string, taskIds: string[]): Promise<void> {
    this.error = null;
    try {
      const response = await tasksApi.reorder(workspaceId, issueId, taskIds);
      runInAction(() => {
        this.tasksByIssue.set(issueId, response.tasks);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to reorder tasks';
      });
    }
  }

  async decomposeTasks(workspaceId: string, issueId: string): Promise<void> {
    this.isDecomposing = true;
    this.error = null;
    try {
      await tasksApi.decompose(workspaceId, issueId);
      await this.fetchTasks(workspaceId, issueId);
    } catch (err: unknown) {
      runInAction(() => {
        const status = (err as { status?: number }).status;
        if (status === 501) {
          this.error =
            'AI decomposition is not yet available. Use the chat /decompose-tasks command instead.';
        } else {
          this.error = err instanceof Error ? err.message : 'Failed to decompose tasks';
        }
      });
    } finally {
      runInAction(() => {
        this.isDecomposing = false;
      });
    }
  }

  async exportContext(
    workspaceId: string,
    issueId: string,
    format: 'markdown' | 'claude_code' | 'task_list' = 'markdown'
  ): Promise<ContextExportResponse | null> {
    this.error = null;
    try {
      return await tasksApi.exportContext(workspaceId, issueId, format);
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to export context';
      });
      return null;
    }
  }

  reset(): void {
    this.tasksByIssue.clear();
    this.isLoading = false;
    this.isDecomposing = false;
    this.error = null;
  }
}
