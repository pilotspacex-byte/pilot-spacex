/**
 * useIssueExtraction - Hook for managing the issue extraction SSE stream.
 *
 * Connects to the extraction SSE endpoint, collects extracted issues,
 * and manages loading/error state for the ExtractionPreviewModal.
 *
 * Feature 009: Intent-to-Issues extraction pipeline.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { SSEClient } from '@/lib/sse-client';
import type { SSEEvent } from '@/lib/sse-client';
import type { ExtractedIssue } from '../components/ExtractionPreviewModal';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

interface ExtractionState {
  /** Extracted issues collected from SSE events */
  issues: ExtractedIssue[];
  /** Whether extraction is in progress */
  isExtracting: boolean;
  /** Error message if extraction failed */
  error: string | null;
  /** Whether the preview modal is open */
  isModalOpen: boolean;
}

interface ExtractionActions {
  /** Start extraction for a note */
  startExtraction: (params: StartExtractionParams) => void;
  /** Close the modal and reset state */
  closeModal: () => void;
  /** Abort in-progress extraction */
  abort: () => void;
}

interface StartExtractionParams {
  noteId: string;
  noteTitle: string;
  noteContent: Record<string, unknown>;
  workspaceId: string;
  selectedText?: string;
  availableLabels?: string[];
  maxIssues?: number;
}

/**
 * Hook for managing issue extraction from note content via SSE streaming.
 *
 * Returns state and actions for the extraction flow:
 * 1. startExtraction() -> opens modal, starts SSE stream
 * 2. Issues arrive via SSE -> added to issues array
 * 3. User selects issues in ExtractionPreviewModal
 * 4. closeModal() or abort() to cancel
 */
export function useIssueExtraction(): [ExtractionState, ExtractionActions] {
  const [issues, setIssues] = useState<ExtractedIssue[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const clientRef = useRef<SSEClient | null>(null);

  // Cleanup on unmount: abort any in-progress SSE connection
  useEffect(() => {
    return () => {
      clientRef.current?.abort();
    };
  }, []);

  const abort = useCallback(() => {
    clientRef.current?.abort();
    clientRef.current = null;
    setIsExtracting(false);
  }, []);

  const closeModal = useCallback(() => {
    abort();
    setIsModalOpen(false);
    setIssues([]);
    setError(null);
  }, [abort]);

  const startExtraction = useCallback(
    (params: StartExtractionParams) => {
      // Abort any existing extraction
      abort();

      // Reset state and open modal
      setIssues([]);
      setError(null);
      setIsExtracting(true);
      setIsModalOpen(true);

      const url = `${API_BASE}/notes/${params.noteId}/extract-issues`;

      const client = new SSEClient({
        url,
        method: 'POST',
        body: {
          note_title: params.noteTitle,
          note_content: params.noteContent,
          selected_text: params.selectedText ?? null,
          available_labels: params.availableLabels?.slice(0, 50) ?? null,
          max_issues: params.maxIssues ?? 10,
        },
        headers: {
          'X-Workspace-ID': params.workspaceId,
        },
        onMessage: (event: SSEEvent) => {
          switch (event.type) {
            case 'issue': {
              const data = event.data as ExtractedIssue;
              setIssues((prev) => [...prev, data]);
              break;
            }
            case 'complete': {
              setIsExtracting(false);
              break;
            }
            case 'error': {
              const errData = event.data as { code?: string; message?: string };
              setError(errData.message ?? 'Extraction failed');
              setIsExtracting(false);
              break;
            }
            case 'progress': {
              // Progress events are informational only
              break;
            }
          }
        },
        onError: (err: Error) => {
          setError(err.message);
          setIsExtracting(false);
        },
        onComplete: () => {
          setIsExtracting(false);
        },
        maxRetries: 0, // No retries for POST extraction
      });

      clientRef.current = client;
      client.connect();
    },
    [abort]
  );

  return [
    { issues, isExtracting, error, isModalOpen },
    { startExtraction, closeModal, abort },
  ];
}
