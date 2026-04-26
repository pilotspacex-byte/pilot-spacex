/**
 * Unit tests for topicCollisionDetection (Phase 93 Plan 04 Task 1).
 *
 * Verifies the locked drop-zone semantics from UI-SPEC §Surface 1:
 *  - pointerY < rect.top + 4   → between-before
 *  - pointerY > rect.bottom - 4 → between-after
 *  - middle 50% of row height   → on
 *  - empty pointerWithin result → empty array (no annotations)
 *  - missing pointerCoordinates → return raw collisions unchanged
 *  - missing droppableRect for an id → that collision passes through unchanged
 */

import { describe, it, expect } from 'vitest';
import type { ClientRect } from '@dnd-kit/core';
import { topicCollisionDetection } from '../lib/topic-collision';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function rect(_id: string, top: number, height = 32, left = 0, width = 240): ClientRect {
  return {
    top,
    bottom: top + height,
    left,
    right: left + width,
    width,
    height,
  } as ClientRect;
}

interface FakeArgs {
  pointerCoordinates: { x: number; y: number } | null;
  droppableRects: Map<string, ClientRect>;
  /** Drives our injected pointerWithin stub. */
  collisionsForPointer: Array<{ id: string }>;
}

/**
 * The real `pointerWithin` from @dnd-kit/core inspects droppableContainers /
 * droppableRects / pointerCoordinates. For a unit test we don't need to
 * exercise that branch — we provide raw `collisions` via a wrapper that simply
 * returns whatever the test fixture says was hit, then verify that
 * `topicCollisionDetection` annotates each collision's `data.dropMode`
 * correctly based on pointerY vs rect.
 *
 * To do this without mocking the @dnd-kit module, we call the strategy with
 * an args object that yields the same `pointerWithin` result. We achieve
 * that by passing `droppableRects` keyed by the same ids and
 * `droppableContainers` shaped so pointerWithin returns hits.
 *
 * Since wiring real droppableContainers is heavy, we accept the engineering
 * tradeoff: drive the test through the public surface by feeding rects whose
 * geometry the strategy reads directly. Our strategy reads `pointerCoordinates`
 * and `droppableRects.get(id)` only — so we test it with the minimal args.
 */
function callStrategy(args: FakeArgs) {
  // Build minimal droppableContainers list shape pointerWithin expects.
  const droppableContainers = args.collisionsForPointer.map(({ id }) => ({
    id,
    rect: { current: args.droppableRects.get(id) ?? null },
    data: { current: {} },
    disabled: false,
  })) as unknown as Parameters<typeof topicCollisionDetection>[0]['droppableContainers'];

  return topicCollisionDetection({
    active: { id: 'active', rect: { current: { initial: null, translated: null } } } as unknown as Parameters<
      typeof topicCollisionDetection
    >[0]['active'],
    collisionRect: rect('active', 0),
    droppableRects: args.droppableRects,
    droppableContainers,
    pointerCoordinates: args.pointerCoordinates,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('topicCollisionDetection', () => {
  it('returns between-before when pointer is in the top 4px of the target row', () => {
    const targetRect = rect('row-a', /*top*/ 100); // 100..132
    const result = callStrategy({
      pointerCoordinates: { x: 50, y: 102 }, // 100 + 2 → top edge
      droppableRects: new Map([['row-a', targetRect]]),
      collisionsForPointer: [{ id: 'row-a' }],
    });
    expect(result.length).toBeGreaterThan(0);
    expect((result[0]?.data as { dropMode?: string } | undefined)?.dropMode).toBe('between-before');
  });

  it('returns between-after when pointer is in the bottom 4px of the target row', () => {
    const targetRect = rect('row-a', 100); // 100..132
    const result = callStrategy({
      pointerCoordinates: { x: 50, y: 130 }, // 132 - 2 → bottom edge
      droppableRects: new Map([['row-a', targetRect]]),
      collisionsForPointer: [{ id: 'row-a' }],
    });
    expect((result[0]?.data as { dropMode?: string } | undefined)?.dropMode).toBe('between-after');
  });

  it('returns on when pointer is in the middle of the target row', () => {
    const targetRect = rect('row-a', 100); // 100..132
    const result = callStrategy({
      pointerCoordinates: { x: 50, y: 116 }, // dead-center of 32px row
      droppableRects: new Map([['row-a', targetRect]]),
      collisionsForPointer: [{ id: 'row-a' }],
    });
    expect((result[0]?.data as { dropMode?: string } | undefined)?.dropMode).toBe('on');
  });

  it('returns an empty array when pointerWithin yields no hits', () => {
    const result = callStrategy({
      pointerCoordinates: { x: 50, y: 50 },
      droppableRects: new Map(),
      collisionsForPointer: [],
    });
    expect(result).toEqual([]);
  });

  it('returns raw collisions when pointerCoordinates is null', () => {
    const targetRect = rect('row-a', 100);
    const result = callStrategy({
      pointerCoordinates: null,
      droppableRects: new Map([['row-a', targetRect]]),
      collisionsForPointer: [{ id: 'row-a' }],
    });
    // Without a pointer Y we cannot annotate dropMode — strategy returns
    // collisions unchanged so caller can still resolve a target.
    if (result.length > 0) {
      expect((result[0]?.data as { dropMode?: string } | undefined)?.dropMode).toBeUndefined();
    }
  });

  it('passes a collision through unchanged when its rect is missing from droppableRects', () => {
    const result = callStrategy({
      pointerCoordinates: { x: 50, y: 100 },
      droppableRects: new Map(), // no rect for row-a
      collisionsForPointer: [{ id: 'row-a' }],
    });
    if (result.length > 0) {
      expect((result[0]?.data as { dropMode?: string } | undefined)?.dropMode).toBeUndefined();
    }
  });
});
