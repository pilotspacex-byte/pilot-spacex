/**
 * useGraphCanvas — shared hook encapsulating the canvas state and logic
 * common to issue, project, and workspace knowledge graph components.
 *
 * Handles:
 *   - Extra nodes/edges from double-click expansion
 *   - Merged node/edge computation
 *   - d3-force layout via startTransition
 *   - Auto-fit on data load
 *   - Auto-center on highlighted node (issue graph)
 *   - Node click / double-click handlers
 *   - Node cap enforcement
 *   - Forbidden error detection
 *   - Layout-computing derivation
 */

import { useCallback, useEffect, useMemo, useRef, useState, startTransition } from 'react';
import { useReactFlow, type Node, type Edge } from '@xyflow/react';
import { toast } from 'sonner';

import { computeForceLayout, type ForceLayoutOptions } from '@/features/issues/utils/graph-styles';
import type { GraphNodeData } from '@/features/issues/components/graph-node-renderer';
import { knowledgeGraphApi } from '@/services/api/knowledge-graph';
import { ApiError } from '@/services/api/client';
import type { GraphNodeDTO, GraphEdgeDTO } from '@/types/knowledge-graph';
import type { GraphResponse } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface UseGraphCanvasOptions {
  data: GraphResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => void;
  workspaceId: string;
  layoutConfig: {
    width: number;
    height: number;
    centerNodeId?: string;
    highlightNodeId?: string;
    linkDistance: number;
    chargeStrength: number;
    collisionRadius: number;
    edgeStrokeWidth?: number;
  };
  /** Maximum number of nodes before expansion is blocked. Default: 200. */
  maxNodeCap?: number;
  /** Depth used for neighbor expansion requests. Default: 2. */
  expandDepth?: number;
  /**
   * When this key changes, extra nodes/edges are cleared.
   * Use to reset expansion when filter/depth changes externally.
   */
  resetKey?: string | number;
}

