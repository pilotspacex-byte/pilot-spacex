'use client';

import * as React from 'react';
import { Target, ChevronDown, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface EstimateSelectorProps {
  value: number | undefined;
  onChange: (points: number | undefined) => void;
  disabled?: boolean;
  className?: string;
}

const FIBONACCI_PRESETS = [1, 2, 3, 5, 8, 13] as const;

/**
 * EstimateSelector provides Fibonacci preset buttons for story point estimation.
 * Uses a Popover with preset values (1, 2, 3, 5, 8, 13) and a clear option.
 *
 * @example
 * ```tsx
 * <EstimateSelector value={points} onChange={setPoints} />
 * ```
 */
export function EstimateSelector({
  value,
  onChange,
  disabled = false,
  className,
}: EstimateSelectorProps) {
  const [open, setOpen] = React.useState(false);

  const handleSelect = (points: number) => {
    onChange(points);
    setOpen(false);
  };

  const handleClear = () => {
    onChange(undefined);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className={cn('justify-between gap-2', className)}
          aria-label={
            value !== undefined
              ? `Estimate: ${value} point${value !== 1 ? 's' : ''}`
              : 'Set estimate'
          }
        >
          <span className="flex items-center gap-2">
            <Target className="size-4 text-muted-foreground" />
            <span>{value !== undefined ? `${value} pt${value !== 1 ? 's' : ''}` : 'Estimate'}</span>
          </span>
          <ChevronDown className="size-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-56 p-3">
        <div className="mb-2 text-xs font-medium text-muted-foreground">Story Points</div>
        <div className="flex flex-wrap gap-1.5">
          {FIBONACCI_PRESETS.map((points) => (
            <button
              key={points}
              type="button"
              onClick={() => handleSelect(points)}
              className={cn(
                'inline-flex h-8 w-10 items-center justify-center rounded-md text-sm font-medium transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                value === points
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'bg-muted/50 text-foreground'
              )}
              aria-label={`${points} point${points !== 1 ? 's' : ''}`}
              aria-pressed={value === points}
            >
              {points}
            </button>
          ))}
        </div>
        {value !== undefined && (
          <button
            type="button"
            onClick={handleClear}
            className={cn(
              'mt-2 flex w-full items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground transition-colors',
              'hover:bg-destructive/10 hover:text-destructive',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
            )}
            aria-label="Clear estimate"
          >
            <X className="size-3" />
            Clear estimate
          </button>
        )}
      </PopoverContent>
    </Popover>
  );
}

export default EstimateSelector;
