/**
 * Unit tests for useContentUpdates hook and highlightBlock helper.
 * @module features/notes/editor/hooks/__tests__/useContentUpdates.test
 */
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { runInAction } from 'mobx';

// Mock supabase before any store imports
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

import { useContentUpdates, highlightBlock } from '../useContentUpdates';
import { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { AIStore } from '@/stores/ai/AIStore';
import type { ContentUpdateData } from '@/stores/ai/types/events';
import type { Editor } from '@tiptap/core';

/**
 * Create a mock TipTap Editor with all required methods.
 */
function createMockEditor(overrides?: Partial<Editor>): Editor {
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
    content: { size: 100 },
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

describe('useContentUpdates', () => {
  let store: PilotSpaceStore;
  let mockRootStore: AIStore;
  let editor: Editor;

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
    editor = createMockEditor();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('hook initialization', () => {
    it('should set up selection change handler on mount', () => {
      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      expect(editor.on).toHaveBeenCalledWith('selectionUpdate', expect.any(Function));
    });

    it('should clean up selection handler on unmount', () => {
      const { unmount } = renderHook(() => useContentUpdates(editor, store, 'note-123'));

      unmount();

      expect(editor.off).toHaveBeenCalledWith('selectionUpdate', expect.any(Function));
    });

    it('should not set up handlers when editor is null', () => {
      renderHook(() => useContentUpdates(null, store, 'note-123'));

      expect(editor.on).not.toHaveBeenCalled();
    });

    it('should dispose MobX reaction on unmount', () => {
      const { unmount } = renderHook(() => useContentUpdates(editor, store, 'note-123'));

      // Add an update to trigger reaction setup
      runInAction(() => {
        store.pendingContentUpdates.push({
          noteId: 'note-123',
          operation: 'replace_block',
          blockId: 'block-456',
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        });
      });

      unmount();

      // After unmount, adding more updates should NOT trigger processing
      const chainMock = editor.chain();
      (chainMock.run as ReturnType<typeof vi.fn>).mockClear();

      runInAction(() => {
        store.pendingContentUpdates.push({
          noteId: 'note-123',
          operation: 'replace_block',
          blockId: 'block-789',
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        });
      });

      // Should not have processed the second update
      expect(chainMock.run).not.toHaveBeenCalled();
    });
  });

  describe('replace_block operation', () => {
    it('should find target block by id and replace content with JSONContent', async () => {
      const targetBlockId = 'block-456';
      const targetPos = 10;
      const targetSize = 20;

      // Mock doc.descendants to find the block
      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      mockDoc.descendants.mockImplementation(
        (callback: (node: unknown, pos: number) => boolean | void) => {
          // Simulate finding the target block
          const node = { attrs: { id: targetBlockId }, nodeSize: targetSize };
          const shouldContinue = callback(node, targetPos);
          return shouldContinue;
        }
      );

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: targetBlockId,
        markdown: null,
        content: { type: 'paragraph', content: [{ type: 'text', text: 'Updated text' }] },
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      // Wait for MobX reaction to fire
      await new Promise((resolve) => setTimeout(resolve, 50));

      const chainMock = editor.chain();
      expect(chainMock.deleteRange).toHaveBeenCalledWith({
        from: targetPos,
        to: targetPos + targetSize,
      });
      expect(chainMock.insertContentAt).toHaveBeenCalledWith(targetPos, update.content);
      expect(chainMock.run).toHaveBeenCalled();
    });

    it('should prefer markdown over content when both present', async () => {
      const targetBlockId = 'block-456';
      const targetPos = 10;
      const targetSize = 20;

      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      mockDoc.descendants.mockImplementation(
        (callback: (node: unknown, pos: number) => boolean | void) => {
          const node = { attrs: { id: targetBlockId }, nodeSize: targetSize };
          callback(node, targetPos);
        }
      );

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: targetBlockId,
        markdown: '**Markdown content**',
        content: { type: 'paragraph', content: [{ type: 'text', text: 'JSON content' }] },
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      const chainMock = editor.chain();
      expect(chainMock.insertContentAt).toHaveBeenCalledWith(targetPos, '**Markdown content**');
      expect(chainMock.insertContentAt).not.toHaveBeenCalledWith(
        targetPos,
        expect.objectContaining({ type: 'paragraph' })
      );
    });

    it('should use content as fallback when markdown not present', async () => {
      const targetBlockId = 'block-456';
      const targetPos = 10;
      const targetSize = 20;

      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      mockDoc.descendants.mockImplementation(
        (callback: (node: unknown, pos: number) => boolean | void) => {
          const node = { attrs: { id: targetBlockId }, nodeSize: targetSize };
          callback(node, targetPos);
        }
      );

      const content = { type: 'paragraph', content: [{ type: 'text', text: 'JSON content' }] };
      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: targetBlockId,
        markdown: null,
        content,
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      const chainMock = editor.chain();
      expect(chainMock.insertContentAt).toHaveBeenCalledWith(targetPos, content);
    });

    it('should skip update when user is editing the target block (conflict detection)', async () => {
      const targetBlockId = 'block-456';

      // Simulate user selecting the target block
      const mockResolve = vi.fn().mockReturnValue({
        parent: { attrs: { id: targetBlockId } },
      });
      editor.state.doc.resolve = mockResolve;

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: targetBlockId,
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      // Trigger selection update to set userEditingBlock
      const selectionHandler = (editor.on as ReturnType<typeof vi.fn>).mock.calls.find(
        (call) => call[0] === 'selectionUpdate'
      )?.[1];
      selectionHandler?.();

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      const chainMock = editor.chain();
      // Should NOT have called chain methods due to conflict
      expect(chainMock.deleteRange).not.toHaveBeenCalled();
      expect(chainMock.run).not.toHaveBeenCalled();
    });

    it('should do nothing when target block not found', async () => {
      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      // Mock descendants to never find the block
      mockDoc.descendants.mockImplementation(() => {
        // Return without calling callback
      });

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'replace_block',
        blockId: 'non-existent-block',
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      const chainMock = editor.chain();
      expect(chainMock.deleteRange).not.toHaveBeenCalled();
      expect(chainMock.run).not.toHaveBeenCalled();
    });
  });

  describe('append_blocks operation', () => {
    it('should insert content after the specified block', async () => {
      const afterBlockId = 'block-100';
      const afterBlockPos = 50;
      const afterBlockSize = 15;

      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      mockDoc.descendants.mockImplementation(
        (callback: (node: unknown, pos: number) => boolean | void) => {
          const node = { attrs: { id: afterBlockId }, nodeSize: afterBlockSize };
          callback(node, afterBlockPos);
        }
      );

      const content = { type: 'bulletList', content: [] };
      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content,
        issueData: null,
        afterBlockId,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertContentAt).toHaveBeenCalledWith(
        afterBlockPos + afterBlockSize,
        content
      );
    });

    it('should append at end when no afterBlockId specified', async () => {
      const docSize = 100;
      // Mock the doc content size
      (editor.state.doc.content as unknown as { size: number }).size = docSize;

      const content = { type: 'paragraph', content: [] };
      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content,
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertContentAt).toHaveBeenCalledWith(docSize, content);
    });

    it('should handle markdown content for append_blocks', async () => {
      const afterBlockId = 'block-100';
      const afterBlockPos = 50;
      const afterBlockSize = 15;

      const mockDoc = editor.state.doc as unknown as {
        descendants: ReturnType<typeof vi.fn>;
      };
      mockDoc.descendants.mockImplementation(
        (callback: (node: unknown, pos: number) => boolean | void) => {
          const node = { attrs: { id: afterBlockId }, nodeSize: afterBlockSize };
          callback(node, afterBlockPos);
        }
      );

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: '- Item 1\n- Item 2',
        content: null,
        issueData: null,
        afterBlockId,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertContentAt).toHaveBeenCalledWith(
        afterBlockPos + afterBlockSize,
        '- Item 1\n- Item 2'
      );
    });
  });

  describe('insert_inline_issue operation', () => {
    it('should call insertInlineIssue command with correct attrs', async () => {
      const issueData = {
        issueId: 'issue-789',
        issueKey: 'PROJ-42',
        title: 'Fix authentication bug',
        type: 'bug' as const,
        state: 'backlog' as const,
        priority: 'urgent' as const,
        sourceBlockId: 'block-50',
      };

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: null,
        markdown: null,
        content: null,
        issueData,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertInlineIssue).toHaveBeenCalledWith({
        issueId: issueData.issueId,
        issueKey: issueData.issueKey,
        title: issueData.title,
        type: issueData.type,
        state: issueData.state,
        priority: issueData.priority,
        sourceBlockId: issueData.sourceBlockId,
        isNew: true,
      });
    });

    it('should set isNew to true for animation', async () => {
      const issueData = {
        issueId: 'issue-789',
        issueKey: 'PROJ-42',
        title: 'Fix bug',
        type: 'bug' as const,
        state: 'backlog' as const,
        priority: 'high' as const,
      };

      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: null,
        markdown: null,
        content: null,
        issueData,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertInlineIssue).toHaveBeenCalledWith(
        expect.objectContaining({ isNew: true })
      );
    });

    it('should do nothing when no issueData provided', async () => {
      const update: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'insert_inline_issue',
        blockId: null,
        markdown: null,
        content: null,
        issueData: null,
        afterBlockId: null,
      };

      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      runInAction(() => {
        store.pendingContentUpdates.push(update);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(editor.commands.insertInlineIssue).not.toHaveBeenCalled();
    });
  });

  describe('MobX reaction', () => {
    it('should process updates when pendingContentUpdates changes', async () => {
      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      const update1: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      };

      const update2: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'heading', attrs: { level: 1 } },
        issueData: null,
        afterBlockId: null,
      };

      runInAction(() => {
        store.pendingContentUpdates.push(update1, update2);
      });

      // Wait for reaction to process
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should have called insertContentAt twice
      expect(editor.commands.insertContentAt).toHaveBeenCalledTimes(2);
      expect(store.pendingContentUpdates).toHaveLength(0); // All consumed
    });

    it('should only process updates matching the noteId', async () => {
      renderHook(() => useContentUpdates(editor, store, 'note-123'));

      const update1: ContentUpdateData = {
        noteId: 'note-123',
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'paragraph' },
        issueData: null,
        afterBlockId: null,
      };

      const update2: ContentUpdateData = {
        noteId: 'note-456', // Different note
        operation: 'append_blocks',
        blockId: null,
        markdown: null,
        content: { type: 'heading' },
        issueData: null,
        afterBlockId: null,
      };

      runInAction(() => {
        store.pendingContentUpdates.push(update1, update2);
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should only process update1
      expect(editor.commands.insertContentAt).toHaveBeenCalledTimes(1);
      expect(editor.commands.insertContentAt).toHaveBeenCalledWith(100, update1.content);

      // update2 should still be in the queue
      expect(store.pendingContentUpdates).toHaveLength(1);
      expect(store.pendingContentUpdates[0]?.noteId).toBe('note-456');
    });

    it('should dispose reaction on unmount', async () => {
      const { unmount } = renderHook(() => useContentUpdates(editor, store, 'note-123'));

      unmount();

      // Clear previous calls
      (editor.commands.insertContentAt as ReturnType<typeof vi.fn>).mockClear();

      // Add update after unmount
      runInAction(() => {
        store.pendingContentUpdates.push({
          noteId: 'note-123',
          operation: 'append_blocks',
          blockId: null,
          markdown: null,
          content: { type: 'paragraph' },
          issueData: null,
          afterBlockId: null,
        });
      });

      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should NOT have processed the update
      expect(editor.commands.insertContentAt).not.toHaveBeenCalled();
    });
  });

  describe('highlightBlock', () => {
    function createBlockEl(id: string): HTMLDivElement {
      const el = document.createElement('div');
      el.setAttribute('data-block-id', id);
      document.body.appendChild(el);
      return el;
    }

    afterEach(() => {
      document.querySelectorAll('[data-block-id]').forEach((el) => el.remove());
      vi.restoreAllMocks();
    });

    it('should add ai-block-edited class and ai-block-fade-out after 50ms', () => {
      vi.useFakeTimers();
      const el = createBlockEl('block-1');
      highlightBlock('block-1', 'edited');
      expect(el.classList.contains('ai-block-edited')).toBe(true);
      expect(el.classList.contains('ai-block-fade-out')).toBe(false);
      vi.advanceTimersByTime(50);
      expect(el.classList.contains('ai-block-fade-out')).toBe(true);
      vi.useRealTimers();
    });

    it('should remove both edited classes after 1100ms', () => {
      vi.useFakeTimers();
      const el = createBlockEl('block-1');
      highlightBlock('block-1', 'edited');
      vi.advanceTimersByTime(1100);
      expect(el.classList.contains('ai-block-edited')).toBe(false);
      expect(el.classList.contains('ai-block-fade-out')).toBe(false);
      vi.useRealTimers();
    });

    it('should add ai-block-new class and remove after 400ms', () => {
      vi.useFakeTimers();
      const el = createBlockEl('block-1');
      highlightBlock('block-1', 'new');
      expect(el.classList.contains('ai-block-new')).toBe(true);
      vi.advanceTimersByTime(400);
      expect(el.classList.contains('ai-block-new')).toBe(false);
      vi.useRealTimers();
    });

    it('should not throw when element not found', () => {
      expect(() => highlightBlock('non-existent', 'edited')).not.toThrow();
    });
  });
});
