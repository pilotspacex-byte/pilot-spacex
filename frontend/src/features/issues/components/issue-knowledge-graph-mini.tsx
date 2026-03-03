'use client';

/**
 * IssueKnowledgeGraphMini — compact 200px knowledge graph preview.
 *
 * Renders inside a CollapsibleSection. Read-only (no pan/zoom/drag).
 * Uses d3-force for layout, @xyflow/react for rendering.
 * NOT wrapped in observer() — uses TanStack Query, not MobX.
 */

import * as React from 'react';
import { Network } from 'lucide-react';
import { ReactFlow, type Node, type Edge, Background, BackgroundVariant } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import * as d3Force from 'd3-force';

import { CollapsibleSection } from './collapsible-section';
import { GraphEmptyState } from './graph-empty-state';
import { nodeTypes } from './graph-node-renderer';
import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';
import type { GraphNodeDTO, GraphEdgeDTO } from '@/types/knowledge-graph';

// ── Layout helper ──────────────────────────────────────────────────────────

interface SimNode extends d3Force.SimulationNodeDatum {
  id: string;
}

function computeLayout(
  graphNodes: GraphNodeDTO[],
  graphEdges: GraphEdgeDTO[],
  centerNodeId: string,
  width: number,
  height: number
): [Node[], Edge[]] {
  if (graphNodes.length === 0) return [[], []];

  const simNodes: SimNode[] = graphNodes.map((n) => ({
    id: n.id,
    x: width / 2 + (Math.random() - 0.5) * 20,
    y: height / 2 + (Math.random() - 0.5) * 20,
  }));

  const simLinks: d3Force.SimulationLinkDatum<SimNode>[] = graphEdges
    .filter(
      (e) =>
        graphNodes.some((n) => n.id === e.sourceId) && graphNodes.some((n) => n.id === e.targetId)
    )
    .map((e) => ({ source: e.sourceId, target: e.targetId }));

  const simulation = d3Force
    .forceSimulation<SimNode>(simNodes)
    .force(
      'link',
      d3Force
        .forceLink<SimNode, d3Force.SimulationLinkDatum<SimNode>>(simLinks)
        .id((d) => d.id)
        .distance(60)
    )
    .force('charge', d3Force.forceManyBody().strength(-80))
    .force('center', d3Force.forceCenter(width / 2, height / 2))
    .force('collision', d3Force.forceCollide(28));

  // Run synchronously for 300 ticks
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
    },
  }));

  const edges: Edge[] = graphEdges
    .filter(
      (e) =>
        graphNodes.some((n) => n.id === e.sourceId) && graphNodes.some((n) => n.id === e.targetId)
    )
    .map((e) => ({
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      label: e.label,
      style: { stroke: '#94a3b8', strokeWidth: 1 },
    }));

  return [nodes, edges];
}

// ── Props ──────────────────────────────────────────────────────────────────

export interface IssueKnowledgeGraphMiniProps {
  workspaceId: string;
  issueId: string;
  onExpandFullView: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────

export function IssueKnowledgeGraphMini({
  workspaceId,
  issueId,
  onExpandFullView,
}: IssueKnowledgeGraphMiniProps) {
  const { data, isLoading, isError, refetch } = useIssueKnowledgeGraph(workspaceId, issueId, {
    enabled: true,
  });

  const GRAPH_HEIGHT = 200;
  const GRAPH_WIDTH = 320;

  const [flowNodes, flowEdges] = React.useMemo(() => {
    if (!data || data.nodes.length === 0) return [[], []];
    return computeLayout(data.nodes, data.edges, data.centerNodeId, GRAPH_WIDTH, GRAPH_HEIGHT);
  }, [data]);

  const nodeCount = data?.nodes.length ?? 0;

  return (
    <CollapsibleSection
      title="Knowledge Graph"
      icon={<Network className="size-4 text-muted-foreground" aria-hidden="true" />}
      count={nodeCount}
      defaultOpen={true}
    >
      {isLoading && <GraphEmptyState variant="loading" height={GRAPH_HEIGHT} />}

      {!isLoading && isError && (
        <GraphEmptyState variant="error" height={GRAPH_HEIGHT} onRetry={() => void refetch()} />
      )}

      {!isLoading && !isError && nodeCount === 0 && (
        <GraphEmptyState variant="empty" height={GRAPH_HEIGHT} />
      )}

      {!isLoading && !isError && nodeCount > 0 && (
        <div
          className="rounded-md border border-border overflow-hidden"
          style={{ height: GRAPH_HEIGHT }}
        >
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            elementsSelectable={false}
            nodesConnectable={false}
            nodesDraggable={false}
            panOnDrag={false}
            zoomOnScroll={false}
            zoomOnPinch={false}
            zoomOnDoubleClick={false}
            preventScrolling={false}
            proOptions={{ hideAttribution: true }}
            fitView
            fitViewOptions={{ padding: 0.2 }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={0.8}
              className="opacity-30"
            />
          </ReactFlow>
        </div>
      )}

      {!isLoading && !isError && nodeCount > 0 && (
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onExpandFullView}
            className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            aria-label="Expand full knowledge graph view"
          >
            Expand full view →
          </button>
        </div>
      )}
    </CollapsibleSection>
  );
}
