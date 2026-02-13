/**
 * MermaidNodeView — ProseMirror NodeView for mermaid code blocks.
 *
 * Renders a single unified card that toggles between:
 *   - Preview mode (default): rendered SVG chart via MermaidPreview React component
 *   - Code mode: editable ProseMirror <pre><code> (contentDOM)
 *
 * The toggle is managed by MermaidPreview's onViewModeChange callback.
 * The React root lifecycle is tied to the NodeView's create/destroy.
 */
import type { Node as ProseMirrorNode } from '@tiptap/pm/model';
import type { EditorView } from '@tiptap/pm/view';
import { createElement } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MermaidPreview } from './pm-blocks/MermaidPreview';

/** Detect current theme from document class list. */
function getCurrentTheme(): 'light' | 'dark' {
  if (typeof document === 'undefined') return 'light';
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

interface MermaidNodeViewOptions {
  node: ProseMirrorNode;
  view: EditorView;
  getPos: (() => number | undefined) | boolean;
}

/**
 * Creates a ProseMirror NodeView for mermaid code blocks.
 * Returns { dom, contentDOM, update, destroy, stopEvent }.
 */
export function createMermaidNodeView({ node }: MermaidNodeViewOptions) {
  let currentCode = node.textContent;
  let viewMode: 'preview' | 'code' = 'preview';

  // --- DOM Structure ---
  // Outer wrapper: single card for the unified block
  const dom = document.createElement('div');
  dom.className = 'mermaid-unified-block';
  dom.setAttribute('data-testid', 'mermaid-unified-block');

  // Persistent toolbar: always visible toggle between Preview/Code
  const toolbar = document.createElement('div');
  toolbar.className = 'mermaid-toolbar';

  const previewBtn = document.createElement('button');
  previewBtn.type = 'button';
  previewBtn.className = 'mermaid-toggle-btn active';
  previewBtn.textContent = 'Preview';
  previewBtn.setAttribute('aria-label', 'Preview diagram');

  const codeBtn = document.createElement('button');
  codeBtn.type = 'button';
  codeBtn.className = 'mermaid-toggle-btn';
  codeBtn.textContent = 'Code';
  codeBtn.setAttribute('aria-label', 'View source code');

  toolbar.appendChild(previewBtn);
  toolbar.appendChild(codeBtn);

  // Preview container: React MermaidPreview mounts here
  const previewContainer = document.createElement('div');
  previewContainer.className = 'mermaid-preview-section';

  // Code container: ProseMirror-managed <pre><code>
  const codeContainer = document.createElement('pre');
  codeContainer.className = 'mermaid-code-section';
  const contentDOM = document.createElement('code');
  codeContainer.appendChild(contentDOM);

  // Assemble: toolbar, then preview, then code
  dom.appendChild(toolbar);
  dom.appendChild(previewContainer);
  dom.appendChild(codeContainer);

  // Default: preview mode — hide code, show preview
  codeContainer.style.display = 'none';

  // --- React Root ---
  const reactRoot: Root = createRoot(previewContainer);

  function updateToolbarState() {
    if (viewMode === 'preview') {
      previewBtn.classList.add('active');
      codeBtn.classList.remove('active');
    } else {
      previewBtn.classList.remove('active');
      codeBtn.classList.add('active');
    }
  }

  /** Toggle view mode — used by toolbar buttons and MermaidPreview callback. */
  function setViewMode(mode: 'preview' | 'code') {
    if (mode === viewMode) return;
    viewMode = mode;
    updateToolbarState();
    if (mode === 'code') {
      previewContainer.style.display = 'none';
      codeContainer.style.display = '';
    } else {
      previewContainer.style.display = '';
      codeContainer.style.display = 'none';
      // Re-render preview with latest code (may have been edited)
      renderPreview();
    }
  }

  previewBtn.addEventListener('click', () => setViewMode('preview'));
  codeBtn.addEventListener('click', () => setViewMode('code'));

  function renderPreview() {
    reactRoot.render(
      createElement(MermaidPreview, {
        code: currentCode,
        theme: getCurrentTheme(),
        onViewModeChange: setViewMode,
        // Hide wrapper card + internal toggle — NodeView provides both
        className:
          '!border-0 !rounded-none !shadow-none !my-0 !ring-0 [&_[data-testid=mermaid-view-toggle]]:hidden',
      })
    );
  }

  // Initial render
  renderPreview();

  return {
    dom,
    contentDOM,

    /** Called by ProseMirror when the node updates. Return false to recreate. */
    update(updatedNode: ProseMirrorNode): boolean {
      if (updatedNode.type.name !== 'codeBlock') return false;
      if ((updatedNode.attrs.language as string) !== 'mermaid') return false;

      const newCode = updatedNode.textContent;
      if (newCode !== currentCode) {
        currentCode = newCode;
        // Re-render preview if visible, otherwise defer to next toggle
        if (viewMode === 'preview') {
          renderPreview();
        }
      }
      return true;
    },

    /** Cleanup React root when NodeView is destroyed. */
    destroy() {
      // Defer unmount to avoid React "unmount during render" warnings
      const root = reactRoot;
      queueMicrotask(() => root.unmount());
    },

    /**
     * Control which events ProseMirror intercepts.
     * - Events in codeContainer: let ProseMirror handle (editing)
     * - Events in previewContainer: stop (React handles toggle/tooltip/export)
     */
    stopEvent(event: Event): boolean {
      const target = event.target as Node;
      if (codeContainer.contains(target)) return false;
      if (toolbar.contains(target)) return true;
      if (previewContainer.contains(target)) return true;
      return false;
    },

    /**
     * Ignore all DOM mutations outside contentDOM. Without this, React
     * renders and style toggles trigger ProseMirror's MutationObserver
     * → NodeView recreation → infinite loop.
     */
    ignoreMutation(mutation: MutationRecord | { type: 'selection'; target: Node }): boolean {
      // Only let ProseMirror observe mutations inside contentDOM (text edits)
      if (contentDOM.contains(mutation.target)) return false;
      return true;
    },
  };
}
