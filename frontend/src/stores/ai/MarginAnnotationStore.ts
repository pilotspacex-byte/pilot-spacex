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
import { supabase } from '@/lib/supabase';
import type { AIStore } from './AIStore';
import type { NoteAnnotation, AnnotationStatus } from '@/types';

/**
 * Get auth headers for API requests.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
  } catch {
    console.warn('Failed to get auth session');
  }
  return {};
}

// Re-export for convenience
export type { NoteAnnotation };

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

  /** Cache for fetched annotations with TTL */
  private cache: Map<string, { annotations: NoteAnnotation[]; timestamp: number }> = new Map();

  /** Cache TTL in milliseconds (5 minutes) */
  private readonly cacheTTL = 5 * 60 * 1000;

  /** Auto-trigger debounce timer */
  private autoTriggerTimer: ReturnType<typeof setTimeout> | null = null;

  /** Auto-trigger debounce duration in milliseconds */
  private readonly autoTriggerDebounce = 2000;

  constructor(_aiStore: AIStore) {
    makeAutoObservable(this, {}, { autoBind: true });
  }

  /**
   * Generate annotations for note blocks via SSE streaming.
   * Clears existing annotations and streams new ones.
   */
  async generateAnnotations(
    noteId: string,
    blocks: Array<{ id: string; content: string }>
  ): Promise<void> {
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
    const authHeaders = await getAuthHeaders();

    this.sseClient = new SSEClient({
      url: `${apiUrl}/ai/notes/${noteId}/annotations`,
      body: {
        block_ids: blockIds,
        context_blocks: 3,
      },
      headers: authHeaders,
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
  async fetchAnnotations(workspaceSlug: string, noteId: string): Promise<void> {
    // Check cache first
    const cached = this.cache.get(noteId);
    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      runInAction(() => {
        this.annotations.set(noteId, cached.annotations);
      });
      return;
    }

    try {
      this.error = null;
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
      const authHeaders = await getAuthHeaders();

      const response = await fetch(
        `${apiUrl}/workspaces/${workspaceSlug}/notes/${noteId}/annotations`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
          },
          credentials: 'include',
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch annotations (${response.status})`);
      }

      const data = await response.json();
      // Backend may return array directly or { items: [...] } format
      const annotations = Array.isArray(data) ? data : data.items || data.annotations || [];

      runInAction(() => {
        this.annotations.set(noteId, annotations);
        // Update cache
        this.cache.set(noteId, { annotations, timestamp: Date.now() });
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to fetch annotations';
      });
    }
  }

  /**
   * Update annotation status (accept, reject, dismiss).
   * Persists to backend and updates local state.
   */
  async updateAnnotationStatus(
    workspaceSlug: string,
    noteId: string,
    annotationId: string,
    status: Exclude<AnnotationStatus, 'pending'>
  ): Promise<void> {
    try {
      this.error = null;
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
      const authHeaders = await getAuthHeaders();

      const response = await fetch(
        `${apiUrl}/workspaces/${workspaceSlug}/notes/${noteId}/annotations/${annotationId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders,
          },
          credentials: 'include',
          body: JSON.stringify({ status }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to update annotation status (${response.status})`);
      }

      // Update local state
      runInAction(() => {
        const noteAnnotations = this.annotations.get(noteId) || [];
        const updatedAnnotations = noteAnnotations.map((a) =>
          a.id === annotationId ? { ...a, status } : a
        );
        this.annotations.set(noteId, updatedAnnotations);
        // Invalidate cache
        this.cache.delete(noteId);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update annotation status';
      });
      throw err;
    }
  }

  /**
   * Auto-trigger annotation generation for specific blocks.
   * Used by MarginAnnotationAutoTriggerExtension when content changes.
   * Debounced to prevent excessive API calls.
   */
  autoTriggerAnnotations(noteId: string, blockIds: string[], workspaceId?: string): void {
    if (!this.enabled || this.isGenerating || blockIds.length === 0) {
      return;
    }

    // Check cache first
    const cached = this.cache.get(noteId);
    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      runInAction(() => {
        this.annotations.set(noteId, cached.annotations);
      });
      return;
    }

    // Clear existing timer
    if (this.autoTriggerTimer) {
      clearTimeout(this.autoTriggerTimer);
    }

    // Debounce the actual generation
    this.autoTriggerTimer = setTimeout(() => {
      this.generateAnnotationsInternal(noteId, blockIds, workspaceId);
    }, this.autoTriggerDebounce);
  }

  /**
   * Internal method to generate annotations via SSE.
   * Called by autoTriggerAnnotations after debounce.
   */
  private async generateAnnotationsInternal(
    noteId: string,
    blockIds: string[],
    workspaceId?: string
  ): Promise<void> {
    // Abort any existing generation
    this.abort();

    this.isGenerating = true;
    this.error = null;
    this.generatingNoteId = noteId;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';
    const authHeaders = await getAuthHeaders();

    this.sseClient = new SSEClient({
      url: `${apiUrl}/ai/notes/${noteId}/annotations`,
      body: {
        block_ids: blockIds,
        context_blocks: 3,
      },
      headers: {
        ...authHeaders,
        ...(workspaceId ? { 'X-Workspace-ID': workspaceId } : {}),
      },
      onMessage: (event) => {
        if (event.type === 'annotation') {
          runInAction(() => {
            const annotation = event.data as NoteAnnotation;
            const current = this.annotations.get(noteId) || [];

            // Append or update annotation
            const existingIndex = current.findIndex((a) => a.id === annotation.id);
            if (existingIndex >= 0) {
              current[existingIndex] = annotation;
              this.annotations.set(noteId, [...current]);
            } else {
              this.annotations.set(noteId, [...current, annotation]);
            }
          });
        } else if (event.type === 'error') {
          runInAction(() => {
            this.error = (event.data as { message: string }).message || 'Auto-trigger failed';
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
          this.error = err.message || 'Failed to auto-trigger annotations';
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
    if (this.autoTriggerTimer) {
      clearTimeout(this.autoTriggerTimer);
      this.autoTriggerTimer = null;
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
    this.cache.clear();
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
