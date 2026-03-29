'use client';

/**
 * useDagreLayout — Auto-layout hook using @dagrejs/dagre.
 *
 * Computes a top-down (or left-right) DAG layout with non-overlapping
 * node positions, then updates ReactFlow nodes via setNodes + fitView.
 */

import { useCallback } from 'react';
import { useReactFlow, type Node } from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import type { WorkflowNodeData } from '@/features/skills/utils/graph-node-types';

const NODE_WIDTH = 200;
const NODE_HEIGHT = 80;

export function useDagreLayout() {
  const { getNodes, getEdges, setNodes, fitView } = useReactFlow<Node<WorkflowNodeData>>();

  const applyLayout = useCallback(
    (direction: 'TB' | 'LR' = 'TB') => {
      const nodes = getNodes();
      const edges = getEdges();

      if (nodes.length === 0) return;

      const g = new dagre.graphlib.Graph();
      g.setDefaultEdgeLabel(() => ({}));
      g.setGraph({
        rankdir: direction,
        nodesep: 80,
        ranksep: 100,
        marginx: 40,
        marginy: 40,
      });

      for (const node of nodes) {
        g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
      }

      for (const edge of edges) {
        g.setEdge(edge.source, edge.target);
      }

      dagre.layout(g);

      const layoutNodes = nodes.map((node) => {
        const nodeWithPos = g.node(node.id);
        return {
          ...node,
          position: {
            x: nodeWithPos.x - NODE_WIDTH / 2,
            y: nodeWithPos.y - NODE_HEIGHT / 2,
          },
        };
      });

      setNodes(layoutNodes);

      // Delay fitView to allow React to render new positions
      requestAnimationFrame(() => {
        fitView({ padding: 0.15 });
      });
    },
    [getNodes, getEdges, setNodes, fitView]
  );

  return { applyLayout };
}
