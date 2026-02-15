/**
 * Unit tests for InlineApprovalCard component.
 *
 * Tests inline non-destructive approval card rendering, approve/reject flows,
 * payload preview routing, collapsed states, ARIA accessibility, and keyboard
 * interaction per DD-003 and spec 014 US-2.
 *
 * @module features/ai/ChatView/MessageList/__tests__/InlineApprovalCard
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ApprovalRequest } from '../../types';

// Mock payload preview components
vi.mock('../../ApprovalOverlay/IssuePreview', () => ({
  IssuePreview: (props: Record<string, unknown>) => (
    <div data-testid="issue-preview" data-issue={JSON.stringify(props.issue)} />
  ),
}));

vi.mock('../../ApprovalOverlay/ContentDiff', () => ({
  ContentDiff: (props: Record<string, unknown>) => (
    <div data-testid="content-diff" data-before={props.before} data-after={props.after} />
  ),
}));

vi.mock('../../ApprovalOverlay/GenericJSON', () => ({
  GenericJSON: (props: Record<string, unknown>) => (
    <div data-testid="generic-json" data-payload={JSON.stringify(props.payload)} />
  ),
}));

// Import after mocks are set up
import { InlineApprovalCard } from '../InlineApprovalCard';

function makeApproval(overrides?: Partial<ApprovalRequest>): ApprovalRequest {
  return {
    id: 'approval-1',
    agentName: 'PilotSpaceAgent',
    actionType: 'add_label',
    status: 'pending',
    contextPreview: 'Add "bug" label to issue PS-42',
    createdAt: new Date('2026-01-01'),
    expiresAt: new Date('2026-01-02'),
    ...overrides,
  };
}

describe('InlineApprovalCard', () => {
  let mockOnApprove: ReturnType<typeof vi.fn>;
  let mockOnReject: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnApprove = vi.fn().mockResolvedValue(undefined);
    mockOnReject = vi.fn().mockResolvedValue(undefined);
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  describe('rendering', () => {
    it('includes action type in aria-label', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({ actionType: 'add_label' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-label', expect.stringContaining('add_label'));
    });

    it('renders the context preview text', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({ contextPreview: 'Add "bug" label to issue PS-42' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByText('Add "bug" label to issue PS-42')).toBeInTheDocument();
    });

    it('renders an "AI Suggestion" badge', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByText('AI Suggestion')).toBeInTheDocument();
    });

    it('renders both Approve and Reject buttons', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
          className="custom-test-class"
        />
      );

      const region = screen.getByRole('region');
      expect(region).toHaveClass('custom-test-class');
    });
  });

  // ---------------------------------------------------------------------------
  // Payload preview
  // ---------------------------------------------------------------------------

  describe('payload preview', () => {
    it('renders IssuePreview when actionType includes "issue" and payload has issue data', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({
            actionType: 'create_issue',
            payload: { issue: { title: 'Fix login bug', priority: 'high' } },
          })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByTestId('issue-preview')).toBeInTheDocument();
    });

    it('renders ContentDiff when actionType includes "update" and payload has before/after strings', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({
            actionType: 'update_description',
            payload: { before: 'old text', after: 'new text' },
          })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByTestId('content-diff')).toBeInTheDocument();
    });

    it('renders GenericJSON as fallback when actionType is neither "issue" nor "update"', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({
            actionType: 'add_label',
            payload: { label: 'bug', color: 'red' },
          })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByTestId('generic-json')).toBeInTheDocument();
    });

    it('renders no payload preview when payload is undefined', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({ payload: undefined })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.queryByTestId('issue-preview')).not.toBeInTheDocument();
      expect(screen.queryByTestId('content-diff')).not.toBeInTheDocument();
      expect(screen.queryByTestId('generic-json')).not.toBeInTheDocument();
    });

    it('renders GenericJSON when actionType includes "issue" but payload has no issue key', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({
            actionType: 'create_issue',
            payload: { name: 'something' },
          })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      // Falls back to GenericJSON since payload.issue is missing
      expect(screen.getByTestId('generic-json')).toBeInTheDocument();
      expect(screen.queryByTestId('issue-preview')).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Approve flow
  // ---------------------------------------------------------------------------

  describe('approve flow', () => {
    it('calls onApprove with the correct approval id', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval({ id: 'approval-xyz' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      expect(mockOnApprove).toHaveBeenCalledTimes(1);
      expect(mockOnApprove).toHaveBeenCalledWith('approval-xyz');
    });

    it('shows loading state while approve is pending', async () => {
      let resolveApprove!: () => void;
      const slowApprove = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveApprove = resolve;
          })
      );
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={slowApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      // Approve button should indicate loading
      const approveButton = screen.getByRole('button', { name: /approv/i });
      expect(approveButton).toHaveAttribute('aria-busy', 'true');

      resolveApprove();
    });

    it('disables both buttons while approve is in progress', async () => {
      let resolveApprove!: () => void;
      const slowApprove = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveApprove = resolve;
          })
      );
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={slowApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      const buttons = screen.getAllByRole('button');
      for (const button of buttons) {
        expect(button).toBeDisabled();
      }

      resolveApprove();
    });

    it('shows approved collapsed state after successful approval', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval({ actionType: 'add_label' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Reject flow
  // ---------------------------------------------------------------------------

  describe('reject flow', () => {
    it('shows rejection textarea when Reject is clicked', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));

      expect(screen.getByPlaceholderText(/reason/i)).toBeInTheDocument();
    });

    it('sends default reason "Rejected" when textarea is empty', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval({ id: 'empty-reason' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      await user.click(screen.getByRole('button', { name: /confirm reject/i }));

      expect(mockOnReject).toHaveBeenCalledWith('empty-reason', 'Rejected');
    });

    it('calls onReject with id and reason when rejection is confirmed', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval({ id: 'approval-abc' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      await user.type(screen.getByPlaceholderText(/reason/i), 'Not the right approach');
      await user.click(screen.getByRole('button', { name: /confirm reject/i }));

      expect(mockOnReject).toHaveBeenCalledTimes(1);
      expect(mockOnReject).toHaveBeenCalledWith('approval-abc', 'Not the right approach');
    });

    it('shows rejected collapsed state with reason after rejection', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      await user.type(screen.getByPlaceholderText(/reason/i), 'Wrong label');
      await user.click(screen.getByRole('button', { name: /confirm reject/i }));

      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
      expect(screen.getByText(/wrong label/i)).toBeInTheDocument();
    });

    it('cancels rejection form on Escape key', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      const textarea = screen.getByPlaceholderText(/reason/i);
      expect(textarea).toBeInTheDocument();

      // Focus textarea explicitly then press Escape
      textarea.focus();
      await user.keyboard('{Escape}');

      // Rejection form should be gone, original buttons should be back
      expect(screen.queryByPlaceholderText(/reason/i)).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Collapsed states
  // ---------------------------------------------------------------------------

  describe('collapsed states', () => {
    it('approved state shows green check and "Approved" text', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });

    it('rejected state shows red X and "Rejected: {reason}" text', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      await user.type(screen.getByPlaceholderText(/reason/i), 'Incorrect target');
      await user.click(screen.getByRole('button', { name: /confirm reject/i }));

      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
      expect(screen.getByText(/incorrect target/i)).toBeInTheDocument();
    });

    it('has no interactive buttons in approved collapsed state', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      // No approve/reject buttons should remain
      expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
    });

    it('has no interactive buttons in rejected collapsed state', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject/i }));
      await user.type(screen.getByPlaceholderText(/reason/i), 'Nope');
      await user.click(screen.getByRole('button', { name: /confirm reject/i }));

      expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // ARIA accessibility
  // ---------------------------------------------------------------------------

  describe('ARIA', () => {
    it('has role="region"', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByRole('region')).toBeInTheDocument();
    });

    it('has aria-label that includes the actionType', () => {
      render(
        <InlineApprovalCard
          approval={makeApproval({ actionType: 'add_label' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const region = screen.getByRole('region');
      expect(region).toHaveAttribute('aria-label', expect.stringContaining('add_label'));
    });

    it('sets aria-busy on approve button during loading', async () => {
      let resolveApprove!: () => void;
      const slowApprove = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            resolveApprove = resolve;
          })
      );
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={slowApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve/i }));

      const approveButton = screen.getByRole('button', { name: /approv/i });
      expect(approveButton).toHaveAttribute('aria-busy', 'true');

      resolveApprove();
    });
  });

  // ---------------------------------------------------------------------------
  // Keyboard interaction
  // ---------------------------------------------------------------------------

  describe('keyboard', () => {
    it('can Tab between Approve and Reject buttons', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval()}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const approveButton = screen.getByRole('button', { name: /approve/i });
      const rejectButton = screen.getByRole('button', { name: /reject/i });

      await user.tab();
      // One of the buttons should have focus after tabbing
      const activeElement = document.activeElement;
      expect(activeElement === approveButton || activeElement === rejectButton).toBe(true);
    });

    it('Enter key on Approve button triggers approve', async () => {
      const user = userEvent.setup();

      render(
        <InlineApprovalCard
          approval={makeApproval({ id: 'keyboard-test' })}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const approveButton = screen.getByRole('button', { name: /approve/i });
      approveButton.focus();
      await user.keyboard('{Enter}');

      expect(mockOnApprove).toHaveBeenCalledWith('keyboard-test');
    });
  });
});
