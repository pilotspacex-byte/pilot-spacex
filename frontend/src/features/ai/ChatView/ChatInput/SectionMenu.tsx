/**
 * SectionMenu - Searchable section selector triggered by # in ChatInput
 * Allows users to reference specific note sections as AI context.
 * Follows shadcn/ui Command pattern (same as SkillMenu/AgentMenu).
 */

import { memo, useCallback, useState, type KeyboardEvent } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { Heading1, Heading2, Heading3 } from 'lucide-react';
import type { HeadingItem } from '@/components/editor/AutoTOC';

interface SectionMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (heading: HeadingItem) => void;
  /** Called when user cancels (Esc or Backspace on empty) - should remove trigger char */
  onCancel?: () => void;
  /** Available headings from current note */
  headings: HeadingItem[];
  children: React.ReactNode;
  /** Width in pixels for popover content */
  popoverWidth?: number;
}

const HEADING_ICONS: Record<number, React.ComponentType<{ className?: string }>> = {
  1: Heading1,
  2: Heading2,
  3: Heading3,
};

export const SectionMenu = memo<SectionMenuProps>(
  ({ open, onOpenChange, onSelect, onCancel, headings, children, popoverWidth }) => {
    const [searchValue, setSearchValue] = useState('');

    const handleSelect = useCallback(
      (headingId: string) => {
        const heading = headings.find((h) => h.id === headingId);
        if (heading) {
          onSelect(heading);
          onOpenChange(false);
          setSearchValue('');
        }
      },
      [headings, onSelect, onOpenChange]
    );

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          onOpenChange(false);
          onCancel?.();
          setSearchValue('');
          return;
        }
        if (e.key === 'Backspace' && searchValue === '') {
          e.preventDefault();
          onOpenChange(false);
          onCancel?.();
          return;
        }
      },
      [searchValue, onOpenChange, onCancel]
    );

    return (
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverTrigger asChild>{children}</PopoverTrigger>
        <PopoverContent
          className={cn('p-0', popoverWidth && 'w-auto')}
          align="start"
          side="top"
          sideOffset={8}
          style={popoverWidth ? { width: popoverWidth } : undefined}
        >
          <Command>
            <CommandInput
              placeholder="Search sections..."
              value={searchValue}
              onValueChange={setSearchValue}
              onKeyDown={handleKeyDown}
              className="h-8 text-sm"
            />
            <CommandList className="max-h-[280px]">
              <CommandEmpty>
                {headings.length === 0
                  ? 'No headings in this note. Add headings to create sections.'
                  : 'No matching sections.'}
              </CommandEmpty>

              <CommandGroup heading="Note Sections">
                {headings.map((heading) => {
                  const Icon = HEADING_ICONS[heading.level] ?? Heading1;
                  return (
                    <CommandItem
                      key={heading.id}
                      value={heading.text || 'Untitled'}
                      onSelect={() => handleSelect(heading.id)}
                      className="flex items-center gap-2 py-1.5 px-2"
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span
                        className={cn(
                          'text-sm truncate',
                          heading.level === 2 && 'pl-2',
                          heading.level === 3 && 'pl-4'
                        )}
                      >
                        {heading.text || 'Untitled'}
                      </span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  }
);

SectionMenu.displayName = 'SectionMenu';
