/**
 * VimeoNode — custom TipTap block node for Vimeo video embeds.
 *
 * CRITICAL (PRE-002): Registered in Group 3 of createEditorExtensions.ts, BEFORE BlockIdExtension.
 * CRITICAL: Uses renderHTML only — NO ReactNodeViewRenderer (avoids React 19 flushSync crash).
 * CRITICAL: addStorage() markdown.serialize REQUIRED — tiptap-markdown silently drops nodes without it.
 *
 * No TipTap 3.x-compatible Vimeo package exists.
 * fourwaves/tiptap-extension-vimeo is TipTap 2.x only, abandoned 2022. Do not use.
 */
import { Node, mergeAttributes, PasteRule } from '@tiptap/core';

export function extractVimeoId(url: string): string | null {
  try {
    const { hostname, pathname } = new URL(url);
    // Standard: https://vimeo.com/123456789
    if (hostname === 'vimeo.com') {
      const match = /^\/(\d+)/.exec(pathname);
      if (match) return match[1] ?? null;
    }
    // Player embed: https://player.vimeo.com/video/123456789
    if (hostname === 'player.vimeo.com') {
      const match = /^\/video\/(\d+)/.exec(pathname);
      if (match) return match[1] ?? null;
    }
  } catch {
    return null;
  }
  return null;
}

export function isVideoUrl(url: string): 'youtube' | 'vimeo' | null {
  try {
    const { hostname } = new URL(url);
    if (hostname === 'www.youtube.com' || hostname === 'youtube.com' || hostname === 'youtu.be') {
      return 'youtube';
    }
    if (hostname === 'vimeo.com' || hostname === 'player.vimeo.com') {
      return 'vimeo';
    }
  } catch {
    return null;
  }
  return null;
}

const VIDEO_URL_REGEX =
  /^https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/|vimeo\.com\/\d+)[^\s]*$/;

export const VimeoNode = Node.create({
  name: 'vimeo',
  group: 'block',
  atom: true,

  addAttributes() {
    return { src: { default: null } };
  },

  parseHTML() {
    return [{ tag: 'iframe[src*="player.vimeo.com"]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'iframe',
      mergeAttributes(HTMLAttributes, {
        class: 'video-embed video-embed--vimeo',
        sandbox: 'allow-scripts allow-same-origin allow-presentation allow-fullscreen',
        allow: 'autoplay; fullscreen',
      }),
    ];
  },

  addStorage() {
    return {
      markdown: {
        serialize(state: unknown, node: { attrs: { src: string } }) {
          (state as { write: (s: string) => void }).write(`[▶ Vimeo](${node.attrs.src})\n\n`);
        },
      },
    };
  },

  addPasteRules() {
    // No-op PasteRule: marks standalone video URLs. Real embed offer UI is in
    // VideoPasteDetector extension (Plan 02). Pattern here must match Plan 02's regex.
    return [
      new PasteRule({
        find: VIDEO_URL_REGEX,
        handler: () => {
          /* handled by VideoPasteDetector */
        },
      }),
    ];
  },
});
