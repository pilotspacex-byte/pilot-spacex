import { makeAutoObservable } from 'mobx';

interface UploadState {
  progress: number; // 0–100
  abortController: AbortController;
  filename: string;
}

/**
 * ArtifactStore — ephemeral MobX store for tracking in-flight file upload progress.
 *
 * Manages upload state keyed by a caller-supplied `uploadKey` (e.g., a temporary
 * node ID in the TipTap editor). Progress is not persisted — clearing the store or
 * reloading the page discards all in-flight state. Completed uploads are removed
 * from the Map so they don't accumulate.
 */
export class ArtifactStore {
  private uploads = new Map<string, UploadState>();

  constructor() {
    makeAutoObservable(this);
  }

  /**
   * Register a new upload and return its AbortController.
   * Callers pass the controller's signal to their XHR or fetch call.
   */
  startUpload(uploadKey: string, filename: string): AbortController {
    const abortController = new AbortController();
    this.uploads.set(uploadKey, { progress: 0, abortController, filename });
    return abortController;
  }

  /**
   * Update progress (0–100) for a registered upload.
   * No-op if the uploadKey is not found (upload may have already completed).
   */
  setProgress(uploadKey: string, progress: number): void {
    const state = this.uploads.get(uploadKey);
    if (state) {
      const normalized = Number.isFinite(progress) ? Math.max(0, Math.min(100, progress)) : 0;
      state.progress = normalized;
    }
  }

  /**
   * Remove upload entry after successful completion.
   */
  completeUpload(uploadKey: string): void {
    this.uploads.delete(uploadKey);
  }

  /**
   * Abort the in-flight request and remove the upload entry.
   */
  cancelUpload(uploadKey: string): void {
    const state = this.uploads.get(uploadKey);
    if (state) state.abortController.abort();
    this.uploads.delete(uploadKey);
  }

  /**
   * Get current progress for an upload, or 0 if not found.
   */
  getProgress(uploadKey: string): number {
    return this.uploads.get(uploadKey)?.progress ?? 0;
  }

  /**
   * Number of currently in-flight uploads.
   */
  get activeUploadCount(): number {
    return this.uploads.size;
  }

  /**
   * Abort all in-flight uploads and clear the Map.
   * Called by RootStore.reset() on sign-out.
   */
  reset(): void {
    for (const state of this.uploads.values()) {
      state.abortController.abort();
    }
    this.uploads.clear();
  }
}
