/**
 * useAttachments — local file upload state for chat context attachments.
 *
 * Manages the full lifecycle: validation → optimistic add → upload → ready/error.
 * Uses useState-based local state (not TanStack Query) since attachment state
 * is ephemeral per message compose session.
 *
 * Upload is deferred to the next macro-task (setTimeout 0) after the attachment
 * is added to state, so callers see 'uploading' status immediately after addFile.
 * A generation counter prevents stale timeout callbacks (from reset or unmount)
 * from calling the API or mutating state.
 *
 * @module features/ai/ChatView/hooks/useAttachments
 */

import { useState, useCallback, useRef, useEffect, useLayoutEffect } from 'react';
import { toast } from 'sonner';
import { attachmentsApi } from '@/services/api/attachments';
import { ACCEPTED_MIME_TYPES, FILE_SIZE_LIMITS } from '@/types/attachments';
import type { AttachmentContext, AttachmentUploadResponse } from '@/types/attachments';

/**
 * Extension → MIME fallback for code files whose browser-reported MIME type
 * doesn't match the allowlist (e.g. .py reported as 'application/x-python-script').
 */
const EXTENSION_MIME_FALLBACK: Record<string, string> = {
  py: 'text/x-python',
  ts: 'text/typescript',
  tsx: 'text/typescript',
  js: 'text/javascript',
  jsx: 'text/javascript',
  rs: 'text/x-rust',
  go: 'text/x-go',
  java: 'text/x-java',
  c: 'text/x-csrc',
  cpp: 'text/x-c++src',
  h: 'text/x-csrc',
  hpp: 'text/x-c++src',
  json: 'application/json',
  yaml: 'application/x-yaml',
  yml: 'application/x-yaml',
  md: 'text/markdown',
  csv: 'text/csv',
  txt: 'text/plain',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
};

// ── Types ──────────────────────────────────────────────────────────────────

interface UseAttachmentsOptions {
  workspaceId: string;
  sessionId?: string;
}

