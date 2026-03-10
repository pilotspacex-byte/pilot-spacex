'use client';

/**
 * useCommandPaletteShortcut - Registers global Cmd+K / Ctrl+K listener.
 *
 * Call once at the workspace shell level. Dispatches to uiStore.toggleCommandPalette().
 * Prevents default browser behaviour (Ctrl+K focuses address bar in some browsers,
 * Cmd+K is TipTap's link shortcut — this runs at the window level so the editor
 * listener on the element should fire first; the global listener handles the global case).
 *
 * IMPORTANT: uses useUIStore() (RootStore instance) — NOT the standalone uiStore singleton
 * from UIStore.ts — so it targets the same observable that CommandPalette observes.
 */

import { useEffect } from 'react';
import { useUIStore } from '@/stores';

export function useCommandPaletteShortcut(): void {
  // Must use the RootStore-scoped UIStore, not the standalone singleton.
  // store is the RootStore UIStore — a stable singleton that never changes reference.
  const store = useUIStore();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // navigator.platform is deprecated; prefer userAgentData with platform fallback.
      const platform =
        (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData
          ?.platform ?? navigator.platform;
      const isMac = /mac/i.test(platform);
      const modifier = isMac ? event.metaKey : event.ctrlKey;

      if (modifier && event.key === 'k') {
        // Only intercept when not inside a TipTap editor element.
        // TipTap handles Cmd+K for links inside the editor; we only want
        // the global shortcut when focus is outside the editor.
        const activeTag = document.activeElement?.tagName.toLowerCase();
        const isEditorFocused =
          document.activeElement?.closest('.ProseMirror') !== null ||
          activeTag === 'input' ||
          activeTag === 'textarea';

        if (isEditorFocused) return;

        event.preventDefault();
        store.toggleCommandPalette();
      }
    }

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
    // store is a stable RootStore singleton — safe to include in deps without causing re-registration.
  }, [store]);
}
