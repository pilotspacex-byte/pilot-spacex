/**
 * RiskRenderer component tests (US-006).
 *
 * RiskRenderer displays a risk register table with:
 * - Risk rows sorted by score (probability × impact, descending)
 * - Score color coding: ≤6 green, ≤12 yellow, >12 red
 * - Strategy badges (avoid/mitigate/transfer/accept)
 * - Owner column (shown only when not readOnly)
 * - Mitigation plan text (when present)
 * - Summary footer with severity counts
 *
 * Spec refs: FR-032 (risk identification with P×I scoring),
 * FR-033 (color-coded severity + mitigation strategies)
 *
 * @module pm-blocks/__tests__/RiskRenderer.test
 */
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';

import { RiskRenderer } from '../renderers/RiskRenderer';
import type { PMRendererProps } from '../PMBlockNodeView';

const defaultProps: PMRendererProps = {
  data: {
    title: 'Risk Register',
    risks: [
      {
        id: 'r1',
        description: 'Database migration failure',
        probability: 3,
        impact: 4,
        mitigation: 'mitigate' as const,
        mitigationPlan: 'Test on staging first',
        owner: 'John Doe',
      },
      {
        id: 'r2',
        description: 'API rate limit exceeded',
        probability: 2,
        impact: 2,
        mitigation: 'accept' as const,
      },
      {
        id: 'r3',
        description: 'Third-party service outage',
        probability: 4,
        impact: 5,
        mitigation: 'transfer' as const,
        owner: 'Jane Smith',
      },
    ],
  },
  readOnly: false,
  onDataChange: () => {},
  blockType: 'risk' as const,
};

// ── Basic rendering ──────────────────────────────────────────────────────
describe('RiskRenderer basic rendering', () => {
  it('renders with data-testid="risk-renderer"', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByTestId('risk-renderer')).toBeInTheDocument();
  });

  it('renders the title', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Risk Register')).toBeInTheDocument();
  });

  it('renders all risk rows', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Database migration failure')).toBeInTheDocument();
    expect(screen.getByText('API rate limit exceeded')).toBeInTheDocument();
    expect(screen.getByText('Third-party service outage')).toBeInTheDocument();
  });

  it('renders a table structure', () => {
    render(<RiskRenderer {...defaultProps} />);
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  });

  it('renders table headers', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.getByText('P')).toBeInTheDocument();
    expect(screen.getByText('I')).toBeInTheDocument();
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('Strategy')).toBeInTheDocument();
  });
});

// ── FR-032: Score calculation ────────────────────────────────────────────
describe('RiskRenderer score calculation (FR-032)', () => {
  it('displays probability values', () => {
    const { container } = render(<RiskRenderer {...defaultProps} />);
    const rows = container.querySelectorAll('tbody tr');

    // Check each row has probability displayed (rows sorted by score: r3, r1, r2)
    const r3Cells = within(rows[0] as HTMLElement).getAllByRole('cell');
    expect(r3Cells[1]).toHaveTextContent('4'); // r3: probability 4

    const r1Cells = within(rows[1] as HTMLElement).getAllByRole('cell');
    expect(r1Cells[1]).toHaveTextContent('3'); // r1: probability 3

    const r2Cells = within(rows[2] as HTMLElement).getAllByRole('cell');
    expect(r2Cells[1]).toHaveTextContent('2'); // r2: probability 2
  });

  it('displays impact values', () => {
    const { container } = render(<RiskRenderer {...defaultProps} />);
    const rows = container.querySelectorAll('tbody tr');

    // Check each row has impact displayed (rows sorted by score: r3, r1, r2)
    const r3Cells = within(rows[0] as HTMLElement).getAllByRole('cell');
    expect(r3Cells[2]).toHaveTextContent('5'); // r3: impact 5

    const r1Cells = within(rows[1] as HTMLElement).getAllByRole('cell');
    expect(r1Cells[2]).toHaveTextContent('4'); // r1: impact 4

    const r2Cells = within(rows[2] as HTMLElement).getAllByRole('cell');
    expect(r2Cells[2]).toHaveTextContent('2'); // r2: impact 2
  });

  it('calculates and displays score as probability × impact', () => {
    const { container } = render(<RiskRenderer {...defaultProps} />);
    const rows = container.querySelectorAll('tbody tr');

    // Check scores in each row (rows sorted by score: r3=20, r1=12, r2=4)
    const r3Cells = within(rows[0] as HTMLElement).getAllByRole('cell');
    expect(r3Cells[3]).toHaveTextContent('20'); // r3: 4 × 5 = 20

    const r1Cells = within(rows[1] as HTMLElement).getAllByRole('cell');
    expect(r1Cells[3]).toHaveTextContent('12'); // r1: 3 × 4 = 12

    const r2Cells = within(rows[2] as HTMLElement).getAllByRole('cell');
    expect(r2Cells[3]).toHaveTextContent('4'); // r2: 2 × 2 = 4
  });
});

