import { useState, useCallback } from 'react';

export interface RecentEntity {
  id: string;
  type: 'Note' | 'Issue' | 'Project';
  title: string;
}

const STORAGE_KEY = (workspaceId: string) => `pilot-recent-entities-${workspaceId}`;
const MAX_RECENT = 5;

function readFromStorage(workspaceId: string): RecentEntity[] {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY(workspaceId));
    return stored ? (JSON.parse(stored) as RecentEntity[]) : [];
  } catch {
    return [];
  }
}

export function useRecentEntities(workspaceId: string) {
  // Track which workspaceId the current state belongs to.
  // When workspaceId changes, re-derive state from sessionStorage without useEffect.
  const [trackedWorkspaceId, setTrackedWorkspaceId] = useState(workspaceId);
  const [recentEntities, setRecentEntities] = useState<RecentEntity[]>(() =>
    readFromStorage(workspaceId)
  );

  // Synchronise state inline when the workspace changes (avoids the
  // react-hooks/no-direct-set-state-in-use-effect lint error while still
  // keeping state accurate after a workspace switch).
  if (trackedWorkspaceId !== workspaceId) {
    setTrackedWorkspaceId(workspaceId);
    setRecentEntities(readFromStorage(workspaceId));
  }

  const addEntity = useCallback(
    (entity: RecentEntity) => {
      setRecentEntities((prev) => {
        const deduped = prev.filter((e) => e.id !== entity.id);
        const next = [entity, ...deduped].slice(0, MAX_RECENT);
        try {
          sessionStorage.setItem(STORAGE_KEY(workspaceId), JSON.stringify(next));
        } catch {
          // sessionStorage full — silently skip persistence
        }
        return next;
      });
    },
    [workspaceId]
  );

  return { recentEntities, addEntity };
}
