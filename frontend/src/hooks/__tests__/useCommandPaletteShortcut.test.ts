/**
 * useCommandPaletteShortcut Tests — T-019
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

import { useCommandPaletteShortcut } from '../useCommandPaletteShortcut';

// Mock UIStore singleton
const mockToggleCommandPalette = vi.fn();
vi.mock('@/stores/UIStore', () => ({
  uiStore: {
    toggleCommandPalette: () => mockToggleCommandPalette(),
  },
}));

function fireKeydown(key: string, modifiers: { metaKey?: boolean; ctrlKey?: boolean } = {}) {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
    metaKey: modifiers.metaKey ?? false,
    ctrlKey: modifiers.ctrlKey ?? false,
  });
  window.dispatchEvent(event);
  return event;
}

describe('useCommandPaletteShortcut', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('registers keydown listener on mount', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    renderHook(() => useCommandPaletteShortcut());
    expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function), { capture: true });
  });

  it('removes keydown listener on unmount', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = renderHook(() => useCommandPaletteShortcut());
    unmount();
    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function), { capture: true });
  });

  it('does not trigger on non-K key', () => {
    renderHook(() => useCommandPaletteShortcut());
    fireKeydown('j', { metaKey: true });
    expect(mockToggleCommandPalette).not.toHaveBeenCalled();
  });

  it('does not trigger on K without modifier', () => {
    renderHook(() => useCommandPaletteShortcut());
    fireKeydown('k');
    expect(mockToggleCommandPalette).not.toHaveBeenCalled();
  });
});
