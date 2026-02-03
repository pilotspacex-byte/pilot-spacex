/**
 * Unit tests for ContentUpdateEvent handling in PilotSpaceStore.
 *
 * Task 6: Tests for content_update SSE event type + handler.
 *
 * @module stores/ai/__tests__/content-update-handler.test
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock supabase before any store imports (avoids missing env error)
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

import { PilotSpaceStore } from '../PilotSpaceStore';
import { PilotSpaceStreamHandler } from '../PilotSpaceStreamHandler';
import type { AIStore } from '../AIStore';
import { isContentUpdateEvent, type ContentUpdateEvent, type SSEEvent } from '../types/events';

describe('ContentUpdateEvent type guard', () => {
  it('should identify content_update event type correctly', () => {
    const validEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] },
        issueData: null,
        afterBlockId: null,
      },
    };

    expect(isContentUpdateEvent(validEvent)).toBe(true);
  });

  it('should reject invalid content_update events with missing fields', () => {
    const invalidEvent1: SSEEvent = {
      type: 'content_update',
      data: {
        // Missing noteId
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    const invalidEvent2: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        // Missing operation
        blockId: 'block-456',
        markdown: null,
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    // Type guard should validate required fields
    expect(isContentUpdateEvent(invalidEvent1)).toBe(false);
    expect(isContentUpdateEvent(invalidEvent2)).toBe(false);
  });

  it('should accept all operation types', () => {
    const replaceBlockEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    const appendBlocksEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'bulletList' },
        issueData: null,
        afterBlockId: 'block-100',
      },
    };

    const insertIssueEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: null,
        markdown: null,
        content: null,
        issueData: {
          issueId: 'issue-789',
          issueKey: 'PROJ-42',
          title: 'Fix bug',
          type: 'bug',
          state: 'backlog',
          priority: 'high',
          sourceBlockId: 'block-50',
        },
        afterBlockId: null,
      },
    };

    expect(isContentUpdateEvent(replaceBlockEvent)).toBe(true);
    expect(isContentUpdateEvent(appendBlocksEvent)).toBe(true);
    expect(isContentUpdateEvent(insertIssueEvent)).toBe(true);
  });
});

describe('PilotSpaceStore.handleContentUpdate', () => {
  let store: PilotSpaceStore;
  let mockRootStore: AIStore;

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
  });

  it('should add content_update to pendingContentUpdates array', () => {
    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph', content: [{ type: 'text', text: 'Updated text' }] },
        issueData: null,
        afterBlockId: null,
      },
    };

    expect(store.pendingContentUpdates).toEqual([]);

    store.handleContentUpdate(event);

    expect(store.pendingContentUpdates).toHaveLength(1);
    expect(store.pendingContentUpdates[0]).toEqual(event.data);
  });

  it('should handle replace_block operation with blockId + content', () => {
    const content = {
      type: 'paragraph',
      content: [{ type: 'text', text: 'Replaced content' }],
    };

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content,
        issueData: null,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(event);

    expect(store.pendingContentUpdates).toHaveLength(1);
    const stored = store.pendingContentUpdates[0];
    expect(stored?.noteId).toBe('note-123');
    expect(stored?.operation).toBe('replace_block');
    expect(stored?.blockId).toBe('block-456');
    expect(stored?.content).toEqual(content);
  });

  it('should handle append_blocks operation with afterBlockId + content', () => {
    const content = {
      type: 'bulletList',
      content: [{ type: 'listItem', content: [{ type: 'paragraph', content: [] }] }],
    };

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content,
        issueData: null,
        afterBlockId: 'block-100',
      },
    };

    store.handleContentUpdate(event);

    expect(store.pendingContentUpdates).toHaveLength(1);
    const stored = store.pendingContentUpdates[0];
    expect(stored?.noteId).toBe('note-123');
    expect(stored?.operation).toBe('append_blocks');
    expect(stored?.afterBlockId).toBe('block-100');
    expect(stored?.content).toEqual(content);
    expect(stored?.blockId).toBeNull();
  });

  it('should handle insert_inline_issue from MCP tool (no issueId/issueKey)', () => {
    // MCP tools only provide title/description/priority/type — no issueId
    const issueData = {
      title: 'Implement search feature',
      description: 'Add full-text search to notes',
      type: 'task' as const,
      priority: 'medium' as const,
    };

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: 'block-50',
        markdown: null,
        content: null,
        issueData,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(event);

    expect(store.pendingContentUpdates).toHaveLength(1);
    const stored = store.pendingContentUpdates[0];
    expect(stored?.operation).toBe('insert_inline_issue');
    expect(stored?.issueData?.title).toBe('Implement search feature');
    expect(stored?.issueData?.issueId).toBeUndefined();
    expect(stored?.issueData?.issueKey).toBeUndefined();
  });

  it('should handle insert_inline_issue operation with issueData', () => {
    const issueData = {
      issueId: 'issue-789',
      issueKey: 'PROJ-42',
      title: 'Fix authentication bug',
      type: 'bug' as const,
      state: 'backlog' as const,
      priority: 'urgent' as const,
      sourceBlockId: 'block-50',
    };

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: null,
        markdown: null,
        content: null,
        issueData,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(event);

    expect(store.pendingContentUpdates).toHaveLength(1);
    const stored = store.pendingContentUpdates[0];
    expect(stored?.noteId).toBe('note-123');
    expect(stored?.operation).toBe('insert_inline_issue');
    expect(stored?.issueData).toEqual(issueData);
    expect(stored?.blockId).toBeNull();
    expect(stored?.content).toBeNull();
  });

  it('should not exceed max pending updates buffer (100 max, FIFO eviction)', () => {
    // Fill buffer with 100 events
    for (let i = 0; i < 100; i++) {
      const event: ContentUpdateEvent = {
        type: 'content_update',
        data: {
          noteId: `note-${i}`,
          operation: 'replace_block',
          blockId: `block-${i}`,
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        },
      };
      store.handleContentUpdate(event);
    }

    expect(store.pendingContentUpdates).toHaveLength(100);
    expect(store.pendingContentUpdates[0]?.noteId).toBe('note-0');

    // Add 101st event - should evict note-0
    const newEvent: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-new',
        operation: 'replace_block',
        blockId: 'block-new',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };
    store.handleContentUpdate(newEvent);

    expect(store.pendingContentUpdates).toHaveLength(100);
    expect(store.pendingContentUpdates[0]?.noteId).toBe('note-1'); // note-0 evicted
    expect(store.pendingContentUpdates[99]?.noteId).toBe('note-new');
  });
});

describe('PilotSpaceStreamHandler.handleSSEEvent routing', () => {
  let store: PilotSpaceStore;
  let streamHandler: PilotSpaceStreamHandler;
  let mockRootStore: AIStore;

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
    streamHandler = new PilotSpaceStreamHandler(store);
    vi.spyOn(store, 'handleContentUpdate');
  });

  it('should route content_update events to handleContentUpdate', () => {
    const sseEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    streamHandler.handleSSEEvent(sseEvent);

    expect(store.handleContentUpdate).toHaveBeenCalledTimes(1);
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe('content_update');
  });

  it('should parse text_delta and content_update events from SSE buffer', () => {
    const textDeltaBuffer = `event:text_delta\ndata:${JSON.stringify({ messageId: 'msg-123', delta: 'Hello world' })}\n\n`;
    const contentUpdateBuffer = `event:content_update\ndata:${JSON.stringify({
      noteId: 'note-123',
      operation: 'replace_block',
      blockId: 'block-456',
      markdown: null,
      content: { type: 'paragraph' },
      issueData: null,
      afterBlockId: null,
    })}\n\n`;

    streamHandler.handleSSEEvent(textDeltaEvent);

    // Streaming state should be updated
    expect(store.streamContent).toContain('Hello world');

    // Then send a content_update event
    const contentUpdateEvent: SSEEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    streamHandler.handleSSEEvent(contentUpdateEvent);

    // Both should work independently
    expect(store.handleContentUpdate).toHaveBeenCalledTimes(1);
    expect(store.pendingContentUpdates).toHaveLength(1);
    expect(store.streamContent).toContain('Hello world'); // Text delta still there
  });
});

describe('ContentUpdateEvent serialization', () => {
  it('should parse content_update from raw SSE data string', () => {
    const rawData = JSON.stringify({
      noteId: 'note-123',
      operation: 'replace_block',
      blockId: 'block-456',
      markdown: null,
      content: { type: 'paragraph', content: [] },
      issueData: null,
      afterBlockId: null,
    });

    const parsed = JSON.parse(rawData);
    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: parsed,
    };

    expect(isContentUpdateEvent(event)).toBe(true);
    expect(event.data.noteId).toBe('note-123');
    expect(event.data.operation).toBe('replace_block');
  });

  it('should handle missing optional fields gracefully (null blockId, null issueData)', () => {
    const eventWithNulls: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: 'block-100',
      },
    };

    expect(isContentUpdateEvent(eventWithNulls)).toBe(true);
    expect(eventWithNulls.data.blockId).toBeNull();
    expect(eventWithNulls.data.issueData).toBeNull();
  });
});

describe('pendingContentUpdates observable', () => {
  let store: PilotSpaceStore;
  let mockRootStore: AIStore;

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
  });

  it('should be observable and trigger MobX reactions', async () => {
    const reactionCallback = vi.fn();

    // Set up reaction (MobX autorun equivalent)
    const { reaction } = await import('mobx');
    reaction(() => store.pendingContentUpdates.length, reactionCallback);

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(event);

    // Reaction should fire
    expect(reactionCallback).toHaveBeenCalled();
  });

  it('should support consuming (removing) processed updates', () => {
    const event1: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    const event2: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-789',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'bulletList' },
        issueData: null,
        afterBlockId: 'block-100',
      },
    };

    store.handleContentUpdate(event1);
    store.handleContentUpdate(event2);

    expect(store.pendingContentUpdates).toHaveLength(2);

    // Consume event for note-123
    const consumed = store.consumeContentUpdate('note-123');

    expect(consumed).toEqual(event1.data);
    expect(store.pendingContentUpdates).toHaveLength(1);
    expect(store.pendingContentUpdates[0]?.noteId).toBe('note-789');

    // Try to consume non-existent noteId
    const notFound = store.consumeContentUpdate('note-999');
    expect(notFound).toBeUndefined();
    expect(store.pendingContentUpdates).toHaveLength(1);
  });

  it('should clear all pending updates on clearConversation()', () => {
    const event1: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'block-456',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      },
    };

    const event2: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: 'note-789',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'bulletList' },
        issueData: null,
        afterBlockId: 'block-100',
      },
    };

    store.handleContentUpdate(event1);
    store.handleContentUpdate(event2);

    expect(store.pendingContentUpdates).toHaveLength(2);

    store.clearConversation();

    expect(store.pendingContentUpdates).toEqual([]);
  });
});
