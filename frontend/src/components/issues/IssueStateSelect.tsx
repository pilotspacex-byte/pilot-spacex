'use client';

import * as React from 'react';
import {
  Circle,
  CircleDot,
  CircleDashed,
  PlayCircle,
  CheckCircle2,
  XCircle,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { IssueState } from '@/types';

export interface IssueStateSelectProps {
  value: IssueState;
  onChange: (state: IssueState) => void;
  disabled?: boolean;
  className?: string;
}

const states: IssueState[] = ['backlog', 'todo', 'in_progress', 'in_review', 'done', 'cancelled'];

const stateConfig: Record<
  IssueState,
  { icon: React.ElementType; className: string; bgClassName: string; label: string }
> = {
  backlog: {
    icon: CircleDashed,
    className: 'text-gray-500',
    bgClassName: 'bg-gray-100 dark:bg-gray-800',
    label: 'Backlog',
  },
  todo: {
    icon: Circle,
    className: 'text-blue-500',
    bgClassName: 'bg-blue-100 dark:bg-blue-900',
    label: 'Todo',
  },
  in_progress: {
    icon: PlayCircle,
    className: 'text-yellow-500',
    bgClassName: 'bg-yellow-100 dark:bg-yellow-900',
    label: 'In Progress',
  },
  in_review: {
    icon: CircleDot,
    className: 'text-purple-500',
    bgClassName: 'bg-purple-100 dark:bg-purple-900',
    label: 'In Review',
  },
  done: {
    icon: CheckCircle2,
    className: 'text-green-500',
    bgClassName: 'bg-green-100 dark:bg-green-900',
    label: 'Done',
  },
  cancelled: {
    icon: XCircle,
    className: 'text-red-500',
    bgClassName: 'bg-red-100 dark:bg-red-900',
    label: 'Cancelled',
  },
};

/**
 * IssueStateSelect provides a dropdown for selecting issue state.
 * Follows the state machine: Backlog -> Todo -> In Progress -> In Review -> Done/Cancelled
 *
 * @example
 * ```tsx
 * <IssueStateSelect
 *   value={state}
 *   onChange={setState}
 * />
 * ```
 */
export function IssueStateSelect({
  value,
  onChange,
  disabled = false,
  className,
}: IssueStateSelectProps) {
  const currentConfig = stateConfig[value];
  const CurrentIcon = currentConfig.icon;

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
        {states.slice(0, 4).map((state) => {
          const config = stateConfig[state];
          const Icon = config.icon;

          return (
            <DropdownMenuItem
              key={state}
              onClick={() => onChange(state)}
              className={cn('flex items-center gap-2', value === state && 'bg-accent')}
            >
              <Icon className={cn('size-4', config.className)} />
              <span>{config.label}</span>
            </DropdownMenuItem>
          );
        })}
        <DropdownMenuSeparator />
        {states.slice(4).map((state) => {
          const config = stateConfig[state];
          const Icon = config.icon;

          return (
            <DropdownMenuItem
              key={state}
              onClick={() => onChange(state)}
              className={cn('flex items-center gap-2', value === state && 'bg-accent')}
            >
              <Icon className={cn('size-4', config.className)} />
              <span>{config.label}</span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default IssueStateSelect;
