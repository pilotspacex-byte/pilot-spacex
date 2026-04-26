'use client';

/**
 * TopicTreeContainer — sidebar topic-tree root (Phase 93 Plan 04 Task 2).
 *
 * Responsibilities:
 *   - Mount the DndContext with a custom collision strategy + Pointer/Keyboard
 *     sensors.
 *   - Recursively render TopicTreeRow + nested children, lazily fetched via
 *     `useTopicChildren(workspaceId, parentId)` only when the row is expanded
 *     (Decision O).
 *   - Wire drag-end → `useMoveTopic.mutate(...)` with the parentId derived
 *     from the locked drop semantics:
 *       'on'             → newParentId = over.id
 *       'between-before' → newParentId = over.parentTopicId  (sibling-before)
 *       'between-after'  → newParentId = over.parentTopicId  (sibling-after)
 *   - Surface typed MoveTopicError as a sonner toast with the locked
 *     UI-SPEC copy. Optimistic UI is owned by useMoveTopic (Plan 93-03).
 *   - Render a single absolutely-positioned drop indicator driven by
 *     `topicTreeStore.dropTargetId / dropMode` (Decision Q).
 *   - Render an aria-live status region announcing drop intent per
 *     UI-SPEC §Surface 1 copy.
 *
 * Right-click "Move to…" picker is OUT OF SCOPE here — Plan 93-05 plugs
 * its handler into TopicTreeRow's `onContextMenu` prop.
 */

