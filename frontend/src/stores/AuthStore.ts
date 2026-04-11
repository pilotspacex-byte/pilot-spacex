'use client';

import { makeAutoObservable, runInAction, computed } from 'mobx';
import { supabase, type User, type Session } from '@/lib/supabase';
import type { AuthChangeEvent } from '@supabase/supabase-js';
import { getAuthProvider, getAuthProviderSync } from '@/services/auth/providers';
import type { AuthProvider as IAuthProvider } from '@/services/auth/providers';

export interface AiSettings {
  model_sonnet?: string;
  model_haiku?: string;
  model_opus?: string;
  base_url?: string;
}

export interface WorkspaceMembership {
  workspaceId: string;
  role: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatarUrl: string | null;
  bio?: string;
  aiSettings?: AiSettings | null;
  workspaceMemberships?: WorkspaceMembership[];
}

const MAX_REFRESH_FAILURES = 3;
const SUPABASE_STORAGE_KEY_PREFIX = 'sb-';

export const isAuthCoreMode =
  (process.env.NEXT_PUBLIC_AUTH_PROVIDER ?? 'supabase').toLowerCase().trim() === 'authcore';

function clearSupabaseAuthKeys(): void {
  if (typeof window === 'undefined') return;
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(SUPABASE_STORAGE_KEY_PREFIX)) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key));
}

export class AuthStore {
  user: AuthUser | null = null;
  session: Session | null = null;
  isLoading = true;
  error: string | null = null;

  private authSubscription: { unsubscribe: () => void } | null = null;
  private refreshFailureCount = 0;
  private provider: IAuthProvider | null = null;

  constructor() {
    makeAutoObservable(this, {
      isAuthenticated: computed,
      userDisplayName: computed,
      userInitials: computed,
    });

    this.initializeAuth();
  }

  get isAuthenticated(): boolean {
    if (isAuthCoreMode) return this.user !== null;
    return this.user !== null && this.session !== null;
  }

  get userDisplayName(): string {
    if (!this.user) return '';
    return this.user.name || this.user.email.split('@')[0] || '';
  }

  get userInitials(): string {
    const name = this.userDisplayName;
    if (!name) return '??';

    const parts = name
      .trim()
      .split(/\s+/)
      .filter((p) => p.length > 0);
    if (parts.length >= 2) {
      const firstChar = parts[0]?.[0] ?? '';
      const lastChar = parts[parts.length - 1]?.[0] ?? '';
      return (firstChar + lastChar).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  private handleRefreshFailure(): void {
    this.refreshFailureCount++;
    if (this.refreshFailureCount >= MAX_REFRESH_FAILURES) {
      this.refreshFailureCount = 0;
      if (!isAuthCoreMode) clearSupabaseAuthKeys();
      this.user = null;
      this.session = null;
      this.error = null;
      if (typeof window !== 'undefined') {
        window.location.href = '/login?error=session_expired';
      }
    }
  }

  private resetRefreshFailures(): void {
    this.refreshFailureCount = 0;
  }

  private async initializeAuth(): Promise<void> {
    try {
      if (isAuthCoreMode) {
        await this.initializeAuthCore();
      } else {
        await this.initializeSupabase();
      }
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to initialize auth';
        this.isLoading = false;
      });
    }
  }

  private async initializeAuthCore(): Promise<void> {
    const provider = await getAuthProvider();
    this.provider = provider;

    const restored = await provider.restoreSession();

    runInAction(() => {
      if (restored) {
        this.user = restored.user;
      }
      this.isLoading = false;
    });
  }

  private async initializeSupabase(): Promise<void> {
    const { data, error } = await supabase.auth.getSession();

    if (error) {
      const isDefinitiveTokenFailure =
        error.message.toLowerCase().includes('refresh token not found') ||
        error.message.toLowerCase().includes('invalid refresh token');

      runInAction(() => {
        if (isDefinitiveTokenFailure) {
          clearSupabaseAuthKeys();
          this.user = null;
          this.session = null;
        } else {
          this.handleRefreshFailure();
          this.error = error.message;
        }
        this.isLoading = false;
      });

      this.subscribeToAuthChanges();

      if (isDefinitiveTokenFailure && typeof window !== 'undefined') {
        window.location.href = '/login?error=session_expired';
      }
      return;
    }

    runInAction(() => {
      if (data.session) {
        this.session = data.session;
        this.user = this.mapSupabaseUser(data.session.user);
      }
      this.isLoading = false;
    });

    this.subscribeToAuthChanges();
  }

