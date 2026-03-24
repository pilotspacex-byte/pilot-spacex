'use client';

/**
 * MonacoNoteEditor - Main Monaco-based note editor component.
 *
 * Replaces NoteCanvasEditor (TipTap) with Monaco's canvas renderer.
 * Supports markdown content with:
 * - Pilot Space theme (light/dark)
 * - Inline markdown decorations (headings, bold, italic, code, lists, blockquotes)
 * - PM block view zones rendered as React portals
 * - AI ghost text inline completions
 * - Slash commands (/) and @ mentions
 * - Yjs collaboration with remote cursors
 * - Edit/Preview mode toggle with crossfade transition
 * - Monaco keybinding overrides for Cmd+Shift+P (command palette),
 *   Cmd+Shift+O (symbol outline), and Cmd+G (go-to-line)
 * - Action registration for edit, navigate, note, and AI categories
 *
 * All Monaco features are composed through the useMonacoNote hook.
 * The `data-lenis-prevent` attribute prevents Lenis scroll hijacking on the editor.
 */

import { useState, useCallback, useEffect } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import type * as monacoNs from 'monaco-editor';
import type { SupabaseClient } from '@supabase/supabase-js';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { MarkdownPreview } from '@/features/markdown-preview/MarkdownPreview';
import { registerEditActions } from '@/features/command-palette/actions/editActions';
import { registerNavigateActions } from '@/features/command-palette/actions/navigateActions';
import { registerNoteActions } from '@/features/command-palette/actions/noteActions';
import { registerAiActions } from '@/features/command-palette/actions/aiActions';
import { useMonacoNote } from './hooks/useMonacoNote';
import { EditorToolbar } from './EditorToolbar';
import type { EditorMode } from './types';
import type { GhostTextFetcher } from './hooks/useMonacoGhostText';
import type { MemberFetcher } from './hooks/useMonacoSlashCmd';
import type { CollabUser } from './hooks/useMonacoCollab';

interface MonacoNoteEditorProps {
  noteId: string;
  initialContent: string;
  onChange?: (content: string) => void;
  isReadOnly?: boolean;
  className?: string;
  /** Ghost text AI completion fetcher */
  ghostTextFetcher?: GhostTextFetcher;
  /** Workspace member fetcher for @ mentions */
  memberFetcher?: MemberFetcher;
  /** Enable Yjs collaboration */
  collabEnabled?: boolean;
  /** Supabase client for collaboration transport */
  supabase?: SupabaseClient;
  /** Current user for collaboration cursors */
  user?: CollabUser;
}

/** No-op ghost text fetcher (returns empty string) */
const noopGhostTextFetcher: GhostTextFetcher = async () => '';

/** Default anonymous user for collab */
const defaultUser: CollabUser = { id: 'anonymous', name: 'Anonymous' };

