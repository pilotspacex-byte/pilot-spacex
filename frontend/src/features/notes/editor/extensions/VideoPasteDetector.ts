/**
 * VideoPasteDetector — TipTap Extension that detects standalone YouTube/Vimeo URL pastes.
 *
 * When a standalone video URL is pasted on an empty paragraph, shows an inline
 * "Embed video?" offer with Accept/Dismiss buttons.
 *
 * CRITICAL (PRE-002): Registered in Group 5 of createEditorExtensions.ts, AFTER BlockIdExtension.
 * This is a decoration/interaction layer, not a block-type extension.
 */
import { Extension, PasteRule } from '@tiptap/core';
import type { Editor } from '@tiptap/core';
import { isVideoUrl, extractVimeoId } from './VimeoNode';

const VIDEO_URL_REGEX =
  /^(https?:\/\/(www\.)?(youtube\.com\/watch|youtu\.be\/|vimeo\.com\/\d+)[^\s]*)$/;

/** Tracks the cleanup function for the currently visible offer, if any. */
let activeOfferCleanup: (() => void) | null = null;

function showEmbedOffer(
  editor: Editor,
  url: string,
  coords: { left: number; bottom: number }
): void {
  const offer = document.createElement('div');
  offer.className = 'video-embed-offer';
  offer.setAttribute('role', 'dialog');
  offer.setAttribute('aria-label', 'Embed video');
  Object.assign(offer.style, {
    position: 'fixed',
    left: `${coords.left}px`,
    top: `${coords.bottom + 4}px`,
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    padding: '6px 10px',
    fontSize: '13px',
    border: '1px solid var(--border, #e2e8f0)',
    borderRadius: '6px',
    background: 'var(--background, #ffffff)',
    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    zIndex: '50',
  });

  const label = document.createElement('span');
  label.textContent = 'Embed video?';

  const acceptBtn = document.createElement('button');
  acceptBtn.textContent = 'Embed';
  acceptBtn.tabIndex = 0;
  acceptBtn.style.cssText =
    'cursor:pointer;padding:2px 8px;border:1px solid var(--border,#e2e8f0);border-radius:4px;background:var(--primary,#0f172a);color:var(--primary-foreground,#fff);font-size:12px;';

  const dismissBtn = document.createElement('button');
  dismissBtn.textContent = 'Dismiss';
  dismissBtn.tabIndex = 0;
  dismissBtn.style.cssText =
    'cursor:pointer;padding:2px 8px;border:1px solid var(--border,#e2e8f0);border-radius:4px;background:transparent;font-size:12px;';

  const cleanup = () => {
    if (offer.parentNode) offer.parentNode.removeChild(offer);
    document.removeEventListener('mousedown', outsideClick);
    activeOfferCleanup = null;
  };

  const handleAccept = (e: Event) => {
    e.preventDefault();
    cleanup();
    const platform = isVideoUrl(url);
    if (platform === 'youtube') {
      editor.chain().focus().setYoutubeVideo({ src: url }).run();
    } else if (platform === 'vimeo') {
      const id = extractVimeoId(url);
      if (id) {
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'vimeo',
            attrs: { src: `https://player.vimeo.com/video/${id}` },
          })
          .run();
      }
    }
  };

  const handleDismiss = (e: Event) => {
    e.preventDefault();
    cleanup();
  };

  acceptBtn.addEventListener('mousedown', handleAccept);
  acceptBtn.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') handleAccept(e);
  });

  dismissBtn.addEventListener('mousedown', handleDismiss);
  dismissBtn.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') handleDismiss(e);
  });

  offer.append(label, acceptBtn, dismissBtn);
  document.body.appendChild(offer);
  activeOfferCleanup = cleanup;

  // Auto-dismiss on outside click
  const outsideClick = (e: MouseEvent) => {
    if (!offer.contains(e.target as Node)) {
      cleanup();
    }
  };
  setTimeout(() => document.addEventListener('mousedown', outsideClick), 100);
}

export const VideoPasteDetector = Extension.create({
  name: 'videoPasteDetector',

  onDestroy() {
    if (activeOfferCleanup) {
      activeOfferCleanup();
    }
  },

  addPasteRules() {
    return [
      new PasteRule({
        find: VIDEO_URL_REGEX,
        handler: ({ state, range, match }) => {
          const url = match[1];
          if (!url || !isVideoUrl(url)) return;

          // Only offer embed if pasted into an empty paragraph
          const $from = state.doc.resolve(range.from);
          const node = $from.parent;
          if (node.type.name !== 'paragraph' || node.textContent.trim() !== '') return;

          // Show embed offer after the paste transaction settles
          requestAnimationFrame(() => {
            const coords = this.editor.view.coordsAtPos(range.from);
            showEmbedOffer(this.editor, url, { left: coords.left, bottom: coords.bottom });
          });
        },
      }),
    ];
  },
});
