'use client';

import * as React from 'react';
import { AlertCircle, ArrowUp, ArrowDown, Minus, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { AIConfidenceTag } from '@/components/ai/AIConfidenceTag';
import type { IssuePriority } from '@/types';

export interface PrioritySuggestion {
  priority: IssuePriority;
  confidence: number;
}

export interface IssuePrioritySelectProps {
  value: IssuePriority;
  onChange: (priority: IssuePriority) => void;
  suggestion?: PrioritySuggestion | null;
  onSuggestionAccept?: () => void;
  onSuggestionReject?: () => void;
  disabled?: boolean;
  className?: string;
  /** Render only the list items without DropdownMenu wrapper (for embedding in popovers) */
  inline?: boolean;
}

const priorities: IssuePriority[] = ['urgent', 'high', 'medium', 'low', 'none'];

const priorityConfig: Record<
  IssuePriority,
  { icon: React.ElementType; className: string; label: string }
> = {
  urgent: { icon: AlertCircle, className: 'text-red-500', label: 'Urgent' },
  high: { icon: ArrowUp, className: 'text-orange-500', label: 'High' },
  medium: { icon: Minus, className: 'text-yellow-500', label: 'Medium' },
  low: { icon: ArrowDown, className: 'text-blue-500', label: 'Low' },
  none: { icon: Minus, className: 'text-gray-400', label: 'No priority' },
};

/**
 * IssuePrioritySelect provides a dropdown for selecting issue priority.
 * Supports AI suggestions with confidence indicators.
 *
 * @example
 * ```tsx
 * <IssuePrioritySelect
 *   value={priority}
 *   onChange={setPriority}
 *   suggestion={{ priority: 'high', confidence: 0.85 }}
 *   onSuggestionAccept={() => recordDecision(true)}
 * />
 * ```
 */
function PriorityOptionsList({
  value,
  onChange,
  suggestion,
  onSuggestionAccept,
  onSuggestionReject,
}: Pick<
  IssuePrioritySelectProps,
  'value' | 'onChange' | 'suggestion' | 'onSuggestionAccept' | 'onSuggestionReject'
>) {
  const handleSelect = (priority: IssuePriority) => {
    if (suggestion && priority === suggestion.priority) {
      onSuggestionAccept?.();
    } else if (suggestion && priority !== suggestion.priority) {
      onSuggestionReject?.();
    }
    onChange(priority);
  };

  return (
    <div className="flex flex-col" role="listbox" aria-label="Issue priority">
      {priorities.map((priority) => {
        const config = priorityConfig[priority];
        const Icon = config.icon;
        const isSuggested = suggestion?.priority === priority;
        const isCurrent = value === priority;
        return (
          <button
            key={priority}
            type="button"
            role="option"
            aria-selected={isCurrent}
            onClick={() => handleSelect(priority)}
            className={cn(
              'flex items-center justify-between rounded-sm px-2 py-1.5 text-sm',
              'hover:bg-accent hover:text-accent-foreground cursor-pointer',
              isCurrent && 'bg-accent'
            )}
          >
            <span className="flex items-center gap-2">
              <Icon className={cn('size-4', config.className)} />
              <span>{config.label}</span>
            </span>
            {isSuggested && !isCurrent && (
              <AIConfidenceTag confidence={suggestion.confidence} showIcon className="ml-2" />
            )}
          </button>
        );
      })}
    </div>
  );
}

export function IssuePrioritySelect({
  value,
  onChange,
  suggestion,
  onSuggestionAccept,
  onSuggestionReject,
  disabled = false,
  className,
  inline = false,
}: IssuePrioritySelectProps) {
  if (inline) {
    return (
      <PriorityOptionsList
        value={value}
        onChange={onChange}
        suggestion={suggestion}
        onSuggestionAccept={onSuggestionAccept}
        onSuggestionReject={onSuggestionReject}
      />
    );
  }

  const effectiveValue = value ?? 'none';
  const currentConfig = priorityConfig[effectiveValue];
  const CurrentIcon = currentConfig.icon;

  const handleSelect = (priority: IssuePriority) => {
    if (suggestion && priority === suggestion.priority) {
      onSuggestionAccept?.();
    } else if (suggestion && priority !== suggestion.priority) {
      onSuggestionReject?.();
    }
    onChange(priority);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className={cn('justify-between gap-2', className)}
        >
          <span className="flex items-center gap-2">
            <CurrentIcon className={cn('size-4', currentConfig.className)} />
            <span>{currentConfig.label}</span>
          </span>
          <ChevronDown className="size-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        {priorities.map((priority) => {
          const config = priorityConfig[priority];
          const Icon = config.icon;
          const isSuggested = suggestion?.priority === priority;
          const isCurrent = value === priority;

          return (
            <DropdownMenuItem
              key={priority}
              onClick={() => handleSelect(priority)}
              className="flex items-center justify-between"
            >
              <span className="flex items-center gap-2">
                <Icon className={cn('size-4', config.className)} />
                <span>{config.label}</span>
              </span>
              {isSuggested && !isCurrent && (
                <AIConfidenceTag confidence={suggestion.confidence} showIcon className="ml-2" />
              )}
              {isCurrent && !isSuggested && (
                <AIConfidenceTag variant="current" className="ml-2">
                  Current
                </AIConfidenceTag>
              )}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default IssuePrioritySelect;
