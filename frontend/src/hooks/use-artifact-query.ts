/**
 * useArtifactQuery — TanStack Query wrapper that dispatches by artifact type.
 *
 * Phase 86: the drawer fetches artifact data on open. NOTE/ISSUE use their
 * existing workspace-scoped API clients; every other type gracefully falls
 * back to a placeholder descriptor so renderers can show "Preview unavailable"
 * rather than throwing.
 *
 * See `.planning/phases/86-peek-drawer-split-pane-lineage/86-UI-SPEC.md` §7.
 */
'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import type { ArtifactTokenKey } from '@/lib/artifact-tokens';
import { notesApi } from '@/services/api/notes';
import { issuesApi } from '@/services/api/issues';
import { artifactsApi } from '@/services/api/artifacts';
import { useWorkspaceStore } from '@/stores';
import type { Note } from '@/types/note';
import type { Issue } from '@/types/issue';

export interface ArtifactLineage {
  sourceChatId?: string;
  sourceMessageId?: string;
  firstSeenAt?: string;
}

export interface ArtifactData {
  type: ArtifactTokenKey;
  id: string;
  /** Filled when a dedicated API client responded with a native payload. */
  note?: Note;
  issue?: Issue;
  /** Generic content for markdown/code/html renderers. */
  content?: string;
  language?: string;
  url?: string;
  title?: string;
  /** Set when no API client exists yet for this type. */
  placeholder?: boolean;
  lineage?: ArtifactLineage | null;
}

const STALE_TIME_MS = 30_000;

export function useArtifactQuery(
  type: ArtifactTokenKey | null,
  id: string | null,
): UseQueryResult<ArtifactData, Error> {
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspaceId ?? '';

  return useQuery<ArtifactData, Error>({
    queryKey: ['artifact', type, id, workspaceId],
    enabled: Boolean(type && id),
    staleTime: STALE_TIME_MS,
    queryFn: async (): Promise<ArtifactData> => {
      if (!type || !id) {
        // `enabled` guards this — type narrowing for TS.
        throw new Error('Artifact query invoked without type or id');
      }
      if (type === 'NOTE') {
        if (!workspaceId) return { type, id, placeholder: true };
        const note = await notesApi.get(workspaceId, id);
        return {
          type,
          id,
          note,
          title: note.title,
          lineage: null,
        };
      }
      if (type === 'ISSUE') {
        if (!workspaceId) return { type, id, placeholder: true };
        const issue = await issuesApi.get(workspaceId, id);
        return {
          type,
          id,
          issue,
          title: issue.name ?? issue.title ?? issue.identifier,
          lineage: null,
        };
      }
      // Phase 87.1 Plan 04 — fetch MD/HTML content via workspace-scoped
      // signed URL endpoint. Re-fetched on demand (signed URLs are short-lived,
      // so we never cache the URL itself — only the resolved content).
      if (type === 'MD' || type === 'HTML') {
        if (!workspaceId) return { type, id, placeholder: true };
        const { url } = await artifactsApi.getSignedUrlByWorkspace(workspaceId, id);
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(
            `Failed to fetch artifact content (${res.status} ${res.statusText})`,
          );
        }
        const content = await res.text();
        return {
          type,
          id,
          content,
          language: type === 'MD' ? 'markdown' : 'html',
        };
      }
      // Other tier-2 file artifacts: no generic getById yet — placeholder.
      return { type, id, placeholder: true };
    },
  });
}
