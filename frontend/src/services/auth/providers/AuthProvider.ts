/**
 * AuthProvider interface — abstracts Supabase and AuthCore auth paths.
 *
 * Implementations:
 * - SupabaseAuthProvider (default, NEXT_PUBLIC_AUTH_PROVIDER=supabase)
 * - AuthCoreAuthProvider (NEXT_PUBLIC_AUTH_PROVIDER=authcore)
 */

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // Unix timestamp (seconds)
}

export interface AuthProviderUser {
  id: string;
  email: string;
  name: string;
  avatarUrl: string | null;
}

export interface LoginResult {
  tokens: AuthTokens;
  user: AuthProviderUser;
}

export interface AuthProvider {
  /**
   * Sign in with email + password. Returns tokens and user on success.
   * Throws on failure.
   */
  login(email: string, password: string): Promise<LoginResult>;

  /**
   * Sign out the current user and clear all local session state.
   */
  logout(): Promise<void>;

  /**
   * Exchange the current refresh token for a new access token.
   * Returns updated tokens on success. Throws on failure.
   */
  refresh(refreshToken: string): Promise<AuthTokens>;

  /**
   * Return the current access token, or null if not authenticated.
   */
  getToken(): Promise<string | null>;
}
