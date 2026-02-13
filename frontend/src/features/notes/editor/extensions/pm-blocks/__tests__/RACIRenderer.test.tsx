/**
 * RACIRenderer component tests (US-005).
 *
 * RACIRenderer displays a RACI matrix table where:
 * - Rows = deliverables
 * - Columns = stakeholders
 * - Cells = RACI roles (R/A/C/I or empty)
 * - Clicking a cell cycles through: '' → 'R' → 'A' → 'C' → 'I' → ''
 * - Validates exactly one 'A' (Accountable) per deliverable
 * - Keyboard accessible (Enter/Space trigger cell cycling)
 *
 * Spec refs: FR-030 (RACI assignment matrix), FR-031 (constraint validation)
 *
 * @module pm-blocks/__tests__/RACIRenderer.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { RACIRenderer } from '../renderers/RACIRenderer';
import type { PMRendererProps } from '../PMBlockNodeView';

const defaultProps: PMRendererProps = {
  data: {
    title: 'RACI Matrix',
    deliverables: ['Deliverable 1', 'Deliverable 2'],
    stakeholders: ['Person A', 'Person B', 'Person C'],
    assignments: {},
  },
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'raci' as const,
};

// ── Basic rendering ──────────────────────────────────────────────────────
describe('RACIRenderer basic rendering', () => {
  it('renders with data-testid="raci-renderer"', () => {
    render(<RACIRenderer {...defaultProps} />);
    expect(screen.getByTestId('raci-renderer')).toBeInTheDocument();
  });

  it('renders the title', () => {
    render(<RACIRenderer {...defaultProps} />);
    expect(screen.getByText('RACI Matrix')).toBeInTheDocument();
  });

  it('renders all deliverable rows', () => {
    render(<RACIRenderer {...defaultProps} />);
    expect(screen.getByText('Deliverable 1')).toBeInTheDocument();
    expect(screen.getByText('Deliverable 2')).toBeInTheDocument();
  });

  it('renders all stakeholder columns', () => {
    render(<RACIRenderer {...defaultProps} />);
    expect(screen.getByText('Person A')).toBeInTheDocument();
    expect(screen.getByText('Person B')).toBeInTheDocument();
    expect(screen.getByText('Person C')).toBeInTheDocument();
  });

  it('renders a table structure', () => {
    render(<RACIRenderer {...defaultProps} />);
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  });
});

// ── Cell cycling ─────────────────────────────────────────────────────────
describe('RACIRenderer cell cycling', () => {
  it('renders empty cells initially when no assignments', () => {
    render(<RACIRenderer {...defaultProps} />);
    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    expect(cell).toHaveTextContent('');
  });

  it('cycles from empty to R on first click', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    await userEvent.click(cell);

    expect(onDataChange).toHaveBeenCalledWith({
      title: 'RACI Matrix',
      deliverables: ['Deliverable 1', 'Deliverable 2'],
      stakeholders: ['Person A', 'Person B', 'Person C'],
      assignments: {
        'Deliverable 1': {
          'Person A': 'R',
        },
      },
    });
  });

  it('cycles through all roles: R → A → C → I → empty', async () => {
    const onDataChange = vi.fn();
    const { rerender } = render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const getCellByDeliverableStakeholder = (deliverable: string, stakeholder: string) =>
      screen.getByRole('button', { name: new RegExp(`${deliverable} - ${stakeholder}:`) });

    const cell = getCellByDeliverableStakeholder('Deliverable 1', 'Person A');

    // Click 1: '' → 'R'
    await userEvent.click(cell);
    expect(onDataChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': 'R' } },
      })
    );

    // Click 2: 'R' → 'A'
    rerender(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: { 'Deliverable 1': { 'Person A': 'R' } },
        }}
        onDataChange={onDataChange}
      />
    );
    const cellR = screen.getByLabelText('Deliverable 1 - Person A: R');
    await userEvent.click(cellR);
    expect(onDataChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': 'A' } },
      })
    );

    // Click 3: 'A' → 'C'
    rerender(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: { 'Deliverable 1': { 'Person A': 'A' } },
        }}
        onDataChange={onDataChange}
      />
    );
    const cellA = screen.getByLabelText('Deliverable 1 - Person A: A');
    await userEvent.click(cellA);
    expect(onDataChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': 'C' } },
      })
    );

    // Click 4: 'C' → 'I'
    rerender(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: { 'Deliverable 1': { 'Person A': 'C' } },
        }}
        onDataChange={onDataChange}
      />
    );
    const cellC = screen.getByLabelText('Deliverable 1 - Person A: C');
    await userEvent.click(cellC);
    expect(onDataChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': 'I' } },
      })
    );

    // Click 5: 'I' → ''
    rerender(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: { 'Deliverable 1': { 'Person A': 'I' } },
        }}
        onDataChange={onDataChange}
      />
    );
    const cellI = screen.getByLabelText('Deliverable 1 - Person A: I');
    await userEvent.click(cellI);
    expect(onDataChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': '' } },
      })
    );
  });

  it('displays role letters in cells when assigned', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': {
              'Person A': 'R',
              'Person B': 'A',
              'Person C': 'C',
            },
          },
        }}
      />
    );

    expect(screen.getByLabelText('Deliverable 1 - Person A: R')).toHaveTextContent('R');
    expect(screen.getByLabelText('Deliverable 1 - Person B: A')).toHaveTextContent('A');
    expect(screen.getByLabelText('Deliverable 1 - Person C: C')).toHaveTextContent('C');
  });
});

// ── onDataChange callback ────────────────────────────────────────────────
describe('RACIRenderer onDataChange', () => {
  it('calls onDataChange with full updated data object', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 2 - Person C: unassigned');
    await userEvent.click(cell);

    expect(onDataChange).toHaveBeenCalledTimes(1);
    expect(onDataChange).toHaveBeenCalledWith({
      title: 'RACI Matrix',
      deliverables: ['Deliverable 1', 'Deliverable 2'],
      stakeholders: ['Person A', 'Person B', 'Person C'],
      assignments: {
        'Deliverable 2': {
          'Person C': 'R',
        },
      },
    });
  });

  it('preserves existing assignments when updating a different cell', async () => {
    const onDataChange = vi.fn();
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'R' },
          },
        }}
        onDataChange={onDataChange}
      />
    );

    const cell = screen.getByLabelText('Deliverable 2 - Person B: unassigned');
    await userEvent.click(cell);

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        assignments: {
          'Deliverable 1': { 'Person A': 'R' },
          'Deliverable 2': { 'Person B': 'R' },
        },
      })
    );
  });
});

// ── FR-031: Validation (exactly one A per deliverable) ───────────────────
describe('RACIRenderer validation (FR-031)', () => {
  it('shows warning when no Accountable (A) is assigned', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          deliverables: ['Deliverable 1'], // Only one deliverable to avoid multiple warnings
          assignments: {
            'Deliverable 1': {
              'Person A': 'R',
              'Person B': 'C',
            },
          },
        }}
      />
    );

    expect(screen.getByText(/Missing Accountable \(A\)/)).toBeInTheDocument();
    expect(screen.getByText(/exactly one required/)).toBeInTheDocument();
  });

  it('shows warning when more than one Accountable (A) is assigned', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          deliverables: ['Deliverable 1'], // Only one deliverable to avoid multiple warnings
          assignments: {
            'Deliverable 1': {
              'Person A': 'A',
              'Person B': 'A',
            },
          },
        }}
      />
    );

    expect(screen.getByText(/2 Accountable \(A\) assigned/)).toBeInTheDocument();
    expect(screen.getByText(/exactly one required/)).toBeInTheDocument();
  });

  it('does not show warning when exactly one Accountable (A) is assigned', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': {
              'Person A': 'R',
              'Person B': 'A',
              'Person C': 'C',
            },
            'Deliverable 2': {
              'Person A': 'A', // Also assign A to second deliverable
            },
          },
        }}
      />
    );

    expect(screen.queryByText(/Missing Accountable/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Accountable \(A\) assigned/)).not.toBeInTheDocument();
  });

  it('renders AlertTriangle icon when validation fails', () => {
    const { container } = render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': {
              'Person A': 'R',
            },
          },
        }}
      />
    );

    // Check for SVG icon (lucide-react AlertTriangle renders as svg)
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('shows multiple warnings for multiple deliverables', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'R' },
            'Deliverable 2': { 'Person B': 'R' },
          },
        }}
      />
    );

    const warnings = screen.getAllByText(/Missing Accountable \(A\)/);
    expect(warnings).toHaveLength(2);
  });
});

// ── ReadOnly mode ────────────────────────────────────────────────────────
describe('RACIRenderer readOnly mode', () => {
  it('does not call onDataChange when cell is clicked in readOnly mode', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} readOnly={true} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    await userEvent.click(cell);

    expect(onDataChange).not.toHaveBeenCalled();
  });

  it('sets tabIndex to -1 on cells in readOnly mode', () => {
    render(<RACIRenderer {...defaultProps} readOnly={true} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    expect(cell).toHaveAttribute('tabIndex', '-1');
  });

  it('sets tabIndex to 0 on cells when not readOnly', () => {
    render(<RACIRenderer {...defaultProps} readOnly={false} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    expect(cell).toHaveAttribute('tabIndex', '0');
  });
});

// ── Keyboard accessibility ───────────────────────────────────────────────
describe('RACIRenderer keyboard accessibility', () => {
  it('triggers cell cycling on Enter key', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    cell.focus();
    await userEvent.keyboard('{Enter}');

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person A': 'R' } },
      })
    );
  });

  it('triggers cell cycling on Space key', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person B: unassigned');
    cell.focus();
    await userEvent.keyboard(' ');

    expect(onDataChange).toHaveBeenCalledWith(
      expect.objectContaining({
        assignments: { 'Deliverable 1': { 'Person B': 'R' } },
      })
    );
  });

  it('does not trigger on other keys', async () => {
    const onDataChange = vi.fn();
    render(<RACIRenderer {...defaultProps} onDataChange={onDataChange} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    cell.focus();
    await userEvent.keyboard('{Tab}');
    await userEvent.keyboard('{Escape}');
    await userEvent.keyboard('a');

    expect(onDataChange).not.toHaveBeenCalled();
  });

  it('has role="button" on cells', () => {
    render(<RACIRenderer {...defaultProps} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    expect(cell).toHaveAttribute('role', 'button');
  });

  it('has descriptive aria-label on cells', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'R' },
          },
        }}
      />
    );

    expect(screen.getByLabelText('Deliverable 1 - Person A: R')).toBeInTheDocument();
    expect(screen.getByLabelText('Deliverable 1 - Person B: unassigned')).toBeInTheDocument();
  });
});

// ── Role styling ─────────────────────────────────────────────────────────
describe('RACIRenderer role styling', () => {
  it('applies R role styling to cells with R', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'R' },
          },
        }}
      />
    );

    const cell = screen.getByLabelText('Deliverable 1 - Person A: R');
    expect(cell).toHaveClass('bg-blue-500/10');
    expect(cell).toHaveClass('text-blue-700');
  });

  it('applies A role styling to cells with A', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'A' },
          },
        }}
      />
    );

    const cell = screen.getByLabelText('Deliverable 1 - Person A: A');
    expect(cell).toHaveClass('bg-primary/10');
    expect(cell).toHaveClass('text-primary');
    expect(cell).toHaveClass('font-bold');
  });

  it('applies C role styling to cells with C', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'C' },
          },
        }}
      />
    );

    const cell = screen.getByLabelText('Deliverable 1 - Person A: C');
    expect(cell).toHaveClass('bg-amber-500/10');
    expect(cell).toHaveClass('text-amber-700');
  });

  it('applies I role styling to cells with I', () => {
    render(
      <RACIRenderer
        {...defaultProps}
        data={{
          ...defaultProps.data,
          assignments: {
            'Deliverable 1': { 'Person A': 'I' },
          },
        }}
      />
    );

    const cell = screen.getByLabelText('Deliverable 1 - Person A: I');
    expect(cell).toHaveClass('bg-muted/30');
    expect(cell).toHaveClass('text-muted-foreground');
  });

  it('has base cell styling on all cells', () => {
    render(<RACIRenderer {...defaultProps} />);

    const cell = screen.getByLabelText('Deliverable 1 - Person A: unassigned');
    expect(cell).toHaveClass('text-center');
    expect(cell).toHaveClass('p-2');
    expect(cell).toHaveClass('cursor-pointer');
  });
});
