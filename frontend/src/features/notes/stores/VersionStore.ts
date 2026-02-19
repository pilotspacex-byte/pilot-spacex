'use client';

/**
 * VersionStore — MobX UI state for note version history panel.
 *
 * MobX holds: panel open/closed, selected version ID, diff pair IDs,
 *   pending restore state, saving indicator.
 * TanStack Query holds: actual version list data (server state).
 *
 * Feature 017: Note Versioning — Sprint 1 (T-216)
 */
import { makeAutoObservable, runInAction } from 'mobx';

export type VersionPanelView = 'timeline' | 'diff' | 'restore';

export class VersionStore {
  /** Panel visibility */
  isOpen = false;
  /** Active sub-view within the panel */
  view: VersionPanelView = 'timeline';
  /** Currently selected version ID in timeline */
  selectedVersionId: string | null = null;
  /** Version IDs selected for diff (v1 = older, v2 = newer) */
  diffVersionIds: [string, string] | null = null;
  /** Version ID that is being restored */
  pendingRestoreVersionId: string | null = null;
  /** Whether a save-version request is in flight */
  isSaving = false;
  /** Whether an undo-ai request is in flight */
  isUndoingAI = false;
  /** 409 conflict info from a restore attempt */
  conflictVersionNumber: number | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  open(): void {
    this.isOpen = true;
  }

  close(): void {
    this.isOpen = false;
    this.view = 'timeline';
    this.selectedVersionId = null;
    this.diffVersionIds = null;
    this.pendingRestoreVersionId = null;
    this.conflictVersionNumber = null;
  }

  toggle(): void {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  selectVersion(versionId: string): void {
    this.selectedVersionId = versionId;
  }

  clearSelection(): void {
    this.selectedVersionId = null;
  }

  openDiff(v1Id: string, v2Id: string): void {
    this.diffVersionIds = [v1Id, v2Id];
    this.view = 'diff';
  }

  closeDiff(): void {
    this.diffVersionIds = null;
    this.view = 'timeline';
  }

  openRestore(versionId: string): void {
    this.pendingRestoreVersionId = versionId;
    this.view = 'restore';
  }

  cancelRestore(): void {
    this.pendingRestoreVersionId = null;
    this.conflictVersionNumber = null;
    this.view = 'timeline';
  }

  setSaving(saving: boolean): void {
    runInAction(() => {
      this.isSaving = saving;
    });
  }

  setUndoingAI(undoing: boolean): void {
    runInAction(() => {
      this.isUndoingAI = undoing;
    });
  }

  setConflict(currentVersionNumber: number): void {
    runInAction(() => {
      this.conflictVersionNumber = currentVersionNumber;
    });
  }

  reset(): void {
    this.isOpen = false;
    this.view = 'timeline';
    this.selectedVersionId = null;
    this.diffVersionIds = null;
    this.pendingRestoreVersionId = null;
    this.isSaving = false;
    this.isUndoingAI = false;
    this.conflictVersionNumber = null;
  }
}
