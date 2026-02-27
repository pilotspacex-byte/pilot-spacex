/**
 * AuthCoreAuthProvider — RS256-signed JWT auth via AuthCore server.
 *
 * Used when NEXT_PUBLIC_AUTH_PROVIDER=authcore.
 * Base URL is discovered at startup via GET /api/v1/auth/config.
 */

import type { AuthProvider, AuthTokens, AuthProviderUser, LoginResult } from './AuthProvider';

const AUTHCORE_TOKENS_KEY = 'authcore:tokens';

interface AuthCoreLoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number; // seconds
  token_type: string;
  user: {
    id: string;
    email: string;
    name?: string;
    avatar_url?: string;
  };
}

interface AuthCoreRefreshResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

function parseJwtExpiry(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!)) as { exp?: number };
    return payload.exp ?? 0;
  } catch {
    return 0;
  }
}

export class AuthCoreAuthProvider implements AuthProvider {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    if (!baseUrl) {
      throw new Error('AuthCoreAuthProvider requires a non-empty baseUrl');
    }
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async login(email: string, password: string): Promise<LoginResult> {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`AuthCore login failed (${res.status}): ${body}`);
    }

    const data: AuthCoreLoginResponse = await res.json();

    const expiresAt =
      parseJwtExpiry(data.access_token) || Math.floor(Date.now() / 1000) + data.expires_in;
    const tokens: AuthTokens = {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      expiresAt,
    };

    if (typeof window !== 'undefined') {
      localStorage.setItem(AUTHCORE_TOKENS_KEY, JSON.stringify(tokens));
    }

    const user: AuthProviderUser = {
      id: data.user.id,
      email: data.user.email,
      name: data.user.name ?? '',
      avatarUrl: data.user.avatar_url ?? null,
    };

    return { tokens, user };
  }

  async logout(): Promise<void> {
    const token = await this.getToken();

    // Best-effort server-side logout; ignore errors
    if (token) {
      try {
        await fetch(`${this.baseUrl}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Network failure during logout — still clear local state
      }
    }

    if (typeof window !== 'undefined') {
      localStorage.removeItem(AUTHCORE_TOKENS_KEY);
    }
  }

  async refresh(refreshToken: string): Promise<AuthTokens> {
    const res = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`AuthCore refresh failed (${res.status}): ${body}`);
    }

    const data: AuthCoreRefreshResponse = await res.json();

    const expiresAt =
      parseJwtExpiry(data.access_token) || Math.floor(Date.now() / 1000) + data.expires_in;
    const tokens: AuthTokens = {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      expiresAt,
    };

    if (typeof window !== 'undefined') {
      localStorage.setItem(AUTHCORE_TOKENS_KEY, JSON.stringify(tokens));
    }

    return tokens;
  }

  async getToken(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    const raw = localStorage.getItem(AUTHCORE_TOKENS_KEY);
    if (!raw) return null;

    try {
      const tokens: AuthTokens = JSON.parse(raw);
      const nowSeconds = Math.floor(Date.now() / 1000);

      // Token is still valid (with 30s buffer)
      if (tokens.expiresAt > nowSeconds + 30) {
        return tokens.accessToken;
      }

      // Attempt silent refresh
      const refreshed = await this.refresh(tokens.refreshToken);
      return refreshed.accessToken;
    } catch {
      localStorage.removeItem(AUTHCORE_TOKENS_KEY);
      return null;
    }
  }
}
