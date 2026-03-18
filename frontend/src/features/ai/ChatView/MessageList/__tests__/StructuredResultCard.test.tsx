/**
 * Unit tests for StructuredResultCard — ExtractionResultCard flow.
 *
 * Tests selection UI, "Create Selected Issues" action, loading state,
 * post-creation state, confidence badges, labels, and inline editing.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
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
    confidence: 0.85,
    labels: ['auth', 'critical'],
  },
  {
    title: 'Add dark mode',
    description: 'Support dark mode theme',
    issue_type: 'feature',
    priority: 'low',
    category: 'implicit',
    source_block_id: null,
    confidence: 0.55,
    labels: ['ui'],
  },
  {
    title: 'Refactor auth module',
    description: 'Clean up authentication code',
    issue_type: 'task',
    priority: 'urgent',
    category: 'related',
    source_block_id: 'block-2',
    confidence: 0.3,
    labels: [],
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

    // Click the checkbox for the first issue
    const selectButtons = screen.getAllByRole('checkbox', { name: /Select issue/i });
    await user.click(selectButtons[0]!);

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
    const selectButtons = screen.getAllByRole('checkbox', { name: /Select issue/i });
    await user.click(selectButtons[0]!);

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

  it('calls onCreateIssues with selected indices and edit overrides', async () => {
    const user = userEvent.setup();
    renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

    // Select first and third issues
    const selectButtons = screen.getAllByRole('checkbox', { name: /Select issue/i });
    await user.click(selectButtons[0]!);
    await user.click(selectButtons[2]!);

    // Click create
    await user.click(screen.getByText('Create 2 Issues'));

    expect(mockOnCreateIssues).toHaveBeenCalledOnce();
    const [indices, overrides] = mockOnCreateIssues.mock.calls[0]!;
    expect(indices).toHaveLength(2);
    expect(indices).toContain(0);
    expect(indices).toContain(2);
    expect(overrides).toBeInstanceOf(Map);
  });

  it('shows loading state when isCreatingIssues is true', async () => {
    const user = userEvent.setup();
    renderExtractionCard({
      onCreateIssues: mockOnCreateIssues,
      isCreatingIssues: true,
    });

    // Select an issue first
    const selectButtons = screen.getAllByRole('checkbox', { name: /Select issue/i });
    await user.click(selectButtons[0]!);

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

  // R2: Post-creation state tests
  describe('post-creation state', () => {
    const createdIssues = [
      { id: 'uuid-1', identifier: 'PILOT-1', title: 'Fix login timeout' },
      { id: 'uuid-2', identifier: 'PILOT-2', title: 'Refactor auth module' },
    ];

    it('shows collapsed success banner after creation', () => {
      renderExtractionCard({ createdIssues });

      expect(screen.getByText('Created 2 issues')).toBeInTheDocument();
      // Issue links should not be visible initially (collapsed)
      expect(screen.queryByText('PILOT-1')).not.toBeInTheDocument();
    });

    it('expands to show created issue identifiers', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ createdIssues, workspaceSlug: 'my-workspace' });

      // Click to expand
      await user.click(screen.getByText('Created 2 issues'));

      expect(screen.getByText('PILOT-1')).toBeInTheDocument();
      expect(screen.getByText('PILOT-2')).toBeInTheDocument();
    });

    it('renders issue links when workspaceSlug is provided', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ createdIssues, workspaceSlug: 'my-workspace' });

      await user.click(screen.getByText('Created 2 issues'));

      const link = screen.getByText('PILOT-1').closest('a');
      expect(link).toHaveAttribute('href', '/my-workspace/issues/uuid-1');
    });

    it('renders spans instead of links when workspaceSlug is missing', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ createdIssues });

      await user.click(screen.getByText('Created 2 issues'));

      const element = screen.getByText('PILOT-1');
      expect(element.closest('a')).toBeNull();
      expect(element.tagName).toBe('SPAN');
    });
  });

  // R4: Confidence badges
  describe('confidence badges', () => {
    it('renders High confidence badge for score >= 0.7', () => {
      renderExtractionCard();

      const highBadges = screen.getAllByText('High');
      expect(highBadges.length).toBeGreaterThanOrEqual(1);
    });

    it('renders Medium confidence badge for score 0.5-0.7', () => {
      renderExtractionCard();

      expect(screen.getByText('Medium')).toBeInTheDocument();
    });

    it('renders Low confidence badge for score < 0.5', () => {
      renderExtractionCard();

      expect(screen.getByText('Low')).toBeInTheDocument();
    });
  });

  // R5: Labels display
  describe('labels display', () => {
    it('renders label chips when labels exist', () => {
      renderExtractionCard();

      expect(screen.getByText('auth')).toBeInTheDocument();
      expect(screen.getByText('critical')).toBeInTheDocument();
      expect(screen.getByText('ui')).toBeInTheDocument();
    });

    it('does not render label chips for empty labels array', () => {
      render(
        <StructuredResultCard
          schemaType="extraction_result"
          data={{
            issues: [
              {
                title: 'No labels issue',
                description: 'Test',
                issue_type: 'bug',
                priority: 'medium',
                category: 'explicit',
                labels: [],
              },
            ],
          }}
        />
      );

      // Only one issue, and it has empty labels — no label chips should render
      const region = screen.getByRole('region');
      expect(within(region).queryByText('auth')).not.toBeInTheDocument();
    });
  });

  // R3: Inline editing
  describe('inline editing', () => {
    it('shows edit button when onCreateIssues is provided', () => {
      renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

      const editButtons = screen.getAllByRole('button', { name: 'Edit issue' });
      expect(editButtons.length).toBe(3);
    });

    it('does not show edit button when no onCreateIssues', () => {
      renderExtractionCard();

      expect(screen.queryByRole('button', { name: 'Edit issue' })).not.toBeInTheDocument();
    });

    it('shows title input and priority select when editing', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

      // Click edit on first issue
      const editButtons = screen.getAllByRole('button', { name: 'Edit issue' });
      await user.click(editButtons[0]!);

      expect(screen.getByLabelText('Edit issue title')).toBeInTheDocument();
      expect(screen.getByLabelText('Edit issue priority')).toBeInTheDocument();
    });

    it('closes edit mode when done button clicked', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

      // Open edit
      const editButtons = screen.getAllByRole('button', { name: 'Edit issue' });
      await user.click(editButtons[0]!);

      // Close edit
      await user.click(screen.getByRole('button', { name: 'Done editing' }));

      // Title input should be gone
      expect(screen.queryByLabelText('Edit issue title')).not.toBeInTheDocument();
    });

    it('passes edited title and priority in overrides when creating', async () => {
      const user = userEvent.setup();
      renderExtractionCard({ onCreateIssues: mockOnCreateIssues });

      // Edit the first issue's title
      const editButtons = screen.getAllByRole('button', { name: 'Edit issue' });
      await user.click(editButtons[0]!);

      const titleInput = screen.getByLabelText('Edit issue title');
      await user.clear(titleInput);
      await user.type(titleInput, 'Updated title');

      const prioritySelect = screen.getByLabelText('Edit issue priority');
      await user.selectOptions(prioritySelect, 'low');

      // Close edit mode
      await user.click(screen.getByRole('button', { name: 'Done editing' }));

      // Select the edited issue and create
      const selectButtons = screen.getAllByRole('checkbox', { name: /Select issue/i });
      await user.click(selectButtons[0]!);
      await user.click(screen.getByText('Create 1 Issue'));

      expect(mockOnCreateIssues).toHaveBeenCalledOnce();
      const [indices, overrides] = mockOnCreateIssues.mock.calls[0]!;
      expect(indices).toContain(0);
      expect(overrides).toBeInstanceOf(Map);
      expect(overrides.get(0)).toEqual({ title: 'Updated title', priority: 'low' });
    });
  });
});
