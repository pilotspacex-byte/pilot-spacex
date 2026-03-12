import { useCallback } from 'react';

import type { IssueState, IssuePriority, UserBrief, UpdateIssueData } from '@/types';
import { useSaveStatus } from './use-save-status';
import { STATE_GROUP_MAP } from '@/features/issues/components/property-block-constants';

export interface UsePropertyMutationsOptions {
  issueState: { name: string; group: string };
  onUpdate: (data: UpdateIssueData) => Promise<unknown>;
  onUpdateState: (state: IssueState) => Promise<unknown>;
}

export function usePropertyMutations({
  issueState,
  onUpdate,
  onUpdateState,
}: UsePropertyMutationsOptions) {
  const { wrapMutation: wrapState } = useSaveStatus('state');
  const handleStateChange = useCallback(
    (state: IssueState) => {
      const matched = STATE_GROUP_MAP[issueState.group] === state ? issueState : null;
      if (matched) return;
      const pending = onUpdateState(state);
      wrapState(() => pending).catch(() => {});
    },
    [issueState, wrapState, onUpdateState]
  );

  const { wrapMutation: wrapPriority } = useSaveStatus('priority');
  const handlePriorityChange = useCallback(
    (priority: IssuePriority) => {
      wrapPriority(() => onUpdate({ priority })).catch(() => {});
    },
    [wrapPriority, onUpdate]
  );

  const { wrapMutation: wrapAssignee } = useSaveStatus('assignee');
  const handleAssigneeChange = useCallback(
    (user: UserBrief | null) => {
      if (user) {
        wrapAssignee(() => onUpdate({ assigneeId: user.id })).catch(() => {});
      } else {
        wrapAssignee(() => onUpdate({ clearAssignee: true })).catch(() => {});
      }
    },
    [wrapAssignee, onUpdate]
  );

  const { wrapMutation: wrapDueDate } = useSaveStatus('targetDate');
  const handleDueDateChange = useCallback(
    (d: Date | undefined) => {
      if (d) {
        wrapDueDate(() => onUpdate({ targetDate: d.toISOString().split('T')[0] })).catch(() => {});
      } else {
        wrapDueDate(() => onUpdate({ clearTargetDate: true })).catch(() => {});
      }
    },
    [wrapDueDate, onUpdate]
  );

  return {
    handleStateChange,
    handlePriorityChange,
    handleAssigneeChange,
    handleDueDateChange,
  } as const;
}
