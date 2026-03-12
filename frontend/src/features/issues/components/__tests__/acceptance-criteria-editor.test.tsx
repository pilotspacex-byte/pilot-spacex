/**
 * AcceptanceCriteriaEditor component tests.
 *
 * Verifies: stable item keys (H-8), mutateRef pattern (H-7),
 * flush-on-unmount (H-9), dirty-state prop sync skip (M-11),
 * add/remove/edit items, Enter key to add.
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AcceptanceCriteriaEditor } from '../acceptance-criteria-editor';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUpdate = vi.fn().mockResolvedValue({});

vi.mock('@/services/api', () => ({
  issuesApi: {
    update: (...args: unknown[]) => mockUpdate(...args),
  },
}));

vi.mock('@/features/issues/hooks/use-issue-detail', () => ({
  issueDetailKeys: {
    detail: (id: string) => ['issues', 'detail', id],
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

const defaultProps = {
  issueId: 'issue-1',
  workspaceId: 'ws-1',
  criteria: ['First criterion', 'Second criterion'],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AcceptanceCriteriaEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders all criteria items', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByDisplayValue('First criterion')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Second criterion')).toBeInTheDocument();
  });

  it('adds a new item on Enter key', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const input = screen.getByLabelText('New acceptance criterion');
    fireEvent.change(input, { target: { value: 'Third criterion' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(screen.getByDisplayValue('Third criterion')).toBeInTheDocument();
    // Input should be cleared
    expect(input).toHaveValue('');
  });

  it('adds a new item on Add button click', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const input = screen.getByLabelText('New acceptance criterion');
    fireEvent.change(input, { target: { value: 'New item' } });
    fireEvent.click(screen.getByLabelText('Add criterion'));

    expect(screen.getByDisplayValue('New item')).toBeInTheDocument();
  });

  it('does not add empty items', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const input = screen.getByLabelText('New acceptance criterion');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Should still only have original 2 items
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
  });

  it('removes an item when remove button is clicked', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByLabelText('Remove criterion: First criterion'));

    expect(screen.queryByDisplayValue('First criterion')).not.toBeInTheDocument();
    expect(screen.getByDisplayValue('Second criterion')).toBeInTheDocument();
  });

  it('edits an item inline', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const firstInput = screen.getByDisplayValue('First criterion');
    fireEvent.change(firstInput, { target: { value: 'Updated criterion' } });

    expect(screen.getByDisplayValue('Updated criterion')).toBeInTheDocument();
  });

  it('debounces save and calls API after DEBOUNCE_MS (H-7)', async () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const firstInput = screen.getByDisplayValue('First criterion');
    fireEvent.change(firstInput, { target: { value: 'Updated' } });

    // Should not save immediately
    expect(mockUpdate).not.toHaveBeenCalled();

    // Advance past debounce
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockUpdate).toHaveBeenCalledWith('ws-1', 'issue-1', {
      acceptanceCriteria: ['Updated', 'Second criterion'],
    });
  });

  it('flushes pending save on unmount (H-9)', async () => {
    const { unmount } = render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const firstInput = screen.getByDisplayValue('First criterion');
    fireEvent.change(firstInput, { target: { value: 'Unsaved edit' } });

    // Should not have saved yet (still within debounce)
    expect(mockUpdate).not.toHaveBeenCalled();

    // Unmount triggers flush — mutation.mutate is async internally,
    // so we need to flush microtasks after unmount
    await act(async () => {
      unmount();
    });

    expect(mockUpdate).toHaveBeenCalledWith('ws-1', 'issue-1', {
      acceptanceCriteria: ['Unsaved edit', 'Second criterion'],
    });
  });

  it('skips prop sync when dirty (M-11)', async () => {
    const { rerender } = render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    // Make a local edit (marks dirty)
    const firstInput = screen.getByDisplayValue('First criterion');
    fireEvent.change(firstInput, { target: { value: 'Local edit' } });

    // Rerender with different criteria from server
    rerender(
      <AcceptanceCriteriaEditor {...defaultProps} criteria={['Server value 1', 'Server value 2']} />
    );

    // Local edit should be preserved, not overwritten by server
    expect(screen.getByDisplayValue('Local edit')).toBeInTheDocument();
  });

  it('accepts prop sync when not dirty', () => {
    const { rerender } = render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    // No local edits, rerender with new props
    rerender(<AcceptanceCriteriaEditor {...defaultProps} criteria={['New server criterion']} />);

    expect(screen.getByDisplayValue('New server criterion')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('First criterion')).not.toBeInTheDocument();
  });

  it('uses stable keys so removing an item preserves others (H-8)', () => {
    render(<AcceptanceCriteriaEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    // Add a third item
    const input = screen.getByLabelText('New acceptance criterion');
    fireEvent.change(input, { target: { value: 'Third' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    // Remove the first item
    fireEvent.click(screen.getByLabelText('Remove criterion: First criterion'));

    // Second and third should remain with correct values
    expect(screen.getByDisplayValue('Second criterion')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Third')).toBeInTheDocument();
  });
});
