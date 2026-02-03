/**
 * Phase 1 SDK Features (T57-T59) Unit Tests
 *
 * Tests for:
 * - T57: MemoryUpdateEvent type guard + handleMemoryUpdate (stores lastMemoryUpdate)
 * - T58: CitationEvent type guard + handleCitation (buffers citations via pending buffer)
 * - T59: ToolInputDeltaEvent type guard + handleToolInputDelta (progressive input via pending buffer)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PilotSpaceStore } from '../PilotSpaceStore';
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';
import { isCitationEvent, isMemoryUpdateEvent, isToolInputDeltaEvent } from '../types/events';
import type { CitationEvent, MemoryUpdateEvent, ToolInputDeltaEvent } from '../types/events';

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

describe('Phase 1 SDK Features (T57-T59)', () => {
  let store: PilotSpaceStore;
  let handler: PilotSpaceStreamHandler;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    store.setWorkspaceId('test-workspace-id');
    handler = new PilotSpaceStreamHandler(store);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ========================================
  // T58: Citation Event
  // ========================================

  describe('isCitationEvent type guard', () => {
    it('should return true for valid citation event', () => {
      const event = {
        type: 'citation' as const,
        data: {
          messageId: 'msg-1',
          citations: [],
        },
      };

      expect(isCitationEvent(event)).toBe(true);
    });

    it('should return false for non-citation event', () => {
      const event = {
        type: 'text_delta' as const,
        data: { delta: 'hello' },
      };

      expect(isCitationEvent(event)).toBe(false);
    });
  });

  // ========================================
  // T57: Memory Update Event
  // ========================================

  describe('isMemoryUpdateEvent type guard', () => {
    it('should return true for valid memory_update event', () => {
      const event = {
        type: 'memory_update' as const,
        data: {
          operation: 'write',
          key: 'user-pref',
          value: 'dark-mode',
        },
      };

      expect(isMemoryUpdateEvent(event)).toBe(true);
    });

    it('should return false for non-memory_update event', () => {
      const event = {
        type: 'text_delta' as const,
        data: { delta: 'hello' },
      };

      expect(isMemoryUpdateEvent(event)).toBe(false);
    });
  });

  // ========================================
  // T59: Tool Input Delta Event
  // ========================================

  describe('isToolInputDeltaEvent type guard', () => {
    it('should return true for valid tool_input_delta event', () => {
      const event = {
        type: 'tool_input_delta' as const,
        data: {
          toolUseId: 'tc-1',
          toolName: 'extract_issues',
          inputDelta: '{"note',
        },
      };

      expect(isToolInputDeltaEvent(event)).toBe(true);
    });

    it('should return false for non-tool_input_delta event', () => {
      const event = {
        type: 'text_delta' as const,
        data: { delta: 'hello' },
      };

      expect(isToolInputDeltaEvent(event)).toBe(false);
    });
  });

  // ========================================
  // T58: handleCitation (pending buffer)
  // ========================================

  describe('handleCitation', () => {
    it('should buffer citations via addPendingCitations', () => {
      const citationEvent: CitationEvent = {
        type: 'citation',
        data: {
          messageId: 'msg-1',
          citations: [
            {
              sourceType: 'document',
              sourceId: 'note-123',
              sourceTitle: 'Test Note',
              citedText: 'some text',
            },
          ],
        },
      };

      handler.handleCitation(citationEvent);

      const buffered = store.consumePendingCitations();
      expect(buffered).toHaveLength(1);
      expect(buffered?.[0]).toEqual({
        sourceType: 'document',
        sourceId: 'note-123',
        sourceTitle: 'Test Note',
        citedText: 'some text',
      });
    });

    it('should accumulate multiple citation events in buffer', () => {
      const citationEvent1: CitationEvent = {
        type: 'citation',
        data: {
          messageId: 'msg-1',
          citations: [
            {
              sourceType: 'document',
              sourceId: 'note-100',
              sourceTitle: 'First Note',
              citedText: 'first cited text',
            },
          ],
        },
      };

      const citationEvent2: CitationEvent = {
        type: 'citation',
        data: {
          messageId: 'msg-1',
          citations: [
            {
              sourceType: 'issue',
              sourceId: 'issue-456',
              sourceTitle: 'Bug Report',
              citedText: 'second cited text',
            },
          ],
        },
      };

      handler.handleCitation(citationEvent1);
      handler.handleCitation(citationEvent2);

      const buffered = store.consumePendingCitations();
      expect(buffered).toHaveLength(2);
      expect(buffered?.[0].sourceId).toBe('note-100');
      expect(buffered?.[1].sourceId).toBe('issue-456');
    });

    it('should not crash and buffer is empty when no citations sent', () => {
      // consumePendingCitations should return undefined when buffer is empty
      const buffered = store.consumePendingCitations();
      expect(buffered).toBeUndefined();
    });

    it('should clear buffer after consumePendingCitations', () => {
      const citationEvent: CitationEvent = {
        type: 'citation',
        data: {
          messageId: 'msg-1',
          citations: [
            {
              sourceType: 'document',
              sourceId: 'note-999',
              sourceTitle: 'Missing Note',
              citedText: 'text',
            },
          ],
        },
      };

      handler.handleCitation(citationEvent);

      // First consume drains the buffer
      const first = store.consumePendingCitations();
      expect(first).toHaveLength(1);

      // Second consume returns undefined (buffer cleared)
      const second = store.consumePendingCitations();
      expect(second).toBeUndefined();
    });
  });

  // ========================================
  // T59: handleToolInputDelta (pending buffer)
  // ========================================

  describe('handleToolInputDelta', () => {
    it('should append input delta to matching pending tool call via partialInput', () => {
      // Seed a pending tool call in the buffer
      store.addPendingToolCall({
        id: 'tc-1',
        name: 'extract_issues',
        input: {} as Record<string, unknown>,
        status: 'pending',
      });

      const delta1: ToolInputDeltaEvent = {
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-1',
          toolName: 'extract_issues',
          inputDelta: '{"note_id":',
        },
      };

      const delta2: ToolInputDeltaEvent = {
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-1',
          toolName: 'extract_issues',
          inputDelta: '"note-123"}',
        },
      };

      handler.handleToolInputDelta(delta1);
      handler.handleToolInputDelta(delta2);

      const tc = store.findPendingToolCall('tc-1');
      expect(tc?.partialInput).toBe('{"note_id":"note-123"}');
    });

    it('should initialize partialInput from undefined on first delta', () => {
      store.addPendingToolCall({
        id: 'tc-2',
        name: 'summarize_note',
        input: {} as Record<string, unknown>,
        status: 'pending',
      });

      const delta: ToolInputDeltaEvent = {
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-2',
          toolName: 'summarize_note',
          inputDelta: '{"text":"hello"}',
        },
      };

      handler.handleToolInputDelta(delta);

      const tc = store.findPendingToolCall('tc-2');
      expect(tc?.partialInput).toBe('{"text":"hello"}');
    });

    it('should not crash when no matching pending tool call exists', () => {
      store.addPendingToolCall({
        id: 'tc-other',
        name: 'other_tool',
        input: {} as Record<string, unknown>,
        status: 'pending',
      });

      const delta: ToolInputDeltaEvent = {
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-nonexistent',
          toolName: 'extract_issues',
          inputDelta: '{"data":true}',
        },
      };

      expect(() => handler.handleToolInputDelta(delta)).not.toThrow();
    });

    it('should not crash when pending buffer is empty', () => {
      const delta: ToolInputDeltaEvent = {
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-1',
          toolName: 'extract_issues',
          inputDelta: '{}',
        },
      };

      expect(() => handler.handleToolInputDelta(delta)).not.toThrow();
    });
  });

  // ========================================
  // T57: handleMemoryUpdate
  // ========================================

  describe('handleMemoryUpdate', () => {
    it('should store lastMemoryUpdate for write operation', () => {
      const event: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'write',
          key: 'user-preference',
          value: { theme: 'dark' },
        },
      };

      handler.handleMemoryUpdate(event);

      expect(store.lastMemoryUpdate).toEqual(event.data);
    });

    it('should store lastMemoryUpdate for read operation', () => {
      const event: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'read',
          key: 'user-preference',
        },
      };

      handler.handleMemoryUpdate(event);

      expect(store.lastMemoryUpdate).toEqual(event.data);
    });

    it('should store lastMemoryUpdate for delete operation', () => {
      const event: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'delete',
          key: 'user-preference',
        },
      };

      handler.handleMemoryUpdate(event);

      expect(store.lastMemoryUpdate).toEqual(event.data);
    });

    it('should overwrite previous lastMemoryUpdate with latest event', () => {
      const event1: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'write',
          key: 'context',
          value: 'first',
        },
      };

      const event2: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'write',
          key: 'context',
          value: 'second',
        },
      };

      handler.handleMemoryUpdate(event1);
      handler.handleMemoryUpdate(event2);

      expect(store.lastMemoryUpdate).toEqual(event2.data);
    });

    it('should not mutate messages or error state', () => {
      const messagesBefore = store.messages.length;
      const errorBefore = store.error;

      const event: MemoryUpdateEvent = {
        type: 'memory_update',
        data: {
          operation: 'write',
          key: 'context',
          value: 'test',
        },
      };

      handler.handleMemoryUpdate(event);

      expect(store.messages.length).toBe(messagesBefore);
      expect(store.error).toBe(errorBefore);
      expect(store.lastMemoryUpdate).toEqual(event.data);
    });
  });

  // ========================================
  // SSE Event Dispatch Integration
  // ========================================

  describe('handleSSEEvent dispatch', () => {
    it('should route citation event to buffer via handleCitation', () => {
      handler.handleSSEEvent({
        type: 'citation',
        data: {
          messageId: 'msg-dispatch',
          citations: [
            {
              sourceType: 'document',
              sourceId: 'doc-1',
              sourceTitle: 'Doc',
              citedText: 'cited',
            },
          ],
        },
      });

      const buffered = store.consumePendingCitations();
      expect(buffered).toHaveLength(1);
      expect(buffered?.[0].sourceId).toBe('doc-1');
    });

    it('should route tool_input_delta event to pending buffer with partialInput', () => {
      // Seed pending tool call in buffer
      store.addPendingToolCall({
        id: 'tc-dispatch',
        name: 'test_tool',
        input: {} as Record<string, unknown>,
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: {
          toolUseId: 'tc-dispatch',
          toolName: 'test_tool',
          inputDelta: '{"key":"val"}',
        },
      });

      const tc = store.findPendingToolCall('tc-dispatch');
      expect(tc?.partialInput).toBe('{"key":"val"}');
    });

    it('should route memory_update event to store lastMemoryUpdate', () => {
      const memoryData = {
        operation: 'write' as const,
        key: 'pref',
        value: 42,
      };

      handler.handleSSEEvent({
        type: 'memory_update',
        data: memoryData,
      });

      expect(store.lastMemoryUpdate).toEqual(memoryData);
    });
  });
});
