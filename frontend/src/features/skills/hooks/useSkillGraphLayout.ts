/**
 * useSkillGraphLayout — converts Plan 92-01's `SkillGraphResult` into the
 * `Node[]` / `Edge[]` shape expected by `<ReactFlow>`.
 *
 * Phase 92 Plan 02 Task 1.
 *
 * Pipeline:
 *   1. Run `layoutSkillGraph` (deterministic two-rank + d3-force) to
 *      populate per-node `x`/`y`.
 *   2. Project each `SkillGraphNode` into a React Flow `Node<FlowNodeData>`,
 *      dispatching `type` to the `nodeTypes` registry (`'skill'` | `'file'`).
 *   3. Project each `SkillGraphEdge` into a React Flow `Edge` with a closed
 *      arrow head.
 *
 * Memoized on `graph` reference identity — upstream `useSkillGraphData`
 * already memoizes on the catalog's data reference, so the chain is stable
 * across no-op rerenders.
 *
 * `nodesDraggable={false}` is set at the canvas level (SkillGraphView), but
 * we also stamp `draggable: false` per node so the read-only contract holds
 * even if the consumer omits the canvas flag.
 */
'use client';

import { useMemo } from 'react';
import { MarkerType, type Edge, type Node } from '@xyflow/react';
import { layoutSkillGraph } from '../lib/skill-graph-layout';
import type { SkillGraphResult } from '../lib/skill-graph';

/**
 * Plain payload carried on each React Flow node. Mirrors `SkillGraphNode.data`
 * with the `label` and `kind` lifted to the top level so the custom node
 * components can read them without reaching into `data.data`.
 */
export interface FlowNodeData extends Record<string, unknown> {
  label: string;
  kind: 'skill' | 'file';
  slug?: string;
  path?: string;
  refCount?: number;
  parentSkillSlugs?: string[];
}

export interface UseSkillGraphLayoutResult {
  flowNodes: Node<FlowNodeData>[];
  flowEdges: Edge[];
  /**
   * `false` while waiting on `useSkillGraphData` (graph === null).
   * `true` once a graph is available, even when the graph is empty —
   * the empty case is rendered by SkillGraphView's branching code, not here.
   */
  isReady: boolean;
}

export function useSkillGraphLayout(
  graph: SkillGraphResult | null,
): UseSkillGraphLayoutResult {
  return useMemo<UseSkillGraphLayoutResult>(() => {
    if (!graph) {
      return { flowNodes: [], flowEdges: [], isReady: false };
    }
    if (graph.nodes.length === 0) {
      return { flowNodes: [], flowEdges: [], isReady: true };
    }

    const positioned = layoutSkillGraph(graph);
    const flowNodes: Node<FlowNodeData>[] = positioned.nodes.map((n) => ({
      id: n.id,
      type: n.kind, // dispatches `nodeTypes.skill` / `nodeTypes.file`
      position: { x: n.x ?? 0, y: n.y ?? 0 },
      draggable: false,
      data: {
        label: n.label,
        kind: n.kind,
        slug: n.data.slug,
        path: n.data.path,
        refCount: n.data.refCount,
        parentSkillSlugs: n.data.parentSkillSlugs,
      },
    }));

    const flowEdges: Edge[] = graph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      markerEnd: { type: MarkerType.ArrowClosed, width: 6, height: 6 },
    }));

    return { flowNodes, flowEdges, isReady: true };
  }, [graph]);
}
