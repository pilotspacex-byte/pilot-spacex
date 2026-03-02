/**
 * Attachment types for chat context file uploads (Feature 020).
 *
 * @module types/attachments
 */

export type AttachmentStatus = 'uploading' | 'ready' | 'error';

export type AttachmentSource = 'local' | 'google_drive';

/**
 * Persisted attachment metadata stored in message history.
 * Mirrors the backend AttachmentMetadataSchema (BaseSchema → camelCase).
 */
export interface AttachmentMetadata {
  attachmentId: string;
  filename: string;
  mimeType: string;
  source: AttachmentSource;
  sizeBytes: number;
}

/**
 * Client-side attachment context during upload and display.
 * Tracks local state before and after server confirmation.
 */
export interface AttachmentContext {
  /** Local temp ID before upload completes */
  id: string;
  /** Server-assigned ID after upload */
  attachmentId?: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  source: AttachmentSource;
  status: AttachmentStatus;
  error?: string;
  /** Original File object retained for retry (only present for local uploads). Not persisted or serialized. */
  _file?: File;
}

/**
 * Upload response from the backend attachment endpoint.
 * Mirrors the backend AttachmentUploadResponseSchema (BaseSchema → camelCase).
 */
export interface AttachmentUploadResponse {
  attachmentId: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  source: AttachmentSource;
  expiresAt: string;
}

/**
 * MIME type whitelist matching backend validation.
 * Any type not in this list will be rejected before upload.
 */
export const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'text/csv',
  'text/x-python',
  'application/x-python',
  'text/typescript',
  'application/typescript',
  'text/javascript',
  'application/javascript',
  'application/json',
  'application/x-yaml',
  'text/yaml',
  'text/x-rust',
  'text/x-go',
  'text/x-java',
  'text/x-csrc',
  'text/x-c++src',
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
] as const;

/**
 * Per-MIME-type size limits in bytes, matching backend validation.
 * The 'default' key applies to any MIME type not explicitly listed.
 */
export const FILE_SIZE_LIMITS: Record<string, number> = {
  'application/pdf': 25 * 1024 * 1024, // 25MB for PDF/docs
  'text/plain': 5 * 1024 * 1024, // 5MB for text/code
  'image/jpeg': 10 * 1024 * 1024, // 10MB for images
  'image/png': 10 * 1024 * 1024,
  'image/webp': 10 * 1024 * 1024,
  'image/gif': 10 * 1024 * 1024,
  default: 5 * 1024 * 1024, // 5MB default for code/text
};

/** Backend response from GET /ai/drive/status (BaseSchema → camelCase). */
export interface DriveStatusResponse {
  connected: boolean;
  googleEmail: string | null;
  connectedAt: string | null;
}

/** A single file or folder from Google Drive (BaseSchema → camelCase). */
export interface DriveFileItem {
  id: string;
  name: string;
  mimeType: string;
  sizeBytes: number | null;
  modifiedAt: string | null;
  isFolder: boolean;
  iconUrl: string | null;
}

/** Paginated response from GET /ai/drive/files (BaseSchema → camelCase). */
export interface DriveFileListResponse {
  files: DriveFileItem[];
  nextPageToken: string | null;
}
