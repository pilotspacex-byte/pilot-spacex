'use client';

/**
 * MemberPicker - Compact workspace member selector with avatars.
 * Used by checklist assignee fields and RACI matrix cells.
 *
 * Renders as a small trigger button that opens a searchable dropdown
 * of workspace members. Designed for inline use within TipTap blocks.
 *
 * FR-014: Checklist items MUST support assignee assignment from workspace members.
 */
import { useState, useCallback } from 'react';
import { Check, User, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { UserBrief } from '@/types';

export interface MemberPickerProps {
  value: UserBrief | null;
  members: UserBrief[];
  onChange: (member: UserBrief | null) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Compact mode renders a smaller trigger (for inline block use) */
  compact?: boolean;
  className?: string;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * MemberPicker renders a searchable dropdown for selecting a workspace member.
 * Supports compact mode for inline use within TipTap PM blocks.
 *
 * @example
 * ```tsx
 * <MemberPicker
 *   value={assignee}
 *   members={workspaceMembers}
 *   onChange={setAssignee}
 *   compact
 * />
 * ```
 */
export function MemberPicker({
  value,
  members,
  onChange,
  disabled = false,
  placeholder = 'Assign...',
  compact = false,
  className,
}: MemberPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredMembers = members.filter(
    (member) =>
      (member.displayName ?? member.email).toLowerCase().includes(search.toLowerCase()) ||
      member.email.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = useCallback(
    (member: UserBrief) => {
      onChange(member);
      setOpen(false);
    },
    [onChange]
  );

  const handleClear = useCallback(
    (e: React.SyntheticEvent) => {
      e.stopPropagation();
      onChange(null);
    },
    [onChange]
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size={compact ? 'icon-sm' : 'sm'}
          disabled={disabled}
          aria-label={value ? `Assigned to ${value.displayName ?? value.email}` : placeholder}
          className={cn(compact ? 'h-6 gap-1 px-1' : 'gap-2 justify-between', className)}
        >
          {value ? (
            <span className="flex items-center gap-1">
              <Avatar className={compact ? 'size-4' : 'size-5'}>
                <AvatarFallback className="text-[8px]">
                  {getInitials(value.displayName ?? value.email)}
                </AvatarFallback>
              </Avatar>
              {!compact && (
                <span className="truncate max-w-24 text-xs">
                  {value.displayName ?? value.email}
                </span>
              )}
              <span
                role="button"
                tabIndex={0}
                onClick={handleClear}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleClear(e);
                  }
                }}
                className="ml-0.5 rounded-full p-0.5 hover:bg-muted cursor-pointer"
                aria-label="Unassign"
              >
                <X className="size-3 text-muted-foreground" />
              </span>
            </span>
          ) : (
            <span className="flex items-center gap-1 text-muted-foreground">
              <User className={compact ? 'size-3' : 'size-4'} />
              {!compact && <span className="text-xs">{placeholder}</span>}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-56 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search members..." value={search} onValueChange={setSearch} />
          <CommandList>
            <CommandEmpty>No members found</CommandEmpty>
            <CommandGroup>
              {filteredMembers.map((member) => {
                const isSelected = value?.id === member.id;
                return (
                  <CommandItem
                    key={member.id}
                    value={member.email}
                    onSelect={() => handleSelect(member)}
                    className="flex items-center justify-between"
                  >
                    <span className="flex items-center gap-2">
                      <Avatar className="size-5">
                        <AvatarFallback className="text-[9px]">
                          {getInitials(member.displayName ?? member.email)}
                        </AvatarFallback>
                      </Avatar>
                      <span className="text-sm truncate">{member.displayName ?? member.email}</span>
                    </span>
                    {isSelected && <Check className="size-4 shrink-0" />}
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