// ── Score sorting (highest first) ────────────────────────────────────────
describe('RiskRenderer score sorting', () => {
  it('sorts risks by score in descending order', () => {
    const { container } = render(<RiskRenderer {...defaultProps} />);
    const rows = container.querySelectorAll('tbody tr');

    // r3 has score 20 (highest) → should be first
    expect(
      within(rows[0] as HTMLElement).getByText('Third-party service outage')
    ).toBeInTheDocument();

    // r1 has score 12 → should be second
    expect(
      within(rows[1] as HTMLElement).getByText('Database migration failure')
    ).toBeInTheDocument();

    // r2 has score 4 (lowest) → should be third
    expect(within(rows[2] as HTMLElement).getByText('API rate limit exceeded')).toBeInTheDocument();
  });

  it('maintains correct sorting with equal scores', () => {
    const { container } = render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Risk A',
              probability: 2,
              impact: 3,
              mitigation: 'mitigate' as const,
            },
            {
              id: 'r2',
              description: 'Risk B',
              probability: 3,
              impact: 2,
              mitigation: 'accept' as const,
            },
            {
              id: 'r3',
              description: 'Risk C',
              probability: 1,
              impact: 6,
              mitigation: 'avoid' as const,
            },
          ],
        }}
      />
    );

    const rows = container.querySelectorAll('tbody tr');

    // All have score 6, but Risk A and B should appear before C (original order preserved)
    expect(within(rows[0] as HTMLElement).getByText('Risk A')).toBeInTheDocument();
    expect(within(rows[1] as HTMLElement).getByText('Risk B')).toBeInTheDocument();
    expect(within(rows[2] as HTMLElement).getByText('Risk C')).toBeInTheDocument();
  });
});

// ── FR-033: Score color coding ───────────────────────────────────────────
describe('RiskRenderer score color coding (FR-033)', () => {
  it('applies green color to scores ≤6 (low severity)', () => {
    render(<RiskRenderer {...defaultProps} />);

    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Low risk',
              probability: 2,
              impact: 3,
              mitigation: 'accept' as const,
            },
          ],
        }}
      />
    );

    const scoreCell = screen.getByText('6').closest('td');
    expect(scoreCell).toHaveClass('bg-green-500/15');
    expect(scoreCell).toHaveClass('text-green-700');
  });

  it('applies yellow color to scores >6 and ≤12 (medium severity)', () => {
    render(<RiskRenderer {...defaultProps} />);

    const scoreCell = screen.getByText('12').closest('td');
    expect(scoreCell).toHaveClass('bg-amber-500/15');
    expect(scoreCell).toHaveClass('text-amber-700');
  });

  it('applies red color to scores >12 (high severity)', () => {
    render(<RiskRenderer {...defaultProps} />);

    const scoreCell = screen.getByText('20').closest('td');
    expect(scoreCell).toHaveClass('bg-red-500/15');
    expect(scoreCell).toHaveClass('text-red-700');
  });

  it('applies correct color to boundary score of 6', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Boundary test',
              probability: 2,
              impact: 3,
              mitigation: 'accept' as const,
            },
          ],
        }}
      />
    );

    const scoreCell = screen.getByText('6').closest('td');
    expect(scoreCell).toHaveClass('bg-green-500/15'); // ≤6 is green
  });

  it('applies correct color to boundary score of 12', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Boundary test',
              probability: 3,
              impact: 4,
              mitigation: 'mitigate' as const,
            },
          ],
        }}
      />
    );

    const scoreCell = screen.getByText('12').closest('td');
    expect(scoreCell).toHaveClass('bg-amber-500/15'); // ≤12 is yellow
  });

  it('applies correct color to score just above 12', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Boundary test',
              probability: 3,
              impact: 5,
              mitigation: 'transfer' as const,
            },
          ],
        }}
      />
    );

    const scoreCell = screen.getByText('15').closest('td');
    expect(scoreCell).toHaveClass('bg-red-500/15'); // >12 is red
  });
});

