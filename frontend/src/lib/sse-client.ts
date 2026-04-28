/**
 * SSE Client Utility with reconnection and error handling.
 *
 * Provides a type-safe wrapper around fetch ReadableStream with:
 * - Automatic reconnection with exponential backoff
 * - Abort controller integration
 * - Typed event parsing
 *
 * @module lib/sse-client
 * @see specs/004-mvp-agents-build/tasks/P16-T111-T120.md#T111
 */

import { getAuthProviderSync } from '@/services/auth/providers';
import type {
  InlineArtifactRef,
} from '@/components/chat/InlineArtifactCard';
import type { ArtifactTokenKey } from '@/lib/artifact-tokens';

/**
 * Phase 87.1 Plan 04 — wire format → ArtifactTokenKey map.
 * Source of truth for SSE handler. Backend `pilot-files` MCP server emits
 * `format: 'md' | 'html'`; frontend renders by ArtifactTokenKey ('MD' | 'HTML').
 * Unknown formats default to 'MD' (safe fallback) — and we already drop
 * malformed events at the parser layer.
 */
const ARTIFACT_FORMAT_TO_TOKEN: Record<string, ArtifactTokenKey> = {
  md: 'MD',
  html: 'HTML',
};

export interface SSEClientOptions {
  /** SSE endpoint URL */
  url: string;
  /** Request body for POST requests (omit for GET) */
  body?: Record<string, unknown>;
  /** HTTP method (default: POST if body provided, GET otherwise) */
  method?: 'GET' | 'POST';
  /** Additional headers */
  headers?: Record<string, string>;
  /** Called for each parsed SSE event */
  onMessage: (event: SSEEvent) => void;
  /**
   * Phase 87.1 Plan 04 — called when a `artifact_created` event arrives.
   * The wire payload (snake_case) is mapped to the frontend `InlineArtifactRef`
   * (camelCase, ArtifactTokenKey). When set, `artifact_created` events are
   * intercepted here and NOT forwarded to `onMessage`.
   */
  onArtifactCreated?: (ref: InlineArtifactRef) => void;
  /** Called on unrecoverable error */
  onError?: (error: Error) => void;
  /** Called when stream completes normally */
  onComplete?: () => void;
  /** Maximum retry attempts (default: 3) */
  maxRetries?: number;
  /** Base retry delay in ms (default: 1000) */
  retryDelayMs?: number;
  /** Allow retries even for POST requests (use for idempotent endpoints) */
  retryable?: boolean;
}

export interface SSEEvent {
  /** Event type from `event:` line */
  type: string;
  /** Parsed JSON data from `data:` line */
  data: unknown;
}

/**
 * SSE Client for streaming AI responses.
 *
 * Uses fetch with ReadableStream for better control over
 * POST requests with body (EventSource only supports GET).
 *
 * @example
 * ```typescript
 * const client = new SSEClient({
 *   url: '/api/v1/ai/notes/123/ghost-text',
 *   body: { context: 'Hello world', cursor_position: 11 },
 *   onMessage: (event) => console.log(event),
 *   onComplete: () => console.log('Done'),
 * });
 *
 * await client.connect();
 * // Later: client.abort();
 * ```
 */
export class SSEClient {
  private abortController: AbortController | null = null;
  private retryCount = 0;
  private readonly maxRetries: number;
  private readonly retryDelayMs: number;
  private isAborted = false;

  constructor(private readonly options: SSEClientOptions) {
    this.maxRetries = options.maxRetries ?? 3;
    this.retryDelayMs = options.retryDelayMs ?? 1000;
  }

