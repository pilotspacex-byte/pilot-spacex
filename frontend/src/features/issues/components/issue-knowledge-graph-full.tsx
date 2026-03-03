'use client';

/**
 * IssueKnowledgeGraphFull — full interactive knowledge graph panel.
 *
 * Layout:
 *   1. Toolbar (40px): Back button, node-type filter chips, depth slider
 *   2. ReactFlow canvas (flex-1): interactive, minimap, zoom 0.3–3x
 *   3. Node detail panel (≤200px): shown when a node is selected
 *
 * State: local useState only (no MobX).
 * NOT wrapped in observer().
 */

import * as React from 'react';
import { ArrowLeft, X } from 'lucide-react';
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
import * as d3Force from 'd3-force';
import { formatDistanceToNow } from 'date-fns';

import { GraphEmptyState } from './graph-empty-state';
import { nodeTypes, type GraphNodeData } from './graph-node-renderer';
import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import type { GraphNodeDTO, GraphEdgeDTO, GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface IssueKnowledgeGraphFullProps {
  workspaceId: string;
  issueId: string;
  /** Highlight a specific node (e.g. from implementation panel). */
  highlightNodeId?: string;
  onClose: () => void;
}

interface FilterChip {
  label: string;
  nodeType: GraphNodeType | 'all';
}

const FILTER_CHIPS: FilterChip[] = [
  { label: 'Issues', nodeType: 'issue' },
  { label: 'Notes', nodeType: 'note' },
  { label: 'PRs', nodeType: 'pull_request' },
  { label: 'Decisions', nodeType: 'decision' },
  { label: 'Code', nodeType: 'code_reference' },
  { label: 'All', nodeType: 'all' },
];

// ── Layout helper ──────────────────────────────────────────────────────────

interface SimNode extends d3Force.SimulationNodeDatum {
  id: string;
}

function computeLayout(
  graphNodes: GraphNodeDTO[],
  graphEdges: GraphEdgeDTO[],
  centerNodeId: string,
  highlightNodeId?: string
): [Node[], Edge[]] {
  if (graphNodes.length === 0) return [[], []];

  const WIDTH = 800;
  const HEIGHT = 500;

  const simNodes: SimNode[] = graphNodes.map((n) => ({
    id: n.id,
    x: WIDTH / 2 + (Math.random() - 0.5) * 40,
    y: HEIGHT / 2 + (Math.random() - 0.5) * 40,
  }));

  const validIds = new Set(graphNodes.map((n) => n.id));
  const simLinks = graphEdges
    .filter((e) => validIds.has(e.sourceId) && validIds.has(e.targetId))
    .map((e) => ({ source: e.sourceId, target: e.targetId }));

  const simulation = d3Force
    .forceSimulation<SimNode>(simNodes)
    .force(
      'link',
      d3Force
        .forceLink<SimNode, d3Force.SimulationLinkDatum<SimNode>>(simLinks)
        .id((d) => d.id)
        .distance(80)
    )
    .force('charge', d3Force.forceManyBody().strength(-120))
    .force('center', d3Force.forceCenter(WIDTH / 2, HEIGHT / 2))
    .force('collision', d3Force.forceCollide(36));

  simulation.stop();
  for (let i = 0; i < 300; i++) simulation.tick();

  const posMap = new Map(simNodes.map((n) => [n.id, { x: n.x ?? 0, y: n.y ?? 0 }]));

  const nodes: Node[] = graphNodes.map((n) => ({
    id: n.id,
    type: 'graphNode',
    position: posMap.get(n.id) ?? { x: 0, y: 0 },
    data: {
      node: n,
      isCurrent: n.id === centerNodeId,
      isHighlighted: n.id === highlightNodeId,
    } satisfies GraphNodeData,
  }));

  const edges: Edge[] = graphEdges
    .filter((e) => validIds.has(e.sourceId) && validIds.has(e.targetId))
    .map((e) => ({
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      label: e.label,
      animated: e.edgeType === 'blocks',
      style: { stroke: '#94a3b8', strokeWidth: 1.5 },
    }));

  return [nodes, edges];
}

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface GraphCanvasProps {
  workspaceId: string;
  issueId: string;
  depth: number;
  activeFilter: GraphNodeType | 'all';
  highlightNodeId?: string;
  onClose: () => void;
}

function GraphCanvas({
  workspaceId,
  issueId,
  depth,
  activeFilter,
  highlightNodeId,
  onClose,
}: GraphCanvasProps) {
  const { fitView, setCenter } = useReactFlow();

  const [selectedNode, setSelectedNode] = React.useState<GraphNodeDTO | null>(null);
  const [extraNodes, setExtraNodes] = React.useState<GraphNodeDTO[]>([]);
  const [extraEdges, setExtraEdges] = React.useState<GraphEdgeDTO[]>([]);

  const nodeTypes_: GraphNodeType[] | undefined =
    activeFilter === 'all' ? undefined : [activeFilter];

  const { data, isLoading, isError, refetch } = useIssueKnowledgeGraph(workspaceId, issueId, {
    depth,
    nodeTypes: nodeTypes_,
    enabled: true,
  });

  // Merge base + expanded neighbor nodes
  const mergedNodes = React.useMemo(() => {
    if (!data) return [];
    const baseIds = new Set(data.nodes.map((n) => n.id));
    return [...data.nodes, ...extraNodes.filter((n) => !baseIds.has(n.id))];
  }, [data, extraNodes]);

  const mergedEdges = React.useMemo(() => {
    if (!data) return [];
    const baseIds = new Set(data.edges.map((e) => e.id));
    return [...data.edges, ...extraEdges.filter((e) => !baseIds.has(e.id))];
  }, [data, extraEdges]);

  const [flowNodes, flowEdges] = React.useMemo(
    () => computeLayout(mergedNodes, mergedEdges, data?.centerNodeId ?? '', highlightNodeId),

    [mergedNodes, mergedEdges, data?.centerNodeId, highlightNodeId]
  );

  // Auto-center on highlighted node
  React.useEffect(() => {
    if (!highlightNodeId || flowNodes.length === 0) return;
    const target = flowNodes.find((n) => n.id === highlightNodeId);
    if (target) {
      void setCenter(target.position.x, target.position.y, { zoom: 1.5, duration: 600 });
    }
  }, [highlightNodeId, flowNodes, setCenter]);

  // Auto-fit when data loads
  React.useEffect(() => {
    if (flowNodes.length > 0) {
      requestAnimationFrame(() => {
        void fitView({ padding: 0.15, duration: 400 });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.centerNodeId]);

  async function handleNodeDoubleClick(nodeId: string) {
    try {
      const neighbors = await knowledgeGraphApi.getNodeNeighbors(workspaceId, nodeId, depth + 1);
      setExtraNodes((prev) => {
        const ids = new Set(prev.map((n) => n.id));
        return [...prev, ...neighbors.nodes.filter((n) => !ids.has(n.id))];
      });
      setExtraEdges((prev) => {
        const ids = new Set(prev.map((e) => e.id));
        return [...prev, ...neighbors.edges.filter((e) => !ids.has(e.id))];
      });
    } catch {
      // silently ignore neighbor expansion errors
    }
  }

  function handleNodeClick(node: GraphNodeDTO) {
    setSelectedNode(node);
  }

  if (isLoading) {
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
        <GraphEmptyState variant="empty" height={400} onOpenChat={onClose} />
      </div>
    );
  }

  const nodeTypedNodes = flowNodes.map((n) => ({
    ...n,
    data: {
      ...(n.data as GraphNodeData),
      onNodeClick: handleNodeClick,
    },
  }));

  return (
    <>
      {/* Graph canvas */}
      <div className="flex-1 min-h-0">
        <ReactFlow
          nodes={nodeTypedNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          minZoom={0.3}
          maxZoom={3}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          proOptions={{ hideAttribution: true }}
          onNodeDoubleClick={(_evt, node) => void handleNodeDoubleClick(node.id)}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={0.8} className="opacity-20" />
          <MiniMap
            position="bottom-right"
            className="!bottom-4 !right-4"
            nodeColor={(n) => {
              const d = n.data as GraphNodeData | undefined;
              if (d?.isCurrent) return '#2563eb';
              return '#94a3b8';
            }}
          />
          <Controls position="bottom-left" className="!bottom-4 !left-4" />
        </ReactFlow>
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
              <p className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(selectedNode.createdAt), { addSuffix: true })}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedNode(null)}
              className="shrink-0 rounded p-0.5 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Close node details"
            >
              <X className="size-4 text-muted-foreground" />
            </button>
          </div>
          {(selectedNode.nodeType === 'issue' || selectedNode.nodeType === 'note') && (
            <div>
              <span className="text-xs text-primary cursor-pointer hover:underline">Open →</span>
            </div>
          )}
        </div>
      )}
    </>
  );
}

