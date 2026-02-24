'use client';

import { makeAutoObservable, runInAction, computed } from 'mobx';
import { supabase, type User, type Session } from '@/lib/supabase';
import type { AuthChangeEvent } from '@supabase/supabase-js';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatarUrl: string | null;
}

const MAX_REFRESH_FAILURES = 3;
const SUPABASE_STORAGE_KEY_PREFIX = 'sb-';

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

  constructor() {
    makeAutoObservable(this, {
      isAuthenticated: computed,
      userDisplayName: computed,
      userInitials: computed,
    });

    this.initializeAuth();
  }

  get isAuthenticated(): boolean {
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
      clearSupabaseAuthKeys();
      this.user = null;
      this.session = null;
      this.error = null;
      if (typeof window !== 'undefined') {
        window.location.href = '/login?error=Session+expired';
      }
    }
  }

  private resetRefreshFailures(): void {
    this.refreshFailureCount = 0;
  }

  private async initializeAuth(): Promise<void> {
    try {
      const { data, error } = await supabase.auth.getSession();

      if (error) {
        // Supabase's _initialize already exhausts internal retries before surfacing this error.
        // An invalid/missing refresh token is a definitive failure — redirect immediately.
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

        // Always subscribe so future auth events (e.g. SIGNED_OUT) are tracked.
        this.subscribeToAuthChanges();

        if (isDefinitiveTokenFailure && typeof window !== 'undefined') {
          window.location.href = '/login?error=Session+expired';
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
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to initialize auth';
        this.isLoading = false;
      });
    }
  }

  private subscribeToAuthChanges(): void {
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

          // Handle expired/invalid refresh token (FR-004)
          if (event === 'TOKEN_REFRESHED' && !session) {
            this.handleRefreshFailure();
            return;
          }

          // Successful token refresh — reset failure counter
          if (event === 'TOKEN_REFRESHED' && session) {
            this.resetRefreshFailures();
          }
        });
      }
    );

    this.authSubscription = data.subscription;
  }

  private mapSupabaseUser(supabaseUser: User): AuthUser {
    return {
      id: supabaseUser.id,
      email: supabaseUser.email || '',
      name: supabaseUser.user_metadata?.name || supabaseUser.user_metadata?.full_name || '',
      avatarUrl: supabaseUser.user_metadata?.avatar_url || null,
    };
  }

  async login(email: string, password: string): Promise<boolean> {
    this.isLoading = true;
    this.error = null;

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.isLoading = false;
        });
        return false;
      }

      runInAction(() => {
        this.session = data.session;
        this.user = data.user ? this.mapSupabaseUser(data.user) : null;
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

  async signup(email: string, password: string, name: string): Promise<boolean> {
    this.isLoading = true;
    this.error = null;

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            name,
            full_name: name,
          },
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
        this.session = data.session;
        this.user = data.user ? this.mapSupabaseUser(data.user) : null;
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
      const { error } = await supabase.auth.signOut();

      if (error) {
        runInAction(() => {
          this.error = error.message;
          this.isLoading = false;
        });
        return;
      }

      runInAction(() => {
        this.user = null;
        this.session = null;
        this.isLoading = false;
      });
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

  async updateProfile(data: { name?: string; avatarUrl?: string }): Promise<boolean> {
    this.isLoading = true;
    this.error = null;

    try {
      const { data: userData, error } = await supabase.auth.updateUser({
        data: {
          name: data.name,
          full_name: data.name,
          avatar_url: data.avatarUrl,
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

  async resetPassword(email: string): Promise<boolean> {
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
