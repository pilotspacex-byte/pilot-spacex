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

    it('should clear pendingQuestion on message_start (defensive reset)', () => {
      store.pendingQuestion = {
        questionId: 'q-stale',
        questions: [{ question: 'Old?', options: [], multiSelect: false }],
      };

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-2', sessionId: 'sess-2' },
      });

      expect(store.pendingQuestion).toBeNull();
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

    it('should extract blockId from note tool_use and call addPendingAIBlockId', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-note-1',
          toolName: 'update_note_block',
          toolInput: { block_id: 'block-abc', content: 'hello' },
        },
      });

      expect(spy).toHaveBeenCalledWith('block-abc');
    });

    it('should extract blockId using camelCase fallback from note tool_use', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-note-2',
          toolName: 'enhance_text',
          toolInput: { blockId: 'block-def' },
        },
      });

      expect(spy).toHaveBeenCalledWith('block-def');
    });

    it('should extract blockId from MCP-prefixed tool names', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-mcp-1',
          toolName: 'mcp__pilot-notes__update_note_block',
          toolInput: { block_id: 'block-mcp' },
        },
      });

      expect(spy).toHaveBeenCalledWith('block-mcp');
    });

    it('should skip ¶N block references for pending-edit indicator', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-para-1',
          toolName: 'update_note_block',
          toolInput: { block_id: '¶3' },
        },
      });

      expect(spy).not.toHaveBeenCalled();
    });

    it('should NOT call addPendingAIBlockId for non-note tools', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'tc-other',
          toolName: 'web_search',
          toolInput: { query: 'test' },
        },
      });

      expect(spy).not.toHaveBeenCalled();
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

    it('should route question_request and set pendingQuestion', () => {
      handler.handleSSEEvent({
        type: 'question_request',
        data: {
          messageId: 'msg-1',
          questionId: 'q-1',
          toolCallId: 'tc-1',
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

      expect(store.error).toBe('Something went wrong');
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

    it('should set startedAt on new thinking blocks', () => {
      const beforeTime = Date.now();
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thought', blockIndex: 0 },
      });

      const blocks = store.streamingState.thinkingBlocks;
      expect(blocks![0]!.startedAt).toBeGreaterThanOrEqual(beforeTime);
      expect(blocks![0]!.startedAt).toBeLessThanOrEqual(Date.now());
    });

    it('should finalize durationMs when text block starts after thinking', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...', blockIndex: 0 },
      });

      // Text block starts — should finalize the thinking block duration
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });

      const blocks = store.streamingState.thinkingBlocks;
      expect(blocks![0]!.durationMs).toBeDefined();
      expect(blocks![0]!.durationMs).toBeGreaterThanOrEqual(0);
    });

    it('should finalize durationMs when tool_use block starts after thinking', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...', blockIndex: 0 },
      });

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      const blocks = store.streamingState.thinkingBlocks;
      expect(blocks![0]!.durationMs).toBeDefined();
    });

    it('should finalize durationMs on message_stop for in-progress thinking', () => {
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-dur', sessionId: 's1' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Still thinking', blockIndex: 0 },
      });

      // message_stop without an intervening text/tool block
      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-dur',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-dur');
      const thinkingBlock = msg?.contentBlocks?.find((b) => b.type === 'thinking');
      expect(thinkingBlock).toBeDefined();
      if (thinkingBlock?.type === 'thinking') {
        expect(thinkingBlock.durationMs).toBeDefined();
        expect(thinkingBlock.durationMs).toBeGreaterThanOrEqual(0);
      }
    });

    it('should pass startedAt and durationMs through to contentBlocks', () => {
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-pass', sessionId: 's1' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'First', blockIndex: 0 },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Response' },
      });
      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-pass',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
        },
      });

      const msg = store.messages.find((m) => m.id === 'msg-pass');
      const thinking = msg?.contentBlocks?.find((b) => b.type === 'thinking');
      expect(thinking).toBeDefined();
      if (thinking?.type === 'thinking') {
        expect(thinking.startedAt).toBeDefined();
        expect(thinking.durationMs).toBeDefined();
      }
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

    it('should create new thinkingBlocks array reference on each thinking_delta', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'First', blockIndex: 0 },
      });

      const firstRef = store.streamingState.thinkingBlocks;

      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: ' second', blockIndex: 0 },
      });

      const secondRef = store.streamingState.thinkingBlocks;

      // Different array references for React memo detection
      expect(firstRef).not.toBe(secondRef);
      // Content accumulated correctly
      expect(secondRef![0]!.content).toBe('First second');
    });

    it('should reset isThinking when tool_use content_block_start follows thinking', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...', blockIndex: 0 },
      });

      expect(store.streamingState.isThinking).toBe(true);

      // tool_use starts without text in between
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      expect(store.streamingState.isThinking).toBe(false);
    });

    it('should reset isThinking when text content_block_start follows thinking', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });
      handler.handleSSEEvent({
        type: 'thinking_delta',
        data: { delta: 'Thinking...', blockIndex: 0 },
      });

      expect(store.streamingState.isThinking).toBe(true);

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'text' },
      });

      expect(store.streamingState.isThinking).toBe(false);
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
      expect(store.error).toBe('Rate limited');

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
      expect(store.error).toBe('Something broke');
    });
  });

  describe('tool_use dedup (2A)', () => {
    it('should not create duplicate tool call when same toolCallId sent twice', () => {
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-dup', toolName: 'extract_issues', toolInput: {} },
      });

      // Second tool_use with same ID but with input
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-dup', toolName: 'extract_issues', toolInput: { noteId: 'n1' } },
      });

      // Should have exactly one pending tool call
      const allPending = store.consumePendingToolCalls();
      expect(allPending).toHaveLength(1);
      expect(allPending![0]!.id).toBe('tc-dup');
      // Input should be merged from second event
      expect(allPending![0]!.input).toEqual({ noteId: 'n1' });
    });

    it('should not overwrite input when duplicate has empty input', () => {
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-dup2', toolName: 'search', toolInput: { query: 'test' } },
      });

      // Second event with empty input should not clear existing input
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-dup2', toolName: 'search', toolInput: {} },
      });

      const pending = store.findPendingToolCall('tc-dup2');
      expect(pending?.input).toEqual({ query: 'test' });
    });
  });

  describe('partialInput parsing on tool_result (2B)', () => {
    it('should parse partialInput into input when input is empty on completion', () => {
      // Add tool call with empty input (streaming scenario)
      store.addPendingToolCall({
        id: 'tc-partial',
        name: 'update_note_block',
        input: {},
        status: 'pending',
      });

      // Accumulate partial input via tool_input_delta
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { toolUseId: 'tc-partial', inputDelta: '{"blockId":"b1",' },
      });
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { toolUseId: 'tc-partial', inputDelta: '"content":"hello"}' },
      });

      // Complete the tool
      handler.handleSSEEvent({
        type: 'tool_result',
        data: { toolCallId: 'tc-partial', status: 'completed', output: { ok: true } },
      });

      const tc = store.findPendingToolCall('tc-partial');
      expect(tc?.input).toEqual({ blockId: 'b1', content: 'hello' });
    });

    it('should leave partialInput as-is when JSON is incomplete', () => {
      store.addPendingToolCall({
        id: 'tc-broken',
        name: 'update_note_block',
        input: {},
        status: 'pending',
      });

      // Incomplete JSON
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { toolUseId: 'tc-broken', inputDelta: '{"blockId":"b1"' },
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: { toolCallId: 'tc-broken', status: 'completed' },
      });

      const tc = store.findPendingToolCall('tc-broken');
      // input remains empty, partialInput still holds the fragment
      expect(tc?.input).toEqual({});
      expect(tc?.partialInput).toBe('{"blockId":"b1"');
    });

    it('should not overwrite existing input with partialInput', () => {
      store.addPendingToolCall({
        id: 'tc-has-input',
        name: 'search',
        input: { query: 'existing' },
        status: 'pending',
        partialInput: '{"query":"from_partial"}',
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: { toolCallId: 'tc-has-input', status: 'completed' },
      });

      const tc = store.findPendingToolCall('tc-has-input');
      // Original input preserved since it's non-empty
      expect(tc?.input).toEqual({ query: 'existing' });
    });
  });

  describe('toolInput from backend in tool_result (2C)', () => {
    it('should use backend-provided toolInput when present', () => {
      store.addPendingToolCall({
        id: 'tc-backend',
        name: 'extract_issues',
        input: {},
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-backend',
          status: 'completed',
          output: { issues: [] },
          toolInput: { noteId: 'n1', blocks: ['b1', 'b2'] },
        },
      });

      const tc = store.findPendingToolCall('tc-backend');
      expect(tc?.input).toEqual({ noteId: 'n1', blocks: ['b1', 'b2'] });
    });

    it('should not overwrite input with empty toolInput from backend', () => {
      store.addPendingToolCall({
        id: 'tc-noop',
        name: 'search',
        input: { query: 'test' },
        status: 'pending',
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-noop',
          status: 'completed',
          toolInput: {},
        },
      });

      const tc = store.findPendingToolCall('tc-noop');
      expect(tc?.input).toEqual({ query: 'test' });
    });

    it('should prefer backend toolInput over partialInput parsing', () => {
      store.addPendingToolCall({
        id: 'tc-both',
        name: 'update_note_block',
        input: {},
        status: 'pending',
        partialInput: '{"fromPartial":true}',
      });

      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'tc-both',
          status: 'completed',
          toolInput: { fromBackend: true },
        },
      });

      const tc = store.findPendingToolCall('tc-both');
      // Backend toolInput wins because it's applied first, making input non-empty
      // so partialInput parsing is skipped
      expect(tc?.input).toEqual({ fromBackend: true });
    });
  });

  describe('block_id extraction from tool_input_delta (SSE flow proof)', () => {
    // Proves the exact SSE sequence from backend:
    // 1. tool_use arrives with toolInput: {} (empty)
    // 2. tool_input_delta streams actual JSON containing block_id
    // 3. addPendingAIBlockId is called from delta, NOT from tool_use

    it('should NOT call addPendingAIBlockId when toolInput is empty at tool_use time', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      // Exactly what backend sends: tool_use with empty toolInput
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_01ABC',
          toolName: 'mcp__pilot-notes__update_note_block',
          toolInput: {},
        },
      });

      // At this point block_id is unknown — should NOT have been called
      expect(spy).not.toHaveBeenCalled();
    });

    it('should extract block_id from tool_input_delta and call addPendingAIBlockId', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      // Step 1: tool_use with empty input (real SSE)
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_01ABC',
          toolName: 'mcp__pilot-notes__update_note_block',
          toolInput: {},
        },
      });
      expect(spy).not.toHaveBeenCalled();

      // Step 2: tool_input_delta streams partial JSON with block_id
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "abc-123-def",' },
      });

      // NOW addPendingAIBlockId should have been called with the extracted block_id
      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith('abc-123-def');
    });

    it('should extract block_id only once even with multiple deltas', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_02DEF',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });

      // First delta with block_id
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "block-xyz",' },
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // More deltas with content — should NOT extract again
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: ' "markdown": "# Hello"}' },
      });
      expect(spy).toHaveBeenCalledTimes(1); // still 1, not 2
    });

    it('should call requestNoteEndScroll for write_to_note with empty toolInput', () => {
      const spy = vi.spyOn(store, 'requestNoteEndScroll');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_03GHI',
          toolName: 'mcp__pilot-notes__write_to_note',
          toolInput: {},
        },
      });

      // write_to_note triggers end-scroll immediately (no block_id needed)
      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('should NOT extract block_id from non-note tool deltas', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_04JKL',
          toolName: 'web_search',
          toolInput: {},
        },
      });

      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "should-be-ignored", "query": "test"}' },
      });

      expect(spy).not.toHaveBeenCalled();
    });

    it('should skip ¶N block references extracted from deltas', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_05MNO',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });

      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "¶3",' },
      });

      // ¶N references are backend-only notation — should be skipped
      expect(spy).not.toHaveBeenCalled();
    });

    it('full SSE sequence: message_start → tool_use(empty) → deltas → tool_result', () => {
      const blockIdSpy = vi.spyOn(store, 'addPendingAIBlockId');

      // message_start
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-proof', sessionId: 'sess-proof' },
      });

      // content_block_start for tool_use
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });

      // tool_use with EMPTY toolInput (this is what backend actually sends)
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_proof',
          toolName: 'mcp__pilot-notes__update_note_block',
          toolInput: {},
        },
      });
      expect(blockIdSpy).not.toHaveBeenCalled();

      // tool_input_delta streams in the actual JSON
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_' },
      });
      expect(blockIdSpy).not.toHaveBeenCalled(); // partial, no match yet

      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: 'id": "real-block-id-456",' },
      });
      // NOW block_id is complete in accumulated partialInput
      expect(blockIdSpy).toHaveBeenCalledTimes(1);
      expect(blockIdSpy).toHaveBeenCalledWith('real-block-id-456');

      // More delta with content
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: ' "markdown": "updated text"}' },
      });
      // Should still be called only once
      expect(blockIdSpy).toHaveBeenCalledTimes(1);

      // tool_result
      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'toolu_proof',
          status: 'completed',
          output: { ok: true },
        },
      });

      // Verify tool call has correct state
      const tc = store.findPendingToolCall('toolu_proof');
      expect(tc?.status).toBe('completed');
      expect(tc?.partialInput).toContain('real-block-id-456');
    });

    it('should clear _blockIdExtractedIds on new message_start', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      // First message with extraction
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-1', sessionId: 's1' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-1', toolName: 'update_note_block', toolInput: {} },
      });
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "b1"}' },
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // New message resets state
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-2', sessionId: 's1' },
      });
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: { toolCallId: 'tc-2', toolName: 'update_note_block', toolInput: {} },
      });
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "b2"}' },
      });

      // Should have been called again for the new message
      expect(spy).toHaveBeenCalledTimes(2);
      expect(spy).toHaveBeenCalledWith('b2');
    });
  });

  describe('block_id extraction fallbacks (dedup + tool_result)', () => {
    // Tests the three extraction paths:
    // 1. tool_input_delta (primary, tested above)
    // 2. tool_use dedup (when AssistantMessage re-emits with full input)
    // 3. tool_result (last-resort fallback from resolved input)

    it('should extract block_id from dedup tool_use with full input', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      // First tool_use with empty input (StreamEvent path)
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_dedup',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });
      expect(spy).not.toHaveBeenCalled();

      // Second tool_use with full input (AssistantMessage path)
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_dedup',
          toolName: 'update_note_block',
          toolInput: { block_id: 'dedup-block', markdown: '# Hello' },
        },
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith('dedup-block');
    });

    it('should extract block_id from tool_result when all other paths missed it', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      // tool_use with empty input
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_fallback',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });

      // tool_result with toolInput (backend provides complete input)
      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'toolu_fallback',
          status: 'completed',
          output: { ok: true },
          toolInput: { block_id: 'fallback-block', markdown: '# Test' },
        },
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith('fallback-block');
    });

    it('should extract block_id from parsed partialInput in tool_result', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_partial',
          toolName: 'enhance_text',
          toolInput: {},
        },
      });

      // Simulate late tool_input_delta that arrived but wasn't processed for blockId
      // (e.g., arrived after tool_result was already processing)
      const tc = store.findPendingToolCall('toolu_partial');
      if (tc) {
        tc.partialInput = '{"block_id": "partial-block", "text": "improved"}';
      }

      // tool_result triggers parsing of partialInput → input → block_id extraction
      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'toolu_partial',
          status: 'completed',
          output: { ok: true },
        },
      });

      expect(spy).toHaveBeenCalledTimes(1);
      expect(spy).toHaveBeenCalledWith('partial-block');
    });

    it('should NOT double-extract if tool_input_delta already extracted', () => {
      const spy = vi.spyOn(store, 'addPendingAIBlockId');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_nodup',
          toolName: 'update_note_block',
          toolInput: {},
        },
      });

      // tool_input_delta extracts block_id (primary path)
      handler.handleSSEEvent({
        type: 'tool_input_delta',
        data: { blockIndex: 1, delta: '{"block_id": "first-extract"}' },
      });
      expect(spy).toHaveBeenCalledTimes(1);

      // tool_result with same tool → should NOT re-extract
      handler.handleSSEEvent({
        type: 'tool_result',
        data: {
          toolCallId: 'toolu_nodup',
          status: 'completed',
          output: { ok: true },
          toolInput: { block_id: 'first-extract', markdown: '# Hi' },
        },
      });
      expect(spy).toHaveBeenCalledTimes(1); // still 1, not 2
    });

    it('should handle write_to_note in dedup path', () => {
      const spy = vi.spyOn(store, 'requestNoteEndScroll');

      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 1, contentType: 'tool_use' },
      });
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_write',
          toolName: 'write_to_note',
          toolInput: {},
        },
      });
      // write_to_note triggers end scroll immediately on first tool_use
      expect(spy).toHaveBeenCalledTimes(1);

      // Dedup tool_use should NOT re-trigger
      handler.handleSSEEvent({
        type: 'tool_use',
        data: {
          toolCallId: 'toolu_write',
          toolName: 'write_to_note',
          toolInput: { note_id: 'n1', markdown: 'text' },
        },
      });
      // Already extracted — should still be 1
      expect(spy).toHaveBeenCalledTimes(1);
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

  // ===========================================================================
  // focus_block event handling
  // ===========================================================================
  describe('focus_block event handling', () => {
    it('should add blockId to pendingAIBlockIds on focus_block', () => {
      handler.handleSSEEvent({
        type: 'focus_block',
        data: { noteId: 'note-1', blockId: 'blk-focus', scrollToEnd: false },
      } as SSEEvent);

      expect(store.pendingAIBlockIds).toContain('blk-focus');
    });

    it('should call requestNoteEndScroll when scrollToEnd is true', () => {
      const spy = vi.spyOn(store, 'requestNoteEndScroll');

      handler.handleSSEEvent({
        type: 'focus_block',
        data: { noteId: 'note-2', blockId: null, scrollToEnd: true },
      } as SSEEvent);

      expect(spy).toHaveBeenCalledOnce();
      expect(store.pendingAIBlockIds).toHaveLength(0);
    });

    it('should not add empty blockId', () => {
      handler.handleSSEEvent({
        type: 'focus_block',
        data: { noteId: 'note-3', blockId: null, scrollToEnd: false },
      } as SSEEvent);

      expect(store.pendingAIBlockIds).toHaveLength(0);
    });

    it('should not duplicate blockId if already pending', () => {
      store.addPendingAIBlockId('blk-dup');

      handler.handleSSEEvent({
        type: 'focus_block',
        data: { noteId: 'note-4', blockId: 'blk-dup', scrollToEnd: false },
      } as SSEEvent);

      expect(store.pendingAIBlockIds.filter((id) => id === 'blk-dup')).toHaveLength(1);
    });

    it('should process focus_block before content_update in sequential dispatch', () => {
      // Simulate the backend SSE order: focus_block → content_update
      const focusEvent = {
        type: 'focus_block',
        data: { noteId: 'note-5', blockId: 'blk-seq', scrollToEnd: false },
      } as SSEEvent;

      const contentUpdateEvent = {
        type: 'content_update',
        data: {
          noteId: 'note-5',
          operation: 'replace_block',
          blockId: 'blk-seq',
          markdown: '# Updated',
          content: null,
          issueData: null,
          afterBlockId: null,
        },
      } as SSEEvent;

      handler.handleSSEEvent(focusEvent);
      // Block should be pending before content_update
      expect(store.pendingAIBlockIds).toContain('blk-seq');

      handler.handleSSEEvent(contentUpdateEvent);
      // content_update should be queued
      expect(store.pendingContentUpdates).toHaveLength(1);
      expect(store.pendingContentUpdates[0]!.blockId).toBe('blk-seq');
    });
  });

  describe('question_request safety timeout (CRITICAL-2)', () => {
    it('should synthesize message_stop if it never arrives after question_request', () => {
      vi.useFakeTimers();

      // Start a message
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-q1', sessionId: 'sess-q1' },
      });

      // Some streaming text
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'text' },
      });
      handler.handleSSEEvent({
        type: 'text_delta',
        data: { delta: 'Let me ask you something.' },
      });

      // question_request arrives
      handler.handleSSEEvent({
        type: 'question_request',
        data: {
          messageId: 'msg-q1',
          questionId: 'q-safety',
          toolCallId: 'tc-safety',
          questions: [
            {
              question: 'Continue?',
              options: [{ label: 'Yes' }, { label: 'No' }],
              multiSelect: false,
            },
          ],
        },
      });

      // No message_stop arrives — stream ends silently (PermissionResultDeny path)
      expect(store.streamingState.isStreaming).toBe(true);
      expect(store.messages).toHaveLength(0);

      // Advance past the 5s safety timeout
      vi.advanceTimersByTime(5000);

      // Safety timeout should have synthesized message_stop
      expect(store.streamingState.isStreaming).toBe(false);
      const msg = store.messages.find((m) => m.id === 'msg-q1');
      expect(msg).toBeDefined();
      expect(msg?.content).toBe('Let me ask you something.');
      expect(msg?.questionData).toBeDefined();
      expect(msg?.questionData?.questionId).toBe('q-safety');

      vi.useRealTimers();
    });

    it('should cancel safety timeout when message_stop arrives normally', () => {
      vi.useFakeTimers();

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-q2', sessionId: 'sess-q2' },
      });

      handler.handleSSEEvent({
        type: 'question_request',
        data: {
          messageId: 'msg-q2',
          questionId: 'q-normal',
          toolCallId: 'tc-normal',
          questions: [{ question: 'Pick one', options: [{ label: 'A' }], multiSelect: false }],
        },
      });

      // Normal message_stop arrives before timeout
      handler.handleSSEEvent({
        type: 'message_stop',
        data: {
          messageId: 'msg-q2',
          stopReason: 'end_turn',
          usage: { inputTokens: 10, outputTokens: 5, totalTokens: 15 },
        },
      });

      expect(store.messages).toHaveLength(1);

      // Advance past timeout — should NOT create a second message
      vi.advanceTimersByTime(5000);
      expect(store.messages).toHaveLength(1);

      vi.useRealTimers();
    });

    it('should cancel safety timeout when new message_start arrives', () => {
      vi.useFakeTimers();

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-q3', sessionId: 'sess-q3' },
      });

      handler.handleSSEEvent({
        type: 'question_request',
        data: {
          messageId: 'msg-q3',
          questionId: 'q-reset',
          toolCallId: 'tc-reset',
          questions: [{ question: 'Choose', options: [{ label: 'X' }], multiSelect: false }],
        },
      });

      // New message_start resets everything
      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-q4', sessionId: 'sess-q3' },
      });

      // Advance past timeout — should NOT synthesize for msg-q3
      vi.advanceTimersByTime(5000);

      // Only the streaming state for msg-q4 should be active, no finalized messages
      expect(store.streamingState.currentMessageId).toBe('msg-q4');
      expect(store.messages).toHaveLength(0);

      vi.useRealTimers();
    });

    it('should cancel safety timeout when content_block_start arrives after question_request', () => {
      vi.useFakeTimers();

      handler.handleSSEEvent({
        type: 'message_start',
        data: { messageId: 'msg-cbs', sessionId: 'sess-cbs' },
      });

      handler.handleSSEEvent({
        type: 'question_request',
        data: {
          messageId: 'msg-cbs',
          questionId: 'q-cbs',
          toolCallId: 'tc-cbs',
          questions: [{ question: 'Pick', options: [{ label: 'A' }], multiSelect: false }],
        },
      });

      // AI continues thinking — content_block_start should cancel safety timeout
      handler.handleSSEEvent({
        type: 'content_block_start',
        data: { index: 0, contentType: 'thinking' },
      });

      // Advance past timeout — should NOT synthesize
      vi.advanceTimersByTime(5000);
      expect(store.messages).toHaveLength(0);

      vi.useRealTimers();
    });

    it('should merge into existing message instead of duplicating on double message_stop', () => {
      // Simulate: safety timeout fires, then real message_stop arrives
      store.streamingState = {
        isStreaming: true,
        streamContent: 'First content',
        currentMessageId: 'msg-dup',
        isThinking: false,
        thinkingStartedAt: null,
      };

      // First message_stop (e.g., from safety timeout)
      handler.handleSSEEvent({
        type: 'message_stop',
        data: { messageId: 'msg-dup', stopReason: 'question_pending' },
      });
      expect(store.messages).toHaveLength(1);
      expect(store.messages[0]!.content).toBe('First content');

      // Set up streaming state again as if AI continued
      store.streamingState = {
        isStreaming: true,
        streamContent: 'Updated content',
        currentMessageId: 'msg-dup',
        isThinking: false,
        thinkingStartedAt: null,
      };

      // Second message_stop (real one) — should merge, not duplicate
      handler.handleSSEEvent({
        type: 'message_stop',
        data: { messageId: 'msg-dup', stopReason: 'end_turn' },
      });

      // Only ONE message, not two
      expect(store.messages).toHaveLength(1);
      expect(store.messages[0]!.id).toBe('msg-dup');
      expect(store.messages[0]!.content).toBe('Updated content');
    });
  });

  describe('handleError — parseErrorMessage', () => {
    it('should extract nested JSON error message from API Error wrapper', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'api_error',
          message:
            'API Error: 429 {"type":"error","error":{"type":"rate_limit_error","message":"you have reached your session usage limit"}}',
          retryable: false,
        },
      });

      expect(store.error).toBe('you have reached your session usage limit');
      expect(store.streamingState.isStreaming).toBe(false);
    });

    it('should extract top-level message from JSON when error.message is absent', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'api_error',
          message: 'API Error: 500 {"message":"Internal server error"}',
          retryable: false,
        },
      });

      expect(store.error).toBe('Internal server error');
    });

    it('should strip "API Error: NNN" prefix when no JSON is present', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'api_error',
          message: 'API Error: 503 Service temporarily unavailable',
          retryable: false,
        },
      });

      expect(store.error).toBe('Service temporarily unavailable');
    });

    it('should fall back to errorCode: rawMessage when stripping yields empty', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'unknown_error',
          message: '',
          retryable: false,
        },
      });

      expect(store.error).toBe('unknown_error: ');
    });

    it('should pass through plain text error messages unchanged', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'connection_error',
          message: 'Connection refused',
          retryable: false,
        },
      });

      expect(store.error).toBe('Connection refused');
    });

    it('should handle malformed JSON gracefully — fall through to prefix stripping', () => {
      handler.handleSSEEvent({
        type: 'error',
        data: {
          errorCode: 'api_error',
          message: 'API Error: 400 {not valid json at all}',
          retryable: false,
        },
      });

      // Falls through JSON parse, strips prefix
      expect(store.error).toBe('{not valid json at all}');
    });
  });
});
