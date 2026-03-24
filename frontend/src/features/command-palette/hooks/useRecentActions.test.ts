import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRecentActions } from './useRecentActions';

const STORAGE_KEY = 'pilot-space:recent-actions';

// Ensure localStorage is available (jsdom forks may not always expose it)
const storage = new Map<string, string>();
const localStorageMock = {
  getItem: vi.fn((key: string) => storage.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => storage.set(key, value)),
  removeItem: vi.fn((key: string) => storage.delete(key)),
  clear: vi.fn(() => storage.clear()),
  get length() {
    return storage.size;
  },
  key: vi.fn((_index: number) => null),
};

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

describe('useRecentActions', () => {
  beforeEach(() => {
    storage.clear();
    vi.clearAllMocks();
  });

  it('returns empty array when localStorage is empty', () => {
    const { result } = renderHook(() => useRecentActions());
    expect(result.current.getRecent()).toEqual([]);
  });

  it('addRecent pushes action ID to front of recent list', () => {
    const { result } = renderHook(() => useRecentActions());
    act(() => {
      result.current.addRecent('action-1');
    });
    expect(result.current.getRecent()).toEqual(['action-1']);
  });

  it('recent list is capped at 5 items (oldest dropped)', () => {
    const { result } = renderHook(() => useRecentActions());
    act(() => {
      result.current.addRecent('a1');
      result.current.addRecent('a2');
      result.current.addRecent('a3');
      result.current.addRecent('a4');
      result.current.addRecent('a5');
      result.current.addRecent('a6');
    });
    const recent = result.current.getRecent();
    expect(recent).toHaveLength(5);
    expect(recent[0]).toBe('a6');
    expect(recent).not.toContain('a1');
  });

  it('duplicate ID moves to front instead of adding twice', () => {
    const { result } = renderHook(() => useRecentActions());
    act(() => {
      result.current.addRecent('a1');
      result.current.addRecent('a2');
      result.current.addRecent('a3');
      result.current.addRecent('a1'); // duplicate
    });
    const recent = result.current.getRecent();
    expect(recent).toHaveLength(3);
    expect(recent[0]).toBe('a1');
    expect(recent[1]).toBe('a3');
    expect(recent[2]).toBe('a2');
  });

  it('getRecent reads from localStorage on each call (not cached)', () => {
    const { result } = renderHook(() => useRecentActions());
    // Manually set localStorage
    storage.set(STORAGE_KEY, JSON.stringify(['ext-1', 'ext-2']));
    expect(result.current.getRecent()).toEqual(['ext-1', 'ext-2']);
  });
});
