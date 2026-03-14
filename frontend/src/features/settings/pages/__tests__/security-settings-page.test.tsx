/**
 * Tests for SecuritySettingsPage.
 *
 * AUTH-06, AUTH-07: Active sessions management and SCIM directory sync UI.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

const mockWorkspaceStore = {
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123', slug: 'test-workspace' }),
  isAdmin: true,
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
  }),
}));

const mockUseSessions = vi.fn();
const mockUseTerminateSession = vi.fn();
const mockUseTerminateAllUserSessions = vi.fn();
const mockUseGenerateScimToken = vi.fn();

vi.mock('@/features/settings/hooks/use-sessions', () => ({
  useSessions: (...args: unknown[]) => mockUseSessions(...args),
  useTerminateSession: (...args: unknown[]) => mockUseTerminateSession(...args),
  useTerminateAllUserSessions: (...args: unknown[]) => mockUseTerminateAllUserSessions(...args),
}));

vi.mock('@/features/settings/hooks/use-scim', () => ({
  useGenerateScimToken: (...args: unknown[]) => mockUseGenerateScimToken(...args),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return {
    ...actual,
    apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  };
});

const mockSessions = [
  {
    id: 'session-1',
    user_id: 'user-1',
    user_display_name: 'Alice Johnson',
    user_avatar_url: null,
    ip_address: '192.168.1.1',
    browser: 'Chrome 120',
    os: 'macOS 14',
    device: 'Desktop',
    last_seen_at: '2026-03-07T15:00:00Z',
    created_at: '2026-03-07T10:00:00Z',
    is_current: true,
  },
  {
    id: 'session-2',
    user_id: 'user-2',
    user_display_name: 'Bob Smith',
    user_avatar_url: null,
    ip_address: '10.0.0.2',
    browser: 'Firefox 121',
    os: 'Windows 11',
    device: 'Desktop',
    last_seen_at: '2026-03-07T14:00:00Z',
    created_at: '2026-03-07T09:00:00Z',
    is_current: false,
  },
];

function setupDefaultMocks() {
  mockUseSessions.mockReturnValue({ data: mockSessions, isLoading: false, error: null });
  mockUseTerminateSession.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  mockUseTerminateAllUserSessions.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  mockUseGenerateScimToken.mockReturnValue({ mutateAsync: vi.fn(), isPending: false, data: null });
}

import { SecuritySettingsPage } from '../security-settings-page';

describe('SecuritySettingsPage', () => {
  beforeEach(() => {
    mockWorkspaceStore.isAdmin = true;
    setupDefaultMocks();
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders sessions table with mocked session data', () => {
    render(<SecuritySettingsPage />);

    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
  });

  it('current session row shows "(you)" badge', () => {
    render(<SecuritySettingsPage />);

    expect(screen.getByText('(you)')).toBeInTheDocument();
  });

  it('current session row has no Terminate button', () => {
    render(<SecuritySettingsPage />);

    // Only Bob (non-current) should have a Terminate button
    const terminateButtons = screen.getAllByRole('button', { name: /Terminate session/i });
    expect(terminateButtons).toHaveLength(1);
  });

  it('non-current session shows Terminate button', () => {
    render(<SecuritySettingsPage />);

    expect(screen.getByRole('button', { name: /Terminate session/i })).toBeInTheDocument();
  });

  it('terminate click shows AlertDialog', async () => {
    const user = userEvent.setup();
    render(<SecuritySettingsPage />);

    const terminateBtn = screen.getByRole('button', { name: /Terminate session/i });
    await user.click(terminateBtn);

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('alertdialog')).toHaveTextContent(/Terminate session/i);
  });

  it('shows page heading and amber alert for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    render(<SecuritySettingsPage />);

    expect(screen.getByRole('heading', { name: 'Security' })).toBeInTheDocument();
    expect(screen.getByText(/Manage active sessions/i)).toBeInTheDocument();
    expect(screen.getByText('Access restricted')).toBeInTheDocument();
    expect(screen.getByText(/Contact your workspace admin/i)).toBeInTheDocument();
    // Should not show the sessions table for non-admins
    expect(screen.queryByText('Active Sessions')).not.toBeInTheDocument();
  });

  it('SCIM URL displays workspace slug in URL', () => {
    render(<SecuritySettingsPage />);

    // The SCIM base URL input should contain the workspace slug
    const scimInput = screen.getByDisplayValue(/test-workspace/);
    expect(scimInput).toBeInTheDocument();
  });

  it('"Generate New SCIM Token" button is visible', () => {
    render(<SecuritySettingsPage />);

    expect(screen.getByRole('button', { name: /Generate New SCIM Token/i })).toBeInTheDocument();
  });

  it('token modal shows after successful mutation with copy button', async () => {
    const user = userEvent.setup();
    const mockToken = 'scim_abc123secrettoken';
    mockUseGenerateScimToken.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        token: mockToken,
        message: 'Store this token securely. It will not be shown again.',
      }),
      isPending: false,
      data: null,
    });
    render(<SecuritySettingsPage />);

    // Click generate token
    const generateBtn = screen.getByRole('button', { name: /Generate New SCIM Token/i });
    await user.click(generateBtn);

    // Confirm dialog should appear
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();

    // Confirm the action
    const confirmBtn = screen.getByRole('button', { name: /^Generate$/i });
    await user.click(confirmBtn);

    // Token dialog should appear with copy button
    expect(screen.getByText(mockToken)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy token/i })).toBeInTheDocument();
  });
});
