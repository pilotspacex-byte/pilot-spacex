import { useQuery } from '@tanstack/react-query';
import { getFileContent } from '@/services/api/git-proxy';
import type { GitRepo } from '@/features/source-control/types';

/**
 * Map file extensions to Monaco language identifiers.
 */
function getLanguageFromPath(filePath: string): string {
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

/**
 * Hook to fetch original + modified file content for diff viewing.
 *
 * Fetches base version (from defaultBranch) and current version (from branch).
 * For added files, original is empty. For deleted files, modified is empty.
 */
export function useFileDiff(
  repo: GitRepo | null,
  filePath: string | null,
  branch: string,
  defaultBranch: string,
  fileStatus?: 'modified' | 'added' | 'deleted' | 'renamed'
) {
  const enabled = !!repo && !!filePath;

  const originalQuery = useQuery<string>({
    queryKey: ['git-file-content', repo?.owner, repo?.repo, filePath, defaultBranch, 'original'],
    queryFn: async () => {
      if (fileStatus === 'added') return '';
      const response = await getFileContent(
        repo!.owner,
        repo!.repo,
        repo!.integrationId,
        filePath!,
        defaultBranch
      );
      return response.content;
    },
    enabled,
    staleTime: 30_000,
  });

  const modifiedQuery = useQuery<string>({
    queryKey: ['git-file-content', repo?.owner, repo?.repo, filePath, branch, 'modified'],
    queryFn: async () => {
      if (fileStatus === 'deleted') return '';
      const response = await getFileContent(
        repo!.owner,
        repo!.repo,
        repo!.integrationId,
        filePath!,
        branch
      );
      return response.content;
    },
    enabled,
    staleTime: 30_000,
  });

  return {
    original: originalQuery.data ?? '',
    modified: modifiedQuery.data ?? '',
    language: filePath ? getLanguageFromPath(filePath) : 'plaintext',
    isLoading: originalQuery.isLoading || modifiedQuery.isLoading,
  };
}
