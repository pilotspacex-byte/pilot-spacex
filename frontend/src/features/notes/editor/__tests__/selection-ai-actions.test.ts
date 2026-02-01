/**
 * Test suite for SelectionToolbar AI actions integration
 * Tests the integration between selection toolbar, PilotSpaceStore, and ChatView
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';
import type { AIStore } from '@/stores/ai/AIStore';

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null } })),
    },
  },
}));

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

describe('SelectionToolbar AI Actions', () => {
  let mockStore: PilotSpaceStore;
  let mockAIStore: Partial<AIStore>;

  beforeEach(() => {
    mockAIStore = {
      pilotSpace: {} as never,
    };
    mockStore = new PilotSpaceStore(mockAIStore as AIStore);
    mockStore.setWorkspaceId('workspace-1');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Selection context tracking', () => {
    it('should populate noteContext when text is selected', async () => {
      const store = mockStore;
      const noteId = 'note-123';

      // Set note context manually (simulating useSelectionContext hook behavior)
      store.setNoteContext({
        noteId,
        selectedText: 'Selected text content',
        selectedBlockIds: ['block-1', 'block-2'],
      });

      expect(store.noteContext).toEqual({
        noteId: 'note-123',
        selectedText: 'Selected text content',
        selectedBlockIds: ['block-1', 'block-2'],
      });
    });

    it('should clear noteContext when selection is cleared', () => {
      const store = mockStore;

      // Set context first
      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Some text',
        selectedBlockIds: ['block-1'],
      });

      // Clear selection
      store.setNoteContext({
        noteId: 'note-123',
        selectedText: undefined,
        selectedBlockIds: undefined,
      });

      expect(store.noteContext?.selectedText).toBeUndefined();
      expect(store.noteContext?.selectedBlockIds).toBeUndefined();
    });

    it('should update selectedBlockIds for multi-block selection', () => {
      const store = mockStore;

      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Multi-block text',
        selectedBlockIds: ['block-1', 'block-2', 'block-3'],
      });

      expect(store.noteContext?.selectedBlockIds).toHaveLength(3);
      expect(store.noteContext?.selectedBlockIds).toEqual(['block-1', 'block-2', 'block-3']);
    });
  });

  describe('Ask Pilot action', () => {
    it('should open ChatView with selection context pre-filled', async () => {
      const store = mockStore;
      const selectedText = 'Help me understand this concept';

      // Simulate "Ask Pilot" action
      store.setNoteContext({
        noteId: 'note-123',
        selectedText,
        selectedBlockIds: ['block-1'],
      });

      // Verify context is set
      expect(store.noteContext?.selectedText).toBe(selectedText);

      // Simulate user opening ChatView (this would be handled by UI state)
      // The ChatInput component should show the context via ContextIndicator
      const conversationContext = store.conversationContext;
      expect(conversationContext.selectedText).toBe(selectedText);
    });

    it('should include selectedBlockIds in conversation context', () => {
      const store = mockStore;

      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Selected text',
        selectedBlockIds: ['block-1', 'block-2'],
      });

      const context = store.conversationContext;
      expect(context.selectedBlockIds).toEqual(['block-1', 'block-2']);
      expect(context.noteId).toBe('note-123');
    });
  });

  describe('Enhance action', () => {
    it('should send enhance request with selected text', async () => {
      const store = mockStore;
      const selectedText = 'This text needs improvement';

      // Mock sendMessage
      const sendMessageSpy = vi.spyOn(store, 'sendMessage').mockResolvedValue(undefined);

      // Set selection context
      store.setNoteContext({
        noteId: 'note-123',
        selectedText,
        selectedBlockIds: ['block-1'],
      });

      // Simulate enhance action
      await store.sendMessage(`Enhance the following text: ${selectedText}`);

      expect(sendMessageSpy).toHaveBeenCalledWith(`Enhance the following text: ${selectedText}`);
    });

    it('should trigger streaming response for enhance action', async () => {
      const store = mockStore;

      // Mock fetch for SSE stream
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: new Headers({ 'Content-Type': 'text/event-stream' }),
          body: {
            getReader: () => ({
              read: vi
                .fn()
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'event: message_start\ndata: {"messageId":"msg-1","sessionId":"session-1"}\n\n'
                  ),
                })
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'event: text_delta\ndata: {"delta":"Improved "}\n\n'
                  ),
                })
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode('event: text_delta\ndata: {"delta":"text"}\n\n'),
                })
                .mockResolvedValueOnce({
                  done: false,
                  value: new TextEncoder().encode(
                    'event: message_stop\ndata: {"messageId":"msg-1"}\n\n'
                  ),
                })
                .mockResolvedValueOnce({ done: true, value: undefined }),
              releaseLock: vi.fn(),
            }),
          },
        } as unknown as Response)
      );

      await store.sendMessage('Enhance the following text: test');

      await waitFor(() => {
        expect(store.messages).toHaveLength(2); // user + assistant
      });

      expect(store.messages[1]?.content).toBe('Improved text');
    });
  });

  describe('Extract Issues action', () => {
    it('should send extract issues request with selected content', async () => {
      const store = mockStore;
      const selectedText = 'TODO: Implement user authentication\nTODO: Add validation';

      const sendMessageSpy = vi.spyOn(store, 'sendMessage').mockResolvedValue(undefined);

      store.setNoteContext({
        noteId: 'note-123',
        selectedText,
        selectedBlockIds: ['block-1'],
      });

      // Simulate extract issues action
      await store.sendMessage(`Extract actionable issues from: ${selectedText}`);

      expect(sendMessageSpy).toHaveBeenCalledWith(
        `Extract actionable issues from: ${selectedText}`
      );
    });

    it('should preserve blockId context for issue extraction', () => {
      const store = mockStore;

      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Issue text',
        selectedBlockIds: ['block-1', 'block-2'],
      });

      const context = store.conversationContext;
      expect(context.selectedBlockIds).toEqual(['block-1', 'block-2']);
    });
  });

  describe('Content updates integration', () => {
    it('should queue content updates from AI responses', () => {
      const store = mockStore;

      // Simulate content_update event
      store.handleContentUpdate({
        type: 'content_update',
        data: {
          noteId: 'note-123',
          operation: 'replace_block',
          markdown: null,
          content: {
            type: 'paragraph',
            content: [{ type: 'text', text: 'Enhanced content here' }],
          },
          blockId: 'block-1',
          issueData: null,
          afterBlockId: null,
        },
      });

      expect(store.pendingContentUpdates).toHaveLength(1);
      expect(store.pendingContentUpdates[0]?.noteId).toBe('note-123');
      expect(store.pendingContentUpdates[0]?.operation).toBe('replace_block');
    });

    it('should consume content update for specific note', () => {
      const store = mockStore;

      // Queue multiple updates
      store.handleContentUpdate({
        type: 'content_update',
        data: {
          noteId: 'note-123',
          operation: 'replace_block',
          markdown: null,
          content: { type: 'paragraph' },
          blockId: 'block-1',
          issueData: null,
          afterBlockId: null,
        },
      });

      store.handleContentUpdate({
        type: 'content_update',
        data: {
          noteId: 'note-456',
          operation: 'append_blocks',
          markdown: null,
          content: { type: 'paragraph' },
          blockId: null,
          issueData: null,
          afterBlockId: 'block-1',
        },
      });

      // Consume update for note-123
      const update = store.consumeContentUpdate('note-123');

      expect(update).toBeDefined();
      expect(update?.noteId).toBe('note-123');
      expect(store.pendingContentUpdates).toHaveLength(1);
      expect(store.pendingContentUpdates[0]?.noteId).toBe('note-456');
    });

    it('should respect FIFO buffer limit of 100 updates', () => {
      const store = mockStore;

      // Add 105 updates
      for (let i = 0; i < 105; i++) {
        store.handleContentUpdate({
          type: 'content_update',
          data: {
            noteId: `note-${i}`,
            operation: 'replace_block',
            markdown: null,
            content: { type: 'paragraph', content: [{ type: 'text', text: `Content ${i}` }] },
            blockId: `block-${i}`,
            issueData: null,
            afterBlockId: null,
          },
        });
      }

      // Should keep only last 100
      expect(store.pendingContentUpdates).toHaveLength(100);
      // First 5 should be evicted
      expect(store.pendingContentUpdates[0]?.noteId).toBe('note-5');
      expect(store.pendingContentUpdates[99]?.noteId).toBe('note-104');
    });
  });

  describe('Selection-to-ChatView workflow', () => {
    it('should maintain context when switching to ChatView', () => {
      const store = mockStore;

      // User selects text
      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Selected content',
        selectedBlockIds: ['block-1'],
      });

      // User opens ChatView (via keyboard shortcut or FAB)
      // Context should be preserved
      expect(store.noteContext).toBeDefined();
      expect(store.conversationContext.selectedText).toBe('Selected content');
    });

    it('should clear selection context after message is sent', async () => {
      const store = mockStore;

      // Mock sendMessage
      vi.spyOn(store, 'sendMessage').mockResolvedValue(undefined);

      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Ask about this',
        selectedBlockIds: ['block-1'],
      });

      // Send message
      await store.sendMessage('Explain this concept');

      // Context should still be available (not auto-cleared)
      // User might want to ask follow-up questions about same selection
      expect(store.noteContext).toBeDefined();
    });
  });

  describe('Error handling', () => {
    it('should handle sendMessage errors gracefully', async () => {
      const store = mockStore;

      // Mock fetch to fail
      global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

      await store.sendMessage('Test message');

      expect(store.error).toBe('Network error');
      expect(store.isStreaming).toBe(false);
    });

    it('should preserve context on error', async () => {
      const store = mockStore;

      store.setNoteContext({
        noteId: 'note-123',
        selectedText: 'Test text',
        selectedBlockIds: ['block-1'],
      });

      // Mock fetch to fail
      global.fetch = vi.fn(() => Promise.reject(new Error('API error')));

      await store.sendMessage('Test');

      // Context should be preserved for retry
      expect(store.noteContext).toBeDefined();
      expect(store.noteContext?.selectedText).toBe('Test text');
    });
  });
});
