/**
 * Tests for ProfileSettingsPage.
 *
 * T013: Display name editing, read-only email, save via authStore.updateProfile.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const { mockToast } = vi.hoisted(() => ({
  mockToast: { success: vi.fn(), error: vi.fn() },
}));
vi.mock('sonner', () => ({
  toast: mockToast,
}));

const mockAuthStore: {
  user: { id: string; name: string; email: string; avatarUrl: string | null } | null;
  userInitials: string;
  error: string | null;
  updateProfile: ReturnType<typeof vi.fn>;
} = {
  user: {
    id: 'user-1',
    name: 'John Doe',
    email: 'john@example.com',
    avatarUrl: null,
  },
  userInitials: 'JD',
  error: null,
  updateProfile: vi.fn().mockResolvedValue(true),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    authStore: mockAuthStore,
  }),
}));

import { ProfileSettingsPage } from '../profile-settings-page';

describe('ProfileSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthStore.user = {
      id: 'user-1',
      name: 'John Doe',
      email: 'john@example.com',
      avatarUrl: null,
    };
    mockAuthStore.error = null;
    mockAuthStore.updateProfile = vi.fn().mockResolvedValue(true);
  });

  it('renders profile page with user info', () => {
    render(<ProfileSettingsPage />);

    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByLabelText('Display Name')).toHaveValue('John Doe');
    expect(screen.getByLabelText('Email')).toHaveValue('john@example.com');
  });

  it('email input is read-only', () => {
    render(<ProfileSettingsPage />);

    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toBeDisabled();
    expect(emailInput).toHaveAttribute('readOnly');
  });

  it('save button disabled when no changes', () => {
    render(<ProfileSettingsPage />);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).toBeDisabled();
  });

  it('returns null when no user', () => {
    mockAuthStore.user = null;

    const { container } = render(<ProfileSettingsPage />);
    expect(container.innerHTML).toBe('');
  });

  it('calls updateProfile and shows success toast on save', async () => {
    const user = userEvent.setup();
    render(<ProfileSettingsPage />);

    const nameInput = screen.getByLabelText('Display Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Jane Doe');

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).not.toBeDisabled();

    fireEvent.submit(saveButton.closest('form')!);

    await waitFor(() => {
      expect(mockAuthStore.updateProfile).toHaveBeenCalledWith({ name: 'Jane Doe' });
    });

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('Profile updated', expect.any(Object));
    });
  });

  it('shows error toast when save fails', async () => {
    mockAuthStore.updateProfile = vi.fn().mockResolvedValue(false);
    mockAuthStore.error = 'Network error';

    const user = userEvent.setup();
    render(<ProfileSettingsPage />);

    const nameInput = screen.getByLabelText('Display Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Jane Doe');

    fireEvent.submit(screen.getByRole('button', { name: /save changes/i }).closest('form')!);

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'Failed to update profile',
        expect.objectContaining({ description: 'Network error' })
      );
    });
  });

  it('shows unsaved changes indicator when name modified', async () => {
    const user = userEvent.setup();
    render(<ProfileSettingsPage />);

    expect(screen.queryByText('You have unsaved changes.')).not.toBeInTheDocument();

    const nameInput = screen.getByLabelText('Display Name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Different Name');

    expect(screen.getByText('You have unsaved changes.')).toBeInTheDocument();
  });
});
