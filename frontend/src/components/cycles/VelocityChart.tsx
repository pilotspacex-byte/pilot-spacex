'use client';

/**
 * VelocityChart - Bar chart showing completed points per cycle with trend line.
 *
 * T166: Displays velocity metrics for sprint planning.
 *
 * @example
 * ```tsx
 * <VelocityChart
 *   data={cycleStore.velocityData}
 *   isLoading={cycleStore.isLoadingVelocity}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { VelocityChartData, VelocityDataPoint } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface VelocityChartProps {
  /** Velocity data from API */
  data: VelocityChartData | null;
  /** Whether data is loading */
  isLoading?: boolean;
  /** Number of cycles to display */
  cycleLimit?: number;
  /** Show committed points comparison */
  showCommitted?: boolean;
  /** Custom height */
  height?: number;
  /** Additional class name */
  className?: string;
}

interface ChartDataPoint {
  name: string;
  completed: number;
  committed: number;
  velocity: number;
  cycleId: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

function calculateTrend(dataPoints: VelocityDataPoint[]): 'up' | 'down' | 'stable' {
  if (dataPoints.length < 2) return 'stable';

  const recent = dataPoints.slice(-3);
  const avgRecent = recent.reduce((sum, d) => sum + d.velocity, 0) / recent.length;

  const older = dataPoints.slice(0, -3);
  if (older.length === 0) return 'stable';

  const avgOlder = older.reduce((sum, d) => sum + d.velocity, 0) / older.length;

  const diff = avgRecent - avgOlder;
  const threshold = avgOlder * 0.1; // 10% threshold

  if (diff > threshold) return 'up';
  if (diff < -threshold) return 'down';
  return 'stable';
}

function formatNumber(value: number): string {
  return value.toFixed(1);
}

// ============================================================================
// Custom Tooltip
// ============================================================================

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;

  const completed = payload.find((p) => p.dataKey === 'completed');
  const committed = payload.find((p) => p.dataKey === 'committed');

  return (
    <div className="rounded-lg border bg-background p-3 shadow-lg">
      <p className="mb-2 font-medium">{label}</p>
      <div className="space-y-1 text-sm">
        {completed && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Completed:</span>
            <span className="font-medium text-green-600">{formatNumber(completed.value)} pts</span>
          </div>
        )}
        {committed && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Committed:</span>
            <span className="font-medium text-blue-600">{formatNumber(committed.value)} pts</span>
          </div>
        )}
        {completed && committed && (
          <div className="flex items-center justify-between gap-4 border-t pt-1">
            <span className="text-muted-foreground">Completion:</span>
            <span
              className={cn(
                'font-medium',
                completed.value >= committed.value ? 'text-green-600' : 'text-amber-600'
              )}
            >
              {((completed.value / committed.value) * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function VelocityChartSkeleton({ height }: { height: number }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-5 w-24" />
      </div>
      <Skeleton className="w-full" style={{ height }} />
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function VelocityChartEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertCircle className="size-12 text-muted-foreground/50 mb-4" />
      <p className="text-muted-foreground">No velocity data available</p>
      <p className="text-sm text-muted-foreground/60 mt-1">
        Complete at least one cycle to see velocity trends
      </p>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const VelocityChart = observer(function VelocityChart({
  data,
  isLoading = false,
  cycleLimit = 10,
  showCommitted = true,
  height = 300,
  className,
}: VelocityChartProps) {
  // Transform data for chart
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    if (!data?.dataPoints) return [];

    return data.dataPoints.slice(-cycleLimit).map((point) => ({
      name: point.cycleName,
      completed: point.completedPoints,
      committed: point.committedPoints,
      velocity: point.velocity,
      cycleId: point.cycleId,
    }));
  }, [data, cycleLimit]);

  // Calculate trend
  const trend = React.useMemo(
    () => (data?.dataPoints ? calculateTrend(data.dataPoints) : 'stable'),
    [data]
  );

  // Trend icon
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  const trendColor =
    trend === 'up'
      ? 'text-success'
      : trend === 'down'
        ? 'text-destructive'
        : 'text-muted-foreground';

  const trendLabel =
    trend === 'up'
      ? 'Velocity improving'
      : trend === 'down'
        ? 'Velocity declining'
        : 'Velocity stable';

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Velocity</CardTitle>
          <CardDescription>Points completed per cycle</CardDescription>
        </CardHeader>
        <CardContent>
          <VelocityChartSkeleton height={height} />
        </CardContent>
      </Card>
    );
  }

  if (!data || chartData.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Velocity</CardTitle>
          <CardDescription>Points completed per cycle</CardDescription>
        </CardHeader>
        <CardContent>
          <VelocityChartEmpty />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Velocity</CardTitle>
            <CardDescription>Points completed per cycle</CardDescription>
          </div>

          <div className="flex items-center gap-4">
            {/* Average velocity */}
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Average</p>
                    <p className="text-2xl font-bold">{formatNumber(data.averageVelocity)}</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  Average velocity over last {chartData.length} cycles
                </TooltipContent>
              </UITooltip>
            </TooltipProvider>

            {/* Trend indicator */}
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      'flex items-center gap-1 rounded-full px-2 py-1',
                      trend === 'up' && 'bg-success/10',
                      trend === 'down' && 'bg-destructive/10',
                      trend === 'stable' && 'bg-muted'
                    )}
                  >
                    <TrendIcon className={cn('size-4', trendColor)} />
                  </div>
                </TooltipTrigger>
                <TooltipContent>{trendLabel}</TooltipContent>
              </UITooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground"
              label={{
                value: 'Points',
                angle: -90,
                position: 'insideLeft',
                className: 'fill-muted-foreground text-xs',
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {/* Average velocity reference line */}
            <ReferenceLine
              y={data.averageVelocity}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="5 5"
              label={{
                value: `Avg: ${formatNumber(data.averageVelocity)}`,
                position: 'right',
                className: 'fill-muted-foreground text-xs',
              }}
            />

            {/* Committed points bar (if enabled) */}
            {showCommitted && (
              <Bar
                dataKey="committed"
                name="Committed"
                fill="hsl(var(--primary) / 0.3)"
                radius={[4, 4, 0, 0]}
              />
            )}

            {/* Completed points bar */}
            <Bar
              dataKey="completed"
              name="Completed"
              fill="hsl(var(--primary))"
              radius={[4, 4, 0, 0]}
            />

            {/* Trend line */}
            <Line
              type="monotone"
              dataKey="velocity"
              name="Velocity"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              dot={{ fill: 'hsl(var(--chart-2))', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

export default VelocityChart;
