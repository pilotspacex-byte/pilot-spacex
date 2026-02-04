/**
 * Async action helpers for CycleStore data loading and chart operations.
 *
 * Extracted from CycleStore to keep files under 700 lines.
 * These functions accept the store instance and perform API calls
 * with proper MobX runInAction wrappers.
 */
import { runInAction } from 'mobx';
import type { Cycle, BurndownChartData, VelocityChartData } from '@/types';
import { cyclesApi, type CycleListResponse } from '@/services/api';
import type { CycleIssue } from './cycle-store-types';
import type { CycleStore } from './CycleStore';

/**
 * Load cycles for a project
 */
export async function loadCycles(
  store: CycleStore,
  workspaceId: string,
  projectId: string,
  options: { includeMetrics?: boolean; loadMore?: boolean } = {}
): Promise<void> {
  const { includeMetrics = true, loadMore = false } = options;

  if (!loadMore) {
    store.isLoading = true;
    store.cycles.clear();
  }
  store.error = null;
  store.currentWorkspaceId = workspaceId;
  store.currentProjectId = projectId;

  try {
    const response: CycleListResponse = await cyclesApi.list(
      workspaceId,
      {
        projectId,
        status: store.filters.status !== 'all' ? store.filters.status : undefined,
        search: store.filters.search,
        includeMetrics,
      },
      {
        cursor: loadMore ? (store.nextCursor ?? undefined) : undefined,
        sortBy: store.sortBy,
        sortOrder: store.sortOrder,
      }
    );

    runInAction(() => {
      response.items.forEach((cycle) => {
        store.cycles.set(cycle.id, cycle);
      });
      store.nextCursor = response.nextCursor;
      store.hasMore = response.hasNext;
      store.isLoading = false;
    });
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load cycles';
      store.isLoading = false;
    });
  }
}

/**
 * Load a single cycle by ID
 */
export async function loadCycle(
  store: CycleStore,
  workspaceId: string,
  cycleId: string,
  includeMetrics = true
): Promise<Cycle | null> {
  store.isLoading = true;
  store.error = null;

  try {
    const cycle = await cyclesApi.get(workspaceId, cycleId, includeMetrics);
    runInAction(() => {
      store.cycles.set(cycle.id, cycle);
      store.currentCycleId = cycle.id;
      store.isLoading = false;
    });
    return cycle;
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load cycle';
      store.isLoading = false;
    });
    return null;
  }
}

/**
 * Load active cycle for a project
 */
export async function loadActiveCycle(
  store: CycleStore,
  workspaceId: string,
  projectId: string
): Promise<Cycle | null> {
  store.isLoading = true;
  store.error = null;

  try {
    const cycle = await cyclesApi.getActive(workspaceId, projectId, true);
    runInAction(() => {
      if (cycle) {
        store.cycles.set(cycle.id, cycle);
        store.currentCycleId = cycle.id;
      }
      store.isLoading = false;
    });
    return cycle;
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load active cycle';
      store.isLoading = false;
    });
    return null;
  }
}

/**
 * Load issues for a cycle
 */
export async function loadCycleIssues(
  store: CycleStore,
  workspaceId: string,
  cycleId: string,
  includeCompleted = true
): Promise<void> {
  store.isLoadingIssues = true;
  store.error = null;

  try {
    const response = await cyclesApi.getIssues(workspaceId, cycleId, includeCompleted);
    runInAction(() => {
      store.cycleIssues.clear();
      response.items.forEach((issue) => {
        store.cycleIssues.set(issue.id, issue as CycleIssue);
      });
      store.isLoadingIssues = false;
    });
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load cycle issues';
      store.isLoadingIssues = false;
    });
  }
}

/**
 * Load burndown chart data
 */
export async function loadBurndownData(
  store: CycleStore,
  workspaceId: string,
  cycleId: string
): Promise<BurndownChartData | null> {
  store.isLoadingBurndown = true;
  store.error = null;

  try {
    const data = await cyclesApi.getBurndownData(workspaceId, cycleId);
    runInAction(() => {
      store.burndownData = data;
      store.isLoadingBurndown = false;
    });
    return data;
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load burndown data';
      store.isLoadingBurndown = false;
    });
    return null;
  }
}

/**
 * Load velocity chart data
 */
export async function loadVelocityData(
  store: CycleStore,
  workspaceId: string,
  projectId: string,
  limit = 10
): Promise<VelocityChartData | null> {
  store.isLoadingVelocity = true;
  store.error = null;

  try {
    const data = await cyclesApi.getVelocityData(workspaceId, projectId, limit);
    runInAction(() => {
      store.velocityData = data;
      store.isLoadingVelocity = false;
    });
    return data;
  } catch (err) {
    runInAction(() => {
      store.error = err instanceof Error ? err.message : 'Failed to load velocity data';
      store.isLoadingVelocity = false;
    });
    return null;
  }
}
