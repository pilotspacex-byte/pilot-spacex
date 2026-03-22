/**
 * graph-styles.ts — shared node type style configuration and tree layout utility
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
  /** Darkened variant for text on bgTint (AA compliant) */
  bgDark: string;
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
    bgTint: '#f0eef8',
    bgDark: '#5a4e99',
    tailwind: 'bg-[#8b7ec8]',
    text: '#fff',
    abbr: 'PJ',
    label: 'Project',
    tier: 0,
  },
  issue: {
    bg: '#5b8fc9',
    bgTint: '#edf3f9',
    bgDark: '#3a6a9e',
    tailwind: 'bg-[#5b8fc9]',
    text: '#fff',
    abbr: 'IS',
    label: 'Issue',
    tier: 1,
  },
  note: {
    bg: '#1f7d66',
    bgTint: '#e8f5f1',
    bgDark: '#165a4a',
    tailwind: 'bg-[#1f7d66]',
    text: '#fff',
    abbr: 'NO',
    label: 'Note',
    tier: 1,
  },
  cycle: {
    bg: '#a0602a',
    bgTint: '#faf0e6',
    bgDark: '#7a491f',
    tailwind: 'bg-[#a0602a]',
    text: '#fff',
    abbr: 'CY',
    label: 'Cycle',
    tier: 1,
  },
  decision: {
    bg: '#8a7025',
    bgTint: '#faf5e4',
    bgDark: '#655119',
    tailwind: 'bg-[#8a7025]',
    text: '#fff',
    abbr: 'DE',
    label: 'Decision',
    tier: 1,
  },
  user: {
    bg: '#9c9590',
    bgTint: '#f3f2f1',
    bgDark: '#5e5955',
    tailwind: 'bg-[#9c9590]',
    text: '#fff',
    abbr: 'US',
    label: 'User',
    tier: 2,
  },
  pull_request: {
    bg: '#6b8fad',
    bgTint: '#eef3f7',
    bgDark: '#4a6f8f',
    tailwind: 'bg-[#6b8fad]',
    text: '#fff',
    abbr: 'PR',
    label: 'Pull Request',
    tier: 2,
  },
  branch: {
    bg: '#5a7d9b',
    bgTint: '#eaf1f6',
    bgDark: '#3d5c75',
    tailwind: 'bg-[#5a7d9b]',
    text: '#fff',
    abbr: 'BR',
    label: 'Branch',
    tier: 2,
  },
  commit: {
    bg: '#4a6f8f',
    bgTint: '#e8eff5',
    bgDark: '#345068',
    tailwind: 'bg-[#4a6f8f]',
    text: '#fff',
    abbr: 'CM',
    label: 'Commit',
    tier: 2,
  },
  code_reference: {
    bg: '#d9534f',
    bgTint: '#fbeaea',
    bgDark: '#a33a37',
    tailwind: 'bg-[#d9534f]',
    text: '#fff',
    abbr: 'CR',
    label: 'Code',
    tier: 2,
  },
  learned_pattern: {
    bg: '#6b8fad',
    bgTint: '#eef3f7',
    bgDark: '#4a6f8f',
    tailwind: 'bg-[#6b8fad]',
    text: '#fff',
    abbr: 'LP',
    label: 'Pattern',
    tier: 2,
  },
  conversation_summary: {
    bg: '#8b7ec8',
    bgTint: '#f0eef8',
    bgDark: '#5a4e99',
    tailwind: 'bg-[#8b7ec8]',
    text: '#fff',
    abbr: 'CS',
    label: 'Summary',
    tier: 3,
  },
  skill_outcome: {
    bg: '#1f7d66',
    bgTint: '#e8f5f1',
    bgDark: '#165a4a',
    tailwind: 'bg-[#1f7d66]',
    text: '#fff',
    abbr: 'SO',
    label: 'Skill',
    tier: 2,
  },
  constitution_rule: {
    bg: '#d9534f',
    bgTint: '#fbeaea',
    bgDark: '#a33a37',
    tailwind: 'bg-[#d9534f]',
    text: '#fff',
    abbr: 'CO',
    label: 'Rule',
    tier: 2,
  },
  work_intent: {
    bg: '#a0602a',
    bgTint: '#faf0e6',
    bgDark: '#7a491f',
    tailwind: 'bg-[#a0602a]',
    text: '#fff',
    abbr: 'WI',
    label: 'Intent',
    tier: 2,
  },
  user_preference: {
    bg: '#8a7025',
    bgTint: '#faf5e4',
    bgDark: '#655119',
    tailwind: 'bg-[#8a7025]',
    text: '#fff',
    abbr: 'UP',
    label: 'Preference',
    tier: 3,
  },
  default: {
    bg: '#9c9590',
    bgTint: '#f3f2f1',
    bgDark: '#5e5955',
    tailwind: 'bg-[#9c9590]',
    text: '#fff',
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

// Each edge type gets a distinct visual signature (stroke color, dash, opacity)
// so relationships are distinguishable without relying on color alone (WCAG).
const EDGE_STYLES: Partial<Record<GraphEdgeType, EdgeStyle>> = {
  belongs_to: { stroke: '#9c9590', opacity: 0.6 },
  parent_of: { stroke: '#9c9590', strokeDasharray: '6 2', opacity: 0.6 },
  relates_to: { stroke: '#6b8fad', strokeDasharray: '4 3', opacity: 0.4 },
  references: { stroke: '#6b8fad', strokeDasharray: '1 3', opacity: 0.45 },
  caused_by: { stroke: '#d9853f', opacity: 0.6 },
  led_to: { stroke: '#d9853f', strokeDasharray: '6 2', opacity: 0.6 },
  blocks: { stroke: '#d9534f', opacity: 0.7 },
  duplicates: { stroke: '#d9534f', strokeDasharray: '4 3', opacity: 0.65 },
  authored_by: { stroke: '#9c9590', strokeDasharray: '2 2', opacity: 0.35 },
  assigned_to: { stroke: '#9c9590', strokeDasharray: '2 4', opacity: 0.4 },
  decided_in: { stroke: '#8a7025', opacity: 0.5 },
  learned_from: { stroke: '#6b8fad', strokeDasharray: '6 3', opacity: 0.35 },
  summarizes: { stroke: '#8b7ec8', strokeDasharray: '4 3', opacity: 0.35 },
};

const DEFAULT_EDGE_STYLE: EdgeStyle = { stroke: '#6b8fad', strokeDasharray: '4 3', opacity: 0.4 };

/** Pre-computed human-readable labels for edge types (avoids per-edge regex in layout). */
const EDGE_TYPE_LABELS: Record<GraphEdgeType, string> = {
  relates_to: 'relates to',
  caused_by: 'caused by',
  led_to: 'led to',
  decided_in: 'decided in',
  authored_by: 'authored by',
  assigned_to: 'assigned to',
  belongs_to: 'belongs to',
  references: 'references',
  learned_from: 'learned from',
  summarizes: 'summarizes',
  blocks: 'blocks',
  duplicates: 'duplicates',
  parent_of: 'parent of',
};

export function getEdgeLabel(edgeType: GraphEdgeType | string): string {
  return EDGE_TYPE_LABELS[edgeType as GraphEdgeType] ?? edgeType;
}

export function getEdgeStyle(edgeType: GraphEdgeType | string): EdgeStyle {
  return EDGE_STYLES[edgeType as GraphEdgeType] ?? DEFAULT_EDGE_STYLE;
}

/** Node dimensions by importance tier — sized for readability at fitView zoom. */
export function getNodeDimensions(
  tier: number,
  isCurrent: boolean
): { width: number; height: number } {
  if (isCurrent) return { width: 150, height: 48 };
  switch (tier) {
    case 0:
      return { width: 140, height: 44 }; // project — cluster anchor
    case 1:
      return { width: 120, height: 38 }; // entity (issue, note, cycle)
    case 2:
      return { width: 100, height: 32 }; // dev/ai (PR, commit, branch)
    default:
      return { width: 80, height: 28 }; // chunk/meta
  }
}

/** Truncate label at a word boundary. Falls back to hard truncation for long single words. */
export function truncateLabel(label: string, maxChars: number): string {
  if (label.length <= maxChars) return label;
  const truncated = label.slice(0, maxChars);
  const lastSpace = truncated.lastIndexOf(' ');
  if (lastSpace > maxChars * 0.6) {
    return truncated.slice(0, lastSpace) + '\u2026';
  }
  return truncated.slice(0, -1) + '\u2026';
}

// ── Shared tree layout ─────────────────────────────────────────────────────

export interface ForceLayoutOptions {
  width: number;
  height: number;
  /** Node ID to mark as the center/current node */
  centerNodeId: string;
  /** Optional node ID to mark as highlighted */
  highlightNodeId?: string;
  /** Horizontal gap between sibling nodes (default: 160) */
  linkDistance?: number;
  /** Vertical gap between parent-child tiers (default: 100) */
  chargeStrength?: number;
  /** Not used in tree layout — kept for API compat */
  collisionRadius?: number;
  /** Edge strokeWidth (default: 1.5) */
  edgeStrokeWidth?: number;
}

/**
 * Computes a grid-based tree layout for the knowledge graph.
 *
 * Structure: project nodes are roots displayed as section headers.
 * Children (issues/notes/cycles) are arranged in a grid below each
 * project, wrapping after COLS columns. Multiple project trees are
 * stacked vertically. Orphan nodes (no parent) appear at the bottom.
 */
export function computeForceLayout(
  graphNodes: GraphNodeDTO[],
  graphEdges: GraphEdgeDTO[],
  options: ForceLayoutOptions
): [Node[], Edge[]] {
  if (graphNodes.length === 0) return [[], []];

  const { centerNodeId, highlightNodeId, edgeStrokeWidth = 1.5 } = options;

  const validIds = new Set(graphNodes.map((n) => n.id));
  const validEdges = graphEdges.filter((e) => validIds.has(e.sourceId) && validIds.has(e.targetId));

  // Build parent→children adjacency from edges.
  // BELONGS_TO: source (child) → target (parent project)
  // PARENT_OF: source (parent) → target (child chunk)
  const childToParent = new Map<string, string>();
  for (const e of validEdges) {
    if (e.edgeType === 'belongs_to') {
      childToParent.set(e.sourceId, e.targetId);
    } else if (e.edgeType === 'parent_of') {
      childToParent.set(e.targetId, e.sourceId);
    }
  }

  // Group children under each parent
  const parentChildren = new Map<string, string[]>();
  for (const [childId, parentId] of childToParent) {
    const list = parentChildren.get(parentId) ?? [];
    list.push(childId);
    parentChildren.set(parentId, list);
  }

  // Find root nodes: nodes that are parents but not children, or project nodes
  const rootIds: string[] = [];
  const orphanIds: string[] = [];
  for (const n of graphNodes) {
    if (childToParent.has(n.id)) continue; // has a parent — not a root
    if (parentChildren.has(n.id)) {
      rootIds.push(n.id); // has children — is a root
    } else {
      orphanIds.push(n.id); // no parent, no children — orphan
    }
  }

  // If centerNodeId is set and is in the graph, ensure it's treated as root
  // (issue-scoped view: the issue is the center, its neighbors are children)
  if (centerNodeId && validIds.has(centerNodeId) && !rootIds.includes(centerNodeId)) {
    // For issue-scoped graphs, the center node is the root
    // Move it from orphans to roots if needed
    const idx = orphanIds.indexOf(centerNodeId);
    if (idx >= 0) orphanIds.splice(idx, 1);
    if (!rootIds.includes(centerNodeId)) rootIds.unshift(centerNodeId);
  }

  // Layout: top-down tree with wrapped rows (max COLS children per row)
  const COL_W = 145; // horizontal space per child column
  const ROW_H = 55; // vertical space per child row
  const COLS = 5; // children per row before wrapping
  const ROOT_GAP_Y = 75; // vertical gap: root → first child row
  const TREE_GAP_Y = 80; // vertical gap between separate project trees
  const CHUNK_GAP_Y = 45; // vertical gap: child → grandchild
  const CHUNK_W = 95; // horizontal space per grandchild

  const posMap = new Map<string, { x: number; y: number }>();
  const visited = new Set<string>();
  let yOffset = 0;

  for (const rootId of rootIds) {
    visited.add(rootId);
    const children = (parentChildren.get(rootId) ?? []).filter((c) => !visited.has(c));
    children.forEach((c) => visited.add(c));

    const cols = Math.min(COLS, Math.max(children.length, 1));
    const gridW = cols * COL_W;

    // Root: centered above its children
    posMap.set(rootId, { x: gridW / 2, y: yOffset });

    // Children: wrapped grid, each row up to COLS wide
    let maxChildY = yOffset + ROOT_GAP_Y;
    children.forEach((childId, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cx = col * COL_W + COL_W / 2;
      const cy = yOffset + ROOT_GAP_Y + row * ROW_H;
      posMap.set(childId, { x: cx, y: cy });

      // Grandchildren (chunks): fanned out below their parent
      const gkids = (parentChildren.get(childId) ?? []).filter((g) => !visited.has(g));
      if (gkids.length > 0) {
        const gkidTotalW = gkids.length * CHUNK_W;
        const gkidStartX = cx - gkidTotalW / 2 + CHUNK_W / 2;
        gkids.forEach((gcId, j) => {
          visited.add(gcId);
          posMap.set(gcId, { x: gkidStartX + j * CHUNK_W, y: cy + CHUNK_GAP_Y });
        });
        maxChildY = Math.max(maxChildY, cy + CHUNK_GAP_Y + ROW_H);
      } else {
        maxChildY = Math.max(maxChildY, cy + ROW_H);
      }
    });

    yOffset = maxChildY + TREE_GAP_Y;
  }

  // Orphan nodes: row at the bottom
  if (orphanIds.length > 0) {
    let orphanX = 0;
    for (const id of orphanIds) {
      if (!visited.has(id)) {
        posMap.set(id, { x: orphanX, y: yOffset });
        orphanX += COL_W;
        visited.add(id);
      }
    }
  }

  // Build ReactFlow nodes
  const nodes: Node[] = graphNodes.map((n) => {
    const style = getGraphNodeStyle(n.nodeType);
    const isCurrent = n.id === centerNodeId;
    const dims = getNodeDimensions(style.tier, isCurrent);
    return {
      id: n.id,
      type: 'graphNode',
      position: posMap.get(n.id) ?? { x: 0, y: 0 },
      // Explicit dimensions so MiniMap can render node shapes
      width: dims.width,
      height: dims.height,
      data: {
        node: n,
        isCurrent,
        isHighlighted: n.id === highlightNodeId,
      },
    };
  });

  // Build ReactFlow edges — only show labels on semantically significant types
  const LABELED_EDGE_TYPES = new Set(['blocks', 'caused_by', 'duplicates']);

  const edges: Edge[] = validEdges.map((e) => {
    const es = getEdgeStyle(e.edgeType);
    const showLabel = LABELED_EDGE_TYPES.has(e.edgeType);
    return {
      id: e.id,
      source: e.sourceId,
      target: e.targetId,
      type: 'smoothstep',
      label: showLabel ? (e.label ?? getEdgeLabel(e.edgeType)) : undefined,
      animated: e.edgeType === 'blocks',
      interactionWidth: 20,
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
