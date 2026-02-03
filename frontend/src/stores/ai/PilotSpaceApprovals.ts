/**
 * PilotSpace Approvals - Manages approval flow per DD-003.
 *
 * Extracted from PilotSpaceStore to keep files under 700 lines.
 * Handles:
 * - Approve/reject pending actions via typed API client
 * - Task lifecycle management
 *
 * @module stores/ai/PilotSpaceApprovals
 */
import { runInAction } from 'mobx';
import { aiApi } from '@/services/api/ai';
import type { PilotSpaceStore, TaskState } from './PilotSpaceStore';
import type { TaskStatus } from './types/events';

/**
 * Manages approval and task operations for PilotSpaceStore.
 *
 * Uses `aiApi` for authenticated requests instead of raw fetch.
 */
export class PilotSpaceApprovals {
  constructor(private readonly store: PilotSpaceStore) {}

  /**
   * Approve a pending request via typed API.
   * @param requestId - Request identifier
   */
  async approveRequest(requestId: string): Promise<void> {
    const request = this.store.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      await aiApi.approveAction(requestId);
      runInAction(() => {
        this.store.pendingApprovals = this.store.pendingApprovals.filter(
          (r) => r.requestId !== requestId
        );
      });
    } catch (err) {
      runInAction(() => {
        this.store.error = err instanceof Error ? err.message : 'Failed to approve request';
      });
    }
  }

  /**
   * Reject a pending request via typed API.
   * @param requestId - Request identifier
   * @param reason - Optional rejection reason
   */
  async rejectRequest(requestId: string, reason?: string): Promise<void> {
    const request = this.store.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      await aiApi.rejectAction(requestId, reason ?? '');
      runInAction(() => {
        this.store.pendingApprovals = this.store.pendingApprovals.filter(
          (r) => r.requestId !== requestId
        );
      });
    } catch (err) {
      runInAction(() => {
        this.store.error = err instanceof Error ? err.message : 'Failed to reject request';
      });
    }
  }

  /**
   * Add or update a task.
   * @param taskId - Task identifier
   * @param update - Task state update
   */
  addTask(taskId: string, update: Partial<Omit<TaskState, 'id'>>): void {
    const existing = this.store.tasks.get(taskId);
    const now = new Date();

    if (existing) {
      this.store.tasks.set(taskId, {
        ...existing,
        ...update,
        updatedAt: now,
      });
    } else {
      this.store.tasks.set(taskId, {
        id: taskId,
        subject: update.subject ?? 'Task',
        status: update.status ?? 'pending',
        progress: update.progress ?? 0,
        description: update.description,
        currentStep: update.currentStep,
        totalSteps: update.totalSteps,
        estimatedSecondsRemaining: update.estimatedSecondsRemaining,
        createdAt: now,
        updatedAt: now,
      });
    }
  }

  /**
   * Update task status.
   * @param taskId - Task identifier
   * @param status - New status
   */
  updateTaskStatus(taskId: string, status: TaskStatus): void {
    const task = this.store.tasks.get(taskId);
    if (task) {
      this.store.tasks.set(taskId, {
        ...task,
        status,
        updatedAt: new Date(),
      });
    }
  }

  /**
   * Remove a task from tracking.
   * @param taskId - Task identifier
   */
  removeTask(taskId: string): void {
    this.store.tasks.delete(taskId);
  }
}
