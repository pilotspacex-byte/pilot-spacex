import { supabase } from '@/lib/supabase';
import { apiClient, type PaginatedResponse } from './client';
import type {
  Note,
  CreateNoteData,
  JSONContent,
  NoteAnnotation,
  AnnotationStatus,
  NoteNoteLink,
  NoteBacklink,
  NoteLinkSearchResult,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

interface NoteFilters {
  projectIds?: string[];
  isPinned?: boolean;
  authorId?: string;
  search?: string;
}

export const notesApi = {
  list(
    workspaceId: string,
    filters?: NoteFilters,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<Note>> {
    const searchParams = new URLSearchParams();
    searchParams.set('page', String(page));
    searchParams.set('pageSize', String(pageSize));

    for (const id of filters?.projectIds ?? []) {
      searchParams.append('project_ids', id);
    }

    if (filters?.isPinned !== undefined) searchParams.set('is_pinned', String(filters.isPinned));
    if (filters?.authorId) searchParams.set('author_id', filters.authorId);
    if (filters?.search) searchParams.set('search', filters.search);

    return apiClient.get<PaginatedResponse<Note>>(
      `/workspaces/${workspaceId}/notes?${searchParams.toString()}`
    );
  },

  get(workspaceId: string, noteId: string): Promise<Note> {
    return apiClient.get<Note>(`/workspaces/${workspaceId}/notes/${noteId}`);
  },

  create(workspaceId: string, data: CreateNoteData): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes`, data);
  },

  update(workspaceId: string, noteId: string, data: Partial<CreateNoteData>): Promise<Note> {
    return apiClient.patch<Note>(`/workspaces/${workspaceId}/notes/${noteId}`, data);
  },

  updateContent(workspaceId: string, noteId: string, content: JSONContent): Promise<Note> {
    return apiClient.patch<Note>(`/workspaces/${workspaceId}/notes/${noteId}`, { content });
  },

  delete(workspaceId: string, noteId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/notes/${noteId}`);
  },

  moveNote(workspaceId: string, noteId: string, projectId: string | null): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/move`, {
      project_id: projectId,
    });
  },

  pin(workspaceId: string, noteId: string): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/pin`);
  },

  unpin(workspaceId: string, noteId: string): Promise<Note> {
    return apiClient.delete<Note>(`/workspaces/${workspaceId}/notes/${noteId}/pin`);
  },

  linkIssue(
    workspaceId: string,
    noteId: string,
    issueId: string,
    linkType?: 'EXTRACTED' | 'REFERENCED' | 'RELATED',
    blockId?: string
  ): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/issues`, {
      issueId,
      linkType,
      blockId,
    });
  },

  unlinkIssue(workspaceId: string, noteId: string, issueId: string): Promise<Note> {
    return apiClient.delete<Note>(`/workspaces/${workspaceId}/notes/${noteId}/issues/${issueId}`);
  },

  getAnnotations(workspaceId: string, noteId: string): Promise<NoteAnnotation[]> {
    return apiClient.get<NoteAnnotation[]>(
      `/workspaces/${workspaceId}/notes/${noteId}/annotations`
    );
  },

  resolveAnnotation(
    workspaceId: string,
    noteId: string,
    annotationId: string
  ): Promise<NoteAnnotation> {
    return apiClient.patch<NoteAnnotation>(
      `/workspaces/${workspaceId}/notes/${noteId}/annotations/${annotationId}/resolve`,
      { resolved: true }
    );
  },

  updateAnnotationStatus(
    workspaceId: string,
    noteId: string,
    annotationId: string,
    status: AnnotationStatus
  ): Promise<NoteAnnotation> {
    return apiClient.patch<NoteAnnotation>(
      `/workspaces/${workspaceId}/notes/${noteId}/annotations/${annotationId}`,
      { status }
    );
  },

  searchNotes(workspaceId: string, query: string): Promise<NoteLinkSearchResult[]> {
    return apiClient
      .get<
        PaginatedResponse<Note>
      >(`/workspaces/${workspaceId}/notes`, { params: { search: query, pageSize: '10' } })
      .then((res) => res.items.map((n) => ({ id: n.id, title: n.title, updatedAt: n.updatedAt })));
  },

  linkNote(
    workspaceId: string,
    noteId: string,
    targetNoteId: string,
    linkType: 'inline' | 'embed' = 'inline',
    blockId?: string
  ): Promise<NoteNoteLink> {
    return apiClient.post<NoteNoteLink>(`/workspaces/${workspaceId}/notes/${noteId}/links`, {
      target_note_id: targetNoteId,
      link_type: linkType,
      block_id: blockId,
    });
  },

  unlinkNote(workspaceId: string, noteId: string, targetNoteId: string): Promise<void> {
    return apiClient.delete(`/workspaces/${workspaceId}/notes/${noteId}/links/${targetNoteId}`);
  },

  getNoteLinks(workspaceId: string, noteId: string): Promise<NoteNoteLink[]> {
    return apiClient.get<NoteNoteLink[]>(`/workspaces/${workspaceId}/notes/${noteId}/links`);
  },

  getNoteBacklinks(workspaceId: string, noteId: string): Promise<NoteBacklink[]> {
    return apiClient.get<NoteBacklink[]>(`/workspaces/${workspaceId}/notes/${noteId}/backlinks`);
  },
};

/**
 * Raw binary API for Yjs CRDT state persistence (T-117).
 *
 * Uses fetch directly (not axios) because axios cannot handle
 * application/octet-stream request/response bodies cleanly.
 * JWT is obtained from the current Supabase session.
 */
export const noteYjsStateApi = {
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

  async put(workspaceId: string, noteId: string, state: Uint8Array): Promise<void> {
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData.session?.access_token;
    const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/notes/${noteId}/yjs-state`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/octet-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: state.buffer as ArrayBuffer,
    });
    if (!res.ok) throw new Error(`YjsState PUT failed: ${res.status}`);
  },
};
