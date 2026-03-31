import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api/client';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface FileDiff {
  path: string;
  status: 'modified' | 'added' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
  patch: string | null;
  originalContent: string;
  modifiedContent: string;
}

interface CompareResponse {
  files: Array<{
    filename: string;
    status: 'modified' | 'added' | 'deleted' | 'renamed';
    additions: number;
    deletions: number;
    patch?: string;
    previous_filename?: string;
  }>;
  base_commit: string;
  head_commit: string;
}

// ─── Language detection ───────────────────────────────────────────────────────

/**
 * Map file extensions to Monaco language identifiers.
 */
export function getLanguageFromPath(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    ts: 'typescript',
    tsx: 'typescript',
    js: 'javascript',
    jsx: 'javascript',
    py: 'python',
    md: 'markdown',
    json: 'json',
    html: 'html',
    css: 'css',
    scss: 'scss',
    less: 'less',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    sql: 'sql',
    sh: 'shell',
    bash: 'shell',
    zsh: 'shell',
    rs: 'rust',
    go: 'go',
    java: 'java',
    rb: 'ruby',
    php: 'php',
    c: 'c',
    cpp: 'cpp',
    h: 'c',
    hpp: 'cpp',
    toml: 'toml',
    ini: 'ini',
    dockerfile: 'dockerfile',
    graphql: 'graphql',
    gql: 'graphql',
    svg: 'xml',
  };
  return map[ext] ?? 'plaintext';
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * useFileDiff — TanStack Query hook fetching diff data for a changed file.
 *
 * Uses the git proxy compare endpoint:
 *   GET /api/v1/workspaces/{wid}/git/repos/{owner}/{repo}/compare/{base}...{head}
 *
 * @param workspaceId - Workspace UUID
 * @param owner       - GitHub repository owner
 * @param repo        - GitHub repository name
 * @param filePath    - Path to the changed file (null when no diff selected)
 * @param base        - Base ref (defaultBranch or commit SHA)
 * @param head        - Head ref (currentBranch)
 */
export function useFileDiff(
  workspaceId: string | null | undefined,
  owner: string | null | undefined,
  repo: string | null | undefined,
  filePath: string | null | undefined,
  base: string | null | undefined,
  head: string | null | undefined
): { diffs: FileDiff[]; isLoading: boolean } {
  const enabled = Boolean(workspaceId) && Boolean(owner) && Boolean(repo) && Boolean(base) && Boolean(head);

  const { data, isLoading } = useQuery<FileDiff[]>({
    queryKey: ['file-diff', workspaceId, owner, repo, base, head],
    queryFn: async (): Promise<FileDiff[]> => {
      const response = await apiClient.get<CompareResponse>(
        `/workspaces/${workspaceId!}/git/repos/${owner!}/${repo!}/compare/${base!}...${head!}`
      );

      return (response.files ?? []).map((f) => ({
        path: f.filename,
        status: f.status,
        additions: f.additions ?? 0,
        deletions: f.deletions ?? 0,
        patch: f.patch ?? null,
        // Original and modified content are fetched on demand by DiffViewer
        originalContent: '',
        modifiedContent: '',
      }));
    },
    enabled,
    staleTime: 30_000,
  });

  // Filter to specific file if filePath provided
  const diffs = filePath
    ? (data ?? []).filter((d) => d.path === filePath)
    : (data ?? []);

  return { diffs, isLoading };
}
