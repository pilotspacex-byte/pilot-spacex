import { makeAutoObservable } from 'mobx';
import type { ChangedFile, GitRepo } from '@/features/source-control/types';

/**
 * GitWebStore - MobX store for Source Control panel UI state.
 *
 * Manages:
 * - Current repo and branch context
 * - Changed files with client-side staging
 * - Commit message and file selection
 *
 * This store holds UI state only. Actual API calls are made by
 * TanStack Query hooks in the SCM panel components.
 */
export class GitWebStore {
  currentRepo: GitRepo | null = null;
  currentBranch = '';
  defaultBranch = '';
  changedFiles: ChangedFile[] = [];
  commitMessage = '';
  selectedFilePath: string | null = null;
  isLoading = false;
  isCommitting = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // --- Computed properties ---

  get stagedFiles(): ChangedFile[] {
    return this.changedFiles.filter((f) => f.staged);
  }

  get unstagedFiles(): ChangedFile[] {
    return this.changedFiles.filter((f) => !f.staged);
  }

  get changedFileCount(): number {
    return this.changedFiles.length;
  }

  get hasStagedFiles(): boolean {
    return this.stagedFiles.length > 0;
  }

  get canCommit(): boolean {
    return this.hasStagedFiles && this.commitMessage.trim().length > 0 && !this.isCommitting;
  }

  // --- Actions ---

  setRepo(repo: GitRepo): void {
    this.currentRepo = repo;
    this.currentBranch = repo.defaultBranch;
    this.defaultBranch = repo.defaultBranch;
  }

  switchBranch(branch: string): void {
    this.currentBranch = branch;
    this.changedFiles = [];
    this.commitMessage = '';
    this.selectedFilePath = null;
    this.error = null;
  }

  stageFile(path: string): void {
    const file = this.changedFiles.find((f) => f.path === path);
    if (file) file.staged = true;
  }

  unstageFile(path: string): void {
    const file = this.changedFiles.find((f) => f.path === path);
    if (file) file.staged = false;
  }

  stageAll(): void {
    this.changedFiles.forEach((f) => {
      f.staged = true;
    });
  }

  unstageAll(): void {
    this.changedFiles.forEach((f) => {
      f.staged = false;
    });
  }

  setCommitMessage(message: string): void {
    this.commitMessage = message;
  }

  selectFile(path: string | null): void {
    this.selectedFilePath = path;
  }

  setChangedFiles(files: Omit<ChangedFile, 'staged'>[]): void {
    this.changedFiles = files.map((f) => ({ ...f, staged: false }));
  }

  clearAfterCommit(): void {
    this.commitMessage = '';
    this.changedFiles.forEach((f) => {
      f.staged = false;
    });
  }

  reset(): void {
    this.currentRepo = null;
    this.currentBranch = '';
    this.defaultBranch = '';
    this.changedFiles = [];
    this.commitMessage = '';
    this.selectedFilePath = null;
    this.isLoading = false;
    this.isCommitting = false;
    this.error = null;
  }
}
