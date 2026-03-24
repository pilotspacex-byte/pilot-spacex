'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import type * as monacoNs from 'monaco-editor';
import { Columns2, Rows2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * DiffViewer - Monaco-based diff editor for viewing file changes.
 *
 * Renders inline or side-by-side diff with syntax highlighting.
 * NOT an observer -- receives data via props (plain component).
 */
interface DiffViewerProps {
  originalContent: string;
  modifiedContent: string;
  language: string;
  filePath: string;
  onClose: () => void;
}

export function DiffViewer({
  originalContent,
  modifiedContent,
  language,
  filePath,
  onClose,
}: DiffViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // useState (not useRef) for editor instance -- React 19 compliance
  const [diffEditor, setDiffEditor] = useState<monacoNs.editor.IStandaloneDiffEditor | null>(null);
  const [sideBySide, setSideBySide] = useState(false);

  // Create diff editor on mount
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let editor: monacoNs.editor.IStandaloneDiffEditor | null = null;
    let disposed = false;

    // Dynamic import to avoid SSR issues
    import('monaco-editor').then((monaco) => {
      if (disposed || !container) return;

      editor = monaco.editor.createDiffEditor(container, {
        readOnly: true,
        renderSideBySide: false,
        originalEditable: false,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        renderOverviewRuler: false,
      });

      setDiffEditor(editor);
    });

    return () => {
      disposed = true;
      if (editor) {
        editor.dispose();
      }
      setDiffEditor(null);
    };
  }, []);

  // Update models when content or language changes
  useEffect(() => {
    if (!diffEditor) return;

    let originalModel: monacoNs.editor.ITextModel | null = null;
    let modifiedModel: monacoNs.editor.ITextModel | null = null;

    import('monaco-editor').then((monaco) => {
      originalModel = monaco.editor.createModel(originalContent, language);
      modifiedModel = monaco.editor.createModel(modifiedContent, language);

      diffEditor.setModel({
        original: originalModel,
        modified: modifiedModel,
      });
    });

    return () => {
      originalModel?.dispose();
      modifiedModel?.dispose();
    };
  }, [diffEditor, originalContent, modifiedContent, language]);

  // Toggle side-by-side / inline
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
