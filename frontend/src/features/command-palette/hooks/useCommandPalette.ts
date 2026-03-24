'use client';

import { useState, useCallback, useEffect } from 'react';

/**
 * Hook for managing command palette open/close state.
 * Registers global Cmd+Shift+P keyboard listener.
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  // Global keyboard listener: Cmd+Shift+P or Ctrl+Shift+P
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        toggle();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggle]);

  // Listen for command-palette:toggle custom event (from Monaco keybinding override)
  useEffect(() => {
    function handleToggleEvent() {
      toggle();
    }
    window.addEventListener('command-palette:toggle', handleToggleEvent);
    return () => window.removeEventListener('command-palette:toggle', handleToggleEvent);
  }, [toggle]);

  return { isOpen, open, close, toggle };
}
