import { makeAutoObservable } from 'mobx';
import type { OpenFile } from '@/features/editor/types';

/**
 * FileStore manages open file tabs, active file selection, and dirty state.
 *
 * Registered in RootStore as `fileStore`. Provides computed properties for
 * tab rendering, dirty-file tracking, and tab eviction when MAX_TABS is reached.
 */
export class FileStore {
  static readonly MAX_TABS = 12;

  openFiles: Map<string, OpenFile> = new Map();
  activeFileId: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  /** The currently active file, or undefined if no file is open. */
  get activeFile(): OpenFile | undefined {
    if (this.activeFileId === null) return undefined;
    return this.openFiles.get(this.activeFileId);
  }

  /** Array of all open files in insertion order. */
  get tabs(): OpenFile[] {
    return Array.from(this.openFiles.values());
  }

  /** True when any open file has unsaved changes. */
  get hasDirtyFiles(): boolean {
    return this.tabs.some((f) => f.isDirty);
  }

  /**
   * Open a file in the editor. If already open, just activates it.
   * When at MAX_TABS, evicts the oldest non-dirty, non-active tab.
   */
  openFile(file: Omit<OpenFile, 'isDirty'>): void {
    if (!this.openFiles.has(file.id)) {
      // Evict if at capacity
      if (this.openFiles.size >= FileStore.MAX_TABS) {
        this._evictOne();
      }
      this.openFiles.set(file.id, { ...file, isDirty: false });
    }
    this.activeFileId = file.id;
  }

  /** Close a file tab. Falls back active to last remaining tab or null. */
  closeFile(id: string): void {
    this.openFiles.delete(id);
    if (this.activeFileId === id) {
      const keys = Array.from(this.openFiles.keys());
      this.activeFileId = keys.length > 0 ? keys[keys.length - 1]! : null;
    }
  }

  /** Close all open tabs. */
  closeAll(): void {
    this.openFiles.clear();
    this.activeFileId = null;
  }

  /** Close all tabs except the specified one. */
  closeOthers(keepId: string): void {
    const kept = this.openFiles.get(keepId);
    this.openFiles.clear();
    if (kept) {
      this.openFiles.set(keepId, kept);
    }
    this.activeFileId = keepId;
  }

  /** Mark a file as having unsaved changes. */
  markDirty(id: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      file.isDirty = true;
    }
  }

  /** Mark a file as saved / clean. */
  markClean(id: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      file.isDirty = false;
    }
  }

  /** Update a file's content and mark it dirty. */
  updateContent(id: string, content: string): void {
    const file = this.openFiles.get(id);
    if (file) {
      file.content = content;
      file.isDirty = true;
    }
  }

  /** Reset the store (for logout / workspace switch). */
  reset(): void {
    this.openFiles.clear();
    this.activeFileId = null;
  }

  /**
   * Evict the oldest non-dirty, non-active tab.
   * If all tabs are dirty or active, evicts the oldest tab.
   */
  private _evictOne(): void {
    for (const [id, file] of this.openFiles) {
      if (!file.isDirty && id !== this.activeFileId) {
        this.openFiles.delete(id);
        return;
      }
    }
    // Fallback: evict the first tab regardless
    const firstKey = this.openFiles.keys().next().value as string | undefined;
    if (firstKey) {
      this.openFiles.delete(firstKey);
    }
  }
}
