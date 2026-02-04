/**
 * CommentInput component tests (T039).
 *
 * Verifies textarea/button rendering, empty submit prevention,
 * Enter/Shift+Enter key handling, clearing after submit,
 * loading state, disabled state, and custom placeholder.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CommentInput } from '../comment-input';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CommentInput', () => {
  const defaultOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders textarea and submit button', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    expect(screen.getByRole('textbox', { name: 'Comment input' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send comment' })).toBeInTheDocument();
  });

  it('submit button disabled when textarea empty', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const button = screen.getByRole('button', { name: 'Send comment' });
    expect(button).toBeDisabled();
  });

  it('submit button enabled when textarea has content', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: 'A comment' } });

    const button = screen.getByRole('button', { name: 'Send comment' });
    expect(button).not.toBeDisabled();
  });

  it('Enter key submits content (calls onSubmit)', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(defaultOnSubmit).toHaveBeenCalledWith('Hello world');
  });

  it('Shift+Enter does not submit', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(defaultOnSubmit).not.toHaveBeenCalled();
  });

  it('clears textarea after successful submit', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' }) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Some comment' } });
    expect(textarea.value).toBe('Some comment');

    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(textarea.value).toBe('');
  });

  it('shows loading state during submission', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} isSubmitting />);

    const button = screen.getByRole('button', { name: 'Send comment' });
    expect(button).toBeDisabled();

    // Loader icon should be visible
    const loader = button.querySelector('.animate-spin');
    expect(loader).toBeTruthy();
  });

  it('disabled prop disables textarea and button', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} disabled />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    expect(textarea).toBeDisabled();

    const button = screen.getByRole('button', { name: 'Send comment' });
    expect(button).toBeDisabled();
  });

  it('trims whitespace before submitting', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: '  Hello  ' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(defaultOnSubmit).toHaveBeenCalledWith('Hello');
  });

  it('does not submit whitespace-only content', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: '   ' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(defaultOnSubmit).not.toHaveBeenCalled();
  });

  it('form submit also works via button click', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: 'Button click' } });

    const button = screen.getByRole('button', { name: 'Send comment' });
    fireEvent.click(button);

    expect(defaultOnSubmit).toHaveBeenCalledWith('Button click');
  });

  it('shows keyboard hints', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    expect(screen.getByText('Enter')).toBeInTheDocument();
    expect(screen.getByText('Shift+Enter')).toBeInTheDocument();
  });

  it('prevents content exceeding MAX_CHARS (10000)', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' }) as HTMLTextAreaElement;
    const longContent = 'A'.repeat(10001);
    fireEvent.change(textarea, { target: { value: longContent } });

    // Should not accept content beyond limit
    expect(textarea.value.length).toBeLessThanOrEqual(10000);
  });

  it('does not submit when isSubmitting is true', () => {
    render(<CommentInput onSubmit={defaultOnSubmit} isSubmitting />);

    const textarea = screen.getByRole('textbox', { name: 'Comment input' });
    fireEvent.change(textarea, { target: { value: 'Should not submit' } });
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });

    expect(defaultOnSubmit).not.toHaveBeenCalled();
  });
});
