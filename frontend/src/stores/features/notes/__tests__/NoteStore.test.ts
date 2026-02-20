/**
 * NoteStore unit tests.
 *
 * Covers:
 * - loadNotes injects workspaceId into notes
 * - loadNote injects workspaceId into loaded note
 * - pinnedNotes computed filters correctly
 * - recentNotes computed returns sorted subset
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Note } from '@/types';
import { NoteStore } from '../NoteStore';

// Mock the notesApi module
vi.mock('@/services/api', () => ({
  notesApi: {
    list: vi.fn(),
    get: vi.fn(),
    updateContent: vi.fn(),
    getAnnotations: vi.fn(),
  },
}));

// Import after mock so we get the mocked version
import { notesApi } from '@/services/api';

function makeNote(overrides: Partial<Note> = {}): Note {
  return {
    id: 'note-1',
    title: 'Test Note',
    isPinned: false,
    wordCount: 0,
    readingTimeMins: 0,
    content: { type: 'doc', content: [] },
    ownerId: 'owner-1',
    workspaceId: 'ws-default',
    collaborators: [],
    linkedIssues: [],
    annotations: [],
    topics: [],
    updatedAt: '2026-01-01T00:00:00Z',
    createdAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('NoteStore', () => {
  let store: NoteStore;

  beforeEach(() => {
    store = new NoteStore();
    vi.clearAllMocks();
  });

  describe('loadNotes', () => {
    it('should inject workspaceId into loaded notes', async () => {
      const mockNotes = [
        makeNote({ id: 'n1', title: 'Note 1' }),
        makeNote({ id: 'n2', title: 'Note 2', isPinned: true }),
      ];

      vi.mocked(notesApi.list).mockResolvedValue({
        items: mockNotes,
        total: 2,
        page: 1,
        pageSize: 50,
        hasMore: false,
      });

      await store.loadNotes('workspace-abc');

      expect(store.notesList).toHaveLength(2);

      const note1 = store.notes.get('n1');
      expect(note1).toBeDefined();
      expect(note1!.workspaceId).toBe('workspace-abc');

      const note2 = store.notes.get('n2');
      expect(note2).toBeDefined();
      expect(note2!.workspaceId).toBe('workspace-abc');
    });

    it('should populate pinnedNotes from loaded notes', async () => {
      const mockNotes = [
        makeNote({ id: 'n1', title: 'Regular Note', isPinned: false }),
        makeNote({ id: 'n2', title: 'Pinned Note', isPinned: true }),
        makeNote({ id: 'n3', title: 'Another Pinned', isPinned: true }),
      ];

      vi.mocked(notesApi.list).mockResolvedValue({
        items: mockNotes,
        total: 3,
        page: 1,
        pageSize: 50,
        hasMore: false,
      });

      await store.loadNotes('workspace-abc');

      expect(store.pinnedNotes).toHaveLength(2);
      expect(store.pinnedNotes.map((n) => n.id)).toContain('n2');
      expect(store.pinnedNotes.map((n) => n.id)).toContain('n3');
    });

    it('should set error on API failure', async () => {
      vi.mocked(notesApi.list).mockRejectedValue(new Error('Network error'));

      await store.loadNotes('workspace-abc');

      expect(store.error).toBe('Network error');
      expect(store.notesList).toHaveLength(0);
      expect(store.isLoading).toBe(false);
    });
  });

  describe('loadNote', () => {
    it('should inject workspaceId into loaded note', async () => {
      const mockNote = makeNote({
        id: 'note-detail',
        title: 'Detailed Note',
        content: {
          type: 'doc',
          content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Hello world' }] }],
        },
      });

      vi.mocked(notesApi.get).mockResolvedValue(mockNote as never);

      await store.loadNote('workspace-xyz', 'note-detail');

      const loaded = store.notes.get('note-detail');
      expect(loaded).toBeDefined();
      expect(loaded!.workspaceId).toBe('workspace-xyz');
      expect(store.currentNoteId).toBe('note-detail');
    });
  });

  describe('recentNotes', () => {
    it('should return notes sorted by updatedAt descending', async () => {
      const mockNotes = [
        makeNote({ id: 'old', title: 'Old', updatedAt: '2026-01-01T00:00:00Z' }),
        makeNote({ id: 'new', title: 'New', updatedAt: '2026-02-01T00:00:00Z' }),
        makeNote({ id: 'mid', title: 'Mid', updatedAt: '2026-01-15T00:00:00Z' }),
      ];

      vi.mocked(notesApi.list).mockResolvedValue({
        items: mockNotes,
        total: 3,
        page: 1,
        pageSize: 50,
        hasMore: false,
      });

      await store.loadNotes('ws');

      const recent = store.recentNotes;
      expect(recent[0]!.id).toBe('new');
      expect(recent[1]!.id).toBe('mid');
      expect(recent[2]!.id).toBe('old');
    });
  });
});
