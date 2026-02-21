'use client';

/**
 * IssueNoteContext - React context for passing issue data to PropertyBlockView.
 *
 * Avoids serializing issue data into TipTap node attributes.
 * The PropertyBlockView NodeView reads from this context to render
 * inline property chips and dispatch updates.
 */
import { createContext, useContext } from 'react';
import type { Issue, UpdateIssueData, IssueState, LabelBrief, Cycle, UserBrief } from '@/types';

export interface IssueNoteContextValue {
  /** Current issue data */
  issue: Issue;
  /** Workspace members mapped to UserBrief for AssigneeSelector */
  members: UserBrief[];
  /** Available labels for LabelSelector */
  labels: LabelBrief[];
  /** Available cycles for CycleSelector */
  cycles: Cycle[];
  /** Dispatch a partial update to the issue */
  onUpdate: (data: UpdateIssueData) => Promise<unknown>;
  /** Update issue state via dedicated state endpoint (accepts state name, not UUID) */
  onUpdateState: (state: IssueState) => Promise<unknown>;
  /** Whether the issue is read-only */
  disabled?: boolean;
}

export const IssueNoteContext = createContext<IssueNoteContextValue | null>(null);

export function useIssueNoteContext(): IssueNoteContextValue {
  const ctx = useContext(IssueNoteContext);
  if (!ctx) {
    throw new Error('useIssueNoteContext must be used within IssueNoteContext.Provider');
  }
  return ctx;
}
