/**
 * FigureExtension — TipTap block node for images with editable captions.
 *
 * ## Design
 *
 * The figure node uses `content: 'inline*'` so the caption text lives as
 * ProseMirror child nodes (NOT in attrs). This makes the caption natively
 * editable by TipTap's NodeViewContent component and enables markdown
 * serialization via node.textContent.
 *
 * ## Markdown serialization
 *
 * Serializes as `![caption text](src)` where caption text = node.textContent.
 * This means the caption survives a markdown round-trip as the alt attribute.
 *
 * ## NodeView
 *
 * FigureNodeView renders the <img> element directly. The figcaption slot is
 * rendered by NodeViewContent (TipTap's content slot for `content: 'inline*'`).
 * FigureNodeView MUST NOT be wrapped in observer() — see constraint note below.
 *
 * ## IMPORTANT: Do NOT wrap NodeView in observer()
 *
 * TipTap's ReactNodeViewRenderer + MobX observer() causes nested flushSync
 * in React 19. Same constraint as IssueEditorContent (CLAUDE.md).
 * FigureNodeView reads node.attrs directly — no MobX reactivity needed.
 */
import { Node, mergeAttributes } from '@tiptap/core';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { FigureNodeView } from './FigureNodeView';

// MarkdownSerializerState interface — tiptap-markdown 0.9 does not re-export this type.
// We only use state.write() here.
interface MarkdownSerializerState {
  write(text: string): void;
}

export const FigureExtension = Node.create({
  name: 'figure',
  group: 'block',
  content: 'inline*', // figcaption is editable inline content — text lives here
  draggable: true,
  isolating: true,

  // NOTE: Do NOT add addExtensions() with StarterKit here.
  // ProseMirror's keyed plugins (history$) throw RangeError on duplicates
  // when the parent editor already registers StarterKit via createEditorExtensions.
  // Tests should explicitly include StarterKit + Markdown in their own editor setup.

  addAttributes() {
    return {
      src: {
        default: null,
        parseHTML: (el: HTMLElement) => el.querySelector('img')?.getAttribute('src') ?? null,
        renderHTML: () => ({}), // rendered explicitly in renderHTML below, not as DOM attr
      },
      alt: {
        default: '',
        parseHTML: (el: HTMLElement) => el.querySelector('img')?.getAttribute('alt') || '',
        renderHTML: () => ({}),
      },
      artifactId: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-artifact-id') ?? null,
        renderHTML: (attrs: Record<string, unknown>) => ({
          'data-artifact-id': attrs.artifactId ?? '',
        }),
      },
      status: {
        default: 'uploading',
        parseHTML: (el: HTMLElement) => el.getAttribute('data-status') ?? 'ready',
        renderHTML: (attrs: Record<string, unknown>) => ({
          'data-status': attrs.status,
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'figure' }];
  },

  renderHTML({ HTMLAttributes, node }) {
    return [
      'figure',
      mergeAttributes(HTMLAttributes, { class: 'note-figure' }),
      [
        'img',
        {
          src: node.attrs.src as string | null,
          alt: node.attrs.alt as string,
          class: 'note-figure-img',
        },
      ],
      ['figcaption', { class: 'note-figure-caption' }, 0], // 0 = ProseMirror content slot
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(FigureNodeView);
  },

  addStorage() {
    return {
      markdown: {
        serialize(state: MarkdownSerializerState, node: ProseMirrorNode) {
          const alt = node.textContent || (node.attrs.alt as string) || '';
          const src = (node.attrs.src as string) || '';
          state.write(`![${alt}](${src})`);
        },
        parse: {},
      },
    };
  },
});
