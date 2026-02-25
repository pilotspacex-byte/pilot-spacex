/**
 * Raw binary API client for Yjs CRDT state persistence.
 *
 * T-117: GET/PUT /workspaces/{id}/notes/{id}/yjs-state
 *
 * Uses fetch directly (not axios) because axios cannot handle
 * application/octet-stream request/response bodies cleanly.
 * JWT is obtained from the current Supabase session.
 * Errors are wrapped in ApiError (RFC 7807) for consistent handling.
 */
import { supabase } from '@/lib/supabase';
import { ApiError } from './client';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

async function _getAuthHeaders(): Promise<Record<string, string>> {
  const { data: sessionData } = await supabase.auth.getSession();
  const token = sessionData.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function _throwApiError(res: Response, context: string): Promise<never> {
  let detail: string | undefined;
  try {
    const text = await res.text();
    const json = JSON.parse(text) as { detail?: string; title?: string };
    detail = json.detail ?? json.title;
  } catch {
    // Non-JSON body — ignore
  }
  throw new ApiError({
    status: res.status,
    title: `${context} failed`,
    detail: detail ?? `HTTP ${res.status}`,
  });
}

export const noteYjsStateApi = {
  /**
   * Fetch persisted Yjs state for a note.
   * Returns null if no state has been persisted yet (client should start from empty Y.Doc).
   */
  async get(workspaceId: string, noteId: string): Promise<Uint8Array | null> {
    const authHeaders = await _getAuthHeaders();
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/notes/${noteId}/yjs-state`, {
      headers: authHeaders,
    });
    if (res.status === 404) return null;
    if (!res.ok) await _throwApiError(res, 'YjsState GET');
    return new Uint8Array(await res.arrayBuffer());
  },

  /**
   * Persist the full Yjs document state for a note (upsert).
   * Call with the output of Y.encodeStateAsUpdate(ydoc).
   */
  async put(workspaceId: string, noteId: string, state: Uint8Array): Promise<void> {
    const authHeaders = await _getAuthHeaders();
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/notes/${noteId}/yjs-state`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/octet-stream',
        ...authHeaders,
      },
      body: new Blob([state.slice()], { type: 'application/octet-stream' }),
    });
    if (!res.ok) await _throwApiError(res, 'YjsState PUT');
  },
};
