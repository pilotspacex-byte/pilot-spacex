'use client';

/**
 * TopicTreeStore — MobX observable for sidebar topic-tree UI state.
 *
 * Phase 93 Plan 04 Task 1. State scope is intentionally narrow:
 *  - `expanded`: Set of topic ids whose children are visible in the sidebar.
 *  - `dragSourceId / dropTargetId / dropMode`: transient drag state surfaced
 *    to TopicTreeContainer so it can render the single absolutely-positioned
 *    drop indicator (Decision Q).
 *
 * NOT a TanStack-cache replacement — children/ancestor data still come from
 * `useTopicChildren` / `useTopicAncestors` (Plan 93-03). This store only
 * holds *UI* state (what's expanded; what the drag is targeting).
 *
 * Singleton export (`topicTreeStore`) is shared across the sidebar so
 * navigation between pages doesn't reset expansion state.
 */

import { makeAutoObservable } from 'mobx';

export type DropMode = 'between-before' | 'between-after' | 'on';

export class TopicTreeStore {
  expanded: Set<string> = new Set<string>();

  dragSourceId: string | null = null;
  dropTargetId: string | null = null;
  dropMode: DropMode | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  // ---- Expansion --------------------------------------------------------

  isExpanded(id: string): boolean {
    return this.expanded.has(id);
  }

  toggle(id: string): void {
    if (this.expanded.has(id)) {
      this.expanded.delete(id);
    } else {
      this.expanded.add(id);
    }
  }

  expand(id: string): void {
    this.expanded.add(id);
  }

  collapse(id: string): void {
    this.expanded.delete(id);
  }

  // ---- Drag state -------------------------------------------------------

  beginDrag(id: string): void {
    this.dragSourceId = id;
  }

  setDropTarget(id: string | null, mode: DropMode | null): void {
    this.dropTargetId = id;
    this.dropMode = mode;
  }

  endDrag(): void {
    this.dragSourceId = null;
    this.dropTargetId = null;
    this.dropMode = null;
  }
}

/**
 * Sidebar-wide singleton. The tree is rendered in exactly one place
 * (`TopicTreeContainer` mounted from `sidebar.tsx`), so a singleton is
 * sufficient and matches the "navigation doesn't collapse the tree"
 * requirement (Decision N implication).
 */
export const topicTreeStore = new TopicTreeStore();
