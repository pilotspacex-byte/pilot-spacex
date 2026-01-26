/**
 * Unit tests for ApprovalStore.
 *
 * T197: Tests for approval store state management and actions.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ApprovalStore } from '../ApprovalStore';
import { aiApi, type ApprovalRequest } from '@/services/api/ai';
import type { AIStore } from '../AIStore';

// Mock the API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    listApprovals: vi.fn(),
    resolveApproval: vi.fn(),
  },
}));

describe('ApprovalStore', () => {
  let store: ApprovalStore;
  let mockRootStore: AIStore;

  const mockApprovalRequests: ApprovalRequest[] = [
    {
      id: '1',
      agent_name: 'issue_extractor',
      action_type: 'extract_issues',
      status: 'pending' as const,
      created_at: '2026-01-26T10:00:00Z',
      expires_at: '2026-01-27T10:00:00Z',
      requested_by: 'John Doe',
      context_preview: '3 issues to create',
      payload: { issues: [{ title: 'Issue 1' }] },
    },
    {
      id: '2',
      agent_name: 'pr_review',
      action_type: 'post_pr_comments',
      status: 'pending' as const,
      created_at: '2026-01-26T11:00:00Z',
      expires_at: '2026-01-27T11:00:00Z',
      requested_by: 'Jane Smith',
      context_preview: 'Post 5 review comments',
      payload: { comments: [{ body: 'Comment 1' }] },
    },
  ];

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new ApprovalStore(mockRootStore);
    vi.clearAllMocks();
  });

  describe('loadPending', () => {
    it('should load pending approvals successfully', async () => {
      const mockResponse = {
        requests: mockApprovalRequests,
        pending_count: 2,
      };

      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      expect(store.isLoading).toBe(false);
      expect(store.requests).toEqual([]);

      await store.loadPending();

      expect(aiApi.listApprovals).toHaveBeenCalledWith('pending');
      expect(store.requests).toEqual(mockApprovalRequests);
      expect(store.pendingCount).toBe(2);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
    });

    it('should handle errors when loading approvals', async () => {
      const errorMessage = 'Network error';
      vi.mocked(aiApi.listApprovals).mockRejectedValue(new Error(errorMessage));

      await store.loadPending();

      expect(store.error).toBe(errorMessage);
      expect(store.isLoading).toBe(false);
      expect(store.requests).toEqual([]);
    });
  });

  describe('loadAll', () => {
    it('should load all approvals without filter', async () => {
      const mockResponse = {
        requests: mockApprovalRequests,
        pending_count: 2,
      };

      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      await store.loadAll();

      expect(aiApi.listApprovals).toHaveBeenCalledWith(undefined);
      expect(store.requests).toEqual(mockApprovalRequests);
    });

    it('should load approvals with status filter', async () => {
      const firstRequest = mockApprovalRequests[0]!;
      const mockResponse = {
        requests: [firstRequest],
        pending_count: 1,
      };

      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      await store.loadAll('approved');

      expect(aiApi.listApprovals).toHaveBeenCalledWith('approved');
      expect(store.requests).toEqual([firstRequest]);
    });
  });

  describe('approve', () => {
    it('should approve request successfully', async () => {
      const mockResponse = {
        requests: [],
        pending_count: 0,
      };

      const mockApprovedRequest: ApprovalRequest = {
        id: '1',
        agent_name: 'issue_extractor',
        action_type: 'extract_issues',
        status: 'approved',
        created_at: '2026-01-26T10:00:00Z',
        expires_at: '2026-01-27T10:00:00Z',
        requested_by: 'John Doe',
        context_preview: '3 issues to create',
      };

      vi.mocked(aiApi.resolveApproval).mockResolvedValue(mockApprovedRequest);
      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      await store.approve('1', 'Looks good');

      expect(aiApi.resolveApproval).toHaveBeenCalledWith('1', {
        approved: true,
        note: 'Looks good',
        selected_issues: undefined,
      });
      expect(aiApi.listApprovals).toHaveBeenCalledWith('pending');
    });

    it('should approve with selected issues', async () => {
      const mockResponse = {
        requests: [],
        pending_count: 0,
      };

      const mockApprovedRequest: ApprovalRequest = {
        id: '1',
        agent_name: 'issue_extractor',
        action_type: 'extract_issues',
        status: 'approved',
        created_at: '2026-01-26T10:00:00Z',
        expires_at: '2026-01-27T10:00:00Z',
        requested_by: 'John Doe',
        context_preview: '3 issues to create',
      };

      vi.mocked(aiApi.resolveApproval).mockResolvedValue(mockApprovedRequest);
      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      await store.approve('1', undefined, [0, 2]);

      expect(aiApi.resolveApproval).toHaveBeenCalledWith('1', {
        approved: true,
        note: undefined,
        selected_issues: [0, 2],
      });
    });

    it('should handle approval errors', async () => {
      const errorMessage = 'Approval failed';
      vi.mocked(aiApi.resolveApproval).mockRejectedValue(new Error(errorMessage));

      await expect(store.approve('1')).rejects.toThrow();
      expect(store.error).toBe(errorMessage);
    });
  });

  describe('reject', () => {
    it('should reject request successfully', async () => {
      const mockResponse = {
        requests: [],
        pending_count: 0,
      };

      const mockRejectedRequest: ApprovalRequest = {
        id: '1',
        agent_name: 'issue_extractor',
        action_type: 'extract_issues',
        status: 'rejected',
        created_at: '2026-01-26T10:00:00Z',
        expires_at: '2026-01-27T10:00:00Z',
        requested_by: 'John Doe',
        context_preview: '3 issues to create',
      };

      vi.mocked(aiApi.resolveApproval).mockResolvedValue(mockRejectedRequest);
      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);

      await store.reject('1', 'Not needed');

      expect(aiApi.resolveApproval).toHaveBeenCalledWith('1', {
        approved: false,
        note: 'Not needed',
      });
      expect(aiApi.listApprovals).toHaveBeenCalledWith('pending');
    });

    it('should handle rejection errors', async () => {
      const errorMessage = 'Rejection failed';
      vi.mocked(aiApi.resolveApproval).mockRejectedValue(new Error(errorMessage));

      await expect(store.reject('1')).rejects.toThrow();
      expect(store.error).toBe(errorMessage);
    });
  });

  describe('selectRequest', () => {
    it('should set selected request', () => {
      expect(store.selectedRequest).toBeNull();

      const request = mockApprovalRequests[0];
      expect(request).toBeDefined();
      store.selectRequest(request!);
      expect(store.selectedRequest).toEqual(request);
    });

    it('should clear selected request', () => {
      const request = mockApprovalRequests[0];
      expect(request).toBeDefined();
      store.selectRequest(request!);
      expect(store.selectedRequest).not.toBeNull();

      store.selectRequest(null);
      expect(store.selectedRequest).toBeNull();
    });
  });

  describe('groupedByAgent', () => {
    it('should group requests by agent name', async () => {
      const mockResponse = {
        requests: mockApprovalRequests,
        pending_count: 2,
      };

      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);
      await store.loadPending();

      const grouped = store.groupedByAgent;

      expect(grouped).toHaveProperty('issue_extractor');
      expect(grouped).toHaveProperty('pr_review');
      expect(grouped.issue_extractor?.length).toBe(1);
      expect(grouped.pr_review?.length).toBe(1);
      expect(grouped.issue_extractor?.[0]?.id).toBe('1');
      expect(grouped.pr_review?.[0]?.id).toBe('2');
    });

    it('should return empty object when no requests', () => {
      expect(store.groupedByAgent).toEqual({});
    });
  });

  describe('setFilter', () => {
    it('should update filter state', () => {
      expect(store.filter).toBe('pending');

      store.setFilter('approved');
      expect(store.filter).toBe('approved');

      store.setFilter(undefined);
      expect(store.filter).toBeUndefined();
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', async () => {
      // Set up some state
      const mockResponse = {
        requests: mockApprovalRequests,
        pending_count: 2,
      };
      vi.mocked(aiApi.listApprovals).mockResolvedValue(mockResponse);
      await store.loadPending();
      const request = mockApprovalRequests[0];
      expect(request).toBeDefined();
      store.selectRequest(request!);
      store.setFilter('approved');

      // Reset
      store.reset();

      expect(store.requests).toEqual([]);
      expect(store.pendingCount).toBe(0);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
      expect(store.selectedRequest).toBeNull();
      expect(store.filter).toBe('pending');
    });
  });
});
