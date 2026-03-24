'use client';

/**
 * GraphDetailPanel — bottom panel showing selected node details.
 *
 * Design: left accent bar matching node type, icon, full label,
 * summary, and timestamp. Clickable node type badge.
 */

import { ExternalLink, Expand, X } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { GraphNodeDTO } from '@/types/knowledge-graph';
import { getGraphNodeStyle } from '@/features/issues/utils/graph-styles';

/** Node types that link to navigable pages. */
const NAVIGABLE_TYPES = new Set(['issue', 'note', 'project', 'cycle']);

interface GraphDetailPanelProps {
  node: GraphNodeDTO;
  onClose: () => void;
  onExpand?: (nodeId: string) => void;
  onNavigate?: (nodeType: string, entityId: string) => void;
}

export function GraphDetailPanel({ node, onClose, onExpand, onNavigate }: GraphDetailPanelProps) {
  const style = getGraphNodeStyle(node.nodeType);

  return (
    <div
      className="border-t border-border bg-background flex"
      style={{ maxHeight: 160, minHeight: 72 }}
    >
      {/* Accent bar */}
      <div
        className="shrink-0"
        style={{ width: 3, backgroundColor: style.bg }}
        aria-hidden="true"
      />

      <div className="flex-1 flex items-start justify-between gap-3 px-4 py-3 min-w-0">
        <div className="flex flex-col gap-1.5 min-w-0">
          {/* Type badge + label */}
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider shrink-0"
              style={{
                backgroundColor: style.bgTint,
                color: style.bgDark,
              }}
            >
              <span
                className="inline-block size-1.5 rounded-full"
                style={{ backgroundColor: style.bg }}
              />
              {style.label}
            </span>
            <span className="font-medium text-sm text-foreground truncate">{node.label}</span>
          </div>

          {/* Summary */}
          {node.summary && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
              {node.summary}
            </p>
          )}

          {/* Timestamp */}
          {node.createdAt && (
            <p className="text-[11px] text-muted-foreground/70">
              {formatDistanceToNow(new Date(node.createdAt), { addSuffix: true })}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {onNavigate &&
            typeof node.properties?.external_id === 'string' &&
            NAVIGABLE_TYPES.has(node.nodeType) && (
              <button
                type="button"
                onClick={() =>
                  onNavigate(node.nodeType, (node.properties?.external_id as string) ?? node.id)
                }
                className="rounded-md p-1 hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label={`Open ${style.label.toLowerCase()}`}
                title={`Open ${style.label.toLowerCase()}`}
              >
                <ExternalLink className="size-3.5 text-muted-foreground" />
              </button>
            )}
          {onExpand && (
            <button
              type="button"
              onClick={() => onExpand(node.id)}
              className="rounded-md p-1 hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Expand neighbors"
            >
              <Expand className="size-3.5 text-muted-foreground" />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Close node details"
          >
            <X className="size-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}
