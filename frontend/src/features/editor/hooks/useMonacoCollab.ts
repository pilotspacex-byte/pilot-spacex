'use client';

/**
 * useMonacoCollab — Yjs collaboration binding for Monaco via y-monaco.
 *
 * Reuses the existing SupabaseYjsProvider transport layer.
 * Creates a Y.Doc, Y.Text ('monaco'), MonacoBinding, and awareness state.
 * Remote cursors are rendered by y-monaco's built-in awareness integration.
 *
 * IMPORTANT: Do NOT create y-indexeddb persistence here -- handled by existing infrastructure.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import * as Y from 'yjs';
import { MonacoBinding } from 'y-monaco';
import { Awareness } from 'y-protocols/awareness';
import type * as monacoNs from 'monaco-editor';
import { SupabaseYjsProvider } from '@/features/notes/collab/SupabaseYjsProvider';
import type { SupabaseClient } from '@supabase/supabase-js';

/** Cursor color palette for remote users */
const CURSOR_COLORS = ['#29a386', '#6366f1', '#d97706', '#0891b2', '#7c3aed', '#d9534f'];

export interface CollabUser {
  id: string;
  name: string;
}

export interface UseMonacoCollabOptions {
  editor: monacoNs.editor.IStandaloneCodeEditor | null;
  model: monacoNs.editor.ITextModel | null;
  noteId: string | null;
  enabled: boolean;
  supabase: SupabaseClient;
  user: CollabUser;
}

export interface UseMonacoCollabReturn {
  isConnected: boolean;
  connectedUsers: number;
}

/**
 * Hook that binds a Monaco editor to a Yjs document for real-time collaboration.
 *
 * @param options - Configuration including editor, model, noteId, supabase client, and user info
 * @returns Connection status and connected user count
 */
export function useMonacoCollab({
  editor,
  model,
  noteId,
  enabled,
  supabase,
  user,
}: UseMonacoCollabOptions): UseMonacoCollabReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [connectedUsers, setConnectedUsers] = useState(0);

  const ydocRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<SupabaseYjsProvider | null>(null);
  const bindingRef = useRef<MonacoBinding | null>(null);
  const awarenessRef = useRef<Awareness | null>(null);

  const updateConnectedUsers = useCallback(() => {
    const awareness = awarenessRef.current;
    if (!awareness) {
      setConnectedUsers(0);
      return;
    }
    const states = awareness.getStates();
    setConnectedUsers(states.size);
  }, []);

  useEffect(() => {
    if (!enabled || !editor || !model || !noteId) return;

    // Create Yjs document and text type
    const ydoc = new Y.Doc();
    const ytext = ydoc.getText('monaco');
    const awareness = new Awareness(ydoc);

    ydocRef.current = ydoc;
    awarenessRef.current = awareness;

    // Set local awareness with random cursor color
    const colorIndex = Math.floor(Math.random() * CURSOR_COLORS.length);
    awareness.setLocalStateField('user', {
      name: user.name,
      color: CURSOR_COLORS[colorIndex],
    });

    // Create MonacoBinding (y-monaco)
    const binding = new MonacoBinding(ytext, model, new Set([editor]), awareness);
    bindingRef.current = binding;

    // Create SupabaseYjsProvider with 'yjs:monaco:' channel prefix
    // to avoid shared type conflicts with legacy TipTap sessions (which use 'yjs:note:')
    const provider = new SupabaseYjsProvider({
      supabase,
      noteId,
      ydoc,
      awareness,
      channelPrefix: 'yjs:monaco:',
      user: {
        id: user.id,
        name: user.name,
        color: CURSOR_COLORS[colorIndex]!,
      },
      onStatusChange: (status) => {
        setIsConnected(status === 'connected');
      },
    });
    providerRef.current = provider;

    // Track awareness changes for connected user count
    const awarenessHandler = () => {
      updateConnectedUsers();
    };
    awareness.on('change', awarenessHandler);

    // Connect the provider
    void provider.connect().then(() => {
      updateConnectedUsers();
    });

    return () => {
      awareness.off('change', awarenessHandler);

      binding.destroy();
      bindingRef.current = null;

      provider.destroy();
      providerRef.current = null;

      ydoc.destroy();
      ydocRef.current = null;

      awarenessRef.current = null;
      setIsConnected(false);
      setConnectedUsers(0);
    };
  }, [enabled, editor, model, noteId, supabase, user.id, user.name, updateConnectedUsers]);

  return { isConnected, connectedUsers };
}
