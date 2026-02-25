/**
 * PilotSpace SSE Parser - SSE stream connection, parsing, and retry logic.
 *
 * Extracted from PilotSpaceStreamHandler to reduce file size.
 * Handles raw SSE stream connection/consumption and event parsing.
 *
 * @module stores/ai/PilotSpaceSSEParser
 */
import { runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import type { PilotSpaceStore } from './PilotSpaceStore';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

/** Maximum retry attempts for retryable errors */
const MAX_RETRY_ATTEMPTS = 3;

/**
 * Manages SSE stream connection, parsing, and retry logic.
 */
export class PilotSpaceSSEParser {
  private client: SSEClient | null = null;
  private _retryCount = 0;
  private _retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private store: PilotSpaceStore,
    private onEvent: (event: SSEEvent) => void
  ) {}

  /** Connect to a specific SSE stream URL (queue mode). */
  async connectToStream(streamUrl: string): Promise<void> {
    this.resetRetryState();
    const absoluteUrl = streamUrl.startsWith('http')
      ? streamUrl
      : `${API_BASE}${streamUrl.startsWith('/') ? '' : '/'}${streamUrl}`;

    this.client = new SSEClient({
      url: absoluteUrl,
      method: 'GET',
      onMessage: (event: SSEEvent) => this.onEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.store.updateStreamingState({
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          });
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.store.updateStreamingState({
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          });
          this.store.error = err.message;
        });
      },
    });

    await this.client.connect();
  }

  /**
   * Consume SSE events from a fetch Response stream (direct mode).
   */
  async consumeSSEStream(response: Response): Promise<void> {
    this.resetRetryState();
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          if (buffer.trim()) {
            const events = this.parseSSEBuffer(buffer + '\n\n');
            for (const event of events) {
              this.onEvent(event);
            }
          }
          runInAction(() => {
            this.store.updateStreamingState({
              isStreaming: false,
              streamContent: '',
              currentMessageId: null,
            });
          });
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = this.parseSSEBuffer(buffer);

        const lastDoubleNewline = buffer.lastIndexOf('\n\n');
        if (lastDoubleNewline !== -1) {
          buffer = buffer.slice(lastDoubleNewline + 2);
        }

        for (const event of events) {
          this.onEvent(event);
        }
      }
    } catch (err) {
      runInAction(() => {
        this.store.updateStreamingState({
          isStreaming: false,
          streamContent: '',
          currentMessageId: null,
        });
        this.store.error = err instanceof Error ? err.message : 'Stream error';
      });
    } finally {
      reader.releaseLock();
    }
  }

  /** Parse SSE buffer into events. */
  parseSSEBuffer(buffer: string): SSEEvent[] {
    const events: SSEEvent[] = [];
    const eventBlocks = buffer.split('\n\n').filter((block) => block.trim());

    for (const block of eventBlocks) {
      const lines = block.split('\n');
      let eventType = '';
      let eventData = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          eventData += (eventData ? '\n' : '') + line.slice(5).trim();
        }
      }

      if (eventType && eventData) {
        try {
          const data = JSON.parse(eventData);
          events.push({ type: eventType, data });
        } catch {
          // Skip invalid JSON
        }
      }
    }

    return events;
  }

  /** Get Supabase auth headers and workspace context. */
  async getAuthHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {};

    try {
      const { supabase } = await import('@/lib/supabase');
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
    } catch {
      console.warn('Failed to get auth session for chat request');
    }

    const workspaceId = this.store.workspaceId;
    if (workspaceId) {
      headers['X-Workspace-Id'] = workspaceId;
    }

    return headers;
  }

  /** Abort the active SSE client connection. */
  abortClient(): void {
    this.resetRetryState();
    this.client?.abort();
    this.client = null;
  }

  /** Retry connection with exponential backoff. Returns true if retrying. */
  handleRetryableError(errorCode: string, message: string, retryAfter?: number): boolean {
    if (this._retryCount >= MAX_RETRY_ATTEMPTS) {
      this._retryCount = 0;
      return false;
    }

    this._retryCount++;
    const delaySeconds = retryAfter ?? Math.pow(2, this._retryCount - 1);
    this.store.error = `[${errorCode}] ${message} — retrying in ${delaySeconds}s (${this._retryCount}/${MAX_RETRY_ATTEMPTS})`;

    this._retryTimer = setTimeout(() => {
      this._retryTimer = null;
      if (this.client) {
        this.client.connect();
      }
    }, delaySeconds * 1000);

    return true;
  }

  /** Reset retry state. Call when starting a new stream. */
  resetRetryState(): void {
    this._retryCount = 0;
    if (this._retryTimer) {
      clearTimeout(this._retryTimer);
      this._retryTimer = null;
    }
  }
}