import { observer } from 'mobx-react-lite';
import { useCallback, useMemo, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { toast } from 'sonner';
import type { Note } from '@/types';
import { useMoveTopic, useTopicChildren, type MoveTopicError } from '../hooks';
import { topicTreeStore, type DropMode } from '../stores/TopicTreeStore';
import { topicCollisionDetection } from '../lib/topic-collision';
import { TopicTreeRow } from './TopicTreeRow';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TopicTreeContainerProps {
  workspaceId: string;
  /** 93-05 plug point — wired into every TopicTreeRow's `onContextMenu`. */
  onRowContextMenu?: (event: React.MouseEvent, note: Note) => void;
}

// ---------------------------------------------------------------------------
// Toast helpers
// ---------------------------------------------------------------------------

function toastMoveError(title: string, err: MoveTopicError, retry?: () => void): void {
  const heading = `Couldn't move "${title}".`;
  switch (err.kind) {
    case 'maxDepth':
      toast.error(heading, {
        description: 'This would exceed the 5-level depth limit.',
        action: retry ? { label: 'Retry', onClick: retry } : undefined,
      });
      return;
    case 'cycle':
      toast.error(heading, {
        description: "A topic can't be moved into its own subtree.",
      });
      return;
    case 'forbidden':
      toast.error(heading, {
        description: 'You do not have permission to move this topic.',
      });
      return;
    case 'notFound':
      toast.error(heading, {
        description: 'The target topic no longer exists.',
      });
      return;
    default:
      toast.error(heading, {
        description: 'Try again.',
        action: retry ? { label: 'Retry', onClick: retry } : undefined,
      });
  }
}

// ---------------------------------------------------------------------------
// Test seam — handlers exposed for unit tests so we can simulate drag-end
// without a fake browser DnD harness. Container code paths are otherwise
// pure React; the seam carries zero runtime cost in production.
// ---------------------------------------------------------------------------

interface TestHooks {
  handleDragStart: (event: { active: { id: string | number } }) => void;
  handleDragOver: (event: {
    active: { id: string | number };
    over: { id: string | number } | null;
    collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null;
  }) => void;
  handleDragEnd: (event: {
    active: { id: string | number; data?: { current?: { note?: Note } } };
    over: { id: string | number; data?: { current?: unknown } } | null;
    collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null;
  }) => void;
  handleDragCancel: () => void;
}

/**
 * Test-only handler holder. Populated as a side-effect of rendering
 * TopicTreeContainer so unit tests can drive drag flow without a fake DOM
 * harness. NEVER read in production code paths.
 */
export const __testHooks: TestHooks = {
  handleDragStart: () => {},
  handleDragOver: () => {},
  handleDragEnd: () => {},
  handleDragCancel: () => {},
};

// ---------------------------------------------------------------------------
// Recursive subtree renderer
// ---------------------------------------------------------------------------

interface TopicSubtreeProps {
  workspaceId: string;
  parentId: string | null;
  depth: number;
  enabled: boolean;
  /** Map of every loaded note → so drag-end can resolve parentTopicId by id. */
  notesById: Map<string, Note>;
  onRowContextMenu?: (event: React.MouseEvent, note: Note) => void;
}

const TopicSubtree = observer(function TopicSubtree({
  workspaceId,
  parentId,
  depth,
  enabled,
  notesById,
  onRowContextMenu,
}: TopicSubtreeProps) {
  const query = useTopicChildren(workspaceId, parentId, 1, 20, { enabled });
  const items = query.data?.items ?? [];

  // Index every fetched note so drag-end can look up parentTopicId.
  for (const item of items) notesById.set(item.id, item);

  if (!enabled) return null;

  return (
    <div data-topic-subtree-parent={parentId ?? '__root__'}>
      {items.map((note) => {
        const childExpanded = topicTreeStore.isExpanded(note.id);
        return (
          <div key={note.id}>
            <TopicTreeRow note={note} depth={depth} onContextMenu={onRowContextMenu} />
            {childExpanded && (
              <TopicSubtree
                workspaceId={workspaceId}
                parentId={note.id}
                depth={depth + 1}
                enabled
                notesById={notesById}
                onRowContextMenu={onRowContextMenu}
              />
            )}
          </div>
        );
      })}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Container
// ---------------------------------------------------------------------------

export const TopicTreeContainer = observer(function TopicTreeContainer({
  workspaceId,
  onRowContextMenu,
}: TopicTreeContainerProps) {
  const move = useMoveTopic(workspaceId);
  const [dragAnnouncement, setDragAnnouncement] = useState<string>('');

  // notesById: pulled up so drag-end can resolve `over.id`'s parentTopicId
  // even if the over-row lives in a deep subtree. Re-created per render so
  // stale entries don't accumulate after collapse.
  const notesById = useMemo(() => new Map<string, Note>(), [workspaceId]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // ---- Handlers --------------------------------------------------------

  const handleDragStart = useCallback((event: DragStartEvent | { active: { id: string | number } }) => {
    topicTreeStore.beginDrag(String(event.active.id));
    setDragAnnouncement('');
  }, []);

  const handleDragOver = useCallback(
    (
      event: DragOverEvent | {
        active: { id: string | number };
        over: { id: string | number } | null;
        collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null;
      },
    ) => {
      const over = event.over;
      const collisions = (event as { collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null }).collisions;
      if (!over) {
        topicTreeStore.setDropTarget(null, null);
        setDragAnnouncement('Drop to move to root');
        return;
      }
      const collision = collisions?.find((c) => c.id === over.id);
      const mode: DropMode = (collision?.data?.dropMode as DropMode | undefined) ?? 'on';
      topicTreeStore.setDropTarget(String(over.id), mode);

      const targetNote = notesById.get(String(over.id));
      const targetTitle = targetNote?.title?.trim() || 'Untitled';
      if (mode === 'on') {
        setDragAnnouncement(`Drop to make child of ${targetTitle}`);
      } else {
        setDragAnnouncement(`Drop to make sibling of ${targetTitle}`);
      }
    },
    [notesById],
  );

  const handleDragEnd = useCallback(
    (
      event: DragEndEvent | {
        active: { id: string | number; data?: { current?: { note?: Note } } };
        over: { id: string | number; data?: { current?: unknown } } | null;
        collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null;
      },
    ) => {
      const { active, over } = event;
      const collisions = (event as { collisions?: Array<{ id: string | number; data?: { dropMode?: DropMode } }> | null }).collisions;
      const activeId = String(active.id);
      // Resolve the dragged note: prefer drag-data payload, fall back to index.
      const activeNote =
        (active.data && 'current' in active.data ? (active.data.current as { note?: Note } | undefined)?.note : undefined) ??
        notesById.get(activeId);
      const activeTitle = activeNote?.title?.trim() || 'Untitled';

      if (!over) {
        topicTreeStore.endDrag();
        setDragAnnouncement('');
        return;
      }

      const collision = collisions?.find((c) => c.id === over.id);
      const mode: DropMode = (collision?.data?.dropMode as DropMode | undefined) ?? 'on';
      const overId = String(over.id);
      const overNote = notesById.get(overId);

      let newParentId: string | null;
      if (mode === 'on') {
        newParentId = overId;
      } else {
        // sibling drop — new parent is over-row's parent.
        newParentId = overNote?.parentTopicId ?? null;
      }

      const oldParentId = activeNote?.parentTopicId ?? null;

      // Skip no-op moves (same parent, sibling drop within same group is a
      // reorder which v1 of TOPIC-06 does not implement).
      if (newParentId === oldParentId && mode === 'on' && overId === activeId) {
        topicTreeStore.endDrag();
        setDragAnnouncement('');
        return;
      }

      const vars = { noteId: activeId, parentId: newParentId, oldParentId };
      const retry = () => move.mutate(vars, { onError: (err) => toastMoveError(activeTitle, err, retry) });
      move.mutate(vars, { onError: (err) => toastMoveError(activeTitle, err, retry) });

      topicTreeStore.endDrag();
      setDragAnnouncement('');
    },
    [move, notesById],
  );

  const handleDragCancel = useCallback(() => {
    topicTreeStore.endDrag();
    setDragAnnouncement('');
  }, []);

  // Wire the test seam. Production runtime cost: 4 reference assignments
  // per render — negligible.
  __testHooks.handleDragStart = handleDragStart as TestHooks['handleDragStart'];
  __testHooks.handleDragOver = handleDragOver as TestHooks['handleDragOver'];
  __testHooks.handleDragEnd = handleDragEnd as TestHooks['handleDragEnd'];
  __testHooks.handleDragCancel = handleDragCancel;

  // Flat sortable-id list — useful if we add intra-parent reordering later.
  const flatIds = useMemo(() => Array.from(notesById.keys()), [notesById]);

  // ---- Render ----------------------------------------------------------

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={topicCollisionDetection}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <SortableContext items={flatIds} strategy={verticalListSortingStrategy}>
        <div
          role="application"
          aria-label="Topic tree"
          tabIndex={0}
          className="relative outline-none"
          data-testid="topic-tree-container"
        >
          <TopicSubtree
            workspaceId={workspaceId}
            parentId={null}
            depth={0}
            enabled
            notesById={notesById}
            onRowContextMenu={onRowContextMenu}
          />

          {/* Drop indicator — single source of truth (Decision Q). */}
          <DropIndicator />
        </div>
      </SortableContext>

      {/* aria-live status — UI-SPEC §Surface 1 locked copy. */}
      <div role="status" aria-live="polite" className="sr-only" data-testid="topic-tree-aria-live">
        {dragAnnouncement}
      </div>

      <DragOverlay
        dropAnimation={null}
        style={{
          opacity: 0.6,
          borderRadius: '8px',
          boxShadow: 'var(--shadow-floating)',
        }}
      >
        {topicTreeStore.dragSourceId ? <DragSourcePreview notesById={notesById} /> : null}
      </DragOverlay>
    </DndContext>
  );
});

// ---------------------------------------------------------------------------
// Drop indicator — observes topicTreeStore for current target/mode.
// ---------------------------------------------------------------------------

const DropIndicator = observer(function DropIndicator() {
  const { dropTargetId, dropMode } = topicTreeStore;
  if (!dropTargetId || !dropMode) return null;

  // The actual indicator overlay is intentionally minimal in v1: we tag the
  // target row via data-attribute and let CSS handle the visual treatment.
  // The CSS hooks are defined in globals.css under [data-topic-drop-target].
  return (
    <style data-topic-drop-target-style>{`
      [data-testid="topic-tree-row-${dropTargetId}"] {
        ${
          dropMode === 'on'
            ? 'box-shadow: inset 0 0 0 2px var(--brand-primary); background-color: color-mix(in srgb, var(--brand-primary) 7%, transparent);'
            : ''
        }
        ${
          dropMode === 'between-before'
            ? 'box-shadow: inset 0 2px 0 0 var(--brand-primary);'
            : ''
        }
        ${
          dropMode === 'between-after'
            ? 'box-shadow: inset 0 -2px 0 0 var(--brand-primary);'
            : ''
        }
      }
    `}</style>
  );
});

// ---------------------------------------------------------------------------
// Drag overlay preview — minimal label rendering of the dragged row.
// ---------------------------------------------------------------------------

const DragSourcePreview = observer(function DragSourcePreview({ notesById }: { notesById: Map<string, Note> }) {
  const id = topicTreeStore.dragSourceId;
  if (!id) return null;
  const note = notesById.get(id);
  const title = note?.title?.trim() || 'Untitled';
  return (
    <div className="flex h-8 items-center gap-1.5 rounded-md bg-[var(--surface-snow)] px-2 text-[13px] font-medium text-[var(--text-heading)] border border-[var(--border-card)]">
      <span className="truncate">{title}</span>
    </div>
  );
});