  private subscribeToAuthChanges(): void {
    if (isAuthCoreMode) return;

    const { data } = supabase.auth.onAuthStateChange(
      (event: AuthChangeEvent, session: Session | null) => {
        runInAction(() => {
          this.session = session;
          this.user = session ? this.mapSupabaseUser(session.user) : null;

          if (event === 'SIGNED_OUT') {
            this.error = null;
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }

          if (event === 'TOKEN_REFRESHED' && !session) {
            this.handleRefreshFailure();
            return;
          }

          if (event === 'TOKEN_REFRESHED' && session) {
            this.resetRefreshFailures();
          }
        });
      }
    );

    this.authSubscription = data.subscription;
  }

  private mapSupabaseUser(supabaseUser: User): AuthUser {
    // Preserve aiSettings across auth state changes — Supabase user metadata
    // doesn't contain AI settings, so we carry forward the existing value.
    const preservedAiSettings = this.user?.aiSettings ?? null;
    return {
      id: supabaseUser.id,
      email: supabaseUser.email || '',
      name: supabaseUser.user_metadata?.name || supabaseUser.user_metadata?.full_name || '',
      avatarUrl: supabaseUser.user_metadata?.avatar_url || null,
      bio: supabaseUser.user_metadata?.['bio'] as string | undefined,
      aiSettings: preservedAiSettings,
    };
  }

  private getProvider(): IAuthProvider {
    return this.provider ?? getAuthProviderSync();
  }

  async login(email: string, password: string): Promise<boolean> {
    this.isLoading = true;
    this.error = null;

    try {
      const provider = this.getProvider();
      const result = await provider.login(email, password);

      runInAction(() => {
        this.user = result.user;
        if (!isAuthCoreMode) {
          // Supabase SDK sets session internally; sync it from getSession()
          supabase.auth.getSession().then(({ data }) => {
            runInAction(() => {
              this.session = data.session;
            });
          });
        }
        this.isLoading = false;
        this.resetRefreshFailures();
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Login failed';
        this.isLoading = false;
      });
      return false;
    }
  }

