/**
 * Cost Dashboard Store - MobX store for AI cost tracking and analytics.
 *
 * T205: Manages cost summary, trends, and detailed records with:
 * - Observable cost summary with agent/user/day breakdowns
 * - Date range filtering
 * - Loading states and error handling
 * - Computed totals and averages
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#Phase24
 */

import { makeAutoObservable, runInAction, computed } from 'mobx';
import { aiApi, type CostSummary } from '@/services/api/ai';
import type { AIStore } from './AIStore';
import { subDays, format } from 'date-fns';

// ============================================================================
// Types
// ============================================================================

export interface DateRange {
  start: Date;
  end: Date;
}

export interface CostByAgentData {
  agent_name: string;
  total_cost_usd: number;
  request_count: number;
  percentage: number;
}

export interface CostTrendData {
  date: string;
  total_cost_usd: number;
  request_count: number;
}

// ============================================================================
// Store
// ============================================================================

export class CostStore {
  // State
  summary: CostSummary | null = null;
  isLoading = false;
  error: string | null = null;
  dateRange: DateRange = {
    start: subDays(new Date(), 30),
    end: new Date(),
  };

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this, {
      totalCost: computed,
      costByAgent: computed,
      costTrends: computed,
      costPerUser: computed,
    });
    // _rootStore reserved for future use with global AI settings/error handling
  }

  // ============================================================================
  // Computed
  // ============================================================================

  get totalCost(): number {
    return this.summary?.total_cost_usd ?? 0;
  }

  get totalRequests(): number {
    return this.summary?.total_requests ?? 0;
  }

  get totalTokens(): number {
    const input = this.summary?.total_input_tokens ?? 0;
    const output = this.summary?.total_output_tokens ?? 0;
    return input + output;
  }

  get avgCostPerRequest(): number {
    if (this.totalRequests === 0) return 0;
    return this.totalCost / this.totalRequests;
  }

  /**
   * Cost by agent with percentage calculation.
   */
  get costByAgent(): CostByAgentData[] {
    if (!this.summary?.by_agent) return [];

    const total = this.totalCost;
    return this.summary.by_agent.map((agent) => ({
      ...agent,
      percentage: total > 0 ? (agent.total_cost_usd / total) * 100 : 0,
    }));
  }

  /**
   * Daily cost trends from by_day data.
   */
  get costTrends(): CostTrendData[] {
    if (!this.summary?.by_day) return [];

    return this.summary.by_day.map((day) => ({
      date: day.date,
      total_cost_usd: day.total_cost_usd,
      request_count: day.request_count,
    }));
  }

  /**
   * Cost per user (for detailed table view).
   */
  get costPerUser(): Array<{
    user_id: string;
    user_name: string;
    total_cost_usd: number;
    request_count: number;
  }> {
    return this.summary?.by_user ?? [];
  }

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Load cost summary for current workspace and date range.
   *
   * @param workspaceId - Workspace UUID
   */
  async loadSummary(workspaceId: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const startDate = format(this.dateRange.start, 'yyyy-MM-dd');
      const endDate = format(this.dateRange.end, 'yyyy-MM-dd');

      const summary = await aiApi.getCostSummary(workspaceId, startDate, endDate);

      runInAction(() => {
        this.summary = summary;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load cost summary';
        this.isLoading = false;
      });
    }
  }

  /**
   * Set date range and reload summary.
   *
   * @param range - Date range to filter by
   * @param workspaceId - Workspace UUID to reload data for
   */
  async setDateRange(range: DateRange, workspaceId: string): Promise<void> {
    runInAction(() => {
      this.dateRange = range;
    });
    await this.loadSummary(workspaceId);
  }

  /**
   * Set preset date range (last 7/30/90 days, this month).
   *
   * @param preset - Preset range identifier
   * @param workspaceId - Workspace UUID to reload data for
   */
  async setPresetRange(
    preset: 'today' | '7d' | '30d' | '90d' | 'month',
    workspaceId: string
  ): Promise<void> {
    const end = new Date();
    let start: Date;

    switch (preset) {
      case 'today':
        start = new Date();
        start.setHours(0, 0, 0, 0);
        break;
      case '7d':
        start = subDays(end, 7);
        break;
      case '30d':
        start = subDays(end, 30);
        break;
      case '90d':
        start = subDays(end, 90);
        break;
      case 'month':
        start = new Date(end.getFullYear(), end.getMonth(), 1);
        break;
    }

    await this.setDateRange({ start, end }, workspaceId);
  }

  /**
   * Reset store to initial state.
   */
  reset(): void {
    this.summary = null;
    this.isLoading = false;
    this.error = null;
    this.dateRange = {
      start: subDays(new Date(), 30),
      end: new Date(),
    };
  }
}
