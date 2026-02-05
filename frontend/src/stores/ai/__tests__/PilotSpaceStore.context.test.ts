/**
 * Unit tests for PilotSpaceStore context management.
 *
 * Tests note context state management and conversationContext computed property.
 *
 * @module stores/ai/__tests__/PilotSpaceStore.context.test
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

import { PilotSpaceStore, type NoteContext } from '../PilotSpaceStore';
import type { AIStore } from '../AIStore';

describe('PilotSpaceStore.setNoteContext', () => {
  let store: PilotSpaceStore;
  let mockRootStore: AIStore;

  beforeEach(() => {
    mockRootStore = {} as AIStore;
    store = new PilotSpaceStore(mockRootStore);
    // Set workspaceId for conversationContext to work
    store.setWorkspaceId('workspace-123');
  });

  it('test_setNoteContext_with_title — Sets noteTitle in context', () => {
    const context: NoteContext = {
      noteId: 'note-123',
      noteTitle: 'Project Planning Document',
      selectedText: undefined,
      selectedBlockIds: undefined,
    };

    store.setNoteContext(context);

    expect(store.noteContext).toEqual(context);
    expect(store.noteContext?.noteTitle).toBe('Project Planning Document');
    expect(store.noteContext?.noteId).toBe('note-123');
  });

  it('test_conversationContext_includes_noteId — Computed includes noteId from noteContext', () => {
    const context: NoteContext = {
      noteId: 'note-456',
      selectedText: 'some selected text',
      selectedBlockIds: ['block-1', 'block-2'],
      noteTitle: 'Meeting Notes',
    };

    store.setNoteContext(context);

    const conversationCtx = store.conversationContext;
    expect(conversationCtx).not.toBeNull();

    expect(conversationCtx!.noteId).toBe('note-456');
    expect(conversationCtx!.workspaceId).toBe('workspace-123');
    expect(conversationCtx!.selectedText).toBe('some selected text');
    expect(conversationCtx!.selectedBlockIds).toEqual(['block-1', 'block-2']);
  });

  it('test_setNoteContext_preserves_selected_text — Setting context does not clear selection', () => {
    // First, set context with selected text
    const initialContext: NoteContext = {
      noteId: 'note-789',
      selectedText: 'important paragraph',
      selectedBlockIds: ['block-5'],
    };

    store.setNoteContext(initialContext);

    expect(store.noteContext?.selectedText).toBe('important paragraph');
    expect(store.noteContext?.selectedBlockIds).toEqual(['block-5']);

    // Update context with new noteTitle, but preserve selection
    const updatedContext: NoteContext = {
      noteId: 'note-789',
      selectedText: 'important paragraph',
      selectedBlockIds: ['block-5'],
      noteTitle: 'Updated Title',
    };

    store.setNoteContext(updatedContext);

    // Selection should still be present
    expect(store.noteContext?.selectedText).toBe('important paragraph');
    expect(store.noteContext?.selectedBlockIds).toEqual(['block-5']);
    expect(store.noteContext?.noteTitle).toBe('Updated Title');
  });
});
