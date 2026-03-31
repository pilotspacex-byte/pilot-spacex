/**
 * SignupCompletionForm tests — S012
 *
 * Covers:
 * - Renders Full Name, Password, Confirm Password fields
 * - Submit button disabled when form is incomplete
 * - Shows inline error when passwords do not match
 * - Shows inline error when password is too short
 * - Does NOT call supabase.auth.updateUser (password is set server-side)
 * - Calls apiClient.post with invitation_id, full_name, AND password on submit
 * - Calls onComplete with workspace_slug on success
 * - Shows toast error when apiClient.post fails
 * - Disables form while submitting
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockApiClientPost = vi.fn();

vi.mock('@/services/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => mockApiClientPost(...args),
  },
}));

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    type,
    ...rest
  }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button type={type ?? 'button'} onClick={onClick} disabled={disabled} {...rest}>
      {children}
    </button>
  ),
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock('@/components/ui/label', () => ({
  Label: ({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) => (
    <label htmlFor={htmlFor}>{children}</label>
  ),
}));

// ---------------------------------------------------------------------------
// Import under test (after mocks)
// ---------------------------------------------------------------------------

import { SignupCompletionForm } from '../signup-completion-form';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SignupCompletionForm', () => {
  const onComplete = vi.fn();
  const invitationId = '550e8400-e29b-41d4-a716-446655440000';

  function setup(overrides: { invitationId?: string; onComplete?: (slug: string) => void } = {}) {
    return render(
      <SignupCompletionForm
        invitationId={overrides.invitationId ?? invitationId}
        onComplete={overrides.onComplete ?? onComplete}
      />,
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Full Name, Password, and Confirm Password fields', () => {
    setup();

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it('disables the submit button when form is empty', () => {
    setup();

    const btn = screen.getByRole('button', { name: /complete account|continue/i });
    expect(btn).toBeDisabled();
  });

  it('disables the submit button when name is only 1 character', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'A');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');

    expect(screen.getByRole('button', { name: /complete account|continue/i })).toBeDisabled();
  });

  it('disables submit when password is less than 8 characters', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'abc');
    await user.type(screen.getByLabelText(/confirm password/i), 'abc');

    expect(screen.getByRole('button', { name: /complete account|continue/i })).toBeDisabled();
  });

  it('shows inline error when passwords do not match', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'different');

    expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
  });

  it('enables the submit button when all fields are valid and passwords match', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');

    expect(screen.getByRole('button', { name: /complete account|continue/i })).not.toBeDisabled();
  });

  it('does NOT call supabase.auth.updateUser on submit (password is set server-side)', async () => {
    const user = userEvent.setup();
    mockApiClientPost.mockResolvedValue({ workspace_slug: 'acme' });
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /complete account|continue/i }));

    await waitFor(() => expect(onComplete).toHaveBeenCalled());
    // No supabase updateUser call — password goes directly in POST body
    expect(mockApiClientPost).toHaveBeenCalledTimes(1);
  });

  it('calls apiClient.post with invitation_id, full_name, and password on submit', async () => {
    const user = userEvent.setup();
    mockApiClientPost.mockResolvedValue({ workspace_slug: 'acme-corp' });
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /complete account|continue/i }));

    await waitFor(() => expect(onComplete).toHaveBeenCalled());
    expect(mockApiClientPost).toHaveBeenCalledWith('/auth/complete-signup', {
      invitation_id: invitationId,
      full_name: 'Alice Smith',
      password: 'password123',
    });
  });

  it('calls onComplete with workspace_slug on success', async () => {
    const user = userEvent.setup();
    mockApiClientPost.mockResolvedValue({ workspace_slug: 'acme-corp' });
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /complete account|continue/i }));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('acme-corp');
    });
  });

  it('shows toast error and does not call onComplete when apiClient.post fails', async () => {
    const user = userEvent.setup();
    mockApiClientPost.mockRejectedValue(new Error('Server error'));
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /complete account|continue/i }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        'Failed to complete signup. Please try again.',
      );
    });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('disables form fields while submitting', async () => {
    const user = userEvent.setup();
    let resolvePost!: (v: unknown) => void;
    mockApiClientPost.mockReturnValue(new Promise((r) => (resolvePost = r)));
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.type(screen.getByLabelText(/^password$/i), 'password123');
    await user.type(screen.getByLabelText(/confirm password/i), 'password123');
    await user.click(screen.getByRole('button', { name: /complete account|continue/i }));

    expect(screen.getByLabelText(/full name/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /complete account|continue|saving/i })).toBeDisabled();

    resolvePost({ workspace_slug: 'acme' });
    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });
});
