/**
 * Unit tests for handleReplaceContent and handleRemoveContent handlers.
 *
 * Tests the new content_update operations: replace_content, remove_content.
 * These handlers find/replace text within ProseMirror blocks.
 *
 * @module features/notes/editor/__tests__/content-update-replace-remove.test
 */

import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

import type { Editor } from '@tiptap/core';
import type { ContentUpdateData } from '@/stores/ai/types/events';
import { handleReplaceContent, handleRemoveContent } from '../hooks/contentUpdateHandlers';

// ---------------------------------------------------------------------------
// Mock editor factory
// ---------------------------------------------------------------------------

interface MockTextNode {
  isText: true;
  text: string;
}

interface MockBlock {
  isTextblock: boolean;
  attrs: { blockId: string };
  nodeSize: number;
  descendants: (callback: (child: MockTextNode, offset: number) => boolean | void) => void;
}

function createMockEditor(blocks: Array<{ blockId: string; text: string }>) {
  const mockBlocks: MockBlock[] = blocks.map((b) => {
    const textNode: MockTextNode = { isText: true, text: b.text };
    return {
      isTextblock: true,
      attrs: { blockId: b.blockId },
      nodeSize: b.text.length + 2, // +2 for open/close tags
      descendants: (callback: (child: MockTextNode, offset: number) => boolean | void) => {
        callback(textNode, 0);
      },
    };
  });

  // Track cumulative positions
  let pos = 0;
  const blockPositions: Array<{ block: MockBlock; pos: number }> = [];
  for (const block of mockBlocks) {
    blockPositions.push({ block, pos });
    pos += block.nodeSize;
  }

  const mockTr = {
    replaceWith: vi.fn().mockReturnThis(),
  };

  const mockSchema = {
    text: vi.fn((str: string) => ({ isText: true, text: str })),
  };

  const mockDoc = {
    descendants: vi.fn((callback: (node: MockBlock, pos: number) => boolean | void) => {
      for (const { block, pos } of blockPositions) {
        const result = callback(block, pos);
        if (result === false) return;
      }
    }),
  };

  const mockView = {
    dispatch: vi.fn(),
  };

  const mockEditor = {
    state: {
      doc: mockDoc,
      tr: mockTr,
      schema: mockSchema,
    },
    view: mockView,
  };

  return {
    editor: mockEditor as unknown as Editor,
    tr: mockTr,
    view: mockView,
    schema: mockSchema,
  };
}

// ---------------------------------------------------------------------------
// handleReplaceContent tests
// ---------------------------------------------------------------------------

describe('handleReplaceContent', () => {
  it('should replace matching text in a single block', () => {
    const { editor, tr, view, schema } = createMockEditor([
      { blockId: 'blk-1', text: 'Hello world, welcome to the world' },
    ]);

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'replace_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      oldPattern: 'world',
      newContent: 'universe',
    };

    handleReplaceContent(editor, update);

    expect(schema.text).toHaveBeenCalledWith('universe');
    expect(tr.replaceWith).toHaveBeenCalled();
    expect(view.dispatch).toHaveBeenCalledWith(tr);
  });

  it('should only replace in specified blockIds', () => {
    const { editor, tr, view } = createMockEditor([
      { blockId: 'blk-1', text: 'Replace me' },
      { blockId: 'blk-2', text: 'Replace me too' },
    ]);

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'replace_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      oldPattern: 'Replace',
      newContent: 'Changed',
      blockIds: ['blk-2'],
    };

    handleReplaceContent(editor, update);

    // Should have been called once (only for blk-2)
    expect(tr.replaceWith).toHaveBeenCalledTimes(1);
    expect(view.dispatch).toHaveBeenCalled();
  });

  it('should warn when oldPattern is missing', () => {
    const { editor } = createMockEditor([{ blockId: 'blk-1', text: 'Some text' }]);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'replace_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      oldPattern: null,
      newContent: 'replacement',
    };

    handleReplaceContent(editor, update);

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('missing oldPattern'));
    warnSpy.mockRestore();
  });

  it('should warn when newContent is missing', () => {
    const { editor } = createMockEditor([{ blockId: 'blk-1', text: 'Some text' }]);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'replace_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      oldPattern: 'Some',
      newContent: undefined as unknown as string,
    };

    handleReplaceContent(editor, update);

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('missing newContent'));
    warnSpy.mockRestore();
  });

  it('should warn when pattern is not found', () => {
    const { editor, tr, view } = createMockEditor([{ blockId: 'blk-1', text: 'Hello world' }]);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'replace_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      oldPattern: 'nonexistent',
      newContent: 'replacement',
    };

    handleReplaceContent(editor, update);

    expect(tr.replaceWith).not.toHaveBeenCalled();
    expect(view.dispatch).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('pattern not found'),
      expect.any(Object)
    );
    warnSpy.mockRestore();
  });
});

// ---------------------------------------------------------------------------
// handleRemoveContent tests
// ---------------------------------------------------------------------------

describe('handleRemoveContent', () => {
  it('should remove matching text from blocks', () => {
    const { editor, tr, view, schema } = createMockEditor([
      { blockId: 'blk-1', text: 'Remove this word please' },
    ]);

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'remove_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      pattern: 'this word ',
    };

    handleRemoveContent(editor, update);

    // Should call schema.text with empty string for removal
    expect(schema.text).toHaveBeenCalledWith('');
    expect(tr.replaceWith).toHaveBeenCalled();
    expect(view.dispatch).toHaveBeenCalled();
  });

  it('should warn when pattern is missing', () => {
    const { editor } = createMockEditor([{ blockId: 'blk-1', text: 'Some text' }]);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'remove_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      pattern: null,
    };

    handleRemoveContent(editor, update);

    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('missing pattern'));
    warnSpy.mockRestore();
  });

  it('should respect blockIds scope', () => {
    const { editor, tr, view } = createMockEditor([
      { blockId: 'blk-1', text: 'Remove me' },
      { blockId: 'blk-2', text: 'Remove me too' },
    ]);

    const update: ContentUpdateData = {
      noteId: 'note-1',
      operation: 'remove_content',
      blockId: null,
      markdown: null,
      content: null,
      issueData: null,
      afterBlockId: null,
      pattern: 'Remove',
      blockIds: ['blk-1'],
    };

    handleRemoveContent(editor, update);

    // Should only replace in blk-1
    expect(tr.replaceWith).toHaveBeenCalledTimes(1);
    expect(view.dispatch).toHaveBeenCalled();
  });
});
