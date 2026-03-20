import type { Editor } from '@tiptap/core';

/**
 * showVideoUrlPrompt — injects a transient inline DOM input for /video URL entry.
 *
 * Per CONTEXT.md decision: inline URL input field, NOT a modal.
 * Used by the /video slash command execute handler in slash-command-items.ts.
 */
export function showVideoUrlPrompt(editor: Editor, onConfirm: (url: string) => void): void {
  const { from } = editor.state.selection;
  const coords = editor.view.coordsAtPos(from);

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Paste YouTube or Vimeo URL...';
  input.className = 'video-url-prompt';
  input.setAttribute('aria-label', 'Enter video URL to embed');

  Object.assign(input.style, {
    position: 'fixed',
    left: `${coords.left}px`,
    top: `${coords.bottom + 4}px`,
    width: '320px',
    padding: '8px 12px',
    fontSize: '14px',
    border: '1px solid var(--border, #e2e8f0)',
    borderRadius: '6px',
    background: 'var(--background, #ffffff)',
    boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    zIndex: '50',
    outline: 'none',
  });

  const cleanup = () => {
    if (input.parentNode) input.parentNode.removeChild(input);
  };

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const url = input.value.trim();
      cleanup();
      onConfirm(url);
    } else if (e.key === 'Escape') {
      cleanup();
      editor.commands.focus();
    }
  });

  input.addEventListener('blur', cleanup);

  document.body.appendChild(input);
  requestAnimationFrame(() => input.focus());
}
