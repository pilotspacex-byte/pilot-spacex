/**
 * SkillMenu - Searchable skill selector with keyboard navigation
 * Follows shadcn/ui Command pattern for accessible menus
 * Search stays in the chat input (external query prop, no CommandInput)
 */

import { memo, useCallback } from 'react';
import type { RefObject } from 'react';
import {
  Command,
  CommandEmpty,
  CommandGroup,
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
  FilePlus,
  Newspaper,
  BookOpen,
  LayoutDashboard,
} from 'lucide-react';
import { SKILLS, SKILL_CATEGORIES } from '../constants';
import type { SkillDefinition } from '../types';

interface SkillMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (skill: SkillDefinition) => void;
  /** Called when user cancels (Esc or Backspace on empty input) - should remove trigger char */
  onCancel?: () => void;
  /** Dynamic skills from API. Falls back to hardcoded SKILLS if not provided. */
  skills?: SkillDefinition[];
  children: React.ReactNode;
  /** Custom class for popover content */
  popoverClassName?: string;
  /** Width in pixels for popover content */
  popoverWidth?: number;
  /** External search query — typed in the chat input after '/'. No CommandInput rendered. */
  searchQuery?: string;
  /** Ref forwarded to the cmdk Command root DOM node for keyboard event forwarding */
  commandRef?: RefObject<HTMLDivElement | null>;
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
  FilePlus,
  Newspaper,
  BookOpen,
  LayoutDashboard,
};

export const SkillMenu = memo<SkillMenuProps>(
  ({
    open,
    onOpenChange,
    onSelect,
    onCancel: _onCancel,
    skills: skillsProp,
    children,
    popoverClassName,
    popoverWidth,
    searchQuery = '',
    commandRef,
  }) => {
    const activeSkills = skillsProp ?? SKILLS;

    const handleSelect = useCallback(
      (skillName: string) => {
        const skill = activeSkills.find((s) => s.name === skillName);
        if (skill) {
          onSelect(skill);
          onOpenChange(false);
        }
      },
      [activeSkills, onSelect, onOpenChange]
    );

    // Filter skills by searchQuery (name or description match)
    const filteredSkills = searchQuery
      ? activeSkills.filter(
          (s) =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.description.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : activeSkills;

    // Group filtered skills by category
    const skillsByCategory = SKILL_CATEGORIES.map((category) => ({
      ...category,
      skills: filteredSkills.filter((s) => s.category === category.id),
    })).filter((group) => group.skills.length > 0);

    return (
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverTrigger asChild>{children}</PopoverTrigger>
        <PopoverContent
          className={cn('p-0', popoverWidth && 'w-auto', popoverClassName)}
          align="start"
          side="top"
          sideOffset={8}
          style={popoverWidth ? { width: popoverWidth } : undefined}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onCloseAutoFocus={(e) => e.preventDefault()}
        >
          <Command ref={commandRef} filter={() => 1}>
            <CommandList className="max-h-[280px]">
              {searchQuery && filteredSkills.length === 0 && (
                <CommandEmpty>No skills found.</CommandEmpty>
              )}

              {skillsByCategory.map((group, idx) => {
                return (
                  <div key={group.id}>
                    {idx > 0 && <CommandSeparator className="my-0.5" />}

                    <CommandGroup heading={group.label}>
                      {group.skills.map((skill) => {
                        const SkillIcon = ICON_MAP[skill.icon] || Sparkles;

                        return (
                          <CommandItem
                            key={skill.name}
                            value={skill.name}
                            onSelect={handleSelect}
                            className="flex items-center gap-2 py-1.5 px-2"
                          >
                            <SkillIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />

                            <span className="font-mono text-xs font-medium shrink-0">
                              /{skill.name}
                            </span>

                            <span className="text-xs text-muted-foreground truncate">
                              {skill.description}
                            </span>
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
  }
);

SkillMenu.displayName = 'SkillMenu';
