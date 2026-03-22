'use client';

/**
 * ProjectKnowledgeGraph — full interactive knowledge graph for a project.
 *
 * Layout:
 *   1. Toolbar (40px): filter chips, depth slider, node count
 *   2. ReactFlow canvas (flex-1): interactive, minimap, zoom 0.3–3x
 *   3. Node detail panel (<=200px): shown when a node is selected
 *
 * State: local useState only (no MobX, NOT observer).
 */

import { useCallback, useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toast } from 'sonner';

import { GraphCanvasShell } from '@/features/issues/components/graph-canvas-shell';
import { useGraphCanvas } from '@/features/issues/hooks/use-graph-canvas';
import { useProjectKnowledgeGraph } from '@/features/projects/hooks/useProjectKnowledgeGraph';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { FilterChip } from '@/features/issues/utils/graph-shared';
import type { GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProjectKnowledgeGraphProps {
  workspaceId: string;
  projectId: string;
}

const FILTER_CHIPS: FilterChip[] = [
  { label: 'Issues', nodeType: 'issue' },
  { label: 'Notes', nodeType: 'note' },
  { label: 'Cycles', nodeType: 'cycle' },
  { label: 'PRs', nodeType: 'pull_request' },
  { label: 'Commits', nodeType: 'commit' },
  { label: 'Code', nodeType: 'code_reference' },
  { label: 'All', nodeType: 'all' },
];

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface ProjectGraphCanvasProps {
  workspaceId: string;
  projectId: string;
  depth: number;
  activeFilter: GraphNodeType | 'all';
  onNodeCountChange: (count: number) => void;
  onRegenerate: () => void;
  isRegenerating: boolean;
  onNavigate: (nodeType: string, entityId: string) => void;
}

function ProjectGraphCanvas({
  workspaceId,
  projectId,
  depth,
  activeFilter,
  onNodeCountChange,
  onRegenerate,
  isRegenerating,
  onNavigate,
}: ProjectGraphCanvasProps) {
  const nodeTypes_ = useMemo<GraphNodeType[] | undefined>(
    () => (activeFilter === 'all' ? undefined : [activeFilter]),
    [activeFilter]
  );

  const { data, isLoading, isError, error, refetch } = useProjectKnowledgeGraph(
    workspaceId,
    projectId,
    {
      depth,
      nodeTypes: nodeTypes_,
    }
  );

  // Report node count to parent for toolbar display
  useEffect(() => {
    const count = data?.nodes.length ?? 0;
    onNodeCountChange(count);
  }, [data?.nodes.length, onNodeCountChange]);

  const resetKey = `${activeFilter}-${depth}`;

  const canvas = useGraphCanvas({
    data,
    isLoading,
    isError,
    error,
    refetch,
    workspaceId,
    layoutConfig: {
      width: 1200,
      height: 800,
      linkDistance: 200,
      chargeStrength: -450,
      collisionRadius: 85,
      edgeStrokeWidth: 1.5,
    },
    maxNodeCap: 200,
    expandDepth: depth,
    resetKey,
  });

  return (
    <GraphCanvasShell
      canvas={canvas}
      isLoading={isLoading}
      isError={isError}
      onRefetch={refetch}
      onRegenerate={onRegenerate}
      isRegenerating={isRegenerating}
      onNavigate={onNavigate}
    />
  );
}

// ── Public component ────────────────────────────────────────────────────────

const NODE_TYPE_ROUTES: Record<string, string> = {
  issue: 'issues',
  note: 'notes',
  project: 'projects',
  cycle: 'projects',
};

export function ProjectKnowledgeGraph({ workspaceId, projectId }: ProjectKnowledgeGraphProps) {
  const [depth, setDepth] = useState(2);
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

  const { refetch } = useProjectKnowledgeGraph(workspaceId, projectId, {
    depth,
    nodeTypes: activeFilter === 'all' ? undefined : [activeFilter],
  });

  const handleRegenerate = useCallback(async () => {
    setIsRegenerating(true);
    try {
      const result = await knowledgeGraphApi.regenerateProjectGraph(workspaceId, projectId);
      toast.success(`Knowledge graph regeneration started (${result.enqueued} jobs enqueued)`);
      setTimeout(() => void refetch(), 3000);
    } catch {
      toast.error('Failed to start knowledge graph regeneration');
    } finally {
      setIsRegenerating(false);
    }
  }, [workspaceId, projectId, refetch]);

  return (
    <div className="flex flex-col h-full bg-background" data-testid="project-knowledge-graph">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-3 border-b border-border shrink-0 overflow-x-auto"
        style={{ height: 40, minHeight: 40 }}
      >
        {/* Filter chips */}
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

        <div className="w-px h-5 bg-border shrink-0" aria-hidden="true" />

        {/* Depth slider */}
        <div className="flex items-center gap-1.5 shrink-0">
          <label
            htmlFor="project-graph-depth"
            className="text-xs text-muted-foreground whitespace-nowrap"
          >
            Depth {depth}
          </label>
          <input
            id="project-graph-depth"
            type="range"
            min={1}
            max={3}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-16 h-1 accent-primary cursor-pointer"
            aria-label="Graph depth"
          />
        </div>

        <button
          type="button"
          onClick={() => void handleRegenerate()}
          disabled={isRegenerating}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Regenerate knowledge graph"
          title="Regenerate knowledge graph"
        >
          <RefreshCw className={`size-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
        </button>

        {nodeCount > 0 && (
          <span className="ml-auto text-xs text-muted-foreground shrink-0 whitespace-nowrap">
            {nodeCount} nodes
          </span>
        )}
      </div>

      {/* Graph canvas + detail panel via ReactFlowProvider */}
      <ReactFlowProvider>
        <div className="flex flex-col flex-1 min-h-0">
          <ProjectGraphCanvas
            workspaceId={workspaceId}
            projectId={projectId}
            depth={depth}
            activeFilter={activeFilter}
            onNodeCountChange={handleNodeCountChange}
            onRegenerate={handleRegenerate}
            isRegenerating={isRegenerating}
            onNavigate={handleNavigate}
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
