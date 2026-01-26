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

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { AlertCircle } from 'lucide-react';
import { useStore } from '@/stores';
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

export const CostDashboardPage = observer(function CostDashboardPage({
  workspaceId,
}: CostDashboardPageProps) {
  const { ai } = useStore();
  const { cost } = ai;

  // Load cost summary on mount
  useEffect(() => {
    cost.loadSummary(workspaceId);
  }, [cost, workspaceId]);

  // Handle date range change
  const handleDateRangeChange = async (range: { start: Date; end: Date }) => {
    await cost.setDateRange(range, workspaceId);
  };

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

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CostByAgentChart
          data={cost.costByAgent}
          onAgentClick={(agentName) => {
            // TODO: Implement filter by agent in future enhancement
            console.log('Filter by agent:', agentName);
          }}
        />
        <CostTrendsChart data={cost.costTrends} />
      </div>

      {/* User Cost Table */}
      <CostTableView data={cost.costPerUser} />
    </div>
  );
});

export default CostDashboardPage;
