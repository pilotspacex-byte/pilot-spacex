'use client';

/**
 * WorkspaceKnowledgeGraph — full interactive knowledge graph for a workspace.
 *
 * Reuses the shared useGraphCanvas hook and GraphCanvasShell component.
 * Shows all workspace nodes with filter chips, depth is N/A (flat overview).
 */

import { useCallback, useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toast } from 'sonner';

import { GraphCanvasShell } from '@/features/issues/components/graph-canvas-shell';
import { useGraphCanvas } from '@/features/issues/hooks/use-graph-canvas';
import { useWorkspaceKnowledgeGraph } from '@/features/knowledge-graph/hooks/useWorkspaceKnowledgeGraph';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import { projectsApi } from '@/services/api/projects';
import type { FilterChip } from '@/features/issues/utils/graph-shared';
import type { GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface WorkspaceKnowledgeGraphProps {
  workspaceId: string;
}

const FILTER_CHIPS: FilterChip[] = [
  { label: 'Projects', nodeType: 'project' },
  { label: 'Issues', nodeType: 'issue' },
  { label: 'Notes', nodeType: 'note' },
  { label: 'Cycles', nodeType: 'cycle' },
  { label: 'PRs', nodeType: 'pull_request' },
  { label: 'Decisions', nodeType: 'decision' },
  { label: 'All', nodeType: 'all' },
];

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface CanvasProps {
  workspaceId: string;
  activeFilter: GraphNodeType | 'all';
  maxNodes: number;
  onNodeCountChange: (count: number) => void;
  onNavigate: (nodeType: string, entityId: string) => void;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

function WorkspaceGraphCanvas({
  workspaceId,
  activeFilter,
  maxNodes,
  onNodeCountChange,
  onNavigate,
  onRegenerate,
  isRegenerating,
}: CanvasProps) {
  const nodeTypes_ = useMemo<GraphNodeType[] | undefined>(
    () => (activeFilter === 'all' ? undefined : [activeFilter]),
    [activeFilter]
  );

  const { data, isLoading, isError, error, refetch } = useWorkspaceKnowledgeGraph(workspaceId, {
    nodeTypes: nodeTypes_,
    maxNodes,
  });

  // Report node count
  useEffect(() => {
    const count = data?.nodes.length ?? 0;
    onNodeCountChange(count);
  }, [data?.nodes.length, onNodeCountChange]);

  const canvas = useGraphCanvas({
    data,
    isLoading,
    isError,
    error,
    refetch,
    workspaceId,
    layoutConfig: {
      width: 1600,
      height: 1000,
      linkDistance: 240,
      chargeStrength: -600,
      collisionRadius: 90,
      edgeStrokeWidth: 1.5,
    },
    maxNodeCap: 500,
    expandDepth: 1,
    resetKey: activeFilter,
  });

  return (
    <GraphCanvasShell
      canvas={canvas}
      isLoading={isLoading}
      isError={isError}
      onRefetch={refetch}
      onNavigate={onNavigate}
      onRegenerate={onRegenerate}
      isRegenerating={isRegenerating}
      minZoom={0.2}
    />
  );
}

// ── Public component ────────────────────────────────────────────────────────

/** Map node type → URL segment for navigation. */
const NODE_TYPE_ROUTES: Record<string, string> = {
  issue: 'issues',
  note: 'notes',
  project: 'projects',
  cycle: 'projects', // cycles live under project pages
};

export function WorkspaceKnowledgeGraph({ workspaceId }: WorkspaceKnowledgeGraphProps) {
  const [activeFilter, setActiveFilter] = useState<GraphNodeType | 'all'>('all');
  const [nodeCount, setNodeCount] = useState(0);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const router = useRouter();
  const params = useParams<{ workspaceSlug: string }>();

  const handleNodeCountChange = useCallback((count: number) => {
    setNodeCount((prev) => (prev === count ? prev : count));
  }, []);

  const handleNavigate = useCallback(
    (nodeType: string, entityId: string) => {
      const route = NODE_TYPE_ROUTES[nodeType];
      if (route && params.workspaceSlug) {
        router.push(`/${params.workspaceSlug}/${route}/${entityId}`);
      }
    },
    [router, params.workspaceSlug]
  );

  const { refetch } = useWorkspaceKnowledgeGraph(workspaceId, {
    nodeTypes: activeFilter === 'all' ? undefined : [activeFilter],
  });

  const handleRegenerate = useCallback(async () => {
    setIsRegenerating(true);
    try {
      // Fetch all projects in the workspace
      const response = await projectsApi.list(workspaceId);
      const projectList = response?.items ?? [];
      if (projectList.length === 0) {
        toast.warning('No projects found. Create a project with issues first.');
        return;
      }
      // Trigger regeneration for each project
      let totalEnqueued = 0;
      for (const project of projectList) {
        const result = await knowledgeGraphApi.regenerateProjectGraph(workspaceId, project.id);
        totalEnqueued += result.enqueued;
      }
      toast.success(
        `Knowledge graph regeneration started (${totalEnqueued} jobs across ${projectList.length} projects)`
      );
      setTimeout(() => void refetch(), 5000);
    } catch {
      toast.error('Failed to start knowledge graph regeneration');
    } finally {
      setIsRegenerating(false);
    }
  }, [workspaceId, refetch]);

  return (
    <div className="flex flex-col h-full bg-background" data-testid="workspace-knowledge-graph">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-3 border-b border-border shrink-0 overflow-x-auto"
        style={{ height: 40, minHeight: 40 }}
      >
        <div
          className="flex items-center gap-1"
          role="toolbar"
          aria-label="Filter graph by node type"
        >
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.nodeType}
              type="button"
              aria-pressed={activeFilter === chip.nodeType}
              onClick={() => setActiveFilter(chip.nodeType)}
              className={[
                'rounded-full px-2.5 py-0.5 text-xs transition-colors shrink-0',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                activeFilter === chip.nodeType
                  ? 'bg-primary text-primary-foreground font-semibold ring-1 ring-primary/40'
                  : 'bg-muted text-muted-foreground font-medium hover:bg-muted/80',
              ].join(' ')}
            >
              {chip.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => void handleRegenerate()}
          disabled={isRegenerating}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Regenerate knowledge graph for all projects"
          title="Regenerate all projects"
        >
          <RefreshCw className={`size-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
        </button>

        {nodeCount > 0 && (
          <span className="ml-auto text-xs text-muted-foreground shrink-0 whitespace-nowrap">
            {nodeCount} nodes
          </span>
        )}
      </div>

      <ReactFlowProvider>
        <div className="flex flex-col flex-1 min-h-0">
          <WorkspaceGraphCanvas
            workspaceId={workspaceId}
            activeFilter={activeFilter}
            maxNodes={200}
            onNodeCountChange={handleNodeCountChange}
            onNavigate={handleNavigate}
            onRegenerate={handleRegenerate}
            isRegenerating={isRegenerating}
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
