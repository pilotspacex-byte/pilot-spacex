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
              a.id === localId
                ? { ...a, attachment_id: response.attachment_id, status: 'ready' }
                : a
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
      // Validate mime type
      if (!(ACCEPTED_MIME_TYPES as readonly string[]).includes(file.type)) {
        toast.error('Unsupported file type. Please upload a PDF, image, or code file.');
        return;
      }

      // Validate file size
      const limit = FILE_SIZE_LIMITS[file.type] ?? FILE_SIZE_LIMITS['default']!;
      const limitMB = Math.round(limit / (1024 * 1024));
      if (file.size > limit) {
        toast.error(`File exceeds the ${limitMB}MB ${file.type} limit.`);
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
        mime_type: file.type,
        size_bytes: file.size,
        source: 'local',
        status: 'uploading',
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

  const retry = useCallback(async (id: string): Promise<void> => {
    setAttachments((prev) =>
      prev.map((a) =>
        a.id === id
          ? { ...a, status: 'error', error: 'Original file no longer available for retry.' }
          : a
      )
    );
  }, []);

  const addFromDrive = useCallback((response: AttachmentUploadResponse): void => {
    if (countRef.current >= 5) {
      toast.error('Maximum 5 attachments per message.');
      return;
    }
    countRef.current += 1;
    setAttachments((prev) => [
      ...prev,
      {
        id: response.attachment_id,
        attachment_id: response.attachment_id,
        filename: response.filename,
        mime_type: response.mime_type,
        size_bytes: response.size_bytes,
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
    .filter((a) => a.status === 'ready' && a.attachment_id !== undefined)
    .map((a) => a.attachment_id!);

  return { attachments, attachmentIds, addFile, addFromDrive, removeFile, retry, reset };
}
