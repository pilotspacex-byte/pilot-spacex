/**
 * React hook for SSE streaming with MobX integration.
 *
 * Provides:
 * - Automatic cleanup on unmount
 * - Loading/error state management
 * - Abort on component unmount
 * - Cancel functionality (FR-022)
 *
 * @module hooks/use-sse-stream
 * @see specs/004-mvp-agents-build/tasks/P16-T111-T120.md#T112
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import { parseAIError, type AIError } from '@/types/ai-errors';

export interface UseSSEStreamOptions<T> {
  /** SSE endpoint URL */
  url: string;
  /** Request body for POST */
  body?: Record<string, unknown>;
  /** Called for each SSE event */
  onEvent: (event: SSEEvent) => void;
  /** Called when stream completes successfully */
  onComplete?: (result?: T) => void;
  /** Called on error */
  onError?: (error: AIError) => void;
  /** Called when stream is cancelled by user (FR-022) */
  onCancel?: () => void;
  /** Additional headers */
  headers?: Record<string, string>;
  /** Auto-start on mount (default: false) */
  autoStart?: boolean;
}

export interface UseSSEStreamResult {
  /** Whether stream is currently active */
  isStreaming: boolean;
  /** Whether cancellation is in progress */
  isCancelling: boolean;
  /** Current error state */
  error: AIError | null;
  /** Start streaming */
  start: (body?: Record<string, unknown>) => Promise<void>;
  /** Abort the stream (internal cleanup) */
  abort: () => void;
  /** Cancel the stream (user-initiated, triggers onCancel) */
  cancel: () => void;
  /** Reset error state */
  clearError: () => void;
}

/**
 * Hook for SSE streaming with lifecycle management.
 *
 * @example
 * ```typescript
 * function GhostTextComponent({ noteId }: { noteId: string }) {
 *   const { isStreaming, error, start, cancel } = useSSEStream<string>({
 *     url: `/api/v1/ai/notes/${noteId}/ghost-text`,
 *     onEvent: (event) => {
 *       if (event.type === 'token') {
 *         setSuggestion(prev => prev + event.data.content);
 *       }
 *     },
 *     onComplete: () => console.log('Done'),
 *     onCancel: () => toast.info('Cancelled'),
 *   });
 *
 *   return (
 *     <div>
 *       <button onClick={() => start({ context: 'Hello' })}>
 *         {isStreaming ? 'Generating...' : 'Generate'}
 *       </button>
 *       {isStreaming && (
 *         <button onClick={cancel}>Cancel</button>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useSSEStream<T = unknown>(options: UseSSEStreamOptions<T>): UseSSEStreamResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [error, setError] = useState<AIError | null>(null);

  const clientRef = useRef<SSEClient | null>(null);
  const isMountedRef = useRef(true);
  const optionsRef = useRef(options);

  // Keep options ref updated
  optionsRef.current = options;

  /**
   * Abort the current stream (internal cleanup).
   */
  const abort = useCallback(() => {
    clientRef.current?.abort();
    clientRef.current = null;
    if (isMountedRef.current) {
      setIsStreaming(false);
      setIsCancelling(false);
    }
  }, []);

  /**
   * Cancel the stream (user-initiated).
   * Triggers onCancel callback.
   */
  const cancel = useCallback(() => {
    if (!clientRef.current || !isStreaming) return;

    setIsCancelling(true);

    // Abort the stream
    clientRef.current.abort();
    clientRef.current = null;

    if (isMountedRef.current) {
      setIsStreaming(false);
      setIsCancelling(false);
      optionsRef.current.onCancel?.();
    }
  }, [isStreaming]);

  /**
   * Start streaming.
   * Aborts any existing stream first.
   */
  const start = useCallback(
    async (body?: Record<string, unknown>) => {
      // Cancel any existing stream
      abort();

      if (!isMountedRef.current) return;

      setError(null);
      setIsStreaming(true);

      const mergedBody = { ...optionsRef.current.body, ...body };

      const client = new SSEClient({
        url: optionsRef.current.url,
        body: Object.keys(mergedBody).length > 0 ? mergedBody : undefined,
        headers: optionsRef.current.headers,
        onMessage: (event) => {
          if (isMountedRef.current) {
            optionsRef.current.onEvent(event);
          }
        },
        onComplete: () => {
          if (isMountedRef.current) {
            setIsStreaming(false);
            optionsRef.current.onComplete?.();
          }
        },
        onError: (err) => {
          if (isMountedRef.current) {
            const aiError = parseAIError(err);
            setError(aiError);
            setIsStreaming(false);
            optionsRef.current.onError?.(aiError);
          }
        },
      });

      clientRef.current = client;
      await client.connect();
    },
    [abort]
  );

  /**
   * Clear error state.
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Auto-start on mount if configured
  useEffect(() => {
    if (options.autoStart) {
      void start();
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      clientRef.current?.abort();
      clientRef.current = null;
    };
  }, []);

  return {
    isStreaming,
    isCancelling,
    error,
    start,
    abort,
    cancel,
    clearError,
  };
}

/**
 * Simplified hook for one-shot SSE streams.
 *
 * Automatically starts on mount and aborts on unmount.
 *
 * @example
 * ```typescript
 * function AIContextPanel({ issueId }: { issueId: string }) {
 *   const [context, setContext] = useState<AIContext | null>(null);
 *
 *   const { isStreaming, error } = useSSEStreamOnce<AIContext>({
 *     url: `/api/v1/ai/issues/${issueId}/context`,
 *     onEvent: (event) => {
 *       if (event.type === 'complete') {
 *         setContext(event.data as AIContext);
 *       }
 *     },
 *   });
 *
 *   if (isStreaming) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *   return <ContextDisplay context={context} />;
 * }
 * ```
 */
export function useSSEStreamOnce<T = unknown>(
  options: Omit<UseSSEStreamOptions<T>, 'autoStart'>
): Omit<UseSSEStreamResult, 'start'> {
  const result = useSSEStream<T>({ ...options, autoStart: true });
  // Omit start since it auto-starts
  const { start: _start, ...rest } = result;
  return rest;
}

// Re-export SSEEvent for convenience
export type { SSEEvent };
