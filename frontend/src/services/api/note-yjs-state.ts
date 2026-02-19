/**
 * Raw binary API client for Yjs CRDT state persistence.
 *
 * T-117: GET/PUT /workspaces/{id}/notes/{id}/yjs-state
 *
 * Uses fetch directly (not axios) because axios cannot handle
 * application/octet-stream request/response bodies cleanly.
 * JWT is obtained from the current Supabase session.
 */
import { supabase } from '@/lib/supabase';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export const noteYjsStateApi = {
  /**
   * Fetch persisted Yjs state for a note.
   * Returns null if no state has been persisted yet (client should start from empty Y.Doc).
   */
  async get(workspaceId: string, noteId: string): Promise<Uint8Array | null> {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData.session?.access_token;
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/notes/${noteId}/yjs-state`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`YjsState GET failed: ${res.status}`);
    return new Uint8Array(await res.arrayBuffer());
  },

  /**
   * Persist the full Yjs document state for a note (upsert).
   * Call with the output of Y.encodeStateAsUpdate(ydoc).
   */
  async put(workspaceId: string, noteId: string, state: Uint8Array): Promise<void> {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData.session?.access_token;
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/notes/${noteId}/yjs-state`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/octet-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: new Blob([state.slice()], { type: 'application/octet-stream' }),
    });
    if (!res.ok) throw new Error(`YjsState PUT failed: ${res.status}`);
  },
};
