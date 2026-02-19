'use client';

/**
 * Date Range Selector - Preset and custom date range selection.
 *
 * T206: Provides preset ranges (Today, 7d, 30d, 90d, This Month)
 * and custom date picker for flexible cost analytics filtering.
 *
 * @example
 * ```tsx
 * <DateRangeSelector
 *   onSelect={(range) => console.log(range)}
 *   currentRange={{ start: new Date(), end: new Date() }}
 * />
 * ```
 */

import { useState } from 'react';
import { Calendar, CalendarDays, CalendarRange } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { format, subDays, startOfMonth, isToday, isSameDay } from 'date-fns';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface DateRange {
  start: Date;
  end: Date;
}

export interface DateRangeSelectorProps {
  /** Callback when date range is selected */
  onSelect: (range: DateRange) => void;
  /** Current active date range */
  currentRange: DateRange;
  /** Additional class name */
  className?: string;
}

type PresetOption = 'today' | '7d' | '30d' | '90d' | 'month';

interface PresetConfig {
  label: string;
  value: PresetOption;
  icon: typeof Calendar;
  getRange: () => DateRange;
}

// ============================================================================
// Preset Configurations
// ============================================================================

const PRESET_OPTIONS: PresetConfig[] = [
  {
    label: 'Today',
    value: 'today',
    icon: Calendar,
    getRange: () => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return { start: today, end: new Date() };
    },
  },
  {
    label: 'Last 7 days',
    value: '7d',
    icon: CalendarDays,
    getRange: () => ({ start: subDays(new Date(), 7), end: new Date() }),
  },
  {
    label: 'Last 30 days',
    value: '30d',
    icon: CalendarDays,
    getRange: () => ({ start: subDays(new Date(), 30), end: new Date() }),
  },
  {
    label: 'Last 90 days',
    value: '90d',
    icon: CalendarRange,
    getRange: () => ({ start: subDays(new Date(), 90), end: new Date() }),
  },
  {
    label: 'This month',
    value: 'month',
    icon: CalendarRange,
    getRange: () => ({ start: startOfMonth(new Date()), end: new Date() }),
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if a date range matches a preset.
 */
function matchesPreset(range: DateRange, preset: PresetConfig): boolean {
  const presetRange = preset.getRange();
  return isSameDay(range.start, presetRange.start) && isSameDay(range.end, presetRange.end);
}

/**
 * Format date range for display.
 */
function formatDateRange(range: DateRange): string {
  if (isToday(range.start) && isToday(range.end)) {
    return 'Today';
  }

  const startStr = format(range.start, 'MMM d');
  const endStr = format(range.end, 'MMM d, yyyy');

  return `${startStr} – ${endStr}`;
}

// ============================================================================
// Component
// ============================================================================

export function DateRangeSelector({ onSelect, currentRange, className }: DateRangeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Find active preset if any
  const activePreset = PRESET_OPTIONS.find((preset) => matchesPreset(currentRange, preset));

  const handlePresetSelect = (preset: PresetConfig) => {
    const range = preset.getRange();
    onSelect(range);
    setIsOpen(false);
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" className="justify-start text-left font-normal">
            <CalendarRange className="mr-2 size-4" />
            <span>{formatDateRange(currentRange)}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <div className="flex flex-col">
            <div className="p-2 border-b">
              <p className="text-xs font-medium text-muted-foreground px-2 py-1.5">Preset Ranges</p>
            </div>
            <div className="p-2 space-y-1">
              {PRESET_OPTIONS.map((preset) => {
                const Icon = preset.icon;
                const isActive = activePreset?.value === preset.value;

                return (
                  <Button
                    key={preset.value}
                    variant={isActive ? 'secondary' : 'ghost'}
                    size="sm"
                    className={cn('w-full justify-start', isActive && 'bg-primary/10 text-primary')}
                    onClick={() => handlePresetSelect(preset)}
                  >
                    <Icon className="mr-2 size-4" />
                    {preset.label}
                  </Button>
                );
              })}
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export default DateRangeSelector;
