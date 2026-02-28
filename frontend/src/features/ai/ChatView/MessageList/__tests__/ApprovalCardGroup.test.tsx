/**
 * Unit tests for ApprovalCardGroup component.
 *
 * Tests batch grouping of inline approval cards, Approve All / Reject All
 * bulk actions, partial failure surfacing, expand/collapse, and ARIA.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ApprovalCardGroup
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ApprovalRequest } from '../../types';

// Mock InlineApprovalCard to avoid full card rendering complexity
vi.mock('../InlineApprovalCard', () => ({
  InlineApprovalCard: ({ approval }: { approval: ApprovalRequest }) => (
    <div data-testid={`inline-card-${approval.id}`} />
  ),
}));

// Import after mocks are set up
import { ApprovalCardGroup } from '../ApprovalCardGroup';

function makeApproval(id: string, overrides?: Partial<ApprovalRequest>): ApprovalRequest {
  return {
    id,
    agentName: 'PilotSpaceAgent',
    actionType: 'add_label',
    status: 'pending',
    contextPreview: `Approval ${id}`,
    createdAt: new Date(),
    expiresAt: new Date(Date.now() + 86400000),
    ...overrides,
  };
}

function makeApprovals(count: number): ApprovalRequest[] {
  return Array.from({ length: count }, (_, i) => makeApproval(`approval-${i + 1}`));
}

describe('ApprovalCardGroup', () => {
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
    it('renders the correct approval count in the header', () => {
      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByText('3 Pending Approvals')).toBeInTheDocument();
    });

    it('renders all approval cards when expanded', () => {
      const approvals = makeApprovals(4);
      render(
        <ApprovalCardGroup
          approvals={approvals}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      for (const a of approvals) {
        expect(screen.getByTestId(`inline-card-${a.id}`)).toBeInTheDocument();
      }
    });

    it('starts in expanded state', () => {
      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByRole('button', { name: /3 pending approvals/i })).toHaveAttribute(
        'aria-expanded',
        'true'
      );
    });

    it('renders Approve All and Reject All buttons', () => {
      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByRole('button', { name: /approve all/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reject all/i })).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Collapse / Expand
  // ---------------------------------------------------------------------------

  describe('collapse / expand', () => {
    it('hides cards when toggled to collapsed', async () => {
      const user = userEvent.setup();
      const approvals = makeApprovals(3);

      render(
        <ApprovalCardGroup
          approvals={approvals}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /3 pending approvals/i }));

      for (const a of approvals) {
        expect(screen.queryByTestId(`inline-card-${a.id}`)).not.toBeInTheDocument();
      }
    });

    it('sets aria-expanded false when collapsed', async () => {
      const user = userEvent.setup();

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const toggleBtn = screen.getByRole('button', { name: /3 pending approvals/i });
      await user.click(toggleBtn);
      expect(toggleBtn).toHaveAttribute('aria-expanded', 'false');
    });

    it('restores cards after expand → collapse → expand', async () => {
      const user = userEvent.setup();
      const approvals = makeApprovals(3);

      render(
        <ApprovalCardGroup
          approvals={approvals}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const toggleBtn = screen.getByRole('button', { name: /3 pending approvals/i });
      await user.click(toggleBtn); // collapse
      await user.click(toggleBtn); // re-expand

      for (const a of approvals) {
        expect(screen.getByTestId(`inline-card-${a.id}`)).toBeInTheDocument();
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Approve All
  // ---------------------------------------------------------------------------

  describe('Approve All', () => {
    it('calls onApprove for each approval id', async () => {
      const user = userEvent.setup();
      const approvals = makeApprovals(3);

      render(
        <ApprovalCardGroup
          approvals={approvals}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve all/i }));
      await waitFor(() => expect(mockOnApprove).toHaveBeenCalledTimes(3));

      for (const a of approvals) {
        expect(mockOnApprove).toHaveBeenCalledWith(a.id);
      }
    });

    it('disables bulk buttons while batch is in-flight', async () => {
      const user = userEvent.setup();
      // Never resolves — simulates in-flight request
      const neverResolve = vi.fn(() => new Promise<void>(() => {}));

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={neverResolve}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve all/i }));

      expect(screen.getByRole('button', { name: /approve all/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /reject all/i })).toBeDisabled();
    });

    it('shows singular error when 1 approval fails', async () => {
      const user = userEvent.setup();
      let callCount = 0;
      const partialFail = vi.fn(() => {
        callCount++;
        return callCount === 2 ? Promise.reject(new Error('network')) : Promise.resolve();
      });

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={partialFail}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve all/i }));

      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
      expect(screen.getByRole('alert')).toHaveTextContent('1 approval failed to process');
    });

    it('shows plural error when multiple approvals fail', async () => {
      const user = userEvent.setup();
      const alwaysFail = vi.fn(() => Promise.reject(new Error('fail')));

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={alwaysFail}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve all/i }));

      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
      expect(screen.getByRole('alert')).toHaveTextContent('3 approvals failed to process');
    });

    it('clears batch error when re-attempting approve all', async () => {
      const user = userEvent.setup();
      let attempt = 0;
      const failThenSucceed = vi.fn(() => {
        attempt++;
        return attempt <= 3 ? Promise.reject(new Error('fail')) : Promise.resolve();
      });

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={failThenSucceed}
          onReject={mockOnReject}
        />
      );

      // First attempt: all 3 fail
      await user.click(screen.getByRole('button', { name: /approve all/i }));
      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());

      // Second attempt: all 3 succeed
      await user.click(screen.getByRole('button', { name: /approve all/i }));
      await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    });
  });

  // ---------------------------------------------------------------------------
  // Reject All
  // ---------------------------------------------------------------------------

  describe('Reject All', () => {
    it('calls onReject with "Batch rejected" for each approval', async () => {
      const user = userEvent.setup();
      const approvals = makeApprovals(3);

      render(
        <ApprovalCardGroup
          approvals={approvals}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject all/i }));
      await waitFor(() => expect(mockOnReject).toHaveBeenCalledTimes(3));

      for (const a of approvals) {
        expect(mockOnReject).toHaveBeenCalledWith(a.id, 'Batch rejected');
      }
    });

    it('shows singular error when 1 rejection fails', async () => {
      const user = userEvent.setup();
      const partialFail = vi.fn((id: string) =>
        id === 'approval-1' ? Promise.reject(new Error('fail')) : Promise.resolve()
      );

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={partialFail}
        />
      );

      await user.click(screen.getByRole('button', { name: /reject all/i }));

      await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
      expect(screen.getByRole('alert')).toHaveTextContent('1 rejection failed to process');
    });
  });

  // ---------------------------------------------------------------------------
  // Accessibility
  // ---------------------------------------------------------------------------

  describe('accessibility', () => {
    it('has role="region" with descriptive label', () => {
      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      expect(screen.getByRole('region')).toHaveAttribute('aria-label', '3 pending approvals');
    });

    it('toggle button aria-controls references the cards list element', () => {
      const { container } = render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={mockOnApprove}
          onReject={mockOnReject}
        />
      );

      const toggleBtn = screen.getByRole('button', { name: /3 pending approvals/i });
      const controlsId = toggleBtn.getAttribute('aria-controls');

      expect(controlsId).toBeTruthy();
      expect(container.querySelector(`#${CSS.escape(controlsId!)}`)).toBeInTheDocument();
    });

    it('batch error is announced via role="alert"', async () => {
      const user = userEvent.setup();
      const alwaysFail = vi.fn(() => Promise.reject(new Error('fail')));

      render(
        <ApprovalCardGroup
          approvals={makeApprovals(3)}
          onApprove={alwaysFail}
          onReject={mockOnReject}
        />
      );

      await user.click(screen.getByRole('button', { name: /approve all/i }));

      await waitFor(() => {
        const alert = screen.getByRole('alert');
        expect(alert).toBeInTheDocument();
      });
    });
  });
});
