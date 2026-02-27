/**
 * Auth provider factory.
 *
 * Provider selection order:
 * 1. NEXT_PUBLIC_AUTH_PROVIDER env var ("supabase" | "authcore")
 * 2. Falls back to "supabase" if unset or unrecognised
 *
 * For "authcore", the base URL is fetched once from GET /api/v1/auth/config
 * and then cached for the lifetime of the module.
 */

import type { AuthProvider } from './AuthProvider';
import { SupabaseAuthProvider } from './SupabaseAuthProvider';
import { AuthCoreAuthProvider } from './AuthCoreAuthProvider';

const AUTH_PROVIDER_ENV = (process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? 'supabase')
  .toLowerCase()
  .trim();

interface AuthConfig {
  provider: string;
  authcore_url: string | null;
}

let _providerInstance: AuthProvider | null = null;

async function fetchAuthConfig(): Promise<AuthConfig> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
  const res = await fetch(`${apiBase}/auth/config`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Failed to fetch auth config: ${res.status}`);
  }
  return res.json() as Promise<AuthConfig>;
}

/**
 * Initialise and return the singleton AuthProvider.
 *
 * Safe to call multiple times — returns the cached instance after the first call.
 * Must be awaited before the first API call or auth check.
 */
export async function getAuthProvider(): Promise<AuthProvider> {
  if (_providerInstance) return _providerInstance;

  const envProvider = AUTH_PROVIDER_ENV;

  if (envProvider === 'authcore') {
    const config = await fetchAuthConfig();
    const baseUrl = config.authcore_url;
    if (!baseUrl) {
      throw new Error('AUTH_PROVIDER=authcore but /api/v1/auth/config returned no authcore_url');
    }
    _providerInstance = new AuthCoreAuthProvider(baseUrl);
  } else {
    _providerInstance = new SupabaseAuthProvider();
  }

  return _providerInstance;
}

/**
 * Synchronous access to the already-initialised provider.
 * Throws if called before getAuthProvider() has resolved.
 * Use in request interceptors where async init was done at app startup.
 */
export function getAuthProviderSync(): AuthProvider {
  if (!_providerInstance) {
    // Fallback to Supabase for SSR / before init completes
    _providerInstance = new SupabaseAuthProvider();
  }
  return _providerInstance;
}

/** Reset for testing purposes only. */
export function _resetAuthProvider(): void {
  _providerInstance = null;
}

export type { AuthProvider };
export { SupabaseAuthProvider, AuthCoreAuthProvider };
export type { AuthTokens, AuthProviderUser, LoginResult } from './AuthProvider';
