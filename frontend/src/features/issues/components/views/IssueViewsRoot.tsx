'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores';
import { IssueToolbar } from './IssueToolbar';
import { BoardView } from './board/BoardView';
import { ListView } from './list/ListView';
import { TableView } from './table/TableView';
import type { Issue, IssueState, IssuePriority } from '@/types';

interface IssueViewsRootProps {
  workspaceSlug: string;
  projectId?: string;
  className?: string;
}

/**
 * IssueViewsRoot — shared orchestrator for Board, List, and Table views.
 * Used by both workspace-level /issues and project-level /projects/[id]/issues.
 */
export const IssueViewsRoot = observer(function IssueViewsRoot({
  workspaceSlug,
  projectId,
  className,
}: IssueViewsRootProps) {
  const router = useRouter();
  const { issueStore, issueViewStore, workspaceStore } = useStore();

  const workspace = workspaceStore.currentWorkspace;
  const workspaceId = workspace?.id ?? workspaceSlug;
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';

  // Hydrate view store from localStorage on mount
  React.useEffect(() => {
    issueViewStore.hydrate();
  }, [issueViewStore]);

  // Load issues
  React.useEffect(() => {
    if (workspaceId) {
      issueStore.loadIssues(workspaceId, projectId);
    }
  }, [workspaceId, projectId, issueStore]);

  // Auto-switch Table → List on mobile
  React.useEffect(() => {
    const mql = window.matchMedia('(max-width: 767px)');
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      if (e.matches && issueViewStore.viewMode === 'table') {
        issueViewStore.setViewMode('list');
      }
    };
    handler(mql);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [issueViewStore]);

  // Pre-apply project filter when projectId is provided
  React.useEffect(() => {
    if (projectId) {
      issueViewStore.setFilterProjectIds([projectId]);
    }
    return () => {
      if (projectId) {
        issueViewStore.setFilterProjectIds([]);
      }
    };
  }, [projectId, issueViewStore]);

  // Client-side filtering
  const filteredIssues = React.useMemo(() => {
    let result = issueStore.issuesList;

    if (issueViewStore.filterStates.length > 0) {
      result = result.filter((i) => {
        const stateName = i.state?.name?.toLowerCase().replace(/\s+/g, '_') ?? 'backlog';
        return issueViewStore.filterStates.includes(stateName);
      });
    }
    if (issueViewStore.filterPriorities.length > 0) {
      result = result.filter((i) => issueViewStore.filterPriorities.includes(i.priority ?? 'none'));
    }
    if (issueViewStore.filterTypes.length > 0) {
      result = result.filter((i) => issueViewStore.filterTypes.includes(i.type ?? 'task'));
    }
    if (issueViewStore.filterAssigneeIds.length > 0) {
      result = result.filter(
        (i) => i.assigneeId && issueViewStore.filterAssigneeIds.includes(i.assigneeId)
      );
    }
    if (issueViewStore.filterLabelIds.length > 0) {
      result = result.filter((i) =>
        i.labels.some((l) => issueViewStore.filterLabelIds.includes(l.id))
      );
    }
    if (issueViewStore.filterProjectIds.length > 0) {
      result = result.filter((i) => issueViewStore.filterProjectIds.includes(i.projectId));
    }

    return result;
  }, [
    issueStore.issuesList,
    issueViewStore.filterStates,
    issueViewStore.filterPriorities,
    issueViewStore.filterTypes,
    issueViewStore.filterAssigneeIds,
    issueViewStore.filterLabelIds,
    issueViewStore.filterProjectIds,
  ]);

  // Handlers
  const handleIssueClick = (issue: Issue) => {
    router.push(`/${workspaceSlug}/issues/${issue.id}`);
  };

  const handleIssueDrop = async (issueId: string, newState: IssueState) => {
    if (workspaceId) {
      await issueStore.updateIssueState(workspaceId, issueId, newState);
    }
  };

  const handleCreateIssue = async (_state: IssueState, name: string) => {
    if (!workspaceId) return;
    if (!projectId) {
      toast.error('Select a project first', {
        description: 'New issues must belong to a project. Open a project to add issues.',
      });
      return;
    }
    const result = await issueStore.createIssue(workspaceId, { name, projectId });
    if (!result) {
      toast.error('Failed to create issue', {
        description: issueStore.error ?? 'Please try again.',
      });
    }
  };

  const handleStateChange = (issueId: string, state: IssueState) => {
    if (workspaceId) {
      issueStore.updateIssueState(workspaceId, issueId, state);
    }
  };

  const handleBulkStateChange = (issueIds: string[], state: IssueState) => {
    if (workspaceId) {
      for (const id of issueIds) {
        issueStore.updateIssueState(workspaceId, id, state);
      }
      issueViewStore.clearSelection();
    }
  };

  const handleBulkPriorityChange = (issueIds: string[], priority: IssuePriority) => {
    if (workspaceId) {
      for (const id of issueIds) {
        issueStore.updateIssue(workspaceId, id, { priority });
      }
      issueViewStore.clearSelection();
    }
  };

  const viewMode = issueViewStore.viewMode;

  return (
    <div className={cn('flex h-full flex-col', className)}>
      <IssueToolbar hideProjectFilter={!!projectId} />

      <div className="flex-1 overflow-hidden">
        {viewMode === 'board' && (
          <BoardView
            issues={filteredIssues}
            isLoading={issueStore.isLoading}
            onIssueClick={handleIssueClick}
            onIssueDrop={handleIssueDrop}
            onCreateIssue={canCreateContent ? handleCreateIssue : undefined}
          />
        )}

        {viewMode === 'list' && (
          <ListView
            issues={filteredIssues}
            isLoading={issueStore.isLoading}
            onIssueClick={handleIssueClick}
            onStateChange={handleStateChange}
            onBulkStateChange={handleBulkStateChange}
            onBulkPriorityChange={handleBulkPriorityChange}
          />
        )}

        {viewMode === 'table' && (
          <TableView
            issues={filteredIssues}
            isLoading={issueStore.isLoading}
            onIssueClick={handleIssueClick}
          />
        )}
      </div>
    </div>
  );
});
