import { makeAutoObservable } from 'mobx';
import type { ChangedFile } from '../git-types';

/**
 * GitStore — MobX observable store for Monaco IDE source control state.
 *
 * Responsibilities:
 * - Track current branch and default branch
 * - Track changed files list
 * - Track repo owner and name (from workspace integrations)
 * - Provide derived state: hasChanges, repoFullName
 *
 * Registered on RootStore as `git: GitStore`.
 */
export class GitStore {
  /** The currently checked-out branch name, or null if no repo connected. */
  currentBranch: string | null = null;

  /** The default branch name (e.g. "main"), or null if not yet loaded. */
  defaultBranch: string | null = null;

  /** List of changed files from the last git status fetch. */
  changedFiles: ChangedFile[] = [];

  /** Whether a git operation (status fetch, commit, etc.) is in progress. */
  isLoading: boolean = false;

  /** GitHub/GitLab repository owner (org or user), or null if not connected. */
  owner: string | null = null;

  /** Repository name (without owner prefix), or null if not connected. */
  repo: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // ─── Computed ─────────────────────────────────────────────────────────────

  /** True when there is at least one changed file. */
  get hasChanges(): boolean {
    return this.changedFiles.length > 0;
  }

  /**
   * Returns the full repository name in "owner/repo" format when both
   * owner and repo are set; null otherwise.
   */
  get repoFullName(): string | null {
    if (this.owner && this.repo) {
      return `${this.owner}/${this.repo}`;
    }
    return null;
  }

  // ─── Actions ──────────────────────────────────────────────────────────────

  /**
   * Update the current branch name.
   * Called after a branch switch or on initial status fetch.
   */
  setBranch(branch: string): void {
    this.currentBranch = branch;
  }

  /**
   * Update the default branch name.
   * Typically called once when the integration config is loaded.
   */
  setDefaultBranch(branch: string): void {
    this.defaultBranch = branch;
  }

  /**
   * Set owner and repository name from the workspace integration config.
   * Called when useProjectGitIntegration resolves owner/repo.
   */
  setRepoInfo(owner: string, repo: string): void {
    this.owner = owner;
    this.repo = repo;
  }

  /**
   * Replace the changed files list.
   * Called by useGitStatus after each status fetch.
   */
  setChangedFiles(files: ChangedFile[]): void {
    this.changedFiles = files;
  }

  /**
   * Set the loading state.
   * Used by hooks to indicate in-progress git operations.
   */
  setLoading(loading: boolean): void {
    this.isLoading = loading;
  }

  /**
   * Reset all state back to defaults.
   * Called on logout, workspace switch, or IDE close.
   */
  reset(): void {
    this.currentBranch = null;
    this.defaultBranch = null;
    this.changedFiles = [];
    this.isLoading = false;
    this.owner = null;
    this.repo = null;
  }
}
