/**
 * Integration tests for the content_update SSE flow.
 *
 * Tests the complete frontend pipeline from raw SSE event data → parse →
 * PilotSpaceStore.handleContentUpdate() → pendingContentUpdates →
 * useContentUpdates hook → TipTap editor commands.
 *
 * Unlike unit tests that test store or hook in isolation, these integration
 * tests wire the full chain together and verify end-to-end behavior.
 *
 * @module features/notes/editor/__tests__/content-update-flow.integration.test
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { runInAction } from 'mobx';

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

import { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { AIStore } from '@/stores/ai/AIStore';
import {
  isContentUpdateEvent,
  type ContentUpdateData,
  type ContentUpdateEvent,
} from '@/stores/ai/types/events';
import { useContentUpdates } from '../hooks/useContentUpdates';
import type { Editor } from '@tiptap/core';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Parse raw SSE event string (as received from backend) into an event object.
 *
 * Format: "event: content_update\ndata: {JSON}\n\n"
 */
function parseSSEEvent(raw: string): { type: string; data: unknown } {
  let type = '';
  let data: unknown = null;

  for (const line of raw.trim().split('\n')) {
    if (line.startsWith('event: ')) {
      type = line.slice('event: '.length);
    } else if (line.startsWith('data: ')) {
      data = JSON.parse(line.slice('data: '.length));
    }
  }

  return { type, data };
}

/**
 * Create a mock TipTap Editor with all methods needed by useContentUpdates.
 */
function createMockEditor(overrides?: Partial<Record<string, unknown>>): Editor {
  const mockChain = {
    deleteRange: vi.fn().mockReturnThis(),
    insertContentAt: vi.fn().mockReturnThis(),
    run: vi.fn().mockReturnThis(),
  };

  const mockDoc = {
    descendants: vi.fn(),
    resolve: vi.fn().mockReturnValue({
      parent: { attrs: { id: null } },
    }),
    content: { size: 200 },
  };

  const mockEditor = {
    state: {
      selection: { from: 0, to: 0 },
      doc: mockDoc,
    },
    chain: vi.fn().mockReturnValue(mockChain),
    commands: {
      insertContentAt: vi.fn(),
      insertInlineIssue: vi.fn(),
    },
    on: vi.fn(),
    off: vi.fn(),
    destroy: vi.fn(),
    ...overrides,
  };

  return mockEditor as unknown as Editor;
}

/**
 * Simulate finding a block in the editor document by ID.
 */
function mockDocFindBlock(editor: Editor, blockId: string, pos: number, nodeSize: number): void {
  const mockDoc = editor.state.doc as unknown as {
    descendants: ReturnType<typeof vi.fn>;
  };
  mockDoc.descendants.mockImplementation(
    (callback: (node: unknown, pos: number) => boolean | void) => {
      const node = { attrs: { id: blockId }, nodeSize };
      callback(node, pos);
    }
  );
}

// ---------------------------------------------------------------------------
// Raw SSE data fixtures (matching backend _emit_*_event output)
// ---------------------------------------------------------------------------

const NOTE_ID = 'note-integration-001';
const BLOCK_ID = 'block-target-42';
const AFTER_BLOCK_ID = 'block-anchor-99';

const RAW_REPLACE_BLOCK_SSE = `event: content_update\ndata: ${JSON.stringify({
  noteId: NOTE_ID,
  operation: 'replace_block',
  blockId: BLOCK_ID,
  markdown: '## Updated heading\n\nParagraph text.',
  content: null,
  issueData: null,
  afterBlockId: null,
})}\n\n`;

const RAW_APPEND_BLOCKS_SSE = `event: content_update\ndata: ${JSON.stringify({
  noteId: NOTE_ID,
  operation: 'append_blocks',
  blockId: 'new-block-1',
  markdown: '- Bullet one\n- Bullet two',
  content: null,
  issueData: null,
  afterBlockId: AFTER_BLOCK_ID,
})}\n\n`;

const RAW_INSERT_ISSUE_SSE = `event: content_update\ndata: ${JSON.stringify({
  noteId: NOTE_ID,
  operation: 'insert_inline_issue',
  blockId: null,
  markdown: null,
  content: null,
  issueData: {
    issueId: 'issue-789',
    issueKey: 'PROJ-42',
    title: 'Fix authentication bug',
    type: 'bug',
    state: 'backlog',
    priority: 'urgent',
    sourceBlockId: 'block-50',
  },
  afterBlockId: null,
})}\n\n`;

// ===========================================================================
// Test 1: Replace block — SSE → store → editor
// ===========================================================================