export interface UseGraphCanvasResult {
  flowNodes: Node[];
  flowEdges: Edge[];
  selectedNode: GraphNodeDTO | null;
  setSelectedNode: (node: GraphNodeDTO | null) => void;
  handleNodeClick: (node: GraphNodeDTO) => void;
  handleNodeDoubleClick: (nodeId: string) => Promise<void>;
  /** flowNodes with onNodeClick injected into data */
  nodeTypedNodes: Node[];
  isLayoutComputing: boolean;
  isForbidden: boolean;
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useGraphCanvas(options: UseGraphCanvasOptions): UseGraphCanvasResult {
  const {
    data,
    isLoading,
    isError,
    error,
    workspaceId,
    layoutConfig,
    maxNodeCap = 200,
    expandDepth = 2,
    resetKey,
  } = options;

  const { fitView, setCenter } = useReactFlow();

  const [selectedNode, setSelectedNode] = useState<GraphNodeDTO | null>(null);
  const [extraNodes, setExtraNodes] = useState<GraphNodeDTO[]>([]);
  const [extraEdges, setExtraEdges] = useState<GraphEdgeDTO[]>([]);
  const [flowNodes, setFlowNodes] = useState<Node[]>([]);
  const [flowEdges, setFlowEdges] = useState<Edge[]>([]);

  // Guard for stale async expansion responses after filter changes
  const resetKeyRef = useRef(resetKey);

  // Reset expanded nodes when resetKey changes
  useEffect(() => {
    resetKeyRef.current = resetKey;
    setExtraNodes([]);
    setExtraEdges([]);
    setSelectedNode(null);
  }, [resetKey]);

  // ── Merged nodes/edges ────────────────────────────────────────────────

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

  // ── Effective center node ─────────────────────────────────────────────

  const effectiveCenterNodeId = useMemo(() => {
    if (!data) return '';
    const center = layoutConfig.centerNodeId ?? data.centerNodeId;
    if (!center) return data.nodes[0]?.id ?? '';
    const exists = data.nodes.some((n) => n.id === center);
    if (!exists) {
      console.warn('[KnowledgeGraph] centerNodeId not found in nodes:', center);
    }
    return exists ? center : (data.nodes[0]?.id ?? '');
  }, [data, layoutConfig.centerNodeId]);

  // ── Layout computation ────────────────────────────────────────────────

  useEffect(() => {
    startTransition(() => {
      if (mergedNodes.length === 0) {
        setFlowNodes([]);
        setFlowEdges([]);
        return;
      }
      const layoutOptions: ForceLayoutOptions = {
        width: layoutConfig.width,
        height: layoutConfig.height,
        centerNodeId: effectiveCenterNodeId,
        highlightNodeId: layoutConfig.highlightNodeId,
        linkDistance: layoutConfig.linkDistance,
        chargeStrength: layoutConfig.chargeStrength,
        collisionRadius: layoutConfig.collisionRadius,
        edgeStrokeWidth: layoutConfig.edgeStrokeWidth ?? 1.5,
      };
      const [nodes, edges] = computeForceLayout(mergedNodes, mergedEdges, layoutOptions);
      setFlowNodes(nodes);
      setFlowEdges(edges);
    });
    // Layout config dimensions/forces are stable constants from the caller — intentionally
    // excluded to avoid unnecessary re-layouts (same pattern as the original components).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mergedNodes, mergedEdges, effectiveCenterNodeId, layoutConfig.highlightNodeId]);

  // ── Auto-center on highlighted node ───────────────────────────────────

  useEffect(() => {
    if (!layoutConfig.highlightNodeId || flowNodes.length === 0) return;
    const target = flowNodes.find((n) => n.id === layoutConfig.highlightNodeId);
    if (target) {
      void setCenter(target.position.x, target.position.y, { zoom: 1.5, duration: 600 });
    }
  }, [layoutConfig.highlightNodeId, flowNodes, setCenter]);

  // ── Auto-fit when data loads ──────────────────────────────────────────

  useEffect(() => {
    if (flowNodes.length > 0) {
      requestAnimationFrame(() => {
        void fitView({ padding: 0.15, duration: 400 });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveCenterNodeId]);

  // ── Node double-click → expand neighbors ──────────────────────────────

  const handleNodeDoubleClick = useCallback(
    async (nodeId: string) => {
      const currentResetKey = resetKeyRef.current;
      const remaining = maxNodeCap - mergedNodes.length;
      if (remaining <= 0) {
        toast.warning(
          `Graph limit reached (${maxNodeCap} nodes). Clear filters to reset the view.`
        );
        return;
      }
      try {
        const neighbors = await knowledgeGraphApi.getNodeNeighbors(
          workspaceId,
          nodeId,
          Math.min(expandDepth, 4)
        );
        // Abort if filter/depth changed during the async call
        if (resetKeyRef.current !== currentResetKey) return;
        setExtraNodes((prev) => {
          const ids = new Set(prev.map((n) => n.id));
          const newNodes = neighbors.nodes.filter((n) => !ids.has(n.id));
          const nodesToAdd = newNodes.slice(0, remaining);
          if (newNodes.length > nodesToAdd.length) {
            toast.warning(
              `Graph limit reached (${maxNodeCap} nodes). ${newNodes.length - nodesToAdd.length} nodes were not added.`
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
    [mergedNodes.length, expandDepth, workspaceId, maxNodeCap]
  );

  // ── Node click → select ───────────────────────────────────────────────

  const handleNodeClick = useCallback((node: GraphNodeDTO) => {
    setSelectedNode(node);
  }, []);

  // ── Nodes with onNodeClick injected ───────────────────────────────────

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

  // ── Derived state ─────────────────────────────────────────────────────

  const isLayoutComputing =
    !isLoading && !isError && !!data && data.nodes.length > 0 && flowNodes.length === 0;

  const isForbidden = ApiError.isForbidden(error);

  return {
    flowNodes,
    flowEdges,
    selectedNode,
    setSelectedNode,
    handleNodeClick,
    handleNodeDoubleClick,
    nodeTypedNodes,
    isLayoutComputing,
    isForbidden,
  };
}
