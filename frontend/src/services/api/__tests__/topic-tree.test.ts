/**
 * Tests for topic-tree additions to `notesApi` (Phase 93 Plan 03 Task 1).
 *
 * Coverage targets:
 *  - `listChildren()` calls /workspaces/{ws}/notes/{id}/children with page/page_size.
 *  - `listAncestors()` calls /workspaces/{ws}/notes/{id}/ancestors.
 *  - `moveTopic()` posts camelCase `{ parentId }` per BaseSchema alias contract (93-02 SUMMARY).
 *  - `moveTopic()` serializes a `null` parentId for the root-move case.
 *  - `moveTopic()` propagates ApiError on 409 problem+json with `error_code` exposed via `errorCode`.
 *
 * Mock harness mirrors `skills.test.ts` — vi.mock the client module, dynamic-import the
 * notes module inside each test so module init re-runs against the mocked client.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock('../client', async () => {
  const actual = await vi.importActual<typeof import('../client')>('../client');
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
      post: (...args: unknown[]) => mockPost(...args),
      patch: (...args: unknown[]) => mockPatch(...args),
      put: (...args: unknown[]) => mockPut(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
    },
  };
});

// supabase is imported by the notes module (for noteYjsStateApi). Stub it so
// nothing tries to talk to a live Supabase during module init.
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('notesApi topic-tree methods', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('listChildren calls correct URL with page + page_size and returns the paginated payload', async () => {
    const fakePage = {
      items: [{ id: 'child-1', title: 'C1' }],
      total: 1,
      hasNext: false,
      hasPrev: false,
      pageSize: 20,
      nextCursor: null,
      prevCursor: null,
    };
    mockGet.mockResolvedValueOnce(fakePage);

    const { notesApi } = await import('../notes');
    const result = await notesApi.listChildren('ws-1', 'note-1', 2, 25);

    expect(mockGet).toHaveBeenCalledTimes(1);
    const url = mockGet.mock.calls[0][0] as string;
    expect(url.startsWith('/workspaces/ws-1/notes/note-1/children?')).toBe(true);
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=25');
    expect(result).toBe(fakePage);
  });

  it('listChildren defaults to page=1, page_size=20 when omitted', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0, hasNext: false, hasPrev: false, pageSize: 20, nextCursor: null, prevCursor: null });
    const { notesApi } = await import('../notes');
    await notesApi.listChildren('ws-1', 'note-1');

    const url = mockGet.mock.calls[0][0] as string;
    expect(url).toContain('page=1');
    expect(url).toContain('page_size=20');
  });

  it('listAncestors calls /workspaces/{ws}/notes/{id}/ancestors and returns the array', async () => {
    const ancestors = [{ id: 'a', title: 'Root' }, { id: 'b', title: 'Child' }];
    mockGet.mockResolvedValueOnce(ancestors);

    const { notesApi } = await import('../notes');
    const result = await notesApi.listAncestors('ws-1', 'b');

    expect(mockGet).toHaveBeenCalledWith('/workspaces/ws-1/notes/b/ancestors');
    expect(result).toBe(ancestors);
  });

  it('moveTopic posts camelCase parentId in body and returns the updated note', async () => {
    const updated = { id: 'note-1', title: 'Moved', parentTopicId: 'parent-2' };
    mockPost.mockResolvedValueOnce(updated);

    const { notesApi } = await import('../notes');
    const result = await notesApi.moveTopic('ws-1', 'note-1', 'parent-2');

    expect(mockPost).toHaveBeenCalledWith(
      '/workspaces/ws-1/notes/note-1/move',
      { parentId: 'parent-2' }
    );
    expect(result).toBe(updated);
  });

  it('moveTopic serializes a null parentId (root move) without dropping the key', async () => {
    mockPost.mockResolvedValueOnce({ id: 'note-1' });

    const { notesApi } = await import('../notes');
    await notesApi.moveTopic('ws-1', 'note-1', null);

    expect(mockPost).toHaveBeenCalledWith(
      '/workspaces/ws-1/notes/note-1/move',
      { parentId: null }
    );
    // Specifically: the body must be { parentId: null }, not {} — backend distinguishes
    // "absent" (validation error) from "null" (root move). JSON.stringify of {parentId: null}
    // yields '{"parentId":null}' — verify the actual sent shape preserves the key.
    const body = mockPost.mock.calls[0][1] as Record<string, unknown>;
    expect('parentId' in body).toBe(true);
    expect(body.parentId).toBeNull();
  });

  it('moveTopic propagates rejection (e.g. ApiError on 409) so callers can branch on errorCode', async () => {
    const apiError = Object.assign(new Error('Topic max depth exceeded'), {
      name: 'ApiError',
      status: 409,
      errorCode: 'topic_max_depth_exceeded',
    });
    mockPost.mockRejectedValueOnce(apiError);

    const { notesApi } = await import('../notes');
    await expect(notesApi.moveTopic('ws-1', 'note-1', 'parent-2')).rejects.toBe(apiError);
  });
});

// ---------------------------------------------------------------------------
// topicTreeKeys factory shape
// ---------------------------------------------------------------------------

describe('topicTreeKeys', () => {
  it('all() includes workspaceId for cache scoping', async () => {
    const { topicTreeKeys } = await import('@/features/topics/lib/topic-tree-keys');
    expect(topicTreeKeys.all('ws-1')).toEqual(['topics', 'ws-1']);
  });

  it('children() segments by workspaceId, parentId or __root__ sentinel, and page', async () => {
    const { topicTreeKeys } = await import('@/features/topics/lib/topic-tree-keys');
    expect(topicTreeKeys.children('ws-1', 'parent-2', 1)).toEqual([
      'topics',
      'ws-1',
      'children',
      'parent-2',
      1,
    ]);
    expect(topicTreeKeys.children('ws-1', null)).toEqual([
      'topics',
      'ws-1',
      'children',
      '__root__',
      1,
    ]);
  });

  it('ancestors() keys by workspaceId + noteId', async () => {
    const { topicTreeKeys } = await import('@/features/topics/lib/topic-tree-keys');
    expect(topicTreeKeys.ancestors('ws-1', 'note-1')).toEqual([
      'topics',
      'ws-1',
      'ancestors',
      'note-1',
    ]);
  });
});
