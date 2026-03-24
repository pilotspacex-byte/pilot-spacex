import { useCallback } from 'react';

const STORAGE_KEY = 'pilot-space:recent-actions';
const MAX_RECENT = 5;

/**
 * Hook for managing recently used command palette actions.
 * Persists to localStorage with a cap of 5 items.
 */
export function useRecentActions() {
  const getRecent = useCallback((): string[] => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      return JSON.parse(raw) as string[];
    } catch {
      return [];
    }
  }, []);

  const addRecent = useCallback(
    (actionId: string) => {
      const current = getRecent();
      // Remove duplicate if exists, then prepend
      const filtered = current.filter((id) => id !== actionId);
      const updated = [actionId, ...filtered].slice(0, MAX_RECENT);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    },
    [getRecent]
  );

  return { addRecent, getRecent };
}
