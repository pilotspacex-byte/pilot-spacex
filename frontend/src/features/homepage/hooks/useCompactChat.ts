'use client';

/**
 * useCompactChat (H040) — Manages PilotSpaceStore session lifecycle for homepage context.
 * Session persists across expand/collapse cycles within browser session.
 */

import { useEffect, useCallback } from 'react';
import { useAIStore } from '@/stores/RootStore';

export interface UseCompactChatReturn {
  messages: ReturnType<typeof useAIStore>['pilotSpace']['messages'];
  isStreaming: boolean;
  streamContent: string;
  error: string | null;
  sendMessage: (text: string) => void;
  abort: () => void;
}

export function useCompactChat(workspaceId: string): UseCompactChatReturn {
  const aiStore = useAIStore();
  const store = aiStore.pilotSpace;

  // Set workspace context on mount
  useEffect(() => {
    if (workspaceId) {
      store.setWorkspaceId(workspaceId);
    }
    return () => {
      store.abort();
    };
  }, [workspaceId, store]);

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      store.sendMessage(text);
    },
    [store]
  );

  const abort = useCallback(() => {
    store.abort();
  }, [store]);

  return {
    messages: store.messages,
    isStreaming: store.isStreaming,
    streamContent: store.streamContent,
    error: store.error ?? null,
    sendMessage,
    abort,
  };
}
