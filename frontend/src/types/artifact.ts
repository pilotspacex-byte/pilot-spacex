/**
 * Artifact domain types.
 *
 * Artifacts are files uploaded to projects and stored in Supabase Storage.
 * They are accessible via short-lived signed URLs that expire at 60 minutes.
 */

export interface Artifact {
  id: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  status: 'ready' | 'pending_upload';
  uploaderId: string;
  uploader?: {
    id: string;
    displayName: string;
    email: string;
  };
  projectId: string;
  workspaceId: string;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
}

export interface ArtifactSignedUrlResponse {
  url: string;
  expiresAt: string; // ISO 8601
}
