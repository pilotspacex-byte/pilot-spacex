'use client';

/**
 * Cost Summary Card - Display metric with trend indicator.
 *
 * T201: Shows single cost metric (Total Cost, Requests, Tokens)
 * with optional comparison to previous period and trend arrow.
 *
 * @example
 * ```tsx
 * <CostSummaryCard
 *   title="Total Cost"
 *   value="$12.34"
 *   previousValue={10.50}
 *   currentValue={12.34}
 * />
 * ```
 */

import { ArrowDown, ArrowUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface CostSummaryCardProps {
  /** Card title */
  title: string;
  /** Formatted value to display */
  value: string | number;
  /** Optional previous period value for comparison */
  previousValue?: number;
  /** Optional current period value for comparison */
  currentValue?: number;
  /** Optional description */
  description?: string;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Calculate percentage change between two values.
 */
function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return ((current - previous) / previous) * 100;
}

/**
 * Format percentage change for display.
 */
function formatPercentage(value: number): string {
  const abs = Math.abs(value);
  return `${abs.toFixed(1)}%`;
}

// ============================================================================
// Component
// ============================================================================

export function CostSummaryCard({
  title,
  value,
  previousValue,
  currentValue,
  description,
  className,
}: CostSummaryCardProps) {
  const showTrend = previousValue !== undefined && currentValue !== undefined;
  const percentageChange = showTrend ? calculatePercentageChange(currentValue, previousValue) : 0;
  const isIncrease = percentageChange > 0;
  const isDecrease = percentageChange < 0;

  return (
    <Card className={cn('hover:bg-muted/50 transition-colors', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline justify-between">
          <div className="text-2xl font-bold">{value}</div>
          {showTrend && percentageChange !== 0 && (
            <div
              className={cn('flex items-center gap-1 text-sm font-medium', {
                'text-red-600 dark:text-red-400':
                  (isIncrease && title.toLowerCase().includes('cost')) ||
                  (isDecrease && !title.toLowerCase().includes('cost')),
                'text-green-600 dark:text-green-400':
                  (isDecrease && title.toLowerCase().includes('cost')) ||
                  (isIncrease && !title.toLowerCase().includes('cost')),
              })}
            >
              {isIncrease ? <ArrowUp className="size-4" /> : <ArrowDown className="size-4" />}
              <span>{formatPercentage(percentageChange)}</span>
            </div>
          )}
        </div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

export default CostSummaryCard;
