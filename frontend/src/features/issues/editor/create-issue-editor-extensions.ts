/**
 * createIssueEditorExtensions - Factory for issue description TipTap editor.
 *
 * T029: Assembles a focused subset of extensions suitable for issue descriptions.
 * Excludes note-specific extensions (BlockId, GhostText, AnnotationMark,
 * MarginAnnotation, IssueLink, SlashCommand, InlineIssue, ParagraphSplit).
 */
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import { Markdown } from 'tiptap-markdown';
import type { AnyExtension } from '@tiptap/core';

import { CodeBlockExtension } from '@/features/notes/editor/extensions/CodeBlockExtension';
import {
  MentionExtension,
  type MentionUser,
} from '@/features/notes/editor/extensions/MentionExtension';

// ============================================================================
// Types
// ============================================================================

export type { MentionUser };

export interface IssueEditorExtensionsOptions {
  /** Placeholder text for empty editor */
  placeholder?: string;
  /** Character limit */
  characterLimit?: number;
  /** Enable @mentions */
  enableMentions?: boolean;
  /** Search function for mention suggestions */
  mentionSearch?: (query: string) => Promise<MentionUser[]>;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_PLACEHOLDER = 'Add a description...';
const DEFAULT_CHARACTER_LIMIT = 50000;

// ============================================================================
// Factory
// ============================================================================

export function createIssueEditorExtensions(
  options: IssueEditorExtensionsOptions = {}
): AnyExtension[] {
  const {
    placeholder = DEFAULT_PLACEHOLDER,
    characterLimit = DEFAULT_CHARACTER_LIMIT,
    enableMentions = false,
    mentionSearch,
  } = options;

  const extensions: AnyExtension[] = [];

  extensions.push(
    StarterKit.configure({
      codeBlock: false,
      heading: { levels: [1, 2, 3] },
      bulletList: { keepMarks: true, keepAttributes: false },
      orderedList: { keepMarks: true, keepAttributes: false },
    })
  );

  extensions.push(
    Markdown.configure({
      html: true,
      tightLists: true,
      breaks: false,
      linkify: false,
      transformPastedText: false,
      transformCopiedText: false,
    })
  );

  extensions.push(
    Placeholder.configure({
      placeholder,
      emptyEditorClass: 'is-editor-empty',
      emptyNodeClass: 'is-node-empty',
      showOnlyWhenEditable: true,
      showOnlyCurrent: true,
    })
  );

  extensions.push(
    CharacterCount.configure({
      limit: characterLimit,
      mode: 'textSize',
    })
  );

  extensions.push(
    CodeBlockExtension.configure({
      defaultLanguage: 'plaintext',
      lineNumbers: false,
      showCopyButton: true,
    })
  );

  if (enableMentions && mentionSearch) {
    extensions.push(
      MentionExtension.configure({
        trigger: '@',
        maxSuggestions: 10,
        debounceMs: 150,
        onSearch: mentionSearch,
      })
    );
  }

  return extensions;
}
