/**
 * PullQuoteExtension — editorial pull quote variant of the standard blockquote.
 *
 * Extends StarterKit's blockquote node with a `pullQuote` boolean attribute.
 * When true, renders `data-pull-quote` on the DOM element and serializes to
 * `> [!quote]` GitHub-compatible callout syntax in markdown.
 *
 * ## Implementation notes
 *
 * 1. `name` MUST stay `'blockquote'` — changing it would:
 *    - Create a NEW node type (schema migration required)
 *    - Remove it from BlockIdExtension's hardcoded type list (blockId would not be assigned)
 *    - Conflict with StarterKit's blockquote schema registration
 *    Use `StarterKit.configure({ blockquote: false })` when registering this extension
 *    to disable StarterKit's bundled blockquote.
 *
 * 2. Markdown serialization uses tiptap-markdown 0.9's ProseMirror-style API:
 *    `addStorage().markdown.serialize(state, node)` — NOT `@tiptap/markdown`'s
 *    `renderMarkdown(node, helpers, context)`. These are different packages/APIs.
 *    Using the wrong API causes pull quotes to silently drop from saved content.
 *
 * 3. Round-trip: the `> [!quote]` prefix needs a markdown-it rule in the parse
 *    config to survive a full round-trip. For v1.1, the round-trip is best-effort:
 *    serialized markdown contains the callout hint; standard markdown parsers
 *    will render it as a normal blockquote (fallback is acceptable).
 */
import Blockquote from '@tiptap/extension-blockquote';
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';

// MarkdownSerializerState is not re-exported by tiptap-markdown, use unknown with cast
// The API surface used: state.write(), state.wrapBlock(), state.renderContent(), state.closeBlock()
interface MarkdownSerializerState {
  write(text: string): void;
  wrapBlock(delim: string, firstDelim: string | null, node: ProseMirrorNode, fn: () => void): void;
  renderContent(node: ProseMirrorNode): void;
  closeBlock(node: ProseMirrorNode): void;
}

export const PullQuoteExtension = Blockquote.extend({
  name: 'blockquote', // KEEP — do not rename (see note 1 above)

  addAttributes() {
    return {
      ...this.parent?.(),
      pullQuote: {
        default: false,
        parseHTML: (element: Element) => element.hasAttribute('data-pull-quote'),
        renderHTML: (attributes: { pullQuote?: boolean }) =>
          attributes.pullQuote ? { 'data-pull-quote': '' } : {},
      },
    };
  },

  addStorage() {
    return {
      markdown: {
        serialize(state: MarkdownSerializerState, node: ProseMirrorNode) {
          if ((node.attrs as { pullQuote?: boolean }).pullQuote) {
            // GitHub-compatible callout syntax — visually distinct in GitHub markdown renderers
            state.write('> [!quote]\n');
            state.wrapBlock('> ', null, node, () => state.renderContent(node));
          } else {
            // Standard blockquote fallback
            state.wrapBlock('> ', null, node, () => state.renderContent(node));
          }
          state.closeBlock(node);
        },
        parse: {
          /**
           * updateDOM hook — called by tiptap-markdown 0.9 after markdown-it renders HTML,
           * before TipTap's parseHTML rules run.
           *
           * Detects blockquotes rendered from `> [!quote]` syntax:
           * markdown-it renders them as <blockquote><p>[!quote]</p><p>content</p></blockquote>
           * (or as <blockquote><p>[!quote]\ncontent</p></blockquote> with line breaks).
           *
           * This hook adds `data-pull-quote` to the blockquote element and removes the
           * `[!quote]` marker paragraph so the content round-trips cleanly.
           */
          updateDOM(element: Element) {
            element.querySelectorAll('blockquote').forEach((blockquote) => {
              const firstChild = blockquote.firstElementChild;
              if (!firstChild) return;
              // Check if the first <p> starts with "[!quote]" (from markdown-it rendering)
              const firstText = firstChild.textContent?.trim() ?? '';
              if (firstText === '[!quote]' || firstText.startsWith('[!quote]')) {
                blockquote.setAttribute('data-pull-quote', '');
                // Remove the "[!quote]" marker paragraph entirely
                if (firstText === '[!quote]') {
                  blockquote.removeChild(firstChild);
                } else {
                  // If [!quote] is inline with content (e.g. "[!quote]\ntext"), strip just the marker
                  const cleaned = firstText.replace(/^\[!quote\]\s*\n?/, '');
                  firstChild.textContent = cleaned;
                }
              }
            });
          },
        },
      },
    };
  },

  addCommands() {
    return {
      ...this.parent?.(),
      togglePullQuote:
        () =>
        ({
          commands,
        }: {
          commands: { updateAttributes: (type: string, attrs: object) => boolean };
        }) => {
          const currentAttrs = this.editor?.getAttributes('blockquote') ?? {};
          return commands.updateAttributes('blockquote', {
            pullQuote: !(currentAttrs.pullQuote ?? false),
          });
        },
    };
  },
});
