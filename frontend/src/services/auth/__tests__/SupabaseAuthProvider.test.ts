/**
 * Unit tests for SupabaseAuthProvider.
 *
 * Supabase SDK is mocked — these tests verify the provider correctly
 * maps SDK responses to the AuthProvider interface contract.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SupabaseAuthProvider } from '../providers/SupabaseAuthProvider';

// Mock the supabase lib module
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      refreshSession: vi.fn(),
      getSession: vi.fn(),
    },
  },
}));

import { supabase } from '@/lib/supabase';

const mockSignIn = vi.mocked(supabase.auth.signInWithPassword);
const mockSignOut = vi.mocked(supabase.auth.signOut);
const mockRefreshSession = vi.mocked(supabase.auth.refreshSession);
const mockGetSession = vi.mocked(supabase.auth.getSession);

const MOCK_SESSION = {
  access_token: 'access-token-abc',
  refresh_token: 'refresh-token-xyz',
  expires_at: 9999999999,
  token_type: 'bearer',
  user: {
    id: 'user-id-123',
    email: 'test@example.com',
    user_metadata: { name: 'Test User', avatar_url: 'https://example.com/avatar.png' },
  },
};

const MOCK_USER = MOCK_SESSION.user;

describe('SupabaseAuthProvider.login', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns LoginResult on success', async () => {
    mockSignIn.mockResolvedValueOnce({
      data: { session: MOCK_SESSION, user: MOCK_USER },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    const result = await provider.login('test@example.com', 'password');

    expect(result.tokens.accessToken).toBe('access-token-abc');
    expect(result.tokens.refreshToken).toBe('refresh-token-xyz');
    expect(result.tokens.expiresAt).toBe(9999999999);
    expect(result.user.id).toBe('user-id-123');
    expect(result.user.email).toBe('test@example.com');
    expect(result.user.name).toBe('Test User');
    expect(result.user.avatarUrl).toBe('https://example.com/avatar.png');
  });

  it('throws on Supabase error', async () => {
    mockSignIn.mockResolvedValueOnce({
      data: { session: null, user: null },
      error: { message: 'Invalid login credentials' },
    } as never);

    const provider = new SupabaseAuthProvider();
    await expect(provider.login('bad@example.com', 'wrong')).rejects.toThrow(
      'Invalid login credentials'
    );
  });

  it('throws when no session returned despite no error', async () => {
    mockSignIn.mockResolvedValueOnce({
      data: { session: null, user: null },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    await expect(provider.login('test@example.com', 'password')).rejects.toThrow(
      'no session returned'
    );
  });

  it('uses full_name when name is absent', async () => {
    const userWithFullName = {
      ...MOCK_USER,
      user_metadata: { full_name: 'Full Name User' },
    };
    mockSignIn.mockResolvedValueOnce({
      data: { session: MOCK_SESSION, user: userWithFullName },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    const result = await provider.login('test@example.com', 'password');
    expect(result.user.name).toBe('Full Name User');
  });
});

describe('SupabaseAuthProvider.logout', () => {
  beforeEach(() => vi.clearAllMocks());

  it('calls supabase.auth.signOut', async () => {
    mockSignOut.mockResolvedValueOnce({ error: null } as never);

    const provider = new SupabaseAuthProvider();
    await provider.logout();

    expect(mockSignOut).toHaveBeenCalledOnce();
  });

  it('throws on signOut error', async () => {
    mockSignOut.mockResolvedValueOnce({ error: { message: 'Sign out failed' } } as never);

    const provider = new SupabaseAuthProvider();
    await expect(provider.logout()).rejects.toThrow('Sign out failed');
  });
});

describe('SupabaseAuthProvider.refresh', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns new AuthTokens on success', async () => {
    const newSession = {
      ...MOCK_SESSION,
      access_token: 'new-access-token',
      refresh_token: 'new-refresh-token',
      expires_at: 9999999998,
    };
    mockRefreshSession.mockResolvedValueOnce({
      data: { session: newSession, user: MOCK_USER },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    const tokens = await provider.refresh('old-refresh-token');

    expect(tokens.accessToken).toBe('new-access-token');
    expect(tokens.refreshToken).toBe('new-refresh-token');
    expect(tokens.expiresAt).toBe(9999999998);
  });

  it('throws on refresh error', async () => {
    mockRefreshSession.mockResolvedValueOnce({
      data: { session: null, user: null },
      error: { message: 'Token expired' },
    } as never);

    const provider = new SupabaseAuthProvider();
    await expect(provider.refresh('expired-token')).rejects.toThrow('Token expired');
  });
});

describe('SupabaseAuthProvider.getToken', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns access token when session exists', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: MOCK_SESSION },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    const token = await provider.getToken();

    expect(token).toBe('access-token-abc');
  });

  it('returns null when no session', async () => {
    mockGetSession.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    } as never);

    const provider = new SupabaseAuthProvider();
    const token = await provider.getToken();

    expect(token).toBeNull();
  });
});
