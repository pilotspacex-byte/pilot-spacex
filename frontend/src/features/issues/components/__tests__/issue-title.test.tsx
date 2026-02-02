/**
 * IssueTitle component tests (T031).
 *
 * Verifies display/edit mode, Enter/Escape key handling,
 * validation (empty, >255 chars), disabled state, and SaveStatus.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IssueTitle } from '../issue-title';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
const mockWrapMutation = vi.fn((fn: () => Promise<unknown>) => fn());

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn(), onAuthStateChange: vi.fn() },
  },
}));

vi.mock('@/stores', () => ({
  useIssueStore: () => ({
    getSaveStatus: vi.fn().mockReturnValue('idle'),
    setSaveStatus: vi.fn(),
  }),
}));

vi.mock('@/features/issues/hooks/use-update-issue', () => ({
  useUpdateIssue: () => ({
    mutateAsync: mockMutateAsync,
  }),
}));

vi.mock('@/features/issues/hooks/use-save-status', () => ({
  useSaveStatus: () => ({
    status: 'idle',
    wrapMutation: mockWrapMutation,
  }),
}));

vi.mock('@/components/ui/save-status', () => ({
  SaveStatus: ({ status }: { status: string }) => <span data-testid="save-status">{status}</span>,
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueTitle', () => {
  const defaultProps = {
    title: 'Fix login bug',
    issueId: 'issue-1',
    workspaceId: 'ws-1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue(undefined);
    mockWrapMutation.mockImplementation((fn: () => Promise<unknown>) => fn());
  });

  it('renders title text in display mode', () => {
    render(<IssueTitle {...defaultProps} />);

    expect(
      screen.getByRole('button', { name: /Edit issue title: Fix login bug/ })
    ).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('clicking title enters edit mode with input', () => {
    render(<IssueTitle {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));

    const input = screen.getByRole('textbox', { name: 'Issue title' });
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue('Fix login bug');
  });

  it('Enter key confirms edit and calls mutateAsync', async () => {
    render(<IssueTitle {...defaultProps} />);

    // Enter edit mode
    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));
    const input = screen.getByRole('textbox', { name: 'Issue title' });

    // Change value and press Enter
    fireEvent.change(input, { target: { value: 'Updated title' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({ name: 'Updated title' });
    });

    // Should exit edit mode
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('Escape key cancels edit and reverts to original', () => {
    render(<IssueTitle {...defaultProps} />);

    // Enter edit mode
    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));
    const input = screen.getByRole('textbox', { name: 'Issue title' });

    // Change value and press Escape
    fireEvent.change(input, { target: { value: 'Something different' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    // Should exit edit mode and show original title
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Edit issue title: Fix login bug/ })
    ).toBeInTheDocument();
  });

  it('empty title is not saved (validation)', async () => {
    render(<IssueTitle {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));
    const input = screen.getByRole('textbox', { name: 'Issue title' });

    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // mutateAsync should not be called for empty title
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('title > 255 chars is not saved', async () => {
    render(<IssueTitle {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));
    const input = screen.getByRole('textbox', { name: 'Issue title' });

    const longTitle = 'A'.repeat(256);
    fireEvent.change(input, { target: { value: longTitle } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // mutateAsync should not be called for too-long title
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('disabled prop prevents editing', () => {
    render(<IssueTitle {...defaultProps} disabled />);

    const button = screen.getByRole('button', { name: /Edit issue title/ });
    expect(button).toBeDisabled();

    fireEvent.click(button);
    // Should not enter edit mode
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('SaveStatus component renders', () => {
    render(<IssueTitle {...defaultProps} />);

    expect(screen.getByTestId('save-status')).toBeInTheDocument();
  });

  it('shows validation error for empty title', () => {
    render(<IssueTitle {...defaultProps} />);

    fireEvent.click(screen.getByRole('button', { name: /Edit issue title/ }));
    const input = screen.getByRole('textbox', { name: 'Issue title' });

    fireEvent.change(input, { target: { value: '' } });

    expect(screen.getByRole('alert')).toHaveTextContent('Title cannot be empty');
  });
});
