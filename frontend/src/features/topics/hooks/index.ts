/**
 * Barrel exports for topic-tree TanStack hooks (Phase 93 Plan 03).
 *
 * Consumers (93-04 sidebar tree, 93-05 breadcrumb + move picker) import from
 * here so the hook surface stays decoupled from the underlying notesApi layer.
 */

export { useTopicChildren } from './useTopicChildren';
export { useTopicAncestors } from './useTopicAncestors';
export { useMoveTopic, type MoveTopicError, type MoveTopicVars } from './useMoveTopic';
export { useTopicsForMove } from './useTopicsForMove';

// Re-export the key factory for downstream cache-aware consumers.
export { topicTreeKeys } from '../lib/topic-tree-keys';