  async loginWithOAuth(provider: 'github' | 'google'): Promise<void> {
    if (isAuthCoreMode) {
      throw new Error('OAuth login is not available with AuthCore');
    }

    this.isLoading = true;
    this.error = null;

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.isLoading = false;
        });
      }
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'OAuth login failed';
        this.isLoading = false;
      });
    }
  }

  /**
   * @returns 'success' on immediate login, 'verification_required' when email
   *          confirmation is needed, or false on failure.
   */
  async signup(email: string, password: string, name?: string): Promise<boolean | 'verification_required'> {
    this.isLoading = true;
    this.error = null;

    try {
      const provider = this.getProvider();
      const result = await provider.signup(email, password, name);

      if (result.verificationRequired) {
        runInAction(() => {
          this.isLoading = false;
        });
        return 'verification_required';
      }

      runInAction(() => {
        this.user = result.user;
        if (!isAuthCoreMode && result.tokens) {
          supabase.auth.getSession().then(({ data }) => {
            runInAction(() => {
              this.session = data.session;
            });
          });
        }
        this.isLoading = false;
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Signup failed';
        this.isLoading = false;
      });
      return false;
    }
  }

  async logout(): Promise<void> {
    this.isLoading = true;
    this.error = null;

    try {
      await this.getProvider().logout();

      runInAction(() => {
        this.user = null;
        this.session = null;
        this.isLoading = false;
      });

      if (isAuthCoreMode && typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Logout failed';
        this.isLoading = false;
      });
    }
  }

  async refreshSession(): Promise<boolean> {
    this.error = null;

    try {
      if (isAuthCoreMode) {
        const token = await this.getProvider().getToken();
        if (!token) {
          runInAction(() => {
            this.handleRefreshFailure();
          });
          return false;
        }
        runInAction(() => {
          this.resetRefreshFailures();
        });
        return true;
      }

      const { data, error } = await supabase.auth.refreshSession();

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.handleRefreshFailure();
        });
        return false;
      }

      runInAction(() => {
        this.session = data.session;
        this.user = data.user ? this.mapSupabaseUser(data.user) : null;
        this.resetRefreshFailures();
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Session refresh failed';
        this.handleRefreshFailure();
      });
      return false;
    }
  }

  async updateProfile(data: { name?: string; avatarUrl?: string; bio?: string }): Promise<boolean> {
    if (isAuthCoreMode) {
      // AuthCore profile updates handled via separate profile API
      return false;
    }

    this.isLoading = true;
    this.error = null;

    try {
      const { data: userData, error } = await supabase.auth.updateUser({
        data: {
          name: data.name,
          full_name: data.name,
          avatar_url: data.avatarUrl,
          bio: data.bio,
        },
      });

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.isLoading = false;
        });
        return false;
      }

      runInAction(() => {
        if (userData.user) {
          this.user = this.mapSupabaseUser(userData.user);
        }
        this.isLoading = false;
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Profile update failed';
        this.isLoading = false;
      });
      return false;
    }
  }

  async fetchBackendProfile(): Promise<void> {
    try {
      const { apiClient } = await import('@/services/api/client');
      const profile = await apiClient.get<{
        aiSettings?: AiSettings | null;
        workspace_memberships?: Array<{ workspace_id: string; role: string }>;
      }>('/auth/me');

      runInAction(() => {
        if (this.user) {
          this.user.aiSettings = profile.aiSettings ?? null;
          this.user.workspaceMemberships = (profile.workspace_memberships ?? []).map((m) => ({
            workspaceId: m.workspace_id,
            role: m.role,
          }));
        }
      });
    } catch {
      // Non-critical — AI settings and memberships will just show empty
    }
  }

  async updateAiSettings(aiSettings: AiSettings | null): Promise<boolean> {
    this.error = null;

    try {
      const { apiClient } = await import('@/services/api/client');
      const profile = await apiClient.patch<{ aiSettings?: AiSettings | null }>('/auth/me', {
        aiSettings,
      });

      runInAction(() => {
        if (this.user) {
          this.user.aiSettings = profile.aiSettings ?? null;
        }
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update AI settings';
      });
      return false;
    }
  }

  async uploadAvatar(file: File): Promise<string | null> {
    if (!this.user) return null;

    // Derive extension from MIME type to avoid trusting user-controlled filename
    const MIME_TO_EXT: Record<string, string> = {
      'image/jpeg': 'jpg',
      'image/png': 'png',
      'image/gif': 'gif',
      'image/webp': 'webp',
    };
    const ext = MIME_TO_EXT[file.type] ?? 'jpg';
    const filePath = `${this.user.id}/avatar.${ext}`;

    const { error: uploadError } = await supabase.storage
      .from('avatars')
      .upload(filePath, file, { upsert: true });

    if (uploadError) {
      runInAction(() => {
        this.error = uploadError.message;
      });
      return null;
    }

    const { data } = supabase.storage.from('avatars').getPublicUrl(filePath);
    // Append cache-busting param so browsers refetch after re-upload to the same path
    const avatarUrl = `${data.publicUrl}?t=${Date.now()}`;

    const success = await this.updateProfile({ avatarUrl });
    return success ? avatarUrl : null;
  }

  async resetPassword(email: string): Promise<boolean> {
    if (isAuthCoreMode) {
      // AuthCore password reset handled via separate flow
      return false;
    }

    this.isLoading = true;
    this.error = null;

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      });

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.isLoading = false;
        });
        return false;
      }

      runInAction(() => {
        this.isLoading = false;
      });

      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Password reset failed';
        this.isLoading = false;
      });
      return false;
    }
  }

  clearError(): void {
    this.error = null;
  }

  dispose(): void {
    if (this.authSubscription) {
      this.authSubscription.unsubscribe();
      this.authSubscription = null;
    }
  }
}

export const authStore = new AuthStore();
