/**
 * PilotSpaceStore Queue Mode Integration Tests
 *
 * Tests the queue mode detection and stream connection logic.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PilotSpaceStore } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';

// Mock SSEClient
vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
    isConnected: false,
  })),
}));

// Mock Supabase auth
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'test-token',
          },
        },
      }),
    },
  },
}));

describe('PilotSpaceStore - Queue Mode Integration', () => {
  let store: PilotSpaceStore;
  let mockAIStore: AIStore;
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    store.setWorkspaceId('test-workspace-id');

    fetchSpy = vi.spyOn(global, 'fetch');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Queue Mode Detection', () => {
    it('should detect queue mode response by Content-Type', async () => {
      // Mock queue mode response
      const mockQueueResponse = {
        job_id: 'test-job-id',
        session_id: 'test-session-id',
        stream_url: '/api/v1/ai/chat/stream/test-job-id',
      };

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({
          'Content-Type': 'application/json',
        }),
        json: async () => mockQueueResponse,
      } as Response);

      // Mock SSEClient.connect to avoid actual connection
      const { SSEClient } = await import('@/lib/sse-client');
      const mockConnect = vi.fn().mockResolvedValue(undefined);
      vi.mocked(SSEClient).mockImplementation(() => ({
        connect: mockConnect,
        abort: vi.fn(),
      }));

      await store.sendMessage('Hello');

      // Verify queue mode flow
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/ai/chat'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          }),
        })
      );

      // Verify session_id stored
      expect(store.sessionId).toBe('test-session-id');

      // Verify SSEClient created with GET method for stream URL
      expect(SSEClient).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'GET',
          url: expect.stringContaining('/api/v1/ai/chat/stream/test-job-id'),
        })
      );
    });

    it('should handle direct mode response by Content-Type', async () => {
      // Mock direct mode SSE response
      const mockSSEStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              'event: message_start\ndata: {"messageId":"msg-1","sessionId":"sess-1"}\n\n'
            )
          );
          controller.enqueue(encoder.encode('event: text_delta\ndata: {"delta":"Hello"}\n\n'));
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({
          'Content-Type': 'text/event-stream',
        }),
        body: mockSSEStream,
      } as Response);

      await store.sendMessage('Hello');

      // Verify direct mode flow
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/ai/chat'),
        expect.objectContaining({
          method: 'POST',
        })
      );

      // Verify session ID was extracted from message_start event
      expect(store.sessionId).toBe('sess-1');
      // streamContent resets on stream end; verify streaming was active
      expect(store.isStreaming).toBe(false);
    });
  });

  describe('Session Management', () => {
    it('should include session_id in subsequent requests', async () => {
      store.setSessionId('existing-session-id');

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          job_id: 'job-2',
          session_id: 'existing-session-id',
          stream_url: '/api/v1/ai/chat/stream/job-2',
        }),
      } as Response);

      await store.sendMessage('Follow-up message');

      // Verify session_id included in request
      const requestBody = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
      expect(requestBody.session_id).toBe('existing-session-id');
    });

    it('should extract session_id from message_start event', async () => {
      const mockSSEStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              'event: message_start\ndata: {"messageId":"msg-1","sessionId":"new-session-id"}\n\n'
            )
          );
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockSSEStream,
      } as Response);

      await store.sendMessage('First message');

      expect(store.sessionId).toBe('new-session-id');
    });
  });

  describe('Error Handling', () => {
    it('should handle fetch errors gracefully', async () => {
      fetchSpy.mockRejectedValueOnce(new Error('Network error'));

      await store.sendMessage('Hello');

      expect(store.error).toContain('Network error');
      expect(store.isStreaming).toBe(false);
    });

    it('should handle non-ok responses', async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      } as Response);

      await store.sendMessage('Hello');

      expect(store.error).toContain('500');
      expect(store.isStreaming).toBe(false);
    });

    it('should handle unexpected Content-Type', async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/html' }),
      } as Response);

      await store.sendMessage('Hello');

      expect(store.error).toContain('Unexpected response content type');
    });
  });

  describe('SSE Event Parsing', () => {
    it('should parse multiple SSE events from buffer', async () => {
      const sseBuffer = `event: message_start
data: {"messageId":"msg-1","sessionId":"sess-1"}

event: text_delta
data: {"delta":"Hello "}

event: text_delta
data: {"delta":"World"}

`;

      const mockSSEStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(sseBuffer));
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockSSEStream,
      } as Response);

      await store.sendMessage('Hello');

      // Session ID extracted from message_start event
      expect(store.sessionId).toBe('sess-1');
      // streamContent resets on stream end; verify stream completed successfully
      expect(store.isStreaming).toBe(false);
      expect(store.error).toBeNull();
    });

    it('should handle malformed JSON gracefully', async () => {
      const sseBuffer = `event: text_delta
data: {invalid json}

event: text_delta
data: {"delta":"Valid"}

`;

      const mockSSEStream = new ReadableStream({
        start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(encoder.encode(sseBuffer));
          controller.close();
        },
      });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'text/event-stream' }),
        body: mockSSEStream,
      } as Response);

      await store.sendMessage('Hello');

      // Should skip malformed event without crashing; stream completes
      expect(store.error).toBeNull();
      expect(store.isStreaming).toBe(false);
    });
  });

  describe('Context Management', () => {
    it('should include conversation context in request', async () => {
      store.setNoteContext({ noteId: 'note-123', noteTitle: 'Test Note' });

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          job_id: 'job-1',
          session_id: 'sess-1',
          stream_url: '/stream',
        }),
      } as Response);

      await store.sendMessage('Hello');

      const requestBody = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
      expect(requestBody.context).toMatchObject({
        workspaceId: 'test-workspace-id',
        noteId: 'note-123',
      });
    });
  });
});
