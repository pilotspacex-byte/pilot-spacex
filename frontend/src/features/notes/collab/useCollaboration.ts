/**
 * useCollaboration — wires Yjs CRDT collaboration into MobX + TanStack Query.
 *
 * T-124: Collaboration hook integrating auth identity, MobX UI state, and
 *        TanStack Query cache invalidation on CRDT convergence.
 *
 * Responsibilities:
 *   1. Read current user identity from MobX AuthStore (name, color, id).
 *   2. Delegate provider lifecycle to useYjsProvider.
 *   3. On CRDT state sync (status → 'connected' after offline), invalidate
 *      TanStack Query note cache so the UI reflects merged content.
 *   4. Expose a minimal surface: { ydoc, awareness, status, peers,
 *      softLimitExceeded, error, connectionStatus } for the editor layer.
 *
 * Color assignment: deterministic from user id (hash → hue) so the same user
 * always appears in the same color across sessions.
 *
 * @module features/notes/collab/useCollaboration
 */
import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { SupabaseClient } from '@supabase/supabase-js';
import { useYjsProvider } from './useYjsProvider';
import type { YjsProviderState } from './useYjsProvider';
import type { ProviderStatus } from './SupabaseYjsProvider';

export interface CollaborationUser {
  id: string;
  name: string;
}

export interface UseCollaborationOptions {
  supabase: SupabaseClient;
  workspaceId: string;
  noteId: string;
  /** Current authenticated user — pass from AuthStore */
  user: CollaborationUser;
  /** TanStack Query key for the note (used for cache invalidation) */
  noteQueryKey?: readonly unknown[];
}

export interface UseCollaborationResult extends YjsProviderState {
  /** Human-readable connection status label for UI */
  connectionStatus: 'online' | 'offline' | 'syncing' | 'error';
}

/**
 * Deterministic user color from id: hash to HSL hue, fixed saturation/lightness.
 * Same user id → same color every time.
 */
function deriveUserColor(userId: string): string {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash * 31 + userId.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return `hsl(${hue}, 65%, 45%)`;
}

/**
 * Map ProviderStatus → human-readable connectionStatus for ConnectionStatus UI.
 */
function toConnectionStatus(
  status: ProviderStatus,
  hasError: boolean
): UseCollaborationResult['connectionStatus'] {
  if (hasError) return 'error';
  switch (status) {
    case 'connected':
      return 'online';
    case 'connecting':
      return 'syncing';
    case 'disconnected':
    default:
      return 'offline';
  }
}

/**
 * Wires Yjs CRDT provider with MobX AuthStore identity and TanStack Query
 * cache invalidation. Returns a clean collaboration API for the editor layer.
 */
export function useCollaboration(options: UseCollaborationOptions): UseCollaborationResult {
  const { supabase, workspaceId, noteId, user, noteQueryKey } = options;
  const queryClient = useQueryClient();
  const prevStatusRef = useRef<ProviderStatus>('disconnected');

  const collaborationUser = {
    id: user.id,
    name: user.name || 'Anonymous',
    color: deriveUserColor(user.id),
  };

  const onStatusChange = useCallback(
    (status: ProviderStatus) => {
      // Invalidate note cache when reconnecting after offline: CRDT may have
      // merged remote changes that the cached note doesn't reflect.
      if (status === 'connected' && prevStatusRef.current === 'disconnected' && noteQueryKey) {
        void queryClient.invalidateQueries({ queryKey: noteQueryKey });
      }
      prevStatusRef.current = status;
    },
    [queryClient, noteQueryKey]
  );

  const providerState = useYjsProvider({
    supabase,
    workspaceId,
    noteId,
    user: collaborationUser,
    onStatusChange,
  });

  // Keep prevStatusRef in sync with actual status
  useEffect(() => {
    prevStatusRef.current = providerState.status;
  }, [providerState.status]);

  const connectionStatus = toConnectionStatus(providerState.status, providerState.error !== null);

  return {
    ...providerState,
    connectionStatus,
  };
}
