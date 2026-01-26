/**
 * Component tests for ApprovalDetailModal.
 *
 * T198: Tests for approval detail modal component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalDetailModal } from '../approval-detail-modal';
import type { ApprovalRequest } from '@/services/api/ai';

describe('ApprovalDetailModal', () => {
  const mockRequest: ApprovalRequest = {
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
      ],
    },
  };

  const mockOnOpenChange = vi.fn();
  const mockOnApprove = vi.fn();
  const mockOnReject = vi.fn();

  it('should render modal with request details', () => {
    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText('Approval Request')).toBeInTheDocument();
    expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    expect(screen.getByText('issue_extractor')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('should show payload preview', () => {
    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText('Action Payload')).toBeInTheDocument();
    expect(screen.getByText(/Issue 1/i)).toBeInTheDocument();
  });

  it('should show risk assessment for action type', () => {
    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText(/Risk Level/i)).toBeInTheDocument();
  });

  it('should show approve and reject buttons for pending requests', () => {
    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByRole('button', { name: /approve & execute/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('should not show action buttons for non-pending requests', () => {
    const approvedRequest = { ...mockRequest, status: 'approved' as const };
    render(
      <ApprovalDetailModal
        request={approvedRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
  });

  it('should call onApprove when approve button is clicked', async () => {
    const user = userEvent.setup();
    mockOnApprove.mockResolvedValue(undefined);

    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    const approveButton = screen.getByRole('button', { name: /approve & execute/i });
    await user.click(approveButton);

    expect(mockOnApprove).toHaveBeenCalled();
  });

  it('should call onReject when reject button is clicked', async () => {
    const user = userEvent.setup();
    mockOnReject.mockResolvedValue(undefined);

    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /^reject$/i });
    await user.click(rejectButton);

    expect(mockOnReject).toHaveBeenCalled();
  });

  it('should allow entering resolution note', async () => {
    const user = userEvent.setup();
    mockOnApprove.mockResolvedValue(undefined);

    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    const noteInput = screen.getByPlaceholderText(/add a note/i);
    await user.type(noteInput, 'This looks good to me');

    const approveButton = screen.getByRole('button', { name: /approve & execute/i });
    await user.click(approveButton);

    expect(mockOnApprove).toHaveBeenCalledWith('This looks good to me');
  });

  it('should show expired warning for expired requests', () => {
    const expiredRequest = {
      ...mockRequest,
      expires_at: '2026-01-20T10:00:00Z', // Past date
    };

    render(
      <ApprovalDetailModal
        request={expiredRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    expect(screen.getByText(/has expired/i)).toBeInTheDocument();
  });

  it('should copy payload to clipboard when copy button is clicked', async () => {
    const user = userEvent.setup();

    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });

    render(
      <ApprovalDetailModal
        request={mockRequest}
        open={true}
        onOpenChange={mockOnOpenChange}
        onApprove={mockOnApprove}
        onReject={mockOnReject}
      />
    );

    const copyButton = screen.getByRole('button', { name: /copy/i });
    await user.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      JSON.stringify(mockRequest.payload, null, 2)
    );
    expect(screen.getByText('Copied!')).toBeInTheDocument();
  });
});
