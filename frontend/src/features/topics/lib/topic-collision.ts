'use client';

/**
 * topicCollisionDetection — custom @dnd-kit/core collision strategy that
 * distinguishes between three drop intents per UI-SPEC §Surface 1 (Phase 93
 * Plan 04 Decision Q):
 *
 *   - top-edge 4px of a row → "between-before" (insert as previous sibling)
 *   - bottom-edge 4px       → "between-after"  (insert as next sibling)
 *   - middle of the row     → "on"             (re-parent under target)
 *
 * Implementation: delegate to `pointerWithin` for the base hit-test, then
 * annotate each collision with `data.dropMode` derived from the pointer's
 * Y coordinate vs. the target row rect. The container reads this annotation
 * to drive the indicator + the moveTopic mutation parent derivation.
 *
 * Decision Q: drop indicator is rendered ONCE by TopicTreeContainer (not per
 * row) by reading `topicTreeStore.dropTargetId / dropMode`. This strategy is
 * the source-of-truth for those values via DndContext `onDragOver`.
 */

import { pointerWithin, type CollisionDetection } from '@dnd-kit/core';

/** Pixels from the top of the row where a hit reads as `between-before`. */
export const TOP_EDGE_PX = 4;
/** Pixels from the bottom of the row where a hit reads as `between-after`. */
export const BOTTOM_EDGE_PX = 4;

export const topicCollisionDetection: CollisionDetection = (args) => {
  const collisions = pointerWithin(args);
  if (collisions.length === 0) return collisions;

  const pointerY = args.pointerCoordinates?.y;
  if (pointerY === undefined || pointerY === null) {
    // Without a pointer Y we cannot annotate dropMode — surface raw
    // collisions so callers can still resolve a target.
    return collisions;
  }

  return collisions.map((collision) => {
    const rect = args.droppableRects.get(collision.id);
    if (!rect) return collision;

    let mode: 'between-before' | 'between-after' | 'on' = 'on';
    if (pointerY < rect.top + TOP_EDGE_PX) {
      mode = 'between-before';
    } else if (pointerY > rect.bottom - BOTTOM_EDGE_PX) {
      mode = 'between-after';
    }

    return {
      ...collision,
      data: { ...collision.data, dropMode: mode },
    };
  });
};
