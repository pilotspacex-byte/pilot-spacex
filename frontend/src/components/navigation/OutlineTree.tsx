'use client';

/**
 * OutlineTree - Tree view of notes in a project
 * Drag-drop reordering, create new note, search/filter
 */
import { useCallback, useMemo, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, AnimatePresence } from 'motion/react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  ChevronRight,
  ChevronDown,
  FileText,
  Plus,
  Search,
  MoreHorizontal,
  Pin,
  Trash2,
  Copy,
  FolderOpen,
  GripVertical,
} from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export interface NoteTreeItem {
  id: string;
  title: string;
  isPinned: boolean;
  hasChildren: boolean;
  children?: NoteTreeItem[];
  level: number;
}

export interface OutlineTreeProps {
  /** Tree items to display */
  items: NoteTreeItem[];
  /** Currently selected note ID */
  selectedNoteId?: string;
  /** Workspace slug for navigation */
  workspaceSlug: string;
  /** Callback when note is selected */
  onSelect?: (noteId: string) => void;
  /** Callback when note order changes */
  onReorder?: (noteId: string, newIndex: number, parentId?: string) => void;
  /** Callback to create new note */
  onCreateNote?: () => void;
  /** Callback to delete note */
  onDelete?: (noteId: string) => void;
  /** Callback to duplicate note */
  onDuplicate?: (noteId: string) => void;
  /** Callback to toggle pin */
  onTogglePin?: (noteId: string) => void;
}

/**
 * Sortable tree item component
 */
function SortableTreeItem({
  item,
  isSelected,
  workspaceSlug,
  onSelect,
  onDelete,
  onDuplicate,
  onTogglePin,
}: {
  item: NoteTreeItem;
  isSelected: boolean;
  workspaceSlug: string;
  onSelect?: () => void;
  onDelete?: () => void;
  onDuplicate?: () => void;
  onTogglePin?: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(item.level === 0);
  const [showMenu, setShowMenu] = useState(false);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <div
        className={cn(
          'group flex items-center gap-1 rounded-md px-1 py-1 transition-colors',
          isSelected && 'bg-accent',
          isDragging && 'opacity-50',
          !isDragging && 'hover:bg-accent/50'
        )}
        style={{ paddingLeft: `${item.level * 12 + 4}px` }}
      >
        {/* Drag handle */}
        <button
          {...listeners}
          className="opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing p-0.5 hover:bg-accent rounded"
        >
          <GripVertical className="h-3.5 w-3.5 text-muted-foreground" />
        </button>

        {/* Expand/collapse */}
        {item.hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-0.5 hover:bg-accent rounded"
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </button>
        ) : (
          <span className="w-5" />
        )}

        {/* Note link */}
        <Link
          href={`/${workspaceSlug}/notes/${item.id}`}
          className="flex flex-1 items-center gap-1.5 min-w-0"
          onClick={() => onSelect?.()}
        >
          <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span
            className={cn(
              'truncate text-sm',
              isSelected ? 'text-foreground font-medium' : 'text-foreground/80'
            )}
          >
            {item.title || 'Untitled'}
          </span>
          {item.isPinned && <Pin className="h-3 w-3 text-amber-500 shrink-0" />}
        </Link>

        {/* Actions menu */}
        <DropdownMenu open={showMenu} onOpenChange={setShowMenu}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn('h-6 w-6 opacity-0 group-hover:opacity-100', showMenu && 'opacity-100')}
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            {onTogglePin && (
              <DropdownMenuItem onClick={onTogglePin}>
                <Pin className="mr-2 h-4 w-4" />
                {item.isPinned ? 'Unpin' : 'Pin'}
              </DropdownMenuItem>
            )}
            {onDuplicate && (
              <DropdownMenuItem onClick={onDuplicate}>
                <Copy className="mr-2 h-4 w-4" />
                Duplicate
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            {onDelete && (
              <DropdownMenuItem className="text-destructive" onClick={onDelete}>
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Children */}
      <AnimatePresence>
        {isExpanded && item.children && item.children.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            {item.children.map((child) => (
              <SortableTreeItem
                key={child.id}
                item={child}
                isSelected={false}
                workspaceSlug={workspaceSlug}
                onSelect={onSelect}
                onDelete={onDelete}
                onDuplicate={onDuplicate}
                onTogglePin={onTogglePin}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Empty state when no notes
 */
function EmptyState({ onCreate }: { onCreate?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-6 text-center">
      <FolderOpen className="h-8 w-8 text-muted-foreground/30 mb-2" />
      <p className="text-sm text-muted-foreground mb-3">No topics yet</p>
      {onCreate && (
        <Button size="sm" onClick={onCreate}>
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Create Topic
        </Button>
      )}
    </div>
  );
}

/**
 * OutlineTree component
 */
export const OutlineTree = observer(function OutlineTree({
  items,
  selectedNoteId,
  workspaceSlug,
  onSelect,
  onReorder,
  onCreateNote,
  onDelete,
  onDuplicate,
  onTogglePin,
}: OutlineTreeProps) {
  const [searchQuery, setSearchQuery] = useState('');

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Filter items by search query
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;

    const query = searchQuery.toLowerCase();

    function filterItem(item: NoteTreeItem): NoteTreeItem | null {
      const matches = item.title.toLowerCase().includes(query);
      const filteredChildren = item.children
        ?.map(filterItem)
        .filter((child): child is NoteTreeItem => child !== null);

      if (matches || (filteredChildren && filteredChildren.length > 0)) {
        return {
          ...item,
          children: filteredChildren,
        };
      }
      return null;
    }

    return items.map(filterItem).filter((item): item is NoteTreeItem => item !== null);
  }, [items, searchQuery]);

  // Flatten for sortable context
  const flattenedIds = useMemo(() => {
    function flatten(items: NoteTreeItem[]): string[] {
      return items.flatMap((item) => [item.id, ...(item.children ? flatten(item.children) : [])]);
    }
    return flatten(filteredItems);
  }, [filteredItems]);

  // Handle drag end
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;

      if (over && active.id !== over.id && onReorder) {
        const newIndex = flattenedIds.indexOf(over.id as string);
        onReorder(active.id as string, newIndex);
      }
    },
    [flattenedIds, onReorder]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Search */}
      <div className="p-2 border-b border-border">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes..."
            className="h-8 pl-8 text-sm"
          />
        </div>
      </div>

      {/* Create button */}
      {onCreateNote && (
        <div className="p-2 border-b border-border">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={onCreateNote}
          >
            <Plus className="mr-2 h-4 w-4" />
            New Topic
          </Button>
        </div>
      )}

      {/* Tree */}
      <ScrollArea className="flex-1">
        {filteredItems.length === 0 ? (
          <EmptyState onCreate={onCreateNote} />
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={flattenedIds} strategy={verticalListSortingStrategy}>
              <div className="p-1">
                {filteredItems.map((item) => (
                  <SortableTreeItem
                    key={item.id}
                    item={item}
                    isSelected={selectedNoteId === item.id}
                    workspaceSlug={workspaceSlug}
                    onSelect={() => onSelect?.(item.id)}
                    onDelete={onDelete ? () => onDelete(item.id) : undefined}
                    onDuplicate={onDuplicate ? () => onDuplicate(item.id) : undefined}
                    onTogglePin={onTogglePin ? () => onTogglePin(item.id) : undefined}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </ScrollArea>
    </div>
  );
});

export default OutlineTree;
