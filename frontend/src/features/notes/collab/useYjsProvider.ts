/**
 * useYjsProvider — Manages the full Yjs CRDT provider lifecycle for a note.
 *
 * T-118: Full Yjs provider (gate-selected transport, auto-reconnect, error boundary).
 * T-119: Offline editing support (IndexedDB via y-indexeddb, CRDT merge on reconnect).
 *
 * Responsibilities:
 *   1. Create and own Y.Doc + Awareness for the note session.
 *   2. Load persisted state from backend (noteYjsStateApi.get) on mount;
 *      fall back to IndexedDB if backend returns 404 (T-119).
 *   3. Connect SupabaseYjsProvider for real-time collaboration.
 *   4. Persist state to backend on Y.Doc updates (debounced 2s, same as auto-save).
 *   5. Sync IndexedDB offline store in background (y-indexeddb).
 *   6. Expose `status`, `awareness`, `ydoc`, `peers` for the editor.
 *   7. Auto-reconnect: on provider error, retry with exponential backoff (max 3 attempts).
 *
 * Transport selection:
 *   - Default: Supabase Realtime broadcast (SupabaseYjsProvider)
 *   - Future: y-websocket fallback (T-103)
 *
 * Soft limits (T-124):
 *   - SOFT_LIMIT_HUMANS = 50: warn-only above this threshold.
 *   - AI_SLOTS = 5: reserved awareness slots for AI presence.
 *
 * @module features/notes/collab/useYjsProvider
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import * as Y from 'yjs';
import { Awareness } from 'y-protocols/awareness';
import { IndexeddbPersistence } from 'y-indexeddb';
import type { SupabaseClient } from '@supabase/supabase-js';
import { SupabaseYjsProvider, type ProviderStatus } from './SupabaseYjsProvider';
import { noteYjsStateApi } from '@/services/api/note-yjs-state';

export const SOFT_LIMIT_HUMANS = 50;
export const AI_SLOTS = 5;

export interface PeerState {
  id: string;
  name: string;
  color: string;
  isAI: boolean;
}

export interface YjsProviderState {
  ydoc: Y.Doc;
  awareness: Awareness;
  status: ProviderStatus;
  peers: PeerState[];
  softLimitExceeded: boolean;
  error: Error | null;
}

export interface UseYjsProviderOptions {
  supabase: SupabaseClient;
  workspaceId: string;
  noteId: string;
  user: { id: string; name: string; color: string };
  /** Called when provider status changes (for UI indicators) */
  onStatusChange?: (status: ProviderStatus) => void;
}

const PERSIST_DEBOUNCE_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_BASE_MS = 1000;

/**
 * Manages the Yjs provider lifecycle for a collaborative note session.
 *
 * Returns stable `ydoc` and `awareness` references — callers should not
 * recreate the editor on status changes.
 */
