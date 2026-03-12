/**
 * TechnicalRequirementsEditor component tests.
 *
 * Verifies: mutateRef pattern (H-7), flush-on-unmount (H-9),
 * dirty-state prop sync skip (M-11), textarea editing.
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TechnicalRequirementsEditor } from '../technical-requirements-editor';

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
  value: 'Initial requirements text',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TechnicalRequirementsEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with initial value', () => {
    render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByLabelText('Technical requirements (markdown)')).toHaveValue(
      'Initial requirements text'
    );
  });

  it('updates textarea on user input', () => {
    render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByLabelText('Technical requirements (markdown)');
    fireEvent.change(textarea, { target: { value: 'Updated text' } });

    expect(textarea).toHaveValue('Updated text');
  });

  it('debounces save and calls API after DEBOUNCE_MS (H-7)', async () => {
    render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByLabelText('Technical requirements (markdown)');
    fireEvent.change(textarea, { target: { value: 'New content' } });

    // Should not save immediately
    expect(mockUpdate).not.toHaveBeenCalled();

    // Advance past debounce
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockUpdate).toHaveBeenCalledWith('ws-1', 'issue-1', {
      technicalRequirements: 'New content',
    });
  });

  it('flushes pending save on unmount (H-9)', async () => {
    const { unmount } = render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByLabelText('Technical requirements (markdown)');
    fireEvent.change(textarea, { target: { value: 'Unsaved content' } });

    // Should not have saved yet
    expect(mockUpdate).not.toHaveBeenCalled();

    // Unmount triggers flush — mutation.mutate is async internally,
    // so we need to flush microtasks after unmount
    await act(async () => {
      unmount();
    });

    expect(mockUpdate).toHaveBeenCalledWith('ws-1', 'issue-1', {
      technicalRequirements: 'Unsaved content',
    });
  });

  it('skips prop sync when dirty (M-11)', () => {
    const { rerender } = render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    // Make a local edit (marks dirty)
    const textarea = screen.getByLabelText('Technical requirements (markdown)');
    fireEvent.change(textarea, { target: { value: 'Local edit' } });

    // Rerender with different value from server
    rerender(<TechnicalRequirementsEditor {...defaultProps} value="Server updated value" />);

    // Local edit should be preserved
    expect(textarea).toHaveValue('Local edit');
  });

  it('accepts prop sync when not dirty', () => {
    const { rerender } = render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    // No local edits, rerender with new props
    rerender(<TechnicalRequirementsEditor {...defaultProps} value="New server value" />);

    expect(screen.getByLabelText('Technical requirements (markdown)')).toHaveValue(
      'New server value'
    );
  });

  it('resets debounce timer on rapid edits', async () => {
    render(<TechnicalRequirementsEditor {...defaultProps} />, {
      wrapper: createWrapper(),
    });

    const textarea = screen.getByLabelText('Technical requirements (markdown)');

    // First edit
    fireEvent.change(textarea, { target: { value: 'Edit 1' } });

    // Advance 1500ms (before debounce fires)
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    expect(mockUpdate).not.toHaveBeenCalled();

    // Second edit resets the timer
    fireEvent.change(textarea, { target: { value: 'Edit 2' } });

    // Advance another 1500ms (3000ms total, but only 1500ms since last edit)
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    expect(mockUpdate).not.toHaveBeenCalled();

    // Advance to 2000ms since last edit
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    expect(mockUpdate).toHaveBeenCalledTimes(1);
    expect(mockUpdate).toHaveBeenCalledWith('ws-1', 'issue-1', { technicalRequirements: 'Edit 2' });
  });
});
