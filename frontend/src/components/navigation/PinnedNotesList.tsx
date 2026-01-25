'use client';

/**
 * PinnedNotesList - Display and manage pinned notes
 * Drag-drop reorder, click to navigate, dropdown menu for actions
 */
import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { AnimatePresence, Reorder } from 'motion/react';
import { FileText, Pin, PinOff, Trash2, Copy, ExternalLink, MoreHorizontal } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export interface PinnedNote {
  id: string;
  title: string;
  updatedAt: string;
}

export interface PinnedNotesListProps {
  /** List of pinned notes */
  notes: PinnedNote[];
  /** Workspace slug for navigation */
  workspaceSlug: string;
  /** Currently selected note ID */
  selectedNoteId?: string;
  /** Callback when order changes */
  onReorder: (noteIds: string[]) => void;
  /** Callback to unpin note */
  onUnpin: (noteId: string) => void;
  /** Callback to delete note */
  onDelete?: (noteId: string) => void;
  /** Callback to duplicate note */
  onDuplicate?: (noteId: string) => void;
}

/**
 * Single pinned note item
 */
function PinnedNoteItem({
  note,
  isSelected,
  workspaceSlug,
  onUnpin,
  onDelete,
  onDuplicate,
}: {
  note: PinnedNote;
  isSelected: boolean;
  workspaceSlug: string;
  onUnpin: () => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
}) {
  const handleCopyLink = useCallback(() => {
    navigator.clipboard.writeText(`${window.location.origin}/${workspaceSlug}/notes/${note.id}`);
  }, [workspaceSlug, note.id]);

  const handleOpenNewTab = useCallback(() => {
    window.open(`/${workspaceSlug}/notes/${note.id}`, '_blank');
  }, [workspaceSlug, note.id]);

  return (
    <Reorder.Item
      value={note}
      className={cn(
        'group flex items-center gap-2 rounded-md px-2 py-1.5 cursor-grab active:cursor-grabbing',
        'transition-colors',
        isSelected ? 'bg-accent' : 'hover:bg-accent/50'
      )}
      whileDrag={{ scale: 1.02, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
    >
      <Pin className="h-3.5 w-3.5 text-amber-500 shrink-0" />
      <Link
        href={`/${workspaceSlug}/notes/${note.id}`}
        className="flex-1 min-w-0 text-sm truncate"
        onClick={(e) => e.stopPropagation()}
      >
        {note.title || 'Untitled'}
      </Link>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={onUnpin}>
            <PinOff className="mr-2 h-4 w-4" />
            Unpin
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleCopyLink}>
            <Copy className="mr-2 h-4 w-4" />
            Copy link
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleOpenNewTab}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Open in new tab
          </DropdownMenuItem>
          {onDuplicate && (
            <DropdownMenuItem onClick={onDuplicate}>
              <FileText className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
          )}
          {onDelete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive" onClick={onDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </Reorder.Item>
  );
}

/**
 * Empty state when no pinned notes
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-4 text-center">
      <Pin className="h-5 w-5 text-muted-foreground/30 mb-2" />
      <p className="text-xs text-muted-foreground">No pinned notes</p>
    </div>
  );
}

/**
 * PinnedNotesList component
 */
export const PinnedNotesList = observer(function PinnedNotesList({
  notes,
  workspaceSlug,
  selectedNoteId,
  onReorder,
  onUnpin,
  onDelete,
  onDuplicate,
}: PinnedNotesListProps) {
  const handleReorder = useCallback(
    (newOrder: PinnedNote[]) => {
      onReorder(newOrder.map((note) => note.id));
    },
    [onReorder]
  );

  if (notes.length === 0) {
    return <EmptyState />;
  }

  return (
    <Reorder.Group axis="y" values={notes} onReorder={handleReorder} className="space-y-0.5">
      <AnimatePresence mode="popLayout">
        {notes.map((note) => (
          <PinnedNoteItem
            key={note.id}
            note={note}
            isSelected={selectedNoteId === note.id}
            workspaceSlug={workspaceSlug}
            onUnpin={() => onUnpin(note.id)}
            onDelete={onDelete ? () => onDelete(note.id) : undefined}
            onDuplicate={onDuplicate ? () => onDuplicate(note.id) : undefined}
          />
        ))}
      </AnimatePresence>
    </Reorder.Group>
  );
});

export default PinnedNotesList;
