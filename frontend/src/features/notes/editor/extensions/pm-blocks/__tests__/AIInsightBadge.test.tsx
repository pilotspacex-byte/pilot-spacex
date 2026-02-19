/**
 * Tests for AIInsightBadge component.
 *
 * AIInsightBadge displays a traffic-light badge on PM blocks with:
 * - Green/yellow/red severity variants (FR-056)
 * - Tooltip with analysis, references, suggested actions (FR-057)
 * - Insufficient data fallback when <3 sprints (FR-058)
 * - Dismissable insights (FR-059)
 *
 * @module pm-blocks/__tests__/AIInsightBadge.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AIInsightBadge } from '../shared/AIInsightBadge';
import type { PMBlockInsight } from '@/services/api/pm-blocks';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeInsight(overrides: Partial<PMBlockInsight> = {}): PMBlockInsight {
  return {
    id: 'insight-1',
    workspaceId: 'ws-1',
    blockId: 'block-1',
    blockType: 'sprint_board',
    insightType: 'velocity_drop',
    severity: 'yellow',
    title: 'Velocity drop detected',
    analysis: 'Sprint velocity decreased 20% vs last sprint.',
    references: ['PS-101', 'PS-102'],
    suggestedActions: ['Review blockers', 'Consider scope reduction'],
    confidence: 0.82,
    dismissed: false,
    ...overrides,
  };
}

const defaultProps = {
  insight: null,
  onDismiss: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Insufficient data (no insight) ────────────────────────────────────────────

describe('AIInsightBadge insufficient data', () => {
  it('renders gray badge when insufficientData=true', () => {
    render(<AIInsightBadge insight={null} insufficientData />);
    const btn = screen.getByRole('status');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent('Insufficient Data');
  });

  it('renders gray badge when insight is null and insufficientData not set', () => {
    render(<AIInsightBadge insight={null} />);
    expect(screen.getByRole('status')).toHaveTextContent('Insufficient Data');
  });

  it('shows tooltip with insufficient data message on click', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={null} insufficientData />);
    await user.click(screen.getByRole('status'));
    expect(
      screen.getByText('AI insights require at least 3 completed sprints.')
    ).toBeInTheDocument();
  });

  it('closes insufficient data tooltip on second click', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={null} insufficientData />);
    const btn = screen.getByRole('status');
    await user.click(btn);
    expect(
      screen.getByText('AI insights require at least 3 completed sprints.')
    ).toBeInTheDocument();
    await user.click(btn);
    expect(
      screen.queryByText('AI insights require at least 3 completed sprints.')
    ).not.toBeInTheDocument();
  });
});

// ── Severity variants ─────────────────────────────────────────────────────────

describe('AIInsightBadge severity variants', () => {
  it('renders green badge for green severity', () => {
    const insight = makeInsight({ severity: 'green', title: 'On Track' });
    render(<AIInsightBadge insight={insight} />);
    const btn = screen.getByRole('status');
    expect(btn).toHaveClass('text-[#29A386]');
  });

  it('renders yellow badge for yellow severity', () => {
    const insight = makeInsight({ severity: 'yellow', title: 'At Risk' });
    render(<AIInsightBadge insight={insight} />);
    const btn = screen.getByRole('status');
    expect(btn).toHaveClass('text-[#D9853F]');
  });

  it('renders red badge for red severity', () => {
    const insight = makeInsight({ severity: 'red', title: 'Blocked' });
    render(<AIInsightBadge insight={insight} />);
    const btn = screen.getByRole('status');
    expect(btn).toHaveClass('text-[#D9534F]');
  });

  it('uses insight title as badge label', () => {
    const insight = makeInsight({ title: 'Custom Title' });
    render(<AIInsightBadge insight={insight} />);
    expect(screen.getByRole('status')).toHaveTextContent('Custom Title');
  });

  it('aria-label includes severity and title', () => {
    const insight = makeInsight({ severity: 'red', title: 'Blocked' });
    render(<AIInsightBadge insight={insight} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'AI insight: red - Blocked');
  });
});

// ── Tooltip content ───────────────────────────────────────────────────────────

describe('AIInsightBadge tooltip', () => {
  it('shows tooltip on click with title and analysis', async () => {
    const user = userEvent.setup();
    const insight = makeInsight();
    render(<AIInsightBadge insight={insight} />);
    await user.click(screen.getByRole('status'));
    // Title appears in both badge and tooltip; verify tooltip is visible (role="tooltip")
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    expect(screen.getByText('Sprint velocity decreased 20% vs last sprint.')).toBeInTheDocument();
  });

  it('shows references in tooltip', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} />);
    await user.click(screen.getByRole('status'));
    expect(screen.getByText('PS-101, PS-102')).toBeInTheDocument();
  });

  it('shows suggested actions in tooltip', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} />);
    await user.click(screen.getByRole('status'));
    expect(screen.getByText(/Review blockers/)).toBeInTheDocument();
    expect(screen.getByText(/Consider scope reduction/)).toBeInTheDocument();
  });

  it('hides tooltip on close button click', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} />);
    await user.click(screen.getByRole('status'));
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Close insight tooltip'));
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('does not show insight tooltip for insufficient data badge', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={null} insufficientData />);
    await user.click(screen.getByRole('status'));
    // Should show insufficient data message, not InsightTooltip
    expect(screen.queryByLabelText('Close insight tooltip')).not.toBeInTheDocument();
  });

  it('hides tooltip on Escape key', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} />);
    const btn = screen.getByRole('status');
    await user.click(btn);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});

// ── Dismiss (FR-059) ──────────────────────────────────────────────────────────

describe('AIInsightBadge dismiss', () => {
  it('shows Dismiss button in tooltip when onDismiss provided', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} onDismiss={vi.fn()} />);
    await user.click(screen.getByRole('status'));
    expect(screen.getByLabelText('Dismiss AI insight')).toBeInTheDocument();
  });

  it('calls onDismiss with insight id on dismiss click', async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<AIInsightBadge insight={makeInsight({ id: 'insight-42' })} onDismiss={onDismiss} />);
    await user.click(screen.getByRole('status'));
    await user.click(screen.getByLabelText('Dismiss AI insight'));
    expect(onDismiss).toHaveBeenCalledWith('insight-42');
  });

  it('closes tooltip after dismiss', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} onDismiss={vi.fn()} />);
    await user.click(screen.getByRole('status'));
    await user.click(screen.getByLabelText('Dismiss AI insight'));
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('does not show Dismiss button when onDismiss not provided', async () => {
    const user = userEvent.setup();
    render(<AIInsightBadge insight={makeInsight()} />);
    await user.click(screen.getByRole('status'));
    expect(screen.queryByLabelText('Dismiss AI insight')).not.toBeInTheDocument();
  });
});

// ── className prop ────────────────────────────────────────────────────────────

describe('AIInsightBadge className', () => {
  it('applies additional className to wrapper', () => {
    const { container } = render(<AIInsightBadge {...defaultProps} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
