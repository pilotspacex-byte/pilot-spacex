'use client';

/**
 * TopicTreeRow — single row in the sidebar topic tree (Phase 93 Plan 04 Task 2).
 *
 * Renders one topic with:
 *   - chevron toggle (12×12, aria-label "Expand/Collapse {title}")
 *   - 14×14 FileText icon (Lucide — never custom SVG, per icons.md)
 *   - 13/500 truncating title (italic "Untitled" placeholder when empty)
 *   - paddingLeft = 8 + depth × 16 (UI-SPEC §Surface 1)
 *   - active-route highlight via usePathname() === /{slug}/topics/{id}
 *   - useSortable wiring so the row is draggable inside DndContext
 *   - onContextMenu prop pass-through (93-05 plugs in the Move-to picker)
 *
 * Drop indicator is rendered by TopicTreeContainer (Decision Q), NOT here —
 * keeping this component a single render-pass with no per-row indicator
 * layout thrash.
 */

import { observer } from 'mobx-react-lite';
import { useParams, usePathname } from 'next/navigation';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ChevronRight, FileText } from 'lucide-react';
import type React from 'react';
import { cn } from '@/lib/utils';
import type { Note } from '@/types';
import { topicTreeStore } from '../stores/TopicTreeStore';

export interface TopicTreeRowProps {
  note: Note;
  /** Depth from the tree root — drives the indent. Provided by TopicTreeContainer. */
  depth: number;
  /** 93-05 hook: open the right-click "Move to…" picker. Default no-op. */
  onContextMenu?: (event: React.MouseEvent, note: Note) => void;
}

export const TopicTreeRow = observer(function TopicTreeRow({
  note,
  depth,
  onContextMenu,
}: TopicTreeRowProps) {
  const pathname = usePathname();
  const params = useParams<{ workspaceSlug?: string }>();
  const workspaceSlug = params?.workspaceSlug ?? '';

  const { setNodeRef, listeners, attributes, transform, transition, isDragging } = useSortable({
    id: note.id,
    data: { note },
  });

  const isExpanded = topicTreeStore.isExpanded(note.id);
  const indent = 8 + depth * 16;
  const title = note.title?.trim() ?? '';
  const displayTitle = title.length > 0 ? title : 'Untitled';

  // Active route match — exact path equality is enough; deeper segments
  // (e.g. `/{slug}/topics/{id}/edit`) still highlight the parent topic.
  const expectedPath = `/${workspaceSlug}/topics/${note.id}`;
  const isActive = pathname === expectedPath || pathname.startsWith(`${expectedPath}/`);

  return (
    <div
      ref={setNodeRef}
      data-testid={`topic-tree-row-${note.id}`}
      {...attributes}
      {...listeners}
      onContextMenu={(e) => {
        if (onContextMenu) onContextMenu(e, note);
      }}
      style={{
        paddingLeft: `${indent}px`,
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={cn(
        'group relative flex items-center gap-1.5 h-8 pr-2 text-[13px] font-medium',
        'motion-safe:transition-colors motion-safe:duration-150',
        'outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1',
        isActive
          ? 'bg-[color-mix(in_srgb,var(--brand-primary)_8%,transparent)] text-[var(--brand-primary)] font-semibold'
          : 'text-[var(--text-heading)] hover:bg-[var(--surface-input)]/60',
        isDragging && 'opacity-60',
      )}
      aria-current={isActive ? 'page' : undefined}
      aria-level={depth + 1}
      aria-label={displayTitle}
    >
      <button
        type="button"
        aria-label={isExpanded ? `Collapse ${displayTitle}` : `Expand ${displayTitle}`}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          topicTreeStore.toggle(note.id);
        }}
        // pointerDown stops the dnd listeners from grabbing the chevron click.
        onPointerDown={(e) => e.stopPropagation()}
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-[var(--text-muted)] hover:text-[var(--text-heading)]"
      >
        <ChevronRight
          className={cn(
            'h-3 w-3 motion-safe:transition-transform motion-safe:duration-150',
            isExpanded && 'rotate-90',
          )}
          aria-hidden="true"
        />
      </button>

      <FileText
        className={cn(
          'h-3.5 w-3.5 shrink-0',
          isActive ? 'text-[var(--brand-primary)]' : 'text-[var(--text-muted)]',
        )}
        aria-hidden="true"
      />

      <span className="flex-1 truncate">
        {title.length > 0 ? (
          title
        ) : (
          <span className="italic text-[var(--text-muted)]">Untitled</span>
        )}
      </span>
    </div>
  );
});
