/**
 * ContextSummaryCard component tests.
 *
 * Tests for AI context summary card displaying issue overview and stats.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ContextSummaryCard } from '../context-summary-card';
import type { ContextSummary } from '@/stores/ai/AIContextStore';

describe('ContextSummaryCard', () => {
  const mockSummary: ContextSummary = {
    issueIdentifier: 'PS-201',
    title: 'Implement AI context panel with streaming support',
    summaryText:
      'Build a comprehensive AI context panel that aggregates related issues, documentation, and implementation tasks with real-time streaming updates.',
    stats: {
      relatedCount: 5,
      docsCount: 3,
      filesCount: 12,
      tasksCount: 8,
    },
  };

  it('renders identifier, title, and summaryText', () => {
    render(<ContextSummaryCard summary={mockSummary} />);

    expect(screen.getByText('PS-201')).toBeInTheDocument();
    expect(
      screen.getByText('Implement AI context panel with streaming support')
    ).toBeInTheDocument();
    expect(screen.getByText(/Build a comprehensive AI context panel/)).toBeInTheDocument();
  });

  it('renders all 4 stat counts with labels', () => {
    render(<ContextSummaryCard summary={mockSummary} />);

    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Issues')).toBeInTheDocument();

    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();

    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Files')).toBeInTheDocument();

    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
  });

  it('renders with zero stat counts', () => {
    const emptySummary: ContextSummary = {
      issueIdentifier: 'PS-999',
      title: 'Simple issue with no context',
      summaryText: 'A minimal issue with no related items.',
      stats: {
        relatedCount: 0,
        docsCount: 0,
        filesCount: 0,
        tasksCount: 0,
      },
    };

    render(<ContextSummaryCard summary={emptySummary} />);

    expect(screen.getByText('PS-999')).toBeInTheDocument();
    expect(screen.getByText('Simple issue with no context')).toBeInTheDocument();

    const zeroCounts = screen.getAllByText('0');
    expect(zeroCounts).toHaveLength(4);

    expect(screen.getByText('Issues')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
    expect(screen.getByText('Files')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();
  });
});
