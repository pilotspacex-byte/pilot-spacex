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

  it('renders fallback text when all stat counts are zero', () => {
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
    expect(screen.getByText('No related items found yet')).toBeInTheDocument();

    expect(screen.queryByText('Issues')).not.toBeInTheDocument();
    expect(screen.queryByText('Docs')).not.toBeInTheDocument();
    expect(screen.queryByText('Files')).not.toBeInTheDocument();
    expect(screen.queryByText('Tasks')).not.toBeInTheDocument();
  });

  it('only renders non-zero stat pills', () => {
    const partialSummary: ContextSummary = {
      issueIdentifier: 'PS-500',
      title: 'Partial context',
      summaryText: 'Some related items.',
      stats: {
        relatedCount: 0,
        docsCount: 2,
        filesCount: 0,
        tasksCount: 5,
      },
    };

    render(<ContextSummaryCard summary={partialSummary} />);

    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Tasks')).toBeInTheDocument();

    expect(screen.queryByText('Issues')).not.toBeInTheDocument();
    expect(screen.queryByText('Files')).not.toBeInTheDocument();
  });
});
