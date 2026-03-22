/**
 * VideoPasteDetector — TipTap Extension that auto-embeds YouTube/Vimeo URLs on paste.
 *
 * When a standalone video URL is pasted into an empty paragraph, the URL text is
 * automatically replaced with an embedded video player (Notion-style auto-embed).
 *
 * CRITICAL (PRE-002): Registered in Group 5 of createEditorExtensions.ts, AFTER BlockIdExtension.
 * This is a decoration/interaction layer, not a block-type extension.
 */
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { isVideoUrl, extractVimeoId } from './VimeoNode';

const VIDEO_URL_REGEX =
  /^(https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/|vimeo\.com\/\d+)[^\s]*)$/;

const videoPastePluginKey = new PluginKey('videoPasteDetector');

export const VideoPasteDetector = Extension.create({
  name: 'videoPasteDetector',

  addProseMirrorPlugins() {
    const editor = this.editor;

    return [
      new Plugin({
        key: videoPastePluginKey,
        props: {
          handlePaste(_view, event) {
            const text = event.clipboardData?.getData('text/plain')?.trim();
            if (!text) return false;

            const match = VIDEO_URL_REGEX.exec(text);
            if (!match) return false;

            const url = match[1];
            if (!url) return false;

            const platform = isVideoUrl(url);
            if (!platform) return false;

            // Auto-embed: replace pasted text with video player
            if (platform === 'youtube') {
              // Use requestAnimationFrame to let the paste transaction settle,
              // then replace the current selection/paragraph with the embed
              requestAnimationFrame(() => {
                editor.chain().focus().setYoutubeVideo({ src: url }).run();
              });
              return true;
            }

            if (platform === 'vimeo') {
              const id = extractVimeoId(url);
              if (id) {
                requestAnimationFrame(() => {
                  editor
                    .chain()
                    .focus()
                    .insertContent({
                      type: 'vimeo',
                      attrs: { src: `https://player.vimeo.com/video/${id}` },
                    })
                    .run();
                });
                return true;
              }
            }

            return false;
          },
        },
      }),
    ];
  },
});
