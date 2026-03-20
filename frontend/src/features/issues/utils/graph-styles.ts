/**
 * graph-styles.ts — shared node type style configuration and d3-force layout utility
 * for knowledge graph rendering.
 *
 * Colors aligned with Pilot Space design tokens (globals.css):
 *   - Entity types use the project's state/semantic palette
 *   - AI/memory types use the AI partner dusty blue family
 *   - Dev types use the info blue family
 *
 * Consumers:
 *   - graph-node-renderer.tsx    (ReactFlow canvas rendering)
 *   - github-implementation-section.tsx (DOM chip rendering)
 *   - issue-knowledge-graph-mini.tsx    (compact graph layout)
 *   - issue-knowledge-graph-full.tsx    (full interactive graph layout)
 */

import type { Node, Edge } from '@xyflow/react';
import * as d3Force from 'd3-force';
import type {
  GraphNodeType,
  GraphNodeDTO,
  GraphEdgeDTO,
  GraphEdgeType,
} from '@/types/knowledge-graph';

export interface NodeStyle {
  /** Hex color for canvas rendering (ReactFlow nodes) */
  bg: string;
  /** Lighter tint for node background surface */
  bgTint: string;
  /** Tailwind background class for DOM rendering */
  tailwind: string;
  /** Text color hex */
  text: string;
  /** 2-letter abbreviation */
  abbr: string;
  /** Display label */
  label: string;
  /** Importance tier: 0 = highest (project), 1 = entity, 2 = dev/ai, 3 = chunk */
  tier: number;
}

// ── Design-system-aligned node colors ───────────────────────────────────────
// Primary entities use the project's semantic palette from globals.css
// AI/memory types use the AI partner dusty blue family
// Dev artifact types use the info blue family

export const GRAPH_NODE_STYLES: Record<GraphNodeType | 'default', NodeStyle> = {
  project: {
    bg: '#8b7ec8',
    tailwind: 'bg-[#8b7ec8]',
    bgTint: '#f0eef8',
    text: '#ffffff',
    abbr: 'PJ',
    label: 'Project',
    tier: 0,
  },
  issue: {
    bg: '#5b8fc9',
    tailwind: 'bg-[#5b8fc9]',
    bgTint: '#edf3f9',
    text: '#ffffff',
    abbr: 'IS',
    label: 'Issue',
    tier: 1,
  },
  note: {
    bg: '#29a386',
    tailwind: 'bg-[#29a386]',
    bgTint: '#e8f5f1',
    text: '#ffffff',
    abbr: 'NO',
    label: 'Note',
    tier: 1,
  },
  cycle: {
    bg: '#d9853f',
    tailwind: 'bg-[#d9853f]',
    bgTint: '#faf0e6',
    text: '#ffffff',
    abbr: 'CY',
    label: 'Cycle',
    tier: 1,
  },
  decision: {
    bg: '#c4a035',
    tailwind: 'bg-[#c4a035]',
    bgTint: '#faf5e4',
    text: '#ffffff',
    abbr: 'DE',
    label: 'Decision',
    tier: 1,
  },
  user: {
    bg: '#9c9590',
    tailwind: 'bg-[#9c9590]',
    bgTint: '#f3f2f1',
    text: '#ffffff',
    abbr: 'US',
    label: 'User',
    tier: 2,
  },
  pull_request: {
    bg: '#6b8fad',
    tailwind: 'bg-[#6b8fad]',
    bgTint: '#eef3f7',
    text: '#ffffff',
    abbr: 'PR',
    label: 'Pull Request',
    tier: 2,
  },
  branch: {
    bg: '#5a7d9b',
    tailwind: 'bg-[#5a7d9b]',
    bgTint: '#eaf1f6',
    text: '#ffffff',
    abbr: 'BR',
    label: 'Branch',
    tier: 2,
  },
  commit: {
    bg: '#4a6f8f',
    tailwind: 'bg-[#4a6f8f]',
    bgTint: '#e8eff5',
    text: '#ffffff',
    abbr: 'CM',
    label: 'Commit',
    tier: 2,
  },
  code_reference: {
    bg: '#d9534f',
    tailwind: 'bg-[#d9534f]',
    bgTint: '#fbeaea',
    text: '#ffffff',
    abbr: 'CR',
    label: 'Code',
    tier: 2,
  },
  learned_pattern: {
    bg: '#6b8fad',
    tailwind: 'bg-[#6b8fad]',
    bgTint: '#eef3f7',
    text: '#ffffff',
    abbr: 'LP',
    label: 'Pattern',
    tier: 2,
  },
  conversation_summary: {
    bg: '#8b7ec8',
    tailwind: 'bg-[#8b7ec8]',
    bgTint: '#f0eef8',
    text: '#ffffff',
    abbr: 'CS',
    label: 'Summary',
    tier: 3,
  },
  skill_outcome: {
    bg: '#29a386',
    tailwind: 'bg-[#29a386]',
    bgTint: '#e8f5f1',
    text: '#ffffff',
    abbr: 'SO',
    label: 'Skill',
    tier: 2,
  },
  constitution_rule: {
    bg: '#d9534f',
    tailwind: 'bg-[#d9534f]',
    bgTint: '#fbeaea',
    text: '#ffffff',
    abbr: 'CO',
    label: 'Rule',
    tier: 2,
  },
  work_intent: {
    bg: '#d9853f',
    tailwind: 'bg-[#d9853f]',
    bgTint: '#faf0e6',
    text: '#ffffff',
    abbr: 'WI',
    label: 'Intent',
    tier: 2,
  },
  user_preference: {
    bg: '#c4a035',
    tailwind: 'bg-[#c4a035]',
    bgTint: '#faf5e4',
    text: '#ffffff',
    abbr: 'UP',
    label: 'Preference',
    tier: 3,
  },
  default: {
    bg: '#9c9590',
    tailwind: 'bg-[#9c9590]',
    bgTint: '#f3f2f1',
    text: '#ffffff',
    abbr: '??',
    label: 'Unknown',
    tier: 3,
  },
};

