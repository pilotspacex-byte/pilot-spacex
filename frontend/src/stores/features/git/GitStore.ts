'use client';

import { makeAutoObservable, runInAction } from 'mobx';
import type {
  FileDiff,
  GitProgress,
  GitPullResult,
  GitRepoStatus,
  BranchInfo,
  FileStatus,
} from '@/lib/tauri';

export class GitStore {
  // Active repo path — set by UI when user selects a project
  repoPath: string = '';

  // Current file statuses + branch + ahead/behind
  status: GitRepoStatus | null = null;

  // All local + remote branches
  branches: BranchInfo[] = [];

  // Loading flags
  isLoadingStatus = false;
  isLoadingBranches = false;

  // Pull state
  isPulling = false;
  pullProgress: GitProgress | null = null;
  pullResult: GitPullResult | null = null;
  pullError: string | null = null;

  // Push state
  isPushing = false;
  pushProgress: GitProgress | null = null;
  pushError: string | null = null;

  // General error (status/branch operations)
  error: string | null = null;

  // Diff state
  selectedFilePath: string | null = null;
  fileDiffs: FileDiff[] = [];
  isLoadingDiff = false;
  diffError: string | null = null;

  // Commit state
  isCommitting = false;
  commitError: string | null = null;
  lastCommitOid: string | null = null;

  // Stage/unstage state
  isStaging = false;
  stageError: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // --- Computed ---

  get currentBranch(): string {
    return this.status?.branch ?? '';
  }

  get hasConflicts(): boolean {
    return (this.pullResult?.conflicts.length ?? 0) > 0;
  }

  get conflictedFiles(): string[] {
    return this.pullResult?.conflicts ?? [];
  }

  get modifiedFiles(): FileStatus[] {
    return this.status?.files.filter((f) => f.status !== 'untracked') ?? [];
  }

  get untrackedFiles(): FileStatus[] {
    return this.status?.files.filter((f) => f.status === 'untracked') ?? [];
  }

  get stagedFiles(): FileStatus[] {
    return this.status?.files.filter((f) => f.staged) ?? [];
  }

  // --- Actions ---

  /**
   * Set the active repository path.
   * Clears all state and triggers a full refresh if path is non-empty.
   */
  setRepoPath(path: string): void {
    this.repoPath = path;
    this.status = null;
    this.branches = [];
    this.pullResult = null;
    this.pullError = null;
    this.pushError = null;
    this.error = null;
    this.selectedFilePath = null;
    this.fileDiffs = [];
    this.diffError = null;
    this.commitError = null;
    this.lastCommitOid = null;
    this.stageError = null;
    if (path) {
      void this.refreshAll();
    }
  }

