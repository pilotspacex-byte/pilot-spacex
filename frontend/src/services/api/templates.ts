/**
 * Note templates API client (T-144, Feature 016 M8).
 *
 * Endpoints (backend: /api/v1/workspaces/{workspace_id}/templates):
 *   GET    /templates             — list (member access; includes system templates)
 *   POST   /templates             — create custom template (admin/owner only)
 *   GET    /templates/{id}        — get one
 *   PATCH  /templates/{id}        — update (admin/owner or creator)
 *   DELETE /templates/{id}        — delete (admin/owner or creator; system templates forbidden)
 */
import { apiClient } from './client';

export interface NoteTemplate {
  id: string;
  workspaceId: string | null;
  name: string;
  description: string | null;
  /** TipTap document JSON (independent copy on apply — FR-064) */
  content: Record<string, unknown>;
  isSystem: boolean;
  createdBy: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface NoteTemplateListResponse {
  templates: NoteTemplate[];
  total: number;
}

export interface CreateTemplateData {
  name: string;
  description?: string;
  /** TipTap document JSON */
  content: Record<string, unknown>;
}

export interface UpdateTemplateData {
  name?: string;
  description?: string;
  content?: Record<string, unknown>;
}

export const templatesApi = {
  /** List all templates visible to the user (system + workspace custom). */
  list(workspaceId: string): Promise<NoteTemplateListResponse> {
    return apiClient.get<NoteTemplateListResponse>(`/workspaces/${workspaceId}/templates`);
  },

  /** Get a single template by ID. */
  get(workspaceId: string, templateId: string): Promise<NoteTemplate> {
    return apiClient.get<NoteTemplate>(`/workspaces/${workspaceId}/templates/${templateId}`);
  },

  /** Create a custom workspace template (admin/owner only). */
  create(workspaceId: string, data: CreateTemplateData): Promise<NoteTemplate> {
    return apiClient.post<NoteTemplate>(`/workspaces/${workspaceId}/templates`, data);
  },

  /** Update a template (admin/owner or creator; system templates forbidden). */
  update(workspaceId: string, templateId: string, data: UpdateTemplateData): Promise<NoteTemplate> {
    return apiClient.patch<NoteTemplate>(
      `/workspaces/${workspaceId}/templates/${templateId}`,
      data
    );
  },

  /** Delete a template (admin/owner or creator; system templates forbidden). */
  delete(workspaceId: string, templateId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/templates/${templateId}`);
  },
};
