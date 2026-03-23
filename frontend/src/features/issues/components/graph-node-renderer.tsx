'use client';

/**
 * GraphNodeComponent — custom ReactFlow node renderer for knowledge graph.
 *
 * Design: "Entwined Growth Tree" — organic botanical aesthetic.
 *   - Project nodes: seed pods with rounded silhouette, filled with branch color
 *   - Entity nodes: leaf-shaped capsules with tinted surface + colored stem accent
 *   - Dev/chunk nodes: smaller buds with subtle coloring
 *   - Current node: warm glow ring (living energy)
 *   - Highlighted node: golden shimmer
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
  Expand,
  Shrink,
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
  isExpanded?: boolean;
  onNodeClick?: (node: GraphNodeDTO) => void;
  onNodeExpand?: (nodeId: string) => void;
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
  const {
    node,
    isCurrent = false,
    isHighlighted = false,
    isExpanded = false,
    onNodeClick,
    onNodeExpand,
  } = data;

  const style = getGraphNodeStyle(node.nodeType);
  const { width, height } = getNodeDimensions(style.tier, isCurrent);
  const IconComponent = NODE_ICONS[node.nodeType] ?? ScrollText;
  const isProject = style.tier === 0;

  const iconSize = isCurrent ? 16 : isProject ? 16 : style.tier === 1 ? 14 : 12;
  const fontSize = isCurrent ? 13 : isProject ? 13 : style.tier === 1 ? 11.5 : 10;
  const maxLabelWidth = width - iconSize - 18;
  const maxChars = isCurrent ? 32 : isProject ? 28 : style.tier === 1 ? 28 : 22;
  const truncated = truncateLabel(node.label, maxChars);

  const tooltipLines = [
    node.label,
    style.label,
    node.summary ? node.summary.slice(0, 100) + (node.summary.length > 100 ? '\u2026' : '') : null,
  ].filter(Boolean);

  // Organic border radius — rounder for projects (seed pod), leaf-like for entities
  const radius = isProject ? height / 2 : style.tier <= 1 ? 14 : 10;

  // Shadow: organic depth — projects get a colored ambient glow
  const shadow = isCurrent
    ? `0 0 0 2.5px ${style.bg}, 0 0 16px 3px color-mix(in srgb, ${style.bg} 35%, transparent)`
    : isHighlighted
      ? `0 0 0 2px #c4a035, 0 0 10px 2px rgba(196,160,53,0.2)`
      : isProject
        ? `0 3px 12px -2px color-mix(in srgb, ${style.bg} 30%, transparent), 0 1px 4px rgba(55,53,47,0.06)`
        : `0 1px 4px rgba(55,53,47,0.08), 0 0 0 1px color-mix(in srgb, ${style.bg} 12%, transparent)`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={() => onNodeClick?.(node)}
          className="group relative flex items-center cursor-pointer transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
          style={{
            width,
            height,
            borderRadius: radius,
            backgroundColor: isProject
              ? style.bg
              : `color-mix(in srgb, ${style.bg} 8%, var(--background))`,
            border: 'none',
            paddingLeft: isProject ? 10 : 8,
            paddingRight: isProject ? 10 : 8,
            gap: 5,
            boxShadow: shadow,
          }}
          aria-label={`${style.label}: ${node.label}`}
        >
          {/* Top-down tree handles */}
          <Handle
            type="target"
            position={Position.Top}
            className="!w-0 !h-0 !border-0 !bg-transparent !min-w-0 !min-h-0"
          />
          <Handle
            type="source"
            position={Position.Bottom}
            className="!w-0 !h-0 !border-0 !bg-transparent !min-w-0 !min-h-0"
          />

          {/* Stem accent — vertical bar on left (entity nodes only) */}
          {!isProject && (
            <span
              className="absolute left-0 top-1/2 -translate-y-1/2 rounded-full"
              style={{
                width: 3,
                height: '60%',
                backgroundColor: style.bg,
                opacity: 0.7,
              }}
              aria-hidden="true"
            />
          )}

          {/* Icon */}
          <span
            className="shrink-0 flex items-center justify-center rounded-full"
            style={{
              width: iconSize + 6,
              height: iconSize + 6,
              backgroundColor: isProject
                ? 'rgba(255,255,255,0.2)'
                : `color-mix(in srgb, ${style.bg} 15%, transparent)`,
            }}
          >
            <IconComponent
              width={iconSize}
              height={iconSize}
              style={{ color: isProject ? '#fff' : style.bg }}
              strokeWidth={1.6}
            />
          </span>

          {/* Label */}
          <span
            className="leading-tight truncate"
            style={{
              fontSize,
              fontWeight: isProject ? 600 : style.tier <= 1 ? 500 : 400,
              color: isProject ? '#fff' : 'var(--foreground)',
              maxWidth: maxLabelWidth - (onNodeExpand ? 14 : 0),
              letterSpacing: isProject ? '0.01em' : undefined,
            }}
          >
            {truncated}
          </span>

          {/* Expand/collapse toggle */}
          {onNodeExpand && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onNodeExpand(node.id);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.stopPropagation();
                  onNodeExpand(node.id);
                }
              }}
              className={`shrink-0 ml-auto rounded-full p-0.5 transition-opacity ${isExpanded ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
              style={{
                backgroundColor: isProject
                  ? 'rgba(255,255,255,0.15)'
                  : `color-mix(in srgb, ${style.bg} 10%, transparent)`,
              }}
              aria-label={isExpanded ? 'Collapse neighbors' : 'Expand neighbors'}
              aria-pressed={isExpanded}
            >
              {isExpanded ? (
                <Shrink
                  width={style.tier <= 1 ? 9 : 7}
                  height={style.tier <= 1 ? 9 : 7}
                  style={{ color: isProject ? '#fff' : style.bgDark }}
                  strokeWidth={2}
                />
              ) : (
                <Expand
                  width={style.tier <= 1 ? 9 : 7}
                  height={style.tier <= 1 ? 9 : 7}
                  style={{ color: isProject ? '#fff' : style.bgDark }}
                  strokeWidth={2}
                />
              )}
            </span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        className="max-w-[220px] rounded-xl px-3 py-2.5 shadow-lg"
        style={{
          borderColor: `color-mix(in srgb, ${style.bg} 20%, var(--border))`,
        }}
      >
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            <span
              className="inline-block size-2 rounded-full shrink-0"
              style={{ backgroundColor: style.bg }}
            />
            <span className="font-semibold text-xs">{tooltipLines[0]}</span>
          </div>
          {tooltipLines.slice(1).map((line, i) => (
            <span key={i} className="text-[11px] leading-snug opacity-60 pl-3.5">
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
