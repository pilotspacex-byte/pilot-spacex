import { apiClient } from './client';
import type {
  GitStatusResponse,
  FileContentResponse,
  BranchListResponse,
  BranchInfo,
  CommitResult,
  PullRequestResult,
  FileChange,
} from '@/features/source-control/types';

/**
 * API service layer for git proxy endpoints.
 *
 * All functions communicate with the backend git proxy router
 * (`/api/v1/git/repos/{owner}/{repo}/...`). The backend forwards
 * requests to the appropriate git provider (GitHub / GitLab) using
 * the workspace integration identified by `integrationId`.
 */

function repoBase(owner: string, repo: string): string {
  return `/git/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`;
}

/**
 * Get repository status (changed files between branch and base ref).
 */
export async function getRepoStatus(
  owner: string,
  repo: string,
  integrationId: string,
  branch: string,
  baseRef?: string
): Promise<GitStatusResponse> {
  const params: Record<string, string> = {
    integration_id: integrationId,
    branch,
  };
  if (baseRef) params.base_ref = baseRef;

  return apiClient.get<GitStatusResponse>(`${repoBase(owner, repo)}/status`, { params });
}

/**
 * Get file content at a specific ref.
 */
export async function getFileContent(
  owner: string,
  repo: string,
  integrationId: string,
  path: string,
  ref: string
): Promise<FileContentResponse> {
  return apiClient.get<FileContentResponse>(
    `${repoBase(owner, repo)}/files/${encodeURIComponent(path)}`,
    { params: { integration_id: integrationId, ref } }
  );
}

/**
 * List branches with optional search and pagination.
 */
export async function listBranches(
  owner: string,
  repo: string,
  integrationId: string,
  search?: string,
  page?: number,
  perPage?: number
): Promise<BranchListResponse> {
  const params: Record<string, string | number> = {
    integration_id: integrationId,
  };
  if (search) params.search = search;
  if (page != null) params.page = page;
  if (perPage != null) params.per_page = perPage;

  return apiClient.get<BranchListResponse>(`${repoBase(owner, repo)}/branches`, { params });
}

/**
 * Create a new branch from a given ref.
 */
export async function createBranch(
  owner: string,
  repo: string,
  integrationId: string,
  name: string,
  fromRef: string
): Promise<BranchInfo> {
  return apiClient.post<BranchInfo>(
    `${repoBase(owner, repo)}/branches`,
    { name, from_ref: fromRef },
    { params: { integration_id: integrationId } }
  );
}

/**
 * Delete a branch by name.
 */
export async function deleteBranch(
  owner: string,
  repo: string,
  integrationId: string,
  name: string
): Promise<void> {
  await apiClient.delete(`${repoBase(owner, repo)}/branches/${encodeURIComponent(name)}`, {
    params: { integration_id: integrationId },
  });
}

/**
 * Get the default branch for a repository.
 */
export async function getDefaultBranch(
  owner: string,
  repo: string,
  integrationId: string
): Promise<{ default_branch: string }> {
  return apiClient.get<{ default_branch: string }>(`${repoBase(owner, repo)}/default-branch`, {
    params: { integration_id: integrationId },
  });
}

/**
 * Create a commit with file changes on a branch.
 */
export async function createCommit(
  owner: string,
  repo: string,
  integrationId: string,
  branch: string,
  message: string,
  files: FileChange[]
): Promise<CommitResult> {
  return apiClient.post<CommitResult>(
    `${repoBase(owner, repo)}/commits`,
    { branch, message, files },
    { params: { integration_id: integrationId } }
  );
}

/**
 * Create a pull request.
 */
export async function createPR(
  owner: string,
  repo: string,
  integrationId: string,
  title: string,
  body: string,
  head: string,
  base: string,
  draft?: boolean
): Promise<PullRequestResult> {
  return apiClient.post<PullRequestResult>(
    `${repoBase(owner, repo)}/pulls`,
    { title, body, head, base, draft: draft ?? false },
    { params: { integration_id: integrationId } }
  );
}
