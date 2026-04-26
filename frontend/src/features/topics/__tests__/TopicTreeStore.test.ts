/**
 * Unit tests for TopicTreeStore (Phase 93 Plan 04 Task 1).
 *
 * Verifies the MobX-observable expansion + drag-state surface used by the
 * sidebar tree. Pure logic — no React.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { TopicTreeStore } from '../stores/TopicTreeStore';

describe('TopicTreeStore', () => {
  let store: TopicTreeStore;

  beforeEach(() => {
    store = new TopicTreeStore();
  });

  it('toggles expansion state for an id', () => {
    expect(store.isExpanded('a')).toBe(false);
    store.toggle('a');
    expect(store.isExpanded('a')).toBe(true);
    store.toggle('a');
    expect(store.isExpanded('a')).toBe(false);
  });

  it('expand and collapse are idempotent', () => {
    store.expand('a');
    store.expand('a');
    expect(store.isExpanded('a')).toBe(true);
    store.collapse('a');
    store.collapse('a');
    expect(store.isExpanded('a')).toBe(false);
  });

  it('tracks drag source via beginDrag and clears it via endDrag', () => {
    expect(store.dragSourceId).toBeNull();
    store.beginDrag('row-1');
    expect(store.dragSourceId).toBe('row-1');
    store.endDrag();
    expect(store.dragSourceId).toBeNull();
    expect(store.dropTargetId).toBeNull();
    expect(store.dropMode).toBeNull();
  });

  it('setDropTarget assigns target id and mode atomically', () => {
    store.setDropTarget('row-2', 'on');
    expect(store.dropTargetId).toBe('row-2');
    expect(store.dropMode).toBe('on');

    store.setDropTarget('row-3', 'between-before');
    expect(store.dropTargetId).toBe('row-3');
    expect(store.dropMode).toBe('between-before');

    store.setDropTarget(null, null);
    expect(store.dropTargetId).toBeNull();
    expect(store.dropMode).toBeNull();
  });

  it('endDrag clears all drag-related state in one shot', () => {
    store.beginDrag('row-1');
    store.setDropTarget('row-2', 'between-after');
    store.endDrag();
    expect(store.dragSourceId).toBeNull();
    expect(store.dropTargetId).toBeNull();
    expect(store.dropMode).toBeNull();
  });
});
