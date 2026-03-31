/**
 * Tests for /auth/invite page.
 *
 * T018: US3 — covers loading state, workspace name rendering,
 * expired/revoked errors, email form submission, 429 error, and
 * existing session fast path.
 *
 * Source: spec.md US1, US2, US3; tasks.md T018
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({
    get: (key: string) => (key === 'invitation_id' ? 'test-invitation-id' : null),
  }),
}));

const mockOnAuthStateChange = vi.fn();
const mockGetSession = vi.fn();
const mockSignOut = vi.fn();

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: mockOnAuthStateChange,
      getSession: mockGetSession,
      signOut: mockSignOut,
    },
  },
}));

const mockPreviewInvitation = vi.fn();
const mockRequestMagicLink = vi.fn();

vi.mock('@/features/members/hooks/use-workspace-invitations', () => ({
  previewInvitation: (...args: unknown[]) => mockPreviewInvitation(...args),
  requestMagicLink: (...args: unknown[]) => mockRequestMagicLink(...args),
}));

vi.mock('@/features/auth/components/signup-completion-form', () => ({
  SignupCompletionForm: ({
    invitationId,
    onComplete,
  }: {
    invitationId: string;
    onComplete: (slug: string) => void;
  }) => (
    <div data-testid="signup-completion-form" data-invitation-id={invitationId}>
      <button onClick={() => onComplete('acme-corp')}>Complete account</button>
    </div>
  ),
}));

// ── Helpers ──────────────────────────────────────────────────────────────

const defaultPreview = {
  invitation_id: 'test-invitation-id',
  status: 'pending' as const,
  workspace_name: 'Acme Corp',
  workspace_slug: 'acme-corp',
  invited_email_masked: 'j***@example.com',
  expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
};

/**
 * Set up auth mocks to simulate no existing session (US1 path).
 * Returns an unsubscribe spy.
 */
function setupNoSession() {
  const unsubscribe = vi.fn();
  mockOnAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe } } });
  mockGetSession.mockResolvedValue({ data: { session: null }, error: null });
  return unsubscribe;
}

/**
 * Set up auth mocks to simulate an existing SIGNED_IN session (US2 path).
 */
function setupExistingSession() {
  const unsubscribe = vi.fn();
  mockOnAuthStateChange.mockReturnValue({ data: { subscription: { unsubscribe } } });
  mockGetSession.mockResolvedValue({
    data: { session: { user: { email: 'j@example.com' } } },
    error: null,
  });
  return unsubscribe;
}

// ── Import page after mocks ───────────────────────────────────────────────
// Must be dynamic due to hoisting requirements
const { default: InvitePage } = await import('../page');

// ── Tests ────────────────────────────────────────────────────────────────

describe('InvitePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading spinner on mount', () => {
    setupNoSession();
    mockPreviewInvitation.mockReturnValue(new Promise(() => {})); // never resolves

    render(<InvitePage />);
    expect(screen.getByText(/loading invitation/i)).toBeInTheDocument();
  });

  it('renders workspace name after preview loads', async () => {
    setupNoSession();
    mockPreviewInvitation.mockResolvedValue(defaultPreview);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/join acme corp/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /send magic link/i })).toBeInTheDocument();
  });

  it('renders masked email hint', async () => {
    setupNoSession();
    mockPreviewInvitation.mockResolvedValue(defaultPreview);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/j\*\*\*@example\.com/)).toBeInTheDocument();
    });
  });

  it('renders expired error for 410 with expired status', async () => {
    setupNoSession();
    const err = Object.assign(new Error('Gone'), { status: 410, data: { details: { invitation_status: 'expired' } } });
    mockPreviewInvitation.mockRejectedValue(err);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/invitation expired/i)).toBeInTheDocument();
    });
  });

  it('renders revoked error for 410 with revoked status', async () => {
    setupNoSession();
    const err = Object.assign(new Error('Gone'), { status: 410, data: { details: { invitation_status: 'revoked' } } });
    mockPreviewInvitation.mockRejectedValue(err);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/invitation revoked/i)).toBeInTheDocument();
    });
  });

  it('renders accepted error for 410 with accepted status', async () => {
    setupNoSession();
    const err = Object.assign(new Error('Gone'), { status: 410, data: { details: { invitation_status: 'accepted' } } });
    mockPreviewInvitation.mockRejectedValue(err);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByText(/already used/i)).toBeInTheDocument();
    });
  });

  it('submits email and shows success state', async () => {
    const user = userEvent.setup();
    setupNoSession();
    mockPreviewInvitation.mockResolvedValue(defaultPreview);
    mockRequestMagicLink.mockResolvedValue({ message: 'Check your email', expires_in_minutes: 60 });

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send magic link/i })).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/email address/i), 'j@example.com');
    await user.click(screen.getByRole('button', { name: /send magic link/i }));

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });

    expect(mockRequestMagicLink).toHaveBeenCalledWith('test-invitation-id', 'j@example.com');
  });

  it('shows rate limit error when requestMagicLink returns 429', async () => {
    const user = userEvent.setup();
    setupNoSession();
    mockPreviewInvitation.mockResolvedValue(defaultPreview);
    const err = Object.assign(new Error('Too many requests'), { status: 429 });
    mockRequestMagicLink.mockRejectedValue(err);

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /send magic link/i })).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText(/email address/i), 'j@example.com');
    await user.click(screen.getByRole('button', { name: /send magic link/i }));

    await waitFor(() => {
      expect(screen.getByText(/too many magic link requests/i)).toBeInTheDocument();
    });
  });

  it('existing session detected: skips email form and shows SignupCompletionForm directly', async () => {
    setupExistingSession();

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByTestId('signup-completion-form')).toBeInTheDocument();
    });

    expect(screen.getByText(/complete your account/i)).toBeInTheDocument();
  });

  it('does NOT call router.push immediately when existing session is detected', async () => {
    const mockPush = vi.fn();
    vi.doMock('next/navigation', () => ({
      useRouter: () => ({ push: mockPush }),
      useSearchParams: () => ({
        get: (key: string) => (key === 'invitation_id' ? 'test-invitation-id' : null),
      }),
    }));

    setupExistingSession();

    render(<InvitePage />);

    await waitFor(() => {
      expect(screen.getByTestId('signup-completion-form')).toBeInTheDocument();
    });
    // router.push should NOT have been called automatically — user must complete the form
    expect(mockPush).not.toHaveBeenCalled();
  });
});
