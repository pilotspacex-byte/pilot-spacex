'use client';

import * as React from 'react';
import { Check, ChevronDown, User, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
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
import { AIConfidenceTag } from '@/components/ai/AIConfidenceTag';
import type { User as UserType } from '@/types';

export interface AssigneeRecommendation {
  userId: string;
  name: string;
  confidence: number;
  reason: string;
}

export interface AssigneeSelectorProps {
  /** Currently selected assignee */
  value: UserType | null;
  /** Available team members */
  members: UserType[];
  /** AI recommendations */
  recommendations?: AssigneeRecommendation[];
  /** Called when assignee changes */
  onChange: (user: UserType | null) => void;
  /** Called when a recommendation is accepted */
  onRecommendationAccept?: (recommendation: AssigneeRecommendation) => void;
  /** Called when a recommendation is rejected */
  onRecommendationReject?: (recommendation: AssigneeRecommendation) => void;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  className?: string;
}

/**
 * Get user initials for avatar fallback.
 */
function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * AssigneeSelector provides a searchable dropdown for selecting issue assignees.
 * Supports AI recommendations with confidence indicators and reasons.
 *
 * @example
 * ```tsx
 * <AssigneeSelector
 *   value={assignee}
 *   members={teamMembers}
 *   recommendations={aiRecommendations}
 *   onChange={setAssignee}
 * />
 * ```
 */
export function AssigneeSelector({
  value,
  members,
  recommendations = [],
  onChange,
  onRecommendationAccept,
  onRecommendationReject,
  disabled = false,
  placeholder = 'Assign to...',
  className,
}: AssigneeSelectorProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  // Filter members by search
  const filteredMembers = members.filter(
    (member) =>
      member.name.toLowerCase().includes(search.toLowerCase()) ||
      member.email.toLowerCase().includes(search.toLowerCase())
  );

  // Get top recommendation
  const topRecommendation = recommendations[0];
  const showRecommendation = topRecommendation && topRecommendation.userId !== value?.id;

  const handleSelect = (member: UserType) => {
    const recommendation = recommendations.find((r) => r.userId === member.id);
    if (recommendation) {
      onRecommendationAccept?.(recommendation);
    }
    onChange(member);
    setOpen(false);
  };

  const handleClear = () => {
    onChange(null);
  };

  const handleRecommendationDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (topRecommendation) {
      onRecommendationReject?.(topRecommendation);
    }
  };

  const handleRecommendationAccept = () => {
    if (topRecommendation) {
      const member = members.find((m) => m.id === topRecommendation.userId);
      if (member) {
        handleSelect(member);
      }
    }
  };

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* AI Recommendation banner */}
      {showRecommendation && (
        <div className="flex items-center gap-2 rounded-md border border-ai/20 bg-ai/5 p-2">
          <Sparkles className="size-4 shrink-0 text-ai" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium truncate">{topRecommendation.name}</span>
              <AIConfidenceTag
                confidence={topRecommendation.confidence}
                showIcon
                className="shrink-0"
              />
            </div>
            <p className="text-xs text-muted-foreground truncate">{topRecommendation.reason}</p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleRecommendationAccept}
              className="text-ai hover:bg-ai/10"
            >
              <Check className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleRecommendationDismiss}
              className="text-muted-foreground hover:bg-muted"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Assignee selector */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            disabled={disabled}
            className="w-full justify-between gap-2"
          >
            {value ? (
              <span className="flex items-center gap-2">
                <Avatar className="size-5">
                  <AvatarImage src={value.avatarUrl} alt={value.name} />
                  <AvatarFallback className="text-[10px]">{getInitials(value.name)}</AvatarFallback>
                </Avatar>
                <span className="truncate">{value.name}</span>
              </span>
            ) : (
              <span className="flex items-center gap-2 text-muted-foreground">
                <User className="size-4" />
                {placeholder}
              </span>
            )}
            <ChevronDown className="size-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput
              placeholder="Search members..."
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandEmpty>No members found</CommandEmpty>

              {/* AI Recommendations group */}
              {recommendations.length > 0 && (
                <>
                  <CommandGroup heading="AI Recommendations">
                    {recommendations.map((rec) => {
                      const member = members.find((m) => m.id === rec.userId);
                      if (!member) return null;

                      const isSelected = value?.id === member.id;

                      return (
                        <CommandItem
                          key={rec.userId}
                          value={member.email}
                          onSelect={() => handleSelect(member)}
                          className="flex items-center justify-between"
                        >
                          <span className="flex items-center gap-2">
                            <Avatar className="size-6">
                              <AvatarImage src={member.avatarUrl} alt={member.name} />
                              <AvatarFallback className="text-[10px]">
                                {getInitials(member.name)}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex flex-col">
                              <span className="text-sm">{member.name}</span>
                              <span className="text-xs text-muted-foreground truncate max-w-32">
                                {rec.reason}
                              </span>
                            </div>
                          </span>
                          <span className="flex items-center gap-1">
                            <AIConfidenceTag
                              confidence={rec.confidence}
                              className="px-1 py-0 text-[10px]"
                            />
                            {isSelected && <Check className="size-4" />}
                          </span>
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                  <CommandSeparator />
                </>
              )}

              {/* All members group */}
              <CommandGroup heading="Team Members">
                {filteredMembers
                  .filter((member) => !recommendations.some((r) => r.userId === member.id))
                  .map((member) => {
                    const isSelected = value?.id === member.id;

                    return (
                      <CommandItem
                        key={member.id}
                        value={member.email}
                        onSelect={() => handleSelect(member)}
                        className="flex items-center justify-between"
                      >
                        <span className="flex items-center gap-2">
                          <Avatar className="size-6">
                            <AvatarImage src={member.avatarUrl} alt={member.name} />
                            <AvatarFallback className="text-[10px]">
                              {getInitials(member.name)}
                            </AvatarFallback>
                          </Avatar>
                          <span>{member.name}</span>
                        </span>
                        {isSelected && <Check className="size-4" />}
                      </CommandItem>
                    );
                  })}
              </CommandGroup>

              {/* Unassign option */}
              {value && (
                <>
                  <CommandSeparator />
                  <CommandGroup>
                    <CommandItem onSelect={handleClear} className="text-muted-foreground">
                      <X className="mr-2 size-4" />
                      Unassign
                    </CommandItem>
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default AssigneeSelector;
