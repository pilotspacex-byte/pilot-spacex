'use client';

/**
 * TopicTreeRowContextMenu — Plan 93-05 Task 2.
 *
 * Wraps a sidebar TopicTreeRow with a Radix ContextMenu. Right-click anywhere
 * on the row opens a menu with a single "Move to…" item that calls
 * `uiStore.openPaletteForMove(note.id, note.parentTopicId)` — caching the
 * source's parent so `useMoveTopic.mutate(...)` has the `oldParentId` it needs
 * for the dual-key optimistic write (Plan 93-03 Decision J).
 *
 * Composition contract: the wrapper expects the TopicTreeRow as `children`
 * and forwards `asChild` to ContextMenuTrigger so Radix attaches its
 * onContextMenu handler to the row's root element directly (no extra DOM
 * wrapper, preserves `useSortable` ref + drag listeners). Decision AA in
 * Plan 93-05 picks this composition over the legacy onContextMenu callback
 * prop on TopicTreeRow.
 */

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from '@/components/ui/context-menu';
import { useUIStore } from '@/stores';
import type { Note } from '@/types';

interface Props {
  note: Note;
  children: React.ReactNode;
}

export function TopicTreeRowContextMenu({ note, children }: Props) {
  const uiStore = useUIStore();

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-48" data-testid="topic-tree-row-context-menu">
        <ContextMenuItem
          data-testid="topic-tree-row-move-to"
          onSelect={() => {
            uiStore.openPaletteForMove(note.id, note.parentTopicId ?? null);
          }}
        >
          Move to…
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