export function getGraphNodeStyle(nodeType: GraphNodeType | string): NodeStyle {
  return GRAPH_NODE_STYLES[nodeType as GraphNodeType] ?? GRAPH_NODE_STYLES.default;
}

// ── Edge style configuration ──────────────────────────────────────────────

export interface EdgeStyle {
  stroke: string;
  strokeDasharray?: string;
  opacity: number;
}

const STRUCTURAL_EDGE: EdgeStyle = { stroke: '#9c9590', opacity: 0.6 };
const SIMILARITY_EDGE: EdgeStyle = { stroke: '#6b8fad', strokeDasharray: '4 3', opacity: 0.4 };
const CAUSAL_EDGE: EdgeStyle = { stroke: '#d9853f', opacity: 0.6 };
const BLOCKING_EDGE: EdgeStyle = { stroke: '#d9534f', opacity: 0.7 };

const EDGE_STYLES: Partial<Record<GraphEdgeType, EdgeStyle>> = {
  belongs_to: STRUCTURAL_EDGE,
  parent_of: STRUCTURAL_EDGE,
  relates_to: SIMILARITY_EDGE,
  references: SIMILARITY_EDGE,
  caused_by: CAUSAL_EDGE,
  led_to: CAUSAL_EDGE,
  blocks: BLOCKING_EDGE,
  duplicates: BLOCKING_EDGE,
  authored_by: { stroke: '#9c9590', strokeDasharray: '2 2', opacity: 0.35 },
  assigned_to: { stroke: '#9c9590', strokeDasharray: '2 2', opacity: 0.35 },
  decided_in: { stroke: '#c4a035', opacity: 0.5 },
  learned_from: { stroke: '#6b8fad', strokeDasharray: '6 3', opacity: 0.35 },
  summarizes: { stroke: '#8b7ec8', strokeDasharray: '4 3', opacity: 0.35 },
};

export function getEdgeStyle(edgeType: GraphEdgeType | string): EdgeStyle {
  return EDGE_STYLES[edgeType as GraphEdgeType] ?? SIMILARITY_EDGE;
}

/** Node dimensions by importance tier */
export function getNodeDimensions(
  tier: number,
  isCurrent: boolean
): { width: number; height: number } {
  if (isCurrent) return { width: 56, height: 38 };
  switch (tier) {
    case 0:
      return { width: 52, height: 36 }; // project
    case 1:
      return { width: 46, height: 32 }; // entity
    case 2:
      return { width: 40, height: 28 }; // dev/ai
    default:
      return { width: 36, height: 26 }; // chunk
  }
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
  // Filter once and reuse for both simulation links and ReactFlow edges.
  const validEdges = graphEdges.filter((e) => validIds.has(e.sourceId) && validIds.has(e.targetId));
  const simLinks = validEdges.map((e) => ({ source: e.sourceId, target: e.targetId }));

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

  const edges: Edge[] = validEdges.map((e) => {
    const es = getEdgeStyle(e.edgeType);
    return {
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      type: 'smoothstep',
      label: e.edgeType === 'blocks' ? e.label : undefined,
      animated: e.edgeType === 'blocks',
      style: {
        stroke: es.stroke,
        strokeWidth: edgeStrokeWidth,
        strokeDasharray: es.strokeDasharray,
        opacity: es.opacity,
      },
    };
  });

  return [nodes, edges];
}
