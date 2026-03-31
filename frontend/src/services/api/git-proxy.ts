/**
 * git-proxy.ts — API client for the git proxy endpoints.
 *
 * Wraps all git proxy routes:
 * - GET /workspaces/{wid}/git/repos/{owner}/{repo}/branches
 * - GET /workspaces/{wid}/git/repos/{owner}/{repo}/status
 * - GET /workspaces/{wid}/git/repos/{owner}/{repo}/files/{path}
 * - POST /workspaces/{wid}/git/repos/{owner}/{repo}/commits
 * - POST /workspaces/{wid}/git/repos/{owner}/{repo}/pulls
 */

import { apiClient } from './client';
import type {
  BranchListResponse,
  BranchInfo,
  GitStatusResponse,
  FileContentResponse,
  CommitResult,
  PullRequestResult,
  FileChange,
} from '@/features/code/git-types';

// ─── Helper ──────────────────────────────────────────────────────────────────

function repoBase(workspaceId: string, owner: string, repo: string): string {
  return `/workspaces/${workspaceId}/git/repos/${owner}/${repo}`;
}

// ─── Branches ─────────────────────────────────────────────────────────────────

/**
 * List branches for a repository.
 */
export function listBranches(
  workspaceId: string,
  owner: string,
  repo: string,
  search?: string
): Promise<BranchListResponse> {
  const params = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiClient.get<BranchListResponse>(`${repoBase(workspaceId, owner, repo)}/branches${params}`);
}

/**
 * Create a new branch from a source branch.
 */
export function createBranch(
  workspaceId: string,
  owner: string,
  repo: string,
  newBranchName: string,
  fromBranch: string
): Promise<BranchInfo> {
  return apiClient.post<BranchInfo>(`${repoBase(workspaceId, owner, repo)}/branches`, {
    name: newBranchName,
    from: fromBranch,
  });
}

/**
 * Delete a branch.
 */
export function deleteBranch(
  workspaceId: string,
  owner: string,
  repo: string,
  branchName: string
): Promise<void> {
  return apiClient.delete<void>(
    `${repoBase(workspaceId, owner, repo)}/branches/${encodeURIComponent(branchName)}`
  );
}

// ─── Status ───────────────────────────────────────────────────────────────────

/**
 * Get git status (changed files) for a repository on a branch.
 */
export function getRepoStatus(
  workspaceId: string,
  owner: string,
  repo: string,
  branch: string
): Promise<GitStatusResponse> {
  return apiClient.get<GitStatusResponse>(
    `${repoBase(workspaceId, owner, repo)}/status?branch=${encodeURIComponent(branch)}`
  );
}

// ─── File Content ─────────────────────────────────────────────────────────────

/**
 * Get file content from a repository at a given branch.
 */
export function getFileContent(
  workspaceId: string,
  owner: string,
  repo: string,
  filePath: string,
  branch: string
): Promise<FileContentResponse> {
  return apiClient.get<FileContentResponse>(
    `${repoBase(workspaceId, owner, repo)}/files/${encodeURIComponent(filePath)}?branch=${encodeURIComponent(branch)}`
  );
}

// ─── Commits ──────────────────────────────────────────────────────────────────

/**
 * Create a commit with the given files.
 */
export function createCommit(
  workspaceId: string,
  owner: string,
  repo: string,
  branch: string,
  message: string,
  files: FileChange[]
): Promise<CommitResult> {
  return apiClient.post<CommitResult>(`${repoBase(workspaceId, owner, repo)}/commits`, {
    branch,
    message,
    files,
  });
}

// ─── Pull Requests ────────────────────────────────────────────────────────────

/**
 * Create a pull request.
 */
export function createPR(
  workspaceId: string,
  owner: string,
  repo: string,
  title: string,
  body: string,
  head: string,
  base: string,
  draft: boolean
): Promise<PullRequestResult> {
  return apiClient.post<PullRequestResult>(`${repoBase(workspaceId, owner, repo)}/pulls`, {
    title,
    body,
    head,
    base,
    draft,
  });
}
