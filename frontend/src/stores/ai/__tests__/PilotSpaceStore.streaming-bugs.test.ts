/**
 * Tests for streaming buffer fixes (T63-T66).
 *
 * During SSE streaming, the assistant message does not exist in messages[]
 * until handleTextComplete (message_stop). Previously, handlers like
 * handleToolUseStart, handleCitation, handleToolInputDelta, and
 * handleToolResult searched messages[] and silently dropped data.
 *
 * These tests verify the pending buffer pattern: events that arrive before
 * message_stop are buffered, then consumed into the finalized message.
 *
 * @module stores/ai/__tests__/PilotSpaceStore.streaming-bugs.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
    isConnected: false,
  })),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } },
      }),
    },
  },
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';

describe('Streaming Buffer Fixes (T63-T66)', () => {
  let store: PilotSpaceStore;
  let handler: PilotSpaceStreamHandler;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    handler = new PilotSpaceStreamHandler(store);
  });

  it('tool_use event during streaming buffers tool call', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'extract_issues',
        toolInput: { noteId: 'n1' },
      },
    });

    const pending = store.findPendingToolCall('tc-1');
    expect(pending).toBeDefined();
    expect(pending?.name).toBe('extract_issues');
    expect(pending?.status).toBe('pending');
    expect(store.messages).toHaveLength(0);
  });

  it('tool_result event during streaming updates pending tool call', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'extract_issues',
        toolInput: { noteId: 'n1' },
      },
    });

    handler.handleSSEEvent({
      type: 'tool_result',
      data: {
        toolCallId: 'tc-1',
        status: 'completed',
        output: { result: 'ok' },
      },
    });

    const pending = store.findPendingToolCall('tc-1');
    expect(pending).toBeDefined();
    expect(pending?.status).toBe('completed');
    expect(pending?.output).toEqual({ result: 'ok' });
  });

  it('tool_input_delta during streaming accumulates on partialInput', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'update_note_block',
        toolInput: {},
      },
    });

    handler.handleSSEEvent({
      type: 'tool_input_delta',
      data: {
        toolUseId: 'tc-1',
        toolName: 'update_note_block',
        inputDelta: '{"note',
      },
    });

    handler.handleSSEEvent({
      type: 'tool_input_delta',
      data: {
        toolUseId: 'tc-1',
        toolName: 'update_note_block',
        inputDelta: '_id":"n1"}',
      },
    });

    const pending = store.findPendingToolCall('tc-1');
    expect(pending).toBeDefined();
    expect(pending?.partialInput).toBe('{"note_id":"n1"}');
    // Original input object remains unchanged
    expect(pending?.input).toEqual({});
  });

  it('citation event during streaming buffers citations', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    const citations = [
      {
        sourceType: 'note',
        sourceId: 'note-1',
        sourceTitle: 'Architecture Notes',
        citedText: 'Use event-driven architecture',
      },
    ];

    handler.handleSSEEvent({
      type: 'citation',
      data: { messageId: 'msg-1', citations },
    });

    const consumed = store.consumePendingCitations();
    expect(consumed).toBeDefined();
    expect(consumed).toHaveLength(1);
    expect(consumed![0]!.sourceTitle).toBe('Architecture Notes');
    expect(store.messages).toHaveLength(0);
  });

  it('message_stop consumes all pending buffers into finalized message', () => {
    // 1. message_start
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    // 2. text_delta
    handler.handleSSEEvent({
      type: 'text_delta',
      data: { messageId: 'msg-1', delta: 'Hello world' },
    });

    // 3. tool_use
    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'extract_issues',
        toolInput: { noteId: 'n1' },
      },
    });

    // 4. tool_result
    handler.handleSSEEvent({
      type: 'tool_result',
      data: {
        toolCallId: 'tc-1',
        status: 'completed',
        output: { issues: [] },
      },
    });

    // 5. citation
    handler.handleSSEEvent({
      type: 'citation',
      data: {
        messageId: 'msg-1',
        citations: [
          {
            sourceType: 'note',
            sourceId: 'note-1',
            sourceTitle: 'Sprint Plan',
            citedText: 'Deliver by Friday',
          },
        ],
      },
    });

    // 6. message_stop
    handler.handleSSEEvent({
      type: 'message_stop',
      data: {
        messageId: 'msg-1',
        stopReason: 'end_turn',
        usage: { inputTokens: 100, outputTokens: 50, totalTokens: 150 },
        costUsd: 0.003,
      },
    });

    // Verify finalized message
    expect(store.messages).toHaveLength(1);
    const msg = store.messages[0]!;
    expect(msg.id).toBe('msg-1');
    expect(msg.content).toBe('Hello world');
    expect(msg.role).toBe('assistant');

    // Tool calls consumed from pending buffer
    expect(msg.toolCalls).toBeDefined();
    expect(msg.toolCalls).toHaveLength(1);
    expect(msg.toolCalls![0]!.id).toBe('tc-1');
    expect(msg.toolCalls![0]!.status).toBe('completed');

    // Citations consumed from pending buffer
    expect(msg.citations).toBeDefined();
    expect(msg.citations).toHaveLength(1);
    expect(msg.citations![0]!.sourceTitle).toBe('Sprint Plan');

    // Pending buffers are empty after consumption
    expect(store.consumePendingToolCalls()).toBeUndefined();
    expect(store.consumePendingCitations()).toBeUndefined();
  });

  it('tool_audit during streaming updates pending tool call duration', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'summarize_note',
        toolInput: { noteId: 'n1' },
      },
    });

    handler.handleSSEEvent({
      type: 'tool_audit',
      data: {
        toolUseId: 'tc-1',
        toolName: 'summarize_note',
        inputSummary: '{"noteId":"n1"}',
        outputSummary: 'Summary generated',
        durationMs: 150,
      },
    });

    const pending = store.findPendingToolCall('tc-1');
    expect(pending).toBeDefined();
    expect(pending?.durationMs).toBe(150);
  });

  it('multiple tool calls and citations buffered correctly', () => {
    handler.handleSSEEvent({
      type: 'message_start',
      data: { messageId: 'msg-1', sessionId: 'sess-1' },
    });

    // Two tool_use events
    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-1',
        toolName: 'summarize_note',
        toolInput: { noteId: 'n1' },
      },
    });

    handler.handleSSEEvent({
      type: 'tool_use',
      data: {
        toolCallId: 'tc-2',
        toolName: 'extract_issues',
        toolInput: { noteId: 'n2' },
      },
    });

    // Two citation events (separate batches)
    handler.handleSSEEvent({
      type: 'citation',
      data: {
        messageId: 'msg-1',
        citations: [
          {
            sourceType: 'note',
            sourceId: 'note-1',
            sourceTitle: 'Design Doc',
            citedText: 'Architecture decision',
          },
        ],
      },
    });

    handler.handleSSEEvent({
      type: 'citation',
      data: {
        messageId: 'msg-1',
        citations: [
          {
            sourceType: 'issue',
            sourceId: 'issue-1',
            sourceTitle: 'PS-42',
            citedText: 'Fix login bug',
          },
        ],
      },
    });

    // message_stop finalizes
    handler.handleSSEEvent({
      type: 'message_stop',
      data: {
        messageId: 'msg-1',
        stopReason: 'end_turn',
      },
    });

    expect(store.messages).toHaveLength(1);
    const msg = store.messages[0]!;

    // Both tool calls present
    expect(msg.toolCalls).toHaveLength(2);
    expect(msg.toolCalls![0]!.id).toBe('tc-1');
    expect(msg.toolCalls![1]!.id).toBe('tc-2');

    // Both citation batches merged
    expect(msg.citations).toHaveLength(2);
    expect(msg.citations![0]!.sourceTitle).toBe('Design Doc');
    expect(msg.citations![1]!.sourceTitle).toBe('PS-42');
  });
});
