/**
 * GhostTextService - SSE client for AI-powered text suggestions
 * Manages EventSource connection with auto-reconnect, cancellation, and timeout
 */

export interface GhostTextRequest {
  /** Text before cursor position */
  text: string;
  /** Cursor position in document */
  cursorPosition: number;
  /** Surrounding context for better suggestions */
  context: string;
  /** Block ID for context */
  blockId?: string;
  /** Block type (paragraph, heading, etc.) */
  blockType?: string;
}

export interface GhostTextEvent {
  /** Event type */
  type: 'text' | 'done' | 'error';
  /** Event data */
  data: string;
}

export interface GhostTextServiceOptions {
  /** Base API URL */
  baseUrl?: string;
  /** Connection timeout in ms (default: 5000) */
  timeoutMs?: number;
  /** Max reconnect attempts (default: 3) */
  maxReconnectAttempts?: number;
  /** Reconnect delay in ms (default: 1000) */
  reconnectDelayMs?: number;
}

const DEFAULT_OPTIONS: Required<GhostTextServiceOptions> = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? '/api/v1',
  timeoutMs: 5000,
  maxReconnectAttempts: 3,
  reconnectDelayMs: 1000,
};

/**
 * GhostTextService manages SSE connections for AI text suggestions
 *
 * Features:
 * - EventSource connection management
 * - Auto-reconnect on connection failure
 * - Request cancellation
 * - 5s timeout
 * - Buffered text accumulation
 *
 * @example
 * ```tsx
 * const service = new GhostTextService();
 *
 * // Request completion
 * await service.requestCompletion(
 *   { text: 'Hello, ', cursorPosition: 7, context: 'greeting' },
 *   (chunk) => setGhostText(prev => prev + chunk),
 *   () => console.log('Complete'),
 *   (error) => console.error(error)
 * );
 *
 * // Cancel if needed
 * service.cancel();
 * ```
 */
export class GhostTextService {
  private eventSource: EventSource | null = null;
  private options: Required<GhostTextServiceOptions>;
  private reconnectAttempts = 0;
  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;
  private textBuffer = '';

  constructor(options: GhostTextServiceOptions = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
  }

  /**
   * Request a text completion from the AI service
   */
  async requestCompletion(
    request: GhostTextRequest,
    onChunk: (text: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    // Cancel any existing request
    this.cancel();

    // Reset state
    this.textBuffer = '';
    this.reconnectAttempts = 0;
    this.abortController = new AbortController();

    try {
      await this.connect(request, onChunk, onComplete, onError);
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        onError(error);
      }
    }
  }

  /**
   * Cancel the current request
   */
  cancel(): void {
    // Clear timeout
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    // Abort fetch
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    // Close EventSource
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    // Reset state
    this.textBuffer = '';
    this.reconnectAttempts = 0;
  }

  /**
   * Get accumulated text buffer
   */
  getBuffer(): string {
    return this.textBuffer;
  }

  /**
   * Check if service is currently connected
   */
  isConnected(): boolean {
    return this.eventSource !== null && this.eventSource.readyState === EventSource.OPEN;
  }

  /**
   * Internal: Connect to SSE endpoint
   */
  private async connect(
    request: GhostTextRequest,
    onChunk: (text: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      // Build URL with query params
      const params = new URLSearchParams({
        text: request.text,
        cursor_position: String(request.cursorPosition),
        context: request.context,
      });

      if (request.blockId) {
        params.set('block_id', request.blockId);
      }
      if (request.blockType) {
        params.set('block_type', request.blockType);
      }

      const url = `${this.options.baseUrl}/ai/ghost-text?${params.toString()}`;

      // Set timeout
      this.timeoutId = setTimeout(() => {
        this.cancel();
        const error = new Error('Ghost text request timed out');
        error.name = 'TimeoutError';
        onError(error);
        reject(error);
      }, this.options.timeoutMs);

      // Create EventSource
      this.eventSource = new EventSource(url, {
        // Note: EventSource doesn't support custom headers directly
        // Authentication would need to be handled via cookies or query params
      });

      // Handle open
      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
      };

      // Handle messages
      this.eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as GhostTextEvent;

          switch (parsed.type) {
            case 'text':
              this.textBuffer += parsed.data;
              onChunk(parsed.data);
              break;

            case 'done':
              this.clearTimeout();
              this.close();
              onComplete();
              resolve();
              break;

            case 'error':
              this.clearTimeout();
              this.close();
              const error = new Error(parsed.data || 'Unknown error');
              onError(error);
              reject(error);
              break;
          }
        } catch {
          // Handle plain text events (non-JSON)
          if (event.data && event.data !== '[DONE]') {
            this.textBuffer += event.data;
            onChunk(event.data);
          } else if (event.data === '[DONE]') {
            this.clearTimeout();
            this.close();
            onComplete();
            resolve();
          }
        }
      };

      // Handle errors
      this.eventSource.onerror = (_event) => {
        // Check if this is a normal close
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          return;
        }

        this.close();

        // Attempt reconnect
        if (this.reconnectAttempts < this.options.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => {
            this.connect(request, onChunk, onComplete, onError).then(resolve).catch(reject);
          }, this.options.reconnectDelayMs * this.reconnectAttempts);
        } else {
          this.clearTimeout();
          const error = new Error('Failed to connect to ghost text service');
          error.name = 'ConnectionError';
          onError(error);
          reject(error);
        }
      };
    });
  }

  /**
   * Internal: Clear timeout
   */
  private clearTimeout(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
  }

  /**
   * Internal: Close connection
   */
  private close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

// Singleton instance
let ghostTextServiceInstance: GhostTextService | null = null;

/**
 * Get singleton instance of GhostTextService
 */
export function getGhostTextService(options?: GhostTextServiceOptions): GhostTextService {
  if (!ghostTextServiceInstance) {
    ghostTextServiceInstance = new GhostTextService(options);
  }
  return ghostTextServiceInstance;
}

/**
 * Reset singleton instance (useful for testing)
 */
export function resetGhostTextService(): void {
  if (ghostTextServiceInstance) {
    ghostTextServiceInstance.cancel();
    ghostTextServiceInstance = null;
  }
}
