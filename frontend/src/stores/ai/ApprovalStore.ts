'use client';

/**
 * Approval Store with pending queue management.
 *
 * Manages human-in-the-loop approval workflow with:
 * - CRUD operations for approval requests
 * - Pending count tracking
 * - Selected request state for detail view
 *
 * @module stores/ai/ApprovalStore
 * @see specs/004-mvp-agents-build/tasks/P16-T111-T120.md#T118
 */

import { makeAutoObservable, runInAction } from 'mobx';
import { aiApi, type ApprovalRequest } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export class ApprovalStore {
  requests: ApprovalRequest[] = [];
  pendingCount = 0;
  isLoading = false;
  error: string | null = null;
  selectedRequest: ApprovalRequest | null = null;

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this);
  }

  /**
   * Load pending approval requests
   */
  async loadPending(): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const response = await aiApi.listApprovals('pending');
      runInAction(() => {
        this.requests = response.requests;
        this.pendingCount = response.pending_count;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load approvals';
        this.isLoading = false;
      });
    }
  }

  /**
   * Load all approvals with optional status filter
   */
  async loadAll(status?: 'pending' | 'approved' | 'rejected' | 'expired'): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const response = await aiApi.listApprovals(status);
      runInAction(() => {
        this.requests = response.requests;
        this.pendingCount = response.pending_count;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load approvals';
        this.isLoading = false;
      });
    }
  }

  /**
   * Approve a pending request
   */
  async approve(id: string, note?: string, selectedIssues?: number[]): Promise<void> {
    try {
      await aiApi.resolveApproval(id, {
        approved: true,
        note,
        selected_issues: selectedIssues,
      });
      await this.loadPending();
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to approve';
      });
      throw err;
    }
  }

  /**
   * Reject a pending request
   */
  async reject(id: string, note?: string): Promise<void> {
    try {
      await aiApi.resolveApproval(id, { approved: false, note });
      await this.loadPending();
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to reject';
      });
      throw err;
    }
  }

  /**
   * Select a request for detail view
   */
  selectRequest(request: ApprovalRequest | null): void {
    this.selectedRequest = request;
  }

  /**
   * Reset store to initial state
   */
  reset(): void {
    this.requests = [];
    this.pendingCount = 0;
    this.isLoading = false;
    this.error = null;
    this.selectedRequest = null;
  }
}
