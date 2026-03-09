/**
 * Tests for SamlCallbackPage.
 *
 * Covers: token_hash exchange via verifyOtp, success redirect, error redirect,
 * missing token_hash guard.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';

// --- Mocks ---

const mockPush = vi.fn();
const mockGet = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: mockGet }),
}));

const mockVerifyOtp = vi.fn();

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      verifyOtp: mockVerifyOtp,
    },
  },
}));

const mockApiPost = vi.fn();

vi.mock('@/services/api', () => ({
  apiClient: {
    post: mockApiPost,
  },
}));

// Mock lucide-react to avoid SVG rendering issues in jsdom
vi.mock('lucide-react', () => ({
  Compass: () => <svg data-testid="compass-icon" />,
}));

// --- Tests ---

describe('SamlCallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiPost.mockResolvedValue({});
  });

  it('calls verifyOtp with token_hash from URL search params', async () => {
    mockGet.mockImplementation((key: string) => (key === 'token_hash' ? 'abc123' : null));

    const mockSession = {
      user: { app_metadata: {}, user_metadata: {} },
    };
    mockVerifyOtp.mockResolvedValue({ data: { session: mockSession }, error: null });

    const { default: SamlCallbackPage } = await import('./page');
    render(<SamlCallbackPage />);

    await waitFor(() => {
      expect(mockVerifyOtp).toHaveBeenCalledWith({
        token_hash: 'abc123',
        type: 'magiclink',
      });
    });
  });

  it('redirects to / on successful verifyOtp', async () => {
    mockGet.mockImplementation((key: string) => (key === 'token_hash' ? 'valid-hash' : null));

    const mockSession = {
      user: { app_metadata: { provider: 'saml' }, user_metadata: {} },
    };
    mockVerifyOtp.mockResolvedValue({ data: { session: mockSession }, error: null });

    const { default: SamlCallbackPage } = await import('./page');
    render(<SamlCallbackPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  it('redirects to /login?error=saml_failed when verifyOtp returns error', async () => {
    mockGet.mockImplementation((key: string) => (key === 'token_hash' ? 'expired-hash' : null));

    mockVerifyOtp.mockResolvedValue({
      data: { session: null },
      error: { message: 'Token has expired' },
    });

    const { default: SamlCallbackPage } = await import('./page');
    render(<SamlCallbackPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?error=saml_failed');
    });
  });

  it('redirects to /login?error=saml_failed immediately when token_hash is missing', async () => {
    mockGet.mockReturnValue(null);

    const { default: SamlCallbackPage } = await import('./page');
    render(<SamlCallbackPage />);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/login?error=saml_failed');
    });

    // verifyOtp should NOT be called when token_hash is absent
    expect(mockVerifyOtp).not.toHaveBeenCalled();
  });
});
