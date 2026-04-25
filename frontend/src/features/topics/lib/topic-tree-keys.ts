/**
 * TanStack Query key factory for the topic-tree feature (Phase 93).
 *
 * Key shape (locked by Plan 93-03 Decision I):
 *   - all(workspaceId)                 → ['topics', workspaceId]
 *   - children(workspaceId, parentId, page=1)
 *                                      → ['topics', workspaceId, 'children', parentId ?? '__root__', page]
 *   - ancestors(workspaceId, noteId)   → ['topics', workspaceId, 'ancestors', noteId]
 *
 * The `__root__` sentinel disambiguates the root listing from a missing
 * parent reference inside the cache key — `null` and `undefined` would both
 * collapse to the same string segment otherwise.
 *
 * Consumers:
 *   - useTopicChildren / useTopicAncestors / useMoveTopic (this plan)
 *   - 93-04 sidebar tree, 93-05 breadcrumb + move picker (downstream UI)
 */

export const topicTreeKeys = {
  /** Root scope — invalidate this to refresh every topic-tree query in the workspace. */
  all: (workspaceId: string) => ['topics', workspaceId] as const,

  /**
   * Paginated children of a parent topic. `parentId === null` lists root topics
   * (collapsed under the `__root__` sentinel for cache-key stability).
   */
  children: (workspaceId: string, parentId: string | null, page: number = 1) =>
    ['topics', workspaceId, 'children', parentId ?? '__root__', page] as const,

  /** Root → leaf chain for a given note (includes self per backend contract). */
  ancestors: (workspaceId: string, noteId: string) =>
    ['topics', workspaceId, 'ancestors', noteId] as const,
} as const;

export type TopicTreeKeys = typeof topicTreeKeys;
