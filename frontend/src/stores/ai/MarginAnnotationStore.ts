/**
 * Margin Annotation Store - MobX store for AI annotations state
 * T171-T173: Manages annotation lifecycle and SSE streaming
 *
 * Features:
 * - Annotation CRUD operations
 * - SSE streaming for real-time generation
 * - Block-to-annotation mapping
 * - Selection state management
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { SSEClient } from '@/lib/sse-client';
import type { AIStore } from './AIStore';

export interface NoteAnnotation {
  id: string;
  noteId: string;
  blockId: string;
  type: 'suggestion' | 'warning' | 'question' | 'insight' | 'reference';
  title: string;
  summary: string;
  content: string;
  suggestedText?: string;
  references?: Array<{ title: string; url: string }>;
  confidence: number;
  createdAt: string;
}

export class MarginAnnotationStore {
  /** Annotations grouped by note ID */
  annotations: Map<string, NoteAnnotation[]> = new Map();

  /** Currently selected annotation ID */
  selectedAnnotationId: string | null = null;

  /** Loading state during generation */
  isGenerating = false;

  /** Error state */
  error: string | null = null;

  /** Enabled state */
  enabled = true;

  /** SSE client for streaming */
  private sseClient: SSEClient | null = null;

  /** Currently generating for note ID */
  private generatingNoteId: string | null = null;

  constructor(_aiStore: AIStore) {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /**
   * Generate annotations for note blocks via SSE streaming.
   * Clears existing annotations and streams new ones.
   */
  async generateAnnotations(noteId: string, blocks: Array<{ id: string; content: string }>): Promise<void> {
    // Abort any in-progress generation
    this.abort();

    this.isGenerating = true;
    this.error = null;
    this.generatingNoteId = noteId;

    // Clear existing annotations for this note
    runInAction(() => {
      this.annotations.set(noteId, []);
    });

    // Prepare request body
    const blockIds = blocks.map((b) => b.id);

    this.sseClient = new SSEClient({
      url: `/api/v1/ai/notes/${noteId}/annotations`,
      body: {
        block_ids: blockIds,
        context_blocks: 3,
      },
      onMessage: (event) => {
        if (event.type === 'annotation') {
          runInAction(() => {
            const annotation = event.data as NoteAnnotation;
            const current = this.annotations.get(noteId) || [];
            this.annotations.set(noteId, [...current, annotation]);
          });
        } else if (event.type === 'error') {
          runInAction(() => {
            this.error = (event.data as { message: string }).message || 'Generation failed';
          });
        }
      },
      onComplete: () => {
        runInAction(() => {
          this.isGenerating = false;
          this.generatingNoteId = null;
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.error = err.message || 'Failed to generate annotations';
          this.isGenerating = false;
          this.generatingNoteId = null;
        });
      },
    });

    try {
      await this.sseClient.connect();
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Connection failed';
        this.isGenerating = false;
        this.generatingNoteId = null;
      });
    }
  }

  /**
   * Fetch existing annotations for a note (from cache or API).
   * Used on note load to restore previously generated annotations.
   */
  async fetchAnnotations(_noteId: string): Promise<void> {
    // TODO: Implement API fetch once backend endpoint is available
    // For now, annotations are only generated via SSE streaming
    this.error = null;
  }

  /**
   * Get annotations grouped by block ID for positioning.
   * Used by MarginAnnotationList component.
   */
  getAnnotationsByBlock(noteId: string): Map<string, NoteAnnotation[]> {
    const annotations = this.annotations.get(noteId) || [];
    const byBlock = new Map<string, NoteAnnotation[]>();

    annotations.forEach((annotation) => {
      const existing = byBlock.get(annotation.blockId) || [];
      byBlock.set(annotation.blockId, [...existing, annotation]);
    });

    return byBlock;
  }

  /**
   * Get all annotations for document (used by TipTap extension).
   */
  getAnnotationsForDoc(): NoteAnnotation[] {
    // Return all annotations across all notes
    // In practice, extension should filter by current note
    const allAnnotations: NoteAnnotation[] = [];
    this.annotations.forEach((noteAnnotations) => {
      allAnnotations.push(...noteAnnotations);
    });
    return allAnnotations;
  }

  /**
   * Get annotations for specific note.
   */
  getAnnotationsForNote(noteId: string): NoteAnnotation[] {
    return this.annotations.get(noteId) || [];
  }

  /**
   * Select an annotation (highlights in UI).
   */
  selectAnnotation(annotationId: string): void {
    this.selectedAnnotationId = annotationId;
  }

  /**
   * Clear annotation selection.
   */
  clearSelection(): void {
    this.selectedAnnotationId = null;
  }

  /**
   * Dismiss annotation (remove from list).
   */
  dismissAnnotation(annotationId: string): void {
    this.annotations.forEach((noteAnnotations, noteId) => {
      const filtered = noteAnnotations.filter((a) => a.id !== annotationId);
      if (filtered.length !== noteAnnotations.length) {
        this.annotations.set(noteId, filtered);
      }
    });

    if (this.selectedAnnotationId === annotationId) {
      this.selectedAnnotationId = null;
    }
  }

  /**
   * Apply annotation suggestion (insert text into editor).
   * Actual insertion is handled by parent component with editor access.
   */
  applyAnnotation(annotationId: string): void {
    // Mark as applied and dismiss
    // Parent component handles actual text insertion
    this.dismissAnnotation(annotationId);
  }

  /**
   * Abort ongoing SSE stream.
   */
  abort(): void {
    if (this.sseClient) {
      this.sseClient.abort();
      this.sseClient = null;
    }
    this.isGenerating = false;
    this.generatingNoteId = null;
  }

  /**
   * Clear all annotations for a note.
   */
  clearAnnotations(noteId: string): void {
    this.annotations.delete(noteId);
    this.clearSelection();
  }

  /**
   * Clear all annotations and state.
   */
  reset(): void {
    this.abort();
    this.annotations.clear();
    this.selectedAnnotationId = null;
    this.error = null;
  }

  /**
   * Set enabled state.
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) {
      this.abort();
    }
  }

  /**
   * Check if currently generating for specific note.
   */
  isGeneratingForNote(noteId: string): boolean {
    return this.isGenerating && this.generatingNoteId === noteId;
  }
}
