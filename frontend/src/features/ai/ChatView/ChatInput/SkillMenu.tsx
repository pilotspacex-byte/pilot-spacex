/**
 * SkillMenu - Searchable skill selector with keyboard navigation
 * Follows shadcn/ui Command pattern for accessible menus
 */

import { memo, useCallback, useState, KeyboardEvent } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import {
  ListTodo,
  Sparkles,
  UserCog,
  Copy,
  Network,
  GitBranch,
  PenTool,
  FileText,
  History,
  Plus,
} from 'lucide-react';
import { SKILLS, SKILL_CATEGORIES } from '../constants';
import type { SkillDefinition } from '../types';

interface SkillMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (skill: SkillDefinition) => void;
  /** Called when user cancels (Esc or Backspace on empty input) - should remove trigger char */
  onCancel?: () => void;
  children: React.ReactNode;
  /** Custom class for popover content */
  popoverClassName?: string;
  /** Width in pixels for popover content */
  popoverWidth?: number;
}

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  ListTodo,
  Sparkles,
  UserCog,
  Copy,
  Network,
  GitBranch,
  PenTool,
  FileText,
  History,
  Plus,
};

export const SkillMenu = memo<SkillMenuProps>(({ open, onOpenChange, onSelect, onCancel, children, popoverClassName, popoverWidth }) => {
  const [searchValue, setSearchValue] = useState('');

  const handleSelect = useCallback(
    (skillName: string) => {
      const skill = SKILLS.find((s) => s.name === skillName);
      if (skill) {
        onSelect(skill);
        onOpenChange(false);
        setSearchValue('');
      }
    },
    [onSelect, onOpenChange]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      // Escape: close menu and remove trigger char
      if (e.key === 'Escape') {
        e.preventDefault();
        onOpenChange(false);
        onCancel?.();
        setSearchValue('');
        return;
      }
      // Backspace on empty input: close menu and remove trigger char
      if (e.key === 'Backspace' && searchValue === '') {
        e.preventDefault();
        onOpenChange(false);
        onCancel?.();
        return;
      }
    },
    [searchValue, onOpenChange, onCancel]
  );

  // Group skills by category
  const skillsByCategory = SKILL_CATEGORIES.map((category) => ({
    ...category,
    skills: SKILLS.filter((s) => s.category === category.id),
  })).filter((group) => group.skills.length > 0);

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        className={cn("p-0", popoverWidth && "w-auto", popoverClassName)}
        align="start"
        side="top"
        sideOffset={8}
        style={popoverWidth ? { width: popoverWidth } : undefined}
      >
        <Command>
          <CommandInput
            placeholder="Search skills..."
            value={searchValue}
            onValueChange={setSearchValue}
            onKeyDown={handleKeyDown}
          />
          <CommandList>
            <CommandEmpty>No skills found.</CommandEmpty>

            {skillsByCategory.map((group, idx) => {
              return (
                <div key={group.id}>
                  {idx > 0 && <CommandSeparator />}

                  <CommandGroup heading={group.label}>
                    {group.skills.map((skill) => {
                      const SkillIcon = ICON_MAP[skill.icon] || Sparkles;

                      return (
                        <CommandItem
                          key={skill.name}
                          value={skill.name}
                          onSelect={handleSelect}
                          className="flex items-start gap-3 py-3"
                        >
                          <SkillIcon className="h-4 w-4 shrink-0 mt-0.5 text-muted-foreground" />

                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-medium">\{skill.name}</span>
                            </div>

                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {skill.description}
                            </p>

                            {skill.examples && skill.examples.length > 0 && (
                              <p className="text-xs text-muted-foreground/70 italic">
                                e.g., &quot;{skill.examples[0]}&quot;
                              </p>
                            )}
                          </div>
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                </div>
              );
            })}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
});

SkillMenu.displayName = 'SkillMenu';
