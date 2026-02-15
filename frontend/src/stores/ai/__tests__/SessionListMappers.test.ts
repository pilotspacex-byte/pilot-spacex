/**
 * Unit tests for SessionListMappers - tool call mapping on session resume.
 */
import { describe, it, expect } from 'vitest';
import { mapMessageResponse } from '../SessionListMappers';
import type { MessageResponse } from '../types/session';

describe('mapMessageResponse', () => {
  const baseMsg: MessageResponse = {
    id: 'msg-1',
    role: 'assistant',
    content: 'Hello',
    timestamp: '2025-02-15T10:00:00Z',
  };

  it('returns undefined toolCalls when no tool_calls in response', () => {
    const result = mapMessageResponse(baseMsg, 'fallback');
    expect(result.toolCalls).toBeUndefined();
  });

  it('maps tool_calls with snake_case to camelCase', () => {
    const msg: MessageResponse = {
      ...baseMsg,
      tool_calls: [
        {
          id: 'call_1',
          name: 'get_issue',
          input: { issue_id: '123' },
          output: { title: 'Bug fix' },
          status: 'completed',
          error_message: undefined,
          duration_ms: 150,
        },
      ],
    };
    const result = mapMessageResponse(msg, 'fallback');
    expect(result.toolCalls).toBeDefined();
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0]).toEqual({
      id: 'call_1',
      name: 'get_issue',
      input: { issue_id: '123' },
      output: { title: 'Bug fix' },
      status: 'completed',
      errorMessage: undefined,
      durationMs: 150,
    });
  });

  it('maps multiple tool calls', () => {
    const msg: MessageResponse = {
      ...baseMsg,
      tool_calls: [
        { id: 'a', name: 'search', input: {}, status: 'completed' },
        {
          id: 'b',
          name: 'create_issue',
          input: { title: 'new' },
          status: 'failed',
          error_message: 'denied',
        },
      ],
    };
    const result = mapMessageResponse(msg, 'fallback');
    expect(result.toolCalls).toHaveLength(2);
    const [first, second] = result.toolCalls!;
    expect(first!.name).toBe('search');
    expect(second!.status).toBe('failed');
    expect(second!.errorMessage).toBe('denied');
  });

  it('returns undefined toolCalls for empty array', () => {
    const msg: MessageResponse = { ...baseMsg, tool_calls: [] };
    const result = mapMessageResponse(msg, 'fallback');
    expect(result.toolCalls).toBeUndefined();
  });

  it('maps tool calls alongside content_blocks and thinking_blocks', () => {
    const msg: MessageResponse = {
      ...baseMsg,
      content_blocks: [
        { type: 'text' as const, content: 'Let me check...' },
        { type: 'tool_call' as const, toolCallId: 'call_1' },
      ],
      thinking_blocks: [{ content: 'I should look up the issue', blockIndex: 0 }],
      tool_calls: [
        {
          id: 'call_1',
          name: 'get_issue',
          input: { id: '42' },
          output: { state: 'open' },
          status: 'completed',
        },
      ],
    };
    const result = mapMessageResponse(msg, 'fallback');
    expect(result.contentBlocks).toHaveLength(2);
    expect(result.thinkingBlocks).toHaveLength(1);
    expect(result.toolCalls).toHaveLength(1);
    expect(result.toolCalls![0]!.output).toEqual({ state: 'open' });
  });
});