// ── Public component ────────────────────────────────────────────────────────

export function IssueKnowledgeGraphFull(props: IssueKnowledgeGraphFullProps) {
  const { workspaceId, issueId, onClose } = props;

  const [depth, setDepth] = React.useState(2);
  const [activeFilter, setActiveFilter] = React.useState<GraphNodeType | 'all'>('all');

  const { data } = useIssueKnowledgeGraph(workspaceId, issueId, {
    depth,
    nodeTypes: activeFilter === 'all' ? undefined : [activeFilter],
    enabled: true,
  });

  return (
    <div className="flex flex-col h-full bg-background" data-testid="knowledge-graph-full">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-3 border-b border-border shrink-0 overflow-x-auto"
        style={{ height: 40, minHeight: 40 }}
      >
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          aria-label="Back to chat"
        >
          <ArrowLeft className="size-3.5" />
          Back to Chat
        </button>

        <div className="w-px h-5 bg-border shrink-0" aria-hidden="true" />

        {/* Filter chips */}
        <div className="flex items-center gap-1" role="group" aria-label="Filter by node type">
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.nodeType}
              type="button"
              onClick={() => setActiveFilter(chip.nodeType)}
              className={[
                'rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors shrink-0',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                activeFilter === chip.nodeType
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80',
              ].join(' ')}
              aria-pressed={activeFilter === chip.nodeType}
            >
              {chip.label}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-border shrink-0" aria-hidden="true" />

        {/* Depth slider */}
        <div className="flex items-center gap-1.5 shrink-0">
          <label htmlFor="graph-depth" className="text-xs text-muted-foreground whitespace-nowrap">
            Depth {depth}
          </label>
          <input
            id="graph-depth"
            type="range"
            min={1}
            max={3}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-16 h-1 accent-primary cursor-pointer"
            aria-label="Graph depth"
          />
        </div>

        {data && (
          <span className="ml-auto text-xs text-muted-foreground shrink-0 whitespace-nowrap">
            {data.nodes.length} nodes
          </span>
        )}
      </div>

      {/* Graph canvas + detail panel via ReactFlowProvider */}
      <ReactFlowProvider>
        <div className="flex flex-col flex-1 min-h-0">
          <GraphCanvas
            workspaceId={workspaceId}
            issueId={issueId}
            depth={depth}
            activeFilter={activeFilter}
            highlightNodeId={props.highlightNodeId}
            onClose={onClose}
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
