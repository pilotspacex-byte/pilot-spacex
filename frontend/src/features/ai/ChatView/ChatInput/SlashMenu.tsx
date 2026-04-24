/**
 * SlashMenu — chip-styled command palette anchored at the chat composer caret.
 *
 * Phase 87 Plan 02 (Wave 2). Driven by the 11-command registry exported from
 * `extensions/slash-extension`. Pure presentation + keyboard navigation; the
 * `query` prop is fed externally by ChatInput's `/`-detection state machine.
 *
 * Per UI-SPEC §3:
 * - Container: 360×360 max, rounded-xl, bg-popover, shadow-md
 * - Row: h-9, gap-3, mono keyword + description
 * - Keyboard: ↑/↓ navigate (wrap), Enter select, Esc close
 *
 * @module features/ai/ChatView/ChatInput/SlashMenu
 */

import { memo, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import {
  CalendarDays,
  CheckSquare,
  FileText,
  GitCommit,
  Hash,
  Network,
  Newspaper,
  Plug,
  Settings,
  Users,
  Wand2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { filterCommands, type SlashCommand } from './extensions/slash-extension';

/** Static lookup keeps Lucide imports tree-shake-friendly. */
const ICONS: Record<string, React.ComponentType<{ className?: string; style?: CSSProperties }>> = {
  Hash,
  CheckSquare,
  FileText,
  GitCommit,
  Wand2,
  Users,
  Settings,
  Plug,
  Network,
  CalendarDays,
  Newspaper,
};

export interface SlashMenuProps {
  /** Substring filter — chars typed in the composer after `/`, without the slash. */
  query: string;
  /** Invoked when the user picks a command (mouse click or Enter). */
  onSelect: (command: SlashCommand) => void;
  /** Invoked when the user dismisses the menu (Escape). */
  onClose: () => void;
}

export const SlashMenu = memo<SlashMenuProps>(({ query, onSelect, onClose }) => {
  const items = useMemo(() => filterCommands(query), [query]);
  const [selectedIdx, setSelectedIdx] = useState(0);

  // Reset highlight when filter changes (selectedIdx may now be out of bounds).
  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  // Window-level keyboard handler so the contenteditable retains focus while
  // the menu owns nav keys. Capture phase ensures we run before TipTap-style
  // editor handlers in sibling components.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (items.length === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx((i) => (i + 1) % items.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx((i) => (i - 1 + items.length) % items.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        onSelect(items[selectedIdx]);
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [items, selectedIdx, onSelect, onClose]);

  return (
    <div
      data-slash-menu
      role="listbox"
      aria-label="Slash commands"
      className="w-[360px] max-h-[360px] rounded-xl border border-border bg-popover shadow-md p-1 overflow-hidden"
    >
      {items.length === 0 ? (
        <div className="h-9 flex items-center justify-center text-[13px] text-muted-foreground">
          {`No commands match "${query}"`}
        </div>
      ) : (
        <ul className="max-h-[340px] overflow-y-auto m-0 p-0 list-none">
          {items.map((cmd, i) => {
            const Icon = ICONS[cmd.iconName] ?? Hash;
            const isSelected = i === selectedIdx;
            const iconStyle: CSSProperties | undefined =
              cmd.iconColor === 'muted' ? undefined : { color: cmd.iconColor };
            const iconClass =
              cmd.iconColor === 'muted' ? 'h-4 w-4 text-muted-foreground' : 'h-4 w-4';
            return (
              <li
                key={cmd.id}
                data-slash-row={cmd.id}
                data-testid={`slash-row-${cmd.id}`}
                role="option"
                aria-selected={isSelected}
                onMouseEnter={() => setSelectedIdx(i)}
                onMouseDown={(e) => {
                  // Prevent the contenteditable from losing focus before we dispatch.
                  e.preventDefault();
                }}
                onClick={() => onSelect(cmd)}
                className={cn(
                  'flex items-center gap-3 h-9 px-3 rounded-md cursor-pointer',
                  isSelected ? 'bg-accent' : 'hover:bg-accent/40',
                )}
              >
                <Icon className={iconClass} style={iconStyle} />
                <span className="font-mono text-[11px] font-semibold">{cmd.keyword}</span>
                <span className="text-[13px] font-normal text-muted-foreground truncate">
                  {cmd.description}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
});

SlashMenu.displayName = 'SlashMenu';
