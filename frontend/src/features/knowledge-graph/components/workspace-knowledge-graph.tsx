'use client';

/**
 * WorkspaceKnowledgeGraph — full interactive knowledge graph for a workspace.
 *
 * Reuses the same ReactFlow + d3-force pattern from project/issue graphs.
 * Shows all workspace nodes with filter chips, depth is N/A (flat overview).
 */

import { useCallback, useEffect, startTransition, useState, useMemo, useRef } from 'react';
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
import { toast } from 'sonner';

import { GraphDetailPanel } from '@/features/issues/components/graph-detail-panel';
import { GraphEmptyState, isForbiddenError } from '@/features/issues/components/graph-empty-state';
import { nodeTypes, type GraphNodeData } from '@/features/issues/components/graph-node-renderer';
import { ErrorBoundary } from '@/components/error-boundary';
import { computeForceLayout } from '@/features/issues/utils/graph-styles';
import { useWorkspaceKnowledgeGraph } from '@/features/knowledge-graph/hooks/useWorkspaceKnowledgeGraph';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeDTO, GraphEdgeDTO, GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface WorkspaceKnowledgeGraphProps {
  workspaceId: string;
}

interface FilterChip {
  label: string;
  nodeType: GraphNodeType | 'all';
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

const minimapNodeColor = (n: Node) => {
  const d = n.data as GraphNodeData | undefined;
  if (d?.isCurrent) return '#2563eb';
  return '#94a3b8';
};

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface CanvasProps {
  workspaceId: string;
  activeFilter: GraphNodeType | 'all';
  maxNodes: number;
  onNodeCountChange: (count: number) => void;
}

function WorkspaceGraphCanvas({
  workspaceId,
  activeFilter,
  maxNodes,
  onNodeCountChange,
}: CanvasProps) {
  const { fitView } = useReactFlow();

  const [selectedNode, setSelectedNode] = useState<GraphNodeDTO | null>(null);
  const [extraNodes, setExtraNodes] = useState<GraphNodeDTO[]>([]);
  const [extraEdges, setExtraEdges] = useState<GraphEdgeDTO[]>([]);
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);
  const filterRef = useRef(activeFilter);

  // Reset expanded nodes when filter changes
  useEffect(() => {
    filterRef.current = activeFilter;
    setExtraNodes([]);
    setExtraEdges([]);
    setSelectedNode(null);
  }, [activeFilter]);

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

  // Layout computation
  useEffect(() => {
    startTransition(() => {
      if (mergedNodes.length === 0) {
        setFlowNodes([]);
        setFlowEdges([]);
        return;
      }
      const [nodes, edges] = computeForceLayout(mergedNodes, mergedEdges, {
        width: 1200,
        height: 700,
        centerNodeId: data?.centerNodeId ?? mergedNodes[0]?.id ?? '',
        linkDistance: 120,
        chargeStrength: -200,
        collisionRadius: 45,
        edgeStrokeWidth: 1.5,
      });
      setFlowNodes(nodes);
      setFlowEdges(edges);
    });
  }, [mergedNodes, mergedEdges, data?.centerNodeId]);

  // Auto-fit when data loads
  useEffect(() => {
    if (flowNodes.length > 0) {
      requestAnimationFrame(() => {
        void fitView({ padding: 0.15, duration: 400 });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.nodes.length]);

  const handleNodeDoubleClick = useCallback(
    async (nodeId: string) => {
      const filterAtRequest = filterRef.current;
      const remaining = 500 - mergedNodes.length;
      if (remaining <= 0) {
        toast.warning('Graph limit reached (500 nodes).');
        return;
      }
      try {
        const neighbors = await knowledgeGraphApi.getNodeNeighbors(workspaceId, nodeId, 2);
        // Abort if filter changed during the async call
        if (filterRef.current !== filterAtRequest) return;
        setExtraNodes((prev) => {
          const ids = new Set(prev.map((n) => n.id));
          const newNodes = neighbors.nodes.filter((n) => !ids.has(n.id));
          return [...prev, ...newNodes.slice(0, remaining)];
        });
        setExtraEdges((prev) => {
          const ids = new Set(prev.map((e) => e.id));
          return [...prev, ...neighbors.edges.filter((e) => !ids.has(e.id))];
        });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        toast.error(`Failed to expand node: ${message}`);
      }
    },
    [mergedNodes.length, workspaceId]
  );

  const handleNodeClick = useCallback((node: GraphNodeDTO) => {
    setSelectedNode(node);
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
        <GraphEmptyState
          variant={isForbiddenError(error) ? 'forbidden' : 'error'}
          height={400}
          onRetry={isForbiddenError(error) ? undefined : () => void refetch()}
        />
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
      <div className="flex-1 min-h-0">
        <ErrorBoundary
          fallback={<GraphEmptyState variant="error" height={400} onRetry={() => void refetch()} />}
        >
          <ReactFlow
            nodes={nodeTypedNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            minZoom={0.2}
            maxZoom={3}
            fitView
            fitViewOptions={{ padding: 0.15 }}
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

      {selectedNode && (
        <GraphDetailPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onExpand={handleNodeDoubleClick}
        />
      )}
    </>
  );
}

// ── Public component ────────────────────────────────────────────────────────

export function WorkspaceKnowledgeGraph({ workspaceId }: WorkspaceKnowledgeGraphProps) {
  const [activeFilter, setActiveFilter] = useState<GraphNodeType | 'all'>('all');
  const [nodeCount, setNodeCount] = useState(0);

  const handleNodeCountChange = useCallback((count: number) => {
    setNodeCount((prev) => (prev === count ? prev : count));
  }, []);

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
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
