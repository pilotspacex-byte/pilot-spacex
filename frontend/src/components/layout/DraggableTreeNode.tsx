'use client';

/**
 * DraggableTreeNode — wraps TreeNode rendering with @dnd-kit useSortable.
 *
 * Adds a drag handle (GripVertical, visible on hover) and applies
 * transform/transition from useSortable to enable smooth animations.
 * Sets opacity to 0.4 when the node is actively being dragged.
 *
 * The data payload ({ parentId, depth, type }) lets handleDragEnd in
 * ProjectPageTree distinguish move vs. reorder without a separate lookup.
 */

import { useRef, useEffect } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { AnimatePresence, motion } from 'motion/react';
import { ChevronRight, ChevronDown, FileText, Plus, GripVertical } from 'lucide-react';
import Link from 'next/link';

import { cn } from '@/lib/utils';
import type { PageTreeNode } from '@/lib/tree-utils';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface DraggableTreeNodeProps {
  node: PageTreeNode;
  workspaceSlug: string;
  projectId: string;
  currentNoteId?: string;
  inlineCreateParentId: string | null;
  /** ID of the node that is currently an invalid drop target (depth limit exceeded). */
  invalidDropTargetId?: string | null;
  onToggleExpand: (nodeId: string) => void;
  isExpanded: (nodeId: string) => boolean;
  onAddChild: (nodeId: string) => void;
  onInlineSubmit: (title: string) => void;
  onInlineCancel: () => void;
}

// ---------------------------------------------------------------------------
// DraggableTreeNode
// ---------------------------------------------------------------------------

export function DraggableTreeNode({
  node,
  workspaceSlug,
  projectId,
  currentNoteId,
  inlineCreateParentId,
  invalidDropTargetId,
  onToggleExpand,
  isExpanded,
  onAddChild,
  onInlineSubmit,
  onInlineCancel,
}: DraggableTreeNodeProps) {
  const expanded = isExpanded(node.id);
  const isActive = node.id === currentNoteId;
  const hasChildren = node.children.length > 0;
  const canAddChild = node.depth < 2;
  const isInlineActive = inlineCreateParentId === node.id;
  const isInvalidTarget = invalidDropTargetId === node.id;

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isInlineActive) {
      inputRef.current?.focus();
    }
  }, [isInlineActive]);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: node.id,
    data: {
      parentId: node.parentId,
      depth: node.depth,
      type: 'tree-node',
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : undefined,
  };

  const indent = node.depth * 16;

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="tree-node"
      className={cn(
        isInvalidTarget && 'ring-1 ring-destructive/50 rounded-md opacity-60 cursor-not-allowed'
      )}
    >
      {/* Node row */}
      <div
        className="group flex items-center gap-0.5 rounded-md py-0.5 pr-1 text-xs"
        style={{ paddingLeft: `${indent + 4}px` }}
      >
        {/* Drag handle (hover reveal) */}
        <button
          type="button"
          aria-label="drag to reorder"
          className="hidden h-4 w-4 shrink-0 cursor-grab items-center justify-center rounded hover:bg-sidebar-accent/50 group-hover:flex active:cursor-grabbing"
          {...listeners}
          {...attributes}
        >
          <GripVertical className="h-3 w-3 text-muted-foreground" />
        </button>

        {/* Expand/collapse chevron */}
        <button
          type="button"
          aria-label={expanded ? 'collapse' : 'expand'}
          onClick={() => onToggleExpand(node.id)}
          className="flex h-4 w-4 shrink-0 items-center justify-center rounded hover:bg-sidebar-accent/50"
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3 w-3 text-muted-foreground" />
            )
          ) : (
            <span className="h-3 w-3" />
          )}
        </button>

        {/* Page link */}
        <Link
          href={`/${workspaceSlug}/notes/${node.id}`}
          className={cn(
            'flex flex-1 items-center gap-1 rounded-md px-1 py-0.5 transition-colors',
            isActive
              ? 'bg-sidebar-accent text-sidebar-foreground font-medium'
              : 'text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
          )}
        >
          {node.iconEmoji ? (
            <span className="shrink-0 w-3 text-center text-xs leading-none">{node.iconEmoji}</span>
          ) : (
            <FileText className="h-3 w-3 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate">{node.title || 'Untitled'}</span>
        </Link>

        {/* Add child button (hidden at depth 2) */}
        {canAddChild && (
          <button
            type="button"
            aria-label="add child page"
            onClick={() => onAddChild(node.id)}
            className="hidden h-4 w-4 shrink-0 items-center justify-center rounded hover:bg-sidebar-accent/50 group-hover:flex"
          >
            <Plus className="h-3 w-3 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Inline create input */}
      {isInlineActive && (
        <div
          className="flex items-center gap-1 py-0.5 pr-1"
          style={{ paddingLeft: `${indent + 24}px` }}
        >
          <FileText className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Page title..."
            className="flex-1 rounded bg-sidebar-accent/30 px-1 py-0.5 text-xs outline-none ring-1 ring-sidebar-border focus:ring-primary"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const value = e.currentTarget.value.trim();
                if (value) onInlineSubmit(value);
                else onInlineCancel();
              } else if (e.key === 'Escape') {
                onInlineCancel();
              }
            }}
            onBlur={(e) => {
              const value = e.currentTarget.value.trim();
              if (value) onInlineSubmit(value);
              else onInlineCancel();
            }}
          />
        </div>
      )}

      {/* Children (animated) */}
      <AnimatePresence initial={false}>
        {expanded && hasChildren && (
          <motion.div
            key={node.id + '-children'}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            {node.children.map((child) => (
              <DraggableTreeNode
                key={child.id}
                node={child}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                currentNoteId={currentNoteId}
                inlineCreateParentId={inlineCreateParentId}
                invalidDropTargetId={invalidDropTargetId}
                onToggleExpand={onToggleExpand}
                isExpanded={isExpanded}
                onAddChild={onAddChild}
                onInlineSubmit={onInlineSubmit}
                onInlineCancel={onInlineCancel}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
