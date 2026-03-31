import { makeAutoObservable } from 'mobx';
import type { FileTab, OpenFile } from '../types';

/**
 * FileStore — MobX observable store for Monaco IDE tab management.
 *
 * Responsibilities:
 * - Track open file tabs (up to MAX_TABS=12)
 * - LRU eviction: when at capacity, evict the oldest (by lastAccessed) non-dirty tab
 * - Dirty state tracking for unsaved change indicators
 * - Active file tracking
 *
 * Registered on RootStore as `files: FileStore`.
 */
export class FileStore {
  /** Maximum number of simultaneous open tabs. When exceeded, LRU eviction fires. */
  static readonly MAX_TABS = 12;

  /** Map of fileId → OpenFile for all currently open tabs. MobX observable map. */
  openFiles: Map<string, OpenFile> = new Map();

  /** ID of the currently focused/active tab, or null if none are open. */
  activeFileId: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // ─── Computed ─────────────────────────────────────────────────────────────

  /** The currently active file, or null if no file is active. */
  get activeFile(): OpenFile | null {
    if (this.activeFileId === null) return null;
    return this.openFiles.get(this.activeFileId) ?? null;
  }

  /** True when at least one open file has unsaved changes. */
  get hasDirtyFiles(): boolean {
    for (const file of this.openFiles.values()) {
      if (file.isDirty) return true;
    }
    return false;
  }

  /**
   * Returns file IDs in LRU order (oldest last-accessed first).
   * Useful for tab bar rendering and eviction candidate selection.
   */
  get tabOrder(): string[] {
    return Array.from(this.openFiles.values())
      .sort((a, b) => a.lastAccessed - b.lastAccessed)
      .map((f) => f.id);
  }

  // ─── Actions ──────────────────────────────────────────────────────────────

  /**
   * Open a file tab. If the file is already open, re-activates it.
   * When at MAX_TABS, evicts the oldest non-dirty tab before adding.
   *
   * @param file - FileTab to open (originalContent defaults to file.content)
   */
  openFile(file: FileTab): void {
    if (this.openFiles.has(file.id)) {
      // Already open — just activate (update lastAccessed via setActiveFile)
      this.setActiveFile(file.id);
      return;
    }

    // Evict if at capacity
    if (this.openFiles.size >= FileStore.MAX_TABS) {
      this._evictLRU();
    }

    const openFile: OpenFile = {
      ...file,
      isDirty: false,
      lastAccessed: file.lastAccessed ?? Date.now(),
      originalContent: file.content,
    };
    this.openFiles.set(file.id, openFile);
    this.activeFileId = file.id;
  }

  /**
   * Close a file tab by ID.
   * If the closed tab was active, activates the most recently accessed remaining tab,
   * or sets activeFileId to null if no tabs remain.
   */
  closeFile(id: string): void {
    this.openFiles.delete(id);

    if (this.activeFileId === id) {
      // Pick the most recently accessed remaining tab
      const remaining = Array.from(this.openFiles.values()).sort(
        (a, b) => b.lastAccessed - a.lastAccessed
      );
      this.activeFileId = remaining.length > 0 ? (remaining[0]?.id ?? null) : null;
    }
  }

  /**
   * Close all tabs except the specified one.
   * Dirty tabs are skipped (not closed) — they require explicit save or discard first.
   */
  closeOtherFiles(id: string): void {
    for (const [fileId, file] of this.openFiles) {
      if (fileId !== id && !file.isDirty) {
        this.openFiles.delete(fileId);
      }
    }
    this.activeFileId = id;
  }

  /**
   * Set the active file and update its lastAccessed timestamp.
   * No-op if the id is not in openFiles.
   */
  setActiveFile(id: string): void {
    const file = this.openFiles.get(id);
    if (!file) return;

    file.lastAccessed = Date.now();
    this.activeFileId = id;
  }

  /**
   * Mark a file as having unsaved changes.
   * No-op if the id is unknown.
   */
  markDirty(id: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      file.isDirty = true;
    }
  }

  /**
   * Mark a file as clean (no unsaved changes).
   * Typically called after a successful save.
   * No-op if the id is unknown.
   */
  markClean(id: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      file.isDirty = false;
      // After save, current content becomes the new baseline for diff
      file.originalContent = file.content;
    }
  }

  /**
   * Update a file's content without touching dirty state.
   * Callers should call markDirty() separately if the change should be tracked.
   *
   * No-op if the id is unknown.
   */
  updateContent(id: string, content: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      // First content load (lazy) — set as the baseline for diff comparison
      if (file.originalContent == null) {
        file.originalContent = content;
      }
      file.content = content;
    }
  }

  /**
   * Reset the store — clears all tabs and resets active file.
   * Called on logout or workspace switch.
   */
  reset(): void {
    this.openFiles.clear();
    this.activeFileId = null;
  }

  // ─── Private ──────────────────────────────────────────────────────────────

  /**
   * Evict the oldest (by lastAccessed) non-dirty tab.
   *
   * Strategy:
   * 1. Sort all tabs by lastAccessed ascending (oldest first)
   * 2. Skip dirty tabs (they have unsaved changes)
   * 3. Evict the first clean, non-active candidate
   * 4. Fallback: if all tabs are dirty, evict the oldest tab regardless
   */
  private _evictLRU(): void {
    const sorted = Array.from(this.openFiles.entries()).sort(
      ([, a], [, b]) => a.lastAccessed - b.lastAccessed
    );

    // First pass: evict oldest clean tab
    for (const [id, file] of sorted) {
      if (!file.isDirty) {
        this.openFiles.delete(id);
        return;
      }
    }

    // Fallback: all tabs dirty — evict oldest regardless
    const firstId = sorted[0]?.[0];
    if (firstId !== undefined) {
      this.openFiles.delete(firstId);
    }
  }
}
