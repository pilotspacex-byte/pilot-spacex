/**
 * Shared TypeScript types for the Source Control (SCM) feature.
 *
 * These types model the git proxy API responses and client-side
 * staging state used by the GitWebStore and SCM panel components.
 */

export interface ChangedFile {
  path: string;
  status: 'modified' | 'added' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  patch: string | null;
  /** Client-side staging state (not persisted to backend). */
  staged: boolean;
}

export interface BranchInfo {
  name: string;
  sha: string;
  isDefault: boolean;
  isProtected: boolean;
}

export interface CommitResult {
  sha: string;
  htmlUrl: string;
  message: string;
}

export interface PullRequestResult {
  number: number;
  htmlUrl: string;
  title: string;
  draft: boolean;
}

export interface FileChange {
  path: string;
  content: string;
  encoding?: string;
  action?: 'create' | 'update' | 'delete';
}

export interface GitRepo {
  owner: string;
  repo: string;
  provider: 'github' | 'gitlab';
  integrationId: string;
  defaultBranch: string;
}

export interface GitStatusResponse {
  files: Omit<ChangedFile, 'staged'>[];
  branch: string;
  totalFiles: number;
  truncated: boolean;
}

export interface FileContentResponse {
  content: string;
  encoding: string;
  sha: string;
  size: number;
}

export interface BranchListResponse {
  branches: BranchInfo[];
  page: number;
  perPage: number;
}
