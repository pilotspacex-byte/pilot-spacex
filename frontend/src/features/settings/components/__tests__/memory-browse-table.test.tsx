/**
 * Tests for MemoryBrowseTable - Phase 71 memory browse table component.
 *
 * Verifies: table rendering, pagination display, row click, checkbox selection,
 * score column visibility based on search query.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryBrowseTable } from '../memory-browse-table';
import type { MemoryListItem, MemoryListResponse } from '../../hooks/use-ai-memory';

// Mock useMemoryList
const mockUseMemoryList = vi.fn();
vi.mock('../../hooks/use-ai-memory', () => ({
  useMemoryList: (...args: unknown[]) => mockUseMemoryList(...args),
}));

const makeItem = (overrides?: Partial<MemoryListItem>): MemoryListItem => ({
  id: `mem-${Math.random().toString(36).slice(2, 8)}`,
  nodeType: 'note_chunk',
  kind: 'raw',
  label: 'Test Memory',
  contentSnippet: 'This is a test snippet of memory content...',
  pinned: false,
  score: null,
  sourceType: null,
  sourceId: null,
  createdAt: '2026-04-01T12:00:00Z',
  ...overrides,
});

const threeItems: MemoryListItem[] = [
  makeItem({ id: 'mem-1', label: 'First Memory', nodeType: 'note_chunk' }),
  makeItem({ id: 'mem-2', label: 'Second Memory', nodeType: 'issue_decision', pinned: true }),
  makeItem({ id: 'mem-3', label: 'Third Memory', nodeType: 'agent_turn', kind: 'summary' }),
];

const mockResponse = (
  items: MemoryListItem[],
  total: number,
  hasNext = false,
): { data: MemoryListResponse; isLoading: boolean } => ({
  data: { items, total, offset: 0, limit: 50, hasNext },
  isLoading: false,
});

const defaultProps = {
  workspaceId: 'ws-1',
  params: { offset: 0, limit: 50 },
  selectedIds: new Set<string>(),
  onSelectionChange: vi.fn(),
  onRowClick: vi.fn(),
  offset: 0,
  limit: 3,
  onPageChange: vi.fn(),
};

describe('MemoryBrowseTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders table with correct number of rows', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10, true));
    render(<MemoryBrowseTable {...defaultProps} />);

    expect(screen.getByText('First Memory')).toBeInTheDocument();
    expect(screen.getByText('Second Memory')).toBeInTheDocument();
    expect(screen.getByText('Third Memory')).toBeInTheDocument();
  });

  it('shows pagination info "Showing 1-3 of 10"', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10, true));
    render(<MemoryBrowseTable {...defaultProps} />);

    expect(screen.getByText('Showing 1-3 of 10')).toBeInTheDocument();
  });

  it('calls onRowClick with the item ID when a row is clicked', async () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    const onRowClick = vi.fn();
    const user = userEvent.setup();

    render(<MemoryBrowseTable {...defaultProps} onRowClick={onRowClick} />);

    await user.click(screen.getByText('First Memory'));
    expect(onRowClick).toHaveBeenCalledWith('mem-1');
  });

  it('updates selection when checkbox is clicked', async () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    const onSelectionChange = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryBrowseTable
        {...defaultProps}
        onSelectionChange={onSelectionChange}
      />,
    );

    // Click the first row's checkbox (find by aria-label)
    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is "select all", subsequent are per-row
    await user.click(checkboxes[1]!);

    expect(onSelectionChange).toHaveBeenCalledWith(new Set(['mem-1']));
  });

  it('shows score column when params.q is set', () => {
    mockUseMemoryList.mockReturnValue(
      mockResponse(
        [makeItem({ id: 'mem-1', label: 'Scored', score: 0.95 })],
        1,
      ),
    );

    render(
      <MemoryBrowseTable {...defaultProps} params={{ offset: 0, limit: 50, q: 'test query' }} />,
    );

    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('0.95')).toBeInTheDocument();
  });

  it('hides score column when params.q is not set', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    render(<MemoryBrowseTable {...defaultProps} />);

    expect(screen.queryByText('Score')).not.toBeInTheDocument();
  });

  it('renders empty state when no items', () => {
    mockUseMemoryList.mockReturnValue(mockResponse([], 0));
    render(<MemoryBrowseTable {...defaultProps} />);

    expect(screen.getByText('No memories yet')).toBeInTheDocument();
    expect(
      screen.getByText(/Memories are created automatically/),
    ).toBeInTheDocument();
  });

  it('disables Previous button on first page', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10, true));
    render(<MemoryBrowseTable {...defaultProps} offset={0} />);

    const prevButton = screen.getByRole('button', { name: /previous page/i });
    expect(prevButton).toBeDisabled();
  });

  it('disables Next button when hasNext is false', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 3, false));
    render(<MemoryBrowseTable {...defaultProps} />);

    const nextButton = screen.getByRole('button', { name: /next page/i });
    expect(nextButton).toBeDisabled();
  });

  it('calls onRowClick when Enter is pressed on a focused row', async () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    const onRowClick = vi.fn();
    const user = userEvent.setup();

    render(<MemoryBrowseTable {...defaultProps} onRowClick={onRowClick} />);

    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1..3] are data rows
    const firstDataRow = rows[1]!;
    firstDataRow.focus();
    await user.keyboard('{Enter}');

    expect(onRowClick).toHaveBeenCalledWith('mem-1');
  });

  it('moves focus to next row on ArrowDown', async () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    const user = userEvent.setup();

    render(<MemoryBrowseTable {...defaultProps} />);

    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1]!;
    const secondDataRow = rows[2]!;
    firstDataRow.focus();
    await user.keyboard('{ArrowDown}');

    expect(document.activeElement).toBe(secondDataRow);
  });

  it('toggles selection when Space is pressed on a focused row', async () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    const onSelectionChange = vi.fn();
    const user = userEvent.setup();

    render(
      <MemoryBrowseTable {...defaultProps} onSelectionChange={onSelectionChange} />,
    );

    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1]!;
    firstDataRow.focus();
    await user.keyboard(' ');

    expect(onSelectionChange).toHaveBeenCalledWith(new Set(['mem-1']));
  });

  it('rows have aria-selected attribute matching selection state', () => {
    mockUseMemoryList.mockReturnValue(mockResponse(threeItems, 10));
    render(
      <MemoryBrowseTable
        {...defaultProps}
        selectedIds={new Set(['mem-2'])}
      />,
    );

    const rows = screen.getAllByRole('row');
    // rows[1] = mem-1 (not selected), rows[2] = mem-2 (selected)
    expect(rows[1]).toHaveAttribute('aria-selected', 'false');
    expect(rows[2]).toHaveAttribute('aria-selected', 'true');
  });
});
