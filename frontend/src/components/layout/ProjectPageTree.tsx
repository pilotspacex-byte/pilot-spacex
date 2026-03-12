'use client';

/**
 * ProjectPageTree - Recursive sidebar tree for project pages.
 *
 * Renders the page hierarchy for a single project with expand/collapse
 * (persisted via UIStore), inline child creation, and active page highlight.
 */

import { useState, useRef, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { AnimatePresence, motion } from 'motion/react';
import { ChevronRight, ChevronDown, FileText, Plus } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores';
import { useProjectPageTree } from '@/features/notes/hooks/useProjectPageTree';
import { useCreateNote } from '@/features/notes/hooks';
import type { PageTreeNode } from '@/lib/tree-utils';

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
// TreeNode — recursive node renderer
// ---------------------------------------------------------------------------

interface TreeNodeProps {
  node: PageTreeNode;
  workspaceSlug: string;
  projectId: string;
  currentNoteId?: string;
  inlineCreateParentId: string | null;
  onToggleExpand: (nodeId: string) => void;
  isExpanded: (nodeId: string) => boolean;
  onAddChild: (nodeId: string) => void;
  onInlineSubmit: (title: string) => void;
  onInlineCancel: () => void;
}

function TreeNode({
  node,
  workspaceSlug,
  projectId,
  currentNoteId,
  inlineCreateParentId,
  onToggleExpand,
  isExpanded,
  onAddChild,
  onInlineSubmit,
  onInlineCancel,
}: TreeNodeProps) {
  const expanded = isExpanded(node.id);
  const isActive = node.id === currentNoteId;
  const hasChildren = node.children.length > 0;
  const canAddChild = node.depth < 2;
  const isInlineActive = inlineCreateParentId === node.id;

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isInlineActive) {
      inputRef.current?.focus();
    }
  }, [isInlineActive]);

  const indent = node.depth * 16;

  return (
    <div data-testid="tree-node">
      {/* Node row */}
      <div
        className="group flex items-center gap-0.5 rounded-md py-0.5 pr-1 text-xs"
        style={{ paddingLeft: `${indent + 4}px` }}
      >
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
              <TreeNode
                key={child.id}
                node={child}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                currentNoteId={currentNoteId}
                inlineCreateParentId={inlineCreateParentId}
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

  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

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

  if (isLoading) {
    return <div className="px-3 py-1 text-xs text-muted-foreground/60">Loading...</div>;
  }

  if (treeNodes.length === 0) {
    return <div className="px-3 py-1 text-xs text-muted-foreground/60">No pages yet</div>;
  }

  return (
    <div className="space-y-px">
      {treeNodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          currentNoteId={currentNoteId}
          inlineCreateParentId={inlineCreateParentId}
          onToggleExpand={(id) => uiStore.toggleNodeExpanded(id)}
          isExpanded={(id) => uiStore.isNodeExpanded(id)}
          onAddChild={(id) => setInlineCreateParentId(id)}
          onInlineSubmit={handleInlineSubmit}
          onInlineCancel={handleInlineCancel}
        />
      ))}
    </div>
  );
});
