'use client';

/**
 * Cost By Agent Chart - Donut chart showing cost distribution by agent.
 *
 * T202: Displays pie/donut chart of agent costs with legend,
 * percentages, and interactive tooltips. Click to filter by agent.
 *
 * @example
 * ```tsx
 * <CostByAgentChart
 *   data={[{ agent_name: 'note_enhancer', total_cost_usd: 1.23, percentage: 45.2 }]}
 * />
 * ```
 */

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { CostByAgentData } from '@/stores/ai/CostStore';
import type { TooltipProps } from 'recharts';

// ============================================================================
// Types
// ============================================================================

interface CustomTooltipProps extends TooltipProps<number, string> {
  active?: boolean;
  payload?: Array<{
    payload: CostByAgentData;
  }>;
}

export interface CostByAgentChartProps {
  /** Agent cost data */
  data: CostByAgentData[];
  /** Additional class name */
  className?: string;
  /** Callback when agent is clicked */
  onAgentClick?: (agentName: string) => void;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Color palette for agent slices.
 * Using a professional, accessible color scheme.
 */
const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
  '#8884d8',
  '#82ca9d',
  '#ffc658',
  '#ff8042',
  '#0088FE',
];

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
 * Format agent name for display (convert snake_case to Title Case).
 */
function formatAgentName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// ============================================================================
// Sub-components
// ============================================================================

/**
 * Custom tooltip content component.
 */
function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload as CostByAgentData;
  if (!data) return null;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="font-semibold text-sm">{formatAgentName(data.agent_name)}</p>
      <div className="mt-1 space-y-1">
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Cost:</span>
          <span className="font-medium">{formatCost(data.total_cost_usd)}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Requests:</span>
          <span className="font-medium">{data.request_count.toLocaleString()}</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-muted-foreground">Share:</span>
          <span className="font-medium">{data.percentage.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Custom legend renderer component factory.
 */
function createLegendRenderer(onAgentClick?: (agentName: string) => void) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return function LegendRenderer(props: any) {
    const { payload } = props;

    if (!payload) return null;

    return (
      <div className="flex flex-col gap-2 mt-4">
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {payload.map((entry: any, index: number) => {
          const data = entry.payload as CostByAgentData;
          return (
            <div
              key={`legend-${index}`}
              className="flex items-center justify-between text-sm cursor-pointer hover:bg-muted/50 rounded px-2 py-1 transition-colors"
              onClick={() => onAgentClick?.(data.agent_name)}
            >
              <div className="flex items-center gap-2">
                <div className="size-3 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="font-medium">{formatAgentName(data.agent_name)}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground text-xs">{data.percentage.toFixed(1)}%</span>
                <span className="font-mono text-xs">{formatCost(data.total_cost_usd)}</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };
}

// ============================================================================
// Component
// ============================================================================

export function CostByAgentChart({ data, className, onAgentClick }: CostByAgentChartProps) {
  const hasData = data && data.length > 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Cost by Agent</CardTitle>
        <CardDescription>Cost distribution across AI agents</CardDescription>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            <p className="text-sm">No cost data available for this period</p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="total_cost_usd"
                nameKey="agent_name"
                onClick={(entry) => onAgentClick?.(entry.agent_name)}
                className="cursor-pointer focus:outline-none"
              >
                {data.map((_entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    className="hover:opacity-80 transition-opacity"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend content={createLegendRenderer(onAgentClick)} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default CostByAgentChart;
