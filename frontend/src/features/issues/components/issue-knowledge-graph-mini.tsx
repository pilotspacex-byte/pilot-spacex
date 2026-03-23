'use client';

/**
 * IssueKnowledgeGraphMini — compact 200px knowledge graph preview.
 *
 * Renders inside a CollapsibleSection. Read-only (no pan/zoom/drag).
 * Uses d3-force for layout, @xyflow/react for rendering.
 * NOT wrapped in observer() — uses TanStack Query, not MobX.
 */

import { useEffect, startTransition, useState, useMemo } from 'react';
import { Network } from 'lucide-react';
import { ReactFlow, type Node, type Edge, Background, BackgroundVariant } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { CollapsibleSection } from './collapsible-section';
import { GraphEmptyState } from './graph-empty-state';
import { ApiError } from '@/services/api/client';
import { nodeTypes } from './graph-node-renderer';
import { ErrorBoundary } from '@/components/error-boundary';
import { computeForceLayout } from '@/features/issues/utils/graph-styles';
import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';

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
  const { data, isLoading, isError, error, refetch } = useIssueKnowledgeGraph(
    workspaceId,
    issueId,
    {
      enabled: true,
    }
  );

  const GRAPH_HEIGHT = 200;
  const GRAPH_WIDTH = 320;

  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  // M-9: validate centerNodeId exists in the node set
  const effectiveCenterNodeId = useMemo(() => {
    if (!data) return undefined;
    const exists = data.nodes.some((n) => n.id === data.centerNodeId);
    if (!exists) {
      console.warn('[KnowledgeGraph] centerNodeId not found in nodes:', data.centerNodeId);
    }
    return exists ? data.centerNodeId : (data.nodes[0]?.id ?? '');
  }, [data]);

  // H-6: move layout computation to useEffect with startTransition to yield to browser
  useEffect(() => {
    startTransition(() => {
      if (!data || data.nodes.length === 0) {
        setFlowNodes([]);
        setFlowEdges([]);
        return;
      }
      const [nodes, edges] = computeForceLayout(data.nodes, data.edges, {
        width: GRAPH_WIDTH,
        height: GRAPH_HEIGHT,
        centerNodeId: effectiveCenterNodeId ?? '',
        linkDistance: 100,
        chargeStrength: -150,
        collisionRadius: 60,
        edgeStrokeWidth: 1,
      });
      setFlowNodes(nodes);
      setFlowEdges(edges);
    });
  }, [data, effectiveCenterNodeId]);

  const nodeCount = data?.nodes.length ?? 0;
  const isLayoutComputing = nodeCount > 0 && !isLoading && !isError && flowNodes.length === 0;

  return (
    <CollapsibleSection
      title="Knowledge Graph"
      icon={<Network className="size-4 text-muted-foreground" aria-hidden="true" />}
      count={nodeCount}
      defaultOpen={true}
    >
      {(isLoading || isLayoutComputing) && (
        <GraphEmptyState variant="loading" height={GRAPH_HEIGHT} />
      )}

      {!isLoading && isError && (
        <GraphEmptyState
          variant={ApiError.isForbidden(error) ? 'forbidden' : 'error'}
          height={GRAPH_HEIGHT}
          onRetry={ApiError.isForbidden(error) ? undefined : () => void refetch()}
        />
      )}

      {!isLoading && !isError && nodeCount === 0 && (
        <GraphEmptyState variant="empty" height={GRAPH_HEIGHT} />
      )}

      {!isLoading && !isError && !isLayoutComputing && nodeCount > 0 && (
        <div
          className="rounded-md border border-border overflow-hidden"
          style={{ height: GRAPH_HEIGHT }}
        >
          <ErrorBoundary
            fallback={
              <GraphEmptyState
                variant="error"
                height={GRAPH_HEIGHT}
                onRetry={() => void refetch()}
              />
            }
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
          </ErrorBoundary>
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
