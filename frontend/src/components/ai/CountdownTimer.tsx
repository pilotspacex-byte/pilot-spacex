'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface CountdownTimerProps {
  /** ISO date string when the countdown expires */
  endTime: string;
  /** Callback when timer expires */
  onExpire?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Show in compact format (1h 30m) vs verbose (1 hour 30 minutes) */
  compact?: boolean;
  /** Show progress bar */
  showProgress?: boolean;
  /** Total duration in milliseconds (for progress calculation) */
  totalDuration?: number;
}

interface TimeRemaining {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  total: number;
}

function calculateTimeRemaining(endTime: string): TimeRemaining {
  const total = new Date(endTime).getTime() - Date.now();

  if (total <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0, total: 0 };
  }

  const seconds = Math.floor((total / 1000) % 60);
  const minutes = Math.floor((total / 1000 / 60) % 60);
  const hours = Math.floor((total / (1000 * 60 * 60)) % 24);
  const days = Math.floor(total / (1000 * 60 * 60 * 24));

  return { days, hours, minutes, seconds, total };
}

function formatTimeRemaining(time: TimeRemaining, compact: boolean): string {
  if (time.total <= 0) {
    return compact ? 'Expired' : 'Expired';
  }

  const parts: string[] = [];

  if (time.days > 0) {
    parts.push(compact ? `${time.days}d` : `${time.days} day${time.days !== 1 ? 's' : ''}`);
  }

  if (time.hours > 0) {
    parts.push(compact ? `${time.hours}h` : `${time.hours} hour${time.hours !== 1 ? 's' : ''}`);
  }

  if (time.minutes > 0 && time.days === 0) {
    parts.push(
      compact ? `${time.minutes}m` : `${time.minutes} minute${time.minutes !== 1 ? 's' : ''}`
    );
  }

  // Only show seconds if less than 5 minutes remaining
  if (time.seconds > 0 && time.hours === 0 && time.minutes < 5 && time.days === 0) {
    parts.push(
      compact ? `${time.seconds}s` : `${time.seconds} second${time.seconds !== 1 ? 's' : ''}`
    );
  }

  if (parts.length === 0) {
    return compact ? '<1m' : 'Less than a minute';
  }

  return parts.join(compact ? ' ' : ' ');
}

function getUrgencyClass(time: TimeRemaining): string {
  // Less than 1 hour - critical
  if (time.total > 0 && time.total < 60 * 60 * 1000) {
    return 'text-destructive';
  }
  // Less than 6 hours - warning
  if (time.total > 0 && time.total < 6 * 60 * 60 * 1000) {
    return 'text-amber-600 dark:text-amber-400';
  }
  // Normal
  return 'text-muted-foreground';
}

/**
 * CountdownTimer displays remaining time until expiration.
 * Updates every second when less than 5 minutes, otherwise every minute.
 */
export function CountdownTimer({
  endTime,
  onExpire,
  className,
  compact = true,
  showProgress = false,
  totalDuration,
}: CountdownTimerProps) {
  const [timeRemaining, setTimeRemaining] = React.useState<TimeRemaining>(() =>
    calculateTimeRemaining(endTime)
  );
  const hasExpiredRef = React.useRef(false);

  React.useEffect(() => {
    hasExpiredRef.current = false;

    const updateTimer = () => {
      const remaining = calculateTimeRemaining(endTime);
      setTimeRemaining(remaining);

      if (remaining.total <= 0 && !hasExpiredRef.current) {
        hasExpiredRef.current = true;
        onExpire?.();
      }
    };

    updateTimer();

    // Update interval based on urgency
    const getInterval = () => {
      const remaining = calculateTimeRemaining(endTime);
      if (remaining.total <= 0) return null;
      // Less than 5 minutes: update every second
      if (remaining.total < 5 * 60 * 1000) return 1000;
      // Less than 1 hour: update every 10 seconds
      if (remaining.total < 60 * 60 * 1000) return 10000;
      // Otherwise: update every minute
      return 60000;
    };

    let intervalId: NodeJS.Timeout | null = null;

    const scheduleUpdate = () => {
      const interval = getInterval();
      if (interval !== null) {
        intervalId = setTimeout(() => {
          updateTimer();
          scheduleUpdate();
        }, interval);
      }
    };

    scheduleUpdate();

    return () => {
      if (intervalId) clearTimeout(intervalId);
    };
  }, [endTime, onExpire]);

  const progressPercentage = React.useMemo(() => {
    if (!showProgress || !totalDuration || totalDuration <= 0) return 0;
    const remaining = Math.max(0, timeRemaining.total);
    return Math.round((remaining / totalDuration) * 100);
  }, [showProgress, totalDuration, timeRemaining.total]);

  return (
    <span
      className={cn('tabular-nums', getUrgencyClass(timeRemaining), className)}
      role="timer"
      aria-live="polite"
      aria-label={`Time remaining: ${formatTimeRemaining(timeRemaining, false)}`}
    >
      {formatTimeRemaining(timeRemaining, compact)}
      {showProgress && totalDuration && (
        <span className="ml-2 inline-block h-1 w-16 overflow-hidden rounded-full bg-muted align-middle">
          <span
            className={cn(
              'block h-full transition-all duration-500',
              progressPercentage > 50
                ? 'bg-emerald-500'
                : progressPercentage > 20
                  ? 'bg-amber-500'
                  : 'bg-destructive'
            )}
            style={{ width: `${progressPercentage}%` }}
          />
        </span>
      )}
    </span>
  );
}
