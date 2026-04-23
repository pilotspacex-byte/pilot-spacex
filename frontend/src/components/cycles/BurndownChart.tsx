'use client';

/**
 * BurndownChart - Line chart showing ideal vs actual progress in a cycle.
 *
 * T167: Displays burndown metrics for sprint tracking.
 *
 * @example
 * ```tsx
 * <BurndownChart
 *   data={cycleStore.burndownData}
 *   isLoading={cycleStore.isLoadingBurndown}
 *   showPoints={true}
 * />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
  ReferenceLine,
} from 'recharts';
import { AlertTriangle, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { BurndownChartData } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface BurndownChartProps {
  /** Burndown data from API */
  data: BurndownChartData | null;
  /** Whether data is loading */
  isLoading?: boolean;
  /** Show points (true) or issues (false) */
  showPoints?: boolean;
  /** Allow toggling between points and issues */
  allowToggle?: boolean;
  /** Custom height */
  height?: number;
  /** Additional class name */
  className?: string;
}

type ChartMode = 'points' | 'issues';

interface ChartDataPoint {
  date: string;
  dateFormatted: string;
  ideal: number;
  actual: number;
  remaining: number;
  isToday: boolean;
  isFuture: boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isToday(dateStr: string): boolean {
  const date = new Date(dateStr);
  const today = new Date();
  return (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  );
}

function isFutureDate(dateStr: string): boolean {
  return new Date(dateStr) > new Date();
}

function calculateStatus(
  data: BurndownChartData,
  mode: ChartMode
): 'on-track' | 'ahead' | 'behind' | 'complete' {
  const today = new Date().toISOString().split('T')[0];
  const todayPoint = data.dataPoints.find((p) => p.date === today);

  if (!todayPoint) {
    // If no data point for today, find the closest past point
    const pastPoints = data.dataPoints.filter((p) => today && p.date <= today);
    if (pastPoints.length === 0) return 'on-track';
    const latest = pastPoints[pastPoints.length - 1];
    if (!latest) return 'on-track';

    const actual = mode === 'points' ? latest.remainingPoints : latest.remainingIssues;
    const ideal = mode === 'points' ? latest.idealPoints : latest.idealIssues;

    if (actual === 0) return 'complete';
    if (actual < ideal) return 'ahead';
    if (actual > ideal * 1.1) return 'behind';
    return 'on-track';
  }

  const actual = mode === 'points' ? todayPoint.remainingPoints : todayPoint.remainingIssues;
  const ideal = mode === 'points' ? todayPoint.idealPoints : todayPoint.idealIssues;

  if (actual === 0) return 'complete';
  if (actual < ideal) return 'ahead';
  if (actual > ideal * 1.1) return 'behind';
  return 'on-track';
}

function getStatusConfig(status: 'on-track' | 'ahead' | 'behind' | 'complete') {
  switch (status) {
    case 'complete':
      return {
        icon: CheckCircle2,
        label: 'Complete',
        color: 'text-green-500',
        bgColor: 'bg-green-100 dark:bg-green-900/30',
      };
    case 'ahead':
      return {
        icon: CheckCircle2,
        label: 'Ahead of schedule',
        color: 'text-green-500',
        bgColor: 'bg-green-100 dark:bg-green-900/30',
      };
    case 'behind':
      return {
        icon: AlertTriangle,
        label: 'Behind schedule',
        color: 'text-amber-500',
        bgColor: 'bg-amber-100 dark:bg-amber-900/30',
      };
    case 'on-track':
    default:
      return {
        icon: Clock,
        label: 'On track',
        color: 'text-blue-500',
        bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      };
  }
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
  mode: ChartMode;
}

function CustomTooltip({ active, payload, label, mode }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;

  const ideal = payload.find((p) => p.dataKey === 'ideal');
  const actual = payload.find((p) => p.dataKey === 'actual');

  const unit = mode === 'points' ? 'pts' : 'issues';
  const diff = actual && ideal ? ideal.value - actual.value : 0;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-lg">
      <p className="mb-2 font-medium">{label}</p>
      <div className="space-y-1 text-sm">
        {ideal && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Ideal:</span>
            <span className="font-medium">
              {ideal.value.toFixed(0)} {unit}
            </span>
          </div>
        )}
        {actual && (
          <div className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground">Actual:</span>
            <span className="font-medium">
              {actual.value.toFixed(0)} {unit}
            </span>
          </div>
        )}
        {actual && ideal && (
          <div className="flex items-center justify-between gap-4 border-t pt-1">
            <span className="text-muted-foreground">Variance:</span>
            <span className={cn('font-medium', diff >= 0 ? 'text-green-600' : 'text-amber-600')}>
              {diff >= 0 ? '+' : ''}
              {diff.toFixed(0)} {unit}
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

function BurndownChartSkeleton({ height }: { height: number }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-8 w-24" />
      </div>
      <Skeleton className="w-full" style={{ height }} />
    </div>
  );
}

// ============================================================================
// Empty State
// ============================================================================

function BurndownChartEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <AlertCircle className="size-12 text-muted-foreground/50 mb-4" />
      <p className="text-muted-foreground">No burndown data available</p>
      <p className="text-sm text-muted-foreground/60 mt-1">
        Start the cycle to see progress tracking
      </p>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const BurndownChart = observer(function BurndownChart({
  data,
  isLoading = false,
  showPoints = true,
  allowToggle = true,
  height = 300,
  className,
}: BurndownChartProps) {
  const [mode, setMode] = React.useState<ChartMode>(showPoints ? 'points' : 'issues');

  // Transform data for chart
  const chartData: ChartDataPoint[] = React.useMemo(() => {
    if (!data?.dataPoints) return [];

    return data.dataPoints.map((point) => ({
      date: point.date,
      dateFormatted: formatDate(point.date),
      ideal: mode === 'points' ? point.idealPoints : point.idealIssues,
      actual: mode === 'points' ? point.remainingPoints : point.remainingIssues,
      remaining: mode === 'points' ? point.remainingPoints : point.remainingIssues,
      isToday: isToday(point.date),
      isFuture: isFutureDate(point.date),
    }));
  }, [data, mode]);

  // Filter actual data to only show past and present
  const actualData = React.useMemo(() => chartData.filter((d) => !d.isFuture), [chartData]);

  // Calculate status
  const status = React.useMemo(
    () => (data ? calculateStatus(data, mode) : 'on-track'),
    [data, mode]
  );

  const statusConfig = getStatusConfig(status);
  const StatusIcon = statusConfig.icon;

  // Calculate progress
  const progress = React.useMemo(() => {
    if (!data) return { completed: 0, total: 0, percentage: 0 };

    const total = mode === 'points' ? data.totalPoints : data.totalIssues;
    const remaining =
      actualData.length > 0 ? (actualData[actualData.length - 1]?.actual ?? 0) : total;
    const completed = total - remaining;

    return {
      completed,
      total,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
    };
  }, [data, mode, actualData]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Burndown</CardTitle>
          <CardDescription>Sprint progress tracking</CardDescription>
        </CardHeader>
        <CardContent>
          <BurndownChartSkeleton height={height} />
        </CardContent>
      </Card>
    );
  }

  if (!data || chartData.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Burndown</CardTitle>
          <CardDescription>Sprint progress tracking</CardDescription>
        </CardHeader>
        <CardContent>
          <BurndownChartEmpty />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Burndown</CardTitle>
            <CardDescription>Sprint progress tracking</CardDescription>
          </div>

          <div className="flex items-center gap-4">
            {/* Progress indicator */}
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Progress</p>
                    <p className="text-2xl font-bold">{progress.percentage}%</p>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  {progress.completed} of {progress.total} {mode === 'points' ? 'points' : 'issues'}{' '}
                  completed
                </TooltipContent>
              </UITooltip>
            </TooltipProvider>

            {/* Status badge */}
            <TooltipProvider>
              <UITooltip>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      'flex items-center gap-1 rounded-full px-3 py-1',
                      statusConfig.bgColor
                    )}
                  >
                    <StatusIcon className={cn('size-4', statusConfig.color)} />
                    <span className={cn('text-sm font-medium', statusConfig.color)}>
                      {statusConfig.label}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  {status === 'ahead'
                    ? 'You are completing work faster than planned'
                    : status === 'behind'
                      ? 'Work is not being completed as quickly as planned'
                      : status === 'complete'
                        ? 'All work in this cycle is complete'
                        : 'Work is progressing as planned'}
                </TooltipContent>
              </UITooltip>
            </TooltipProvider>

            {/* Mode toggle */}
            {allowToggle && (
              <Select value={mode} onValueChange={(v) => setMode(v as ChartMode)}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="points">Points</SelectItem>
                  <SelectItem value="issues">Tasks</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="burndownGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />

            <XAxis
              dataKey="dateFormatted"
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
              domain={[0, 'dataMax + 5']}
              label={{
                value: mode === 'points' ? 'Points' : 'Tasks',
                angle: -90,
                position: 'insideLeft',
                className: 'fill-muted-foreground text-xs',
              }}
            />

            <Tooltip content={<CustomTooltip mode={mode} />} />

            <Legend />

            {/* Today marker */}
            {chartData.some((d) => d.isToday) && (
              <ReferenceLine
                x={chartData.find((d) => d.isToday)?.dateFormatted}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="3 3"
                label={{
                  value: 'Today',
                  position: 'top',
                  className: 'fill-muted-foreground text-xs',
                }}
              />
            )}

            {/* Ideal burndown line (full period) */}
            <Line
              type="linear"
              dataKey="ideal"
              name="Ideal"
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="5 5"
              strokeWidth={2}
              dot={false}
            />

            {/* Actual burndown area */}
            <Area
              type="monotone"
              data={actualData}
              dataKey="actual"
              name="Actual"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              fill="url(#burndownGradient)"
              dot={{ fill: 'hsl(var(--primary))', r: 3 }}
              activeDot={{ r: 5, strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
});

export default BurndownChart;