  /**
   * Fetch the current working tree and index status for the active repo.
   */
  async refreshStatus(): Promise<void> {
    if (!this.repoPath) return;
    this.isLoadingStatus = true;
    this.error = null;
    try {
      const { gitStatus } = await import('@/lib/tauri');
      const result = await gitStatus(this.repoPath);
      runInAction(() => {
        this.status = result;
        this.isLoadingStatus = false;
      });
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
        this.isLoadingStatus = false;
      });
    }
  }

  /**
   * Fetch all local and remote branches for the active repo.
   */
  async refreshBranches(): Promise<void> {
    if (!this.repoPath) return;
    this.isLoadingBranches = true;
    this.error = null;
    try {
      const { gitBranchList } = await import('@/lib/tauri');
      const result = await gitBranchList(this.repoPath);
      runInAction(() => {
        this.branches = result;
        this.isLoadingBranches = false;
      });
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
        this.isLoadingBranches = false;
      });
    }
  }

  /**
   * Refresh both status and branches in parallel.
   */
  async refreshAll(): Promise<void> {
    await Promise.all([this.refreshStatus(), this.refreshBranches()]);
  }

  /**
   * Pull from origin for the active repo, streaming progress updates.
   * Automatically refreshes all state after completion.
   */
  async pull(): Promise<void> {
    if (!this.repoPath) return;
    this.isPulling = true;
    this.pullProgress = null;
    this.pullResult = null;
    this.pullError = null;
    try {
      const { gitPull } = await import('@/lib/tauri');
      const result = await gitPull(this.repoPath, (progress) => {
        runInAction(() => {
          this.pullProgress = progress;
        });
      });
      runInAction(() => {
        this.pullResult = result;
        this.isPulling = false;
        this.pullProgress = null;
      });
      await this.refreshAll();
    } catch (e) {
      runInAction(() => {
        this.pullError = e instanceof Error ? e.message : String(e);
        this.isPulling = false;
        this.pullProgress = null;
      });
    }
  }

  /**
   * Push the current branch to origin for the active repo, streaming progress updates.
   * Automatically refreshes all state after completion.
   */
  async push(): Promise<void> {
    if (!this.repoPath) return;
    this.isPushing = true;
    this.pushProgress = null;
    this.pushError = null;
    try {
      const { gitPush } = await import('@/lib/tauri');
      await gitPush(this.repoPath, (progress) => {
        runInAction(() => {
          this.pushProgress = progress;
        });
      });
      runInAction(() => {
        this.isPushing = false;
        this.pushProgress = null;
      });
      await this.refreshAll();
    } catch (e) {
      runInAction(() => {
        this.pushError = e instanceof Error ? e.message : String(e);
        this.isPushing = false;
        this.pushProgress = null;
      });
    }
  }

  /**
   * Create a new branch from the current HEAD commit, then refresh branches.
   */
  async createBranch(name: string): Promise<void> {
    if (!this.repoPath) return;
    this.error = null;
    try {
      const { gitBranchCreate } = await import('@/lib/tauri');
      await gitBranchCreate(this.repoPath, name);
      await this.refreshBranches();
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
      });
    }
  }

  /**
   * Switch to a branch by name using a safe checkout, then refresh all state.
   */
  async switchBranch(name: string): Promise<void> {
    if (!this.repoPath) return;
    this.error = null;
    try {
      const { gitBranchSwitch } = await import('@/lib/tauri');
      await gitBranchSwitch(this.repoPath, name);
      await this.refreshAll();
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
      });
    }
  }

  /**
   * Delete a local branch by name, then refresh branches.
   */
  async deleteBranch(name: string): Promise<void> {
    if (!this.repoPath) return;
    this.error = null;
    try {
      const { gitBranchDelete } = await import('@/lib/tauri');
      await gitBranchDelete(this.repoPath, name);
      await this.refreshBranches();
    } catch (e) {
      runInAction(() => {
        this.error = e instanceof Error ? e.message : String(e);
      });
    }
  }

  /**
   * Dismiss the last pull result (acknowledge conflicts or clear success state).
   */
  dismissConflicts(): void {
    this.pullResult = null;
  }

  /**
   * Reset all observables to their initial defaults.
   */
  reset(): void {
    this.repoPath = '';
    this.status = null;
    this.branches = [];
    this.isLoadingStatus = false;
    this.isLoadingBranches = false;
    this.isPulling = false;
    this.pullProgress = null;
    this.pullResult = null;
    this.pullError = null;
    this.isPushing = false;
    this.pushProgress = null;
    this.pushError = null;
    this.error = null;
    this.selectedFilePath = null;
    this.fileDiffs = [];
    this.isLoadingDiff = false;
    this.diffError = null;
    this.isCommitting = false;
    this.commitError = null;
    this.lastCommitOid = null;
    this.isStaging = false;
    this.stageError = null;
  }

  // --- Diff / Stage / Unstage / Commit actions ---

  /**
   * Fetch the unified diff for a specific file or all changed files.
   * Stores results in `fileDiffs`. Sets `isLoadingDiff` while loading.
   */
  async fetchDiff(filePath?: string): Promise<void> {
    if (!this.repoPath) return;
    runInAction(() => {
      this.isLoadingDiff = true;
      this.diffError = null;
    });
    try {
      const { gitDiff } = await import('@/lib/tauri');
      const result = await gitDiff(this.repoPath, filePath);
      runInAction(() => {
        this.fileDiffs = result;
        this.isLoadingDiff = false;
      });
    } catch (e) {
      runInAction(() => {
        this.diffError = e instanceof Error ? e.message : String(e);
        this.isLoadingDiff = false;
      });
    }
  }

  /**
   * Stage the specified files in the git index, then refresh status.
   */
  async stageFiles(paths: string[]): Promise<void> {
    if (!this.repoPath) return;
    runInAction(() => {
      this.isStaging = true;
      this.stageError = null;
    });
    try {
      const { gitStage } = await import('@/lib/tauri');
      await gitStage(this.repoPath, paths);
      await this.refreshStatus();
      runInAction(() => {
        this.isStaging = false;
      });
    } catch (e) {
      runInAction(() => {
        this.stageError = e instanceof Error ? e.message : String(e);
        this.isStaging = false;
      });
    }
  }

  /**
   * Unstage the specified files (reset index to HEAD), then refresh status.
   */
  async unstageFiles(paths: string[]): Promise<void> {
    if (!this.repoPath) return;
    runInAction(() => {
      this.isStaging = true;
      this.stageError = null;
    });
    try {
      const { gitUnstage } = await import('@/lib/tauri');
      await gitUnstage(this.repoPath, paths);
      await this.refreshStatus();
      runInAction(() => {
        this.isStaging = false;
      });
    } catch (e) {
      runInAction(() => {
        this.stageError = e instanceof Error ? e.message : String(e);
        this.isStaging = false;
      });
    }
  }

  /**
   * Stage all unstaged and untracked files in the working tree.
   */
  async stageAll(): Promise<void> {
    const allPaths = this.status?.files.filter((f) => !f.staged).map((f) => f.path) ?? [];
    if (allPaths.length === 0) return;
    await this.stageFiles(allPaths);
  }

  /**
   * Unstage all currently staged files.
   */
  async unstageAll(): Promise<void> {
    const stagedPaths = this.status?.files.filter((f) => f.staged).map((f) => f.path) ?? [];
    if (stagedPaths.length === 0) return;
    await this.unstageFiles(stagedPaths);
  }

  /**
   * Create a commit from the currently staged files with the given message.
   * Stores the resulting commit OID in `lastCommitOid`. Refreshes status after.
   */
  async commit(message: string): Promise<void> {
    if (!this.repoPath) return;
    runInAction(() => {
      this.isCommitting = true;
      this.commitError = null;
    });
    try {
      const { gitCommit } = await import('@/lib/tauri');
      const oid = await gitCommit(this.repoPath, message);
      runInAction(() => {
        this.lastCommitOid = oid;
        this.isCommitting = false;
      });
      await this.refreshStatus();
    } catch (e) {
      runInAction(() => {
        this.commitError = e instanceof Error ? e.message : String(e);
        this.isCommitting = false;
      });
    }
  }

  /**
   * Select a file to view its diff. Automatically triggers fetchDiff for non-null paths.
   */
  selectFile(path: string | null): void {
    this.selectedFilePath = path;
    if (path !== null) {
      void this.fetchDiff(path);
    }
  }

  /**
   * Clear commit result state (error + OID). Call after user acknowledges.
   */
  clearCommitState(): void {
    this.commitError = null;
    this.lastCommitOid = null;
  }
}
