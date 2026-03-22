/**
 * YoutubeExtension — wraps @tiptap/extension-youtube with tiptap-markdown serialization.
 *
 * CRITICAL (PRE-002): Registered in Group 3 of createEditorExtensions.ts, BEFORE BlockIdExtension.
 * CRITICAL: Uses renderHTML only — NO ReactNodeViewRenderer (avoids React 19 flushSync crash).
 * CRITICAL: addStorage() markdown.serialize REQUIRED — tiptap-markdown silently drops nodes without it.
 */
import { Youtube } from '@tiptap/extension-youtube';

export const YoutubeExtension = Youtube.extend({
  addStorage() {
    return {
      ...this.parent?.(),
      markdown: {
        serialize(state: unknown, node: { attrs: { src: string } }) {
          (state as { write: (s: string) => void }).write(`[▶ YouTube](${node.attrs.src})\n\n`);
        },
      },
    };
  },
}).configure({
  nocookie: true,
  HTMLAttributes: {
    class: 'video-embed video-embed--youtube',
    // allow-same-origin is safe here: iframe content is cross-origin (youtube-nocookie.com),
    // so it cannot access the parent page. Without it, YouTube's player JS fails to load.
    sandbox: 'allow-scripts allow-same-origin allow-presentation allow-fullscreen',
    allow: 'autoplay; fullscreen',
  },
});
