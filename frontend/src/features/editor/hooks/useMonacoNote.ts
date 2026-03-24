'use client';

/**
 * useMonacoNote — Composite hook wiring all Monaco features for note editing.
 *
 * Composes:
 * - useMonacoTheme: Light/dark theme registration + tracking
 * - useMonacoViewZones: PM block view zones as React portals
 * - applyMarkdownDecorations: Inline markdown decorations (headings, bold, etc.)
 * - useMonacoGhostText: AI inline completions provider
 * - useMonacoSlashCmd: Slash commands and @ mentions
 * - useMonacoCollab: Yjs collaboration with remote cursors
 */

import { useEffect, type ReactPortal } from 'react';
import type * as monacoNs from 'monaco-editor';
import type { SupabaseClient } from '@supabase/supabase-js';
import { useMonacoTheme } from './useMonacoTheme';
import { useMonacoViewZones } from './useMonacoViewZones';
import { useMonacoGhostText, type GhostTextFetcher } from './useMonacoGhostText';
import { useMonacoSlashCmd, type MemberFetcher } from './useMonacoSlashCmd';
import { useMonacoCollab, type CollabUser, type UseMonacoCollabReturn } from './useMonacoCollab';
import { applyMarkdownDecorations } from '../decorations/markdownDecorations';

export interface UseMonacoNoteOptions {
  noteId: string;
  editor: monacoNs.editor.IStandaloneCodeEditor | null;
  monacoInstance: typeof monacoNs | null;
  content: string;
  ghostTextFetcher: GhostTextFetcher;
  memberFetcher?: MemberFetcher;
  collabEnabled: boolean;
  supabase: SupabaseClient;
  user: CollabUser;
}

export interface UseMonacoNoteReturn {
  theme: string;
  viewZonePortals: ReactPortal[];
  collab: UseMonacoCollabReturn;
}

/**
 * Composite hook that wires all individual Monaco hooks together for note editing.
 *
 * Cleanup order: collab -> view zones -> decorations -> theme
 * (React runs cleanup in reverse-declaration order, so declare in order:
 *  theme -> decorations -> view zones -> ghost text -> slash cmd -> collab)
 */
export function useMonacoNote({
  noteId,
  editor,
  monacoInstance,
  content,
  ghostTextFetcher,
  memberFetcher,
  collabEnabled,
  supabase,
  user,
}: UseMonacoNoteOptions): UseMonacoNoteReturn {
  // 1. Theme registration and tracking
  const theme = useMonacoTheme(monacoInstance);

  // 2. Markdown decorations (inline: headings, bold, italic, code, lists, blockquotes)
  useEffect(() => {
    if (!editor || !monacoInstance) return;
    const disposable = applyMarkdownDecorations(editor, monacoInstance);
    return () => disposable.dispose();
  }, [editor, monacoInstance]);

  // 3. PM block view zones (React portals for decision, raci, risk, etc.)
  const viewZonePortals = useMonacoViewZones(editor, content);

  // 4. AI ghost text inline completions
  useMonacoGhostText(monacoInstance, editor, ghostTextFetcher, noteId);

  // 5. Slash commands (/) and mentions (@)
  useMonacoSlashCmd(monacoInstance, editor, memberFetcher);

  // 6. Yjs collaboration with remote cursors
  const collab = useMonacoCollab({
    editor,
    model: editor?.getModel() ?? null,
    noteId: collabEnabled ? noteId : null,
    enabled: collabEnabled,
    supabase,
    user,
  });

  return { theme, viewZonePortals, collab };
}
