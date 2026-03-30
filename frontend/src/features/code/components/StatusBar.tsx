'use client';

import { observer } from 'mobx-react-lite';
import { useFileStore } from '@/stores/RootStore';
import { getLanguageLabel } from '../types';

interface StatusBarProps {
  /** Current cursor line number (1-based). */
  line?: number;
  /** Current cursor column number (1-based). */
  col?: number;
  /** Whether a save is currently in progress. */
  isSaving?: boolean;
}

/**
 * StatusBar — IDE status bar with line/col, language, encoding, and branch.
 *
 * Height: 22px (h-[22px]).
 * Font: text-[11px].
 * Background: bg-muted/50.
 *
 * Receives cursor position from MonacoFileEditor onDidChangeCursorPosition.
 */
export const StatusBar = observer(function StatusBar({
  line = 1,
  col = 1,
  isSaving = false,
}: StatusBarProps) {
  const fileStore = useFileStore();
  const activeFile = fileStore.activeFile;

  const language = activeFile ? getLanguageLabel(activeFile.name) : '';
  // Placeholder branch name — real branch from GitStore added in Plan 05
  const branch = 'main';

  return (
    <div
      className="flex h-[22px] shrink-0 items-center justify-between border-t border-border bg-muted/50 px-3"
      role="status"
      aria-label="Editor status"
    >
      {/* Left section */}
      <div className="flex items-center gap-3">
        {activeFile && (
          <>
            <span className="text-[11px] text-muted-foreground tabular-nums">
              Ln {line}, Col {col}
            </span>
            <span className="text-[11px] text-muted-foreground">UTF-8</span>
            {language && (
              <span className="text-[11px] text-muted-foreground capitalize">{language}</span>
            )}
          </>
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {isSaving && (
          <span className="text-[11px] text-muted-foreground animate-pulse">Saving...</span>
        )}
        {!isSaving && activeFile?.isDirty && (
          <span className="text-[11px] text-amber-500">Unsaved</span>
        )}
        <span className="text-[11px] text-muted-foreground">{branch}</span>
      </div>
    </div>
  );
});
