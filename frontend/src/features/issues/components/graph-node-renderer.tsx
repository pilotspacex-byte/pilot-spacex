'use client';

/**
 * GraphNodeComponent — custom ReactFlow node renderer for knowledge graph nodes.
 *
 * Renders a colored rectangle with truncated label, type abbreviation, and
 * a Tooltip showing full node metadata. Current-issue nodes get a larger
 * size and ring highlight.
 */

import { type NodeProps, type Node, type NodeTypes } from '@xyflow/react';
import {
  FileText,
  GitPullRequest,
  User,
  Lightbulb,
  Code,
  BookOpen,
  MessageSquare,
  Star,
  CircleDot,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { GraphNodeDTO, GraphNodeType } from '@/types/knowledge-graph';
import { getGraphNodeStyle } from '@/features/issues/utils/graph-styles';

// ── Types ──────────────────────────────────────────────────────────────────

export interface GraphNodeData extends Record<string, unknown> {
  node: GraphNodeDTO;
  isCurrent?: boolean;
  isHighlighted?: boolean;
  onNodeClick?: (node: GraphNodeDTO) => void;
}

export type GraphFlowNode = Node<GraphNodeData, 'graphNode'>;

const NODE_ICONS: Partial<Record<GraphNodeType, LucideIcon>> = {
  issue: CircleDot,
  note: FileText,
  decision: Lightbulb,
  user: User,
  pull_request: GitPullRequest,
  code_reference: Code,
  learned_pattern: BookOpen,
  conversation_summary: MessageSquare,
  skill_outcome: Star,
};

function renderNodeIcon(nodeType: GraphNodeType, color: string, size: number) {
  const IconComponent = NODE_ICONS[nodeType] ?? CircleDot;
  return <IconComponent style={{ color }} className="shrink-0" width={size} height={size} />;
}

// ── Component ─────────────────────────────────────────────────────────────

export function GraphNodeComponent({ data }: NodeProps<GraphFlowNode>) {
  const { node, isCurrent = false, isHighlighted = false, onNodeClick } = data;

  const style = getGraphNodeStyle(node.nodeType);

  const width = isCurrent ? 48 : 40;
  const height = isCurrent ? 32 : 28;
  const truncatedLabel = node.label.length > 12 ? node.label.slice(0, 11) + '\u2026' : node.label;

  const ringStyle = isCurrent
    ? {
        outline: '2px solid #93c5fd',
        outlineOffset: '2px',
        boxShadow: '0 0 8px 2px rgba(59,130,246,0.4)',
      }
    : isHighlighted
      ? { outline: '2px solid #fbbf24', outlineOffset: '2px' }
      : {};

  function handleClick() {
    onNodeClick?.(node);
  }

  const tooltipLines = [
    node.label,
    node.nodeType,
    node.summary ? node.summary.slice(0, 80) + (node.summary.length > 80 ? '…' : '') : null,
  ].filter(Boolean);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={handleClick}
          className="flex items-center justify-center gap-0.5 rounded-md cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
          style={{
            width,
            height,
            backgroundColor: style.bg,
            color: style.text,
            ...ringStyle,
          }}
          aria-label={`${node.nodeType}: ${node.label}`}
        >
          {renderNodeIcon(node.nodeType, style.text, isCurrent ? 10 : 9)}
          <span
            className="text-[8px] font-semibold leading-none truncate max-w-[28px]"
            style={{ color: style.text }}
          >
            {truncatedLabel}
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[200px]">
        <div className="flex flex-col gap-0.5">
          {tooltipLines.map((line, i) => (
            <span key={i} className={i === 0 ? 'font-semibold' : 'text-xs opacity-80'}>
              {line}
            </span>
          ))}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

// ── nodeTypes map for ReactFlow ────────────────────────────────────────────

export const nodeTypes: NodeTypes = {
  graphNode: GraphNodeComponent as NodeTypes[string],
};
