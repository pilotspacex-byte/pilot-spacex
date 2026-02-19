/**
 * Version API client — typed wrappers for note versioning endpoints.
 *
 * All calls go to: /api/v1/workspaces/{workspaceId}/notes/{noteId}/versions/...
 * Feature 017: Note Versioning — Sprint 1 (T-216)
 */

import { apiClient } from '@/services/api/client';

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
  `/workspaces/${workspaceId}/notes/${noteId}/versions`;

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
    return apiClient.get<NoteVersionListResponse>(`${base(workspaceId, noteId)}${q ? `?${q}` : ''}`);
  },

  get(workspaceId: string, noteId: string, versionId: string): Promise<NoteVersionResponse> {
    return apiClient.get<NoteVersionResponse>(`${base(workspaceId, noteId)}/${versionId}`);
  },

  create(workspaceId: string, noteId: string, label?: string): Promise<NoteVersionResponse> {
    return apiClient.post<NoteVersionResponse>(base(workspaceId, noteId), {
      label: label ?? null,
    });
  },

  diff(workspaceId: string, noteId: string, v1Id: string, v2Id: string): Promise<DiffResponse> {
    return apiClient.get<DiffResponse>(`${base(workspaceId, noteId)}/${v1Id}/diff/${v2Id}`);
  },

  restore(
    workspaceId: string,
    noteId: string,
    versionId: string,
    versionNumber: number
  ): Promise<RestoreResponse> {
    return apiClient.post<RestoreResponse>(`${base(workspaceId, noteId)}/${versionId}/restore`, {
      versionNumber,
    });
  },

  digest(workspaceId: string, noteId: string, versionId: string): Promise<DigestResponse> {
    return apiClient.get<DigestResponse>(`${base(workspaceId, noteId)}/${versionId}/digest`);
  },

  pin(
    workspaceId: string,
    noteId: string,
    versionId: string,
    pinned: boolean
  ): Promise<NoteVersionResponse> {
    return apiClient.put<NoteVersionResponse>(`${base(workspaceId, noteId)}/${versionId}/pin`, {
      pinned,
    });
  },

  undoAI(workspaceId: string, noteId: string, versionNumber: number): Promise<UndoAiResponse> {
    return apiClient.post<UndoAiResponse>(`${base(workspaceId, noteId)}/undo-ai`, {
      versionNumber,
    });
  },
};
