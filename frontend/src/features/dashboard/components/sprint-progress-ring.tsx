'use client';

/**
 * SprintProgressRing — SVG circular progress indicator for sprint completion.
 *
 * Shows completion percentage in Fraunces display font at the center of the ring.
 * Animated stroke-dashoffset transition (500ms ease-out, motion-safe).
 * Fully accessible with ARIA progressbar role.
 *
 * Phase 77 — Implementation Dashboard (DSH-01, UIX-04)
 */
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SprintProgressRingProps {
  percent: number;
  className?: string;
}

const RADIUS = 52;
const STROKE_WIDTH = 8;
const VIEW_BOX_SIZE = 120;
const CENTER = VIEW_BOX_SIZE / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export const SprintProgressRing = React.memo(function SprintProgressRing({
  percent,
  className,
}: SprintProgressRingProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const dashOffset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;

  return (
    <div
      className={cn('flex flex-col items-center gap-1', className)}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Sprint completion"
    >
      <svg
        viewBox={`0 0 ${VIEW_BOX_SIZE} ${VIEW_BOX_SIZE}`}
        className="motion-safe:transition-all w-[120px] h-[120px]"
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE_WIDTH}
          className="stroke-muted"
        />
        {/* Progress arc */}
        <circle
          cx={CENTER}
          cy={CENTER}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE_WIDTH}
          stroke="hsl(var(--primary))"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          style={{
            transformOrigin: 'center',
            transform: 'rotate(-90deg)',
            transition: 'stroke-dashoffset 500ms ease-out',
          }}
        />
        {/* Center text: percentage */}
        <text
          x={CENTER}
          y={CENTER - 4}
          textAnchor="middle"
          dominantBaseline="middle"
          className="font-display"
          style={{
            fontSize: '28px',
            fontWeight: 400,
            lineHeight: 1.1,
            fill: 'hsl(var(--foreground))',
            fontFamily: 'var(--font-display)',
          }}
        >
          {clamped}%
        </text>
        {/* Below percentage: "Complete" label */}
        <text
          x={CENTER}
          y={CENTER + 20}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fontSize: '12px',
            fontWeight: 600,
            fill: 'hsl(var(--muted-foreground))',
            fontFamily: 'var(--font-sans)',
          }}
        >
          Complete
        </text>
      </svg>
    </div>
  );
});

SprintProgressRing.displayName = 'SprintProgressRing';
