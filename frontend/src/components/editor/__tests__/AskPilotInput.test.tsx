/**
 * Unit tests for AskPilotInput component.
 *
 * Tests inline AI assistant input behavior, submission, and callbacks.
 *
 * @module components/editor/__tests__/AskPilotInput.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AskPilotInput } from '../AskPilotInput';

describe('AskPilotInput', () => {
  const mockOnSubmit = vi.fn();
  const mockOnChatViewOpen = vi.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
    mockOnChatViewOpen.mockClear();
  });

  it('test_submit_calls_onChatViewOpen — Enter key calls onChatViewOpen', async () => {
    render(
      <AskPilotInput
        noteId="note-123"
        workspaceId="workspace-456"
        onSubmit={mockOnSubmit}
        onChatViewOpen={mockOnChatViewOpen}
      />
    );

    const input = screen.getByRole('textbox', { name: /ask pilot ai assistant/i });

    // Type a question
    fireEvent.change(input, { target: { value: 'Extract issues from this note' } });

    // Press Enter
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnChatViewOpen).toHaveBeenCalledTimes(1);
    });
  });

  it('test_submit_calls_onSubmit_with_value — Enter key calls onSubmit with trimmed input', async () => {
    mockOnSubmit.mockResolvedValue(undefined);

    render(
      <AskPilotInput
        noteId="note-123"
        workspaceId="workspace-456"
        onSubmit={mockOnSubmit}
        onChatViewOpen={mockOnChatViewOpen}
      />
    );

    const input = screen.getByRole('textbox', { name: /ask pilot ai assistant/i });

    // Type a question with extra whitespace
    fireEvent.change(input, { target: { value: '  What are the key points?  ' } });

    // Press Enter
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith('What are the key points?');
    });
  });

  it('test_empty_input_does_not_submit — Empty string does not trigger callbacks', async () => {
    render(
      <AskPilotInput
        noteId="note-123"
        workspaceId="workspace-456"
        onSubmit={mockOnSubmit}
        onChatViewOpen={mockOnChatViewOpen}
      />
    );

    const input = screen.getByRole('textbox', { name: /ask pilot ai assistant/i });

    // Press Enter without typing anything
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    // Wait to ensure no async calls happen
    await waitFor(() => {
      expect(mockOnSubmit).not.toHaveBeenCalled();
      expect(mockOnChatViewOpen).not.toHaveBeenCalled();
    });

    // Try with whitespace only
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnSubmit).not.toHaveBeenCalled();
      expect(mockOnChatViewOpen).not.toHaveBeenCalled();
    });
  });

  it('test_clears_input_after_submit — After submit, input value is cleared', async () => {
    mockOnSubmit.mockResolvedValue(undefined);

    render(
      <AskPilotInput
        noteId="note-123"
        workspaceId="workspace-456"
        onSubmit={mockOnSubmit}
        onChatViewOpen={mockOnChatViewOpen}
      />
    );

    const input = screen.getByRole('textbox', {
      name: /ask pilot ai assistant/i,
    }) as HTMLInputElement;

    // Type a question
    fireEvent.change(input, { target: { value: 'Summarize this note' } });
    expect(input.value).toBe('Summarize this note');

    // Press Enter
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    // Input should be cleared immediately (before async onSubmit completes)
    await waitFor(() => {
      expect(input.value).toBe('');
    });

    // Ensure submit was called
    expect(mockOnSubmit).toHaveBeenCalledWith('Summarize this note');
  });
});
