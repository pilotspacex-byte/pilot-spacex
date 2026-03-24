/**
 * graph-shared.ts — shared types and utilities for knowledge graph canvas components.
 *
 * Extracted from the duplicated code in:
 *   - issue-knowledge-graph-full.tsx
 *   - project-knowledge-graph.tsx
 *   - workspace-knowledge-graph.tsx
 */

import type { Node } from '@xyflow/react';
import type { GraphNodeData } from '@/features/issues/components/graph-node-renderer';
import type { GraphNodeType } from '@/types/knowledge-graph';
import { getGraphNodeStyle } from '@/features/issues/utils/graph-styles';

// ── Shared types ────────────────────────────────────────────────────────────

export interface FilterChip {
  label: string;
  nodeType: GraphNodeType | 'all';
}

// ── Shared utilities ────────────────────────────────────────────────────────

/** MiniMap node color: uses the node type's accent color, brighter for current node. */
export const minimapNodeColor = (n: Node): string => {
  const d = n.data as GraphNodeData | undefined;
  if (!d?.node) return '#94a3b8';
  if (d.isCurrent) return '#2563eb';
  return getGraphNodeStyle(d.node.nodeType).bg;
};
