import { apiClient } from './client';
import type {
  AttachmentUploadResponse,
  DriveStatusResponse,
  DriveFileListResponse,
} from '@/types/attachments';

export const attachmentsApi = {
  /**
   * Upload a file as a chat context attachment.
   *
   * Uses multipart/form-data so the axios instance's default JSON
   * Content-Type header is overridden per-request.
   */
  upload(file: File, workspaceId: string, sessionId?: string): Promise<AttachmentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', workspaceId);
    if (sessionId) formData.append('session_id', sessionId);

    return apiClient.post<AttachmentUploadResponse>('/ai/attachments/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * Delete an uploaded attachment by its server-assigned ID.
   * Called when a user removes an attachment before or after sending.
   */
  delete(attachmentId: string): Promise<void> {
    return apiClient.delete<void>(`/ai/attachments/${attachmentId}`);
  },

  /**
   * Check whether Google Drive is connected for the given workspace.
   * GET /ai/drive/status?workspace_id=...
   */
  getDriveStatus(workspaceId: string): Promise<DriveStatusResponse> {
    return apiClient.get<DriveStatusResponse>('/ai/drive/status', {
      params: { workspace_id: workspaceId },
    });
  },

  /**
   * Retrieve the Google OAuth authorization URL for Drive connection.
   * GET /ai/drive/auth-url?workspace_id=...&redirect_uri=...
   */
  getDriveAuthUrl(workspaceId: string, redirectUri: string): Promise<{ auth_url: string }> {
    return apiClient.get<{ auth_url: string }>('/ai/drive/auth-url', {
      params: { workspace_id: workspaceId, redirect_uri: redirectUri },
    });
  },

  /**
   * List files and folders from Google Drive.
   * GET /ai/drive/files?workspace_id=...&parent_id=...&search=...&page_token=...
   */
  getDriveFiles(
    workspaceId: string,
    params?: { parent_id?: string; search?: string; page_token?: string }
  ): Promise<DriveFileListResponse> {
    return apiClient.get<DriveFileListResponse>('/ai/drive/files', {
      params: { workspace_id: workspaceId, ...params },
    });
  },

  /**
   * Import a Drive file as a chat context attachment.
   * POST /ai/drive/import
   */
  importDriveFile(request: {
    workspace_id: string;
    file_id: string;
    filename: string;
    mime_type: string;
    session_id?: string;
  }): Promise<AttachmentUploadResponse> {
    return apiClient.post<AttachmentUploadResponse>('/ai/drive/import', request);
  },

  /**
   * Revoke stored Google Drive credentials for the workspace.
   * DELETE /ai/drive/credentials?workspace_id=...
   */
  revokeDriveCredentials(workspaceId: string): Promise<void> {
    return apiClient.delete<void>('/ai/drive/credentials', {
      params: { workspace_id: workspaceId },
    });
  },
};
