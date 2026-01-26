'use client';

/**
 * Cost Trends Chart - Line chart showing cost over time.
 *
 * T203: Displays cost trends with configurable timeframe,
 * tooltips with details, and responsive design.
 *
 * @example
 * ```tsx
 * <CostTrendsChart
 *   data={[{ date: '2026-01-20', total_cost_usd: 1.23, request_count: 45 }]}
 * />
 * ```
 */

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { format, parseISO } from 'date-fns';
import type { CostTrendData } from '@/stores/ai/CostStore';
import type { TooltipProps } from 'recharts';

// ============================================================================
// Types
// ============================================================================

export interface CostTrendsChartProps {
  /** Trend data points */
  data: CostTrendData[];
  /** Additional class name */
  className?: string;
}

interface CustomTooltipProps extends TooltipProps<number, string> {
  active?: boolean;
  payload?: Array<{
    payload: CostTrendData;
  }>;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format cost for display.
 */
function formatCost(cost: number): string {
  if (cost < 0.01) return '<$0.01';
  return `$${cost.toFixed(2)}`;
}

/**
 * Format date for axis display (MMM d).
 */
function formatAxisDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'MMM d');
  } catch {
    return dateStr;
  }
}

/**
 * Format date for tooltip (full format).
 */
function formatTooltipDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy');
  } catch {
    return dateStr;
  }
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Custom tooltip content component.
 */
function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload as CostTrendData;
  if (!data) return null;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="font-semibold text-sm">{formatTooltipDate(data.date)}</p>
      <div className="mt-1 space-y-1">
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Cost:</span>
          <span className="font-medium font-mono">{formatCost(data.total_cost_usd)}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Requests:</span>
          <span className="font-medium">{data.request_count.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Avg/Request:</span>
          <span className="font-medium font-mono">
            {formatCost(data.request_count > 0 ? data.total_cost_usd / data.request_count : 0)}
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Component
// ============================================================================

export function CostTrendsChart({ data, className }: CostTrendsChartProps) {
  const hasData = data && data.length > 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Cost Trends</CardTitle>
        <CardDescription>Daily AI usage costs over time</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <p className="text-sm">No trend data available for this period</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={formatAxisDate}
                className="text-xs"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <YAxis
                tickFormatter={(value) => `$${value.toFixed(2)}`}
                className="text-xs"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="total_cost_usd"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#costGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default CostTrendsChart;
