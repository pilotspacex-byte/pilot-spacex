/**
 * Tests for DecisionRenderer component.
 *
 * DecisionRenderer displays Decision Record PM blocks with:
 * - Status banner (Open → Decided → Superseded) state machine
 * - Option cards with pros/cons/effort/risk metadata
 * - Selection buttons in open status
 * - Status transition buttons (Decide/Supersede)
 * - Rationale and decision date display
 * - Create Issue button when decided
 * - Superseded indicator
 *
 * Spec refs: FR-020 (state machine), FR-021 (binary/multi-option),
 * FR-022 (pros/cons/effort/risk), FR-023 (decision recording),
 * FR-024 (create issue)
 *
 * @module pm-blocks/__tests__/DecisionRenderer.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DecisionRenderer } from '../renderers/DecisionRenderer';

const defaultProps = {
  data: {} as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'decision' as const,
};

// ── Basic rendering ─────────────────────────────────────────────────────
describe('DecisionRenderer basic rendering', () => {
  it('renders the root element with data-testid', () => {
    render(<DecisionRenderer {...defaultProps} />);
    expect(screen.getByTestId('decision-renderer')).toBeInTheDocument();
  });

  it('renders default title when empty data object passed', () => {
    render(<DecisionRenderer {...defaultProps} data={{}} />);
    expect(screen.getByText('Untitled Decision')).toBeInTheDocument();
  });

  it('renders custom title when provided', () => {
    const data = { title: 'Choose database technology' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Choose database technology')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    const data = {
      title: 'Decision',
      description: 'We need to pick a database for the new service',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('We need to pick a database for the new service')).toBeInTheDocument();
  });

  it('renders default options when no options provided', () => {
    render(<DecisionRenderer {...defaultProps} data={{}} />);
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option B')).toBeInTheDocument();
  });
});

// ── Status banner ───────────────────────────────────────────────────────
describe('DecisionRenderer status banner', () => {
  it('shows "Open" status for open status', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('Open');
  });

  it('shows "Decided" status for decided status', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('Decided');
  });

  it('shows "Superseded" status for superseded status', () => {
    const data = { status: 'superseded' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent('Superseded');
  });

  it('has proper aria-label for accessibility', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const banner = screen.getByRole('status');
    expect(banner).toHaveAttribute('aria-label', 'Decision status: Open');
  });
});

// ── Status transitions ──────────────────────────────────────────────────
describe('DecisionRenderer status transitions', () => {
  it('shows "Decide →" button when status is open and not readOnly', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Mark as decided')).toBeInTheDocument();
  });

  it('does not show "Decide →" button when readOnly', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Mark as decided')).not.toBeInTheDocument();
  });

  it('clicking "Decide →" calls onDataChange with status=decided and decisionDate', async () => {
    const onDataChange = vi.fn();
    const data = { status: 'open', title: 'Test' };
    render(<DecisionRenderer {...defaultProps} data={data} onDataChange={onDataChange} />);

    const decideButton = screen.getByLabelText('Mark as decided');
    await userEvent.click(decideButton);

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 'decided',
        decisionDate: expect.any(String),
      })
    );

    // Verify date format is YYYY-MM-DD
    const call = onDataChange.mock.calls[0]![0];
    expect(call.decisionDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('shows "Supersede →" button when status is decided and not readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Mark as superseded')).toBeInTheDocument();
  });

  it('does not show "Supersede →" button when readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Mark as superseded')).not.toBeInTheDocument();
  });

  it('clicking "Supersede →" calls onDataChange with status=superseded', async () => {
    const onDataChange = vi.fn();
    const data = { status: 'decided', title: 'Test' };
    render(<DecisionRenderer {...defaultProps} data={data} onDataChange={onDataChange} />);

    const supersedeButton = screen.getByLabelText('Mark as superseded');
    await userEvent.click(supersedeButton);

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 'superseded',
      })
    );
  });

  it('does not show transition buttons when status is superseded', () => {
    const data = { status: 'superseded' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Mark as decided')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Mark as superseded')).not.toBeInTheDocument();
  });
});

// ── Option cards ────────────────────────────────────────────────────────
describe('DecisionRenderer option cards', () => {
  it('renders all options from data', () => {
    const data = {
      options: [
        { id: 'opt-1', label: 'PostgreSQL', pros: [], cons: [] },
        { id: 'opt-2', label: 'MongoDB', pros: [], cons: [] },
        { id: 'opt-3', label: 'DynamoDB', pros: [], cons: [] },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
    expect(screen.getByText('MongoDB')).toBeInTheDocument();
    expect(screen.getByText('DynamoDB')).toBeInTheDocument();
  });

  it('renders option with data-testid', () => {
    const data = {
      options: [{ id: 'opt-1', label: 'Option A', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByTestId('option-card-opt-1')).toBeInTheDocument();
  });

  it('shows "Select" button on unselected option when status is open and not readOnly', () => {
    const data = {
      status: 'open',
      options: [{ id: 'opt-1', label: 'Option A', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Select Option A')).toBeInTheDocument();
  });

  it('does not show "Select" button when readOnly', () => {
    const data = {
      status: 'open',
      options: [{ id: 'opt-1', label: 'Option A', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Select Option A')).not.toBeInTheDocument();
  });

  it('does not show "Select" button when status is not open', () => {
    const data = {
      status: 'decided',
      options: [{ id: 'opt-1', label: 'Option A', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Select Option A')).not.toBeInTheDocument();
  });

  it('clicking Select button calls onDataChange with selectedOptionId', async () => {
    const onDataChange = vi.fn();
    const data = {
      status: 'open',
      options: [{ id: 'opt-1', label: 'PostgreSQL', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} onDataChange={onDataChange} />);

    const selectButton = screen.getByLabelText('Select PostgreSQL');
    await userEvent.click(selectButton);

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedOptionId: 'opt-1',
      })
    );
  });

  it('shows check icon on selected option', () => {
    const data = {
      selectedOptionId: 'opt-1',
      options: [{ id: 'opt-1', label: 'PostgreSQL', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const card = screen.getByTestId('option-card-opt-1');
    expect(card).toHaveAttribute('aria-selected', 'true');
  });

  it('does not show Select button on selected option', () => {
    const data = {
      status: 'open',
      selectedOptionId: 'opt-1',
      options: [{ id: 'opt-1', label: 'PostgreSQL', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Select PostgreSQL')).not.toBeInTheDocument();
  });

  it('renders option description when provided', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          description: 'This is a detailed description',
          pros: [],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('This is a detailed description')).toBeInTheDocument();
  });
});

// ── Pros/cons rendering ─────────────────────────────────────────────────
describe('DecisionRenderer pros/cons', () => {
  it('renders pros list when present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'PostgreSQL',
          pros: ['Strong ACID compliance', 'Rich query language'],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Strong ACID compliance')).toBeInTheDocument();
    expect(screen.getByText('Rich query language')).toBeInTheDocument();
  });

  it('renders cons list when present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'MongoDB',
          pros: [],
          cons: ['Eventual consistency', 'Limited transaction support'],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Eventual consistency')).toBeInTheDocument();
    expect(screen.getByText('Limited transaction support')).toBeInTheDocument();
  });

  it('pros list has proper aria-label', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          pros: ['Pro 1'],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Pros')).toBeInTheDocument();
  });

  it('cons list has proper aria-label', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          pros: [],
          cons: ['Con 1'],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Cons')).toBeInTheDocument();
  });

  it('does not render pros list when empty', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          pros: [],
          cons: ['Con 1'],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Pros')).not.toBeInTheDocument();
  });

  it('does not render cons list when empty', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          pros: ['Pro 1'],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Cons')).not.toBeInTheDocument();
  });
});

// ── Effort/risk badges ──────────────────────────────────────────────────
describe('DecisionRenderer effort/risk badges', () => {
  it('renders effort badge when present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          effort: 'Medium',
          pros: [],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Effort: Medium')).toBeInTheDocument();
  });

  it('renders risk badge when present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          risk: 'High',
          pros: [],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Risk: High')).toBeInTheDocument();
  });

  it('renders both effort and risk badges when both present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          effort: 'Low',
          risk: 'Medium',
          pros: [],
          cons: [],
        },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Effort: Low')).toBeInTheDocument();
    expect(screen.getByText('Risk: Medium')).toBeInTheDocument();
  });

  it('does not render badge container when neither effort nor risk present', () => {
    const data = {
      options: [
        {
          id: 'opt-1',
          label: 'Option A',
          pros: [],
          cons: [],
        },
      ],
    };
    const { container } = render(<DecisionRenderer {...defaultProps} data={data} />);
    const badgeTexts = container.textContent || '';
    expect(badgeTexts).not.toMatch(/Effort:/);
    expect(badgeTexts).not.toMatch(/Risk:/);
  });
});

// ── Read-only mode ──────────────────────────────────────────────────────
describe('DecisionRenderer read-only mode', () => {
  it('does not show Select buttons when readOnly', () => {
    const data = {
      status: 'open',
      options: [
        { id: 'opt-1', label: 'Option A', pros: [], cons: [] },
        { id: 'opt-2', label: 'Option B', pros: [], cons: [] },
      ],
    };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Select Option A')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Select Option B')).not.toBeInTheDocument();
  });

  it('does not show Decide button when readOnly', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Mark as decided')).not.toBeInTheDocument();
  });

  it('does not show Supersede button when readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Mark as superseded')).not.toBeInTheDocument();
  });

  it('does not show Create Issue button when readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Create issue from decision')).not.toBeInTheDocument();
  });
});

// ── Create Issue button ─────────────────────────────────────────────────
describe('DecisionRenderer Create Issue button', () => {
  it('shows Create Issue button when status is decided and not readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByLabelText('Create issue from decision')).toBeInTheDocument();
  });

  it('does not show Create Issue button when status is open', () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Create issue from decision')).not.toBeInTheDocument();
  });

  it('does not show Create Issue button when status is superseded', () => {
    const data = { status: 'superseded' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByLabelText('Create issue from decision')).not.toBeInTheDocument();
  });

  it('does not show Create Issue button when readOnly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} readOnly={true} />);
    expect(screen.queryByLabelText('Create issue from decision')).not.toBeInTheDocument();
  });

  it('renders button text correctly', () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Create Issue')).toBeInTheDocument();
  });
});

// ── Decision metadata ───────────────────────────────────────────────────
describe('DecisionRenderer decision metadata', () => {
  it('shows decision date when decisionDate is set', () => {
    const data = { decisionDate: '2026-03-15' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Decided on 2026-03-15')).toBeInTheDocument();
  });

  it('does not show decision date when not set', () => {
    const data = {};
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByText(/Decided on/)).not.toBeInTheDocument();
  });

  it('shows rationale text when present', () => {
    const data = {
      rationale: 'We chose PostgreSQL because it offers strong ACID guarantees',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(
      screen.getByText('We chose PostgreSQL because it offers strong ACID guarantees')
    ).toBeInTheDocument();
  });

  it('does not show rationale when not present', () => {
    const data = {};
    const { container } = render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(container.textContent).not.toMatch(/rationale/i);
  });
});

// ── Superseded indicator ────────────────────────────────────────────────
describe('DecisionRenderer superseded indicator', () => {
  it('shows supersededBy text when status is superseded and supersededBy is set', () => {
    const data = {
      status: 'superseded',
      supersededBy: 'Decision-2024-002',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Superseded by: Decision-2024-002')).toBeInTheDocument();
  });

  it('does not show superseded indicator when status is not superseded', () => {
    const data = {
      status: 'decided',
      supersededBy: 'Decision-2024-002',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByText(/Superseded by:/i)).not.toBeInTheDocument();
  });

  it('does not show superseded indicator when supersededBy is not set', () => {
    const data = {
      status: 'superseded',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.queryByText(/Superseded by:/i)).not.toBeInTheDocument();
  });

  it('shows superseded indicator only when both conditions met', () => {
    const data = {
      status: 'superseded',
      supersededBy: 'New Decision',
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    expect(screen.getByText('Superseded by: New Decision')).toBeInTheDocument();
  });
});

// ── Keyboard navigation ─────────────────────────────────────────────────
describe('DecisionRenderer keyboard navigation', () => {
  it('Select button is keyboard accessible', async () => {
    const data = {
      status: 'open',
      options: [{ id: 'opt-1', label: 'Option A', pros: [], cons: [] }],
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const selectButton = screen.getByLabelText('Select Option A');
    selectButton.focus();
    expect(selectButton).toHaveFocus();
  });

  it('Decide button is keyboard accessible', async () => {
    const data = { status: 'open' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const decideButton = screen.getByLabelText('Mark as decided');
    decideButton.focus();
    expect(decideButton).toHaveFocus();
  });

  it('Supersede button is keyboard accessible', async () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const supersedeButton = screen.getByLabelText('Mark as superseded');
    supersedeButton.focus();
    expect(supersedeButton).toHaveFocus();
  });

  it('Create Issue button is keyboard accessible', async () => {
    const data = { status: 'decided' };
    render(<DecisionRenderer {...defaultProps} data={data} />);
    const createButton = screen.getByLabelText('Create issue from decision');
    createButton.focus();
    expect(createButton).toHaveFocus();
  });
});

// ── Integration scenarios ───────────────────────────────────────────────
describe('DecisionRenderer integration scenarios', () => {
  it('renders complete decision with all metadata', () => {
    const data = {
      title: 'Select Database Technology',
      description: 'Choose primary database for user service',
      status: 'decided',
      selectedOptionId: 'opt-1',
      decisionDate: '2026-02-01',
      rationale: 'PostgreSQL provides best balance of features and team expertise',
      options: [
        {
          id: 'opt-1',
          label: 'PostgreSQL',
          description: 'Relational database with strong ACID support',
          pros: ['Strong consistency', 'Rich query language', 'Team expertise'],
          cons: ['Vertical scaling limits'],
          effort: 'Medium',
          risk: 'Low',
        },
        {
          id: 'opt-2',
          label: 'MongoDB',
          description: 'Document-oriented NoSQL database',
          pros: ['Flexible schema', 'Horizontal scaling'],
          cons: ['Eventual consistency', 'Limited transaction support'],
          effort: 'High',
          risk: 'Medium',
        },
      ],
    };

    render(<DecisionRenderer {...defaultProps} data={data} />);

    // Title and description
    expect(screen.getByText('Select Database Technology')).toBeInTheDocument();
    expect(screen.getByText('Choose primary database for user service')).toBeInTheDocument();

    // Status
    expect(screen.getByText('Decided')).toBeInTheDocument();

    // Both options
    expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
    expect(screen.getByText('MongoDB')).toBeInTheDocument();

    // Pros and cons
    expect(screen.getByText('Strong consistency')).toBeInTheDocument();
    expect(screen.getByText('Vertical scaling limits')).toBeInTheDocument();
    expect(screen.getByText('Flexible schema')).toBeInTheDocument();

    // Effort/risk
    expect(screen.getByText('Effort: Medium')).toBeInTheDocument();
    expect(screen.getByText('Risk: Low')).toBeInTheDocument();

    // Decision metadata
    expect(screen.getByText('Decided on 2026-02-01')).toBeInTheDocument();
    expect(
      screen.getByText('PostgreSQL provides best balance of features and team expertise')
    ).toBeInTheDocument();

    // Create Issue button
    expect(screen.getByLabelText('Create issue from decision')).toBeInTheDocument();
  });

  it('handles state transition from open to decided to superseded', async () => {
    const onDataChange = vi.fn();
    const { rerender } = render(
      <DecisionRenderer {...defaultProps} data={{ status: 'open' }} onDataChange={onDataChange} />
    );

    // Initial open state
    expect(screen.getByText('Open')).toBeInTheDocument();
    expect(screen.getByLabelText('Mark as decided')).toBeInTheDocument();

    // Transition to decided
    await userEvent.click(screen.getByLabelText('Mark as decided'));
    expect(onDataChange).toHaveBeenCalledWith(expect.objectContaining({ status: 'decided' }));

    // Re-render with decided status
    rerender(
      <DecisionRenderer
        {...defaultProps}
        data={{ status: 'decided' }}
        onDataChange={onDataChange}
      />
    );

    expect(screen.getByText('Decided')).toBeInTheDocument();
    expect(screen.getByLabelText('Mark as superseded')).toBeInTheDocument();

    // Transition to superseded
    await userEvent.click(screen.getByLabelText('Mark as superseded'));
    expect(onDataChange).toHaveBeenCalledWith(expect.objectContaining({ status: 'superseded' }));
  });

  it('merges custom data with defaults correctly', () => {
    const data = {
      title: 'Custom Title',
      // status and options should come from defaults
    };
    render(<DecisionRenderer {...defaultProps} data={data} />);

    // Custom title
    expect(screen.getByText('Custom Title')).toBeInTheDocument();

    // Default status (open)
    expect(screen.getByText('Open')).toBeInTheDocument();

    // Default options
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option B')).toBeInTheDocument();
  });
});
