/**
 * Hook for tracking elapsed time with rAF-based 1Hz updates.
 *
 * Uses requestAnimationFrame throttled to 1Hz for CPU efficiency.
 * rAF pauses when tab is hidden (RD-001), preventing drift and saving resources.
 *
 * @module hooks/useElapsedTime
 */
import { useState, useEffect, useCallback } from 'react';

/**
 * Format elapsed milliseconds into a human-readable string.
 *
 * @param elapsedMs - Elapsed time in milliseconds
 * @returns Formatted string: "0s", "3.2s", "1m 12s"
 */
function formatElapsed(elapsedMs: number): string {
  const totalSeconds = elapsedMs / 1000;

  if (totalSeconds < 60) {
    if (totalSeconds < 10) {
      return `${totalSeconds.toFixed(1)}s`;
    }
    return `${Math.floor(totalSeconds)}s`;
  }

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}m ${seconds}s`;
}

/**
 * Track elapsed time from a given start timestamp.
 *
 * Uses rAF loop throttled to 1Hz for efficient updates.
 * Returns "0s" when inactive or startTimestamp is null.
 *
 * @param startTimestamp - Unix timestamp (ms) when timing started, or null
 * @param isActive - Whether the timer is currently running
 * @returns Formatted elapsed time string
 */
export function useElapsedTime(startTimestamp: number | null, isActive: boolean): string {
  const [elapsed, setElapsed] = useState('0s');

  const resetElapsed = useCallback(() => {
    setElapsed('0s');
  }, []);

  useEffect(() => {
    if (!isActive || startTimestamp === null) {
      // Reset via microtask to avoid synchronous setState in effect body
      queueMicrotask(resetElapsed);
      return;
    }

    // Capture non-null value for closure
    const start = startTimestamp;
    let rafId: number | null = null;
    let lastUpdate = 0;

    function tick(now: number) {
      // First tick or 1Hz throttle: update display
      if (lastUpdate === 0 || now - lastUpdate >= 1000) {
        lastUpdate = now;
        const currentElapsed = Date.now() - start;
        setElapsed(formatElapsed(currentElapsed));
      }
      rafId = requestAnimationFrame(tick);
    }

    // First rAF fires quickly (~16ms) for near-immediate initialization
    rafId = requestAnimationFrame(tick);

    return () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
    };
  }, [isActive, startTimestamp, resetElapsed]);

  return elapsed;
}
