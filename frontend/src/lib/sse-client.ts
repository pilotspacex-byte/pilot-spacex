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

import { supabase } from '@/lib/supabase';

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
              this.options.onMessage(event);
            }
          }
          this.options.onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = this.parseEvents(buffer);
        buffer = events.remaining;

        for (const event of events.parsed) {
          this.options.onMessage(event);
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
   * Get Supabase auth headers for authenticated requests.
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        return { Authorization: `Bearer ${session.access_token}` };
      }
    } catch {
      console.warn('Failed to get auth session for SSE request');
    }
    return {};
  }

  /**
   * Parse SSE events from buffer.
   * Returns parsed events and any remaining incomplete data.
   */
  private parseEvents(buffer: string): { parsed: SSEEvent[]; remaining: string } {
    const parsed: SSEEvent[] = [];
    const lines = buffer.split('\n');
    let remaining = '';
    let currentEvent: Partial<SSEEvent> = {};
    let dataBuffer = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line === undefined) continue;

      // Empty line marks end of event
      if (line === '') {
        if (currentEvent.type !== undefined) {
          // Parse accumulated data
          if (dataBuffer) {
            try {
              currentEvent.data = JSON.parse(dataBuffer);
            } catch {
              currentEvent.data = dataBuffer;
            }
          }

          if (currentEvent.type && currentEvent.data !== undefined) {
            parsed.push(currentEvent as SSEEvent);
          }
        }
        currentEvent = {};
        dataBuffer = '';
        continue;
      }

      // Parse field lines
      if (line.startsWith('event:')) {
        currentEvent.type = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const data = line.slice(5).trim();
        dataBuffer += (dataBuffer ? '\n' : '') + data;
      } else if (line.startsWith('id:') || line.startsWith('retry:')) {
        // Ignore id and retry fields for now
      } else if (line.startsWith(':')) {
        // Comment line - ignore
      } else if (i === lines.length - 1 && line !== '') {
        // Last non-empty line might be incomplete
        remaining = line;
      }
    }

    // Keep incomplete event data in remaining buffer
    if (currentEvent.type !== undefined || dataBuffer) {
      const parts: string[] = [];
      if (currentEvent.type !== undefined) {
        parts.push(`event:${currentEvent.type}`);
      }
      if (dataBuffer) {
        parts.push(`data:${dataBuffer}`);
      }
      remaining = parts.join('\n') + (remaining ? '\n' + remaining : '');
    }

    return { parsed, remaining };
  }

  /**
   * Delay helper for retry backoff.
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
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
