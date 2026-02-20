'use client';

import { useCallback, useState, type ChangeEvent } from 'react';
import { cn } from '@/lib/utils';
import { EstimateSelector } from '@/components/issues';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type EffortMode = 'points' | 'hours';

export interface EffortFieldProps {
  estimatePoints?: number;
  estimateHours?: number;
  onPointsChange: (points: number | undefined) => void;
  onHoursChange: (hours: number | undefined) => void;
  disabled?: boolean;
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Determine initial mode: prefer whichever field has data, default points. */
function deriveInitialMode(_points?: number, hours?: number): EffortMode {
  if (hours != null && hours > 0) return 'hours';
  return 'points';
}

// ---------------------------------------------------------------------------
// EffortField
// ---------------------------------------------------------------------------

/**
 * Unified effort estimation field with a [Points | Hours] segmented toggle.
 *
 * - Points mode renders the existing `EstimateSelector` (Fibonacci presets).
 * - Hours mode renders a numeric input (step 0.5, 0-9999.9).
 * - Toggling preserves both values independently.
 * - Hours displays "Not set" placeholder when empty (never "0.0").
 */
export function EffortField({
  estimatePoints,
  estimateHours,
  onPointsChange,
  onHoursChange,
  disabled = false,
  className,
}: EffortFieldProps) {
  const [mode, setMode] = useState<EffortMode>(() =>
    deriveInitialMode(estimatePoints, estimateHours)
  );

  const handleHoursBlur = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      if (raw === '') {
        onHoursChange(undefined);
        return;
      }
      const val = parseFloat(raw);
      if (isNaN(val)) return;
      const clamped = Math.min(9999.9, Math.max(0, val));
      const rounded = Math.round(clamped * 2) / 2;
      onHoursChange(rounded);
    },
    [onHoursChange]
  );

  return (
    <div className={cn('flex w-full items-center gap-2', className)}>
      {/* Segmented toggle */}
      <div
        className="inline-flex shrink-0 rounded-lg border border-input bg-muted/50 p-0.5"
        role="radiogroup"
        aria-label="Effort estimation mode"
      >
        <button
          type="button"
          role="radio"
          aria-checked={mode === 'points'}
          onClick={() => setMode('points')}
          disabled={disabled}
          className={cn(
            'rounded-md px-2 py-0.5 text-xs font-medium transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
            mode === 'points'
              ? 'bg-background shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Points
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={mode === 'hours'}
          onClick={() => setMode('hours')}
          disabled={disabled}
          className={cn(
            'rounded-md px-2 py-0.5 text-xs font-medium transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
            mode === 'hours'
              ? 'bg-background shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Hours
        </button>
      </div>

      {/* Active field */}
      {mode === 'points' ? (
        <EstimateSelector
          value={estimatePoints}
          onChange={onPointsChange}
          disabled={disabled}
          className="h-8 min-w-0 flex-1"
        />
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-1">
          <input
            key={estimateHours ?? 'empty'}
            type="number"
            min={0}
            max={9999.9}
            step={0.5}
            defaultValue={estimateHours != null && estimateHours > 0 ? estimateHours : ''}
            onBlur={handleHoursBlur}
            disabled={disabled}
            aria-label="Time estimate in hours"
            placeholder="Not set"
            className={cn(
              'h-8 w-full rounded-[10px] border border-input bg-background px-3 text-sm',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'text-foreground placeholder:text-muted-foreground'
            )}
          />
          <span className="shrink-0 text-xs text-muted-foreground">h</span>
        </div>
      )}
    </div>
  );
}
