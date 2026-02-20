import { makeAutoObservable, runInAction, reaction } from 'mobx';
import type {
  Note,
  NoteAnnotation,
  GhostTextSuggestion,
  JSONContent,
  AnnotationStatus,
} from '@/types';
import { notesApi } from '@/services/api';
import { VersionStore } from '@/features/notes/stores/VersionStore';

/**
 * Auto-save configuration
 */
const AUTO_SAVE_DEBOUNCE_MS = 2000;

/**
 * NoteStore - MobX store for Note-First workflow
 *
 * Manages:
 * - Note CRUD operations with optimistic updates
 * - Auto-save with dirty state tracking
 * - AI annotations with accept/reject workflow
 * - Ghost text suggestions for AI-assisted writing
 */
export class NoteStore {
  // Core state
  notes: Map<string, Note> = new Map();
  currentNoteId: string | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  // Auto-save state
  lastSavedAt: Date | null = null;
  private _originalContent: string | null = null;
  private _autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

  // Editor state
  ghostTextSuggestion: GhostTextSuggestion | null = null;
  isGhostTextLoading = false;

  // Annotations - Map of noteId -> annotations[]
  annotationsMap: Map<string, NoteAnnotation[]> = new Map();
  selectedAnnotationId: string | null = null;

  // Version history panel UI state (Feature 017)
  versions: VersionStore = new VersionStore();

  // Filters
  pinnedOnly = false;
  searchQuery = '';

  // Disposal tracking
  private _disposers: (() => void)[] = [];

  constructor() {
    makeAutoObservable(this, {}, { autoBind: true });

    // Set up auto-save reaction
    this._disposers.push(
      reaction(
        () => this.currentNote?.content,
        () => {
          if (this.hasUnsavedChanges) {
            this._scheduleAutoSave();
          }
        },
        { delay: AUTO_SAVE_DEBOUNCE_MS }
      )
    );
  }

  // ============================================
  // COMPUTED PROPERTIES
  // ============================================

  get currentNote(): Note | null {
    return this.currentNoteId ? (this.notes.get(this.currentNoteId) ?? null) : null;
  }

  get notesList(): Note[] {
    return Array.from(this.notes.values());
  }

  get filteredNotes(): Note[] {
    let notes = this.notesList;

    if (this.pinnedOnly) {
      notes = notes.filter((n) => n.isPinned);
    }

    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      notes = notes.filter(
        (n) =>
          n.title.toLowerCase().includes(query) ||
          n.topics.some((t) => t.toLowerCase().includes(query))
      );
    }

