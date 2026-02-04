/**
 * CSS styles for ghost text (add to your global stylesheet).
 *
 * Extracted from GhostTextExtension to keep files under 700 lines.
 */
export const ghostTextStyles = `
  .ghost-text-suggestion-container {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    pointer-events: none;
    user-select: none;
  }

  .ghost-text-suggestion {
    color: var(--ai, hsl(210 40% 55%));
    opacity: 0.5;
    font-style: italic;
    transition: opacity 150ms ease-out;
  }

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
  }

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

  @keyframes ghost-text-fade-in {
    from { opacity: 0; transform: translateX(-4px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes ghost-text-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes ghost-text-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @keyframes ghost-text-dots-blink {
    0% { content: ''; }
    25% { content: '.'; }
    50% { content: '..'; }
    75% { content: '...'; }
    100% { content: ''; }
  }

  @keyframes ghost-text-pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 0.8; }
  }
`;
