'use client';

/**
 * Cost Dashboard Page - AI usage and cost analytics.
 *
 * T200: Main dashboard displaying cost summary, charts, and tables
 * with date range filtering and real-time updates.
 *
 * @example
 * ```tsx
 * <CostDashboardPage workspaceId="..." />
 * ```
 */

import { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, RefreshCw, Sparkles } from 'lucide-react';
import { format } from 'date-fns';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useStore } from '@/stores';
import { aiApi } from '@/services/api/ai';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CostSummaryCard } from '../components/cost-summary-card';
import { DateRangeSelector } from '../components/date-range-selector';
import { CostByAgentChart } from '../components/cost-by-agent-chart';
import { CostTrendsChart } from '../components/cost-trends-chart';
import { CostTableView } from '../components/cost-table-view';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// ============================================================================
// Types
// ============================================================================

export interface CostDashboardPageProps {
  /** Workspace ID to load costs for */
  workspaceId: string;
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
 * Format token count with K/M suffix.
 */
function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toLocaleString();
}

// ============================================================================
// Component
// ============================================================================

// Feature chart color palette (accessible, consistent with chart-* CSS vars)
const FEATURE_COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
  '#8884d8',
  '#82ca9d',
  '#ffc658',
];

/** Convert snake_case operation_type label to Title Case for display. */
function formatFeatureName(name: string): string {
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export const CostDashboardPage = observer(function CostDashboardPage({
  workspaceId,
}: CostDashboardPageProps) {
  const { ai, workspaceStore } = useStore();
  const { cost } = ai;

  const [activeTab, setActiveTab] = useState<'by_agent' | 'by_feature'>('by_agent');

  // Resolve the actual workspace UUID from the store.
  // The page prop `workspaceId` may be the slug (see costs/page.tsx); the store
  // holds the authoritative UUID required for X-Workspace-Id header lookups.
  const resolvedWorkspaceId = workspaceStore.currentWorkspace?.id ?? workspaceId;

  // Load cost summary on mount
  useEffect(() => {
    cost.loadSummary(resolvedWorkspaceId);
  }, [cost, resolvedWorkspaceId]);

  // Handle date range change
  const handleDateRangeChange = async (range: { start: Date; end: Date }) => {
    await cost.setDateRange(range, resolvedWorkspaceId);
  };

  // Lazy-load feature breakdown only when tab is active
  const startDate = format(cost.dateRange.start, 'yyyy-MM-dd');
  const endDate = format(cost.dateRange.end, 'yyyy-MM-dd');

  const { data: featureSummary, isLoading: isFeatureLoading } = useQuery({
    queryKey: ['costs-by-feature', resolvedWorkspaceId, startDate, endDate],
    queryFn: () => aiApi.getCostSummary(resolvedWorkspaceId, startDate, endDate, 'operation_type'),
    enabled: activeTab === 'by_feature' && !!resolvedWorkspaceId,
    staleTime: 60_000,
  });

  const featureChartData = featureSummary?.by_feature
    ? Object.entries(featureSummary.by_feature)
        .map(([name, value]) => ({ name, value: Number(value) }))
        .sort((a, b) => b.value - a.value)
    : [];

  // Admin guard
  if (!workspaceStore.isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <AlertCircle className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <h3 className="text-lg font-medium">Access restricted</h3>
        <p className="text-sm text-muted-foreground">
          AI cost analytics are only available to workspace admins.
        </p>
      </div>
    );
  }

  // Loading state
  if (cost.isLoading && !cost.summary) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-64" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-[400px]" />
          <Skeleton className="h-[400px]" />
        </div>
      </div>
    );
  }

  // Error state
  if (cost.error) {
    return (
      <div className="space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="size-4" />
          <AlertTitle>Failed to load cost data</AlertTitle>
          <AlertDescription>{cost.error}</AlertDescription>
        </Alert>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => cost.loadSummary(resolvedWorkspaceId)}
          className="flex items-center gap-2"
          aria-label="Retry loading cost data"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Retry
        </Button>
      </div>
    );
  }

  // Empty state — no AI usage yet
  if (!cost.isLoading && !cost.error && cost.totalRequests === 0) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Cost Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Monitor AI usage and costs across your workspace
          </p>
        </div>
        <div className="flex flex-col items-center justify-center rounded-xl bg-background-subtle py-16 shadow-warm-sm">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-ai-muted">
            <Sparkles className="h-6 w-6 text-ai" />
          </div>
          <h3 className="mt-4 text-sm font-semibold text-foreground">No AI usage yet</h3>
          <p className="mt-1.5 max-w-sm text-center text-sm text-muted-foreground leading-relaxed">
            Costs will appear here once your team starts using AI features — ghost text, issue
            extraction, PR reviews, and chat.
          </p>
          <p className="mt-3 text-xs text-muted-foreground/60">
            Configure AI providers in Settings to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Cost Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Monitor AI usage and costs across your workspace
          </p>
        </div>
        <DateRangeSelector onSelect={handleDateRangeChange} currentRange={cost.dateRange} />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <CostSummaryCard
          title="Total Cost"
          value={formatCost(cost.totalCost)}
          description="Total AI usage cost"
        />
        <CostSummaryCard
          title="Total Requests"
          value={cost.totalRequests.toLocaleString()}
          description="Number of AI requests"
        />
        <CostSummaryCard
          title="Total Tokens"
          value={formatTokens(cost.totalTokens)}
          description="Input + output tokens"
        />
        <CostSummaryCard
          title="Avg Cost/Request"
          value={formatCost(cost.avgCostPerRequest)}
          description="Average per request"
        />
      </div>

      {/* Charts Grid with By Agent / By Feature tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'by_agent' | 'by_feature')}>
        <TabsList>
          <TabsTrigger value="by_agent">By Agent</TabsTrigger>
          <TabsTrigger value="by_feature">By Feature</TabsTrigger>
        </TabsList>

        <TabsContent value="by_agent" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CostByAgentChart
              data={cost.costByAgent}
              onAgentClick={(_agentName) => {
                // Filter by agent is not yet implemented
              }}
            />
            <CostTrendsChart data={cost.costTrends} />
          </div>
        </TabsContent>

        <TabsContent value="by_feature" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Cost by Feature</CardTitle>
              <CardDescription>
                Token cost breakdown by operation type for this period
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isFeatureLoading ? (
                <div className="flex items-center justify-center h-[300px]">
                  <Skeleton className="h-full w-full" />
                </div>
              ) : featureChartData.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
                  <Sparkles className="h-8 w-8 text-muted-foreground/30 mb-3" />
                  <p className="text-sm">No feature cost data for this period</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    Try selecting a wider date range
                  </p>
                </div>
              ) : (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(300, featureChartData.length * 48)}
                >
                  <BarChart
                    data={featureChartData}
                    layout="vertical"
                    margin={{ top: 4, right: 24, bottom: 4, left: 120 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis
                      type="number"
                      tickFormatter={(v: number) => (v < 0.01 ? '<$0.01' : `$${v.toFixed(2)}`)}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tickFormatter={formatFeatureName}
                      width={116}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip
                      formatter={(value: number | undefined) => {
                        if (value == null) return '—';
                        return value < 0.01 ? '<$0.01' : `$${value.toFixed(4)}`;
                      }}
                      labelFormatter={(label: unknown) =>
                        typeof label === 'string' ? formatFeatureName(label) : String(label)
                      }
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {featureChartData.map((_entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={FEATURE_COLORS[index % FEATURE_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* User Cost Table */}
      <CostTableView data={cost.costPerUser} />
    </div>
  );
});

export default CostDashboardPage;
