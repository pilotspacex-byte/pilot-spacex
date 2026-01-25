import { apiClient, type PaginatedResponse } from './client';
import type { Note, CreateNoteData, JSONContent, NoteAnnotation, AnnotationStatus } from '@/types';

interface NoteFilters {
  projectId?: string;
  isPinned?: boolean;
  authorId?: string;
}

export const notesApi = {
  list(
    workspaceId: string,
    filters?: NoteFilters,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<Note>> {
    const params: Record<string, string> = {
      page: String(page),
      pageSize: String(pageSize),
    };

    if (filters?.projectId) params.projectId = filters.projectId;
    if (filters?.isPinned !== undefined) params.isPinned = String(filters.isPinned);
    if (filters?.authorId) params.authorId = filters.authorId;

    return apiClient.get<PaginatedResponse<Note>>(`/workspaces/${workspaceId}/notes`, { params });
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
    return apiClient.patch<Note>(`/workspaces/${workspaceId}/notes/${noteId}/content`, { content });
  },

  delete(workspaceId: string, noteId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/notes/${noteId}`);
  },

  pin(workspaceId: string, noteId: string): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/pin`);
  },

  unpin(workspaceId: string, noteId: string): Promise<Note> {
    return apiClient.delete<Note>(`/workspaces/${workspaceId}/notes/${noteId}/pin`);
  },

  linkIssue(workspaceId: string, noteId: string, issueId: string): Promise<Note> {
    return apiClient.post<Note>(`/workspaces/${workspaceId}/notes/${noteId}/issues`, { issueId });
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
};
