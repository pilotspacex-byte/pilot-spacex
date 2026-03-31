'use client';

import { observer } from 'mobx-react-lite';
import { useTheme } from 'next-themes';
import { Moon, Sun, Monitor } from 'lucide-react';
import { useFileStore, useGitStore } from '@/stores/RootStore';
import { getLanguageLabel } from '../types';

interface StatusBarProps {
  /** Current cursor line number (1-based). */
  line?: number;
  /** Current cursor column number (1-based). */
  col?: number;
  /** Whether a save is currently in progress. */
  isSaving?: boolean;
}

const THEME_CYCLE = ['light', 'dark', 'system'] as const;
const THEME_ICON = { light: Sun, dark: Moon, system: Monitor } as const;
const THEME_LABEL = { light: 'Light', dark: 'Dark', system: 'System' } as const;

/**
 * StatusBar — IDE status bar with line/col, language, encoding, theme toggle, and branch.
 *
 * Height: 22px (h-[22px]).
 * Font: text-[11px].
 * Background: bg-muted/50.
 */
export const StatusBar = observer(function StatusBar({
  line = 1,
  col = 1,
  isSaving = false,
}: StatusBarProps) {
  const fileStore = useFileStore();
  const gitStore = useGitStore();
  const activeFile = fileStore.activeFile;
  const { theme, setTheme } = useTheme();

  const language = activeFile ? getLanguageLabel(activeFile.name) : '';
  const branch = gitStore.currentBranch ?? 'main';

  const currentTheme = (theme ?? 'system') as (typeof THEME_CYCLE)[number];
  const ThemeIcon = THEME_ICON[currentTheme] ?? Monitor;
  const themeLabel = THEME_LABEL[currentTheme] ?? 'System';

  const cycleTheme = () => {
    const idx = THEME_CYCLE.indexOf(currentTheme);
    const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length]!;
    setTheme(next);
  };

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
        {/* Theme toggle — cycles light → dark → system */}
        <button
          type="button"
          onClick={cycleTheme}
          className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          aria-label={`Theme: ${themeLabel}. Click to change.`}
          title={`Theme: ${themeLabel}`}
        >
          <ThemeIcon className="size-3" />
          <span>{themeLabel}</span>
        </button>
        <span className="text-[11px] text-muted-foreground">{branch}</span>
      </div>
    </div>
  );
});