// ── Strategy labels ──────────────────────────────────────────────────────
describe('RiskRenderer strategy labels', () => {
  it('displays "Avoid" for avoid strategy', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Test risk',
              probability: 2,
              impact: 2,
              mitigation: 'avoid' as const,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Avoid')).toBeInTheDocument();
  });

  it('displays "Mitigate" for mitigate strategy', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Mitigate')).toBeInTheDocument();
  });

  it('displays "Transfer" for transfer strategy', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Transfer')).toBeInTheDocument();
  });

  it('displays "Accept" for accept strategy', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Accept')).toBeInTheDocument();
  });

  it('renders strategy badges with correct styling', () => {
    render(<RiskRenderer {...defaultProps} />);

    const mitigateBadge = screen.getByText('Mitigate');
    expect(mitigateBadge).toHaveClass('inline-flex');
    expect(mitigateBadge).toHaveClass('items-center');
    expect(mitigateBadge).toHaveClass('rounded-full');
  });
});

// ── Summary footer ───────────────────────────────────────────────────────
describe('RiskRenderer summary footer', () => {
  it('displays total risk count', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Total: 3 risks')).toBeInTheDocument();
  });

  it('displays high severity count (score >12)', () => {
    render(<RiskRenderer {...defaultProps} />);
    // r3 has score 20 (only high risk)
    expect(screen.getByText('High: 1')).toBeInTheDocument();
  });

  it('displays medium severity count (score 6-12)', () => {
    render(<RiskRenderer {...defaultProps} />);
    // r1 has score 12 (only medium risk)
    expect(screen.getByText('Medium: 1')).toBeInTheDocument();
  });

  it('displays low severity count (score ≤6)', () => {
    render(<RiskRenderer {...defaultProps} />);
    // r2 has score 4 (only low risk)
    expect(screen.getByText('Low: 1')).toBeInTheDocument();
  });

  it('calculates correct counts with multiple risks per severity', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'High 1',
              probability: 5,
              impact: 5,
              mitigation: 'transfer' as const,
            }, // 25 (high)
            {
              id: 'r2',
              description: 'High 2',
              probability: 4,
              impact: 4,
              mitigation: 'avoid' as const,
            }, // 16 (high)
            {
              id: 'r3',
              description: 'Medium 1',
              probability: 3,
              impact: 3,
              mitigation: 'mitigate' as const,
            }, // 9 (medium)
            {
              id: 'r4',
              description: 'Medium 2',
              probability: 2,
              impact: 4,
              mitigation: 'mitigate' as const,
            }, // 8 (medium)
            {
              id: 'r5',
              description: 'Low 1',
              probability: 2,
              impact: 2,
              mitigation: 'accept' as const,
            }, // 4 (low)
            {
              id: 'r6',
              description: 'Low 2',
              probability: 1,
              impact: 3,
              mitigation: 'accept' as const,
            }, // 3 (low)
          ],
        }}
      />
    );

    expect(screen.getByText('Total: 6 risks')).toBeInTheDocument();
    expect(screen.getByText('High: 2')).toBeInTheDocument();
    expect(screen.getByText('Medium: 2')).toBeInTheDocument();
    expect(screen.getByText('Low: 2')).toBeInTheDocument();
  });

  it('handles zero counts correctly', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Only high risk',
              probability: 5,
              impact: 5,
              mitigation: 'transfer' as const,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Total: 1 risks')).toBeInTheDocument();
    expect(screen.getByText('High: 1')).toBeInTheDocument();
    expect(screen.getByText('Medium: 0')).toBeInTheDocument();
    expect(screen.getByText('Low: 0')).toBeInTheDocument();
  });
});

