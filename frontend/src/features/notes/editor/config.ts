import { Editor, type Extensions } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import CharacterCount from '@tiptap/extension-character-count';
import type { EditorOptions } from './types';

/**
 * Default character limit for notes
 */
const DEFAULT_CHARACTER_LIMIT = 100000;

/**
 * Default placeholder text
 */
const DEFAULT_PLACEHOLDER = 'Start writing your thoughts...';

/**
 * Base TipTap extensions for the note editor
 */
export function getBaseExtensions(options?: {
  placeholder?: string;
  characterLimit?: number;
}): Extensions {
  const { placeholder = DEFAULT_PLACEHOLDER, characterLimit = DEFAULT_CHARACTER_LIMIT } =
    options ?? {};

  return [
    StarterKit.configure({
      // Configure heading levels
      heading: {
        levels: [1, 2, 3],
      },
      // Disable code block from StarterKit (we have our own)
      codeBlock: false,
      // Configure horizontal rule
      horizontalRule: {
        HTMLAttributes: {
          class: 'note-divider',
        },
      },
      // Configure paragraph
      paragraph: {
        HTMLAttributes: {
          class: 'note-paragraph',
        },
      },
      // Configure bullet list
      bulletList: {
        HTMLAttributes: {
          class: 'note-bullet-list',
        },
        keepMarks: true,
        keepAttributes: false,
      },
      // Configure ordered list
      orderedList: {
        HTMLAttributes: {
          class: 'note-ordered-list',
        },
        keepMarks: true,
        keepAttributes: false,
      },
      // Configure blockquote
      blockquote: {
        HTMLAttributes: {
          class: 'note-blockquote',
        },
      },
    }),
    Placeholder.configure({
      placeholder: ({ node }) => {
        if (node.type.name === 'heading') {
          const level = node.attrs.level as number;
          return `Heading ${level}`;
        }
        return placeholder;
      },
      emptyEditorClass: 'is-editor-empty',
      emptyNodeClass: 'is-empty',
      showOnlyWhenEditable: true,
      showOnlyCurrent: true,
      includeChildren: false,
    }),
    CharacterCount.configure({
      limit: characterLimit,
      mode: 'textSize',
    }),
  ];
}

/**
 * Create a TipTap editor instance with the Note-First configuration
 *
 * @example
 * ```tsx
 * const editor = createEditor({
 *   content: note.content,
 *   placeholder: 'Start writing...',
 *   onUpdate: ({ editor }) => {
 *     noteStore.updateContent(noteId, editor.getJSON());
 *   },
 * });
 * ```
 */
export function createEditor(options: EditorOptions = {}): Editor {
  const {
    content,
    placeholder,
    editable = true,
    autofocus = false,
    onUpdate,
    onSelectionUpdate,
    onBlur,
    onFocus,
    onCreate,
    onDestroy,
  } = options;

  const extensions = getBaseExtensions({ placeholder });

  return new Editor({
    extensions,
    content,
    editable,
    autofocus,
    editorProps: {
      attributes: {
        class: 'note-editor prose prose-lg dark:prose-invert focus:outline-none',
        spellcheck: 'true',
      },
      handleDOMEvents: {
        // Prevent default drop behavior
        drop: (_, event) => {
          // Allow dropping text but prevent file drops
          if (event.dataTransfer?.files.length) {
            event.preventDefault();
            return true;
          }
          return false;
        },
      },
    },
    parseOptions: {
      preserveWhitespace: 'full',
    },
    onUpdate: onUpdate
      ? ({ editor, transaction }) => {
          onUpdate({ editor, transaction });
        }
      : undefined,
    onSelectionUpdate: onSelectionUpdate
      ? ({ editor, transaction }) => {
          onSelectionUpdate({ editor, transaction });
        }
      : undefined,
    onBlur: onBlur
      ? ({ editor, event }) => {
          onBlur({ editor, event });
        }
      : undefined,
    onFocus: onFocus
      ? ({ editor, event }) => {
          onFocus({ editor, event });
        }
      : undefined,
    onCreate: onCreate
      ? ({ editor }) => {
          onCreate({ editor });
        }
      : undefined,
    onDestroy,
  });
}

/**
 * Default editor configuration values
 */
export const editorConfig = {
  characterLimit: DEFAULT_CHARACTER_LIMIT,
  placeholder: DEFAULT_PLACEHOLDER,
  headingLevels: [1, 2, 3] as const,
  historyDepth: 100,
  historyGroupDelay: 500,
} as const;

/**
 * CSS classes for editor elements
 */
export const editorClasses = {
  editor: 'note-editor',
  paragraph: 'note-paragraph',
  heading: 'note-heading',
  bulletList: 'note-bullet-list',
  orderedList: 'note-ordered-list',
  blockquote: 'note-blockquote',
  codeBlock: 'note-code-block',
  divider: 'note-divider',
  empty: 'is-editor-empty',
  emptyNode: 'is-empty',
} as const;
