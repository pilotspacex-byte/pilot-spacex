import { describe, it, expect, vi } from 'vitest';

// Mock supabase before importing SSEClient (top-level env dependency)
vi.mock('@/lib/supabase', () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

import { SSEClient } from '../sse-client';

/**
 * Tests for SSEClient.parseEvents (exposed indirectly through connect flow).
 *
 * We test the private parseEvents method by instantiating SSEClient and
 * using its behavior through a minimal harness that accesses the private method.
 */

// Access private parseEvents for unit testing
function createParser() {
  const client = new SSEClient({
    url: 'http://localhost/test',
    onMessage: () => {},
  });
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (buffer: string) => (client as any).parseEvents(buffer);
}

describe('SSEClient.parseEvents', () => {
  const parse = createParser();

  it('parses a complete event block', () => {
    const buffer = 'event:phase\ndata:{"name":"test","status":"pending"}\n\n';
    const { parsed, remaining } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('phase');
    expect(parsed[0].data).toEqual({ name: 'test', status: 'pending' });
    expect(remaining).toBe('');
  });

  it('parses multiple complete events', () => {
    const buffer =
      'event:phase\ndata:{"name":"a","status":"pending"}\n\n' +
      'event:phase\ndata:{"name":"b","status":"complete"}\n\n';
    const { parsed, remaining } = parse(buffer);

    expect(parsed).toHaveLength(2);
    expect(parsed[0].data).toEqual({ name: 'a', status: 'pending' });
    expect(parsed[1].data).toEqual({ name: 'b', status: 'complete' });
    expect(remaining).toBe('');
  });

  it('keeps incomplete event in remaining buffer', () => {
    const buffer = 'event:phase\ndata:{"name":"test"';
    const { parsed, remaining } = parse(buffer);

    expect(parsed).toHaveLength(0);
    expect(remaining).toBe('event:phase\ndata:{"name":"test"');
  });

  it('handles event: line split from data: line across chunks', () => {
    // Chunk 1: just the event line
    const result1 = parse('event:context_summary\n');
    expect(result1.parsed).toHaveLength(0);
    expect(result1.remaining).toContain('event:context_summary');

    // Chunk 2: remaining from chunk1 + data line + double newline
    const buffer2 = result1.remaining + 'data:{"issueIdentifier":"PS-1","summaryText":"test"}\n\n';
    const result2 = parse(buffer2);
    expect(result2.parsed).toHaveLength(1);
    expect(result2.parsed[0].type).toBe('context_summary');
    expect(result2.parsed[0].data).toEqual({
      issueIdentifier: 'PS-1',
      summaryText: 'test',
    });
    expect(result2.remaining).toBe('');
  });

  it('handles data split mid-JSON across chunks', () => {
    // Chunk 1: event + partial data
    const result1 = parse('event:related_issues\ndata:{"items":[{"id"');
    expect(result1.parsed).toHaveLength(0);

    // Chunk 2: rest of data
    const buffer2 = result1.remaining + ':"1"}]}\n\n';
    const result2 = parse(buffer2);
    expect(result2.parsed).toHaveLength(1);
    expect(result2.parsed[0].type).toBe('related_issues');
    expect(result2.parsed[0].data).toEqual({ items: [{ id: '1' }] });
  });

  it('handles multi-line data fields', () => {
    const buffer = 'event:test\ndata:line1\ndata:line2\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(1);
    // Multi-line data should be joined with newlines — non-JSON fallback
    expect(parsed[0].data).toBe('line1\nline2');
  });

  it('ignores comment lines', () => {
    const buffer = ':heartbeat\nevent:phase\ndata:{"ok":true}\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('phase');
  });

  it('ignores id and retry fields', () => {
    const buffer = 'id:123\nretry:5000\nevent:phase\ndata:{"ok":true}\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('phase');
  });

  it('skips events with event type but no data', () => {
    const buffer = 'event:empty\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(0);
  });

  it('skips empty segments between double-newlines', () => {
    const buffer = '\n\nevent:phase\ndata:{"a":1}\n\n\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('phase');
  });

  it('returns non-JSON data as string fallback', () => {
    const buffer = 'event:test\ndata:not valid json\n\n';
    const { parsed } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].data).toBe('not valid json');
  });

  it('handles complete event followed by incomplete event', () => {
    const buffer = 'event:a\ndata:{"x":1}\n\nevent:b\ndata:{"y"';
    const { parsed, remaining } = parse(buffer);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe('a');
    expect(remaining).toBe('event:b\ndata:{"y"');
  });
});
