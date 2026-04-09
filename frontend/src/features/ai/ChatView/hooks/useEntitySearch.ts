import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { notesApi } from '@/services/api/notes';
import { issuesApi } from '@/services/api/issues';
import { projectsApi } from '@/services/api/projects';

interface UseEntitySearchParams {
  query: string;
  workspaceId: string;
}

export function useEntitySearch({ query, workspaceId }: UseEntitySearchParams) {
  // 150ms debounce via setTimeout ref
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 150);
    return () => clearTimeout(t);
  }, [query]);

  const enabled = !!workspaceId;

  const notesQuery = useQuery({
    queryKey: ['entity-search-notes', workspaceId, debouncedQuery],
    queryFn: () => notesApi.list(workspaceId, { search: debouncedQuery }, 1, 20),
    staleTime: 30_000,
    enabled,
  });

  const issuesQuery = useQuery({
    queryKey: ['entity-search-issues', workspaceId, debouncedQuery],
    queryFn: () => issuesApi.list(workspaceId, { search: debouncedQuery }, 1, 20),
    staleTime: 30_000,
    enabled,
  });

  const projectsQuery = useQuery({
    queryKey: ['entity-search-projects', workspaceId],
    queryFn: () => projectsApi.list(workspaceId),
    staleTime: 60_000,
    enabled,
  });

  // Client-side filter for projects (no server-side search)
  const filteredProjects = useMemo(() => {
    const items = projectsQuery.data?.items ?? [];
    if (!debouncedQuery) return items;
    return items.filter((p) =>
      p.name.toLowerCase().includes(debouncedQuery.toLowerCase())
    );
  }, [projectsQuery.data, debouncedQuery]);

  return {
    notes: notesQuery.data?.items ?? [],
    issues: issuesQuery.data?.items ?? [],
    projects: filteredProjects,
    isLoading: notesQuery.isFetching || issuesQuery.isFetching || projectsQuery.isFetching,
  };
}
