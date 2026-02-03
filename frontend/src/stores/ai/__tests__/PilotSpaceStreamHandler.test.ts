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
      store.addPendingToolCall({ id: 'tc-1', name: 'extract_issues', input: {}, status: 'pending' });

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
