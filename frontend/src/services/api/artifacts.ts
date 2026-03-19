import { getAuthProviderSync } from '@/services/auth/providers';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

export interface ArtifactUploadResponse {
  id: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  status: 'pending_upload' | 'ready' | 'error';
}

export interface ArtifactUrlResponse {
  url: string;
  expiresAt: string; // ISO date string
}

export const artifactsApi = {
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

  /**
   * Fetch a short-lived signed URL for a stored artifact.
   *
   * GET /v1/workspaces/{workspaceId}/projects/{projectId}/artifacts/{artifactId}/url
   */
  async getSignedUrl(
    workspaceId: string,
    projectId: string,
    artifactId: string
  ): Promise<ArtifactUrlResponse> {
    let token: string | null = null;
    try {
      token = await getAuthProviderSync().getToken();
    } catch {
      // Proceed without auth header
    }

    const res = await fetch(
      `${API_BASE}/workspaces/${workspaceId}/projects/${projectId}/artifacts/${artifactId}/url`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    );

    if (!res.ok) throw new Error(`Failed to get signed URL: ${res.status}`);
    return res.json() as Promise<ArtifactUrlResponse>;
  },
};
