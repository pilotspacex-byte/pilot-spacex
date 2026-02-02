/**
 * Keyboard navigation tests for the Issue Detail page.
 *
 * T049: Tests useIssueKeyboardShortcuts hook behavior including
 * Escape, Cmd+S, Ctrl+S, editable field handling, and cleanup.
 */

import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useIssueKeyboardShortcuts } from '@/features/issues/hooks/use-issue-keyboard-shortcuts';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fireKey(key: string, options: Partial<KeyboardEventInit> = {}, target?: HTMLElement) {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
    ...options,
  });

  if (target) {
    Object.defineProperty(event, 'target', { value: target });
  }

  document.dispatchEvent(event);
  return event;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useIssueKeyboardShortcuts', () => {
  const onCloseAISidebar = vi.fn();
  const onForceSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Force unmount to trigger cleanup
  });

  it('Escape key calls onCloseAISidebar', () => {
    renderHook(() => useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave }));

    act(() => {
      fireKey('Escape');
    });

    expect(onCloseAISidebar).toHaveBeenCalledOnce();
  });

  it('Cmd+S calls onForceSave and prevents default', () => {
    renderHook(() => useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave }));

    const preventDefaultSpy = vi.fn();

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'preventDefault', { value: preventDefaultSpy });
      document.dispatchEvent(event);
    });

    expect(onForceSave).toHaveBeenCalledOnce();
    expect(preventDefaultSpy).toHaveBeenCalledOnce();
  });

  it('Ctrl+S calls onForceSave (Windows)', () => {
    renderHook(() => useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave }));

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'preventDefault', { value: vi.fn() });
      document.dispatchEvent(event);
    });

    expect(onForceSave).toHaveBeenCalledOnce();
  });

  it('Escape is ignored when focused in input element', () => {
    renderHook(() => useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave }));

    const input = document.createElement('input');
    document.body.appendChild(input);

    act(() => {
      fireKey('Escape', {}, input);
    });

    expect(onCloseAISidebar).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it('Cmd+S still works when focused in input (prevents browser save)', () => {
    renderHook(() => useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave }));

    const input = document.createElement('input');
    document.body.appendChild(input);

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', { value: input });
      Object.defineProperty(event, 'preventDefault', { value: vi.fn() });
      document.dispatchEvent(event);
    });

    expect(onForceSave).toHaveBeenCalledOnce();

    document.body.removeChild(input);
  });

  it('disabled mode ignores all shortcuts', () => {
    renderHook(() =>
      useIssueKeyboardShortcuts({
        onCloseAISidebar,
        onForceSave,
        enabled: false,
      })
    );

    act(() => {
      fireKey('Escape');
    });

    act(() => {
      const event = new KeyboardEvent('keydown', {
        key: 's',
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      document.dispatchEvent(event);
    });

    expect(onCloseAISidebar).not.toHaveBeenCalled();
    expect(onForceSave).not.toHaveBeenCalled();
  });

  it('cleanup removes event listener on unmount', () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener');

    const { unmount } = renderHook(() =>
      useIssueKeyboardShortcuts({ onCloseAISidebar, onForceSave })
    );

    unmount();

    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    removeSpy.mockRestore();
  });
});