describe('Integration: replace_block SSE → store → editor', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should parse raw SSE, route through store, and call editor chain for replace_block', async () => {
    // Step 1: Parse raw SSE (simulating SSEClient.onmessage)
    const parsed = parseSSEEvent(RAW_REPLACE_BLOCK_SSE);
    expect(parsed.type).toBe('content_update');

    const event = { type: parsed.type, data: parsed.data } as ContentUpdateEvent;
    expect(isContentUpdateEvent(event)).toBe(true);

    // Step 2: Verify store accepts the event (test store independently first)
    const verifyStore = new PilotSpaceStore({} as AIStore);
    verifyStore.handleContentUpdate(event);
    expect(verifyStore.pendingContentUpdates).toHaveLength(1);
    expect(verifyStore.pendingContentUpdates[0]?.noteId).toBe(NOTE_ID);
    expect(verifyStore.pendingContentUpdates[0]?.operation).toBe('replace_block');
    expect(verifyStore.pendingContentUpdates[0]?.markdown).toBe(
      '## Updated heading\n\nParagraph text.'
    );

    // Step 3: Wire useContentUpdates hook FIRST, then push update
    const targetPos = 10;
    const targetSize = 30;
    mockDocFindBlock(editor, BLOCK_ID, targetPos, targetSize);

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    // Step 4: Feed to store (hook reaction triggers)
    store.handleContentUpdate(event);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Step 5: Verify editor received correct commands
    const chain = editor.chain();
    expect(chain.deleteRange).toHaveBeenCalledWith({
      from: targetPos,
      to: targetPos + targetSize,
    });
    expect(chain.insertContentAt).toHaveBeenCalledWith(
      targetPos,
      '## Updated heading\n\nParagraph text.'
    );
    expect(chain.run).toHaveBeenCalled();
  });
});

// ===========================================================================
// Test 2: Append blocks with markdown — SSE → store → editor
// ===========================================================================

describe('Integration: append_blocks SSE → store → editor', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should parse raw SSE, route through store, and call insertContentAt for append_blocks', async () => {
    // Step 1: Parse
    const parsed = parseSSEEvent(RAW_APPEND_BLOCKS_SSE);
    const event = { type: parsed.type, data: parsed.data } as ContentUpdateEvent;
    expect(isContentUpdateEvent(event)).toBe(true);

    // Step 2: Mock finding the afterBlock in editor
    const anchorPos = 80;
    const anchorSize = 20;
    mockDocFindBlock(editor, AFTER_BLOCK_ID, anchorPos, anchorSize);

    // Step 3: Mount hook first, then push update
    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    // Step 4: Feed to store (hook reaction will fire)
    store.handleContentUpdate(event);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Step 5: Verify editor.commands.insertContentAt called with correct position
    expect(editor.commands.insertContentAt).toHaveBeenCalledWith(
      anchorPos + anchorSize,
      '- Bullet one\n- Bullet two'
    );
  });

  it('should append at document end when afterBlockId block not found', async () => {
    const noAnchorEvent: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: NOTE_ID,
        operation: 'append_blocks',
        blockId: null,
        markdown: 'End-of-doc content',
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    // Mock doc.descendants to never find the block
    const mockDoc = editor.state.doc as unknown as {
      descendants: ReturnType<typeof vi.fn>;
    };
    mockDoc.descendants.mockImplementation(() => {
      // no block found
    });

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));
    store.handleContentUpdate(noAnchorEvent);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Should fall back to doc.content.size
    expect(editor.commands.insertContentAt).toHaveBeenCalledWith(
      200, // mockDoc content.size
      'End-of-doc content'
    );
  });
});

// ===========================================================================
// Test 3: Insert inline issue — SSE → store → editor
// ===========================================================================

describe('Integration: insert_inline_issue SSE → store → editor', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should parse raw SSE, route through store, and call insertInlineIssue', async () => {
    const parsed = parseSSEEvent(RAW_INSERT_ISSUE_SSE);
    const event = { type: parsed.type, data: parsed.data } as ContentUpdateEvent;
    expect(isContentUpdateEvent(event)).toBe(true);

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));
    store.handleContentUpdate(event);

    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(editor.commands.insertInlineIssue).toHaveBeenCalledWith({
      issueId: 'issue-789',
      issueKey: 'PROJ-42',
      title: 'Fix authentication bug',
      type: 'bug',
      state: 'backlog',
      priority: 'urgent',
      sourceBlockId: 'block-50',
      isNew: true,
    });
  });
});

// ===========================================================================
// Test 4: Conflict detection — user editing block → AI update skipped
// ===========================================================================

