'use client';

/**
 * GraphNodeComponent — custom ReactFlow node renderer for knowledge graph.
 *
 * Design principles (Pilot Space v4):
 *   - Tier-based sizing: projects > entities > dev artifacts > chunks
 *   - Tinted surface with left accent bar (not white-on-saturated)
 *   - Readable labels at default zoom
 *   - Current node: primary ring + subtle glow
 *   - Highlighted node: warm amber ring
 */

import { Handle, Position, type NodeProps, type Node, type NodeTypes } from '@xyflow/react';
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
  FolderKanban,
  RefreshCcw,
  GitBranch,
  GitCommit,
  ScrollText,
  Zap,
  Heart,
  Scale,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { GraphNodeDTO, GraphNodeType } from '@/types/knowledge-graph';
import {
  getGraphNodeStyle,
  getNodeDimensions,
  truncateLabel,
} from '@/features/issues/utils/graph-styles';

// ── Types ──────────────────────────────────────────────────────────────────

export interface GraphNodeData extends Record<string, unknown> {
  node: GraphNodeDTO;
  isCurrent?: boolean;
  isHighlighted?: boolean;
  onNodeClick?: (node: GraphNodeDTO) => void;
}

export type GraphFlowNode = Node<GraphNodeData, 'graphNode'>;

const NODE_ICONS: Partial<Record<GraphNodeType, LucideIcon>> = {
  project: FolderKanban,
  issue: CircleDot,
  note: FileText,
  cycle: RefreshCcw,
  decision: Lightbulb,
  user: User,
  pull_request: GitPullRequest,
  branch: GitBranch,
  commit: GitCommit,
  code_reference: Code,
  learned_pattern: BookOpen,
  conversation_summary: MessageSquare,
  skill_outcome: Star,
  constitution_rule: Scale,
  work_intent: Zap,
  user_preference: Heart,
};

// ── Component ─────────────────────────────────────────────────────────────

export function GraphNodeComponent({ data }: NodeProps<GraphFlowNode>) {
  const { node, isCurrent = false, isHighlighted = false, onNodeClick } = data;

  const style = getGraphNodeStyle(node.nodeType);
  const { width, height } = getNodeDimensions(style.tier, isCurrent);
  const IconComponent = NODE_ICONS[node.nodeType] ?? ScrollText;
  const isProject = style.tier === 0;
  const iconSize = isCurrent
    ? 16
    : isProject
      ? 16
      : style.tier === 1
        ? 14
        : style.tier === 2
          ? 12
          : 10;
  const fontSize = isCurrent
    ? 13
    : isProject
      ? 13
      : style.tier === 1
        ? 11
        : style.tier === 2
          ? 10
          : 9;
  const maxLabelWidth = width - iconSize - 16;
  const maxChars = isCurrent
    ? 28
    : isProject
      ? 24
      : style.tier === 1
        ? 28
        : style.tier === 2
          ? 20
          : 16;

  const truncated = truncateLabel(node.label, maxChars);

  const tooltipLines = [
    node.label,
    style.label,
    node.summary ? node.summary.slice(0, 100) + (node.summary.length > 100 ? '\u2026' : '') : null,
  ].filter(Boolean);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={() => onNodeClick?.(node)}
          className="relative flex items-center gap-1.5 cursor-pointer transition-shadow duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
          style={{
            width,
            height,
            borderRadius: isProject ? 12 : 8,
            backgroundColor: isProject ? style.bg : style.bgTint,
            border: isProject
              ? `2px solid color-mix(in srgb, ${style.bg} 70%, transparent)`
              : `1px solid color-mix(in srgb, ${style.bg} 25%, transparent)`,
            borderLeftWidth: isProject ? 2 : 3,
            borderLeftColor: isProject ? undefined : style.bg,
            paddingLeft: isProject ? 8 : 6,
            paddingRight: isProject ? 8 : 6,
            boxShadow: isCurrent
              ? `0 0 0 2px #29a386, 0 0 12px 2px rgba(41,163,134,0.25)`
              : isProject
                ? `0 2px 8px rgba(139,126,200,0.25), 0 1px 3px rgba(55,53,47,0.08)`
                : isHighlighted
                  ? `0 0 0 2px #c4a035, 0 0 8px 2px rgba(196,160,53,0.2)`
                  : `0 1px 2px rgba(55,53,47,0.06)`,
          }}
          aria-label={`${style.label}: ${node.label}`}
        >
          {/* Invisible handles for edge connections */}
          <Handle
            type="target"
            position={Position.Left}
            className="!w-0 !h-0 !border-0 !bg-transparent !min-w-0 !min-h-0"
          />
          <Handle
            type="source"
            position={Position.Right}
            className="!w-0 !h-0 !border-0 !bg-transparent !min-w-0 !min-h-0"
          />

          <IconComponent
            width={iconSize}
            height={iconSize}
            className="shrink-0"
            style={{ color: isProject ? '#fff' : style.bg }}
            strokeWidth={1.8}
          />
          <span
            className="leading-none truncate"
            style={{
              fontSize,
              fontWeight: isProject ? 600 : style.tier <= 1 ? 500 : 400,
              color: isProject ? '#fff' : 'var(--foreground)',
              maxWidth: maxLabelWidth,
            }}
          >
            {truncated}
          </span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-[220px] rounded-lg px-3 py-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block size-2 rounded-full shrink-0"
              style={{ backgroundColor: style.bg }}
            />
            <span className="font-semibold text-xs">{tooltipLines[0]}</span>
          </div>
          {tooltipLines.slice(1).map((line, i) => (
            <span key={i} className="text-[11px] leading-snug opacity-70 pl-3.5">
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