// ── Owner column visibility ──────────────────────────────────────────────
describe('RiskRenderer owner column', () => {
  it('shows owner column when not readOnly', () => {
    render(<RiskRenderer {...defaultProps} readOnly={false} />);
    expect(screen.getByText('Owner')).toBeInTheDocument();
  });

  it('hides owner column when readOnly', () => {
    render(<RiskRenderer {...defaultProps} readOnly={true} />);
    expect(screen.queryByText('Owner')).not.toBeInTheDocument();
  });

  it('displays owner names when present', () => {
    render(<RiskRenderer {...defaultProps} readOnly={false} />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('displays em-dash for missing owner', () => {
    render(<RiskRenderer {...defaultProps} readOnly={false} />);
    // r2 has no owner
    const { container } = render(<RiskRenderer {...defaultProps} readOnly={false} />);
    const rows = container.querySelectorAll('tbody tr');
    // r2 is third row (lowest score)
    expect(within(rows[2] as HTMLElement).getByText('—')).toBeInTheDocument();
  });
});

// ── Mitigation plan text ─────────────────────────────────────────────────
describe('RiskRenderer mitigation plan', () => {
  it('shows mitigation plan text when present', () => {
    render(<RiskRenderer {...defaultProps} />);
    expect(screen.getByText('Test on staging first')).toBeInTheDocument();
  });

  it('does not render mitigation plan element when not present', () => {
    render(<RiskRenderer {...defaultProps} />);

    // r2 and r3 have no mitigation plan
    const r2Description = screen.getByText('API rate limit exceeded');
    const r2Row = r2Description.closest('tr');

    // Check there's no italic text (mitigation plan style) in this row
    const italicElements = r2Row?.querySelectorAll('.italic');
    expect(italicElements?.length).toBe(0);
  });

  it('renders mitigation plan with italic styling', () => {
    render(<RiskRenderer {...defaultProps} />);
    const mitigationPlan = screen.getByText('Test on staging first');
    expect(mitigationPlan).toHaveClass('italic');
    expect(mitigationPlan).toHaveClass('text-muted-foreground');
  });

  it('renders mitigation plan below risk description', () => {
    render(<RiskRenderer {...defaultProps} />);

    // r1 has mitigation plan
    const r1Description = screen.getByText('Database migration failure');
    const r1Cell = r1Description.closest('td');
    const mitigationPlan = within(r1Cell as HTMLElement).getByText('Test on staging first');

    expect(mitigationPlan).toBeInTheDocument();
    expect(mitigationPlan.tagName).toBe('P');
  });
});

// ── Edge cases ───────────────────────────────────────────────────────────
describe('RiskRenderer edge cases', () => {
  it('renders empty table when no risks', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [],
        }}
      />
    );

    expect(screen.getByText('Risk Register')).toBeInTheDocument();
    expect(screen.getByText('Total: 0 risks')).toBeInTheDocument();
    expect(screen.getByText('High: 0')).toBeInTheDocument();
    expect(screen.getByText('Medium: 0')).toBeInTheDocument();
    expect(screen.getByText('Low: 0')).toBeInTheDocument();
  });

  it('handles minimal risk data', () => {
    const { container } = render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Minimal risk',
              probability: 1,
              impact: 1,
              mitigation: 'accept' as const,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Minimal risk')).toBeInTheDocument();

    // Check score cell specifically (4th cell in the row)
    const rows = container.querySelectorAll('tbody tr');
    const cells = within(rows[0] as HTMLElement).getAllByRole('cell');
    expect(cells[3]).toHaveTextContent('1'); // score 1×1=1
  });

  it('handles maximum risk data', () => {
    render(
      <RiskRenderer
        {...defaultProps}
        data={{
          title: 'Risk Register',
          risks: [
            {
              id: 'r1',
              description: 'Maximum risk',
              probability: 5,
              impact: 5,
              mitigation: 'avoid' as const,
            },
          ],
        }}
      />
    );

    expect(screen.getByText('Maximum risk')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument(); // score 5×5=25
  });

  it('uses default data when data prop is incomplete', () => {
    render(<RiskRenderer {...defaultProps} data={{}} />);

    // DEFAULT_DATA has title 'Risk Register' and one example risk
    expect(screen.getByText('Risk Register')).toBeInTheDocument();
    expect(screen.getByText('Example risk')).toBeInTheDocument();
  });
});