export default function MonacoNoteEditor({
  noteId,
  initialContent,
  onChange,
  isReadOnly = false,
  className,
  ghostTextFetcher = noopGhostTextFetcher,
  memberFetcher,
  collabEnabled = false,
  supabase,
  user = defaultUser,
}: MonacoNoteEditorProps) {
  const [mode, setMode] = useState<EditorMode>('edit');
  const [content, setContent] = useState(initialContent);
  // Use state (not refs) for values consumed during render (React 19 refs rule)
  const [monacoInstance, setMonacoInstance] = useState<typeof monacoNs | null>(null);
  const [editorInstance, setEditorInstance] =
    useState<monacoNs.editor.IStandaloneCodeEditor | null>(null);

  // Compose all Monaco features through the composite hook
  const { theme: currentTheme, viewZonePortals } = useMonacoNote({
    noteId,
    editor: editorInstance,
    monacoInstance,
    content,
    ghostTextFetcher,
    memberFetcher,
    collabEnabled: collabEnabled && !!supabase,
    supabase: supabase as SupabaseClient, // Safe: collab disabled when supabase is undefined
    user,
  });

  const handleMount: OnMount = useCallback((editor, monacoInst) => {
    setEditorInstance(editor);
    setMonacoInstance(monacoInst);

    // Focus the editor
    editor.focus();
  }, []);

  const handleChange = useCallback(
    (value: string | undefined) => {
      const newContent = value ?? '';
      setContent(newContent);
      onChange?.(newContent);
    },
    [onChange]
  );

  // Monaco keybinding overrides (intercept when editor focused)
  useEffect(() => {
    if (!editorInstance || !monacoInstance) return;
    const monaco = monacoInstance;

    // Cmd+Shift+P: open command palette (override Monaco's built-in)
    editorInstance.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyP,
      () => {
        window.dispatchEvent(new CustomEvent('command-palette:toggle'));
      }
    );

    // Cmd+Shift+O: toggle symbol outline (override Monaco's built-in go-to-symbol)
    editorInstance.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyO,
      () => {
        window.dispatchEvent(new CustomEvent('symbol-outline:toggle'));
      }
    );

    // Cmd+G: go-to-line using Monaco's built-in dialog
    editorInstance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyG, () => {
      editorInstance.getAction('editor.action.gotoLine')?.run();
    });
  }, [editorInstance, monacoInstance]);

  // Register editor-dependent actions (edit, navigate, note, ai)
  useEffect(() => {
    if (!editorInstance) return;
    const editor = editorInstance;

    const cleanups = [
      registerEditActions({
        undo: () => editor.trigger('command-palette', 'undo', null),
        redo: () => editor.trigger('command-palette', 'redo', null),
        find: () => editor.getAction('actions.find')?.run(),
        replace: () => editor.getAction('editor.action.startFindReplaceAction')?.run(),
      }),
      registerNavigateActions({
        goToFile: () => {
          window.dispatchEvent(new CustomEvent('quick-open:toggle'));
        },
        goToLine: () => {
          editor.getAction('editor.action.gotoLine')?.run();
        },
        goToSymbol: () => {
          window.dispatchEvent(new CustomEvent('symbol-outline:toggle'));
        },
      }),
      registerNoteActions({
        insertPMBlock: (type: string) => {
          const position = editor.getPosition();
          if (position) {
            editor.executeEdits('command-palette', [
              {
                range: {
                  startLineNumber: position.lineNumber,
                  startColumn: 1,
                  endLineNumber: position.lineNumber,
                  endColumn: 1,
                },
                text: `\n:::pm-${type}\n:::\n`,
              },
            ]);
          }
        },
      }),
      registerAiActions({
        // AI actions wired with optional chaining; no-op until AI providers connected
      }),
    ];
    return () => cleanups.forEach((fn) => fn());
  }, [editorInstance]);

  // Listen for symbol-outline:navigate custom event
  useEffect(() => {
    if (!editorInstance) return;
    const editor = editorInstance;

    function handleNavigate(e: Event) {
      const detail = (e as CustomEvent<{ line: number }>).detail;
      editor.revealLineInCenter(detail.line);
      editor.setPosition({ lineNumber: detail.line, column: 1 });
      editor.focus();
    }
    window.addEventListener('symbol-outline:navigate', handleNavigate);
    return () => window.removeEventListener('symbol-outline:navigate', handleNavigate);
  }, [editorInstance]);

  return (
    <div className={cn('flex flex-col h-full', className)} data-lenis-prevent>
      <EditorToolbar
        mode={mode}
        onModeChange={setMode}
        fileName="note.md"
        isDirty={false}
        isReadOnly={isReadOnly}
        language="markdown"
      />

      {/* Crossfade wrapper: 200ms opacity transition per UI-SPEC */}
      <div className="flex-1 relative overflow-hidden">
        {/* Edit mode: Monaco editor */}
        <div
          className={cn(
            'absolute inset-0 transition-opacity duration-200',
            mode === 'edit' ? 'opacity-100 z-10' : 'opacity-0 z-0 pointer-events-none'
          )}
        >
          <Editor
            defaultLanguage="markdown"
            defaultValue={initialContent}
            theme={currentTheme}
            onMount={handleMount}
            onChange={handleChange}
            loading={<Skeleton className="h-full w-full" />}
            options={{
              fontSize: 14,
              lineHeight: 22.4, // 14 * 1.6
              fontFamily: 'var(--font-mono)',
              wordWrap: 'on',
              minimap: { enabled: false },
              lineNumbers: 'on',
              glyphMargin: true,
              scrollbar: {
                verticalScrollbarSize: 7,
                horizontalScrollbarSize: 7,
                verticalHasArrows: false,
              },
              padding: { top: 16 },
              renderLineHighlight: 'line',
              cursorStyle: 'line',
              cursorBlinking: 'smooth',
              smoothScrolling: true,
              readOnly: isReadOnly,
            }}
          />
        </div>

        {/* Preview mode: MarkdownPreview (unmounted in edit mode to avoid remark pipeline on every keystroke) */}
        {mode === 'preview' && (
          <div className="absolute inset-0 overflow-auto z-10">
            <MarkdownPreview content={content} className="py-8" />
          </div>
        )}
      </div>

      {/* View zone portals render into Monaco view zone DOM nodes */}
      {viewZonePortals}
    </div>
  );
}