describe('Integration: conflict detection', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should skip replace_block when user is editing the target block', async () => {
    const targetBlockId = 'block-user-editing';

    // Simulate user cursor in the target block
    const mockResolve = vi.fn().mockReturnValue({
      parent: { attrs: { id: targetBlockId } },
    });
    editor.state.doc.resolve = mockResolve;

    // Mock finding the block in doc
    mockDocFindBlock(editor, targetBlockId, 10, 20);

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    // Trigger the selectionUpdate handler to set userEditingBlockRef
    const selectionHandler = (editor.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (call: unknown[]) => call[0] === 'selectionUpdate'
    )?.[1] as (() => void) | undefined;
    selectionHandler?.();

    // Now push a replace_block for the same block the user is editing
    const conflictEvent: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: NOTE_ID,
        operation: 'replace_block',
        blockId: targetBlockId,
        markdown: 'AI wants to replace this',
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(conflictEvent);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Editor chain should NOT have been called
    const chain = editor.chain();
    expect(chain.deleteRange).not.toHaveBeenCalled();
    expect(chain.run).not.toHaveBeenCalled();
  });

  it('should allow update when user is editing a different block', async () => {
    const userBlockId = 'block-user-is-here';
    const aiTargetBlockId = 'block-ai-target';

    // User is editing userBlockId
    const mockResolve = vi.fn().mockReturnValue({
      parent: { attrs: { id: userBlockId } },
    });
    editor.state.doc.resolve = mockResolve;

    // AI wants to update aiTargetBlockId (different block)
    mockDocFindBlock(editor, aiTargetBlockId, 50, 15);

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    // Trigger selection handler
    const selectionHandler = (editor.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (call: unknown[]) => call[0] === 'selectionUpdate'
    )?.[1] as (() => void) | undefined;
    selectionHandler?.();

    const event: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: NOTE_ID,
        operation: 'replace_block',
        blockId: aiTargetBlockId,
        markdown: 'AI replaces different block',
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(event);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Should succeed since different block
    const chain = editor.chain();
    expect(chain.deleteRange).toHaveBeenCalledWith({ from: 50, to: 65 });
    expect(chain.run).toHaveBeenCalled();
  });
});

// ===========================================================================
// Test 5: Multiple updates in sequence — batch processing
// ===========================================================================

describe('Integration: multiple sequential updates', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should apply all updates for the same noteId in order', async () => {
    const callOrder: string[] = [];

    // Track call order via side effects
    (editor.commands.insertContentAt as ReturnType<typeof vi.fn>).mockImplementation(
      (_pos: number, content: unknown) => {
        callOrder.push(`append:${typeof content === 'string' ? content : 'json'}`);
      }
    );
    (editor.commands.insertInlineIssue as ReturnType<typeof vi.fn>).mockImplementation(
      (data: { title: string }) => {
        callOrder.push(`issue:${data.title}`);
      }
    );

    // Mock doc size for append operations
    const mockDoc = editor.state.doc as unknown as {
      descendants: ReturnType<typeof vi.fn>;
      content: { size: number };
    };
    mockDoc.descendants.mockImplementation(() => {
      // No specific block found — appends go to end
    });

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    const update1: ContentUpdateData = {
      noteId: NOTE_ID,
      operation: 'append_blocks',
      blockId: null,
      markdown: 'First append',
      content: null,
      issueData: null,
      afterBlockId: null,
    };

    const update2: ContentUpdateData = {
      noteId: NOTE_ID,
      operation: 'append_blocks',
      blockId: null,
      markdown: 'Second append',
      content: null,
      issueData: null,
      afterBlockId: null,
    };

    const update3: ContentUpdateData = {
      noteId: NOTE_ID,
      operation: 'insert_inline_issue',
      blockId: null,
      markdown: null,
      content: null,
      issueData: {
        issueId: 'iss-1',
        issueKey: 'P-1',
        title: 'Third issue',
        type: 'task',
        state: 'backlog',
        priority: 'medium',
      },
      afterBlockId: null,
    };

    // Push all three at once
    runInAction(() => {
      store.pendingContentUpdates.push(update1, update2, update3);
    });

    await new Promise((resolve) => setTimeout(resolve, 100));

    // All three should be processed
    expect(callOrder).toEqual(['append:First append', 'append:Second append', 'issue:Third issue']);

    // Queue should be empty
    expect(store.pendingContentUpdates).toHaveLength(0);
  });
});

// ===========================================================================
// Test 6: Note filtering — events for wrong noteId are ignored
// ===========================================================================

