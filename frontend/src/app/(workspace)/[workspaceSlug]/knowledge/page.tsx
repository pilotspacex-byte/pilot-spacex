'use client';

import { useParams } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { Network } from 'lucide-react';
import { WorkspaceKnowledgeGraph } from '@/features/knowledge-graph/components/workspace-knowledge-graph';
import { useWorkspaceStore } from '@/stores';

function WorkspaceKnowledgePage() {
  const params = useParams<{ workspaceSlug: string }>();
  const workspaceStore = useWorkspaceStore();
  const workspaceSlug = params.workspaceSlug;

  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ?? workspaceStore.currentWorkspace?.id;

  if (!workspaceId) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 text-center">
        <Network className="h-10 w-10 text-muted-foreground mb-3" />
        <h3 className="text-lg font-medium">Loading workspace…</h3>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 border-b border-border px-6 py-4 shrink-0">
        <Network className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Knowledge Graph</h1>
        <span className="text-sm text-muted-foreground">{workspaceSlug}</span>
      </div>

      <div className="flex-1 min-h-0">
        <WorkspaceKnowledgeGraph workspaceId={workspaceId} />
      </div>
    </div>
  );
}

export default observer(WorkspaceKnowledgePage);
