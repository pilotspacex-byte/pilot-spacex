/**
 * GhostTextStore Tests (T130)
 * Tests for MobX store managing AI-powered text suggestions.
 * Store uses fetch + JSON (not SSE) per backend ghost_text.py contract.
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { autorun } from 'mobx';
import { GhostTextStore } from '@/stores/ai/GhostTextStore';
import { AIStore } from '@/stores/ai/AIStore';

// Mock Supabase auth
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

// Mock aiApi
vi.mock('@/services/api/ai', () => ({
  aiApi: {
    getGhostTextUrl: (_noteId: string) => 'http://localhost:8000/api/v1/ai/ghost-text',
  },
}));

describe('GhostTextStore', () => {
  let aiStore: AIStore;
  let ghostTextStore: GhostTextStore;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let fetchSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    aiStore = new AIStore();
    ghostTextStore = aiStore.ghostText;
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ suggestion: '', confidence: 0.5, cached: false }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  afterEach(() => {
    ghostTextStore.abort();
    fetchSpy.mockRestore();
  });

  describe('initialization', () => {
    it('should initialize with default state', () => {
      expect(ghostTextStore.suggestion).toBe('');
      expect(ghostTextStore.isLoading).toBe(false);
      expect(ghostTextStore.isEnabled).toBe(true);
      expect(ghostTextStore.error).toBeNull();
      expect(ghostTextStore.errorCode).toBeNull();
    });

    it('should respect AI store global enabled state', () => {
      aiStore.setGloballyEnabled(false);
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');
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
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should not request when globally disabled', () => {
      aiStore.setGloballyEnabled(false);
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should return cached suggestion if available', () => {
      const cacheKey = 'note-123:Hello :Hello ';
      // @ts-expect-error - accessing private cache for testing
      ghostTextStore.cache.set(cacheKey, 'world');

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      expect(ghostTextStore.suggestion).toBe('world');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should fetch suggestion via JSON endpoint', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'world', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      // Wait for debounce (0ms) + async import + auth + fetch chain
      await vi.waitFor(() => {
        expect(ghostTextStore.suggestion).toBe('world');
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/ghost-text',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ context: 'Hello ', prefix: 'Hello ', workspace_id: 'ws-1' }),
        })
      );
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should debounce multiple requests', async () => {
      fetchSpy.mockResolvedValue(
        new Response(JSON.stringify({ suggestion: 'rld', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');
      ghostTextStore.requestSuggestion('note-123', 'Hello w', 'Hello w', 'ws-1');
      ghostTextStore.requestSuggestion('note-123', 'Hello wo', 'Hello wo', 'ws-1');

      // Only last request should trigger after debounce
      expect(ghostTextStore.isLoading).toBe(false);

      // Wait for the debounced fetch to complete
      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      });

      // Verify it was called with the LAST request's data
      expect(fetchSpy).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/ai/ghost-text',
        expect.objectContaining({
          body: JSON.stringify({ context: 'Hello wo', prefix: 'Hello wo', workspace_id: 'ws-1' }),
        })
      );
    });

    it('should cache successful suggestions', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'world', confidence: 0.9, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      // Wait for fetch chain to complete
      await vi.waitFor(() => {
        expect(ghostTextStore.suggestion).toBe('world');
      });

      // Check cache - key includes prefix now
      const cacheKey = 'note-123:Hello :Hello ';
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
    it('should abort current request and reset loading', () => {
      ghostTextStore.isLoading = true;
      ghostTextStore.abort();
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should clear debounce timer', () => {
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      // @ts-expect-error - accessing private debounceTimer
      expect(ghostTextStore.debounceTimer).not.toBeNull();

      ghostTextStore.abort();

      // @ts-expect-error - accessing private debounceTimer
      expect(ghostTextStore.debounceTimer).toBeNull();
    });
  });

  describe('error handling', () => {
    it('should set error on fetch failure', async () => {
      fetchSpy.mockRejectedValueOnce(new Error('Network error'));

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.error).toBe('Network error');
      });
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should silently handle rate limit (429)', async () => {
      fetchSpy.mockResolvedValueOnce(new Response('Rate limit exceeded', { status: 429 }));

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalled();
      });
      // Allow async chain to settle
      await vi.waitFor(() => {
        expect(ghostTextStore.isLoading).toBe(false);
      });
      expect(ghostTextStore.error).toBeNull();
    });

    it('should set error on non-429 HTTP failure', async () => {
      fetchSpy.mockResolvedValueOnce(new Response('Server error', { status: 500 }));

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.error).toBe('Ghost text failed (500)');
      });
      expect(ghostTextStore.isLoading).toBe(false);
      expect(ghostTextStore.errorCode).toBe(500);
    });

    it('should set 402 errorCode and backend detail on missing API key', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'No Anthropic API key configured' }), {
          status: 402,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.errorCode).toBe(402);
      });
      expect(ghostTextStore.error).toBe('No Anthropic API key configured');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should set 403 errorCode and backend detail on unauthorized workspace', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'User is not a member of this workspace' }), {
          status: 403,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.errorCode).toBe(403);
      });
      expect(ghostTextStore.error).toBe('User is not a member of this workspace');
      expect(ghostTextStore.isLoading).toBe(false);
    });

    it('should use fallback message for 402 with non-JSON body', async () => {
      fetchSpy.mockResolvedValueOnce(new Response('Payment Required', { status: 402 }));

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.errorCode).toBe(402);
      });
      expect(ghostTextStore.error).toBe(
        'No API key configured. Add one in Settings > AI Providers.'
      );
    });

    it('should clear errorCode on abort', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'No Anthropic API key configured' }), {
          status: 402,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');
      await vi.waitFor(() => {
        expect(ghostTextStore.errorCode).toBe(402);
      });

      ghostTextStore.abort();
      expect(ghostTextStore.errorCode).toBeNull();
      expect(ghostTextStore.error).toBeNull();
    });

    it('should clear stale error on cache hit', () => {
      // Simulate prior error state
      ghostTextStore.error = 'Ghost text failed (500)';
      ghostTextStore.errorCode = 500;

      // Populate cache
      const cacheKey = 'note-123:Hello :Hello ';
      // @ts-expect-error - accessing private cache for testing
      ghostTextStore.cache.set(cacheKey, 'world');

      // Cache hit should clear stale error
      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      expect(ghostTextStore.suggestion).toBe('world');
      expect(ghostTextStore.error).toBeNull();
      expect(ghostTextStore.errorCode).toBeNull();
    });
  });

  describe('confidence gating', () => {
    it('should suppress suggestion when confidence < 0.5', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'test', confidence: 0.3, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.isLoading).toBe(false);
      });
      expect(ghostTextStore.suggestion).toBe('');
    });

    it('should show suggestion when confidence >= 0.5', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'test', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.suggestion).toBe('test');
      });
    });

    it('should show suggestion at exact confidence boundary (0.5)', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'boundary', confidence: 0.5, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(ghostTextStore.suggestion).toBe('boundary');
      });
    });
  });

  describe('context truncation', () => {
    it('should truncate context to 500 chars and prefix to 200 chars', async () => {
      const longContext = 'a'.repeat(1000);
      const longPrefix = 'b'.repeat(400);

      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'ok', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', longContext, longPrefix, 'ws-1');

      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      });

      const call = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((call[1] as RequestInit & { body?: string })?.body as string);
      expect(body.context).toHaveLength(500);
      expect(body.prefix).toHaveLength(200);
      expect(body.context).toBe('a'.repeat(500));
      expect(body.prefix).toBe('b'.repeat(200));
    });
  });

  describe('blockType and noteTitle (T003)', () => {
    it('should include block_type in request body when provided', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'ok', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1', 'heading');

      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      });

      const call = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((call[1] as RequestInit & { body?: string })?.body as string);
      expect(body.block_type).toBe('heading');
    });

    it('should include note_title in request body when provided', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'ok', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion(
        'note-123',
        'Hello ',
        'Hello ',
        'ws-1',
        'paragraph',
        'My Note Title'
      );

      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      });

      const call = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((call[1] as RequestInit & { body?: string })?.body as string);
      expect(body.note_title).toBe('My Note Title');
      expect(body.block_type).toBe('paragraph');
    });

    it('should omit block_type and note_title when not provided', async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ suggestion: 'ok', confidence: 0.8, cached: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );

      ghostTextStore.requestSuggestion('note-123', 'Hello ', 'Hello ', 'ws-1');

      await vi.waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledTimes(1);
      });

      const call = fetchSpy.mock.calls[0]!;
      const body = JSON.parse((call[1] as RequestInit & { body?: string })?.body as string);
      expect(body.block_type).toBeUndefined();
      expect(body.note_title).toBeUndefined();
    });
  });

  describe('MobX reactivity', () => {
    it('should trigger reactions on suggestion change', () => {
      const reactions: string[] = [];

      const dispose = autorun(() => {
        reactions.push(ghostTextStore.suggestion);
      });

      ghostTextStore.suggestion = 'test 1';
      ghostTextStore.suggestion = 'test 2';

      expect(reactions).toEqual(['', 'test 1', 'test 2']);
      dispose();
    });

    it('should trigger reactions on isLoading change', () => {
      const loadingStates: boolean[] = [];

      const dispose = autorun(() => {
        loadingStates.push(ghostTextStore.isLoading);
      });

      ghostTextStore.isLoading = true;
      ghostTextStore.isLoading = false;

      expect(loadingStates).toEqual([false, true, false]);
      dispose();
    });
  });
});
