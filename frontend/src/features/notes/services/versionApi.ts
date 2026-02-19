/**
 * Version API client — typed wrappers for note versioning endpoints.
 *
 * All calls go to: /api/v1/workspaces/{workspaceId}/notes/{noteId}/versions/...
 * Feature 017: Note Versioning — Sprint 1 (T-216)
 */

export type VersionTrigger = 'manual' | 'auto' | 'ai_before' | 'ai_after';

export interface NoteVersionResponse {
  id: string;
  noteId: string;
  workspaceId: string;
  trigger: VersionTrigger;
  label: string | null;
  pinned: boolean;
  digest: string | null;
  digestCachedAt: string | null;
  createdBy: string | null;
  versionNumber: number;
  createdAt: string;
  /** Populated only when trigger === 'ai_after' (GAP-02) */
  aiBeforeVersionId: string | null;
}

export interface NoteVersionListResponse {
  versions: NoteVersionResponse[];
  total: number;
  noteId: string;
}

export interface BlockDiffResponse {
  blockId: string;
  diffType: 'added' | 'removed' | 'modified' | 'unchanged';
  oldContent: Record<string, unknown> | null;
  newContent: Record<string, unknown> | null;
}

export interface DiffResponse {
  version1Id: string;
  version2Id: string;
  blocks: BlockDiffResponse[];
  addedCount: number;
  removedCount: number;
  modifiedCount: number;
  hasChanges: boolean;
}

export interface DigestResponse {
  versionId: string;
  digest: string;
  fromCache: boolean;
}

export interface RestoreResponse {
  newVersion: NoteVersionResponse;
  restoredFromVersionId: string;
}

export interface UndoAiResponse {
  newVersion: NoteVersionResponse;
  restoredFromVersionId: string;
}

const base = (workspaceId: string, noteId: string) =>
  `/api/v1/workspaces/${workspaceId}/notes/${noteId}/versions`;

async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const message =
      typeof err.detail === 'string' ? err.detail : (err.detail?.message ?? res.statusText);
    const e = Object.assign(new Error(message), { status: res.status, body: err });
    throw e;
  }
  return res.json() as Promise<T>;
}

export const versionApi = {
  list(
    workspaceId: string,
    noteId: string,
    params: { limit?: number; offset?: number } = {}
  ): Promise<NoteVersionListResponse> {
    const qs = new URLSearchParams();
    if (params.limit != null) qs.set('limit', String(params.limit));
    if (params.offset != null) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return apiFetch<NoteVersionListResponse>(`${base(workspaceId, noteId)}${q ? `?${q}` : ''}`);
  },

  get(workspaceId: string, noteId: string, versionId: string): Promise<NoteVersionResponse> {
    return apiFetch<NoteVersionResponse>(`${base(workspaceId, noteId)}/${versionId}`);
  },

  create(workspaceId: string, noteId: string, label?: string): Promise<NoteVersionResponse> {
    return apiFetch<NoteVersionResponse>(base(workspaceId, noteId), {
      method: 'POST',
      body: JSON.stringify({ label: label ?? null }),
    });
  },

  diff(workspaceId: string, noteId: string, v1Id: string, v2Id: string): Promise<DiffResponse> {
    return apiFetch<DiffResponse>(`${base(workspaceId, noteId)}/${v1Id}/diff/${v2Id}`);
  },

  restore(
    workspaceId: string,
    noteId: string,
    versionId: string,
    versionNumber: number
  ): Promise<RestoreResponse> {
    return apiFetch<RestoreResponse>(`${base(workspaceId, noteId)}/${versionId}/restore`, {
      method: 'POST',
      body: JSON.stringify({ versionNumber }),
    });
  },

  digest(workspaceId: string, noteId: string, versionId: string): Promise<DigestResponse> {
    return apiFetch<DigestResponse>(`${base(workspaceId, noteId)}/${versionId}/digest`);
  },

  pin(
    workspaceId: string,
    noteId: string,
    versionId: string,
    pinned: boolean
  ): Promise<NoteVersionResponse> {
    return apiFetch<NoteVersionResponse>(`${base(workspaceId, noteId)}/${versionId}/pin`, {
      method: 'PUT',
      body: JSON.stringify({ pinned }),
    });
  },

  undoAI(workspaceId: string, noteId: string, versionNumber: number): Promise<UndoAiResponse> {
    return apiFetch<UndoAiResponse>(`${base(workspaceId, noteId)}/undo-ai`, {
      method: 'POST',
      body: JSON.stringify({ versionNumber }),
    });
  },
};
