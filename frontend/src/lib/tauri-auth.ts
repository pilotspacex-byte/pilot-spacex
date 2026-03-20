/**
 * Tauri Auth Bridge — syncs Supabase JWT tokens to Tauri Store and OS keychain.
 *
 * Called once on app mount (Tauri mode only). Subscribes to
 * supabase.auth.onAuthStateChange and writes access_token + refresh_token
 * to:
 *   1. OS keychain (macOS Keychain / Windows Credential Manager / Linux Secret
 *      Service) via Rust IPC — secure, OS-protected credential storage
 *   2. Tauri Store (pilot-auth.json) — sync channel so the WebView Supabase
 *      JS client can read tokens without going through IPC
 *
 * On first launch after upgrading from Plan 31-01 (Store-only), calls
 * migrateTokensToKeychain() to copy any existing Store tokens to keychain.
 *
 * This module MUST only be imported dynamically behind an isTauri() guard.
 */

import { supabase } from '@/lib/supabase';

let initialized = false;

export async function syncTokenToTauriStore(): Promise<void> {
  if (initialized) return;
  initialized = true;

  // Lazy imports — keeps these Tauri-specific modules out of SSG/web bundles
  const { setAuthToken, migrateTokensToKeychain } = await import('@/lib/tauri');
  const { load } = await import('@tauri-apps/plugin-store');

  // Load (or create) the persistent auth store. We call store.save() explicitly
  // on each write, so the default autoSave debounce is left at its default.
  const store = await load('pilot-auth.json', { defaults: {} });

  // One-time migration: copy any Store-only tokens into OS keychain.
  // No-op if keychain already has tokens or no tokens exist.
  await migrateTokensToKeychain().catch(() => {});

  // Sync current session immediately (app restart case — session persisted in Store)
  const { data } = await supabase.auth.getSession();
  if (data.session?.access_token) {
    await store.set('access_token', data.session.access_token);
    await store.set('refresh_token', data.session.refresh_token ?? null);
    await store.save();
    // Also write to OS keychain via Rust IPC (secure storage)
    await setAuthToken(data.session.access_token, data.session.refresh_token ?? null).catch(
      () => {}
    );
  }

  // Subscribe to future auth state changes (sign-in, token refresh, sign-out)
  supabase.auth.onAuthStateChange(async (_event, session) => {
    if (session?.access_token) {
      await store.set('access_token', session.access_token);
      await store.set('refresh_token', session.refresh_token ?? null);
      // Write to OS keychain (secure source of truth for Rust-side access)
      await setAuthToken(session.access_token, session.refresh_token ?? null).catch(() => {});
    } else {
      await store.delete('access_token');
      await store.delete('refresh_token');
      // Clear OS keychain on sign-out
      await setAuthToken(null, null).catch(() => {});
    }
    await store.save();
  });
}
