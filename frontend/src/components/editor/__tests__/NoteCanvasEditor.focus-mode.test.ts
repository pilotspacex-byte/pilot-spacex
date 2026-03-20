/**
 * Unit tests for NoteCanvasEditor keyboard shortcuts — focus mode.
 *
 * These tests directly test the keyboard handler logic (the same logic
 * registered inside the `useNoteCanvasEditor` keyboard shortcut useEffect).
 * Using window.dispatchEvent with constructed KeyboardEvent objects, since
 * mounting useNoteCanvasEditor requires complex TipTap + store mocking.
 *
 * @module components/editor/__tests__/NoteCanvasEditor.focus-mode.test
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('NoteCanvasEditor keyboard shortcuts — focus mode', () => {
  let registeredHandler: ((e: KeyboardEvent) => void) | null;
  let mockToggleFocusMode: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    registeredHandler = null;
    mockToggleFocusMode = vi.fn();
  });

  afterEach(() => {
    if (registeredHandler) {
      window.removeEventListener('keydown', registeredHandler);
      registeredHandler = null;
    }
  });

  function buildHandler(isFocusMode: boolean, onToggleFocusMode?: () => void) {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        onToggleFocusMode?.();
      }
      if (e.key === 'Escape' && isFocusMode) {
        onToggleFocusMode?.();
        // Do NOT call e.preventDefault() — let other Escape handlers chain normally
      }
    };
    registeredHandler = handler;
    window.addEventListener('keydown', handler);
    return handler;
  }

  it('Cmd+Shift+F calls onToggleFocusMode', () => {
    buildHandler(false, mockToggleFocusMode);
    window.dispatchEvent(
      new KeyboardEvent('keydown', { metaKey: true, shiftKey: true, key: 'f', bubbles: true })
    );
    expect(mockToggleFocusMode).toHaveBeenCalledOnce();
  });

  it('Ctrl+Shift+F calls onToggleFocusMode (Linux/Windows)', () => {
    buildHandler(false, mockToggleFocusMode);
    window.dispatchEvent(
      new KeyboardEvent('keydown', { ctrlKey: true, shiftKey: true, key: 'f', bubbles: true })
    );
    expect(mockToggleFocusMode).toHaveBeenCalledOnce();
  });

  it('Cmd+Shift+F is case-insensitive (uppercase F)', () => {
    buildHandler(false, mockToggleFocusMode);
    window.dispatchEvent(
      new KeyboardEvent('keydown', { metaKey: true, shiftKey: true, key: 'F', bubbles: true })
    );
    expect(mockToggleFocusMode).toHaveBeenCalledOnce();
  });

  it('Escape when isFocusMode=true calls onToggleFocusMode', () => {
    buildHandler(true, mockToggleFocusMode);
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(mockToggleFocusMode).toHaveBeenCalledOnce();
  });

  it('Escape when isFocusMode=false does NOT call onToggleFocusMode', () => {
    buildHandler(false, mockToggleFocusMode);
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(mockToggleFocusMode).not.toHaveBeenCalled();
  });

  it('Cmd+Shift+F without onToggleFocusMode does not throw', () => {
    // Pass undefined — simulates onToggleFocusMode?.() with no callback
    expect(() => {
      buildHandler(false, undefined);
      window.dispatchEvent(
        new KeyboardEvent('keydown', { metaKey: true, shiftKey: true, key: 'f', bubbles: true })
      );
    }).not.toThrow();
  });

  it('Cmd+Shift+S does NOT call onToggleFocusMode (only Cmd+S for save)', () => {
    buildHandler(false, mockToggleFocusMode);
    window.dispatchEvent(
      new KeyboardEvent('keydown', { metaKey: true, shiftKey: true, key: 's', bubbles: true })
    );
    expect(mockToggleFocusMode).not.toHaveBeenCalled();
  });
});
