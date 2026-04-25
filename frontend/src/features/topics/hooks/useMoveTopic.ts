'use client';

/**
 * useMoveTopic — TanStack mutation hook implementing Plan 93-03 Decision J:
 * dual-key optimistic write across the OLD parent's children list and the NEW
 * parent's children list, with snapshot rollback on error AND a discriminated
 * MoveTopicError union so 93-04 / 93-05 UI can branch on cause without
 * re-parsing the RFC 7807 problem body.
 *
 * Pitfalls guarded:
 *  - Per UI-SPEC §Design-Debt 7: snapshot BOTH children lists; restore BOTH on error.
 *  - Per CLAUDE.md design rule: ApiError errorCode is the single source for error
 *    discrimination — wire field is snake_case `error_code`, exposed as camelCase
 *    `errorCode` by ApiError.
 *  - onSettled invalidates the entire topic-tree scope so success-path stale data
 *    (e.g. ancestors, sibling lists on other pages) is reconciled.
 */

import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';
import { notesApi } from '@/services/api';
import { ApiError } from '@/services/api/client';
import type { Note } from '@/types';
import type { PaginatedResponse } from '@/services/api/client';
import { topicTreeKeys } from '../lib/topic-tree-keys';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type MoveTopicError =
  | { kind: 'maxDepth' }
  | { kind: 'cycle' }
  | { kind: 'notFound' }
  | { kind: 'forbidden' }
  | { kind: 'unknown'; original: unknown };

export interface MoveTopicVars {
  noteId: string;
  parentId: string | null;
  oldParentId: string | null;
}

interface MoveTopicCtx {
  /** Snapshots of every (queryKey, data) pair we touched, for blanket restore. */
  snapshots: Array<readonly [QueryKey, unknown]>;
}

// ---------------------------------------------------------------------------
// Error mapping
// ---------------------------------------------------------------------------

function mapToMoveTopicError(err: unknown): MoveTopicError {
  if (err instanceof ApiError) {
    switch (err.errorCode) {
      case 'topic_max_depth_exceeded':
        return { kind: 'maxDepth' };
      case 'topic_cycle_rejected':
        return { kind: 'cycle' };
      case 'topic_not_found':
      case 'parent_not_found':
        return { kind: 'notFound' };
      case 'cross_workspace_move':
        return { kind: 'forbidden' };
      default:
        // Status-only fallback (no error_code on the wire).
        if (err.status === 404) return { kind: 'notFound' };
        if (err.status === 403) return { kind: 'forbidden' };
        return { kind: 'unknown', original: err };
    }
  }
  // Duck-typed ApiError-like — used in tests where a plain object carries the
  // ApiError shape without going through axios. Status + errorCode resolved
  // identically to the instance branch above.
  if (typeof err === 'object' && err !== null) {
    const candidate = err as { errorCode?: unknown; status?: unknown };
    const code = typeof candidate.errorCode === 'string' ? candidate.errorCode : undefined;
    const status = typeof candidate.status === 'number' ? candidate.status : undefined;
    if (code === 'topic_max_depth_exceeded') return { kind: 'maxDepth' };
    if (code === 'topic_cycle_rejected') return { kind: 'cycle' };
    if (code === 'topic_not_found' || code === 'parent_not_found') return { kind: 'notFound' };
    if (code === 'cross_workspace_move') return { kind: 'forbidden' };
    if (status === 404) return { kind: 'notFound' };
    if (status === 403) return { kind: 'forbidden' };
  }
  return { kind: 'unknown', original: err };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMoveTopic(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation<Note, MoveTopicError, MoveTopicVars, MoveTopicCtx>({
    // Wrap the API call so the mutation surfaces a typed error from the start.
    mutationFn: async (vars) => {
      try {
        return await notesApi.moveTopic(workspaceId, vars.noteId, vars.parentId);
      } catch (err) {
        throw mapToMoveTopicError(err);
      }
    },

    onMutate: async (vars) => {
      const oldKey = topicTreeKeys.children(workspaceId, vars.oldParentId, 1);
      const newKey = topicTreeKeys.children(workspaceId, vars.parentId, 1);

      // Cancel any in-flight refetches that could clobber the optimistic write.
      await Promise.all([
        queryClient.cancelQueries({ queryKey: oldKey }),
        queryClient.cancelQueries({ queryKey: newKey }),
      ]);

      // Capture every page-keyed variant matching each prefix so multi-page caches
      // round-trip cleanly. The prefix is everything up to and including the parent
      // segment (drops the trailing page index — same prefix for any page).
      const oldPrefix = oldKey.slice(0, 4);
      const newPrefix = newKey.slice(0, 4);
      const oldSnapshots = queryClient.getQueriesData({ queryKey: oldPrefix });
      const newSnapshots = queryClient.getQueriesData({ queryKey: newPrefix });
      const snapshots: Array<readonly [QueryKey, unknown]> = [
        ...oldSnapshots,
        ...newSnapshots,
      ];

      // Optimistic write — only mutate caches that already have data; skip otherwise
      // so the next genuine fetch can populate naturally.
      const oldList = queryClient.getQueryData<PaginatedResponse<Note>>(oldKey);
      const newList = queryClient.getQueryData<PaginatedResponse<Note>>(newKey);

      let movedItem: Note | null = null;
      if (oldList) {
        const removedItems = oldList.items.filter((n) => n.id !== vars.noteId);
        movedItem = oldList.items.find((n) => n.id === vars.noteId) ?? null;
        queryClient.setQueryData<PaginatedResponse<Note>>(oldKey, {
          ...oldList,
          items: removedItems,
          total: Math.max(0, oldList.total - (removedItems.length === oldList.items.length ? 0 : 1)),
        });
      }

      if (newList && movedItem) {
        // Insert at top of new parent (page=1) — matches UI-SPEC v1 expectations.
        const projected: Note = {
          ...movedItem,
          parentTopicId: vars.parentId,
        };
        queryClient.setQueryData<PaginatedResponse<Note>>(newKey, {
          ...newList,
          items: [projected, ...newList.items.filter((n) => n.id !== vars.noteId)],
          total: newList.total + 1,
        });
      }

      return { snapshots };
    },

    onError: (_err, _vars, ctx) => {
      // Restore every snapshot we captured, regardless of whether we mutated it
      // (idempotent; setting the same data is a no-op).
      ctx?.snapshots.forEach(([key, data]) => {
        queryClient.setQueryData(key, data);
      });
    },

    onSettled: () => {
      // Reconcile the entire topic-tree scope (ancestors + every children page).
      queryClient.invalidateQueries({ queryKey: topicTreeKeys.all(workspaceId) });
    },
  });
}
