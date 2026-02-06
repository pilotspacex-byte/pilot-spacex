/**
 * Tests for ForgotPasswordPage.
 *
 * T034: Email input form, resetPassword call, FR-029 no email enumeration.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: Record<string, unknown>) => <div {...props}>{children}</div>,
  },
}));

vi.mock('@/stores/AuthStore', () => ({
  authStore: {
    resetPassword: vi.fn().mockResolvedValue(true),
    error: null,
    isLoading: false,
  },
}));

import ForgotPasswordPage from '../forgot-password/page';

describe('ForgotPasswordPage', () => {
  it('renders forgot password form', () => {
    render(<ForgotPasswordPage />);

    expect(screen.getByText('Forgot your password?')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
  });

  it('shows validation error for empty email', async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    expect(screen.getByText('Please enter your email address.')).toBeInTheDocument();
  });

  it('shows success message after submission', async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordPage />);

    await user.type(screen.getByLabelText('Email'), 'test@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    expect(screen.getByText('Check your email')).toBeInTheDocument();
  });

  it('has back to sign in link', () => {
    render(<ForgotPasswordPage />);

    const link = screen.getByRole('link', { name: /back to sign in/i });
    expect(link).toHaveAttribute('href', '/login');
  });
});
