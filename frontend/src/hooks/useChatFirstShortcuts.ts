'use client';

import { useEffect } from 'react';
import { useUIStore, useArtifactPanelStore } from '@/stores';

/**
 * Keyboard shortcuts for the chat-first layout.
 *
 * - Cmd+B: Toggle sidebar
 * - Cmd+Shift+C: Toggle between chat-first and chat-artifact modes
 * - Cmd+/: Focus chat input
 * - Cmd+Shift+N: New chat (clears conversation, returns to chat-first)
 */
export function useChatFirstShortcuts(): void {
  const uiStore = useUIStore();
  const artifactPanel = useArtifactPanelStore();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const isMod = e.metaKey || e.ctrlKey;
      if (!isMod) return;

      // Cmd+B: Toggle sidebar
      if (e.key === 'b' && !e.shiftKey) {
        e.preventDefault();
        uiStore.toggleSidebar();
        return;
      }

      // Cmd+Shift+C: Toggle layout mode (chat-first ↔ chat-artifact)
      if (e.key === 'C' && e.shiftKey) {
        e.preventDefault();
        if (uiStore.layoutMode === 'chat-first') {
          if (artifactPanel.hasOpenTabs) {
            uiStore.setLayoutMode('chat-artifact');
          }
        } else {
          uiStore.setLayoutMode('chat-first');
        }
        return;
      }

      // Cmd+/: Focus chat input
      if (e.key === '/') {
        e.preventDefault();
        const chatInput = document.querySelector<HTMLElement>('[data-testid="chat-input"], [aria-label="Chat input"]');
        chatInput?.focus();
        return;
      }

      // Cmd+Shift+N: New chat
      if (e.key === 'N' && e.shiftKey) {
        e.preventDefault();
        uiStore.setLayoutMode('chat-first');
        artifactPanel.closeAllUnpinned();
        return;
      }

      // Cmd+[: Go back in artifact history
      if (e.key === '[' && !e.shiftKey) {
        e.preventDefault();
        artifactPanel.goBack();
        return;
      }

      // Cmd+]: Go forward in artifact history
      if (e.key === ']' && !e.shiftKey) {
        e.preventDefault();
        artifactPanel.goForward();
        return;
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [uiStore, artifactPanel]);
}