export function useYjsProvider(options: UseYjsProviderOptions): YjsProviderState {
  const { supabase, workspaceId, noteId, user, onStatusChange } = options;

  // Stable refs — created once, never replaced
  const ydocRef = useRef<Y.Doc | null>(null);
  const awarenessRef = useRef<Awareness | null>(null);
  const providerRef = useRef<SupabaseYjsProvider | null>(null);
  const idbRef = useRef<IndexeddbPersistence | null>(null);
  const persistTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const destroyedRef = useRef(false);

  // Initialise Y.Doc + Awareness once
  if (!ydocRef.current) {
    ydocRef.current = new Y.Doc();
    awarenessRef.current = new Awareness(ydocRef.current);
  }

  const [status, setStatus] = useState<ProviderStatus>('disconnected');
  const [peers, setPeers] = useState<PeerState[]>([]);
  const [error, setError] = useState<Error | null>(null);

  // ── Peer tracking from awareness ──────────────────────────────────────
  const refreshPeers = useCallback(() => {
    const awareness = awarenessRef.current;
    if (!awareness) return;

    const result: PeerState[] = [];
    awareness
      .getStates()
      .forEach((state: Map<string, unknown> | Record<string, unknown>, clientId: number) => {
        if (clientId === awareness.clientID) return; // Exclude self
        const rawState = state as Record<string, unknown>;
        const u = rawState['user'] as
          | { id?: string; name?: string; color?: string; isAI?: boolean }
          | undefined;
        if (u?.id) {
          result.push({
            id: u.id,
            name: u.name ?? 'Unknown',
            color: u.color ?? '#888',
            isAI: u.isAI === true,
          });
        }
      });
    setPeers(result);
  }, []);

  // ── Debounced backend persistence ─────────────────────────────────────
  const schedulePersist = useCallback(() => {
    if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    persistTimerRef.current = setTimeout(async () => {
      const ydoc = ydocRef.current;
      if (!ydoc || destroyedRef.current) return;
      try {
        const state = Y.encodeStateAsUpdate(ydoc);
        await noteYjsStateApi.put(workspaceId, noteId, state);
      } catch {
        // Non-fatal: offline persistence (IndexedDB) still works
      }
    }, PERSIST_DEBOUNCE_MS);
  }, [workspaceId, noteId]);

  // ── Connect provider with retry ────────────────────────────────────────
  const connectProvider = useCallback(async () => {
    const ydoc = ydocRef.current;
    const awareness = awarenessRef.current;
    if (!ydoc || !awareness || destroyedRef.current) return;

    // Destroy previous provider if exists
    if (providerRef.current) {
      providerRef.current.destroy();
      providerRef.current = null;
    }

    const provider = new SupabaseYjsProvider({
      supabase,
      noteId,
      ydoc,
      awareness,
      user,
      onStatusChange: (s) => {
        setStatus(s);
        onStatusChange?.(s);
        if (s === 'connected') {
          reconnectAttemptsRef.current = 0;
          setError(null);
        }
      },
      onError: async (err) => {
        if (destroyedRef.current) return;
        const attempt = reconnectAttemptsRef.current;
        if (attempt >= MAX_RECONNECT_ATTEMPTS) {
          setError(err);
          return;
        }
        reconnectAttemptsRef.current = attempt + 1;
        const delay = RECONNECT_BASE_MS * Math.pow(2, attempt);
        await new Promise((r) => setTimeout(r, delay));
        if (!destroyedRef.current) connectProvider();
      },
    });

    providerRef.current = provider;

    try {
      await provider.connect();
    } catch (err) {
      // onError will handle retry
      if (err instanceof Error) setError(err);
    }
  }, [supabase, noteId, user, onStatusChange]); // workspaceId not needed here

  // ── Main lifecycle effect ──────────────────────────────────────────────
  useEffect(() => {
    destroyedRef.current = false;
    const ydoc = ydocRef.current!;
    const awareness = awarenessRef.current!;

    // IndexedDB offline persistence (T-119)
    const idbKey = `yjs:note:${noteId}`;
    const idb = new IndexeddbPersistence(idbKey, ydoc);
    idbRef.current = idb;

    // Track peers on awareness change
    awareness.on('change', refreshPeers);

    // Persist on every Y.Doc update
    const onUpdate = () => schedulePersist();
    ydoc.on('update', onUpdate);

    // Async init: load backend state, then connect
    (async () => {
      // Wait for IndexedDB to finish loading offline state
      await idb.whenSynced;

      if (destroyedRef.current) return;

      try {
        // Try loading persisted state from backend
        const serverState = await noteYjsStateApi.get(workspaceId, noteId);
        if (serverState && serverState.length > 0 && !destroyedRef.current) {
          // Merge server state into existing Y.Doc (CRDT convergence)
          Y.applyUpdate(ydoc, serverState);
        }
      } catch {
        // Backend unavailable — IndexedDB state is already loaded
      }

      if (!destroyedRef.current) {
        await connectProvider();
      }
    })();

    return () => {
      destroyedRef.current = true;

      if (persistTimerRef.current) {
        clearTimeout(persistTimerRef.current);
        persistTimerRef.current = null;
      }

      ydoc.off('update', onUpdate);
      awareness.off('change', refreshPeers);

      providerRef.current?.destroy();
      providerRef.current = null;

      idbRef.current?.destroy();
      idbRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteId, workspaceId]); // Re-run only when note/workspace changes

  const humanPeers = peers.filter((p) => !p.isAI);
  const softLimitExceeded = humanPeers.length >= SOFT_LIMIT_HUMANS;

  return {
    ydoc: ydocRef.current!,
    awareness: awarenessRef.current!,
    status,
    peers,
    softLimitExceeded,
    error,
  };
}
