/**
 * Slash command menu DOM creation and rendering.
 *
 * Extracted from SlashCommandExtension to keep files under 700 lines.
 */
import type { Editor } from '@tiptap/core';
import type { SlashCommand } from './slash-command-items';

/**
 * Helper to create a kbd element for keyboard hints
 */
function createKbd(text: string): HTMLElement {
  const kbd = document.createElement('kbd');
  kbd.textContent = text;
  kbd.style.cssText = `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    background: var(--muted, hsl(240 5% 15%));
    border: 1px solid var(--border, hsl(240 5% 22%));
    border-radius: 3px;
    font-family: inherit;
    font-size: 9px;
    font-weight: 500;
  `;
  return kbd;
}

/**
 * Creates the slash command menu element - Claude Code style (compact)
 */
export function createCommandMenu(
  commands: SlashCommand[],
  selectedIndex: number,
  editor: Editor,
  onExecute?: (command: SlashCommand) => void,
  onSelect?: (command: SlashCommand) => void
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'slash-command-menu';
  container.setAttribute('role', 'listbox');

  container.style.cssText = `
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 50;
    margin-top: 4px;
    background: var(--popover, hsl(240 10% 8%));
    border: 1px solid var(--border, hsl(240 5% 18%));
    border-radius: 6px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    min-width: 360px;
    max-width: 460px;
    font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace);
    font-size: 12px;
    overflow: hidden;
  `;

  if (commands.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'slash-command-empty';
    empty.textContent = 'No commands found';
    empty.style.cssText = `
      padding: 12px 16px;
      color: var(--muted-foreground, hsl(240 5% 45%));
    `;
    container.appendChild(empty);
    return container;
  }

  // Commands list container (scrollable, 5 items visible)
  const listContainer = document.createElement('div');
  listContainer.className = 'slash-command-list';
  listContainer.style.cssText = `
    max-height: 140px;
    overflow-y: auto;
    padding: 4px;
    scrollbar-width: thin;
    scrollbar-color: hsl(240 5% 25%) transparent;
  `;

  commands.forEach((cmd, index) => {
    const isSelected = index === selectedIndex;
    const button = document.createElement('button');
    button.className = `slash-command-item ${isSelected ? 'is-selected' : ''}`;
    button.setAttribute('role', 'option');
    button.setAttribute('aria-selected', String(isSelected));
    button.setAttribute('type', 'button');
    button.setAttribute('data-index', String(index));

    // Primary theme color for selected state
    button.style.cssText = `
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 8px;
      border: none;
      border-radius: 4px;
      background: ${isSelected ? 'var(--primary, hsl(142 70% 45%))' : 'transparent'};
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      font-size: inherit;
      line-height: 1.3;
      transition: background-color 0.1s;
    `;

    // Selection arrow indicator
    const indicator = document.createElement('span');
    indicator.className = 'slash-command-indicator';
    indicator.textContent = isSelected ? '>' : '';
    indicator.style.cssText = `
      flex-shrink: 0;
      width: 12px;
      font-size: 14px;
      font-weight: bold;
      color: ${isSelected ? 'var(--primary-foreground, white)' : 'transparent'};
    `;

    // Command name
    const cmdName = document.createElement('span');
    cmdName.className = 'slash-command-name';
    cmdName.textContent = `/${cmd.name}`;
    cmdName.style.cssText = `
      flex-shrink: 0;
      min-width: 100px;
      font-weight: 500;
      color: ${isSelected ? 'var(--primary-foreground, white)' : cmd.group === 'ai' ? 'var(--ai, hsl(210 70% 60%))' : 'var(--foreground, hsl(240 5% 85%))'};
    `;

    // Description
    const desc = document.createElement('span');
    desc.className = 'slash-command-desc';
    desc.textContent = cmd.description;
    desc.style.cssText = `
      flex: 1;
      color: ${isSelected ? 'var(--primary-foreground, white)' : 'var(--muted-foreground, hsl(240 5% 50%))'};
      opacity: ${isSelected ? '0.85' : '1'};
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    button.appendChild(indicator);
    button.appendChild(cmdName);
    button.appendChild(desc);

    // Hover effect
    button.addEventListener('mouseenter', () => {
      if (!isSelected) {
        button.style.backgroundColor = 'var(--accent, hsl(240 5% 15%))';
      }
    });
    button.addEventListener('mouseleave', () => {
      if (!isSelected) {
        button.style.backgroundColor = 'transparent';
      }
    });

    // Click handler
    button.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (onSelect) {
        onSelect(cmd);
      } else {
        cmd.execute(editor);
        onExecute?.(cmd);
      }
    });

    listContainer.appendChild(button);
  });

  container.appendChild(listContainer);

  // Footer with navigation hints
  const footer = document.createElement('div');
  footer.className = 'slash-command-footer';
  footer.style.cssText = `
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 12px;
    border-top: 1px solid var(--border, hsl(240 5% 18%));
    color: var(--muted-foreground, hsl(240 5% 40%));
    font-size: 10px;
  `;

  // Navigation hint
  const navHint = document.createElement('span');
  navHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  navHint.appendChild(createKbd('\u2191'));
  navHint.appendChild(createKbd('\u2193'));
  const navText = document.createElement('span');
  navText.textContent = ' nav';
  navHint.appendChild(navText);

  // Select hint
  const selectHint = document.createElement('span');
  selectHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  selectHint.appendChild(createKbd('\u21B5'));
  const selectText = document.createElement('span');
  selectText.textContent = ' select';
  selectHint.appendChild(selectText);

  // Close hint
  const escHint = document.createElement('span');
  escHint.style.cssText = 'display: flex; align-items: center; gap: 3px;';
  escHint.appendChild(createKbd('esc'));
  const escText = document.createElement('span');
  escText.textContent = ' close';
  escHint.appendChild(escText);

  footer.appendChild(navHint);
  footer.appendChild(selectHint);
  footer.appendChild(escHint);
  container.appendChild(footer);

  // Scroll selected item into view
  requestAnimationFrame(() => {
    const selected = listContainer.querySelector('.is-selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  });

  return container;
}
