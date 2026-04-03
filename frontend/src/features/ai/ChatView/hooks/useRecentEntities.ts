import { useState, useCallback, useEffect } from 'react';

export interface RecentEntity {
  id: string;
  type: 'Note' | 'Issue' | 'Project';
  title: string;
}

const STORAGE_KEY = (workspaceId: string) => `pilot-recent-entities-${workspaceId}`;
const MAX_RECENT = 5;

export function useRecentEntities(workspaceId: string) {
  const [recentEntities, setRecentEntities] = useState<RecentEntity[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY(workspaceId));
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // Re-read from sessionStorage whenever workspaceId changes (e.g., workspace switch
  // or when the component mounts with an empty placeholder ID that later resolves).
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY(workspaceId));
      setRecentEntities(stored ? JSON.parse(stored) : []);
    } catch {
      setRecentEntities([]);
    }
  }, [workspaceId]);

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
