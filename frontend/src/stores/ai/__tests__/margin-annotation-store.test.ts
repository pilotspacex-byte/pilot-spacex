/**
 * MarginAnnotationStore Tests (T176)
 * Unit tests for margin annotation state management
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MarginAnnotationStore } from '../MarginAnnotationStore';
import type { NoteAnnotation } from '@/types';
import { AIStore } from '../AIStore';

// Mock dependencies
vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn(),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

describe('MarginAnnotationStore', () => {
  let store: MarginAnnotationStore;
  let aiStore: AIStore;

  beforeEach(() => {
    aiStore = new AIStore();
    store = aiStore.marginAnnotation;
  });

  afterEach(() => {
    store.abort();
  });

  describe('getAnnotationsByBlock', () => {
    it('should group annotations by block ID', () => {
      const annotations: NoteAnnotation[] = [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content 1',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: { title: 'Test 1', summary: 'Summary 1' },
          createdAt: new Date().toISOString(),
        },
        {
          id: '2',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'warning',
          content: 'Content 2',
          confidence: 0.8,
          status: 'pending',
          aiMetadata: { title: 'Test 2', summary: 'Summary 2' },
          createdAt: new Date().toISOString(),
        },
        {
          id: '3',
          noteId: 'note-1',
          blockId: 'block-2',
          type: 'insight',
          content: 'Content 3',
          confidence: 0.75,
          status: 'pending',
          aiMetadata: { title: 'Test 3', summary: 'Summary 3' },
          createdAt: new Date().toISOString(),
        },
      ];

      store.annotations.set('note-1', annotations);

      const byBlock = store.getAnnotationsByBlock('note-1');

      expect(byBlock.get('block-1')).toHaveLength(2);
      expect(byBlock.get('block-2')).toHaveLength(1);
    });

    it('should return empty map for non-existent note', () => {
      const byBlock = store.getAnnotationsByBlock('non-existent');
      expect(byBlock.size).toBe(0);
    });

    it('should handle empty annotations', () => {
      store.annotations.set('note-1', []);
      const byBlock = store.getAnnotationsByBlock('note-1');
      expect(byBlock.size).toBe(0);
    });
  });

  describe('selectAnnotation', () => {
    it('should set selected annotation ID', () => {
      store.selectAnnotation('annotation-1');
      expect(store.selectedAnnotationId).toBe('annotation-1');
    });

    it('should replace previous selection', () => {
      store.selectAnnotation('annotation-1');
      store.selectAnnotation('annotation-2');
      expect(store.selectedAnnotationId).toBe('annotation-2');
    });
  });

  describe('clearSelection', () => {
    it('should clear selected annotation', () => {
      store.selectAnnotation('annotation-1');
      store.clearSelection();
      expect(store.selectedAnnotationId).toBeNull();
    });

    it('should be idempotent', () => {
      store.clearSelection();
      store.clearSelection();
      expect(store.selectedAnnotationId).toBeNull();
    });
  });

  describe('dismissAnnotation', () => {
    it('should remove annotation from list', () => {
      const annotations: NoteAnnotation[] = [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content 1',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: { title: 'Test 1', summary: 'Summary 1' },
          createdAt: new Date().toISOString(),
        },
        {
          id: '2',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'warning',
          content: 'Content 2',
          confidence: 0.8,
          status: 'pending',
          aiMetadata: { title: 'Test 2', summary: 'Summary 2' },
          createdAt: new Date().toISOString(),
        },
      ];
      store.annotations.set('note-1', annotations);

      store.dismissAnnotation('1');

      const result = store.annotations.get('note-1');
      expect(result).toHaveLength(1);
      expect(result?.[0]?.id).toBe('2');
    });

    it('should clear selection if dismissed annotation was selected', () => {
      store.annotations.set('note-1', [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: {
            title: 'Test',
            summary: 'Summary',
          },
          createdAt: new Date().toISOString(),
        },
      ]);
      store.selectAnnotation('1');

      store.dismissAnnotation('1');

      expect(store.selectedAnnotationId).toBeNull();
    });

    it('should not clear selection if different annotation dismissed', () => {
      store.annotations.set('note-1', [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: {
            title: 'Test',
            summary: 'Summary',
          },
          createdAt: new Date().toISOString(),
        },
        {
          id: '2',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'warning',
          content: 'Content 2',
          confidence: 0.8,
          status: 'pending',
          aiMetadata: {
            title: 'Test 2',
            summary: 'Summary 2',
          },
          createdAt: new Date().toISOString(),
        },
      ]);
      store.selectAnnotation('1');

      store.dismissAnnotation('2');

      expect(store.selectedAnnotationId).toBe('1');
    });
  });

  describe('abort', () => {
    it('should set loading to false', () => {
      store.isGenerating = true;
      store.abort();
      expect(store.isGenerating).toBe(false);
    });

    it('should be safe to call multiple times', () => {
      store.abort();
      store.abort();
      expect(store.isGenerating).toBe(false);
    });
  });

  describe('clearAnnotations', () => {
    it('should remove all annotations for note', () => {
      store.annotations.set('note-1', [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: {
            title: 'Test',
            summary: 'Summary',
          },
          createdAt: new Date().toISOString(),
        },
      ]);
      store.selectAnnotation('1');

      store.clearAnnotations('note-1');

      expect(store.annotations.has('note-1')).toBe(false);
      expect(store.selectedAnnotationId).toBeNull();
    });
  });

  describe('getAnnotationsForNote', () => {
    it('should return annotations for specific note', () => {
      const annotations: NoteAnnotation[] = [
        {
          id: '1',
          noteId: 'note-1',
          blockId: 'block-1',
          type: 'suggestion',
          content: 'Content',
          confidence: 0.9,
          status: 'pending',
          aiMetadata: { title: 'Test', summary: 'Summary' },
          createdAt: new Date().toISOString(),
        },
      ];
      store.annotations.set('note-1', annotations);

      const result = store.getAnnotationsForNote('note-1');

      expect(result).toEqual(annotations);
    });

    it('should return empty array for non-existent note', () => {
      const result = store.getAnnotationsForNote('non-existent');
      expect(result).toEqual([]);
    });
  });

  describe('setEnabled', () => {
    it('should update enabled state', () => {
      store.setEnabled(false);
      expect(store.enabled).toBe(false);
    });

    it('should abort when disabled', () => {
      store.isGenerating = true;
      store.setEnabled(false);
      expect(store.isGenerating).toBe(false);
    });
  });

  describe('isGeneratingForNote', () => {
    it('should return true when generating for specific note', () => {
      store.isGenerating = true;
      store['generatingNoteId'] = 'note-1';

      expect(store.isGeneratingForNote('note-1')).toBe(true);
    });

    it('should return false when generating for different note', () => {
      store.isGenerating = true;
      store['generatingNoteId'] = 'note-1';

      expect(store.isGeneratingForNote('note-2')).toBe(false);
    });

    it('should return false when not generating', () => {
      store.isGenerating = false;

      expect(store.isGeneratingForNote('note-1')).toBe(false);
    });
  });
});
