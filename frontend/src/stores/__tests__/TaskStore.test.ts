/**
 * Unit tests for TaskStore.
 *
 * Tests MobX store for task management: CRUD, optimistic updates, reorder, export.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TaskStore } from '../TaskStore';
import type { Task, TaskListResponse, DecomposeResponse, ContextExportResponse } from '@/types';

vi.mock('@/services/api', () => ({
  tasksApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateStatus: vi.fn(),
    reorder: vi.fn(),
    exportContext: vi.fn(),
    decompose: vi.fn(),
  },
}));

import { tasksApi } from '@/services/api';

const mockedTasksApi = vi.mocked(tasksApi);

function createTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'task-1',
    issueId: 'issue-1',
    workspaceId: 'ws-1',
    title: 'Test task',
    status: 'todo' as const,
    sortOrder: 0,
    acceptanceCriteria: [],
    codeReferences: [],
    aiGenerated: false,
    dependencyIds: [],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('TaskStore', () => {
  let store: TaskStore;

  beforeEach(() => {
    store = new TaskStore();
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have empty tasksByIssue map', () => {
      expect(store.tasksByIssue.size).toBe(0);
    });

    it('should not be loading', () => {
      expect(store.isLoading).toBe(false);
    });

    it('should not be decomposing', () => {
      expect(store.isDecomposing).toBe(false);
    });

    it('should have null error', () => {
      expect(store.error).toBeNull();
    });
  });

  describe('getTasksForIssue', () => {
    it('should return empty array for unknown issue', () => {
      expect(store.getTasksForIssue('unknown')).toEqual([]);
    });

    it('should return tasks for known issue', () => {
      const tasks = [createTask()];
      store.tasksByIssue.set('issue-1', tasks);
      expect(store.getTasksForIssue('issue-1')).toEqual(tasks);
    });
  });

  describe('getCompletionPercent', () => {
    it('should return 0 for no tasks', () => {
      expect(store.getCompletionPercent('issue-1')).toBe(0);
    });

    it('should return 50 for 2/4 done', () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 't1', status: 'done' as const }),
        createTask({ id: 't2', status: 'done' as const }),
        createTask({ id: 't3', status: 'todo' as const }),
        createTask({ id: 't4', status: 'in_progress' as const }),
      ]);
      expect(store.getCompletionPercent('issue-1')).toBe(50);
    });

    it('should return 100 for all done', () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 't1', status: 'done' as const }),
        createTask({ id: 't2', status: 'done' as const }),
        createTask({ id: 't3', status: 'done' as const }),
      ]);
      expect(store.getCompletionPercent('issue-1')).toBe(100);
    });

    it('should return 0 for no done tasks', () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 't1', status: 'todo' as const }),
        createTask({ id: 't2', status: 'in_progress' as const }),
      ]);
      expect(store.getCompletionPercent('issue-1')).toBe(0);
    });

    it('should round to nearest integer', () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 't1', status: 'done' as const }),
        createTask({ id: 't2', status: 'todo' as const }),
        createTask({ id: 't3', status: 'todo' as const }),
      ]);
      // 1/3 = 33.33... -> 33
      expect(store.getCompletionPercent('issue-1')).toBe(33);
    });
  });

  describe('getCompletedCount', () => {
    it('should return 0 for no tasks', () => {
      expect(store.getCompletedCount('issue-1')).toBe(0);
    });

    it('should count only done tasks', () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 't1', status: 'done' as const }),
        createTask({ id: 't2', status: 'todo' as const }),
        createTask({ id: 't3', status: 'done' as const }),
      ]);
      expect(store.getCompletedCount('issue-1')).toBe(2);
    });
  });

  describe('fetchTasks', () => {
    it('should load tasks and store by issueId', async () => {
      const tasks = [createTask(), createTask({ id: 'task-2' })];
      const response: TaskListResponse = {
        tasks,
        total: 2,
        completed: 0,
        completionPercent: 0,
      };
      mockedTasksApi.list.mockResolvedValue(response);

      await store.fetchTasks('ws-1', 'issue-1');

      expect(mockedTasksApi.list).toHaveBeenCalledWith('ws-1', 'issue-1');
      expect(store.getTasksForIssue('issue-1')).toEqual(tasks);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
    });

    it('should set isLoading during fetch', async () => {
      let resolvePromise: (value: TaskListResponse) => void;
      const promise = new Promise<TaskListResponse>((resolve) => {
        resolvePromise = resolve;
      });
      mockedTasksApi.list.mockReturnValue(promise);

      const fetchPromise = store.fetchTasks('ws-1', 'issue-1');
      expect(store.isLoading).toBe(true);

      resolvePromise!({ tasks: [], total: 0, completed: 0, completionPercent: 0 });
      await fetchPromise;
      expect(store.isLoading).toBe(false);
    });

    it('should handle API error', async () => {
      mockedTasksApi.list.mockRejectedValue(new Error('Network error'));

      await store.fetchTasks('ws-1', 'issue-1');

      expect(store.error).toBe('Network error');
      expect(store.isLoading).toBe(false);
    });

    it('should handle non-Error rejection', async () => {
      mockedTasksApi.list.mockRejectedValue('something went wrong');

      await store.fetchTasks('ws-1', 'issue-1');

      expect(store.error).toBe('Failed to load tasks');
    });
  });

  describe('createTask', () => {
    it('should add created task to local list', async () => {
      const newTask = createTask({ id: 'new-task' });
      mockedTasksApi.create.mockResolvedValue(newTask);

      const result = await store.createTask('ws-1', 'issue-1', {
        title: 'New task',
      });

      expect(result).toEqual(newTask);
      expect(store.getTasksForIssue('issue-1')).toContainEqual(newTask);
    });

    it('should append to existing tasks', async () => {
      const existing = createTask({ id: 'existing' });
      store.tasksByIssue.set('issue-1', [existing]);

      const newTask = createTask({ id: 'new-task' });
      mockedTasksApi.create.mockResolvedValue(newTask);

      await store.createTask('ws-1', 'issue-1', { title: 'New task' });

      const tasks = store.getTasksForIssue('issue-1');
      expect(tasks).toHaveLength(2);
      expect(tasks[0]).toEqual(existing);
      expect(tasks[1]).toEqual(newTask);
    });

    it('should return null on error', async () => {
      mockedTasksApi.create.mockRejectedValue(new Error('Create failed'));

      const result = await store.createTask('ws-1', 'issue-1', {
        title: 'New task',
      });

      expect(result).toBeNull();
      expect(store.error).toBe('Create failed');
    });
  });

  describe('updateTask', () => {
    it('should update task in local list', async () => {
      const task = createTask({ id: 'task-1', title: 'Original' });
      store.tasksByIssue.set('issue-1', [task]);

      const updated = createTask({ id: 'task-1', title: 'Updated' });
      mockedTasksApi.update.mockResolvedValue(updated);

      const result = await store.updateTask('ws-1', 'task-1', 'issue-1', {
        title: 'Updated',
      });

      expect(result).toEqual(updated);
      expect(store.getTasksForIssue('issue-1')[0]!.title).toBe('Updated');
    });

    it('should not modify list if task not found', async () => {
      store.tasksByIssue.set('issue-1', [createTask({ id: 'other' })]);
      const updated = createTask({ id: 'missing', title: 'Updated' });
      mockedTasksApi.update.mockResolvedValue(updated);

      await store.updateTask('ws-1', 'missing', 'issue-1', {
        title: 'Updated',
      });

      expect(store.getTasksForIssue('issue-1')).toHaveLength(1);
      expect(store.getTasksForIssue('issue-1')[0]!.id).toBe('other');
    });

    it('should return null on error', async () => {
      mockedTasksApi.update.mockRejectedValue(new Error('Update failed'));

      const result = await store.updateTask('ws-1', 'task-1', 'issue-1', {
        title: 'Updated',
      });

      expect(result).toBeNull();
      expect(store.error).toBe('Update failed');
    });
  });

  describe('deleteTask', () => {
    it('should remove task from local list', async () => {
      store.tasksByIssue.set('issue-1', [
        createTask({ id: 'task-1' }),
        createTask({ id: 'task-2' }),
      ]);
      mockedTasksApi.delete.mockResolvedValue(undefined);

      const result = await store.deleteTask('ws-1', 'task-1', 'issue-1');

      expect(result).toBe(true);
      expect(store.getTasksForIssue('issue-1')).toHaveLength(1);
      expect(store.getTasksForIssue('issue-1')[0]!.id).toBe('task-2');
    });

    it('should return false on error', async () => {
      mockedTasksApi.delete.mockRejectedValue(new Error('Delete failed'));

      const result = await store.deleteTask('ws-1', 'task-1', 'issue-1');

      expect(result).toBe(false);
      expect(store.error).toBe('Delete failed');
    });
  });

  describe('updateStatus (optimistic)', () => {
    it('should optimistically update status immediately', async () => {
      const task = createTask({ id: 'task-1', status: 'todo' as const });
      store.tasksByIssue.set('issue-1', [task]);

      const updatedTask = createTask({ id: 'task-1', status: 'done' as const });
      let resolveApi: (value: Task) => void;
      const apiPromise = new Promise<Task>((resolve) => {
        resolveApi = resolve;
      });
      mockedTasksApi.updateStatus.mockReturnValue(apiPromise);

      const updatePromise = store.updateStatus('ws-1', 'task-1', 'issue-1', 'done');

      // Status should be updated immediately (optimistic)
      expect(store.getTasksForIssue('issue-1')[0]!.status).toBe('done');

      resolveApi!(updatedTask);
      await updatePromise;

      expect(store.getTasksForIssue('issue-1')[0]!.status).toBe('done');
    });

    it('should rollback on API error', async () => {
      const task = createTask({ id: 'task-1', status: 'todo' as const });
      store.tasksByIssue.set('issue-1', [task]);

      mockedTasksApi.updateStatus.mockRejectedValue(new Error('Status update failed'));

      const result = await store.updateStatus('ws-1', 'task-1', 'issue-1', 'done');

      expect(result).toBeNull();
      // Should rollback to original status
      expect(store.getTasksForIssue('issue-1')[0]!.status).toBe('todo');
      expect(store.error).toBe('Status update failed');
    });

    it('should return updated task on success', async () => {
      const task = createTask({ id: 'task-1', status: 'todo' as const });
      store.tasksByIssue.set('issue-1', [task]);

      const updatedTask = createTask({
        id: 'task-1',
        status: 'in_progress' as const,
      });
      mockedTasksApi.updateStatus.mockResolvedValue(updatedTask);

      const result = await store.updateStatus('ws-1', 'task-1', 'issue-1', 'in_progress');

      expect(result).toEqual(updatedTask);
    });
  });

  describe('reorderTasks (optimistic)', () => {
    it('should optimistically reorder tasks immediately before API resolves', async () => {
      const t1 = createTask({ id: 't1', sortOrder: 0 });
      const t2 = createTask({ id: 't2', sortOrder: 1 });
      const t3 = createTask({ id: 't3', sortOrder: 2 });
      store.tasksByIssue.set('issue-1', [t1, t2, t3]);

      let resolveApi: (value: TaskListResponse) => void;
      const apiPromise = new Promise<TaskListResponse>((resolve) => {
        resolveApi = resolve;
      });
      mockedTasksApi.reorder.mockReturnValue(apiPromise);

      const reorderPromise = store.reorderTasks('ws-1', 'issue-1', ['t3', 't1', 't2']);

      // Optimistic: local state should reflect new order immediately
      const optimistic = store.getTasksForIssue('issue-1');
      expect(optimistic[0]!.id).toBe('t3');
      expect(optimistic[1]!.id).toBe('t1');
      expect(optimistic[2]!.id).toBe('t2');

      // Resolve API with server response
      resolveApi!({
        tasks: [
          createTask({ id: 't3', sortOrder: 0 }),
          createTask({ id: 't1', sortOrder: 1 }),
          createTask({ id: 't2', sortOrder: 2 }),
        ],
        total: 3,
        completed: 0,
        completionPercent: 0,
      });
      await reorderPromise;

      // After API resolves, server response replaces optimistic state
      const final = store.getTasksForIssue('issue-1');
      expect(final[0]!.id).toBe('t3');
      expect(final[1]!.id).toBe('t1');
      expect(final[2]!.id).toBe('t2');
    });

    it('should replace optimistic state with API response on success', async () => {
      const t1 = createTask({ id: 't1', sortOrder: 0 });
      const t2 = createTask({ id: 't2', sortOrder: 1 });
      store.tasksByIssue.set('issue-1', [t1, t2]);

      const reordered: TaskListResponse = {
        tasks: [createTask({ id: 't2', sortOrder: 0 }), createTask({ id: 't1', sortOrder: 1 })],
        total: 2,
        completed: 0,
        completionPercent: 0,
      };
      mockedTasksApi.reorder.mockResolvedValue(reordered);

      await store.reorderTasks('ws-1', 'issue-1', ['t2', 't1']);

      expect(mockedTasksApi.reorder).toHaveBeenCalledWith('ws-1', 'issue-1', ['t2', 't1']);
      const tasks = store.getTasksForIssue('issue-1');
      expect(tasks[0]!.id).toBe('t2');
      expect(tasks[1]!.id).toBe('t1');
    });

    it('should rollback to previous order on API error', async () => {
      const t1 = createTask({ id: 't1', sortOrder: 0 });
      const t2 = createTask({ id: 't2', sortOrder: 1 });
      const t3 = createTask({ id: 't3', sortOrder: 2 });
      store.tasksByIssue.set('issue-1', [t1, t2, t3]);

      mockedTasksApi.reorder.mockRejectedValue(new Error('Reorder failed'));

      await store.reorderTasks('ws-1', 'issue-1', ['t3', 't1', 't2']);

      // Should rollback to original order
      const tasks = store.getTasksForIssue('issue-1');
      expect(tasks[0]!.id).toBe('t1');
      expect(tasks[1]!.id).toBe('t2');
      expect(tasks[2]!.id).toBe('t3');
      expect(store.error).toBe('Reorder failed');
    });

    it('should handle non-Error rejection with rollback', async () => {
      const t1 = createTask({ id: 't1', sortOrder: 0 });
      const t2 = createTask({ id: 't2', sortOrder: 1 });
      store.tasksByIssue.set('issue-1', [t1, t2]);

      mockedTasksApi.reorder.mockRejectedValue('network timeout');

      await store.reorderTasks('ws-1', 'issue-1', ['t2', 't1']);

      // Should rollback
      const tasks = store.getTasksForIssue('issue-1');
      expect(tasks[0]!.id).toBe('t1');
      expect(tasks[1]!.id).toBe('t2');
      expect(store.error).toBe('Failed to reorder tasks');
    });

    it('should handle reorder with no existing tasks gracefully', async () => {
      // No tasks set for issue-1
      const reordered: TaskListResponse = {
        tasks: [],
        total: 0,
        completed: 0,
        completionPercent: 0,
      };
      mockedTasksApi.reorder.mockResolvedValue(reordered);

      await store.reorderTasks('ws-1', 'issue-1', ['t1', 't2']);

      expect(store.getTasksForIssue('issue-1')).toEqual([]);
      expect(store.error).toBeNull();
    });
  });

  describe('exportContext', () => {
    it('should return context export response', async () => {
      const response: ContextExportResponse = {
        content: '# Issue Context\n\nTask list here',
        format: 'markdown' as const,
        generatedAt: '2026-01-01T00:00:00Z',
        stats: { tasksCount: 3, relatedIssuesCount: 2, relatedDocsCount: 1 },
      };
      mockedTasksApi.exportContext.mockResolvedValue(response);

      const result = await store.exportContext('ws-1', 'issue-1', 'markdown');

      expect(result).toEqual(response);
      expect(mockedTasksApi.exportContext).toHaveBeenCalledWith('ws-1', 'issue-1', 'markdown');
    });

    it('should return null on error', async () => {
      mockedTasksApi.exportContext.mockRejectedValue(new Error('Export failed'));

      const result = await store.exportContext('ws-1', 'issue-1', 'claude_code');

      expect(result).toBeNull();
      expect(store.error).toBe('Export failed');
    });
  });

  describe('decomposeTasks', () => {
    it('should call decompose API and refresh task list', async () => {
      const decomposedTasks = [
        createTask({ id: 'd1', title: 'Subtask 1', aiGenerated: true }),
        createTask({ id: 'd2', title: 'Subtask 2', aiGenerated: true }),
      ];
      const decomposeResponse: DecomposeResponse = {
        subtasks: [],
        summary: null,
        totalEstimatedDays: null,
        criticalPath: null,
        parallelOpportunities: null,
      };
      const listResponse: TaskListResponse = {
        tasks: decomposedTasks,
        total: 2,
        completed: 0,
        completionPercent: 0,
      };
      mockedTasksApi.decompose.mockResolvedValue(decomposeResponse);
      mockedTasksApi.list.mockResolvedValue(listResponse);

      await store.decomposeTasks('ws-1', 'issue-1');

      expect(mockedTasksApi.decompose).toHaveBeenCalledWith('ws-1', 'issue-1');
      expect(mockedTasksApi.list).toHaveBeenCalledWith('ws-1', 'issue-1');
      expect(store.getTasksForIssue('issue-1')).toEqual(decomposedTasks);
      expect(store.isDecomposing).toBe(false);
      expect(store.error).toBeNull();
    });

    it('should toggle isDecomposing flag during operation', async () => {
      let resolveDecompose: (value: DecomposeResponse) => void;
      const decomposePromise = new Promise<DecomposeResponse>((resolve) => {
        resolveDecompose = resolve;
      });
      mockedTasksApi.decompose.mockReturnValue(decomposePromise);
      mockedTasksApi.list.mockResolvedValue({
        tasks: [],
        total: 0,
        completed: 0,
        completionPercent: 0,
      });

      const actionPromise = store.decomposeTasks('ws-1', 'issue-1');
      expect(store.isDecomposing).toBe(true);

      resolveDecompose!({
        subtasks: [],
        summary: null,
        totalEstimatedDays: null,
        criticalPath: null,
        parallelOpportunities: null,
      });
      await actionPromise;
      expect(store.isDecomposing).toBe(false);
    });

    it('should handle API error gracefully', async () => {
      mockedTasksApi.decompose.mockRejectedValue(new Error('Decompose failed'));

      await store.decomposeTasks('ws-1', 'issue-1');

      expect(store.error).toBe('Decompose failed');
      expect(store.isDecomposing).toBe(false);
      expect(mockedTasksApi.list).not.toHaveBeenCalled();
    });

    it('should handle non-Error rejection', async () => {
      mockedTasksApi.decompose.mockRejectedValue('unknown error');

      await store.decomposeTasks('ws-1', 'issue-1');

      expect(store.error).toBe('Failed to decompose tasks');
      expect(store.isDecomposing).toBe(false);
    });
  });

  describe('reset', () => {
    it('should clear all data', () => {
      store.tasksByIssue.set('issue-1', [createTask()]);
      store.isLoading = true;
      store.isDecomposing = true;
      store.error = 'Some error';

      store.reset();

      expect(store.tasksByIssue.size).toBe(0);
      expect(store.isLoading).toBe(false);
      expect(store.isDecomposing).toBe(false);
      expect(store.error).toBeNull();
    });
  });
});
