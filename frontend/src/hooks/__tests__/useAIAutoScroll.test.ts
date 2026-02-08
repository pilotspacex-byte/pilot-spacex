/**
 * Unit tests for useAIAutoScroll hook.
 *
 * @module hooks/__tests__/useAIAutoScroll.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAIAutoScroll } from '../useAIAutoScroll';

describe('useAIAutoScroll', () => {
  let scrollRef: React.RefObject<HTMLDivElement | null>;
  let mockScrollContainer: HTMLDivElement;
  let rafCallbacks: Array<() => void>;
  let originalRAF: typeof requestAnimationFrame;
  let originalCancelRAF: typeof cancelAnimationFrame;

  beforeEach(() => {
    mockScrollContainer = document.createElement('div');
    Object.defineProperty(mockScrollContainer, 'getBoundingClientRect', {
      value: () => ({ top: 0, bottom: 600, left: 0, right: 800 }),
    });
    // jsdom doesn't implement scrollTo; mock it for container-based scrolling
    mockScrollContainer.scrollTo = vi.fn();
    Object.defineProperty(mockScrollContainer, 'scrollTop', { value: 0, writable: true });
    scrollRef = { current: mockScrollContainer };

    // Mock requestAnimationFrame to capture callbacks for manual flushing
    rafCallbacks = [];
    originalRAF = globalThis.requestAnimationFrame;
    originalCancelRAF = globalThis.cancelAnimationFrame;
    globalThis.requestAnimationFrame = vi.fn((cb: FrameRequestCallback) => {
      const id = rafCallbacks.length + 1;
      rafCallbacks.push(() => cb(performance.now()));
      return id;
    });
    globalThis.cancelAnimationFrame = vi.fn();
  });

  afterEach(() => {
    globalThis.requestAnimationFrame = originalRAF;
    globalThis.cancelAnimationFrame = originalCancelRAF;
  });

  /** Flush all pending rAF callbacks inside act() */
  function flushRAF() {
    act(() => {
      const cbs = [...rafCallbacks];
      rafCallbacks.length = 0;
      cbs.forEach((cb) => cb());
    });
  }

  it('returns initial state with no off-screen update', () => {
    const { result } = renderHook(() =>
      useAIAutoScroll(scrollRef, [], null)
    );

    expect(result.current.hasOffScreenUpdate).toBe(false);
    expect(result.current.offScreenBlockId).toBeNull();
  });

  it('auto-scrolls when block is off-screen and user is not editing', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-1');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: ['block-1'], editingId: null } }
    );

    flushRAF();

    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('auto-scrolls even when user is editing elsewhere (no indicator-only mode)', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-2');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    const { rerender } = renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: [] as string[], editingId: 'other-block' as string | null } }
    );

    // Add a processing block while user edits elsewhere
    rerender({ blockIds: ['block-2'], editingId: 'other-block' });
    flushRAF();

    // Should auto-scroll even though user is editing another block
    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('does not trigger when block is visible in viewport', () => {
    // Create a mock block element that IS visible (within container bounds 0-600)
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-visible');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 200, bottom: 220, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    const { result } = renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: ['block-visible'], editingId: null } }
    );

    flushRAF();

    // Block is visible: no auto-scroll
    expect(mockScrollContainer.scrollTo).not.toHaveBeenCalled();
    expect(result.current.hasOffScreenUpdate).toBe(false);
    expect(result.current.offScreenBlockId).toBeNull();

    document.body.removeChild(mockEl);
  });

  it('dismissIndicator clears state', () => {
    const { result } = renderHook(() =>
      useAIAutoScroll(scrollRef, [], null)
    );

    act(() => {
      result.current.dismissIndicator();
    });

    expect(result.current.hasOffScreenUpdate).toBe(false);
    expect(result.current.offScreenBlockId).toBeNull();
  });

  it('scrollToBlock scrolls and clears state', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-4');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: ['block-4'], editingId: null } }
    );

    flushRAF();

    // Auto-scroll should have been called
    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('auto-scrolls on initial mount when processingBlockIds already exist', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-mount');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    renderHook(() => useAIAutoScroll(scrollRef, ['block-mount'], null));

    flushRAF();

    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('auto-scrolls on initial mount when user is editing elsewhere', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-mount-2');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    renderHook(() =>
      useAIAutoScroll(scrollRef, ['block-mount-2'], 'other-block')
    );

    flushRAF();

    // Should auto-scroll even when user is editing elsewhere
    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('auto-scrolls for block above viewport', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-above');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: -100, bottom: -80, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    const { rerender } = renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: [] as string[], editingId: 'other-block' as string | null } }
    );

    rerender({ blockIds: ['block-above'], editingId: 'other-block' });
    flushRAF();

    // Should auto-scroll (element is above viewport)
    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });

  it('auto-scrolls for block below viewport', () => {
    const mockEl = document.createElement('div');
    mockEl.setAttribute('data-block-id', 'block-below');
    Object.defineProperty(mockEl, 'getBoundingClientRect', {
      value: () => ({ top: 700, bottom: 720, left: 0, right: 800 }),
    });
    document.body.appendChild(mockEl);

    const { rerender } = renderHook(
      ({ blockIds, editingId }) => useAIAutoScroll(scrollRef, blockIds, editingId),
      { initialProps: { blockIds: [] as string[], editingId: 'other-block' as string | null } }
    );

    rerender({ blockIds: ['block-below'], editingId: 'other-block' });
    flushRAF();

    // Should auto-scroll (element is below viewport)
    expect(mockScrollContainer.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ behavior: 'smooth' })
    );

    document.body.removeChild(mockEl);
  });
});
