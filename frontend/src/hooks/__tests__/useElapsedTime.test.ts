/**
 * Unit tests for useElapsedTime hook.
 *
 * Tests rAF-based elapsed time formatting, activity toggling,
 * boundary formatting, and cleanup on unmount.
 *
 * @module hooks/__tests__/useElapsedTime
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useElapsedTime } from '../useElapsedTime';

describe('useElapsedTime', () => {
  let rafCallbacks: Map<number, FrameRequestCallback>;
  let nextRafId: number;
  let rafMock: ReturnType<typeof vi.fn>;
  let cafMock: ReturnType<typeof vi.fn>;
  let perfNowMock: ReturnType<typeof vi.fn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let dateNowMock: any;

  beforeEach(() => {
    rafCallbacks = new Map();
    nextRafId = 1;

    rafMock = vi.fn((cb: FrameRequestCallback) => {
      const id = nextRafId++;
      rafCallbacks.set(id, cb);
      return id;
    });

    cafMock = vi.fn((id: number) => {
      rafCallbacks.delete(id);
    });

    perfNowMock = vi.fn().mockReturnValue(0);

    vi.stubGlobal('requestAnimationFrame', rafMock);
    vi.stubGlobal('cancelAnimationFrame', cafMock);
    vi.spyOn(performance, 'now').mockImplementation(perfNowMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function flushRaf(performanceNow: number) {
    perfNowMock.mockReturnValue(performanceNow);
    const callbacks = Array.from(rafCallbacks.values());
    rafCallbacks.clear();
    for (const cb of callbacks) {
      cb(performanceNow);
    }
  }

  async function flushMicrotasks() {
    await act(async () => {
      // queueMicrotask runs before next paint
      await Promise.resolve();
    });
  }

  function mockDateNow(value: number) {
    dateNowMock = vi.spyOn(Date, 'now').mockReturnValue(value);
  }

  // ========================================
  // Null startTimestamp
  // ========================================

  it('returns "0s" when startTimestamp is null', () => {
    const { result } = renderHook(() => useElapsedTime(null, true));
    expect(result.current).toBe('0s');
  });

  it('returns "0s" when isActive is false', async () => {
    mockDateNow(10000);
    const { result } = renderHook(() => useElapsedTime(5000, false));
    await flushMicrotasks();
    expect(result.current).toBe('0s');
  });

  // ========================================
  // Active timing (via rAF)
  // ========================================

  it('returns formatted elapsed time after first rAF tick', () => {
    mockDateNow(3500);
    const { result } = renderHook(() => useElapsedTime(1000, true));

    // First rAF tick initializes display (lastUpdate === 0 triggers update)
    act(() => flushRaf(16));
    expect(result.current).toBe('2.5s');
  });

  it('updates display on rAF tick after 1s throttle', () => {
    mockDateNow(1500);
    const { result } = renderHook(() => useElapsedTime(1000, true));

    // First tick initializes
    act(() => flushRaf(16));
    expect(result.current).toBe('0.5s');

    // rAF tick at 500ms (within throttle) - no update
    dateNowMock.mockReturnValue(1800);
    act(() => flushRaf(500));
    expect(result.current).toBe('0.5s');

    // rAF tick at 1100ms (past throttle) - should update
    dateNowMock.mockReturnValue(3200);
    act(() => flushRaf(1100));
    expect(result.current).toBe('2.2s');
  });

  // ========================================
  // Stops updating when isActive becomes false
  // ========================================

  it('stops updating when isActive becomes false', async () => {
    mockDateNow(4000);
    const { result, rerender } = renderHook(({ isActive }) => useElapsedTime(1000, isActive), {
      initialProps: { isActive: true },
    });

    act(() => flushRaf(16));
    expect(result.current).toBe('3.0s');

    // Deactivate
    rerender({ isActive: false });
    await flushMicrotasks();
    expect(result.current).toBe('0s');
    expect(cafMock).toHaveBeenCalled();
  });

  // ========================================
  // Boundary formatting
  // ========================================

  it('formats 999ms elapsed as "1.0s" (toFixed(1) rounds up)', () => {
    mockDateNow(1999);
    const { result } = renderHook(() => useElapsedTime(1000, true));
    act(() => flushRaf(16));
    expect(result.current).toBe('1.0s');
  });

  it('formats exactly 1000ms as "1.0s"', () => {
    mockDateNow(2000);
    const { result } = renderHook(() => useElapsedTime(1000, true));
    act(() => flushRaf(16));
    expect(result.current).toBe('1.0s');
  });

  it('formats 10000ms as "10s" (no decimal for >= 10s)', () => {
    mockDateNow(11000);
    const { result } = renderHook(() => useElapsedTime(1000, true));
    act(() => flushRaf(16));
    expect(result.current).toBe('10s');
  });

  it('formats 60000ms as "1m 0s"', () => {
    mockDateNow(61000);
    const { result } = renderHook(() => useElapsedTime(1000, true));
    act(() => flushRaf(16));
    expect(result.current).toBe('1m 0s');
  });

  it('formats 72500ms as "1m 12s"', () => {
    mockDateNow(73500);
    const { result } = renderHook(() => useElapsedTime(1000, true));
    act(() => flushRaf(16));
    expect(result.current).toBe('1m 12s');
  });

  // ========================================
  // Cleanup on unmount
  // ========================================

  it('cancels rAF on unmount to prevent memory leaks', () => {
    mockDateNow(2000);
    const { unmount } = renderHook(() => useElapsedTime(1000, true));

    expect(rafMock).toHaveBeenCalled();
    unmount();
    expect(cafMock).toHaveBeenCalled();
    expect(rafCallbacks.size).toBe(0);
  });
});
