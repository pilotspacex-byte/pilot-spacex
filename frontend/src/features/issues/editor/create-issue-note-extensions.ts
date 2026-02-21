/**
 * createIssueNoteExtensions - Factory for issue note-first TipTap editor.
 *
 * Reuses the full note canvas extension set from createEditorExtensions
 * and prepends the PropertyBlockNode extension for inline issue properties.
 */
import type { AnyExtension } from '@tiptap/core';
import {
  createEditorExtensions,
  type EditorExtensionsOptions,
} from '@/features/notes/editor/extensions/createEditorExtensions';
import { PropertyBlockNode } from './property-block-extension';

export interface IssueNoteExtensionsOptions extends EditorExtensionsOptions {
  /** Issue ID for the property block node */
  issueId?: string;
}

export function createIssueNoteExtensions(
  options: IssueNoteExtensionsOptions = {}
): AnyExtension[] {
  const { issueId, ...editorOptions } = options;

  // Get full note canvas extension set
  const extensions = createEditorExtensions({
    placeholder: 'Start texting here...',
    ...editorOptions,
  });

  // Prepend PropertyBlockNode (must be registered for schema, but position
  // enforcement is handled by the appendTransaction plugin inside the extension)
  return [PropertyBlockNode.configure({ issueId }), ...extensions];
}
