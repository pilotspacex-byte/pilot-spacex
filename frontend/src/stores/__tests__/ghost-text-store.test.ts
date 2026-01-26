/**
 * GhostTextStore Tests (T130)
 * Tests for MobX store managing AI-powered text suggestions
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { when } from 'mobx';
import { GhostTextStore } from '@/stores/ai/GhostTextStore';
import { AIStore } from '@/stores/ai/AIStore';
import type { SSEClient } from '@/lib/sse-client';

// Mock SSEClient
vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
    isConnected: false,
    resetRetries: vi.fn(),
  })),
}));

// Mock aiApi
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    getGhostTextUrl: (noteId: string) => `/api/v1/ai/notes/${noteId}/ghost-text`,
  },
}));

describe('GhostTextStore', () => {
  let aiStore: AIStore;
  let ghostTextStore: GhostTextStore;

  beforeEach(() => {
    vi.clearAllMocks();
    aiStore = new AIStore();
    ghostTextStore = aiStore.ghostText;
  });

  afterEach(() => {
    ghostTextStore.abort();
  });

  describe('initialization', () => {
    it('should initialize with default state', () => {
      expect(ghostTextStore.suggestion).toBe('');
      expect(ghostTextStore.isLoading).toBe(false);
      expect(ghostTextStore.isEnabled).toBe(true);
      expect(ghostTextStore.error).toBeNull();
    });

    it('should respect AI store global enabled state', () => {
      aiStore.setGloballyEnabled(false);
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      expect(ghostTextStore.isLoading).toBe(false);
    });
  });

  describe('setEnabled', () => {
    it('should enable ghost text', () => {
      ghostTextStore.setEnabled(true);
      expect(ghostTextStore.isEnabled).toBe(true);
    });

    it('should disable ghost text and clear suggestion', () => {
      ghostTextStore.suggestion = 'test suggestion';
      ghostTextStore.setEnabled(false);

      expect(ghostTextStore.isEnabled).toBe(false);
      expect(ghostTextStore.suggestion).toBe('');
    });
  });

  describe('requestSuggestion', () => {
    it('should not request when disabled', () => {
      ghostTextStore.setEnabled(false);
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should not request when globally disabled', () => {
      aiStore.setGloballyEnabled(false);
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should return cached suggestion if available', () => {
      // Simulate cache hit
      const cacheKey = 'note-123:Hello ';
      // @ts-expect-error - accessing private cache for testing
      ghostTextStore.cache.set(cacheKey, 'world');

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      expect(ghostTextStore.suggestion).toBe('world');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should debounce multiple requests', async () => {
      vi.useFakeTimers();

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);
      ghostTextStore.requestSuggestion('note-123', 'Hello w', 7);
      ghostTextStore.requestSuggestion('note-123', 'Hello wo', 8);

      // Only last request should trigger after debounce
      expect(ghostTextStore.isLoading).toBe(false);

      vi.advanceTimersByTime(500);
      await vi.runAllTimersAsync();

      expect(ghostTextStore.isLoading).toBe(true);

      vi.useRealTimers();
    });

    it('should cache successful suggestions', async () => {
      const mockClient = {
        connect: vi.fn().mockResolvedValue(undefined),
        abort: vi.fn(),
        isConnected: false,
        resetRetries: vi.fn(),
      } as unknown as SSEClient;

      // Mock SSEClient to simulate successful response
      const { SSEClient } = await import('@/lib/sse-client');
      vi.mocked(SSEClient).mockImplementation(
        (options) =>
          ({
            ...mockClient,
            connect: async () => {
              // Simulate token events
              options.onMessage({ type: 'token', data: { content: 'world' } });
              options.onComplete?.();
            },
          }) as unknown as SSEClient
      );

      await ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      // Wait for debounce and completion
      await new Promise((resolve) => setTimeout(resolve, 600));

      // Check cache
      const cacheKey = 'note-123:Hello ';
      // @ts-expect-error - accessing private cache for testing
      expect(ghostTextStore.cache.get(cacheKey)).toBe('world');
    });
  });

  describe('clearSuggestion', () => {
    it('should clear current suggestion', () => {
      ghostTextStore.suggestion = 'test suggestion';
      ghostTextStore.clearSuggestion();

      expect(ghostTextStore.suggestion).toBe('');
    });
  });

  describe('abort', () => {
    it('should abort current request', () => {
      const mockClient = {
        abort: vi.fn(),
        connect: vi.fn(),
        isConnected: true,
        resetRetries: vi.fn(),
      } as unknown as SSEClient;

      // @ts-expect-error - setting private client for testing
      ghostTextStore.client = mockClient;
      ghostTextStore.isLoading = true;

      ghostTextStore.abort();

      expect(mockClient.abort).toHaveBeenCalled();
      expect(ghostTextStore.isLoading).toBe(false);
      // @ts-expect-error - accessing private client
      expect(ghostTextStore.client).toBeNull();
    });

    it('should clear debounce timer', async () => {
      vi.useFakeTimers();

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      // @ts-expect-error - accessing private debounceTimer
      expect(ghostTextStore.debounceTimer).not.toBeNull();

      ghostTextStore.abort();

      // @ts-expect-error - accessing private debounceTimer
      expect(ghostTextStore.debounceTimer).toBeNull();

      vi.useRealTimers();
    });
  });

  describe('cache management', () => {
    it('should limit cache size to maxCacheSize', () => {
      const maxSize = 10;

      // Fill cache beyond max size
      for (let i = 0; i < maxSize + 5; i++) {
        const cacheKey = `note-${i}:context`;
        // @ts-expect-error - accessing private cache for testing
        ghostTextStore.cache.set(cacheKey, `suggestion-${i}`);
      }

      // Should evict oldest entries
      // @ts-expect-error - accessing private cache
      expect(ghostTextStore.cache.size).toBeLessThanOrEqual(maxSize);
    });
  });

  describe('error handling', () => {
    it('should set error on fetch failure', async () => {
      const mockClient = {
        connect: vi.fn().mockResolvedValue(undefined),
        abort: vi.fn(),
        isConnected: false,
        resetRetries: vi.fn(),
      } as unknown as SSEClient;

      const { SSEClient } = await import('@/lib/sse-client');
      vi.mocked(SSEClient).mockImplementation(
        (options) =>
          ({
            ...mockClient,
            connect: async () => {
              options.onError?.(new Error('Network error'));
            },
          }) as unknown as SSEClient
      );

      await ghostTextStore.requestSuggestion('note-123', 'Hello ', 6);

      // Wait for debounce
      await new Promise((resolve) => setTimeout(resolve, 600));

      await when(() => ghostTextStore.error !== null);

      expect(ghostTextStore.error).toBe('Network error');
      expect(ghostTextStore.isLoading).toBe(false);
    });
  });

  describe('MobX reactivity', () => {
    it('should trigger reactions on suggestion change', async () => {
      const reactions: string[] = [];

      // Set up autorun to track suggestion changes
      const { autorun } = await import('mobx');
      const dispose = autorun(() => {
        reactions.push(ghostTextStore.suggestion);
      });

      ghostTextStore.suggestion = 'test 1';
      ghostTextStore.suggestion = 'test 2';

      expect(reactions).toEqual(['', 'test 1', 'test 2']);

      dispose();
    });

    it('should trigger reactions on isLoading change', async () => {
      const loadingStates: boolean[] = [];

      const { autorun } = await import('mobx');
      const dispose = autorun(() => {
        loadingStates.push(ghostTextStore.isLoading);
      });

      // @ts-expect-error - setting private client for testing
      ghostTextStore.client = {} as SSEClient;
      ghostTextStore.isLoading = true;
      ghostTextStore.isLoading = false;

      expect(loadingStates).toEqual([false, true, false]);

      dispose();
    });
  });
});
