/**
 * Ghost Text Store with debouncing and caching.
 *
 * Manages AI-powered text suggestions with:
 * - Debounced requests (500ms per DD-067)
 * - LRU cache for recent suggestions
 * - JSON fetch (backend returns GhostTextResponse, not SSE)
 * - Loading indicator during fetch
 *
 * @see DD-067 (Ghost text: 500ms/50 tokens/code-aware)
 * @see DD-011 (Gemini Flash for latency-critical)
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { aiApi } from '@/services/api/ai';
import type { AIStore } from './AIStore';

export class GhostTextStore {
  suggestion = '';
  isLoading = false;
  isEnabled = true;
  error: string | null = null;

  private abortController: AbortController | null = null;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
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

  requestSuggestion(noteId: string, context: string, prefix: string, workspaceId: string): void {
    if (!this.isEnabled || !this.rootStore.isGloballyEnabled) return;

    // Check cache
    const cacheKey = `${noteId}:${context.slice(-100)}:${prefix.slice(-50)}`;
    const cached = this.cache.get(cacheKey);
    if (cached) {
      this.suggestion = cached;
      return;
    }

    // Debounce - no additional delay here since GhostTextExtension already
    // debounces at 500ms per DD-067. Any extra delay here would be additive.
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      this.fetchSuggestion(context, prefix, workspaceId, cacheKey);
    }, 0);
  }

  private async fetchSuggestion(
    context: string,
    prefix: string,
    workspaceId: string,
    cacheKey: string
  ): Promise<void> {
    this.abort();

    runInAction(() => {
      this.isLoading = true;
      this.error = null;
      this.suggestion = '';
    });

    this.abortController = new AbortController();

    try {
      // Backend returns JSON GhostTextResponse { suggestion, confidence, cached }
      const { supabase } = await import('@/lib/supabase');
      const {
        data: { session },
      } = await supabase.auth.getSession();

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const response = await fetch(aiApi.getGhostTextUrl(''), {
        method: 'POST',
        headers,
        body: JSON.stringify({
          context: context.slice(-500),
          prefix: prefix.slice(-200),
          workspace_id: workspaceId,
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        if (response.status === 429) {
          // Rate limited - silently ignore, don't show error to user
          runInAction(() => {
            this.isLoading = false;
          });
          return;
        }
        throw new Error(`Ghost text request failed: ${response.status}`);
      }

      const data = await response.json();

      runInAction(() => {
        this.suggestion = data.suggestion ?? '';
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
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // Request was aborted (user continued typing) - not an error
        return;
      }
      runInAction(() => {
        this.isLoading = false;
        this.error = err instanceof Error ? err.message : 'Ghost text failed';
      });
    }
  }

  clearSuggestion(): void {
    this.suggestion = '';
  }

  abort(): void {
    this.abortController?.abort();
    this.abortController = null;
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    this.isLoading = false;
  }
}
