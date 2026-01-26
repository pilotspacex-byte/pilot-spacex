/**
 * Component tests for ApprovalCard.
 *
 * T198: Tests for approval card component rendering and interactions.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalCard } from '../approval-card';
import type { ApprovalRequest } from '@/services/api/ai';

describe('ApprovalCard', () => {
  const mockRequest: ApprovalRequest = {
    id: '1',
    agent_name: 'issue_extractor',
    action_type: 'extract_issues',
    status: 'pending',
    created_at: '2026-01-26T10:00:00Z',
    expires_at: '2026-01-27T10:00:00Z',
    requested_by: 'John Doe',
    context_preview: '3 issues to create from note',
    payload: { issues: [{ title: 'Issue 1' }] },
  };

  const mockOnSelect = vi.fn();
  const mockOnQuickApprove = vi.fn();
  const mockOnQuickReject = vi.fn();

  it('should render approval card with correct information', () => {
    render(<ApprovalCard request={mockRequest} onSelect={mockOnSelect} />);

    expect(screen.getByText('3 issues to create from note')).toBeInTheDocument();
    expect(screen.getByText('issue_extractor')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText(/Extract Issues/i)).toBeInTheDocument();
  });

  it('should show pending status badge', () => {
    render(<ApprovalCard request={mockRequest} onSelect={mockOnSelect} />);

    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('should show approved status badge', () => {
    const approvedRequest = { ...mockRequest, status: 'approved' as const };
    render(<ApprovalCard request={approvedRequest} onSelect={mockOnSelect} />);

    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('should show rejected status badge', () => {
    const rejectedRequest = { ...mockRequest, status: 'rejected' as const };
    render(<ApprovalCard request={rejectedRequest} onSelect={mockOnSelect} />);

    expect(screen.getByText('Rejected')).toBeInTheDocument();
  });

  it('should show expired status badge', () => {
    const expiredRequest = { ...mockRequest, status: 'expired' as const };
    render(<ApprovalCard request={expiredRequest} onSelect={mockOnSelect} />);

    expect(screen.getByText('Expired')).toBeInTheDocument();
  });

  it('should call onSelect when card is clicked', async () => {
    const user = userEvent.setup();
    render(<ApprovalCard request={mockRequest} onSelect={mockOnSelect} />);

    const card = screen.getByTestId(`approval-card-${mockRequest.id}`);
    await user.click(card);

    expect(mockOnSelect).toHaveBeenCalledWith(mockRequest);
  });

  it('should show quick action buttons for pending requests', () => {
    render(
      <ApprovalCard
        request={mockRequest}
        onSelect={mockOnSelect}
        onQuickApprove={mockOnQuickApprove}
        onQuickReject={mockOnQuickReject}
      />
    );

    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
  });

  it('should not show quick actions for non-pending requests', () => {
    const approvedRequest = { ...mockRequest, status: 'approved' as const };
    render(
      <ApprovalCard
        request={approvedRequest}
        onSelect={mockOnSelect}
        onQuickApprove={mockOnQuickApprove}
        onQuickReject={mockOnQuickReject}
      />
    );

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
  });

  it('should call onQuickApprove when approve button is clicked', async () => {
    const user = userEvent.setup();
    mockOnQuickApprove.mockResolvedValue(undefined);

    render(
      <ApprovalCard
        request={mockRequest}
        onSelect={mockOnSelect}
        onQuickApprove={mockOnQuickApprove}
        onQuickReject={mockOnQuickReject}
      />
    );

    const approveButton = screen.getByRole('button', { name: /approve/i });
    await user.click(approveButton);

    expect(mockOnQuickApprove).toHaveBeenCalledWith(mockRequest.id);
    expect(mockOnSelect).not.toHaveBeenCalled();
  });

  it('should call onQuickReject when reject button is clicked', async () => {
    const user = userEvent.setup();
    mockOnQuickReject.mockResolvedValue(undefined);

    render(
      <ApprovalCard
        request={mockRequest}
        onSelect={mockOnSelect}
        onQuickApprove={mockOnQuickApprove}
        onQuickReject={mockOnQuickReject}
      />
    );

    const rejectButton = screen.getByRole('button', { name: /reject/i });
    await user.click(rejectButton);

    expect(mockOnQuickReject).toHaveBeenCalledWith(mockRequest.id);
    expect(mockOnSelect).not.toHaveBeenCalled();
  });

  it('should show expiration indicator for pending requests', () => {
    render(<ApprovalCard request={mockRequest} onSelect={mockOnSelect} />);

    // Check for "Expires" text or clock icon
    expect(screen.getByText(/expires/i)).toBeInTheDocument();
  });

  it('should highlight border for pending requests', () => {
    render(<ApprovalCard request={mockRequest} onSelect={mockOnSelect} />);

    const card = screen.getByTestId(`approval-card-${mockRequest.id}`);
    expect(card).toHaveClass('border-l-4', 'border-l-yellow-500');
  });
});
