/**
 * useGraphKeyboardNav — keyboard nav + click dispatch for the skill DAG
 * canvas (Phase 92 Plan 03 Task 2).
 *
 * Pure-logic hook. Owns selectedId state and surfaces handlers the canvas
 * wrapper attaches:
 *   - onKeyDown (sibling div, role="application", tabIndex=0)
 *   - onNodeClick / onNodeDoubleClick (passed to <ReactFlow>)
 *
 * UI-SPEC §Interaction Contract — keyboard model:
 *   - ↓ on skill   → first reference file (target of outgoing edge)
 *   - ↑ on file    → parent skill (source of incoming edge)
 *   - → on any     → next sibling within rank (alphabetical, wraps)
 *   - ← on any     → previous sibling within rank (wraps)
 *   - Enter on skill → router.push(/{ws}/skills/{slug})
 *   - Enter on file  → onOpenFilePeek(parentSkillSlugs[0], path)
 *   - Esc          → clear selection
 *   - other keys   → no-op (no preventDefault, no state change)
 *
 * UI-SPEC OQ3 (double-click split lock):
 *   - skill node DBL-click → router.push to detail page
 *   - file node DBL-click  → onOpenFilePeek (Plan 91-04 peek drawer)
 *
 * The hook does not rely on `useReactFlow()` — every navigation decision is
 * made from the static `flowNodes` + `flowEdges` arrays the caller already
 * computed via `useSkillGraphLayout`. This keeps the hook unit-testable
 * without mounting React Flow.
 */
'use client';

import { useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Edge, Node } from '@xyflow/react';
import type { FlowNodeData } from './useSkillGraphLayout';

export interface UseGraphKeyboardNavArgs {
  flowNodes: Node<FlowNodeData>[];
  flowEdges: Edge[];
  workspaceSlug: string;
  /** Phase 91-04 peek setter — opens the drawer at a skill reference file. */
  onOpenFilePeek: (parentSkillSlug: string, path: string) => void;
}

export interface UseGraphKeyboardNavResult {
  selectedId: string | null;
  onKeyDown: (event: React.KeyboardEvent) => void;
  clearSelection: () => void;
  onNodeClick: (event: React.MouseEvent, node: Node) => void;
  onNodeDoubleClick: (event: React.MouseEvent, node: Node) => void;
}

const HANDLED_KEYS = new Set([
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Enter',
  'Escape',
]);

export function useGraphKeyboardNav(
  args: UseGraphKeyboardNavArgs,
): UseGraphKeyboardNavResult {
  const { flowNodes, flowEdges, workspaceSlug, onOpenFilePeek } = args;
  const router = useRouter();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Index nodes by id for O(1) lookup.
  const nodeById = useMemo(() => {
    const m = new Map<string, Node<FlowNodeData>>();
    for (const n of flowNodes) m.set(n.id, n);
    return m;
  }, [flowNodes]);

  // Pre-sort siblings within each rank (alphabetical by id — the layout
  // builder already emits skill nodes name-sorted and file nodes path-sorted,
  // so id ordering matches the visual rank ordering).
  const siblingRanks = useMemo(() => {
    const skills = flowNodes
      .filter((n) => n.type === 'skill')
      .map((n) => n.id)
      .sort();
    const files = flowNodes
      .filter((n) => n.type === 'file')
      .map((n) => n.id)
      .sort();
    return { skill: skills, file: files };
  }, [flowNodes]);

  const activate = useCallback(
    (node: Node<FlowNodeData>) => {
      if (node.data.kind === 'skill' && node.data.slug) {
        router.push(`/${workspaceSlug}/skills/${node.data.slug}`);
        return;
      }
      if (node.data.kind === 'file' && node.data.path) {
        const parent = node.data.parentSkillSlugs?.[0];
        if (!parent) return; // safe no-op for orphan files
        onOpenFilePeek(parent, node.data.path);
      }
    },
    [router, workspaceSlug, onOpenFilePeek],
  );

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedId(node.id);
  }, []);

  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const flowNode = nodeById.get(node.id);
      if (!flowNode) return;
      activate(flowNode);
    },
    [nodeById, activate],
  );

  const clearSelection = useCallback(() => {
    setSelectedId(null);
  }, []);

  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (!HANDLED_KEYS.has(event.key)) return;

      // Esc always works (even with no selection).
      if (event.key === 'Escape') {
        event.preventDefault();
        setSelectedId(null);
        return;
      }

      if (selectedId === null) {
        // Arrow / Enter with nothing selected — no-op (don't preventDefault).
        return;
      }

      const current = nodeById.get(selectedId);
      if (!current) return;

      const kind = current.data.kind;

      switch (event.key) {
        case 'ArrowDown': {
          // skill ↓ → first reference file
          if (kind !== 'skill') return;
          const out = flowEdges.find((e) => e.source === current.id);
          if (!out) return;
          event.preventDefault();
          setSelectedId(out.target);
          return;
        }
        case 'ArrowUp': {
          // file ↑ → parent skill
          if (kind !== 'file') return;
          const incoming = flowEdges.find((e) => e.target === current.id);
          if (!incoming) return;
          event.preventDefault();
          setSelectedId(incoming.source);
          return;
        }
        case 'ArrowRight':
        case 'ArrowLeft': {
          const rank = siblingRanks[kind];
          if (rank.length === 0) return;
          const idx = rank.indexOf(current.id);
          if (idx === -1) return;
          event.preventDefault();
          const delta = event.key === 'ArrowRight' ? 1 : -1;
          const nextIdx = (idx + delta + rank.length) % rank.length;
          setSelectedId(rank[nextIdx]!);
          return;
        }
        case 'Enter': {
          event.preventDefault();
          activate(current);
          return;
        }
      }
    },
    [selectedId, nodeById, flowEdges, siblingRanks, activate],
  );

  return {
    selectedId,
    onKeyDown,
    clearSelection,
    onNodeClick,
    onNodeDoubleClick,
  };
}