  /**
   * Establish SSE connection and start processing events.
   * Retries automatically on recoverable errors.
   */
  async connect(): Promise<void> {
    this.isAborted = false;
    this.abortController = new AbortController();

    try {
      const authHeaders = await this.getAuthHeaders();

      // Determine HTTP method: explicit, or based on body presence
      const method = this.options.method ?? (this.options.body ? 'POST' : 'GET');

      const response = await fetch(this.options.url, {
        method,
        headers: {
          Accept: 'text/event-stream',
          ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}),
          ...authHeaders,
          ...this.options.headers,
        },
        body:
          this.options.body && method === 'POST' ? JSON.stringify(this.options.body) : undefined,
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`SSE connection failed: ${response.status} ${errorText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (!this.isAborted) {
        const { done, value } = await reader.read();

        if (done) {
          // Process any remaining data in buffer
          if (buffer.trim()) {
            const events = this.parseEvents(buffer + '\n\n');
            for (const event of events.parsed) {
              this.dispatchEvent(event);
            }
          }
          this.options.onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = this.parseEvents(buffer);
        buffer = events.remaining;

        for (const event of events.parsed) {
          this.dispatchEvent(event);
        }
      }
    } catch (error) {
      // Handle intentional abort
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      // Handle abort flag
      if (this.isAborted) {
        return;
      }

      // Retry on recoverable errors — skip for POST unless explicitly marked retryable
      const method = this.options.method ?? (this.options.body ? 'POST' : 'GET');
      const canRetry = method === 'GET' || this.options.retryable === true;
      if (canRetry && this.retryCount < this.maxRetries) {
        this.retryCount++;
        const delay = this.retryDelayMs * Math.pow(2, this.retryCount - 1);
        await this.delay(delay);

        if (!this.isAborted) {
          return this.connect();
        }
        return;
      }

      // Unrecoverable error
      this.options.onError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }

  /**
   * Abort the current connection.
   * Safe to call multiple times.
   */
  abort(): void {
    this.isAborted = true;
    this.abortController?.abort();
    this.abortController = null;
  }

  /**
   * Check if connection is active.
   */
  get isConnected(): boolean {
    return this.abortController !== null && !this.isAborted;
  }

  /**
   * Reset retry count for next connection attempt.
   */
  resetRetries(): void {
    this.retryCount = 0;
  }

  /**
   * Get auth headers for authenticated requests.
   * Works for both Supabase and AuthCore providers.
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const token = await getAuthProviderSync().getToken();
      if (token) {
        return { Authorization: `Bearer ${token}` };
      }
    } catch {
      console.warn('Failed to get auth token for SSE request');
    }
    return {};
  }

  /**
   * Phase 87.1 Plan 04 — Route a parsed SSE event to the right callback.
   *
   * `artifact_created` events are mapped (snake_case → InlineArtifactRef) and
   * passed to `onArtifactCreated` if registered. They are NOT also forwarded
   * to `onMessage` — preventing double-handling.
   *
   * All other events flow through `onMessage` unchanged.
   */
  private dispatchEvent(event: SSEEvent): void {
    if (event.type === 'artifact_created' && this.options.onArtifactCreated) {
      const ref = mapArtifactCreatedPayload(event.data);
      if (ref) {
        this.options.onArtifactCreated(ref);
      }
      return;
    }
    this.options.onMessage(event);
  }

  /**
   * Parse SSE events from buffer.
   * Returns parsed events and any remaining incomplete data.
   *
   * Uses double-newline splitting to correctly handle chunk boundaries
   * where event:/data: lines may be split across ReadableStream chunks.
   */
  private parseEvents(buffer: string): { parsed: SSEEvent[]; remaining: string } {
    const parsed: SSEEvent[] = [];

    // Split on double-newline — each complete SSE event ends with \n\n
    const segments = buffer.split('\n\n');

    // Last segment is either empty (buffer ended with \n\n) or incomplete
    const remaining = segments.pop() ?? '';

    for (const segment of segments) {
      if (!segment.trim()) continue;

      const event = this.parseEventBlock(segment);
      if (event) {
        parsed.push(event);
      }
    }

    return { parsed, remaining };
  }

  /**
   * Parse a single SSE event block (lines between double-newlines).
   */
  private parseEventBlock(block: string): SSEEvent | null {
    let eventType: string | undefined;
    let dataBuffer = '';

    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const data = line.slice(5).trim();
        dataBuffer += (dataBuffer ? '\n' : '') + data;
      } else if (line.startsWith(':') || line.startsWith('id:') || line.startsWith('retry:')) {
        // Comment, id, retry — ignore
      }
    }

    if (!eventType || !dataBuffer) return null;

    let parsedData: unknown;
    try {
      parsedData = JSON.parse(dataBuffer);
    } catch {
      parsedData = dataBuffer;
    }

    return { type: eventType, data: parsedData };
  }

  /**
   * Delay helper for retry backoff.
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

/**
 * Phase 87.1 Plan 04 — Map the SSE `artifact_created` wire payload (snake_case
 * dict from `pilot-files` MCP server) to a frontend `InlineArtifactRef`
 * (camelCase, ArtifactTokenKey-typed).
 *
 * Wire shape: `{ artifact_id, filename, mime_type, size_bytes, format }`
 * Returns `null` (with a warn) when `artifact_id` is missing or not a string —
 * mirrors backend's silent-drop posture for malformed metadata.
 */
function mapArtifactCreatedPayload(data: unknown): InlineArtifactRef | null {
  if (!data || typeof data !== 'object') {
    console.warn('[sse] dropped malformed artifact_created event (non-object payload)');
    return null;
  }
  const d = data as Record<string, unknown>;
  const artifactId = d['artifact_id'];
  if (typeof artifactId !== 'string' || artifactId.length === 0) {
    console.warn('[sse] dropped malformed artifact_created event (missing artifact_id)');
    return null;
  }
  const filenameRaw = d['filename'];
  const formatRaw = d['format'];
  const filename = typeof filenameRaw === 'string' ? filenameRaw : undefined;
  const formatKey = typeof formatRaw === 'string' ? formatRaw.toLowerCase() : '';
  const type: ArtifactTokenKey = ARTIFACT_FORMAT_TO_TOKEN[formatKey] ?? 'MD';

  return {
    id: artifactId,
    type,
    title: filename,
    updatedAt: new Date().toISOString(),
  };
}

/**
 * Convenience function to create and connect an SSE client.
 *
 * @example
 * ```typescript
 * const client = await createSSEConnection({
 *   url: '/api/v1/ai/notes/123/ghost-text',
 *   onMessage: (event) => console.log(event),
 * });
 *
 * // Abort when done
 * client.abort();
 * ```
 */
export async function createSSEConnection(options: SSEClientOptions): Promise<SSEClient> {
  const client = new SSEClient(options);
  await client.connect();
  return client;
}
