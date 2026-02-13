/**
 * Tests for useBlockEditGuard hook (FR-048).
 *
 * Validates that the edit guard correctly tracks user-edited PM blocks
 * and prevents the Agent from overwriting them.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useBlockEditGuard } from '../shared/useBlockEditGuard';

/** Minimal mock of TipTap Editor with storage */
function createMockEditor(isDestroyed = false) {
  return {
    storage: {} as Record<string, unknown>,
    isDestroyed,
  } as unknown as import('@tiptap/core').Editor;
}

describe('useBlockEditGuard', () => {
  let mockEditor: ReturnType<typeof createMockEditor>;

  beforeEach(() => {
    mockEditor = createMockEditor();
  });

  it('returns all methods when editor is provided', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    expect(result.current.markEdited).toBeDefined();
    expect(result.current.isEdited).toBeDefined();
    expect(result.current.clearEdited).toBeDefined();
    expect(result.current.getEditedBlockIds).toBeDefined();
  });

  it('marks a block as user-edited', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-1');
    });

    expect(result.current.isEdited('block-1')).toBe(true);
  });

  it('returns false for blocks that have not been edited', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    expect(result.current.isEdited('block-1')).toBe(false);
  });

  it('tracks multiple edited blocks independently', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-1');
      result.current.markEdited('block-3');
    });

    expect(result.current.isEdited('block-1')).toBe(true);
    expect(result.current.isEdited('block-2')).toBe(false);
    expect(result.current.isEdited('block-3')).toBe(true);
  });

  it('clears the user-edited flag for a specific block', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-1');
      result.current.markEdited('block-2');
    });

    expect(result.current.isEdited('block-1')).toBe(true);

    act(() => {
      result.current.clearEdited('block-1');
    });

    expect(result.current.isEdited('block-1')).toBe(false);
    expect(result.current.isEdited('block-2')).toBe(true);
  });

  it('returns all edited block IDs', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-a');
      result.current.markEdited('block-b');
      result.current.markEdited('block-c');
    });

    const ids = result.current.getEditedBlockIds();
    expect(ids).toHaveLength(3);
    expect(ids).toContain('block-a');
    expect(ids).toContain('block-b');
    expect(ids).toContain('block-c');
  });

  it('returns empty array when no blocks are edited', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    expect(result.current.getEditedBlockIds()).toEqual([]);
  });

  it('is idempotent when marking the same block multiple times', () => {
    const { result } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-1');
      result.current.markEdited('block-1');
      result.current.markEdited('block-1');
    });

    expect(result.current.getEditedBlockIds()).toHaveLength(1);
  });

  it('handles null editor gracefully', () => {
    const { result } = renderHook(() => useBlockEditGuard(null));

    expect(result.current.isEdited('block-1')).toBe(false);
    expect(result.current.getEditedBlockIds()).toEqual([]);

    // Should not throw
    act(() => {
      result.current.markEdited('block-1');
      result.current.clearEdited('block-1');
    });

    expect(result.current.isEdited('block-1')).toBe(false);
  });

  it('handles destroyed editor gracefully', () => {
    const destroyedEditor = createMockEditor(true);
    const { result } = renderHook(() => useBlockEditGuard(destroyedEditor));

    expect(result.current.isEdited('block-1')).toBe(false);
    expect(result.current.getEditedBlockIds()).toEqual([]);
  });

  it('persists state in editor.storage across re-renders', () => {
    const { result, rerender } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      result.current.markEdited('block-1');
    });

    rerender();

    expect(result.current.isEdited('block-1')).toBe(true);
  });

  it('shares state between multiple hook instances on same editor', () => {
    const { result: guard1 } = renderHook(() => useBlockEditGuard(mockEditor));
    const { result: guard2 } = renderHook(() => useBlockEditGuard(mockEditor));

    act(() => {
      guard1.current.markEdited('block-1');
    });

    expect(guard2.current.isEdited('block-1')).toBe(true);
  });
});
