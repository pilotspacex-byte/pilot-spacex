import { useEffect, useCallback } from 'react';

interface UseIssueKeyboardShortcutsOptions {
  /** Called when Escape is pressed to close the AI sidebar. */
  onCloseAISidebar?: () => void;
  /** Called when Cmd/Ctrl+S is pressed for force save. */
  onForceSave?: () => void;
  /** Disables all keyboard shortcuts when false. Defaults to true. */
  enabled?: boolean;
}

/**
 * Keyboard shortcuts for the Issue Detail page.
 *
 * Supported shortcuts:
 * - Escape: Close AI Context sidebar
 * - Cmd/Ctrl+S: Force save current issue edits
 *
 * Shortcuts are ignored when the hook is disabled or when the user
 * is focused inside an input/textarea/contenteditable element
 * (except for Cmd/Ctrl+S which always applies to prevent browser save).
 */
export function useIssueKeyboardShortcuts({
  onCloseAISidebar,
  onForceSave,
  enabled = true,
}: UseIssueKeyboardShortcutsOptions) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const target = event.target as HTMLElement;
      const isEditable =
        target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      // Cmd/Ctrl+S: Force save (always intercept to prevent browser save dialog)
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault();
        onForceSave?.();
        return;
      }

      // Escape: Close AI Context sidebar (skip if inside editable fields)
      if (event.key === 'Escape' && !isEditable && onCloseAISidebar) {
        onCloseAISidebar();
        return;
      }
    },
    [enabled, onCloseAISidebar, onForceSave]
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);
}
