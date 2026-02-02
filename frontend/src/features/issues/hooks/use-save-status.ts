import { useCallback } from 'react';

import { useIssueStore } from '@/stores';

type SaveStatusState = 'idle' | 'saving' | 'saved' | 'error';

/**
 * Hook to wire per-field save status from IssueStore.
 *
 * Returns the current status for the given field and a `wrapMutation` helper
 * that sets status to 'saving' before the async call, then 'saved' or 'error'
 * depending on the outcome. The 'saved' state auto-clears to 'idle' after 2 s
 * (handled by IssueStore.setSaveStatus).
 *
 * Usage:
 * ```tsx
 * const { status, wrapMutation } = useSaveStatus('title');
 *
 * const handleBlur = () => {
 *   wrapMutation(() => updateIssue(workspaceId, issueId, { title: value }));
 * };
 * ```
 */
export function useSaveStatus(fieldName: string) {
  const issueStore = useIssueStore();

  const status: SaveStatusState = issueStore.getSaveStatus(fieldName);

  const wrapMutation = useCallback(
    async <T>(mutationFn: () => Promise<T>): Promise<T> => {
      issueStore.setSaveStatus(fieldName, 'saving');
      try {
        const result = await mutationFn();
        issueStore.setSaveStatus(fieldName, 'saved');
        return result;
      } catch (error) {
        issueStore.setSaveStatus(fieldName, 'error');
        throw error;
      }
    },
    [issueStore, fieldName]
  );

  return { status, wrapMutation } as const;
}
