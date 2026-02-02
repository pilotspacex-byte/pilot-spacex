'use client';

import * as React from 'react';
import { Bug, Lightbulb, Wrench, CheckSquare, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { IssueType } from '@/types';

export interface IssueTypeSelectProps {
  value: IssueType;
  onChange: (type: IssueType) => void;
  disabled?: boolean;
  className?: string;
}

const issueTypes: IssueType[] = ['bug', 'feature', 'improvement', 'task'];

const typeConfig: Record<IssueType, { icon: React.ElementType; className: string; label: string }> =
  {
    bug: { icon: Bug, className: 'text-red-500', label: 'Bug' },
    feature: { icon: Lightbulb, className: 'text-purple-500', label: 'Feature' },
    improvement: { icon: Wrench, className: 'text-blue-500', label: 'Improvement' },
    task: { icon: CheckSquare, className: 'text-gray-500', label: 'Task' },
  };

/**
 * IssueTypeSelect provides a dropdown for selecting issue type.
 * Displays Bug, Feature, Improvement, or Task with colored icons.
 *
 * @example
 * ```tsx
 * <IssueTypeSelect value={type} onChange={setType} />
 * ```
 */
export function IssueTypeSelect({
  value,
  onChange,
  disabled = false,
  className,
}: IssueTypeSelectProps) {
  const currentConfig = typeConfig[value];
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
        {issueTypes.map((type) => {
          const config = typeConfig[type];
          const Icon = config.icon;

          return (
            <DropdownMenuItem
              key={type}
              onClick={() => onChange(type)}
              className={cn('flex items-center gap-2', value === type && 'bg-accent')}
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

export default IssueTypeSelect;
