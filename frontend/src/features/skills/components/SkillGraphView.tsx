/**
 * SkillGraphView — top-level DAG canvas (Phase 92 Plan 02 Task 3).
 *
 * Wires Plan 92-01's pure helpers into a `<ReactFlow>` viewport via the
 * Plan 92-02 hooks. Renders four mutually exclusive branches:
 *
 *   1. catalog.isPending → centered skeleton block (no React Flow mount)
 *   2. catalog.isError   → <GraphErrorState onReload=catalog.refetch />
 *   3. graph.nodes === [] → <GraphEmptyState />
 *   4. ready             → <ReactFlow> with custom node dispatch
 *
 * Decision lock (UI-SPEC Design-Debt #5): `role="application"` is set on a
 * SIBLING `<div tabIndex=0>` that wraps the React Flow canvas region, NOT
 * on the React Flow root. This preserves React Flow's `<Controls>` AT
 * contract while still providing a focusable region for Plan 92-03's
 * keyboard nav handler to attach to.
 *
 * Cycle banner (UI-SPEC §Surface 4) is intentionally NOT implemented — the
 * v1 graph builder always returns `cycles: []` because the bipartite
 * skill→file structure is cycle-free by construction. Plan 92-01's SUMMARY
 * documents this contract; adding banner UI without a code path to trigger
 * it would be dead code.
 */
'use client';

import '@xyflow/react/dist/style.css';

import * as React from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Node,
} from '@xyflow/react';

import { useSkillGraphData } from '../hooks/useSkillGraphData';
import { useSkillGraphLayout } from '../hooks/useSkillGraphLayout';
import { useGraphKeyboardNav } from '../hooks/useGraphKeyboardNav';
import { SkillGraphNode } from './graph-nodes/SkillGraphNode';
import { FileGraphNode } from './graph-nodes/FileGraphNode';
import { GraphEmptyState } from './graph-states/GraphEmptyState';
import { GraphErrorState } from './graph-states/GraphErrorState';

/**
 * MiniMap node-color dispatch. Exported so the (mocked) test suite can call
 * the function directly without rendering the MiniMap stub.
 */
export function miniMapNodeColor(node: Node): string {
  return node.type === 'skill' ? '#7c5cff' : '#f1f1ef';
}

const NODE_TYPES = {
  skill: SkillGraphNode,
  file: FileGraphNode,
} as const;

export interface SkillGraphViewProps {
  /** Workspace slug used by keyboard nav to navigate to skill detail pages. */
  workspaceSlug?: string;
  /**
   * Phase 91-04 peek setter. Called when the user activates a file node
   * (Enter on selection, or DBL-click). When omitted the file activation is
   * a safe no-op.
   */
  onOpenFilePeek?: (parentSkillSlug: string, path: string) => void;
  /** Plan 92-03 toggle handoff — switches gallery back to cards mode. */
  onSwitchToCards?: () => void;
}

export function SkillGraphView({
  workspaceSlug = '',
  onOpenFilePeek,
  onSwitchToCards,
}: SkillGraphViewProps = {}): React.ReactElement {
  const { catalog, graph } = useSkillGraphData();
  const { flowNodes, flowEdges, isReady } = useSkillGraphLayout(graph);

  // Plan 92-03 — keyboard nav + click dispatch. The hook is pure-logic
  // (does not call `useReactFlow()`) so it can be invoked outside the
  // ReactFlowProvider; this also keeps the test harness simple.
  const noopPeek = React.useCallback(
    (_slug: string, _path: string) => {
      // intentional no-op fallback when consumer omits onOpenFilePeek
    },
    [],
  );
  const keyboardNav = useGraphKeyboardNav({
    flowNodes,
    flowEdges,
    workspaceSlug,
    onOpenFilePeek: onOpenFilePeek ?? noopPeek,
  });

  // Branch 1: pending → skeleton.
  if (catalog.isPending) {
    return (
      <ViewportShell>
        <div
          data-testid="skill-graph-skeleton"
          className="flex h-full w-full items-center justify-center"
        >
          <div className="h-20 w-[280px] motion-safe:animate-pulse rounded-2xl bg-[var(--surface-input,#f1f1ef)]" aria-label="Loading skills graph" role="status" />
        </div>
      </ViewportShell>
    );
  }

  // Branch 2: error → calm-error block (Reload triggers refetch).
  if (catalog.isError) {
    return (
      <ViewportShell>
        <GraphErrorState
          onReload={() => void catalog.refetch()}
          onSwitchToCards={onSwitchToCards}
        />
      </ViewportShell>
    );
  }

  // Defensive fallback: hooks haven't produced a layout yet but no error.
  // Show skeleton until the layout pipeline catches up with the catalog state.
  if (!isReady) {
    return (
      <ViewportShell>
        <div
          data-testid="skill-graph-skeleton"
          className="flex h-full w-full items-center justify-center"
        >
          <div className="h-20 w-[280px] motion-safe:animate-pulse rounded-2xl bg-[var(--surface-input,#f1f1ef)]" aria-label="Loading skills graph" role="status" />
        </div>
      </ViewportShell>
    );
  }

  // Branch 3: ready but no nodes → calm-empty block. Drive off the layout
  // hook's projected node array (the single source of truth for what the
  // canvas would render) so tests can simulate "real catalog, mocked layout"
  // without coupling the view to graph internals.
  if (flowNodes.length === 0) {
    return (
      <ViewportShell>
        <GraphEmptyState onSwitchToCards={onSwitchToCards} />
      </ViewportShell>
    );
  }

  // Branch 4: ready → mount React Flow.
  const skillCount = flowNodes.filter((n) => n.type === 'skill').length;
  const fileCount = flowNodes.filter((n) => n.type === 'file').length;
  const skillWord = skillCount === 1 ? 'skill' : 'skills';
  const fileWord = fileCount === 1 ? 'reference file' : 'reference files';
  const canvasAriaLabel = `Skill dependency graph. ${skillCount} ${skillWord}, ${fileCount} ${fileWord}. Use arrow keys to navigate, Enter to open, Escape to deselect.`;

  return (
    <ViewportShell>
      <ReactFlowProvider>
        <div
          tabIndex={0}
          role="application"
          aria-label={canvasAriaLabel}
          onKeyDown={keyboardNav.onKeyDown}
          className="h-full w-full focus-visible:outline-2 focus-visible:outline-[#29a386]"
        >
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={NODE_TYPES}
            fitView
            nodesDraggable={false}
            onNodeClick={keyboardNav.onNodeClick}
            onNodeDoubleClick={keyboardNav.onNodeDoubleClick}
            proOptions={{ hideAttribution: true }}
            minZoom={0.4}
            maxZoom={2}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1.5}
              color="#f0f0ee"
            />
            <Controls position="bottom-left" showInteractive />
            <MiniMap
              position="bottom-right"
              pannable
              zoomable
              nodeColor={miniMapNodeColor}
              maskColor="rgba(255,255,255,0.6)"
              style={{ width: 168, height: 112 }}
            />
          </ReactFlow>
        </div>
      </ReactFlowProvider>
    </ViewportShell>
  );
}

/**
 * Outer wrapper used by every branch so the viewport keeps a stable height
 * regardless of which state is rendered. `min-h: max(560px, calc(100vh - 160px))`
 * mirrors the UI-SPEC's "comfortable canvas" target on a 1440-tall display.
 */
function ViewportShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="relative h-full w-full"
      style={{ minHeight: 'max(560px, calc(100vh - 160px))' }}
    >
      {children}
    </div>
  );
}
