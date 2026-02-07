/**
 * Unit tests for PilotSpaceStreamHandler.
 *
 * Tests SSE event dispatch, stream parsing, and auth header resolution.
 *
 * @module stores/ai/__tests__/PilotSpaceStreamHandler.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token-123' } },
      }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation(() => ({
    connect: vi.fn().mockResolvedValue(undefined),
    abort: vi.fn(),
  })),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';
import type { SSEEvent } from '../types/events';

describe('PilotSpaceStreamHandler', () => {
  let store: PilotSpaceStore;
  let handler: PilotSpaceStreamHandler;

  beforeEach(() => {
    const mockAIStore = {} as AIStore;
    store = new PilotSpaceStore(mockAIStore);
    handler = new PilotSpaceStreamHandler(store);
  });

  describe('parseSSEBuffer', () => {
    it('should parse a single event from buffer', () => {
      const buffer = 'event: text_delta\ndata: {"delta":"Hello"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(1);
      expect(events[0]!.type).toBe('text_delta');
      expect(events[0]!.data).toEqual({ delta: 'Hello' });
    });

    it('should parse multiple events from buffer', () => {
      const buffer =
        'event: message_start\ndata: {"messageId":"m1","sessionId":"s1"}\n\n' +
        'event: text_delta\ndata: {"delta":"Hi"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(2);
      expect(events[0]!.type).toBe('message_start');
      expect(events[1]!.type).toBe('text_delta');
    });

    it('should skip events with invalid JSON', () => {
      const buffer =
        'event: text_delta\ndata: {invalid json}\n\n' +
        'event: text_delta\ndata: {"delta":"Valid"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(1);
      expect(events[0]!.data).toEqual({ delta: 'Valid' });
    });

    it('should skip blocks without event type', () => {
      const buffer = 'data: {"delta":"no-type"}\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(0);
    });

    it('should skip blocks without data', () => {
      const buffer = 'event: text_delta\n\n';
      const events = handler.parseSSEBuffer(buffer);

      expect(events).toHaveLength(0);
    });

    it('should return empty array for empty buffer', () => {
      expect(handler.parseSSEBuffer('')).toHaveLength(0);
      expect(handler.parseSSEBuffer('\n\n')).toHaveLength(0);
    });
  });

  describe('handleSSEEvent routing', () => {
    it('should route message_start and set session ID', () => {
      const event: SSEEvent = {
        type: 'message_start',
        data: { messageId: 'msg-1', sessionId: 'sess-1' },
      };

      handler.handleSSEEvent(event);

      expect(store.sessionId).toBe('sess-1');
      expect(store.streamingState.currentMessageId).toBe('msg-1');
      expect(store.streamingState.isStreaming).toBe(true);
    });

    it('should route text_delta and accumulate content', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Hello ' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'World' },
      });

      expect(store.streamingState.streamContent).toBe('Hello World');
    });

    it('should route thinking_delta and track thinking state', () => {
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Analyzing...' },
      });

      expect(store.streamingState.isThinking).toBe(true);
      expect(store.streamingState.thinkingContent).toBe('Analyzing...');
      expect(store.streamingState.thinkingStartedAt).toBeTruthy();
    });

    it('should end thinking when text_delta arrives after thinking', () => {
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...' },
      });
      expect(store.streamingState.isThinking).toBe(true);

      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Response' },
      });
      expect(store.streamingState.isThinking).toBe(false);
    });

    it('should route tool_use and buffer as pending tool call', () => {
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-1',
          toolName: 'extract_issues',
          toolInput: { noteId: 'n1' },
        },
      });

      // Tool call should be in pending buffer, not in messages[]
      const pending = store.findPendingToolCall('tc-1');
      expect(pending).toBeDefined();
      expect(pending?.name).toBe('extract_issues');
      expect(pending?.status).toBe('pending');
    });

    it('should route tool_result and update pending tool call status', () => {
      // Buffer a tool call first (simulates tool_use during streaming)
      store.addPendingToolCall({
        id: 'tc-1',
        name: 'extract_issues',
        input: {},
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-1',
          status: 'completed',
          output: { issues: [] },
        },
      });

      const pending = store.findPendingToolCall('tc-1');
      expect(pending?.status).toBe('completed');
      expect(pending?.output).toEqual({ issues: [] });
    });

    it('should route tool_result and update finalized message tool call', () => {
      // Tool call already finalized in messages[]
      store.addMessage({
        id: 'msg-1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        toolCalls: [{ id: 'tc-1', name: 'extract_issues', input: {}, status: 'pending' }],
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-1',
          status: 'completed',
          output: { issues: [] },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg?.toolCalls?.[0]?.status).toBe('completed');
      expect(msg?.toolCalls?.[0]?.output).toEqual({ issues: [] });
    });

    it('should route tool_result with cancelled status to failed', () => {
      store.addPendingToolCall({ id: 'tc-1', name: 'test_tool', input: {}, status: 'pending' });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: { toolCallId: 'tc-1', status: 'cancelled' },
      });

      expect(store.findPendingToolCall('tc-1')?.status).toBe('failed');
    });

    describe('tool_result toolUseId fallback', () => {
      it('should resolve tool call using toolUseId when toolCallId is absent', () => {
        // Buffer a tool call
        store.addPendingToolCall({
          id: 'tc-web-search',
          name: 'web_search',
          input: {},
          status: 'pending',
        });

        // Send tool_result with toolUseId instead of toolCallId
        handler.handleSSEEvent({
          type: 'tool_result',
          data: {
            toolUseId: 'tc-web-search',
            status: 'completed',
            output: { results: ['result1'] },
            // eslint-disable-next-line @typescript-eslint/no-explicit-any -- testing legacy runtime field without toolCallId
          } as any,
        });

        const pending = store.findPendingToolCall('tc-web-search');
        expect(pending?.status).toBe('completed');
        expect(pending?.output).toEqual({ results: ['result1'] });
      });

      it('should prefer toolCallId over toolUseId when both present', () => {
        store.addPendingToolCall({ id: 'tc-prefer', name: 'test', input: {}, status: 'pending' });

        handler.handleSSEEvent({
          type: 'tool_result',
          data: {
            toolCallId: 'tc-prefer',
            toolUseId: 'tc-wrong',
            status: 'completed',
          },
        });

        expect(store.findPendingToolCall('tc-prefer')?.status).toBe('completed');
      });

      it('should ignore tool_result when neither toolCallId nor toolUseId present', () => {
        store.addPendingToolCall({
          id: 'tc-no-id',
          name: 'test',
          input: {},
          status: 'pending',
        });

        handler.handleSSEEvent({
          type: 'tool_result',
          data: {
            status: 'completed',
            // eslint-disable-next-line @typescript-eslint/no-explicit-any -- testing edge case with missing IDs
          } as any,
        });

        // Tool call should still be pending since no ID was provided
        expect(store.findPendingToolCall('tc-no-id')?.status).toBe('pending');
      });
    });

    it('should route task_progress and update task state', () => {
      handler.handleSSEEvent({
        type: 'task_progress',
        data: {
          taskId: 'task-1',
          subject: 'PR Review',
          status: 'in_progress',
          progress: 50,
          agentName: 'PRReviewAgent',
          model: 'claude-opus',
        },
      });

      const task = store.tasks.get('task-1');
      expect(task).toBeDefined();
      expect(task?.subject).toBe('PR Review');
      expect(task?.progress).toBe(50);
      expect(task?.agentName).toBe('PRReviewAgent');
    });

    it('should route approval_request and add to pending', () => {
      handler.handleSSEEvent({
        type: 'approval_request',
        data: {
          requestId: 'req-1',
          actionType: 'create_issue',
          description: 'Create issue from note',
          affectedEntities: [{ type: 'issue', id: 'i-1', name: 'Bug fix' }],
          urgency: 'medium',
          expiresAt: '2026-02-04T00:00:00Z',
        },
      });

      expect(store.pendingApprovals).toHaveLength(1);
      expect(store.pendingApprovals[0]?.requestId).toBe('req-1');
      expect(store.pendingApprovals[0]?.actionType).toBe('create_issue');
    });

    it('should route ask_user_question and set pendingQuestion', () => {
      handler.handleSSEEvent({
        type: 'ask_user_question',
        data: {
          messageId: 'msg-1',
          questionId: 'q-1',
          questions: [
            { question: 'Which priority?', options: [{ label: 'High' }], multiSelect: false },
          ],
        },
      });

      expect(store.pendingQuestion?.questionId).toBe('q-1');
      expect(store.pendingQuestion?.questions).toHaveLength(1);
    });

    it('should route structured_result and set pending result', () => {
      handler.handleSSEEvent({
        type: 'structured_result',
        data: {
          messageId: 'msg-1',
          schemaType: 'extraction_result',
          data: { issues: [{ title: 'Bug' }] },
        },
      });

      const result = store.consumePendingStructuredResult();
      expect(result?.schemaType).toBe('extraction_result');
    });

    it('should route content_update to store.handleContentUpdate', () => {
      const spy = vi.spyOn(store, 'handleContentUpdate');

      handler.handleSSEEvent({
        type: 'content_update',
        data: {
          noteId: 'note-1',
          operation: 'replace_block',
          blockId: 'b-1',
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        },
      });

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('should route message_stop and finalize assistant message', () => {
      // Set up streaming state as if message_start + text_delta happened
      store.streamingState = {
        isStreaming: true,
        streamContent: 'Final answer',
        currentMessageId: 'msg-1',
        thinkingContent: 'I thought about it',
        isThinking: false,
        thinkingStartedAt: Date.now() - 1000,
      };

      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-1',
          stopReason: 'end_turn',
          usage: { inputTokens: 100, outputTokens: 50, totalTokens: 150 },
          costUsd: 0.003,
        },
      });

      // Should create assistant message
      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg).toBeDefined();
      expect(msg?.role).toBe('assistant');
      expect(msg?.content).toBe('Final answer');
      expect(msg?.thinkingContent).toBe('I thought about it');
      expect(msg?.thinkingDurationMs).toBeGreaterThan(0);
      expect(msg?.metadata?.tokenCount).toBe(150);
      expect(msg?.metadata?.costUsd).toBe(0.003);

      // Should reset streaming state
      expect(store.streamingState.isStreaming).toBe(false);
      expect(store.streamingState.streamContent).toBe('');
    });

    it('should mark pending tool calls as completed on message_stop', () => {
      // Set up streaming state
      store.streamingState = {
        isStreaming: true,
        streamContent: 'Response',
        currentMessageId: 'msg-1',
        isThinking: false,
        thinkingStartedAt: null,
      };

      // Buffer tool calls that never received tool_result
      store.addPendingToolCall({
        id: 'tc-1',
        name: 'Read',
        input: { file: 'test.ts' },
        status: 'pending',
      });
      store.addPendingToolCall({
        id: 'tc-2',
        name: 'Grep',
        input: { pattern: 'foo' },
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-1',
          stopReason: 'end_turn',
          usage: { inputTokens: 100, outputTokens: 50, totalTokens: 150 },
        },
      });

      // Tool calls should be attached to the finalized message as completed
      const msg = store.messages.find((m) => m.id === 'msg-1');
      expect(msg?.toolCalls).toHaveLength(2);
      expect(msg?.toolCalls?.[0]?.status).toBe('completed');
      expect(msg?.toolCalls?.[1]?.status).toBe('completed');
    });

    it('should route error and set error state', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'internal_error',
          message: 'Something went wrong',
          retryable: false,
        },
      });

      expect(store.error).toBe('[internal_error] Something went wrong');
      expect(store.streamingState.isStreaming).toBe(false);
    });
  });

  describe('getAuthHeaders', () => {
    it('should return authorization header when session exists', async () => {
      const headers = await handler.getAuthHeaders();
      expect(headers).toEqual({ Authorization: 'Bearer test-token-123' });
    });
  });

  describe('content_block_start handling (G13)', () => {
    it('should track currentBlockType from content_block_start', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.currentBlockType).toBe('text');
      expect(store.streamingState.currentBlockIndex).toBe(0);
    });

    it('should track tool_use block type', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      expect(store.streamingState.currentBlockType).toBe('tool_use');
      expect(store.streamingState.currentBlockIndex).toBe(1);
    });

    it('should transition phase to content on first text block', () => {
      // Start with message_start phase
      store.streamingState.phase = 'message_start';

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.phase).toBe('content');
    });

    it('should defer block separator until real text_delta arrives after existing content', () => {
      // Simulate first text block with content
      store.streamingState.streamContent = 'First block text';
      store.streamingState.currentBlockType = 'text';

      // content_block_start no longer inserts separator eagerly
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });

      expect(store.streamingState.streamContent).toBe('First block text');

      // Separator inserted when real text_delta arrives
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Second block text' },
      });

      expect(store.streamingState.streamContent).toBe('First block text\n\nSecond block text');
    });

    it('should not insert block separator when streamContent is empty', () => {
      store.streamingState.streamContent = '';

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.streamContent).toBe('');
    });

    it('should store parentToolUseId when present', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'parent-tc-1' },
      });

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'child-tc-1',
          toolName: 'Read',
          toolInput: { file: 'test.py' },
        },
      });

      // Tool call buffered in pending with parent ID
      const pending = store.findPendingToolCall('child-tc-1');
      expect(pending?.parentToolUseId).toBe('parent-tc-1');
    });
  });

  describe('noise text_delta filtering', () => {
    it('should filter out "(no content)" text deltas', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: '(no content)' },
      });

      expect(store.streamingState.streamContent).toBe('');
    });

    it('should preserve whitespace deltas containing newlines (markdown formatting)', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: '   \n  ' },
      });

      expect(store.streamingState.streamContent).toBe('   \n  ');
    });

    it('should filter out empty string deltas', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: '' },
      });

      expect(store.streamingState.streamContent).toBe('');
    });

    it('should not filter real content', () => {
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Hello world' },
      });

      expect(store.streamingState.streamContent).toBe('Hello world');
    });

    it('should not insert deferred separator when only noise follows', () => {
      store.streamingState.streamContent = 'First block';
      store.streamingState.currentBlockType = 'text';

      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: '(no content)' },
      });

      expect(store.streamingState.streamContent).toBe('First block');
    });
  });

  describe('tool_input_delta with blockIndex mapping', () => {
    it('should route tool_input_delta via blockIndex when toolUseId is absent', () => {
      // Simulate content_block_start for tool_use block at index 2
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 2, contentType: 'tool_use' },
      });

      // tool_use event registers the tool call
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-block-2',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });

      // tool_input_delta with blockIndex (backend format) instead of toolUseId
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 2, delta: '{"key":"val"}' },
      });

      const tc = store.findPendingToolCall('tc-block-2');
      expect(tc?.partialInput).toBe('{"key":"val"}');
    });

    it('should route tool_input_delta via toolUseId when present', () => {
      store.addPendingToolCall({
        id: 'tc-direct',
        name: 'extract_issues',
        input: {},
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { toolUseId: 'tc-direct', inputDelta: '{"noteId":"n1"}' },
      });

      const tc = store.findPendingToolCall('tc-direct');
      expect(tc?.partialInput).toBe('{"noteId":"n1"}');
    });
  });

  describe('duplicate summary text block filtering', () => {
    it('should skip text_deltas from index:0 text blocks when content already exists', () => {
      // Simulate word-by-word text from index:1 block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Hello world' },
      });
      expect(store.streamingState.streamContent).toBe('Hello world');

      // Summary block at index:0 — should be skipped
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: ' Hello world  ' },
      });

      // Content should NOT be duplicated
      expect(store.streamingState.streamContent).toBe('Hello world');
    });

    it('should not skip first text block at index:0 when content is empty', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'First message' },
      });

      expect(store.streamingState.streamContent).toBe('First message');
    });

    it('should resume accepting text after non-text block clears skip flag', () => {
      // Populate existing content
      store.streamingState.streamContent = 'Existing';

      // Summary block — sets skip flag
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      // Thinking block — clears skip flag
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });

      // New real text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'New content' },
      });

      expect(store.streamingState.streamContent).toContain('New content');
    });
  });

  describe('multi-turn thinking blocks', () => {
    it('should create separate thinking blocks for each thinking turn', () => {
      // First thinking turn
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'First thought', blockIndex: 0 },
      });

      // Interleave text + tool call
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Some response' },
      });

      // Second thinking turn — also blockIndex: 0 (model resets)
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Second thought', blockIndex: 0 },
      });

      // Should have 2 separate thinking blocks
      const blocks = store.streamingState.thinkingBlocks;
      expect(blocks).toHaveLength(2);
      expect(blocks![0]!.content).toBe('First thought');
      expect(blocks![1]!.content).toBe('Second thought');
      // Block indices should be 0 and 1 (our turn counter, not raw blockIndex)
      expect(blocks![0]!.blockIndex).toBe(0);
      expect(blocks![1]!.blockIndex).toBe(1);
    });

    it('should accumulate deltas within the same thinking turn', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Part 1 ', blockIndex: 0 },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Part 2', blockIndex: 0 },
      });

      const blocks = store.streamingState.thinkingBlocks;
      expect(blocks).toHaveLength(1);
      expect(blocks![0]!.content).toBe('Part 1 Part 2');
    });
  });

  describe('flag-based block separator', () => {
    it('should NOT insert separator between consecutive deltas in same text block', () => {
      // Start a text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      // Multiple deltas in the same block
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: 'Hello' } });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: ' world' } });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: '!' } });

      // Should be concatenated without any \n\n between them
      expect(store.streamingState.streamContent).toBe('Hello world!');
    });

    it('should insert separator only once between text blocks', () => {
      // First text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: 'First' } });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: ' block' } });

      // Second text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: 'Second' } });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: ' block' } });

      // One separator between blocks, no separators within blocks
      expect(store.streamingState.streamContent).toBe('First block\n\nSecond block');
    });
  });

  describe('ordered content blocks', () => {
    it('should build interleaved contentBlocks at finalization', () => {
      // message_start
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-ordered', sessionId: 's1' },
      });

      // Thinking block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Let me think...', blockIndex: 0 },
      });

      // Text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Here is the answer' },
      });

      // Tool call
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 2, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-1', toolName: 'search', toolInput: {} },
      });

      // Second thinking block (new turn, blockIndex resets)
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking again...', blockIndex: 0 },
      });

      // Second text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Final answer' },
      });

      // Finalize
      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-ordered',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-ordered');
      expect(msg?.contentBlocks).toBeDefined();
      expect(msg!.contentBlocks).toHaveLength(5);

      // Verify order: thinking → text → tool_call → thinking → text
      expect(msg!.contentBlocks![0]!.type).toBe('thinking');
      expect(msg!.contentBlocks![1]!.type).toBe('text');
      expect(msg!.contentBlocks![2]!.type).toBe('tool_call');
      expect(msg!.contentBlocks![3]!.type).toBe('thinking');
      expect(msg!.contentBlocks![4]!.type).toBe('text');

      // Verify content
      const tb0 = msg!.contentBlocks![0] as { type: 'thinking'; content: string };
      expect(tb0.content).toBe('Let me think...');
      const txt0 = msg!.contentBlocks![1] as { type: 'text'; content: string };
      expect(txt0.content).toBe('Here is the answer');
      const tc0 = msg!.contentBlocks![2] as { type: 'tool_call'; toolCallId: string };
      expect(tc0.toolCallId).toBe('tc-1');
      const tb1 = msg!.contentBlocks![3] as { type: 'thinking'; content: string };
      expect(tb1.content).toBe('Thinking again...');
      const txt1 = msg!.contentBlocks![4] as { type: 'text'; content: string };
      expect(txt1.content).toBe('Final answer');
    });

    it('should not set contentBlocks when there are no tracked blocks', () => {
      store.streamingState = {
        isStreaming: true,
        streamContent: 'Simple text',
        currentMessageId: 'msg-simple',
        isThinking: false,
        thinkingStartedAt: null,
      };

      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-simple',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-simple');
      expect(msg?.contentBlocks).toBeUndefined();
    });

    it('should track separate text segments per text block', () => {
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-segments', sessionId: 's1' },
      });

      // First text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: 'Segment 1' } });

      // Tool call between text blocks
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-seg', toolName: 'search', toolInput: {} },
      });

      // Second text block
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 2, contentType: 'text' },
      });
      handler.handleSSEEvent({ type: 'text_delta', data: { delta: 'Segment 2' } });

      // Finalize
      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-segments',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-segments');
      expect(msg!.contentBlocks).toHaveLength(3);
      expect(msg!.contentBlocks![0]).toEqual({ type: 'text', content: 'Segment 1' });
      expect(msg!.contentBlocks![1]).toEqual({ type: 'tool_call', toolCallId: 'tc-seg' });
      expect(msg!.contentBlocks![2]).toEqual({ type: 'text', content: 'Segment 2' });
    });
  });

  describe('blockOrder and textSegments sync to streamingState', () => {
    it('should sync blockOrder after thinking content_block_start', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });

      expect(store.streamingState.blockOrder).toEqual(['thinking']);
      expect(store.streamingState.textSegments).toEqual([]);
    });

    it('should sync blockOrder and textSegments after text content_block_start', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });

      expect(store.streamingState.blockOrder).toEqual(['text']);
      expect(store.streamingState.textSegments).toEqual(['']);
    });

    it('should sync blockOrder after tool_use content_block_start', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use' },
      });

      expect(store.streamingState.blockOrder).toEqual(['tool_use']);
    });

    it('should accumulate blockOrder across multiple content_block_starts', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 2, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 3, contentType: 'text' },
      });

      expect(store.streamingState.blockOrder).toEqual(['thinking', 'text', 'tool_use', 'text']);
      expect(store.streamingState.textSegments).toEqual(['', '']);
    });

    it('should update textSegments as text_delta events arrive', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Hello' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: ' world' },
      });

      expect(store.streamingState.textSegments).toEqual(['Hello world']);
    });

    it('should track separate textSegments for each text block', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'First' },
      });

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 2, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Second' },
      });

      expect(store.streamingState.textSegments).toEqual(['First', 'Second']);
      expect(store.streamingState.blockOrder).toEqual(['text', 'tool_use', 'text']);
    });

    it('should create new array references on each sync (MobX detection)', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      const firstBlockOrder = store.streamingState.blockOrder;
      const firstTextSegments = store.streamingState.textSegments;

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'thinking' },
      });
      const secondBlockOrder = store.streamingState.blockOrder;
      const secondTextSegments = store.streamingState.textSegments;

      // Different references for MobX reactivity
      expect(firstBlockOrder).not.toBe(secondBlockOrder);
      expect(firstTextSegments).not.toBe(secondTextSegments);
    });
  });

  describe('parentToolUseId correlation (G12)', () => {
    it('should reset parentToolUseId on message_start', () => {
      // Set parent from a content_block_start
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'old-parent' },
      });

      // message_start should reset it
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-2', sessionId: 'sess-1' },
      });

      // Tool call after reset should not have parentToolUseId
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-2',
          toolName: 'Write',
          toolInput: { content: 'test' },
        },
      });

      const pending = store.findPendingToolCall('tc-2');
      expect(pending?.parentToolUseId).toBeUndefined();
    });

    it('should attach parentToolUseId to tool calls from subagent blocks', () => {
      // First, a content_block_start with parent
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use', parentToolUseId: 'subagent-parent' },
      });

      // Tool call should get parent ID (buffered in pending)
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-3',
          toolName: 'extract_issues',
          toolInput: { noteId: 'n1' },
        },
      });

      const pending = store.findPendingToolCall('tc-3');
      expect(pending?.parentToolUseId).toBe('subagent-parent');
    });
  });

  describe('abortClient', () => {
    it('should not throw when no client exists', () => {
      expect(() => handler.abortClient()).not.toThrow();
    });
  });

  describe('budget_warning handler', () => {
    it('should set store.error with warning message and cost info', () => {
      const event: SSEEvent = {
        type: 'budget_warning',
        data: {
          currentCostUsd: 0.45,
          maxBudgetUsd: 0.5,
          percentUsed: 90,
          message: 'Budget nearly exhausted',
        },
      };

      handler.handleSSEEvent(event);

      expect(store.error).toContain('Budget warning');
      expect(store.error).toContain('90%');
      expect(store.error).toContain('0.4500');
      expect(store.error).toContain('0.50');
    });
  });

  describe('tool_audit handler', () => {
    it('should update durationMs on pending tool call', () => {
      // Buffer a tool call (simulates tool_use during streaming)
      store.addPendingToolCall({ id: 'tc1', name: 'read_note', input: {}, status: 'pending' });

      // Dispatch tool_audit with camelCase fields
      handler.handleSSEEvent({
        type: 'tool_audit',
        data: {
          toolUseId: 'tc1',
          toolName: 'read_note',
          inputSummary: '{}',
          outputSummary: 'ok',
          durationMs: 150,
        },
      });

      const pending = store.findPendingToolCall('tc1');
      expect(pending).toBeDefined();
      expect(pending?.durationMs).toBe(150);
    });

    it('should update durationMs on finalized message tool call', () => {
      store.addMessage({
        id: 'm1',
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        toolCalls: [{ id: 'tc1', name: 'read_note', input: {}, status: 'pending' }],
      });

      handler.handleSSEEvent({
        type: 'tool_audit',
        data: {
          toolUseId: 'tc1',
          toolName: 'read_note',
          inputSummary: '{}',
          outputSummary: 'ok',
          durationMs: 150,
        },
      });

      const msg = store.messages.find((m) => m.toolCalls?.some((tc) => tc.id === 'tc1'));
      expect(msg?.toolCalls?.[0]?.durationMs).toBe(150);
    });

    it('should not throw when tool call ID is not found', () => {
      handler.handleSSEEvent({
        type: 'tool_audit',
        data: {
          toolUseId: 'nonexistent',
          toolName: 'read_note',
          inputSummary: '{}',
          outputSummary: 'ok',
          durationMs: 100,
        },
      });

      // No messages, no error thrown
      expect(store.messages).toHaveLength(0);
    });
  });

  describe('error auto-retry', () => {
    it('should set retry message and keep streaming on retryable error', () => {
      vi.useFakeTimers();

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'm1', sessionId: 's1' },
      });

      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'rate_limited',
          message: 'Rate limited',
          retryable: true,
          retryAfter: 2,
        },
      });

      expect(store.error).toContain('retrying');
      expect(store.error).toContain('1/3');
      expect(store.streamingState.isStreaming).toBe(true);

      vi.useRealTimers();
    });

    it('should reset streaming after max retries exceeded', () => {
      vi.useFakeTimers();

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'm1', sessionId: 's1' },
      });

      // Exhaust all 3 retry attempts
      for (let i = 0; i < 3; i++) {
        handler.handleSSEEvent({
          type: 'error',
          data: {
            errorCode: 'rate_limited',
            message: 'Rate limited',
            retryable: true,
            retryAfter: 1,
          },
        });
      }

      // 4th retryable error should exceed max retries and reset
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'rate_limited',
          message: 'Rate limited',
          retryable: true,
          retryAfter: 1,
        },
      });

      expect(store.streamingState.isStreaming).toBe(false);
      expect(store.error).toBe('[rate_limited] Rate limited');

      vi.useRealTimers();
    });

    it('should immediately reset streaming on non-retryable error', () => {
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'm1', sessionId: 's1' },
      });

      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'internal_error',
          message: 'Something broke',
          retryable: false,
        },
      });

      expect(store.streamingState.isStreaming).toBe(false);
      expect(store.error).toBe('[internal_error] Something broke');
    });
  });

  describe('resetRetryState', () => {
    it('should clear retry count so next error starts at 1/3', () => {
      vi.useFakeTimers();

      // First retryable error increments to 1/3
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'm1', sessionId: 's1' },
      });

      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'rate_limited',
          message: 'err',
          retryable: true,
          retryAfter: 1,
        },
      });

      expect(store.error).toContain('1/3');

      // Reset retry state
      handler.resetRetryState();

      // Next retryable error should say 1/3, not 2/3
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'rate_limited',
          message: 'err again',
          retryable: true,
          retryAfter: 1,
        },
      });

      expect(store.error).toContain('1/3');
      expect(store.error).not.toContain('2/3');

      vi.useRealTimers();
    });
  });
});