export interface UseAttachmentsReturn {
  attachments: AttachmentContext[];
  /** Server-assigned IDs of attachments with status === 'ready' */
  attachmentIds: string[];
  addFile: (file: File) => Promise<void>;
  /** Add a Drive-imported attachment directly from its upload response. */
  addFromDrive: (response: AttachmentUploadResponse) => void;
  removeFile: (id: string) => void;
  retry: (id: string) => Promise<void>;
  reset: () => void;
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useAttachments({
  workspaceId,
  sessionId,
}: UseAttachmentsOptions): UseAttachmentsReturn {
  const [attachments, setAttachments] = useState<AttachmentContext[]>([]);

  // Stable ref always reflecting current count for synchronous validation
  // across concurrent addFile calls within the same event handler tick.
  const countRef = useRef<number>(0);

  // Generation counter: incremented on reset() and unmount.
  // Each deferred upload captures the current generation; if the generation
  // has advanced by the time the setTimeout fires, the upload is abandoned.
  const generationRef = useRef<number>(0);

  // Stable refs for options to avoid stale closure in setTimeout callbacks
  const workspaceIdRef = useRef(workspaceId);
  const sessionIdRef = useRef(sessionId);

  // Stable ref to setAttachments for use inside setTimeout without re-renders
  const setAttachmentsRef = useRef(setAttachments);

  // Sync mutable refs after each render (useLayoutEffect = synchronous,
  // before paint; avoids the react-hooks/refs "during render" lint error).
  // Dependencies listed explicitly to satisfy exhaustive-deps rule.
  useLayoutEffect(() => {
    countRef.current = attachments.length;
    workspaceIdRef.current = workspaceId;
    sessionIdRef.current = sessionId;
    setAttachmentsRef.current = setAttachments;
  }, [attachments.length, workspaceId, sessionId]);

  // Cancel all pending deferred uploads on unmount
  useEffect(() => {
    return () => {
      generationRef.current += 1;
    };
  }, []);

  const scheduleUpload = useCallback((localId: string, file: File): void => {
    const capturedGeneration = generationRef.current;

    // Defer to next macro-task so the component renders with 'uploading'
    // status before the network request is made.
    setTimeout(() => {
      // Abort if reset() or unmount happened since this upload was scheduled
      if (generationRef.current !== capturedGeneration) return;

      attachmentsApi
        .upload(file, workspaceIdRef.current, sessionIdRef.current)
        .then((response) => {
          if (generationRef.current !== capturedGeneration) return;
          setAttachmentsRef.current((prev) =>
            prev.map((a) =>
              a.id === localId ? { ...a, attachmentId: response.attachmentId, status: 'ready' } : a
            )
          );
        })
        .catch((err: unknown) => {
          if (generationRef.current !== capturedGeneration) return;
          const errorMessage = err instanceof Error ? err.message : 'Upload failed';
          setAttachmentsRef.current((prev) =>
            prev.map((a) => (a.id === localId ? { ...a, status: 'error', error: errorMessage } : a))
          );
        });
    }, 0);
  }, []);

  const addFile = useCallback(
    async (file: File): Promise<void> => {
      // Validate mime type — also accept files whose extension maps to a known type
      // (browsers sometimes report wrong MIME for code files like .py, .ts, .rs)
      const isAcceptedMime = (ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type);
      const isAcceptedByExt =
        !isAcceptedMime && file.name.includes('.') && EXTENSION_MIME_FALLBACK[file.name.split('.').pop()!.toLowerCase()];
      if (!isAcceptedMime && !isAcceptedByExt) {
        toast.error('Unsupported file type. Please upload a PDF, image, Office document, or code file.');
        return;
      }

      // Resolve effective MIME type (browser-reported or extension fallback)
      const effectiveMime = isAcceptedMime
        ? file.type
        : (isAcceptedByExt as string);

      // Validate file size
      const limit = FILE_SIZE_LIMITS[effectiveMime] ?? FILE_SIZE_LIMITS['default']!;
      const limitMB = Math.round(limit / (1024 * 1024));
      if (file.size > limit) {
        toast.error(`File exceeds the ${limitMB}MB limit.`);
        return;
      }

      // Validate max count using ref so concurrent calls in the same tick each
      // see the updated count without waiting for a re-render.
      if (countRef.current >= 5) {
        toast.error('Maximum 5 attachments per message.');
        return;
      }

      const localId = crypto.randomUUID();

      // Increment ref immediately so concurrent addFile calls in the same tick
      // each see the correct count before React re-renders.
      countRef.current += 1;

      const newAttachment: AttachmentContext = {
        id: localId,
        filename: file.name,
        mimeType: effectiveMime,
        sizeBytes: file.size,
        source: 'local',
        status: 'uploading',
        _file: file,
      };

      setAttachments((prev) => [...prev, newAttachment]);

      // Start upload in next macro-task — callers see 'uploading' immediately
      scheduleUpload(localId, file);
    },
    [scheduleUpload]
  );

  const removeFile = useCallback((id: string): void => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const retry = useCallback(
    async (id: string): Promise<void> => {
      const attachment = attachments.find((a) => a.id === id);
      if (!attachment?._file) {
        setAttachments((prev) =>
          prev.map((a) =>
            a.id === id
              ? { ...a, status: 'error', error: 'File no longer available for retry.' }
              : a
          )
        );
        return;
      }

      // Reset to uploading state, preserve _file for future retries
      setAttachments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'uploading', error: undefined } : a))
      );

      scheduleUpload(id, attachment._file);
    },
    [attachments, scheduleUpload]
  );

  const addFromDrive = useCallback((response: AttachmentUploadResponse): void => {
    if (countRef.current >= 5) {
      toast.error('Maximum 5 attachments per message.');
      return;
    }
    countRef.current += 1;
    setAttachments((prev) => [
      ...prev,
      {
        id: response.attachmentId,
        attachmentId: response.attachmentId,
        filename: response.filename,
        mimeType: response.mimeType,
        sizeBytes: response.sizeBytes,
        source: 'google_drive' as const,
        status: 'ready' as const,
      },
    ]);
  }, []);

  const reset = useCallback((): void => {
    // Advance generation to cancel any in-flight deferred uploads
    generationRef.current += 1;
    setAttachments([]);
  }, []);

  const attachmentIds: string[] = attachments
    .filter((a) => a.status === 'ready' && a.attachmentId !== undefined)
    .map((a) => a.attachmentId!);

  return { attachments, attachmentIds, addFile, addFromDrive, removeFile, retry, reset };
}
