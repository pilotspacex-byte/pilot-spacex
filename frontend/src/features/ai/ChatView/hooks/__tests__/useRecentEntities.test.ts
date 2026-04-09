import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRecentEntities, type RecentEntity } from '../useRecentEntities';

beforeEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

const WORKSPACE = 'ws-test-1';
const KEY = `pilot-recent-entities-${WORKSPACE}`;

function entity(id: string, type: RecentEntity['type'] = 'Note', title = `Entity ${id}`): RecentEntity {
  return { id, type, title };
}

describe('useRecentEntities', () => {
  it('starts with empty array when no sessionStorage entry', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    expect(result.current.recentEntities).toEqual([]);
  });

  it('adds an entity and returns it in the list', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    act(() => {
      result.current.addEntity(entity('a'));
    });
    expect(result.current.recentEntities).toEqual([entity('a')]);
  });

  it('deduplicates by id — moves existing entity to front', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    act(() => {
      result.current.addEntity(entity('a'));
      result.current.addEntity(entity('b'));
      result.current.addEntity(entity('a', 'Note', 'Updated Title'));
    });
    expect(result.current.recentEntities[0]).toEqual(entity('a', 'Note', 'Updated Title'));
    expect(result.current.recentEntities[1]).toEqual(entity('b'));
    expect(result.current.recentEntities).toHaveLength(2);
  });

  it('caps at 5 entities — oldest is evicted', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    act(() => {
      for (let i = 1; i <= 6; i++) {
        result.current.addEntity(entity(String(i)));
      }
    });
    expect(result.current.recentEntities).toHaveLength(5);
    // Entity 1 was the first added and should be evicted
    expect(result.current.recentEntities.map((e) => e.id)).toEqual(['6', '5', '4', '3', '2']);
  });

  it('persists to sessionStorage on add', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    act(() => {
      result.current.addEntity(entity('x'));
    });
    const stored = JSON.parse(sessionStorage.getItem(KEY)!);
    expect(stored).toEqual([entity('x')]);
  });

  it('reads from sessionStorage on mount', () => {
    const preloaded = [entity('pre-1'), entity('pre-2')];
    sessionStorage.setItem(KEY, JSON.stringify(preloaded));

    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    expect(result.current.recentEntities).toEqual(preloaded);
  });

  it('isolates by workspaceId', () => {
    sessionStorage.setItem(`pilot-recent-entities-ws-A`, JSON.stringify([entity('a')]));
    sessionStorage.setItem(`pilot-recent-entities-ws-B`, JSON.stringify([entity('b')]));

    const { result: resultA } = renderHook(() => useRecentEntities('ws-A'));
    const { result: resultB } = renderHook(() => useRecentEntities('ws-B'));

    expect(resultA.current.recentEntities[0]?.id).toBe('a');
    expect(resultB.current.recentEntities[0]?.id).toBe('b');
  });

  it('reloads recents from sessionStorage when workspaceId changes', () => {
    sessionStorage.setItem(`pilot-recent-entities-ws-A`, JSON.stringify([entity('a')]));
    sessionStorage.setItem(`pilot-recent-entities-ws-B`, JSON.stringify([entity('b')]));

    const { result, rerender } = renderHook(
      ({ wsId }: { wsId: string }) => useRecentEntities(wsId),
      { initialProps: { wsId: 'ws-A' } }
    );

    expect(result.current.recentEntities[0]?.id).toBe('a');

    // Switch workspace — should reload from sessionStorage for ws-B
    rerender({ wsId: 'ws-B' });
    expect(result.current.recentEntities[0]?.id).toBe('b');
  });

  it('falls back to empty array when new workspaceId has no stored recents', () => {
    sessionStorage.setItem(`pilot-recent-entities-ws-A`, JSON.stringify([entity('a')]));

    const { result, rerender } = renderHook(
      ({ wsId }: { wsId: string }) => useRecentEntities(wsId),
      { initialProps: { wsId: 'ws-A' } }
    );

    expect(result.current.recentEntities).toHaveLength(1);

    rerender({ wsId: 'ws-empty' });
    expect(result.current.recentEntities).toEqual([]);
  });

  it('falls back to empty array on corrupt sessionStorage JSON', () => {
    sessionStorage.setItem(KEY, '{not valid json!!!');
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    expect(result.current.recentEntities).toEqual([]);
  });

  it('handles sessionStorage.setItem failure gracefully', () => {
    const { result } = renderHook(() => useRecentEntities(WORKSPACE));
    // Mock setItem to throw (e.g., storage full)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('QuotaExceededError');
    });
    // Should not throw
    act(() => {
      result.current.addEntity(entity('fail'));
    });
    // In-memory state still updates even if persistence fails
    expect(result.current.recentEntities).toEqual([entity('fail')]);
    vi.restoreAllMocks();
  });
});
