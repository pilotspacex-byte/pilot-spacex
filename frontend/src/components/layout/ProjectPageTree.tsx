'use client';

/**
 * ProjectPageTree - Recursive sidebar tree for project pages with drag-and-drop.
 *
 * Renders the page hierarchy for a single project with expand/collapse
 * (persisted via UIStore), inline child creation, active page highlight,
 * and @dnd-kit drag-and-drop for reordering and re-parenting.
 *
 * Drag-end logic:
 * - Same parentId: sibling reorder — calls reorderPage.mutate
 * - Different parentId: re-parent — calls movePage.mutate
 * No optimistic updates — tree reflects server state after cache invalidation.
 */

import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  TouchSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { FileText } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { useUIStore } from '@/stores';
import { useProjectPageTree } from '@/features/notes/hooks/useProjectPageTree';
import { useCreateNote, useMovePage, useReorderPage } from '@/features/notes/hooks';
import { flattenTreeWithDepth, getSubtreeHeight } from '@/lib/tree-utils';
import { DraggableTreeNode } from './DraggableTreeNode';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ProjectPageTreeProps {
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
  projectName: string;
  currentNoteId?: string;
}

// ---------------------------------------------------------------------------
// ProjectPageTree — main export
// ---------------------------------------------------------------------------

export const ProjectPageTree = observer(function ProjectPageTree({
  workspaceId,
  workspaceSlug,
  projectId,
  currentNoteId,
}: ProjectPageTreeProps) {
  const router = useRouter();
  const uiStore = useUIStore();
  const { data: treeNodes = [], isLoading } = useProjectPageTree(workspaceId, projectId);

  const [inlineCreateParentId, setInlineCreateParentId] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [invalidDropTargetId, setInvalidDropTargetId] = useState<string | null>(null);

  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  const movePage = useMovePage(workspaceId, projectId);
  const reorderPage = useReorderPage(workspaceId, projectId);

  // Sensors — matching BoardView pattern
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Flat list of visible node ids for SortableContext
  const flatItems = flattenTreeWithDepth(treeNodes, (id) => uiStore.isNodeExpanded(id));
  const flatIds = flatItems.map((n) => n.id);

  // O(1) node metadata lookup for drag handlers (visible nodes only)
  const nodeMap = new Map(flatItems.map((n) => [n.id, { parentId: n.parentId, depth: n.depth }]));

  // Full node map (all nodes, including collapsed children) for subtree height lookup
  const fullNodeMap = new Map<string, import('@/lib/tree-utils').PageTreeNode>();
  (function walkAll(nodes: import('@/lib/tree-utils').PageTreeNode[]): void {
    for (const node of nodes) {
      fullNodeMap.set(node.id, node);
      if (node.children.length > 0) walkAll(node.children);
    }
  })(treeNodes);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      setInvalidDropTargetId(null);
      return;
    }

    const activeFullNode = fullNodeMap.get(active.id as string);
    const overMeta = nodeMap.get(over.id as string);

    if (!activeFullNode || !overMeta) {
      setInvalidDropTargetId(null);
      return;
    }

    const activeParentId = nodeMap.get(active.id as string)?.parentId;
    const overParentId = overMeta.parentId;

    if (activeParentId === overParentId) {
      // Same-parent reorder — depth unchanged, always valid
      setInvalidDropTargetId(null);
      return;
    }

    // Re-parent: active moves to over's parent, so active.depth becomes overMeta.depth.
    // The deepest descendant of active lands at: overMeta.depth + getSubtreeHeight(activeFullNode)
    const newDeepestDepth = overMeta.depth + getSubtreeHeight(activeFullNode);
    if (newDeepestDepth > 2) {
      setInvalidDropTargetId(over.id as string);
    } else {
      setInvalidDropTargetId(null);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) {
      setInvalidDropTargetId(null);
      return;
    }

    // Block drop onto invalid (depth-exceeding) target
    if (invalidDropTargetId && over.id === invalidDropTargetId) {
      setInvalidDropTargetId(null);
      return;
    }
    setInvalidDropTargetId(null);

    const activeNodeMeta = nodeMap.get(active.id as string);
    const overNodeMeta = nodeMap.get(over.id as string);

    if (!activeNodeMeta || !overNodeMeta) return;

    const activeParentId = activeNodeMeta.parentId;
    const overParentId = overNodeMeta.parentId;

    if (activeParentId === overParentId) {
      // Same parent — sibling reorder
      reorderPage.mutate({ noteId: active.id as string, insertAfterId: over.id as string });
    } else {
      // Different parent — re-parent
      movePage.mutate({ noteId: active.id as string, newParentId: overParentId });
    }
  };

  const handleInlineSubmit = (title: string) => {
    if (!inlineCreateParentId) return;
    createNote.mutate({
      title,
      parentId: inlineCreateParentId,
      projectId,
    });
    setInlineCreateParentId(null);
  };

  const handleInlineCancel = () => {
    setInlineCreateParentId(null);
  };

  // Active node for DragOverlay preview
  const activeNode = activeId ? flatItems.find((n) => n.id === activeId) : null;

  if (isLoading) {
    return <div className="px-3 py-1 text-xs text-muted-foreground/60">Loading...</div>;
  }

  if (treeNodes.length === 0) {
    return <div className="px-3 py-1 text-xs text-muted-foreground/60">No pages yet</div>;
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={flatIds} strategy={verticalListSortingStrategy}>
        <div className="space-y-px">
          {treeNodes.map((node) => (
            <DraggableTreeNode
              key={node.id}
              node={node}
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              currentNoteId={currentNoteId}
              inlineCreateParentId={inlineCreateParentId}
              invalidDropTargetId={invalidDropTargetId}
              onToggleExpand={(id) => uiStore.toggleNodeExpanded(id)}
              isExpanded={(id) => uiStore.isNodeExpanded(id)}
              onAddChild={(id) => setInlineCreateParentId(id)}
              onInlineSubmit={handleInlineSubmit}
              onInlineCancel={handleInlineCancel}
            />
          ))}
        </div>
      </SortableContext>

      <DragOverlay>
        {activeNode ? (
          <div className="flex items-center gap-1 rounded-md bg-sidebar-accent px-2 py-1 text-xs shadow-lg opacity-90">
            <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
            <span className="truncate text-sidebar-foreground">
              {treeNodes
                .flatMap(function flatten(n): typeof treeNodes {
                  return [n, ...n.children.flatMap(flatten)];
                })
                .find((n) => n.id === activeId)?.title ?? 'Page'}
            </span>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
});
