/**
 * Unit tests for StructuredResultCard — ExtractionResultCard flow.
 *
 * Tests selection UI, "Create Selected Issues" action, and loading state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StructuredResultCard } from '../StructuredResultCard';

const mockIssues = [
  {
    title: 'Fix login timeout',
    description: 'Login form times out after 10 seconds',
    issue_type: 'bug',
    priority: 'high',
    category: 'explicit',
    source_block_id: 'block-1',
  },
  {
    title: 'Add dark mode',
    description: 'Support dark mode theme',
    issue_type: 'feature',
    priority: 'low',
    category: 'implicit',
    source_block_id: null,
  },
  {
    title: 'Refactor auth module',
    description: 'Clean up authentication code',
    issue_type: 'task',
    priority: 'urgent',
    category: 'related',
    source_block_id: 'block-2',
  },
];

function renderExtractionCard(
  overrides?: Partial<React.ComponentProps<typeof StructuredResultCard>>
) {
  return render(
    <StructuredResultCard
      schemaType="extraction_result"
      data={{ issues: mockIssues, summary: 'Found 3 issues' }}
      {...overrides}
    />
  );
}

describe('ExtractionResultCard', () => {
  const mockOnCreateIssues = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders issue count and summary', () => {
    renderExtractionCard();

    expect(screen.getByText('Extracted 3 Issues')).toBeInTheDocument();
    expect(screen.getByText('Found 3 issues')).toBeInTheDocument();
  });

  it('renders all issue titles', () => {
    renderExtractionCard();

    expect(screen.getByText('Fix login timeout')).toBeInTheDocument();
    expect(screen.getByText('Add dark mode')).toBeInTheDocument();
    expect(screen.getByText('Refactor auth module')).toBeInTheDocument();
  });

  it('shows no issues message when empty', () => {
    render(<StructuredResultCard schemaType="extraction_result" data={{ issues: [] }} />);

    expect(screen.getByText('No issues found.')).toBeInTheDocument();
  });

  it('toggles issue selection on click', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    // Click first issue
    await user.click(screen.getByText('Fix login timeout'));

    // Should show "1 selected"
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  it('selects all issues via Select All', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    await user.click(screen.getByText('Select All'));
    expect(screen.getByText('3 selected')).toBeInTheDocument();
  });

  it('selects recommended (high/urgent priority) via Select Recommended', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    await user.click(screen.getByText('Select Recommended'));
    // high + urgent = 2 issues
    expect(screen.getByText('2 selected')).toBeInTheDocument();
  });

  it('shows Create button only when issues selected and callback provided', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    // Initially no create button (nothing selected)
    expect(screen.queryByText(/Create \d+ Issue/)).not.toBeInTheDocument();

    // Select an issue
    await user.click(screen.getByText('Fix login timeout'));

    // Now the button should appear
    expect(screen.getByText('Create 1 Issue')).toBeInTheDocument();
  });

  it('does not show Create button when no callback provided', async () => {
    const user = userEvent.setup();
    renderExtractionCard(); // no onCreateIssues

    await user.click(screen.getByText('Select All'));

    // No create button even with selection
    expect(screen.queryByText(/Create \d+ Issue/)).not.toBeInTheDocument();
  });

  it('calls onCreateIssues with selected indices', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    // Select first and third issues
    await user.click(screen.getByText('Fix login timeout'));
    await user.click(screen.getByText('Refactor auth module'));

    // Click create
    await user.click(screen.getByText('Create 2 Issues'));

    expect(mockOnCreateIssues).toHaveBeenCalledOnce();
    const args = mockOnCreateIssues.mock.calls[0]![0] as number[];
    expect(args).toHaveLength(2);
    expect(args).toContain(0);
    expect(args).toContain(2);
  });

  it('shows loading state when isCreatingIssues is true', async () => {
    const user = userEvent.setup();
    renderExtractionCard({
      onCreateIssues: mockOnCreateIssues,
      isCreatingIssues: true,
    });

    // Select an issue first
    await user.click(screen.getByText('Fix login timeout'));

    // Should show "Creating..." instead of "Create 1 Issue"
    expect(screen.getByText('Creating...')).toBeInTheDocument();
  });

  it('renders unknown schema type fallback', () => {
    render(<StructuredResultCard schemaType="unknown_type" data={{}} />);

    expect(screen.getByText('Unknown result type: unknown_type')).toBeInTheDocument();
  });

  it('renders decomposition_result schema', () => {
    render(
      <StructuredResultCard
        schemaType="decomposition_result"
        data={{
          subtasks: [{ title: 'Task 1', description: 'Do this', storyPoints: 3, dependsOn: [] }],
          totalPoints: 3,
        }}
      />
    );

    expect(screen.getByText(/Task Breakdown/)).toBeInTheDocument();
    expect(screen.getByText('Task 1')).toBeInTheDocument();
  });
});
