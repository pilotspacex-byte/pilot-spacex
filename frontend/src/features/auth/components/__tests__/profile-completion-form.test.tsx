/**
 * ProfileCompletionForm tests — S011
 *
 * Covers:
 * - Renders full name input and submit button
 * - Disables submit when name is too short
 * - Calls PATCH /users/me on submit
 * - Shows loading state while submitting
 * - Calls onComplete() after successful save
 * - Shows error toast on API failure
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockApiClientPatch = vi.fn();

vi.mock('@/services/api/client', () => ({
  apiClient: {
    patch: (...args: unknown[]) => mockApiClientPatch(...args),
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

// Minimal UI mocks
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

import { ProfileCompletionForm } from '../profile-completion-form';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ProfileCompletionForm', () => {
  const onComplete = vi.fn();

  function setup(overrides: { onComplete?: () => void } = {}) {
    return render(<ProfileCompletionForm onComplete={overrides.onComplete ?? onComplete} />);
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the full name input and submit button', () => {
    setup();

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue to workspace/i })).toBeInTheDocument();
  });

  it('disables the submit button when name is empty', () => {
    setup();

    const btn = screen.getByRole('button', { name: /continue to workspace/i });
    expect(btn).toBeDisabled();
  });

  it('disables the submit button when name is only 1 character', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'A');
    expect(screen.getByRole('button', { name: /continue to workspace/i })).toBeDisabled();
  });

  it('enables the submit button when name has 2+ characters', async () => {
    const user = userEvent.setup();
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice');
    expect(screen.getByRole('button', { name: /continue to workspace/i })).not.toBeDisabled();
  });

  it('calls PATCH /users/me with trimmed full_name on submit', async () => {
    const user = userEvent.setup();
    mockApiClientPatch.mockResolvedValue({});
    setup();

    await user.type(screen.getByLabelText(/full name/i), '  Alice Smith  ');
    await user.click(screen.getByRole('button', { name: /continue to workspace/i }));

    await waitFor(() => {
      expect(mockApiClientPatch).toHaveBeenCalledWith('/users/me', {
        full_name: 'Alice Smith',
      });
    });
  });

  it('calls onComplete() after successful save', async () => {
    const user = userEvent.setup();
    mockApiClientPatch.mockResolvedValue({});
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.click(screen.getByRole('button', { name: /continue to workspace/i }));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledOnce();
    });
  });

  it('shows success toast after save', async () => {
    const user = userEvent.setup();
    mockApiClientPatch.mockResolvedValue({});
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.click(screen.getByRole('button', { name: /continue to workspace/i }));

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith('Profile saved!');
    });
  });

  it('shows error toast and does not call onComplete on API failure', async () => {
    const user = userEvent.setup();
    mockApiClientPatch.mockRejectedValue(new Error('Network error'));
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.click(screen.getByRole('button', { name: /continue to workspace/i }));

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith(
        'Failed to save profile. Please try again.',
      );
    });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('disables input while submitting', async () => {
    const user = userEvent.setup();
    let resolveApi!: (v: unknown) => void;
    mockApiClientPatch.mockReturnValue(new Promise((r) => (resolveApi = r)));
    setup();

    await user.type(screen.getByLabelText(/full name/i), 'Alice Smith');
    await user.click(screen.getByRole('button', { name: /continue to workspace/i }));

    // Input should be disabled while API is in-flight
    expect(screen.getByLabelText(/full name/i)).toBeDisabled();

    // Resolve API
    resolveApi({});
    await waitFor(() => expect(onComplete).toHaveBeenCalled());
  });
});
