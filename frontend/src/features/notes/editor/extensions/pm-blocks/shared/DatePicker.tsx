'use client';

/**
 * DatePicker - Date input with calendar popup and overdue indicator.
 * Used by checklist due dates and PM block date fields.
 *
 * Shows a red badge when the date is in the past and the item is not completed.
 *
 * FR-015: Checklist items MUST support due dates with overdue indicators.
 * Overdue logic: dueDate < now && !checked
 */
import { useState, useMemo } from 'react';
import { CalendarIcon, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface DatePickerProps {
  value: Date | null;
  onChange: (date: Date | null) => void;
  /** When true, overdue styling is suppressed (item is done) */
  isCompleted?: boolean;
  disabled?: boolean;
  placeholder?: string;
  /** Compact mode for inline block use */
  compact?: boolean;
  className?: string;
}

function formatShortDate(date: Date): string {
  const now = new Date();
  const isCurrentYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    ...(isCurrentYear ? {} : { year: 'numeric' }),
  });
}

/**
 * DatePicker renders a date trigger button with calendar popup.
 * Displays a red overdue badge when the date has passed and `isCompleted` is false.
 *
 * @example
 * ```tsx
 * <DatePicker
 *   value={dueDate}
 *   onChange={setDueDate}
 *   isCompleted={isChecked}
 *   compact
 * />
 * ```
 */
export function DatePicker({
  value,
  onChange,
  isCompleted = false,
  disabled = false,
  placeholder = 'Set date...',
  compact = false,
  className,
}: DatePickerProps) {
  const [open, setOpen] = useState(false);

  const isOverdue = useMemo(() => {
    if (!value || isCompleted) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dueDate = new Date(value);
    dueDate.setHours(0, 0, 0, 0);
    return dueDate < today;
  }, [value, isCompleted]);

  const handleSelect = (date: Date | undefined) => {
    onChange(date ?? null);
    setOpen(false);
  };

  const handleClear = (e: React.SyntheticEvent) => {
    e.stopPropagation();
    onChange(null);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size={compact ? 'icon-sm' : 'sm'}
          disabled={disabled}
          aria-label={value ? `Due date: ${formatShortDate(value)}` : placeholder}
          className={cn(
            compact ? 'h-6 gap-1 px-1' : 'gap-2 justify-start',
            isOverdue && 'text-destructive hover:text-destructive',
            className
          )}
        >
          <CalendarIcon
            className={cn(compact ? 'size-3' : 'size-4', isOverdue && 'text-destructive')}
          />
          {value ? (
            <span className="flex items-center gap-1">
              <span className={cn('text-xs', isOverdue && 'font-medium')}>
                {formatShortDate(value)}
              </span>
              {isOverdue && (
                <span
                  className="inline-flex items-center rounded-full bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium text-destructive"
                  aria-label="Overdue"
                >
                  Overdue
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
                aria-label="Clear date"
              >
                <X className="size-3 text-muted-foreground" />
              </span>
            </span>
          ) : (
            !compact && <span className="text-xs text-muted-foreground">{placeholder}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value ?? undefined}
          onSelect={handleSelect}
          defaultMonth={value ?? undefined}
        />
      </PopoverContent>
    </Popover>
  );
}
