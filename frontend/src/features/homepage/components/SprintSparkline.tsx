'use client';

/**
 * SprintSparkline — SVG-only sparkline showing velocity trend.
 *
 * 120x32px SVG polyline with fill gradient. No external chart library.
 * Shows completion percentage and optional projected end date tooltip.
 */

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { VelocityDataPoint, Cycle } from '@/types';

export interface SprintSparklineProps {
  velocityData: VelocityDataPoint[];
  averageVelocity: number;
  activeCycle: Cycle | null;
  isLoading?: boolean;
  className?: string;
}

const WIDTH = 120;
const HEIGHT = 32;
const PADDING = 2;

export function SprintSparkline({
  velocityData,
  averageVelocity,
  activeCycle,
  isLoading = false,
  className,
}: SprintSparklineProps) {
  const points = useMemo(() => {
    if (velocityData.length < 2) return '';

    const values = velocityData.map((d) => d.velocity);
    const max = Math.max(...values, 1);
    const drawWidth = WIDTH - PADDING * 2;
    const drawHeight = HEIGHT - PADDING * 2;

    return values
      .map((v, i) => {
        const x = PADDING + (i / (values.length - 1)) * drawWidth;
        const y = PADDING + drawHeight - (v / max) * drawHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }, [velocityData]);

  const fillPoints = useMemo(() => {
    if (!points) return '';
    // Close path at bottom for gradient fill
    const drawWidth = WIDTH - PADDING * 2;
    return `${PADDING},${HEIGHT - PADDING} ${points} ${PADDING + drawWidth},${HEIGHT - PADDING}`;
  }, [points]);

  // Compute completion for active cycle
  const completionPct = useMemo(() => {
    if (!activeCycle) return null;
    const total = activeCycle.metrics?.totalIssues ?? 0;
    const completed = activeCycle.metrics?.completedIssues ?? 0;
    if (total === 0) return 0;
    return Math.round((completed / total) * 100);
  }, [activeCycle]);

  if (isLoading) {
    return <span className="h-8 w-[120px] animate-pulse rounded bg-muted/30" aria-hidden="true" />;
  }

  if (velocityData.length < 2 && !activeCycle) {
    return null;
  }

  const tooltipText = activeCycle
    ? `${activeCycle.name}: ${completionPct}% complete (avg velocity: ${averageVelocity.toFixed(1)})`
    : `Average velocity: ${averageVelocity.toFixed(1)}`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className={cn(
            'inline-flex items-center gap-2 rounded-md border border-border-subtle px-2.5 py-1.5',
            'motion-safe:transition-colors hover:bg-accent/50',
            className
          )}
          role="img"
          aria-label={tooltipText}
        >
          {velocityData.length >= 2 && (
            <svg
              width={WIDTH}
              height={HEIGHT}
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              className="shrink-0"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="sparkline-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.2" />
                  <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.02" />
                </linearGradient>
              </defs>
              <polygon points={fillPoints} fill="url(#sparkline-fill)" />
              <polyline
                points={points}
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}

          {completionPct !== null && (
            <span className="text-xs tabular-nums text-muted-foreground">{completionPct}%</span>
          )}
        </div>
      </TooltipTrigger>
      <TooltipContent side="top">
        <p className="text-xs">{tooltipText}</p>
      </TooltipContent>
    </Tooltip>
  );
}
