/**
 * TokenRing - SVG circular progress indicator for session token usage.
 *
 * Displays token consumption as a circular arc in the chat header.
 * Color changes at threshold breakpoints to warn users approaching the limit:
 *   - < 80%:   --primary  (teal   #29a386)
 *   - 80-95%:  --warning  (amber  #d9853f)
 *   - >= 95%:  --destructive (red #d9534f)
 *
 * Hidden when totalTokens is 0 (no active session).
 * Animated via CSS transition on stroke-dashoffset (respects prefers-reduced-motion).
 *
 * @module features/ai/ChatView/TokenRing
 */

import React from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

/** Diameter 32px — radius 13, stroke-width 3, inset by 3px on each side */
const RADIUS = 13;
const STROKE_WIDTH = 3;
const SIZE = 32;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

interface TokenRingProps {
  totalTokens: number;
  budgetTokens?: number; // default 8000
}

/** Format token count to compact label: "4.2k" for 4200, "500" for 500. */
function formatLabel(tokens: number): string {
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  }
  return String(tokens);
}

/** Format token count with locale comma grouping. */
function formatLocale(tokens: number): string {
  return tokens.toLocaleString();
}

/** Determine the arc stroke color based on usage percentage. */
function getStrokeColor(percent: number): string {
  if (percent >= 95) return 'var(--destructive)';
  if (percent >= 80) return 'var(--warning)';
  return 'var(--primary)';
}

/**
 * TokenRing — circular progress SVG for session token budget.
 * Returns null when totalTokens is 0 (hidden when no active session).
 */
export const TokenRing = React.memo<TokenRingProps>(
  ({ totalTokens, budgetTokens = 8000 }) => {
    // Hidden when no active session
    if (!totalTokens) return null;

    const percent = Math.min((totalTokens / budgetTokens) * 100, 100);
    const strokeColor = getStrokeColor(percent);
    const dashOffset = CIRCUMFERENCE - (percent / 100) * CIRCUMFERENCE;
    const label = formatLabel(totalTokens);
    const isWarning = percent >= 80;

    const tooltipText = `${formatLocale(totalTokens)} / ${formatLocale(budgetTokens)} tokens used this session${isWarning ? ' — approaching session limit' : ''}`;

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            role="progressbar"
            aria-valuenow={totalTokens}
            aria-valuemin={0}
            aria-valuemax={budgetTokens}
            aria-label="Session token usage"
            className="relative flex items-center justify-center flex-shrink-0"
            style={{ width: SIZE, height: SIZE }}
          >
            <svg
              width={SIZE}
              height={SIZE}
              viewBox={`0 0 ${SIZE} ${SIZE}`}
              aria-hidden="true"
            >
              {/* Track circle — full circumference, ai-muted color */}
              <circle
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke="var(--ai-muted)"
                strokeWidth={STROKE_WIDTH}
              />
              {/* Progress arc — starts at 12 o'clock via -90deg rotation */}
              <circle
                data-testid="token-ring-progress"
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke={strokeColor}
                strokeWidth={STROKE_WIDTH}
                strokeLinecap="round"
                strokeDasharray={CIRCUMFERENCE}
                strokeDashoffset={dashOffset}
                style={{
                  transform: 'rotate(-90deg)',
                  transformOrigin: '50% 50%',
                  transition: 'stroke-dashoffset 400ms ease-out, stroke 200ms ease',
                }}
                className="motion-reduce:transition-none"
              />
            </svg>
            {/* Center label — Geist Mono 12px weight 400 */}
            <span
              className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-normal leading-none text-foreground tabular-nums select-none"
              aria-hidden="true"
            >
              {label}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {tooltipText}
        </TooltipContent>
      </Tooltip>
    );
  }
);

TokenRing.displayName = 'TokenRing';
