/**
 * Integration tests for approval flow.
 *
 * T199: Integration test for complete approve/reject workflow.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalQueuePage } from '../pages/approval-queue-page';
import { StoreContext, RootStore } from '@/stores/RootStore';
import { aiApi } from '@/services/api/ai';
import type { ApprovalRequest } from '@/services/api/ai';

// Mock the API
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    listApprovals: vi.fn(),
    resolveApproval: vi.fn(),
  },
}));

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('Approval Flow Integration', () => {
  let rootStore: RootStore;
  const user = userEvent.setup();

  const mockPendingRequests: ApprovalRequest[] = [
    {
      id: '1',
      agent_name: 'issue_extractor',
      action_type: 'extract_issues',
      status: 'pending',
      created_at: '2026-01-26T10:00:00Z',
      expires_at: '2026-01-27T10:00:00Z',
      requested_by: 'John Doe',
      context_preview: '3 issues to create from note',
      payload: {
        issues: [
          { title: 'Issue 1', description: 'Description 1' },
          { title: 'Issue 2', description: 'Description 2' },
          { title: 'Issue 3', description: 'Description 3' },
        ],
      },
    },
    {
      id: '2',
      agent_name: 'pr_review',
      action_type: 'post_pr_comments',
      status: 'pending',
      created_at: '2026-01-26T11:00:00Z',
      expires_at: '2026-01-27T11:00:00Z',
      requested_by: 'Jane Smith',
      context_preview: 'Post 5 review comments on PR #123',
      payload: {
        comments: [
          { line: 42, body: 'Consider using async/await here' },
          { line: 58, body: 'Add error handling' },
        ],
      },
    },
  ];

  beforeEach(() => {
    rootStore = new RootStore();
    vi.clearAllMocks();
  });

  const renderWithStore = (component: React.ReactElement) => {
    return render(<StoreContext.Provider value={rootStore}>{component}</StoreContext.Provider>);
  };

  it('should display pending approvals on page load', async () => {
    vi.mocked(aiApi.listApprovals).mockResolvedValue({
      requests: mockPendingRequests,
      pending_count: 2,
    });

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
      expect(screen.getByText('Post 5 review comments on PR #123')).toBeInTheDocument();
    });

    expect(screen.getByText('2 pending')).toBeInTheDocument();
  });

  it('should show empty state when no pending approvals', async () => {
    vi.mocked(aiApi.listApprovals).mockResolvedValue({
      requests: [],
      pending_count: 0,
    });

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('No Pending Approvals')).toBeInTheDocument();
    });
  });

  it('should open detail modal when clicking on approval card', async () => {
    vi.mocked(aiApi.listApprovals).mockResolvedValue({
      requests: mockPendingRequests,
      pending_count: 2,
    });

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    });

    // Click on first approval card
    const card = screen.getByText('3 issues to create from note').closest('div[data-testid]');
    if (card) {
      await user.click(card);
    }

    await waitFor(() => {
      expect(screen.getByText('Approval Request')).toBeInTheDocument();
      expect(screen.getByText('Action Payload')).toBeInTheDocument();
    });
  });

  it('should approve request and reload list', async () => {
    const secondRequest = mockPendingRequests[1];
    expect(secondRequest).toBeDefined();

    vi.mocked(aiApi.listApprovals)
      .mockResolvedValueOnce({
        requests: mockPendingRequests,
        pending_count: 2,
      })
      .mockResolvedValueOnce({
        requests: [secondRequest!],
        pending_count: 1,
      });

    const mockResolvedRequest: ApprovalRequest = {
      id: '1',
      agent_name: 'issue_extractor',
      action_type: 'extract_issues',
      status: 'approved',
      created_at: '2026-01-26T10:00:00Z',
      expires_at: '2026-01-27T10:00:00Z',
      requested_by: 'John Doe',
      context_preview: '3 issues to create from note',
    };

    vi.mocked(aiApi.resolveApproval).mockResolvedValue(mockResolvedRequest);

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    });

    // Open detail modal
    const cardText = screen.getByText('3 issues to create from note');
    const card = cardText.closest('div[data-testid]');
    if (!card) throw new Error('Card not found');
    await user.click(card);

    // Wait for modal to open
    await waitFor(() => {
      expect(screen.getByText('Approval Request')).toBeInTheDocument();
    });

    // Click approve button
    const approveButton = screen.getByRole('button', { name: /approve & execute/i });
    await user.click(approveButton);

    // Verify API was called
    await waitFor(() => {
      expect(aiApi.resolveApproval).toHaveBeenCalledWith('1', {
        approved: true,
        note: undefined,
        selected_issues: undefined,
      });
    });

    // Verify list was reloaded and first item is gone
    await waitFor(() => {
      expect(screen.queryByText('3 issues to create from note')).not.toBeInTheDocument();
      expect(screen.getByText('Post 5 review comments on PR #123')).toBeInTheDocument();
      expect(screen.getByText('1 pending')).toBeInTheDocument();
    });
  });

  it('should reject request with note and reload list', async () => {
    const firstRequest = mockPendingRequests[0];
    expect(firstRequest).toBeDefined();

    vi.mocked(aiApi.listApprovals)
      .mockResolvedValueOnce({
        requests: mockPendingRequests,
        pending_count: 2,
      })
      .mockResolvedValueOnce({
        requests: [firstRequest!],
        pending_count: 1,
      });

    const mockResolvedRequest: ApprovalRequest = {
      id: '1',
      agent_name: 'issue_extractor',
      action_type: 'extract_issues',
      status: 'approved',
      created_at: '2026-01-26T10:00:00Z',
      expires_at: '2026-01-27T10:00:00Z',
      requested_by: 'John Doe',
      context_preview: '3 issues to create from note',
    };

    vi.mocked(aiApi.resolveApproval).mockResolvedValue(mockResolvedRequest);

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('Post 5 review comments on PR #123')).toBeInTheDocument();
    });

    // Open detail modal
    const cardText = screen.getByText('Post 5 review comments on PR #123');
    const card = cardText.closest('div[data-testid]');
    if (!card) throw new Error('Card not found');
    await user.click(card);

    // Wait for modal
    await waitFor(() => {
      expect(screen.getByText('Approval Request')).toBeInTheDocument();
    });

    // Enter rejection note
    const noteInput = screen.getByPlaceholderText(/add a note/i);
    await user.type(noteInput, 'Not needed, handled manually');

    // Click reject button
    const rejectButton = screen.getByRole('button', { name: /^reject$/i });
    await user.click(rejectButton);

    // Verify API was called with note
    await waitFor(() => {
      expect(aiApi.resolveApproval).toHaveBeenCalledWith('2', {
        approved: false,
        note: 'Not needed, handled manually',
      });
    });

    // Verify list was reloaded
    await waitFor(() => {
      expect(screen.queryByText('Post 5 review comments on PR #123')).not.toBeInTheDocument();
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    });
  });

  it('should filter approvals by status', async () => {
    const firstRequest = mockPendingRequests[0];
    expect(firstRequest).toBeDefined();

    const approvedRequest: ApprovalRequest = {
      ...firstRequest!,
      status: 'approved' as const,
    };

    vi.mocked(aiApi.listApprovals)
      .mockResolvedValueOnce({
        requests: mockPendingRequests,
        pending_count: 2,
      })
      .mockResolvedValueOnce({
        requests: [approvedRequest],
        pending_count: 2,
      });

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    });

    // Click on "Approved" tab
    const approvedTab = screen.getByRole('tab', { name: /approved/i });
    await user.click(approvedTab);

    // Verify filter was applied
    await waitFor(() => {
      expect(aiApi.listApprovals).toHaveBeenCalledWith('approved');
    });
  });

  it('should handle API errors gracefully', async () => {
    vi.mocked(aiApi.listApprovals).mockRejectedValue(new Error('Network error'));

    renderWithStore(<ApprovalQueuePage />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('should show loading state while fetching approvals', async () => {
    vi.mocked(aiApi.listApprovals).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                requests: mockPendingRequests,
                pending_count: 2,
              }),
            100
          )
        )
    );

    renderWithStore(<ApprovalQueuePage />);

    // Check for loading spinner
    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    });
  });
});
