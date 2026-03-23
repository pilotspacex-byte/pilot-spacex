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
    bg: '#7c6fb5',
    bgTint: '#efedf6',
    bgDark: '#554a8a',
    tailwind: 'bg-[#7c6fb5]',
    text: '#fff',
    abbr: 'PJ',
    label: 'Project',
    tier: 0,
  },
  issue: {
    bg: '#3d7fa8',
    bgTint: '#eaf2f7',
    bgDark: '#2c5f82',
    tailwind: 'bg-[#3d7fa8]',
    text: '#fff',
    abbr: 'IS',
    label: 'Issue',
    tier: 1,
  },
  note: {
    bg: '#2d8a73',
    bgTint: '#e6f3ef',
    bgDark: '#1d6654',
    tailwind: 'bg-[#2d8a73]',
    text: '#fff',
    abbr: 'NO',
    label: 'Note',
    tier: 1,
  },
  cycle: {
    bg: '#c47a4a',
    bgTint: '#f8ede4',
    bgDark: '#935a35',
    tailwind: 'bg-[#c47a4a]',
    text: '#fff',
    abbr: 'CY',
    label: 'Cycle',
    tier: 1,
  },
  decision: {
    bg: '#b5943d',
    bgTint: '#f7f2e2',
    bgDark: '#856d2c',
    tailwind: 'bg-[#b5943d]',
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
// Organic vine-like edges — softer strokes, subtle dash patterns
const EDGE_STYLES: Partial<Record<GraphEdgeType, EdgeStyle>> = {
  belongs_to: { stroke: '#a8a29e', opacity: 0.5 },
  parent_of: { stroke: '#a8a29e', strokeDasharray: '8 3', opacity: 0.45 },
  relates_to: { stroke: '#7ba3bd', strokeDasharray: '6 4', opacity: 0.35 },
  references: { stroke: '#7ba3bd', strokeDasharray: '2 4', opacity: 0.35 },
  caused_by: { stroke: '#c9956a', opacity: 0.5 },
  led_to: { stroke: '#c9956a', strokeDasharray: '8 3', opacity: 0.5 },
  blocks: { stroke: '#c47070', opacity: 0.6 },
  duplicates: { stroke: '#c47070', strokeDasharray: '6 4', opacity: 0.5 },
  authored_by: { stroke: '#a8a29e', strokeDasharray: '3 3', opacity: 0.3 },
  assigned_to: { stroke: '#a8a29e', strokeDasharray: '3 5', opacity: 0.3 },
  decided_in: { stroke: '#b5a054', opacity: 0.4 },
  learned_from: { stroke: '#7ba3bd', strokeDasharray: '8 4', opacity: 0.3 },
  summarizes: { stroke: '#9b8fc0', strokeDasharray: '6 4', opacity: 0.3 },
};

const DEFAULT_EDGE_STYLE: EdgeStyle = { stroke: '#a8a29e', strokeDasharray: '6 4', opacity: 0.35 };

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
  if (isCurrent) return { width: 180, height: 46 };
  switch (tier) {
    case 0:
      return { width: 170, height: 44 }; // project — cluster anchor
    case 1:
      return { width: 155, height: 40 }; // entity (issue, note, cycle)
    case 2:
      return { width: 130, height: 34 }; // dev/ai (PR, commit, branch)
    default:
      return { width: 110, height: 30 }; // chunk/meta
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

  // Layout: top-down tree with wrapped rows
  const COL_W = 175; // horizontal space per child column
  const ROW_H = 58; // vertical space per child row
  const COLS = 4; // children per row before wrapping
  const ROOT_GAP_Y = 72; // vertical gap: root → first child row
  const TREE_GAP_Y = 70; // vertical gap between separate project trees
  const CHUNK_GAP_Y = 50; // vertical gap: child → grandchild
  const CHUNK_W = 120; // horizontal space per grandchild

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

  // Structural edges (belongs_to, parent_of) store child→parent direction
  // in the DB, but the tree renders parent→child (top→bottom). Swap them.
  const REVERSE_EDGE_TYPES = new Set(['belongs_to']);

  const edges: Edge[] = validEdges.map((e) => {
    const es = getEdgeStyle(e.edgeType);
    const showLabel = LABELED_EDGE_TYPES.has(e.edgeType);
    const reverse = REVERSE_EDGE_TYPES.has(e.edgeType);
    return {
      id: e.id,
      source: reverse ? e.targetId : e.sourceId,
      target: reverse ? e.sourceId : e.targetId,
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
