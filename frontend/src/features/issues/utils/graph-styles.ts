/**
 * graph-styles.ts — shared node type style configuration and d3-force layout utility
 * for knowledge graph rendering.
 *
 * Consumers:
 *   - graph-node-renderer.tsx    (ReactFlow canvas rendering)
 *   - github-implementation-section.tsx (DOM chip rendering)
 *   - issue-knowledge-graph-mini.tsx    (compact graph layout)
 *   - issue-knowledge-graph-full.tsx    (full interactive graph layout)
 */

import type { Node, Edge } from '@xyflow/react';
import * as d3Force from 'd3-force';
import type { GraphNodeType, GraphNodeDTO, GraphEdgeDTO } from '@/types/knowledge-graph';

export interface NodeStyle {
  /** Hex color for canvas rendering (ReactFlow nodes) */
  bg: string;
  /** Tailwind background class for DOM rendering */
  tailwind: string;
  /** Text color hex */
  text: string;
  /** 2-letter abbreviation */
  abbr: string;
  /** Display label */
  label: string;
}

export const GRAPH_NODE_STYLES: Record<GraphNodeType | 'default', NodeStyle> = {
  issue: { bg: '#3b82f6', tailwind: 'bg-blue-500', text: '#ffffff', abbr: 'IS', label: 'Issue' },
  note: { bg: '#10b981', tailwind: 'bg-emerald-500', text: '#ffffff', abbr: 'NO', label: 'Note' },
  decision: {
    bg: '#f59e0b',
    tailwind: 'bg-amber-500',
    text: '#ffffff',
    abbr: 'DE',
    label: 'Decision',
  },
  user: { bg: '#94a3b8', tailwind: 'bg-slate-400', text: '#ffffff', abbr: 'US', label: 'User' },
  pull_request: {
    bg: '#a855f7',
    tailwind: 'bg-purple-500',
    text: '#ffffff',
    abbr: 'PR',
    label: 'Pull Request',
  },
  code_reference: {
    bg: '#f97316',
    tailwind: 'bg-orange-500',
    text: '#ffffff',
    abbr: 'CR',
    label: 'Code',
  },
  learned_pattern: {
    bg: '#14b8a6',
    tailwind: 'bg-teal-500',
    text: '#ffffff',
    abbr: 'LP',
    label: 'Pattern',
  },
  conversation_summary: {
    bg: '#818cf8',
    tailwind: 'bg-indigo-400',
    text: '#ffffff',
    abbr: 'CS',
    label: 'Summary',
  },
  skill_outcome: {
    bg: '#818cf8',
    tailwind: 'bg-indigo-400',
    text: '#ffffff',
    abbr: 'SO',
    label: 'Skill',
  },
  project: {
    bg: '#8b5cf6',
    tailwind: 'bg-violet-500',
    text: '#ffffff',
    abbr: 'PJ',
    label: 'Project',
  },
  cycle: {
    bg: '#f97316',
    tailwind: 'bg-orange-500',
    text: '#ffffff',
    abbr: 'CY',
    label: 'Cycle',
  },
  constitution_rule: {
    bg: '#ef4444',
    tailwind: 'bg-red-500',
    text: '#ffffff',
    abbr: 'CO',
    label: 'Rule',
  },
  work_intent: {
    bg: '#f59e0b',
    tailwind: 'bg-amber-500',
    text: '#ffffff',
    abbr: 'WI',
    label: 'Intent',
  },
  user_preference: {
    bg: '#f43f5e',
    tailwind: 'bg-rose-500',
    text: '#ffffff',
    abbr: 'UP',
    label: 'Preference',
  },
  default: {
    bg: '#64748b',
    tailwind: 'bg-slate-500',
    text: '#ffffff',
    abbr: '??',
    label: 'Unknown',
  },
};

export function getGraphNodeStyle(nodeType: GraphNodeType | string): NodeStyle {
  return GRAPH_NODE_STYLES[nodeType as GraphNodeType] ?? GRAPH_NODE_STYLES.default;
}

// ── Shared d3-force layout ─────────────────────────────────────────────────

interface SimNode extends d3Force.SimulationNodeDatum {
  id: string;
}

export interface ForceLayoutOptions {
  width: number;
  height: number;
  /** Node ID to mark as the center/current node */
  centerNodeId: string;
  /** Optional node ID to mark as highlighted */
  highlightNodeId?: string;
  /** d3 link distance (default: 70) */
  linkDistance?: number;
  /** d3 charge strength (default: -100) */
  chargeStrength?: number;
  /** d3 collision radius (default: 32) */
  collisionRadius?: number;
  /** Edge strokeWidth (default: 1.5) */
  edgeStrokeWidth?: number;
}

/**
 * Runs a synchronous d3-force simulation to compute node positions,
 * then returns ReactFlow Node and Edge arrays ready for rendering.
 *
 * Intended to be called inside startTransition() to avoid blocking the main thread.
 */
export function computeForceLayout(
  graphNodes: GraphNodeDTO[],
  graphEdges: GraphEdgeDTO[],
  options: ForceLayoutOptions
): [Node[], Edge[]] {
  if (graphNodes.length === 0) return [[], []];

  const {
    width,
    height,
    centerNodeId,
    highlightNodeId,
    linkDistance = 70,
    chargeStrength = -100,
    collisionRadius = 32,
    edgeStrokeWidth = 1.5,
  } = options;

  const simNodes: SimNode[] = graphNodes.map((n) => ({
    id: n.id,
    x: width / 2 + (Math.random() - 0.5) * 30,
    y: height / 2 + (Math.random() - 0.5) * 30,
  }));

  // Use a Set for O(1) edge validity checks instead of O(n) .some()
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
        .distance(linkDistance)
    )
    .force('charge', d3Force.forceManyBody().strength(chargeStrength))
    .force('center', d3Force.forceCenter(width / 2, height / 2))
    .force('collision', d3Force.forceCollide(collisionRadius));

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
    },
  }));

  const edges: Edge[] = graphEdges
    .filter((e) => validIds.has(e.sourceId) && validIds.has(e.targetId))
    .map((e) => ({
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      label: e.label,
      animated: e.edgeType === 'blocks',
      style: { stroke: '#94a3b8', strokeWidth: edgeStrokeWidth },
    }));

  return [nodes, edges];
}
