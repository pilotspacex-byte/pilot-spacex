'use client';

/**
 * useCommandPaletteShortcut - Registers global Cmd+K / Ctrl+K listener.
 *
 * Call once at the workspace shell level. Dispatches to uiStore.toggleCommandPalette().
 * Prevents default browser behaviour (Ctrl+K focuses address bar in some browsers,
 * Cmd+K is TipTap's link shortcut — this runs at the window level so the editor
 * listener on the element should fire first; the global listener handles the global case).
 */

import { useEffect } from 'react';
import { uiStore } from '@/stores/UIStore';

export function useCommandPaletteShortcut(): void {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const isMac = navigator.platform.toUpperCase().includes('MAC');
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
        uiStore.toggleCommandPalette();
      }
    }

    window.addEventListener('keydown', handleKeyDown, { capture: true });
    return () => window.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, []);
}
