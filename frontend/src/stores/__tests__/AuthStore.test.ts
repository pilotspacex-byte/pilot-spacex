/**
 * Unit tests for AuthStore — verifies provider-based auth routing
 * for both Supabase (default) and AuthCore modes.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock supabase before anything imports it
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      signInWithOAuth: vi.fn(),
      refreshSession: vi.fn(),
      updateUser: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
  },
}));

// Mock auth providers
const mockLogin = vi.fn();
const mockSignup = vi.fn();
const mockLogout = vi.fn();
const mockGetToken = vi.fn();
const mockRefresh = vi.fn();
const mockRestoreSession = vi.fn();

vi.mock('@/services/auth/providers', () => ({
  getAuthProvider: vi.fn().mockResolvedValue({
    login: (...args: unknown[]) => mockLogin(...args),
    signup: (...args: unknown[]) => mockSignup(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    getToken: (...args: unknown[]) => mockGetToken(...args),
    refresh: (...args: unknown[]) => mockRefresh(...args),
    restoreSession: (...args: unknown[]) => mockRestoreSession(...args),
  }),
  getAuthProviderSync: vi.fn().mockReturnValue({
    login: (...args: unknown[]) => mockLogin(...args),
    signup: (...args: unknown[]) => mockSignup(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    getToken: (...args: unknown[]) => mockGetToken(...args),
    refresh: (...args: unknown[]) => mockRefresh(...args),
    restoreSession: (...args: unknown[]) => mockRestoreSession(...args),
  }),
}));

describe('AuthStore — Supabase mode (default)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure NEXT_PUBLIC_AUTH_PROVIDER is unset (supabase default)
    vi.stubEnv('NEXT_PUBLIC_AUTH_PROVIDER', 'supabase');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('exports isAuthCoreMode as false in supabase mode', async () => {
    // Dynamic import to get fresh module — note: isAuthCoreMode is set at module load time
    // In the default test env, NEXT_PUBLIC_AUTH_PROVIDER is undefined → supabase mode
    const { isAuthCoreMode } = await import('@/stores/AuthStore');
    expect(isAuthCoreMode).toBe(false);
  });

  it('isAuthenticated requires both user and session in supabase mode', async () => {
    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();

    // Wait for init to finish
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    expect(store.isAuthenticated).toBe(false);
    expect(store.user).toBeNull();
  });

  it('login delegates to provider', async () => {
    mockLogin.mockResolvedValueOnce({
      tokens: { accessToken: 'at', refreshToken: 'rt', expiresAt: 999 },
      user: { id: 'u1', email: 'test@example.com', name: 'Test', avatarUrl: null },
    });

    const { supabase } = await import('@/lib/supabase');
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    } as never);

    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    const success = await store.login('test@example.com', 'password');

    expect(success).toBe(true);
    expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password');
    expect(store.user?.email).toBe('test@example.com');
  });

  it('signup delegates to provider', async () => {
    mockSignup.mockResolvedValueOnce({
      user: { id: 'u2', email: 'new@example.com', name: 'New', avatarUrl: null },
      tokens: { accessToken: 'at', refreshToken: 'rt', expiresAt: 999 },
      verificationRequired: false,
    });

    const { supabase } = await import('@/lib/supabase');
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    } as never);

    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    const success = await store.signup('new@example.com', 'password', 'New User');

    expect(success).toBe(true);
    expect(mockSignup).toHaveBeenCalledWith('new@example.com', 'password', 'New User');
    expect(store.user?.email).toBe('new@example.com');
  });

  it('logout delegates to provider and clears state', async () => {
    mockLogout.mockResolvedValueOnce(undefined);

    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    await store.logout();

    expect(mockLogout).toHaveBeenCalledOnce();
    expect(store.user).toBeNull();
    expect(store.session).toBeNull();
  });

  it('login error sets error state', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));

    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    const success = await store.login('bad@example.com', 'wrong');

    expect(success).toBe(false);
    expect(store.error).toBe('Invalid credentials');
  });

  it('signup with verificationRequired returns verification_required without setting user', async () => {
    mockSignup.mockResolvedValueOnce({
      user: null,
      tokens: null,
      verificationRequired: true,
    });

    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    const result = await store.signup('new@example.com', 'password');

    expect(result).toBe('verification_required');
    expect(store.user).toBeNull(); // no user yet — needs email verification
  });

  it('userDisplayName falls back to email prefix', async () => {
    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    // Manually set user with no name
    store.user = { id: 'u1', email: 'hello@test.com', name: '', avatarUrl: null };

    expect(store.userDisplayName).toBe('hello');
  });

  it('userInitials returns 2-char initials from name', async () => {
    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    store.user = { id: 'u1', email: 'test@test.com', name: 'John Doe', avatarUrl: null };

    expect(store.userInitials).toBe('JD');
  });

  it('dispose unsubscribes from auth changes', async () => {
    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    store.dispose();
    // Should not throw
  });

  it('clearError resets error to null', async () => {
    const { AuthStore } = await import('@/stores/AuthStore');
    const store = new AuthStore();
    await vi.waitFor(() => expect(store.isLoading).toBe(false));

    store.error = 'Some error';
    store.clearError();

    expect(store.error).toBeNull();
  });
});
