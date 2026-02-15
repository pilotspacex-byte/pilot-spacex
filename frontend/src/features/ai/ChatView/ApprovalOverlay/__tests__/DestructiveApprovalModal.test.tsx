/**
 * Unit tests for DestructiveApprovalModal component.
 *
 * Tests destructive action modal rendering, countdown timer, non-dismissable
 * behavior, approve/reject flows, payload preview routing, ARIA accessibility,
 * and null approval handling per DD-003 and spec 014 US-3.
 *
 * @module features/ai/ChatView/ApprovalOverlay/__tests__/DestructiveApprovalModal
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ApprovalRequest } from '../../types';

// Mock payload preview components
vi.mock('../IssuePreview', () => ({
  IssuePreview: (props: Record<string, unknown>) => (
    <div data-testid="issue-preview" data-issue={JSON.stringify(props.issue)} />
  ),
}));

vi.mock('../ContentDiff', () => ({
  ContentDiff: (props: Record<string, unknown>) => (
    <div data-testid="content-diff" data-before={props.before} data-after={props.after} />
  ),
}));

vi.mock('../GenericJSON', () => ({
  GenericJSON: (props: Record<string, unknown>) => (
    <div data-testid="generic-json" data-payload={JSON.stringify(props.payload)} />
  ),
}));

// Import after mocks are set up
import { DestructiveApprovalModal } from '../DestructiveApprovalModal';

function makeApproval(overrides?: Partial<ApprovalRequest>): ApprovalRequest {
  return {
    id: 'approval-1',
    agentName: 'PilotSpaceAgent',
    actionType: 'delete_issue',
    status: 'pending',
    contextPreview: 'Delete 5 issues from project Alpha',
    createdAt: new Date('2026-01-01T00:00:00Z'),
    expiresAt: new Date(Date.now() + 5 * 60 * 1000), // 5 minutes from now
    ...overrides,
  };
}

describe('DestructiveApprovalModal', () => {
  let mockOnApprove: ReturnType<typeof vi.fn>;
  let mockOnReject: ReturnType<typeof vi.fn>;
  let mockOnClose: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockOnApprove = vi.fn().mockResolvedValue(undefined);
    mockOnReject = vi.fn().mockResolvedValue(undefined);
    mockOnClose = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders when isOpen is true', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={false}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    });

    it('shows the formatted action type', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({ actionType: 'delete_issue' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Delete Issue')).toBeInTheDocument();
    });

    it('shows the agent name', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({ agentName: 'PilotSpaceAgent' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText(/PilotSpaceAgent/)).toBeInTheDocument();
    });

    it('shows the context preview', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({ contextPreview: 'Delete 5 issues from project Alpha' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Delete 5 issues from project Alpha')).toBeInTheDocument();
    });

    it('shows Approve and Reject buttons', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByTestId('approve-button')).toBeInTheDocument();
      expect(screen.getByTestId('reject-button')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Timer
  // ---------------------------------------------------------------------------

  describe('timer', () => {
    it('shows countdown starting near 05:00', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({ expiresAt: new Date(Date.now() + 5 * 60 * 1000) })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      // Timer uses padded format "05:00" or "04:59" depending on render timing
      expect(screen.getByText(/0[45]:\d{2}/)).toBeInTheDocument();
    });

    it('decrements the countdown every second', () => {
      const expiresAt = new Date(Date.now() + 5 * 60 * 1000);

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ expiresAt })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      // Advance 10 seconds
      act(() => {
        vi.advanceTimersByTime(10_000);
      });

      // Timer should show around 04:50 or 04:49 (padded format)
      expect(screen.getByText(/04:4\d|04:50/)).toBeInTheDocument();
    });

    it('auto-rejects when timer hits 0', () => {
      const expiresAt = new Date(Date.now() + 5 * 60 * 1000);

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ id: 'timeout-test', expiresAt })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      act(() => {
        vi.advanceTimersByTime(300_000); // 5 minutes
      });

      expect(mockOnReject).toHaveBeenCalledWith(
        'timeout-test',
        'Auto-rejected: approval timed out'
      );
    });

    it('timer has aria-live="polite"', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      const timerElement = screen.getByText(/\d{2}:\d{2}/);
      // The timer or its container should have aria-live
      const liveRegion = timerElement.closest('[aria-live]');
      expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    });
  });

  // ---------------------------------------------------------------------------
  // Non-dismissable behavior
  // ---------------------------------------------------------------------------

  describe('non-dismissable', () => {
    it('Escape key immediately rejects with default reason', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ id: 'escape-reject' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.keyboard('{Escape}');

      // Single Escape should reject immediately (US-3 scenario 3)
      expect(mockOnReject).toHaveBeenCalledTimes(1);
      expect(mockOnReject).toHaveBeenCalledWith('escape-reject', 'Rejected by user');
    });

    it('clicking outside does NOT close the dialog', async () => {
      const user = userEvent.setup({
        advanceTimers: vi.advanceTimersByTime,
        // Radix Dialog sets pointer-events: none on body; skip that check
        pointerEventsCheck: 0,
      });

      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      // Click on the overlay/backdrop area
      const dialog = screen.getByRole('alertdialog');
      const backdrop = dialog.parentElement;
      if (backdrop) {
        await user.click(backdrop);
      }

      // Dialog should still be present
      expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------------------
  // Approve flow
  // ---------------------------------------------------------------------------

  describe('approve flow', () => {
    it('calls onApprove with the correct id when Approve is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ id: 'destructive-123' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('approve-button'));

      expect(mockOnApprove).toHaveBeenCalledTimes(1);
      expect(mockOnApprove).toHaveBeenCalledWith('destructive-123');
    });

    it('shows loading state while approve is pending', async () => {
      let resolveApprove!: () => void;
      const slowApprove = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveApprove = resolve;
          })
      );
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={slowApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('approve-button'));

      // During loading, button text changes to "Approving..."
      expect(screen.getByText('Approving...')).toBeInTheDocument();
      expect(screen.getByTestId('approve-button')).toBeDisabled();

      await act(async () => {
        resolveApprove();
      });
    });

    it('disables both Approve and Reject buttons during loading', async () => {
      let resolveApprove!: () => void;
      const slowApprove = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveApprove = resolve;
          })
      );
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={slowApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('approve-button'));

      const buttons = screen.getAllByRole('button');
      for (const button of buttons) {
        expect(button).toBeDisabled();
      }

      await act(async () => {
        resolveApprove();
      });
    });
  });

  // ---------------------------------------------------------------------------
  // Reject flow
  // ---------------------------------------------------------------------------

  describe('reject flow', () => {
    it('shows rejection textarea when Reject is clicked', async () => {
      const user = userEvent.setup({
        advanceTimers: vi.advanceTimersByTime,
        pointerEventsCheck: 0,
      });

      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('reject-button'));

      expect(screen.getByPlaceholderText(/rejecting this action/i)).toBeInTheDocument();
    });

    it('allows confirming rejection without a reason (defaults to "Rejected by user")', async () => {
      const user = userEvent.setup({
        advanceTimers: vi.advanceTimersByTime,
        pointerEventsCheck: 0,
      });

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ id: 'no-reason-test' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('reject-button'));

      const confirmRejectButton = screen.getByTestId('confirm-reject-button');
      // Reason is optional, so button should NOT be disabled
      expect(confirmRejectButton).not.toBeDisabled();

      await user.click(confirmRejectButton);

      expect(mockOnReject).toHaveBeenCalledWith('no-reason-test', 'Rejected by user');
    });

    it('calls onReject with id and reason when rejection is confirmed with a reason', async () => {
      const user = userEvent.setup({
        advanceTimers: vi.advanceTimersByTime,
        pointerEventsCheck: 0,
      });

      render(
        <DestructiveApprovalModal
          approval={makeApproval({ id: 'reject-test' })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('reject-button'));
      await user.type(screen.getByPlaceholderText(/rejecting this action/i), 'Too risky right now');
      await user.click(screen.getByTestId('confirm-reject-button'));

      expect(mockOnReject).toHaveBeenCalledTimes(1);
      expect(mockOnReject).toHaveBeenCalledWith('reject-test', 'Too risky right now');
    });

    it('clears rejection form when going back from reject view', async () => {
      const user = userEvent.setup({
        advanceTimers: vi.advanceTimersByTime,
        pointerEventsCheck: 0,
      });

      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByTestId('reject-button'));
      await user.type(screen.getByPlaceholderText(/rejecting this action/i), 'Some text');

      // Click the Back button to return to main view
      const backButton = screen.getByRole('button', { name: /back/i });
      await user.click(backButton);

      // Should be back to Approve/Reject view
      expect(screen.getByTestId('approve-button')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText(/rejecting this action/i)).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Payload preview
  // ---------------------------------------------------------------------------

  describe('payload preview', () => {
    it('renders IssuePreview when actionType includes "issue" and payload has issue data', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({
            actionType: 'delete_issue',
            payload: { issue: { title: 'Bug fix', priority: 'high' } },
          })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByTestId('issue-preview')).toBeInTheDocument();
    });

    it('renders ContentDiff when actionType includes "update" and payload has before/after', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({
            actionType: 'update_description',
            payload: { before: 'old', after: 'new' },
          })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByTestId('content-diff')).toBeInTheDocument();
    });

    it('renders GenericJSON as fallback for other action types', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({
            actionType: 'delete_workspace',
            payload: { workspaceId: 'ws-1', name: 'Alpha' },
          })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByTestId('generic-json')).toBeInTheDocument();
    });

    it('renders no payload preview when payload is undefined', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval({ payload: undefined })}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByTestId('issue-preview')).not.toBeInTheDocument();
      expect(screen.queryByTestId('content-diff')).not.toBeInTheDocument();
      expect(screen.queryByTestId('generic-json')).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // ARIA accessibility
  // ---------------------------------------------------------------------------

  describe('ARIA', () => {
    it('has role="alertdialog"', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    });

    it('dialog is modal (traps focus and blocks interaction outside)', () => {
      render(
        <DestructiveApprovalModal
          approval={makeApproval()}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      const dialog = screen.getByRole('alertdialog');
      // Radix Dialog renders modal behavior; verify the dialog element exists
      // and has proper labelling for screen readers
      expect(dialog).toHaveAttribute('aria-labelledby', 'destructive-approval-title');
      expect(dialog).toHaveAttribute('aria-describedby', 'destructive-approval-description');
    });
  });

  // ---------------------------------------------------------------------------
  // Null approval
  // ---------------------------------------------------------------------------

  describe('null approval', () => {
    it('returns null when approval is null and isOpen is true', () => {
      const { container } = render(
        <DestructiveApprovalModal
          approval={null}
          isOpen={true}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      expect(container.innerHTML).toBe('');
    });

    it('returns null when approval is null and isOpen is false', () => {
      const { container } = render(
        <DestructiveApprovalModal
          approval={null}
          isOpen={false}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          onClose={mockOnClose}
        />
      );

      expect(container.innerHTML).toBe('');
    });
  });
});
