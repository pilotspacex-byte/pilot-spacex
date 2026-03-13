'use client';

/**
 * ProjectKnowledgeGraph — full interactive knowledge graph for a project.
 *
 * Layout:
 *   1. Toolbar (40px): filter chips, depth slider, node count
 *   2. ReactFlow canvas (flex-1): interactive, minimap, zoom 0.3–3x
 *   3. Node detail panel (≤200px): shown when a node is selected
 *
 * State: local useState only (no MobX, NOT observer).
 */

import { useCallback, useEffect, startTransition, useState, useMemo } from 'react';
import { X } from 'lucide-react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';

import { GraphEmptyState } from '@/features/issues/components/graph-empty-state';
import { nodeTypes, type GraphNodeData } from '@/features/issues/components/graph-node-renderer';
import { ErrorBoundary } from '@/components/error-boundary';
import { computeForceLayout } from '@/features/issues/utils/graph-styles';
import { useProjectKnowledgeGraph } from '@/features/projects/hooks/useProjectKnowledgeGraph';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeDTO, GraphEdgeDTO, GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProjectKnowledgeGraphProps {
  workspaceId: string;
  projectId: string;
}

interface FilterChip {
  label: string;
  nodeType: GraphNodeType | 'all';
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

const minimapNodeColor = (n: Node) => {
  const d = n.data as GraphNodeData | undefined;
  if (d?.isCurrent) return '#2563eb';
  return '#94a3b8';
};

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface ProjectGraphCanvasProps {
  workspaceId: string;
  projectId: string;
  depth: number;
  activeFilter: GraphNodeType | 'all';
  onNodeCountChange: (count: number) => void;
}

function ProjectGraphCanvas({
  workspaceId,
  projectId,
  depth,
  activeFilter,
  onNodeCountChange,
}: ProjectGraphCanvasProps) {
  const { fitView } = useReactFlow();

  const [selectedNode, setSelectedNode] = useState<GraphNodeDTO | null>(null);
  const [extraNodes, setExtraNodes] = useState<GraphNodeDTO[]>([]);
  const [extraEdges, setExtraEdges] = useState<GraphEdgeDTO[]>([]);
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  // Reset expanded nodes when filter or depth changes
  useEffect(() => {
    setExtraNodes([]);
    setExtraEdges([]);
    setSelectedNode(null);
  }, [activeFilter, depth]);

  const nodeTypes_ = useMemo<GraphNodeType[] | undefined>(
    () => (activeFilter === 'all' ? undefined : [activeFilter]),
    [activeFilter]
  );

  const { data, isLoading, isError, refetch } = useProjectKnowledgeGraph(workspaceId, projectId, {
    depth,
    nodeTypes: nodeTypes_,
  });

  // Report node count to parent for toolbar display (guard against no-op updates)
  useEffect(() => {
    const count = data?.nodes.length ?? 0;
    onNodeCountChange(count);
  }, [data?.nodes.length, onNodeCountChange]);

  // Merge base + expanded neighbor nodes
  const mergedNodes = useMemo(() => {
    if (!data) return [];
    const baseIds = new Set(data.nodes.map((n) => n.id));
    return [...data.nodes, ...extraNodes.filter((n) => !baseIds.has(n.id))];
  }, [data, extraNodes]);

  const mergedEdges = useMemo(() => {
    if (!data) return [];
    const baseIds = new Set(data.edges.map((e) => e.id));
    return [...data.edges, ...extraEdges.filter((e) => !baseIds.has(e.id))];
  }, [data, extraEdges]);

  const effectiveCenterNodeId = useMemo(() => {
    if (!data) return '';
    const center = data.centerNodeId;
    if (!center) return data.nodes[0]?.id ?? '';
    const exists = data.nodes.some((n) => n.id === center);
    return exists ? center : (data.nodes[0]?.id ?? '');
  }, [data]);

  // Layout computation via useEffect + startTransition
  useEffect(() => {
    startTransition(() => {
      if (mergedNodes.length === 0) {
        setFlowNodes([]);
        setFlowEdges([]);
        return;
      }
      const [nodes, edges] = computeForceLayout(mergedNodes, mergedEdges, {
        width: 1000,
        height: 600,
        centerNodeId: effectiveCenterNodeId,
        linkDistance: 100,
        chargeStrength: -150,
        collisionRadius: 40,
        edgeStrokeWidth: 1.5,
      });
      setFlowNodes(nodes);
      setFlowEdges(edges);
    });
  }, [mergedNodes, mergedEdges, effectiveCenterNodeId]);

  // Auto-fit when data loads
  useEffect(() => {
    if (flowNodes.length > 0) {
      requestAnimationFrame(() => {
        void fitView({ padding: 0.15, duration: 400 });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveCenterNodeId]);

  const handleNodeDoubleClick = useCallback(
    async (nodeId: string) => {
      const remaining = 200 - mergedNodes.length;
      if (remaining <= 0) {
        toast.warning('Graph limit reached (200 nodes). Clear filters to reset the view.');
        return;
      }
      try {
        const neighbors = await knowledgeGraphApi.getNodeNeighbors(
          workspaceId,
          nodeId,
          Math.min(depth + 1, 4)
        );
        setExtraNodes((prev) => {
          const ids = new Set(prev.map((n) => n.id));
          const newNodes = neighbors.nodes.filter((n) => !ids.has(n.id));
          // Cap total nodes at 200: only add as many as the remaining capacity allows.
          const nodesToAdd = newNodes.slice(0, remaining);
          if (newNodes.length > nodesToAdd.length) {
            toast.warning(
              `Graph limit reached (200 nodes). ${newNodes.length - nodesToAdd.length} nodes were not added.`
            );
          }
          return [...prev, ...nodesToAdd];
        });
        setExtraEdges((prev) => {
          const ids = new Set(prev.map((e) => e.id));
          return [...prev, ...neighbors.edges.filter((e) => !ids.has(e.id))];
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        console.error('Failed to expand node:', err);
        toast.error(`Failed to expand node: ${message}`);
      }
    },
    [mergedNodes.length, depth, workspaceId]
  );

  const handleNodeClick = useCallback((node: GraphNodeDTO) => {
    setSelectedNode(node);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const nodeTypedNodes = useMemo(
    () =>
      flowNodes.map((n) => ({
        ...n,
        data: {
          ...(n.data as GraphNodeData),
          onNodeClick: handleNodeClick,
        },
      })),
    [flowNodes, handleNodeClick]
  );

  const isLayoutComputing =
    !isLoading && !isError && !!data && data.nodes.length > 0 && flowNodes.length === 0;

  if (isLoading || isLayoutComputing) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <GraphEmptyState variant="loading" height={400} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <GraphEmptyState variant="error" height={400} onRetry={() => void refetch()} />
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <GraphEmptyState variant="empty" height={400} />
      </div>
    );
  }

  return (
    <>
      {/* Graph canvas */}
      <div className="flex-1 min-h-0">
        <ErrorBoundary
          fallback={<GraphEmptyState variant="error" height={400} onRetry={() => void refetch()} />}
        >
          <ReactFlow
            nodes={nodeTypedNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            minZoom={0.3}
            maxZoom={3}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            // React Flow MIT — attribution hidden per internal product decision (non-commercial/early-stage)
            proOptions={{ hideAttribution: true }}
            onNodeDoubleClick={(_evt, node) => void handleNodeDoubleClick(node.id)}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={0.8}
              className="opacity-20"
            />
            <MiniMap
              position="bottom-right"
              className="!bottom-4 !right-4"
              nodeColor={minimapNodeColor}
            />
            <Controls position="bottom-left" className="!bottom-4 !left-4" />
          </ReactFlow>
        </ErrorBoundary>
      </div>

      {/* Node detail panel */}
      {selectedNode && (
        <div
          className="border-t border-border bg-background p-4 flex flex-col gap-2"
          style={{ maxHeight: 200, minHeight: 80 }}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-col gap-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="inline-block rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground uppercase tracking-wide">
                  {selectedNode.nodeType.replace('_', ' ')}
                </span>
                <span className="font-semibold text-sm truncate">{selectedNode.label}</span>
              </div>
              {selectedNode.summary && (
                <p className="text-xs text-muted-foreground line-clamp-2">{selectedNode.summary}</p>
              )}
              {selectedNode.createdAt && (
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(selectedNode.createdAt), { addSuffix: true })}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleCloseDetail}
              className="shrink-0 rounded p-0.5 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Close node details"
            >
              <X className="size-4 text-muted-foreground" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// ── Public component ────────────────────────────────────────────────────────

export function ProjectKnowledgeGraph({ workspaceId, projectId }: ProjectKnowledgeGraphProps) {
  const [depth, setDepth] = useState(2);
  const [activeFilter, setActiveFilter] = useState<GraphNodeType | 'all'>('all');
  const [nodeCount, setNodeCount] = useState(0);

  const handleNodeCountChange = useCallback((count: number) => {
    setNodeCount((prev) => (prev === count ? prev : count));
  }, []);

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
          role="tablist"
          aria-label="Filter graph by node type"
        >
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.nodeType}
              role="tab"
              type="button"
              aria-selected={activeFilter === chip.nodeType}
              onClick={() => setActiveFilter(chip.nodeType)}
              className={[
                'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors shrink-0',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                activeFilter === chip.nodeType
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80',
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
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
