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

// ── Types ──────────────────────────────────────────────────────────────────

export interface GraphNodeData extends Record<string, unknown> {
  node: GraphNodeDTO;
  isCurrent?: boolean;
  isHighlighted?: boolean;
  onNodeClick?: (node: GraphNodeDTO) => void;
}

export type GraphFlowNode = Node<GraphNodeData, 'graphNode'>;

// ── Color + abbreviation config ──────────────────────────────────────────

interface NodeStyle {
  bg: string;
  text: string;
  abbr: string;
}

const NODE_STYLES: Record<GraphNodeType | 'default', NodeStyle> = {
  issue: { bg: '#3b82f6', text: '#ffffff', abbr: 'IS' },
  note: { bg: '#10b981', text: '#ffffff', abbr: 'NO' },
  decision: { bg: '#f59e0b', text: '#ffffff', abbr: 'DE' },
  user: { bg: '#94a3b8', text: '#ffffff', abbr: 'US' },
  pull_request: { bg: '#a855f7', text: '#ffffff', abbr: 'PR' },
  code_reference: { bg: '#f97316', text: '#ffffff', abbr: 'CR' },
  learned_pattern: { bg: '#14b8a6', text: '#ffffff', abbr: 'LP' },
  conversation_summary: { bg: '#cbd5e1', text: '#000000', abbr: 'CS' },
  skill_outcome: { bg: '#818cf8', text: '#ffffff', abbr: 'SO' },
  project: { bg: '#6b7280', text: '#ffffff', abbr: 'PJ' },
  cycle: { bg: '#6b7280', text: '#ffffff', abbr: 'CY' },
  constitution_rule: { bg: '#6b7280', text: '#ffffff', abbr: 'CO' },
  work_intent: { bg: '#6b7280', text: '#ffffff', abbr: 'WI' },
  user_preference: { bg: '#6b7280', text: '#ffffff', abbr: 'UP' },
  default: { bg: '#6b7280', text: '#ffffff', abbr: '??' },
};

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

function getNodeStyle(nodeType: GraphNodeType): NodeStyle {
  return NODE_STYLES[nodeType] ?? NODE_STYLES.default;
}

function renderNodeIcon(nodeType: GraphNodeType, color: string, size: number) {
  const IconComponent = NODE_ICONS[nodeType] ?? CircleDot;
  return <IconComponent style={{ color }} className="shrink-0" width={size} height={size} />;
}

// ── Component ─────────────────────────────────────────────────────────────

export function GraphNodeComponent({ data }: NodeProps<GraphFlowNode>) {
  const { node, isCurrent = false, isHighlighted = false, onNodeClick } = data;

  const style = getNodeStyle(node.nodeType);

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