    return notes.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }

  get pinnedNotes(): Note[] {
    return this.notesList.filter((n) => n.isPinned);
  }

  get recentNotes(): Note[] {
    return this.filteredNotes.slice(0, 10);
  }

  /**
   * Check if current note has unsaved changes
   */
  get hasUnsavedChanges(): boolean {
    if (!this.currentNote || this._originalContent === null) return false;
    return JSON.stringify(this.currentNote.content) !== this._originalContent;
  }

  /**
   * Get annotations for current note
   */
  get currentAnnotations(): NoteAnnotation[] {
    if (!this.currentNoteId) return [];
    return this.annotationsMap.get(this.currentNoteId) ?? [];
  }

  /**
   * Get pending annotations for current note
   */
  get pendingAnnotations(): NoteAnnotation[] {
    return this.currentAnnotations.filter((a) => a.status === 'pending');
  }

  /**
   * Get annotations sorted by block position
   */
  get sortedAnnotations(): NoteAnnotation[] {
    return [...this.currentAnnotations].sort((a, b) => {
      // Sort by block ID (which should be in document order)
      return a.blockId.localeCompare(b.blockId);
    });
  }

  /**
   * Get annotations grouped by block ID
   */
  get annotationsByBlock(): Map<string, NoteAnnotation[]> {
    const grouped = new Map<string, NoteAnnotation[]>();
    for (const annotation of this.currentAnnotations) {
      const existing = grouped.get(annotation.blockId) ?? [];
      existing.push(annotation);
      grouped.set(annotation.blockId, existing);
    }
    return grouped;
  }

  /**
   * @deprecated Use pendingAnnotations instead
   */
  get unresolvedAnnotations(): NoteAnnotation[] {
    return this.currentAnnotations.filter((a) => a.status === 'pending' || !a.resolved);
  }

  // ============================================
  // SYNCHRONOUS ACTIONS
  // ============================================

  setCurrentNote(noteId: string | null) {
    this.currentNoteId = noteId;
    if (noteId) {
      const note = this.notes.get(noteId);
      if (note) {
        this._originalContent = JSON.stringify(note.content);
      }
      this.loadAnnotations(noteId);
    } else {
      this._originalContent = null;
      this.selectedAnnotationId = null;
    }
  }

  setSearchQuery(query: string) {
    this.searchQuery = query;
  }

  setPinnedOnly(value: boolean) {
    this.pinnedOnly = value;
  }

  selectAnnotation(annotationId: string | null) {
    this.selectedAnnotationId = annotationId;
  }

  setGhostTextSuggestion(suggestion: GhostTextSuggestion | null) {
    this.ghostTextSuggestion = suggestion;
  }

  setGhostTextLoading(loading: boolean) {
    this.isGhostTextLoading = loading;
  }

  /**
   * Update note content locally (for editor sync)
   * Triggers auto-save after debounce
   */
  updateContent(noteId: string, content: JSONContent) {
    const note = this.notes.get(noteId);
    if (!note) return;

    // Calculate word count from content
    const wordCount = this._calculateWordCount(content);
    const readingTimeMins = Math.ceil(wordCount / 200); // Assume 200 WPM

    this.notes.set(noteId, {
      ...note,
      content,
      wordCount,
      readingTimeMins,
      updatedAt: new Date().toISOString(),
    });
  }

  /**
   * Mark content as saved (reset dirty state)
   */
  markAsSaved() {
    if (this.currentNote) {
      this._originalContent = JSON.stringify(this.currentNote.content);
      this.lastSavedAt = new Date();
    }
  }

  // ============================================
  // ANNOTATION ACTIONS
  // ============================================

  /**
   * Accept an annotation (optimistic update)
   */
  async acceptAnnotation(annotationId: string): Promise<boolean> {
    return this._updateAnnotationStatus(annotationId, 'accepted');
  }

  /**
   * Reject an annotation (optimistic update)
   */
  async rejectAnnotation(annotationId: string): Promise<boolean> {
    return this._updateAnnotationStatus(annotationId, 'rejected');
  }

  /**
   * Dismiss an annotation (optimistic update)
   */
  async dismissAnnotation(annotationId: string): Promise<boolean> {
    return this._updateAnnotationStatus(annotationId, 'dismissed');
  }

  private async _updateAnnotationStatus(
    annotationId: string,
    status: AnnotationStatus
  ): Promise<boolean> {
    if (!this.currentNoteId) return false;

    const annotations = this.annotationsMap.get(this.currentNoteId);
    if (!annotations) return false;

    const index = annotations.findIndex((a) => a.id === annotationId);
    if (index === -1) return false;

    const existingAnnotation = annotations[index];
    if (!existingAnnotation) return false;

    const previousStatus = existingAnnotation.status;

    // Optimistic update - create a complete NoteAnnotation object
    const updatedAnnotation: NoteAnnotation = { ...existingAnnotation, status };
    annotations[index] = updatedAnnotation;
    this.annotationsMap.set(this.currentNoteId, [...annotations]);

    try {
      const note = this.notes.get(this.currentNoteId);
      if (!note) throw new Error('Note not found');

      await notesApi.updateAnnotationStatus(
        note.workspaceId,
        this.currentNoteId,
        annotationId,
        status
      );
      return true;
    } catch (err) {
      // Rollback on failure - create a complete NoteAnnotation object for rollback
      runInAction(() => {
        const rollbackAnnotation: NoteAnnotation = {
          ...existingAnnotation,
          status: previousStatus,
        };
        annotations[index] = rollbackAnnotation;
        this.annotationsMap.set(this.currentNoteId!, [...annotations]);
        this.error = err instanceof Error ? err.message : 'Failed to update annotation';
      });
      return false;
    }
  }

  // ============================================
  // ASYNC ACTIONS
  // ============================================

  async loadNotes(workspaceId: string) {
    this.isLoading = true;
    this.error = null;

    try {
      const response = await notesApi.list(workspaceId);
      runInAction(() => {
        this.notes.clear();
        response.items.forEach((note) => {
          // Backend NoteResponse omits workspaceId; inject it so auto-save works
          this.notes.set(note.id, { ...note, workspaceId });
        });
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load notes';
        this.isLoading = false;
      });
    }
  }

  async loadNote(workspaceId: string, noteId: string) {
    this.isLoading = true;
    this.error = null;

    try {
      const note = await notesApi.get(workspaceId, noteId);
      runInAction(() => {
        // Backend NoteDetailResponse omits workspaceId; inject it so auto-save works
        const noteWithWorkspace = { ...note, workspaceId };
        this.notes.set(noteWithWorkspace.id, noteWithWorkspace);
        this.currentNoteId = noteWithWorkspace.id;
        this._originalContent = JSON.stringify(noteWithWorkspace.content);
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load note';
        this.isLoading = false;
      });
    }
  }

  async createNote(workspaceId: string, title: string, projectId?: string) {
    this.isSaving = true;
    this.error = null;

    try {
      const note = await notesApi.create(workspaceId, {
        title,
        workspaceId,
        projectId,
      });
      runInAction(() => {
        this.notes.set(note.id, note);
        this.currentNoteId = note.id;
        this._originalContent = JSON.stringify(note.content);
        this.lastSavedAt = new Date();
        this.isSaving = false;
      });
      return note;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to create note';
        this.isSaving = false;
      });
      return null;
    }
  }

  async updateNote(workspaceId: string, noteId: string, data: Partial<Note>) {
    this.isSaving = true;
    this.error = null;

    try {
      const note = await notesApi.update(workspaceId, noteId, data);
      runInAction(() => {
        this.notes.set(note.id, note);
        if (this.currentNoteId === noteId) {
          this._originalContent = JSON.stringify(note.content);
          this.lastSavedAt = new Date();
        }
        this.isSaving = false;
      });
      return note;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update note';
        this.isSaving = false;
      });
      return null;
    }
  }

  /**
   * Save current note content
   */
  async saveNote(): Promise<boolean> {
    const note = this.currentNote;
    if (!note || !this.hasUnsavedChanges) return true;

    this.isSaving = true;
    this.error = null;

    try {
      await notesApi.updateContent(note.workspaceId, note.id, note.content);
      runInAction(() => {
        this._originalContent = JSON.stringify(note.content);
        this.lastSavedAt = new Date();
        this.isSaving = false;
      });
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to save note';
        this.isSaving = false;
      });
      return false;
    }
  }

  async deleteNote(workspaceId: string, noteId: string) {
    try {
      await notesApi.delete(workspaceId, noteId);
      runInAction(() => {
        this.notes.delete(noteId);
        this.annotationsMap.delete(noteId);
        if (this.currentNoteId === noteId) {
          this.currentNoteId = null;
          this._originalContent = null;
        }
      });
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to delete note';
      });
      return false;
    }
  }

  async togglePin(workspaceId: string, noteId: string) {
    const note = this.notes.get(noteId);
    if (!note) return;

    // Optimistic update
    const previousPinned = note.isPinned;
    this.notes.set(noteId, { ...note, isPinned: !previousPinned });

    try {
      const updatedNote = previousPinned
        ? await notesApi.unpin(workspaceId, noteId)
        : await notesApi.pin(workspaceId, noteId);
      runInAction(() => {
        this.notes.set(updatedNote.id, updatedNote);
      });
    } catch (err) {
      // Rollback
      runInAction(() => {
        this.notes.set(noteId, { ...note, isPinned: previousPinned });
        this.error = err instanceof Error ? err.message : 'Failed to toggle pin';
      });
    }
  }

  async loadAnnotations(noteId: string) {
    const note = this.notes.get(noteId);
    if (!note) return;

    try {
      const annotations = await notesApi.getAnnotations(note.workspaceId, noteId);
      runInAction(() => {
        this.annotationsMap.set(noteId, annotations);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load annotations';
      });
    }
  }

  /**
   * @deprecated Use acceptAnnotation/rejectAnnotation instead
   */
  async resolveAnnotation(workspaceId: string, noteId: string, annotationId: string) {
    try {
      const annotation = await notesApi.resolveAnnotation(workspaceId, noteId, annotationId);
      runInAction(() => {
        const annotations = this.annotationsMap.get(noteId) ?? [];
        const index = annotations.findIndex((a) => a.id === annotationId);
        if (index !== -1) {
          annotations[index] = annotation;
          this.annotationsMap.set(noteId, [...annotations]);
        }
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to resolve annotation';
      });
    }
  }

  // ============================================
  // PRIVATE METHODS
  // ============================================

  private _scheduleAutoSave() {
    if (this._autoSaveTimer) {
      clearTimeout(this._autoSaveTimer);
    }

    this._autoSaveTimer = setTimeout(() => {
      this.saveNote();
    }, AUTO_SAVE_DEBOUNCE_MS);
  }

  private _calculateWordCount(content: JSONContent): number {
    let count = 0;

    const traverse = (node: JSONContent) => {
      if (node.text) {
        count += node.text.split(/\s+/).filter(Boolean).length;
      }
      if (node.content) {
        node.content.forEach(traverse);
      }
    };

    traverse(content);
    return count;
  }

  // ============================================
  // LIFECYCLE
  // ============================================

  reset() {
    if (this._autoSaveTimer) {
      clearTimeout(this._autoSaveTimer);
    }

    this.notes.clear();
    this.annotationsMap.clear();
    this.currentNoteId = null;
    this._originalContent = null;
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.lastSavedAt = null;
    this.ghostTextSuggestion = null;
    this.isGhostTextLoading = false;
    this.selectedAnnotationId = null;
    this.pinnedOnly = false;
    this.searchQuery = '';
    this.versions.reset();
  }

  dispose() {
    if (this._autoSaveTimer) {
      clearTimeout(this._autoSaveTimer);
    }
    this._disposers.forEach((dispose) => dispose());
    this._disposers = [];
  }
}

export const noteStore = new NoteStore();
