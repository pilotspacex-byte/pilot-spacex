/**
 * SkillEditorPanel — Split-screen editor panel (LEFT side) for skill preview.
 * Shows SKILL.md text view or graph data view with a toggle.
 *
 * @module features/ai/ChatView/SkillEditor/SkillEditorPanel
 */
'use client';

import { Suspense, useCallback, useState } from 'react';
import dynamic from 'next/dynamic';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { ChevronLeft, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useStore } from '@/stores/RootStore';
import { useSkillGraphMutation } from '@/features/skills/hooks/use-skill-graph-queries';
import { SkillMarkdownPreview } from './SkillMarkdownPreview';

const GraphWorkflowCanvas = dynamic(
  () =>
    import('@/features/skills/components/graph-workflow-canvas').then(
      (mod) => mod.GraphWorkflowCanvas,
    ),
  { ssr: false },
);

type ViewMode = 'text' | 'graph';

export const SkillEditorPanel = observer(function SkillEditorPanel() {
  const { aiStore, workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const skillStore = aiStore.pilotSpace.skillGeneratorStore;
  const draft = skillStore.currentDraft;
  const [viewMode, setViewMode] = useState<ViewMode>('text');

  const graphMutation = useSkillGraphMutation(workspaceId);

  const handleGraphSave = useCallback(
    (data: { nodes: unknown[]; edges: unknown[] }) => {
      if (!draft?.sessionId) return;
      graphMutation.mutate(
        {
          templateId: draft.sessionId,
          data: {
            graph_json: { nodes: data.nodes, edges: data.edges },
            node_count: data.nodes.length,
            edge_count: data.edges.length,
          },
        },
        {
          onSuccess: () => toast.success('Graph saved'),
          onError: () => toast.error('Failed to save graph'),
        },
      );
    },
    [draft?.sessionId, graphMutation],
  );

  if (!draft || !skillStore.isPreviewVisible) return null;

  // Graph stats available via draft.graphData?.nodes/edges

  return (
    <div
      data-testid="skill-editor-panel"
      className="w-[480px] min-w-[380px] border-r flex flex-col h-full bg-background"
    >
      {/* Header */}
      <div className="shrink-0 flex items-center gap-2 px-4 py-3 border-b">
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 shrink-0"
          onClick={() => skillStore.dismissPreview()}
          aria-label="Collapse editor panel"
          data-testid="collapse-editor-btn"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <h2 className="text-sm font-semibold truncate flex-1">{draft.name}</h2>

        {/* View mode toggle */}
        <div className="flex items-center rounded-md border bg-muted p-0.5 gap-0.5">
          <button
            type="button"
            onClick={() => setViewMode('text')}
            className={cn(
              'px-2.5 py-1 text-xs font-medium rounded-sm transition-colors',
              viewMode === 'text'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
            data-testid="toggle-text-view"
          >
            Text
          </button>
          <button
            type="button"
            onClick={() => setViewMode('graph')}
            className={cn(
              'px-2.5 py-1 text-xs font-medium rounded-sm transition-colors',
              viewMode === 'graph'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
            data-testid="toggle-graph-view"
          >
            Graph
          </button>
        </div>
      </div>

      {/* Content */}
      {viewMode === 'text' ? (
        <div className="flex-1 overflow-auto min-h-0 p-4">
          <SkillMarkdownPreview content={draft.skillContent} />
        </div>
      ) : (
        <div className="flex-1 flex min-h-0">
          {/* Graph canvas (left) */}
          <div className="flex-1 min-h-0">
            <Suspense
              fallback={
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              }
            >
              <GraphWorkflowCanvas
                initialNodes={draft.graphData?.nodes as never[] | undefined}
                initialEdges={draft.graphData?.edges as never[] | undefined}
                onSave={handleGraphSave}
              />
            </Suspense>
          </div>
          {/* SKILL.md preview (right) */}
          <div className="w-[320px] shrink-0 border-l overflow-auto p-4">
            <SkillMarkdownPreview content={draft.skillContent} />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="shrink-0 flex items-center gap-2 px-4 py-3 border-t">
        <Badge variant="secondary" className="text-xs">
          {draft.category}
        </Badge>
        {draft.examplePrompts.length > 0 && (
          <Badge variant="outline" className="text-xs">
            {draft.examplePrompts.length} example{draft.examplePrompts.length !== 1 ? 's' : ''}
          </Badge>
        )}
        {draft.contextRequirements.length > 0 && (
          <Badge variant="outline" className="text-xs">
            {draft.contextRequirements.length} ctx req{draft.contextRequirements.length !== 1 ? 's' : ''}
          </Badge>
        )}
        <div className="flex-1" />
        <Button
          size="sm"
          onClick={() => skillStore.openSaveDialog()}
          className="gap-1.5"
          data-testid="editor-save-btn"
        >
          <Save className="h-3.5 w-3.5" aria-hidden="true" />
          Save
        </Button>
      </div>
    </div>
  );
});

SkillEditorPanel.displayName = 'SkillEditorPanel';
