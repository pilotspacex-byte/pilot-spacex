/**
 * Tests for ResetPasswordPage.
 *
 * T035: Supabase token verification, password form, validation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown>) => <div {...props}>{children}</div>,
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

const mockSubscription = { unsubscribe: vi.fn() };
let authChangeCallback: ((event: string) => void) | null = null;

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: vi.fn((cb: (event: string) => void) => {
        authChangeCallback = cb;
        return { data: { subscription: mockSubscription } };
      }),
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      updateUser: vi.fn().mockResolvedValue({ error: null }),
    },
  },
}));

import ResetPasswordPage from '../reset-password/page';

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    authChangeCallback = null;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders loading state initially', () => {
    render(<ResetPasswordPage />);

    expect(screen.getByText('Verifying reset link...')).toBeInTheDocument();
  });

  it('shows expired state after timeout', async () => {
    render(<ResetPasswordPage />);

    expect(screen.getByText('Verifying reset link...')).toBeInTheDocument();

    // Wait for getSession promise to resolve, then advance timer
    await act(async () => {
      await Promise.resolve();
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText('Link expired')).toBeInTheDocument();
  });

  it('validates password length', async () => {
    vi.useRealTimers();
    const user = userEvent.setup();

    render(<ResetPasswordPage />);

    // Trigger PASSWORD_RECOVERY to show form
    await act(async () => {
      authChangeCallback?.('PASSWORD_RECOVERY');
    });

    const passwordInput = screen.getByLabelText('New Password');
    const confirmInput = screen.getByLabelText('Confirm Password');

    await user.type(passwordInput, 'short');
    await user.type(confirmInput, 'short');
    await user.click(screen.getByRole('button', { name: /update password/i }));

    expect(screen.getByText('Password must be at least 8 characters.')).toBeInTheDocument();
  });

  it('validates password match', async () => {
    vi.useRealTimers();
    const user = userEvent.setup();

    render(<ResetPasswordPage />);

    await act(async () => {
      authChangeCallback?.('PASSWORD_RECOVERY');
    });

    const passwordInput = screen.getByLabelText('New Password');
    const confirmInput = screen.getByLabelText('Confirm Password');

    await user.type(passwordInput, 'validpassword123');
    await user.type(confirmInput, 'differentpassword');
    await user.click(screen.getByRole('button', { name: /update password/i }));

    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
  });
});
