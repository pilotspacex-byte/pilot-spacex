import { apiClient } from './client';
import { getAuthProviderSync } from '@/services/auth/providers';
import type { Artifact, ArtifactSignedUrlResponse } from '@/types/artifact';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

export interface ArtifactUploadResponse {
  id: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  status: 'pending_upload' | 'ready' | 'error';
}

/**
 * @deprecated Use ArtifactSignedUrlResponse from @/types/artifact instead.
 * Kept for backward compatibility with existing callers.
 */
export interface ArtifactUrlResponse {
  url: string;
  expiresAt: string; // ISO date string
}

export const artifactsApi = {
  /**
   * List all artifacts for a project.
   *
   * GET /workspaces/{workspaceId}/projects/{projectId}/artifacts
   * Handles both flat Artifact[] and PaginatedResponse<Artifact> shapes.
   */
  list(workspaceId: string, projectId: string): Promise<Artifact[]> {
    return apiClient
      .get<
        Artifact[] | { artifacts: Artifact[]; total: number } | { items: Artifact[] }
      >(`/workspaces/${workspaceId}/projects/${projectId}/artifacts`)
      .then((res) => {
        if (Array.isArray(res)) return res;
        if ('artifacts' in res) return res.artifacts;
        return (res as { items: Artifact[] }).items;
      });
  },

  /**
   * Delete an artifact by ID.
   *
   * DELETE /workspaces/{workspaceId}/projects/{projectId}/artifacts/{artifactId}
   */
  delete(workspaceId: string, projectId: string, artifactId: string): Promise<void> {
    return apiClient.delete<void>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}`
    );
  },

  /**
   * Fetch a short-lived signed URL for artifact download/preview via apiClient.
   *
   * GET /workspaces/{workspaceId}/projects/{projectId}/artifacts/{artifactId}/url
   * Returns ArtifactSignedUrlResponse (url + expiresAt).
   */
  getSignedUrl(
    workspaceId: string,
    projectId: string,
    artifactId: string
  ): Promise<ArtifactSignedUrlResponse> {
    return apiClient.get<ArtifactSignedUrlResponse>(
      `/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/url`
    );
  },

  /**
   * Upload a file to the artifacts store via multipart POST.
   *
   * Uses XMLHttpRequest so that upload progress events fire reliably.
   * `onProgress` is called with 0–100 as the upload proceeds.
   */
  upload(
    workspaceId: string,
    projectId: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<ArtifactUploadResponse> {
    return new Promise((resolve, reject) => {
      void (async () => {
        let token: string | null = null;
        try {
          token = await getAuthProviderSync().getToken();
        } catch {
          // Proceed without auth header — server will reject with 401 if required
        }

        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        xhr.open('POST', `${API_BASE}/workspaces/${workspaceId}/projects/${projectId}/artifacts`);
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && onProgress) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText) as ArtifactUploadResponse);
            } catch {
              reject(new Error('Invalid JSON response from upload'));
            }
          } else {
            reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));
        xhr.onabort = () => reject(new Error('Upload aborted'));

        xhr.send(formData);
      })();
    });
  },
};
