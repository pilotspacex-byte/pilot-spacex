'use client';

/**
 * IssueKnowledgeGraphFull — full interactive knowledge graph panel.
 *
 * Layout:
 *   1. Toolbar (40px): Back button, node-type filter chips, depth slider
 *   2. ReactFlow canvas (flex-1): interactive, minimap, zoom 0.3–3x
 *   3. Node detail panel (<=200px): shown when a node is selected
 *
 * State: local useState only (no MobX).
 * NOT wrapped in observer().
 */

import * as React from 'react';
import { useMemo } from 'react';
import { ArrowLeft } from 'lucide-react';
import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { GraphCanvasShell } from './graph-canvas-shell';
import { useGraphCanvas } from '@/features/issues/hooks/use-graph-canvas';
import { useIssueKnowledgeGraph } from '@/features/issues/hooks/use-issue-knowledge-graph';
import type { FilterChip } from '@/features/issues/utils/graph-shared';
import type { GraphNodeType } from '@/types/knowledge-graph';

// ── Types ──────────────────────────────────────────────────────────────────

export interface IssueKnowledgeGraphFullProps {
  workspaceId: string;
  issueId: string;
  /** Highlight a specific node (e.g. from implementation panel). */
  highlightNodeId?: string;
  onClose: () => void;
}

const FILTER_CHIPS: FilterChip[] = [
  { label: 'Issues', nodeType: 'issue' },
  { label: 'Notes', nodeType: 'note' },
  { label: 'PRs', nodeType: 'pull_request' },
  { label: 'Decisions', nodeType: 'decision' },
  { label: 'Code', nodeType: 'code_reference' },
  { label: 'All', nodeType: 'all' },
];

// ── Inner component (needs ReactFlowProvider context) ─────────────────────

interface GraphCanvasProps {
  workspaceId: string;
  issueId: string;
  depth: number;
  activeFilter: GraphNodeType | 'all';
  highlightNodeId?: string;
  onClose: () => void;
}

function GraphCanvas({
  workspaceId,
  issueId,
  depth,
  activeFilter,
  highlightNodeId,
  onClose,
}: GraphCanvasProps) {
  const nodeTypes_ = useMemo<GraphNodeType[] | undefined>(
    () => (activeFilter === 'all' ? undefined : [activeFilter]),
    [activeFilter]
  );

  const { data, isLoading, isError, error, refetch } = useIssueKnowledgeGraph(
    workspaceId,
    issueId,
    {
      depth,
      nodeTypes: nodeTypes_,
      enabled: true,
    }
  );

  const resetKey = `${activeFilter}-${depth}`;

  const canvas = useGraphCanvas({
    data,
    isLoading,
    isError,
    error,
    refetch,
    workspaceId,
    layoutConfig: {
      width: 800,
      height: 500,
      highlightNodeId,
      linkDistance: 80,
      chargeStrength: -120,
      collisionRadius: 36,
      edgeStrokeWidth: 1.5,
    },
    maxNodeCap: 200,
    expandDepth: depth,
    resetKey,
  });

  return (
    <GraphCanvasShell
      canvas={canvas}
      isLoading={isLoading}
      isError={isError}
      onRefetch={refetch}
      emptyStateAction={onClose}
    />
  );
}

// ── Public component ────────────────────────────────────────────────────────

export function IssueKnowledgeGraphFull(props: IssueKnowledgeGraphFullProps) {
  const { workspaceId, issueId, onClose } = props;

  const [depth, setDepth] = React.useState(2);
  const [activeFilter, setActiveFilter] = React.useState<GraphNodeType | 'all'>('all');

  const { data } = useIssueKnowledgeGraph(workspaceId, issueId, {
    depth,
    nodeTypes: activeFilter === 'all' ? undefined : [activeFilter],
    enabled: true,
  });

  return (
    <div className="flex flex-col h-full bg-background" data-testid="knowledge-graph-full">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-3 border-b border-border shrink-0 overflow-x-auto"
        style={{ height: 40, minHeight: 40 }}
      >
        <button
          type="button"
          onClick={onClose}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          aria-label="Back to chat"
        >
          <ArrowLeft className="size-3.5" />
          Back to Chat
        </button>

        <div className="w-px h-5 bg-border shrink-0" aria-hidden="true" />

        {/* Filter chips */}
        <div
          className="flex items-center gap-1"
          role="toolbar"
          aria-label="Filter graph by node type"
        >
          {FILTER_CHIPS.map((chip) => (
            <button
              key={chip.nodeType}
              type="button"
              aria-pressed={activeFilter === chip.nodeType}
              onClick={() => setActiveFilter(chip.nodeType)}
              className={[
                'rounded-full px-2.5 py-0.5 text-xs transition-colors shrink-0',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                activeFilter === chip.nodeType
                  ? 'bg-primary text-primary-foreground font-semibold ring-1 ring-primary/40'
                  : 'bg-muted text-muted-foreground font-medium hover:bg-muted/80',
              ].join(' ')}
            >
              {chip.label}
            </button>
          ))}
        </div>

        <div className="w-px h-5 bg-border shrink-0" aria-hidden="true" />

        {/* Depth slider */}
        <div className="flex items-center gap-1.5 shrink-0">
          <label htmlFor="graph-depth" className="text-xs text-muted-foreground whitespace-nowrap">
            Depth {depth}
          </label>
          <input
            id="graph-depth"
            type="range"
            min={1}
            max={3}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            className="w-16 h-1 accent-primary cursor-pointer"
            aria-label="Graph depth"
          />
        </div>

        {data && (
          <span className="ml-auto text-xs text-muted-foreground shrink-0 whitespace-nowrap">
            {data.nodes.length} nodes
          </span>
        )}
      </div>

      {/* Graph canvas + detail panel via ReactFlowProvider */}
      <ReactFlowProvider>
        <div className="flex flex-col flex-1 min-h-0">
          <GraphCanvas
            workspaceId={workspaceId}
            issueId={issueId}
            depth={depth}
            activeFilter={activeFilter}
            highlightNodeId={props.highlightNodeId}
            onClose={onClose}
          />
        </div>
      </ReactFlowProvider>
    </div>
  );
}
