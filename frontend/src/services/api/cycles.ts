/**
 * Cycles API client.
 *
 * T164: API client for Sprint Planning feature (US-04).
 */

import { apiClient, type PaginatedResponse } from './client';
import type {
  Cycle,
  CycleStatus,
  CreateCycleData,
  UpdateCycleData,
  RolloverCycleData,
  RolloverCycleResult,
  BurndownChartData,
  VelocityChartData,
  Issue,
} from '@/types';

interface CycleFilters {
  projectId: string;
  status?: CycleStatus;
  search?: string;
  includeMetrics?: boolean;
}

interface CyclePaginationOptions {
  cursor?: string;
  pageSize?: number;
  sortBy?: 'sequence' | 'created_at' | 'start_date';
  sortOrder?: 'asc' | 'desc';
}

export interface CycleListResponse {
  items: Cycle[];
  total: number;
  nextCursor: string | null;
  prevCursor: string | null;
  hasNext: boolean;
  hasPrev: boolean;
  pageSize: number;
}

export const cyclesApi = {
  /**
   * List cycles for a project with pagination.
   */
  list(
    workspaceId: string,
    filters: CycleFilters,
    options: CyclePaginationOptions = {}
  ): Promise<CycleListResponse> {
    const params: Record<string, string> = {
      project_id: filters.projectId,
    };

    if (filters.status) params.status = filters.status;
    if (filters.search) params.search = filters.search;
    if (filters.includeMetrics) params.include_metrics = 'true';
    if (options.cursor) params.cursor = options.cursor;
    if (options.pageSize) params.page_size = String(options.pageSize);
    if (options.sortBy) params.sort_by = options.sortBy;
    if (options.sortOrder) params.sort_order = options.sortOrder;

    return apiClient.get<CycleListResponse>(`/workspaces/${workspaceId}/cycles`, { params });
  },

  /**
   * Get a single cycle by ID.
   */
  get(workspaceId: string, cycleId: string, includeMetrics = true): Promise<Cycle> {
    const params: Record<string, string> = {};
    if (includeMetrics) params.include_metrics = 'true';

    return apiClient.get<Cycle>(`/workspaces/${workspaceId}/cycles/${cycleId}`, { params });
  },

  /**
   * Get the currently active cycle for a project.
   */
  getActive(workspaceId: string, projectId: string, includeMetrics = true): Promise<Cycle | null> {
    const params: Record<string, string> = {
      project_id: projectId,
    };
    if (includeMetrics) params.include_metrics = 'true';

    return apiClient.get<Cycle | null>(`/workspaces/${workspaceId}/cycles/active`, { params });
  },

  /**
   * Create a new cycle.
   */
  create(workspaceId: string, data: CreateCycleData): Promise<Cycle> {
    return apiClient.post<Cycle>(`/workspaces/${workspaceId}/cycles`, {
      name: data.name,
      description: data.description,
      project_id: data.projectId,
      start_date: data.startDate,
      end_date: data.endDate,
      owned_by_id: data.ownedById,
      status: data.status ?? 'draft',
    });
  },

  /**
   * Update an existing cycle.
   */
  update(workspaceId: string, cycleId: string, data: UpdateCycleData): Promise<Cycle> {
    return apiClient.patch<Cycle>(`/workspaces/${workspaceId}/cycles/${cycleId}`, {
      name: data.name,
      description: data.description,
      start_date: data.startDate,
      end_date: data.endDate,
      status: data.status,
      owned_by_id: data.ownedById,
      clear_description: data.clearDescription,
      clear_start_date: data.clearStartDate,
      clear_end_date: data.clearEndDate,
      clear_owner: data.clearOwner,
    });
  },

  /**
   * Soft delete a cycle.
   */
  delete(workspaceId: string, cycleId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/cycles/${cycleId}`);
  },

  /**
   * Add an issue to a cycle.
   */
  addIssue(
    workspaceId: string,
    cycleId: string,
    issueId: string
  ): Promise<{ added: boolean; issueId: string }> {
    return apiClient.post<{ added: boolean; issueId: string }>(
      `/workspaces/${workspaceId}/cycles/${cycleId}/issues`,
      { issue_id: issueId }
    );
  },

  /**
   * Add multiple issues to a cycle.
   */
  bulkAddIssues(
    workspaceId: string,
    cycleId: string,
    issueIds: string[]
  ): Promise<{ addedCount: number; totalRequested: number }> {
    return apiClient.post<{ addedCount: number; totalRequested: number }>(
      `/workspaces/${workspaceId}/cycles/${cycleId}/issues/bulk`,
      { issue_ids: issueIds }
    );
  },

  /**
   * Remove an issue from a cycle.
   */
  removeIssue(workspaceId: string, cycleId: string, issueId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/cycles/${cycleId}/issues/${issueId}`);
  },

  /**
   * Get issues in a cycle.
   */
  getIssues(
    workspaceId: string,
    cycleId: string,
    includeCompleted = true
  ): Promise<PaginatedResponse<Issue>> {
    const params: Record<string, string> = {};
    if (!includeCompleted) params.include_completed = 'false';

    return apiClient.get<PaginatedResponse<Issue>>(
      `/workspaces/${workspaceId}/cycles/${cycleId}/issues`,
      { params }
    );
  },

  /**
   * Rollover incomplete issues to another cycle.
   */
  rollover(
    workspaceId: string,
    cycleId: string,
    data: RolloverCycleData
  ): Promise<RolloverCycleResult> {
    return apiClient.post<RolloverCycleResult>(
      `/workspaces/${workspaceId}/cycles/${cycleId}/rollover`,
      {
        target_cycle_id: data.targetCycleId,
        issue_ids: data.issueIds,
        include_in_progress: data.includeInProgress ?? true,
        complete_source_cycle: data.completeSourceCycle ?? true,
      }
    );
  },

  /**
   * Get burndown chart data for a cycle.
   */
  getBurndownData(workspaceId: string, cycleId: string): Promise<BurndownChartData> {
    return apiClient.get<BurndownChartData>(
      `/workspaces/${workspaceId}/cycles/${cycleId}/burndown`
    );
  },

  /**
   * Get velocity chart data for a project.
   */
  getVelocityData(workspaceId: string, projectId: string, limit = 10): Promise<VelocityChartData> {
    const params: Record<string, string> = {
      project_id: projectId,
      limit: String(limit),
    };

    return apiClient.get<VelocityChartData>(`/workspaces/${workspaceId}/cycles/velocity`, {
      params,
    });
  },
};
