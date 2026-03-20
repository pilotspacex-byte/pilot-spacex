/**
 * Tauri Auth Bridge — syncs Supabase JWT tokens to Tauri Store and OS keychain,
 * and intercepts OAuth deep link callbacks for PKCE flow completion.
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
 * OAuth PKCE flow (Plan 31-03):
 *   - loginWithOAuth() opens external browser with redirectTo: pilotspace://auth/callback
 *   - OS routes pilotspace:// URLs to the Tauri app
 *   - initDeepLinkListener() intercepts the URL, extracts the auth code, and
 *     calls supabase.auth.exchangeCodeForSession() to complete the PKCE handshake
 *   - onAuthStateChange fires, syncTokenToTauriStore() persists the new session
 *
 * This module MUST only be imported dynamically behind an isTauri() guard.
 */

import { supabase } from '@/lib/supabase';

let initialized = false;
let deepLinkInitialized = false;

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

  // Initialize deep link listener for OAuth callbacks (PKCE flow completion)
  await initDeepLinkListener().catch(console.error);
}

/**
 * Register a listener for pilotspace://auth/callback deep links.
 *
 * When the OS routes a pilotspace:// URL to the app (after OAuth redirect),
 * this handler extracts the PKCE authorization code and exchanges it for a
 * Supabase session. The resulting session triggers onAuthStateChange, which
 * causes syncTokenToTauriStore to persist tokens to Store and keychain.
 *
 * Idempotent — safe to call multiple times (no-op after first call).
 */
export async function initDeepLinkListener(): Promise<void> {
  if (deepLinkInitialized) return;
  deepLinkInitialized = true;

  const { onOpenUrl } = await import('@tauri-apps/plugin-deep-link');

  await onOpenUrl(async (urls: string[]) => {
    for (const rawUrl of urls) {
      try {
        const url = new URL(rawUrl);

        // Only handle auth callback deep links: pilotspace://auth/callback
        if (url.host !== 'auth' || url.pathname !== '/callback') continue;

        const code = url.searchParams.get('code');
        if (!code) {
          console.error('[tauri-auth] Deep link missing code parameter:', rawUrl);
          continue;
        }

        // Exchange the authorization code for a session (PKCE flow completion)
        const { data, error } = await supabase.auth.exchangeCodeForSession(code);

        if (error) {
          console.error('[tauri-auth] Failed to exchange code for session:', error.message);
          // Navigate to login with error so the user sees a helpful message
          if (typeof window !== 'undefined') {
            window.location.href = `/login?error=${encodeURIComponent(error.message)}`;
          }
          continue;
        }

        if (data.session) {
          // Session is now active. The onAuthStateChange listener from
          // syncTokenToTauriStore() will automatically sync tokens to Store + keychain.
          // Navigate to the app home.
          if (typeof window !== 'undefined') {
            window.location.href = '/';
          }
        }
      } catch (err) {
        console.error('[tauri-auth] Deep link processing error:', err);
      }
    }
  });
}
