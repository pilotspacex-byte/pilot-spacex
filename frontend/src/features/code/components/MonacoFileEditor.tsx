'use client';

/**
 * MonacoFileEditor — Monaco editor wrapper for source code files.
 *
 * Responsibilities:
 * - Render Monaco with Pilot Space warm theme (light/dark adaptive)
 * - Configure editor options: JetBrains Mono 13px, line-height 20px
 * - Cmd+S / Ctrl+S → calls onSave callback
 * - beforeMount: register Pilot Space themes
 * - Local bundling (no CDN) via monaco-loader side-effect import
 *
 * Stripped from branch version:
 * - usePluginEditorBridge, usePluginLoader, PluginSandbox
 * - useMonacoGhostText (deferred)
 * - useMonacoCollab (deferred)
 * - useMonacoNote, useMonacoSlashCmd, useMonacoViewZones
 * - useTypeScriptDefaults, usePythonLanguage
 * - Command palette / symbol outline action registration
 */

import { useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { OnMount, BeforeMount } from '@monaco-editor/react';
import type * as monacoNs from 'monaco-editor';
import { Skeleton } from '@/components/ui/skeleton';
import { useMonacoTheme } from '../hooks/useMonacoTheme';
import { definePilotSpaceThemes } from '../themes/pilotSpaceTheme';

// Side-effect import: configures @monaco-editor/react to use local monaco-editor
// package instead of CDN. Must run before the first <Editor /> render.
import '../monaco-loader';

// ─── Dynamic Import ───────────────────────────────────────────────────────────
// Monaco Editor is SSR-incompatible (uses browser-only window/document APIs).
// We load it dynamically with ssr:false to skip server-side rendering.
const Editor = dynamic(() => import('@monaco-editor/react').then((m) => m.default), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

// ─── Props Interface ──────────────────────────────────────────────────────────

export interface MonacoFileEditorProps {
  /** Stable identifier for this file tab — used as Monaco model URI key. */
  fileId: string;
  /** The text content to display. */
  content: string;
  /** Monaco language ID (e.g. 'typescript', 'python'). */
  language: string;
  /** When true, editing is disabled. */
  readOnly?: boolean;
  /** Called when the user edits content. */
  onChange?: (value: string) => void;
  /** Called when user triggers Cmd+S / Ctrl+S. */
  onSave?: () => void;
}

// ─── Editor Options (stable reference) ───────────────────────────────────────

const EDITOR_OPTIONS: monacoNs.editor.IStandaloneEditorConstructionOptions = {
  // Typography — JetBrains Mono 13px/20px per design spec
  fontSize: 13,
  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Consolas, monospace",
  lineHeight: 20,
  fontLigatures: true,

  // Layout
  wordWrap: 'off',
  scrollBeyondLastLine: false,
  lineNumbers: 'on',

  // Minimap — enabled for desktop (component consumer can override for small panels)
  minimap: { enabled: true },

  // Scrollbar
  scrollbar: {
    verticalScrollbarSize: 7,
    horizontalScrollbarSize: 7,
    useShadows: false,
  },

  // Bracket colorization
  bracketPairColorization: { enabled: true },

  // Cursor
  cursorStyle: 'line',
  cursorBlinking: 'smooth',
  smoothScrolling: true,

  // UX
  renderLineHighlight: 'line',
  selectOnLineNumbers: true,
  automaticLayout: true,
  padding: { top: 12, bottom: 12 },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function MonacoFileEditor({
  fileId,
  content,
  language,
  readOnly = false,
  onChange,
  onSave,
}: MonacoFileEditorProps) {
  const { theme } = useMonacoTheme();

  /**
   * beforeMount: Register Pilot Space themes before Monaco renders its first frame.
   * This prevents a flash of the default VS Code theme.
   */
  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    definePilotSpaceThemes(monaco);
  }, []);

  /**
   * onMount: Register Cmd+S / Ctrl+S keybinding for save action.
   */
  const handleMount: OnMount = useCallback(
    (editor, monaco) => {
      // Cmd+S (macOS) / Ctrl+S (Windows/Linux) → trigger save
      editor.addAction({
        id: 'pilot-space.save',
        label: 'Save File',
        keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
        run: () => {
          onSave?.();
        },
      });
    },
    [onSave]
  );

  const handleChange = useCallback(
    (value: string | undefined) => {
      if (value !== undefined) {
        onChange?.(value);
      }
    },
    [onChange]
  );

  return (
    <div className="relative h-full w-full" data-file-id={fileId}>
      <Editor
        language={language}
        value={content}
        theme={theme}
        beforeMount={handleBeforeMount}
        onMount={handleMount}
        onChange={handleChange}
        loading={<Skeleton className="h-full w-full" />}
        options={{
          ...EDITOR_OPTIONS,
          readOnly,
        }}
      />
    </div>
  );
}

