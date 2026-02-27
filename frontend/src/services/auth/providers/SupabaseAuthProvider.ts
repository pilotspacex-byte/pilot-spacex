/**
 * SupabaseAuthProvider — delegates all auth operations to the Supabase SDK.
 *
 * This is the default provider (NEXT_PUBLIC_AUTH_PROVIDER=supabase or unset).
 * Zero behavioral change vs the pre-abstraction code paths.
 */

import { supabase } from '@/lib/supabase';
import type { AuthProvider, AuthTokens, LoginResult } from './AuthProvider';

export class SupabaseAuthProvider implements AuthProvider {
  async login(email: string, password: string): Promise<LoginResult> {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      throw new Error(error.message);
    }

    if (!data.session || !data.user) {
      throw new Error('Login succeeded but no session returned');
    }

    return {
      tokens: {
        accessToken: data.session.access_token,
        refreshToken: data.session.refresh_token,
        expiresAt: data.session.expires_at ?? 0,
      },
      user: {
        id: data.user.id,
        email: data.user.email ?? '',
        name:
          (data.user.user_metadata?.name as string | undefined) ||
          (data.user.user_metadata?.full_name as string | undefined) ||
          '',
        avatarUrl: (data.user.user_metadata?.avatar_url as string | undefined) ?? null,
      },
    };
  }

  async logout(): Promise<void> {
    const { error } = await supabase.auth.signOut();
    if (error) {
      throw new Error(error.message);
    }
  }

  async refresh(refreshToken: string): Promise<AuthTokens> {
    const { data, error } = await supabase.auth.refreshSession({ refresh_token: refreshToken });

    if (error) {
      throw new Error(error.message);
    }

    if (!data.session) {
      throw new Error('Refresh succeeded but no session returned');
    }

    return {
      accessToken: data.session.access_token,
      refreshToken: data.session.refresh_token,
      expiresAt: data.session.expires_at ?? 0,
    };
  }

  async getToken(): Promise<string | null> {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }
}