describe('Integration: note filtering', () => {
  let store: PilotSpaceStore;
  let editor: Editor;

  beforeEach(() => {
    store = new PilotSpaceStore({} as AIStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should ignore content_update events for a different noteId', async () => {
    const WRONG_NOTE_ID = 'note-wrong-999';

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    // Push update for a different note
    const wrongNoteUpdate: ContentUpdateEvent = {
      type: 'content_update',
      data: {
        noteId: WRONG_NOTE_ID,
        operation: 'append_blocks',
        blockId: null,
        markdown: 'Should be ignored',
        content: null,
        issueData: null,
        afterBlockId: null,
      },
    };

    store.handleContentUpdate(wrongNoteUpdate);

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Editor should NOT have been called
    expect(editor.commands.insertContentAt).not.toHaveBeenCalled();
    expect(editor.commands.insertInlineIssue).not.toHaveBeenCalled();

    // Update for the wrong note should remain in the queue
    expect(store.pendingContentUpdates).toHaveLength(1);
    expect(store.pendingContentUpdates[0]?.noteId).toBe(WRONG_NOTE_ID);
  });

  it('should process only matching noteId when mixed updates exist', async () => {
    const mockDoc = editor.state.doc as unknown as {
      descendants: ReturnType<typeof vi.fn>;
    };
    mockDoc.descendants.mockImplementation(() => {
      // No specific block found
    });

    renderHook(() => useContentUpdates(editor, store, NOTE_ID));

    const matchingUpdate: ContentUpdateData = {
      noteId: NOTE_ID,
      operation: 'append_blocks',
      blockId: null,
      markdown: 'Matching note',
      content: null,
      issueData: null,
      afterBlockId: null,
    };

    const nonMatchingUpdate: ContentUpdateData = {
      noteId: 'note-other-555',
      operation: 'append_blocks',
      blockId: null,
      markdown: 'Other note',
      content: null,
      issueData: null,
      afterBlockId: null,
    };

    runInAction(() => {
      store.pendingContentUpdates.push(matchingUpdate, nonMatchingUpdate);
    });

    await new Promise((resolve) => setTimeout(resolve, 50));

    // Only matching update should be processed
    expect(editor.commands.insertContentAt).toHaveBeenCalledTimes(1);
    expect(editor.commands.insertContentAt).toHaveBeenCalledWith(200, 'Matching note');

    // Non-matching update remains in queue
    expect(store.pendingContentUpdates).toHaveLength(1);
    expect(store.pendingContentUpdates[0]?.noteId).toBe('note-other-555');
  });
});

// ===========================================================================
// Test: SSE parsing round-trip (backend format → frontend parse → validate)
// ===========================================================================

describe('Integration: SSE parsing round-trip', () => {
  it('should correctly parse all backend SSE event formats', () => {
    const rawEvents = [RAW_REPLACE_BLOCK_SSE, RAW_APPEND_BLOCKS_SSE, RAW_INSERT_ISSUE_SSE];

    for (const raw of rawEvents) {
      const parsed = parseSSEEvent(raw);
      expect(parsed.type).toBe('content_update');

      const event = { type: parsed.type, data: parsed.data };
      expect(isContentUpdateEvent(event)).toBe(true);

      const data = parsed.data as ContentUpdateData;
      expect(data.noteId).toBe(NOTE_ID);
      expect(['replace_block', 'append_blocks', 'insert_inline_issue']).toContain(data.operation);
      // markdown field must be present (string or null)
      expect('markdown' in data).toBe(true);
    }
  });

  it('should reject SSE events with missing required fields', () => {
    const malformedData = JSON.stringify({
      // Missing noteId
      operation: 'replace_block',
      blockId: 'b-1',
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
    });
    const malformedSSE = `event: content_update\ndata: ${malformedData}\n\n`;
    const parsed = parseSSEEvent(malformedSSE);
    const event = { type: parsed.type, data: parsed.data };

    expect(isContentUpdateEvent(event)).toBe(false);
  });

  it('should handle special characters in markdown through SSE', () => {
    const markdown = 'Code: `const x = {"key": "value"}`\nNewline\tTab';
    const sseData = JSON.stringify({
      noteId: NOTE_ID,
      operation: 'replace_block',
      blockId: 'b-special',
      markdown,
      content: null,
      issueData: null,
      afterBlockId: null,
    });
    const raw = `event: content_update\ndata: ${sseData}\n\n`;

    const parsed = parseSSEEvent(raw);
    const data = parsed.data as ContentUpdateData;

    expect(data.markdown).toBe(markdown);
    expect(data.markdown).toContain('{"key": "value"}');
    expect(data.markdown).toContain('\n');
    expect(data.markdown).toContain('\t');
  });
});
