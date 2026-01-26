/**
 * Ghost Text Decoration - ProseMirror decoration utilities
 * Per T122: CSS styles and decoration factory for ghost text
 */
import { Decoration } from '@tiptap/pm/view';

/**
 * Creates a ghost text decoration widget at the specified position
 *
 * @param position - Document position where ghost text should appear
 * @param text - Ghost text suggestion content
 * @param className - CSS class for styling (default: 'ghost-text-suggestion')
 * @returns ProseMirror Decoration widget
 *
 * @example
 * ```typescript
 * const decoration = createGhostTextDecoration(42, 'world', 'ghost-text-suggestion');
 * const decorations = DecorationSet.create(doc, [decoration]);
 * ```
 */
export function createGhostTextDecoration(
  position: number,
  text: string,
  className = 'ghost-text-suggestion'
): Decoration {
  return Decoration.widget(position, () => createGhostTextWidget(text, className), { side: 1 });
}

/**
 * Creates the DOM element for ghost text with Tab hint
 * Includes both the suggestion text and keyboard hint badge
 */
function createGhostTextWidget(text: string, className: string): HTMLElement {
  const container = document.createElement('span');
  container.className = `${className}-container`;
  container.setAttribute('data-ghost-text', 'true');
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = `
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    pointer-events: none;
    user-select: none;
    animation: ghost-text-fade-in 200ms ease-out;
  `;

  // Ghost text suggestion
  const textSpan = document.createElement('span');
  textSpan.className = className;
  textSpan.textContent = text;
  textSpan.style.cssText = `
    color: var(--ai, hsl(210 40% 55%));
    opacity: 0.5;
    font-style: italic;
    transition: opacity 150ms ease-out;
  `;
  container.appendChild(textSpan);

  // Tab hint badge
  const hint = document.createElement('span');
  hint.className = 'ghost-text-hint';
  hint.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 500;
    font-style: normal;
    color: var(--ai, hsl(210 40% 55%));
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border: 1px solid var(--ai-border, hsl(210 40% 55% / 0.2));
    border-radius: 4px;
    opacity: 0.8;
    white-space: nowrap;
    transition: opacity 150ms ease-out;
  `;
  hint.textContent = 'Tab ↹';
  container.appendChild(hint);

  return container;
}

/**
 * Creates a loading indicator decoration widget
 *
 * @param position - Document position where loading indicator should appear
 * @returns ProseMirror Decoration widget
 *
 * @example
 * ```typescript
 * const decoration = createLoadingDecoration(42);
 * const decorations = DecorationSet.create(doc, [decoration]);
 * ```
 */
export function createLoadingDecoration(position: number): Decoration {
  return Decoration.widget(position, createLoadingWidget, { side: 1 });
}

/**
 * Creates the DOM element for loading indicator with shimmer effect
 */
function createLoadingWidget(): HTMLElement {
  const container = document.createElement('span');
  container.className = 'ghost-text-loader';
  container.setAttribute('aria-hidden', 'true');
  container.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 4px;
    padding: 2px 8px;
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border-radius: 4px;
    animation: ghost-text-fade-in 200ms ease-out;
  `;

  // AI icon (sparkle)
  const icon = document.createElement('span');
  icon.className = 'ghost-text-loader-icon';
  icon.textContent = '✦';
  icon.style.cssText = `
    display: inline-flex;
    font-size: 12px;
    color: var(--ai, hsl(210 40% 55%));
    animation: ghost-text-spin 2s linear infinite;
  `;
  container.appendChild(icon);

  // Loading text with shimmer
  const text = document.createElement('span');
  text.className = 'ghost-text-loader-text';
  text.textContent = 'Thinking';
  text.style.cssText = `
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
    background: linear-gradient(
      90deg,
      var(--ai, hsl(210 40% 55%)) 0%,
      var(--ai-hover, hsl(210 40% 45%)) 50%,
      var(--ai, hsl(210 40% 55%)) 100%
    );
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: ghost-text-shimmer 1.5s ease-in-out infinite;
  `;
  container.appendChild(text);

  // Animated dots
  const dots = document.createElement('span');
  dots.className = 'ghost-text-dots';
  dots.style.cssText = `
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
    animation: ghost-text-dots-blink 1s steps(4, end) infinite;
  `;
  dots.textContent = '...';
  container.appendChild(dots);

  return container;
}

/**
 * CSS styles for ghost text decorations
 * Add to your global stylesheet or component styles
 *
 * Includes:
 * - Base ghost text styling with AI color variables
 * - Loading indicator animations
 * - Dark mode support via CSS variables
 * - Accessibility considerations (aria-hidden, pointer-events: none)
 */
export const ghostTextStyles = `
  /* Ghost text suggestion container */
  .ghost-text-suggestion-container {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    pointer-events: none;
    user-select: none;
  }

  /* Ghost text suggestion text */
  .ghost-text-suggestion {
    color: var(--ai, hsl(210 40% 55%));
    opacity: 0.5;
    font-style: italic;
    transition: opacity 150ms ease-out;
  }

  /* Keyboard hint badge */
  .ghost-text-hint {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 500;
    font-style: normal;
    color: var(--ai, hsl(210 40% 55%));
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border: 1px solid var(--ai-border, hsl(210 40% 55% / 0.2));
    border-radius: 4px;
    opacity: 0.8;
    white-space: nowrap;
    transition: opacity 150ms ease-out;
  }

  /* Loading indicator */
  .ghost-text-loader {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 4px;
    padding: 2px 8px;
    background: var(--ai-muted, hsl(210 40% 55% / 0.1));
    border-radius: 4px;
  }

  .ghost-text-loader-icon {
    display: inline-flex;
    font-size: 12px;
    color: var(--ai, hsl(210 40% 55%));
  }

  .ghost-text-loader-text {
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
  }

  .ghost-text-dots {
    font-size: 11px;
    font-weight: 500;
    color: var(--ai, hsl(210 40% 55%));
  }

  /* Animations */
  @keyframes ghost-text-fade-in {
    from {
      opacity: 0;
      transform: translateX(-4px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes ghost-text-spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes ghost-text-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  @keyframes ghost-text-dots-blink {
    0% {
      content: '';
    }
    25% {
      content: '.';
    }
    50% {
      content: '..';
    }
    75% {
      content: '...';
    }
    100% {
      content: '';
    }
  }

  @keyframes ghost-text-pulse {
    0%,
    100% {
      opacity: 0.3;
    }
    50% {
      opacity: 0.8;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .ghost-text-suggestion {
      color: var(--ai, hsl(210 50% 70%));
      opacity: 0.6;
    }

    .ghost-text-hint {
      color: var(--ai, hsl(210 50% 70%));
      background: var(--ai-muted, hsl(210 50% 70% / 0.15));
      border-color: var(--ai-border, hsl(210 50% 70% / 0.25));
    }

    .ghost-text-loader {
      background: var(--ai-muted, hsl(210 50% 70% / 0.15));
    }

    .ghost-text-loader-icon,
    .ghost-text-loader-text,
    .ghost-text-dots {
      color: var(--ai, hsl(210 50% 70%));
    }
  }
`;
