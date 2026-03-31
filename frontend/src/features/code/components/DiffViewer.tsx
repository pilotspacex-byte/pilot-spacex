'use client';

// Side-effect import: configures @monaco-editor/react to use local bundle (not CDN)
import '../monaco-loader';

import { useRef, useState, useEffect, useCallback } from 'react';
import type * as monacoNs from 'monaco-editor';
import { Columns2, Rows2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMonacoTheme } from '../hooks/useMonacoTheme';
import { definePilotSpaceThemes, PILOT_SPACE_DARK } from '../themes/pilotSpaceTheme';

/**
 * DiffViewer — Monaco-based diff editor for viewing file changes.
 *
 * Warm Pilot Space diff colors overlaid on the active theme:
 *   Added   background: rgba(41, 163, 134, 0.08) — teal green
 *   Removed background: rgba(217, 83, 79, 0.06) — warm red
 */
interface DiffViewerProps {
  originalContent: string;
  modifiedContent: string;
  language: string;
  filePath: string;
  onClose: () => void;
}

const DIFF_LIGHT = 'pilot-space-diff-light';
const DIFF_DARK = 'pilot-space-diff-dark';

export function DiffViewer({
  originalContent,
  modifiedContent,
  language,
  filePath,
  onClose,
}: DiffViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [diffEditor, setDiffEditor] = useState<monacoNs.editor.IStandaloneDiffEditor | null>(null);
  const [sideBySide, setSideBySide] = useState(true);
  const { theme } = useMonacoTheme();

  // ─── Create diff editor on mount ──────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let editor: monacoNs.editor.IStandaloneDiffEditor | null = null;
    let disposed = false;

    void import('monaco-editor').then((monaco) => {
      if (disposed || !container) return;

      // Register base themes first
      definePilotSpaceThemes(monaco);

      // Define diff overlay themes with warm diff colors on top of base themes
      const diffColors = {
        'diffEditor.insertedLineBackground': '#29A38614',
        'diffEditor.insertedTextBackground': '#29A38625',
        'diffEditor.removedLineBackground': '#D9534F0F',
        'diffEditor.removedTextBackground': '#D9534F20',
        'diffEditor.diagonalFill': '#29A38614',
      };

      monaco.editor.defineTheme(DIFF_LIGHT, {
        base: 'vs',
        inherit: true,
        rules: [],
        colors: diffColors,
      });

      monaco.editor.defineTheme(DIFF_DARK, {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: diffColors,
      });

      const activeDiffTheme = theme === PILOT_SPACE_DARK ? DIFF_DARK : DIFF_LIGHT;

      editor = monaco.editor.createDiffEditor(container, {
        readOnly: true,
        renderSideBySide: true,
        originalEditable: false,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        renderOverviewRuler: false,
      });

      monaco.editor.setTheme(activeDiffTheme);
      setDiffEditor(editor);
    });

    return () => {
      disposed = true;
      if (editor) {
        editor.dispose();
      }
      setDiffEditor(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Sync theme when light/dark changes ───────────────────────────────────
  useEffect(() => {
    if (!diffEditor) return;
    void import('monaco-editor').then((monaco) => {
      const activeDiffTheme = theme === PILOT_SPACE_DARK ? DIFF_DARK : DIFF_LIGHT;
      monaco.editor.setTheme(activeDiffTheme);
    });
  }, [theme, diffEditor]);

  // ─── Update models when content or language changes ────────────────────────
  useEffect(() => {
    if (!diffEditor) return;

    let cancelled = false;
    let originalModel: monacoNs.editor.ITextModel | null = null;
    let modifiedModel: monacoNs.editor.ITextModel | null = null;

    void import('monaco-editor').then((monaco) => {
      if (cancelled) return;

      originalModel = monaco.editor.createModel(originalContent, language);
      modifiedModel = monaco.editor.createModel(modifiedContent, language);

      diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel,
      });
    });

    return () => {
      cancelled = true;
      originalModel?.dispose();
      modifiedModel?.dispose();
    };
  }, [diffEditor, originalContent, modifiedContent, language]);

  // ─── Toggle side-by-side / inline ─────────────────────────────────────────
  const toggleLayout = useCallback(() => {
    setSideBySide((prev) => {
      const next = !prev;
      diffEditor?.updateOptions({ renderSideBySide: next });
      return next;
    });
  }, [diffEditor]);

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b bg-muted/30 shrink-0">
        <span className="text-xs font-mono text-muted-foreground truncate" title={filePath}>
          {filePath}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={toggleLayout}
            title={sideBySide ? 'Switch to inline diff' : 'Switch to side-by-side diff'}
          >
            {sideBySide ? <Rows2 className="h-3.5 w-3.5" /> : <Columns2 className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onClose}
            title="Close diff"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Diff editor container */}
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}

export default DiffViewer;
