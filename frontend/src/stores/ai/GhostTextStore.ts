/**
 * Ghost Text Store with debouncing and caching.
 *
 * Manages AI-powered text suggestions with:
 * - Debounced requests (300ms per requirements)
 * - LRU cache for recent suggestions
 * - SSE streaming for real-time updates
 * - Loading indicator during fetch
 *
 * @see T071-T074 (GhostText Integration with 300ms debounce)
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import { aiApi } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export class GhostTextStore {
  suggestion = '';
  isLoading = false;
  isEnabled = true;
  error: string | null = null;

  private client: SSEClient | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly debounceMs = 300; // 300ms debounce per requirements
  private cache = new Map<string, string>();
  private readonly maxCacheSize = 10;

  constructor(private rootStore: AIStore) {
    makeAutoObservable(this);
  }

  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
    if (!enabled) {
      this.clearSuggestion();
    }
  }

  requestSuggestion(noteId: string, context: string, cursorPosition: number): void {
    if (!this.isEnabled || !this.rootStore.isGloballyEnabled) return;

    // Check cache
    const cacheKey = `${noteId}:${context.slice(-100)}`;
    const cached = this.cache.get(cacheKey);
    if (cached) {
      this.suggestion = cached;
      return;
    }

    // Debounce
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.fetchSuggestion(noteId, context, cursorPosition, cacheKey);
    }, this.debounceMs);
  }

  private async fetchSuggestion(
    noteId: string,
    context: string,
    cursorPosition: number,
    cacheKey: string
  ): Promise<void> {
    this.abort();

    runInAction(() => {
      this.isLoading = true;
      this.error = null;
      this.suggestion = '';
    });

    this.client = new SSEClient({
      url: aiApi.getGhostTextUrl(noteId),
      body: {
        context,
        cursor_position: cursorPosition,
      },
      onMessage: (event: SSEEvent) => {
        if (event.type === 'token') {
          runInAction(() => {
            this.suggestion += (event.data as { content: string }).content;
          });
        }
      },
      onComplete: () => {
        runInAction(() => {
          this.isLoading = false;
          // Cache the result
          if (this.suggestion) {
            this.cache.set(cacheKey, this.suggestion);
            if (this.cache.size > this.maxCacheSize) {
              const firstKey = this.cache.keys().next().value;
              if (firstKey) {
                this.cache.delete(firstKey);
              }
            }
          }
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.isLoading = false;
          this.error = err.message;
        });
      },
    });

    await this.client.connect();
  }

  clearSuggestion(): void {
    this.suggestion = '';
  }

  abort(): void {
    this.client?.abort();
    this.client = null;
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    this.isLoading = false;
  }
}
