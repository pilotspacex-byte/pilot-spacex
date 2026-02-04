/**
 * TokenBudgetRing - Compact SVG circular progress ring for session token consumption.
 *
 * Shows a 24x24 ring near the send button with color-coded thresholds:
 * - Green (<60%), Yellow (60-79%), Orange (80-94%), Red (>=95%)
 * - Pulses at >=95% budget usage via motion-safe:animate-pulse
 *
 * @module components/ui/token-budget-ring
 * @see specs/005-conversational-agent-arch/plan.md (T025-T028)
 */

import { cn } from '@/lib/utils';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';

const RADIUS = 10;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

interface TokenBudgetRingProps {
  /** Token usage percentage (0-100) */
  percentage: number;
  /** Tokens used in current session */
  tokensUsed?: number;
  /** Total token budget */
  tokenBudget?: number;
  className?: string;
}

/** Returns CSS color variable based on usage threshold. */
function getColor(pct: number): string {
  if (pct >= 95) return 'var(--destructive)';
  if (pct >= 80) return '#D98040';
  if (pct >= 60) return 'var(--warning)';
  return 'var(--primary)';
}

/** Formats a token count as "X.XK" (e.g. 3400 -> "3.4K"). */
function formatTokensK(tokens: number): string {
  return `${(tokens / 1000).toFixed(tokens % 1000 === 0 ? 0 : 1)}K`;
}

export function TokenBudgetRing({
  percentage,
  tokensUsed,
  tokenBudget,
  className,
}: TokenBudgetRingProps) {
  const clamped = Math.max(0, Math.min(100, percentage));
  const filled = (clamped / 100) * CIRCUMFERENCE;
  const color = getColor(clamped);
  const shouldPulse = clamped >= 95;

  const tooltipText =
    tokensUsed != null && tokenBudget != null
      ? `${formatTokensK(tokensUsed)} / ${formatTokensK(tokenBudget)} tokens (${Math.round(clamped)}%)`
      : `${Math.round(clamped)}% token budget used`;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <svg
          width={24}
          height={24}
          viewBox="0 0 24 24"
          role="progressbar"
          aria-valuenow={Math.round(clamped)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Token budget: ${Math.round(clamped)}% used`}
          className={cn(
            'shrink-0 cursor-default',
            shouldPulse && 'motion-safe:animate-pulse',
            className
          )}
        >
          {/* Background track */}
          <circle
            cx={12}
            cy={12}
            r={RADIUS}
            stroke="var(--border-subtle)"
            strokeWidth={2}
            fill="none"
          />
          {/* Progress arc */}
          <circle
            cx={12}
            cy={12}
            r={RADIUS}
            stroke={color}
            strokeWidth={2}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
            strokeDashoffset={0}
            transform="rotate(-90 12 12)"
          />
        </svg>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={4}>
        {tooltipText}
      </TooltipContent>
    </Tooltip>
  );
}
