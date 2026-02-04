/**
 * Ghost text DOM widget creation for inline suggestions and loading state.
 *
 * Extracted from GhostTextExtension to keep files under 700 lines.
 */

/**
 * Creates a ghost text decoration widget with Tab hint
 */
export function createGhostTextWidget(text: string, className: string): HTMLElement {
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
  hint.textContent = 'Tab \u21B9';
  container.appendChild(hint);

  return container;
}

/**
 * Creates an AI-styled loading indicator widget with shimmer effect
 */
export function createLoadingWidget(): HTMLElement {
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

  // AI icon using CSS instead of SVG for safety
  const icon = document.createElement('span');
  icon.className = 'ghost-text-loader-icon';
  icon.textContent = '\u2726';
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
 * Extract the next word from a string (including trailing space)
 */
export function getNextWord(text: string): string {
  const trimmed = text.trimStart();
  const match = trimmed.match(/^(\S+\s*)/);
  if (match && match[1] !== undefined) {
    return match[1];
  }
  return trimmed || '';
}
