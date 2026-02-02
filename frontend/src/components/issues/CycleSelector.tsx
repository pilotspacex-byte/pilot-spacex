'use client';

import { RefreshCw, ChevronDown, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Cycle } from '@/types';

export interface CycleSelectorProps {
  value: string | null;
  onChange: (cycleId: string | null) => void;
  cycles: Cycle[];
  disabled?: boolean;
  className?: string;
}

function formatDateRange(startDate?: string, endDate?: string): string {
  if (!startDate && !endDate) return '';

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (startDate && endDate) {
    return `${formatDate(startDate)} \u2013 ${formatDate(endDate)}`;
  }
  if (startDate) return `From ${formatDate(startDate)}`;
  return `Until ${formatDate(endDate!)}`;
}

/**
 * CycleSelector provides a dropdown for assigning an issue to a cycle (sprint).
 * Supports null value for unassigned, highlights active cycles.
 *
 * @example
 * ```tsx
 * <CycleSelector value={cycleId} onChange={setCycleId} cycles={cycles} />
 * ```
 */
export function CycleSelector({
  value,
  onChange,
  cycles,
  disabled = false,
  className,
}: CycleSelectorProps) {
  const selectedCycle = cycles.find((c) => c.id === value);

  const triggerLabel = selectedCycle ? selectedCycle.name : 'No cycle';

  const triggerSubtext = selectedCycle
    ? formatDateRange(selectedCycle.startDate, selectedCycle.endDate)
    : undefined;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className={cn('justify-between gap-2', className)}
        >
          <span className="flex items-center gap-2 truncate">
            <RefreshCw className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate">
              {triggerLabel}
              {triggerSubtext && (
                <span className="ml-1.5 text-xs text-muted-foreground">{triggerSubtext}</span>
              )}
            </span>
          </span>
          <ChevronDown className="size-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuItem
          onClick={() => onChange(null)}
          className={cn('flex items-center gap-2', value === null && 'bg-accent')}
        >
          <X className="size-4 text-muted-foreground" />
          <span>No cycle</span>
        </DropdownMenuItem>
        {cycles.length > 0 && <DropdownMenuSeparator />}
        {cycles.map((cycle) => {
          const dateRange = formatDateRange(cycle.startDate, cycle.endDate);
          const isActive = cycle.status === 'active';

          return (
            <DropdownMenuItem
              key={cycle.id}
              onClick={() => onChange(cycle.id)}
              className={cn('flex flex-col items-start gap-0.5', value === cycle.id && 'bg-accent')}
            >
              <span className="flex w-full items-center gap-2">
                <span className="truncate font-medium">{cycle.name}</span>
                {isActive && (
                  <span className="shrink-0 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                    Active
                  </span>
                )}
              </span>
              {dateRange && <span className="text-xs text-muted-foreground">{dateRange}</span>}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default CycleSelector;
