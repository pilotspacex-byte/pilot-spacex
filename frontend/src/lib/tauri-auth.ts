/**
 * Tauri Auth Bridge — syncs Supabase JWT tokens to Tauri Store.
 *
 * Called once on app mount (Tauri mode only). Subscribes to
 * supabase.auth.onAuthStateChange and writes access_token + refresh_token
 * to the Tauri Store file (pilot-auth.json), which is readable by
 * Rust commands via tauri-plugin-store.
 *
 * This module MUST only be imported dynamically behind an isTauri() guard.
 */

import { supabase } from '@/lib/supabase';

let initialized = false;

export async function syncTokenToTauriStore(): Promise<void> {
  if (initialized) return;
  initialized = true;

  const { load } = await import('@tauri-apps/plugin-store');
  // Load (or create) the persistent auth store. We call store.save() explicitly
  // on each write, so the default autoSave debounce is left at its default.
  const store = await load('pilot-auth.json', { defaults: {} });

  // Sync current session immediately (app restart case)
  const { data } = await supabase.auth.getSession();
  if (data.session?.access_token) {
    await store.set('access_token', data.session.access_token);
    await store.set('refresh_token', data.session.refresh_token ?? null);
    await store.save();
  }

  // Subscribe to future auth state changes
  supabase.auth.onAuthStateChange(async (_event, session) => {
    if (session?.access_token) {
      await store.set('access_token', session.access_token);
      await store.set('refresh_token', session.refresh_token ?? null);
    } else {
      await store.delete('access_token');
      await store.delete('refresh_token');
    }
    await store.save();
  });
}
