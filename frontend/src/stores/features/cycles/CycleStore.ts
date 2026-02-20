/**
 * CycleStore - MobX store for Sprint Planning feature (US-04).
 *
 * T164: Manages cycle state with TanStack Query for server state.
 *
 * Types: ./cycle-store-types.ts
 * Data loading actions: ./cycle-store-actions.ts
 */
import { makeAutoObservable, runInAction } from 'mobx';
import type {
  Cycle,
  CreateCycleData,
  UpdateCycleData,
  RolloverCycleData,
  RolloverCycleResult,
  IssueState,
  BurndownChartData,
  VelocityChartData,
} from '@/types';

import { getIssueStateKey } from '@/lib/issue-helpers';
import { cyclesApi } from '@/services/api';
import type { CycleIssue, CycleFilters, SortBy, SortOrder } from './cycle-store-types';
import * as actions from './cycle-store-actions';

// Re-export types for consumers
export type { CycleIssue } from './cycle-store-types';

/**
 * CycleStore manages all cycle-related state for Sprint Planning.
 *
 * Responsibilities:
 * - Cycle CRUD operations with optimistic updates
 * - Active cycle tracking
 * - Issue assignment to cycles
 * - Rollover functionality
 * - Metrics and chart data
 *
 * @example
 * ```tsx
 * const { cycleStore } = useStore();
 *
 * // Load cycles for a project
 * await cycleStore.loadCycles('workspace-id', 'project-id');
 *
 * // Get active cycle
 * const activeCycle = cycleStore.activeCycle;
 *
 * // Create new cycle
 * await cycleStore.createCycle({ name: 'Sprint 1', projectId: '...' });
 * ```
 */
export class CycleStore {
  // ============================================================================
  // Observable State
  // ============================================================================

  /** All cycles indexed by ID */
  cycles: Map<string, Cycle> = new Map();

  /** Currently selected cycle ID */
  currentCycleId: string | null = null;

  /** Issues in the current cycle */
  cycleIssues: Map<string, CycleIssue> = new Map();

  /** Burndown chart data for current cycle */
  burndownData: BurndownChartData | null = null;

  /** Velocity chart data for project */
  velocityData: VelocityChartData | null = null;

  /** Loading states */
  isLoading = false;
  isSaving = false;
  isLoadingIssues = false;
  isLoadingBurndown = false;
  isLoadingVelocity = false;

  /** Error state */
  error: string | null = null;

  /** Filters and sorting */
  filters: CycleFilters = {};
  sortBy: SortBy = 'sequence';
  sortOrder: SortOrder = 'desc';

  /** Current project context */
  currentProjectId: string | null = null;
  currentWorkspaceId: string | null = null;

  /** Pagination */
  nextCursor: string | null = null;
  hasMore = false;

  // ============================================================================
  // Constructor
  // ============================================================================

  constructor() {
    makeAutoObservable(this);
  }

  // ============================================================================
  // Computed Properties
  // ============================================================================

  /** Currently selected cycle with full details */
  get currentCycle(): Cycle | null {
    return this.currentCycleId ? (this.cycles.get(this.currentCycleId) ?? null) : null;
  }

  /** All cycles as array */
  get cyclesList(): Cycle[] {
    return Array.from(this.cycles.values());
  }

  /** Filtered and sorted cycles */
  get filteredCycles(): Cycle[] {
    let cycles = this.cyclesList;

    if (this.filters.status && this.filters.status !== 'all') {
      cycles = cycles.filter((c) => c.status === this.filters.status);
    }

    if (this.filters.search) {
      const query = this.filters.search.toLowerCase();
      cycles = cycles.filter(
        (c) => c.name.toLowerCase().includes(query) || c.description?.toLowerCase().includes(query)
      );
    }

    return this.sortCycles(cycles);
  }

  /** Currently active cycle (status === 'active') */
  get activeCycle(): Cycle | null {
    return this.cyclesList.find((c) => c.status === 'active') ?? null;
  }

  /** Upcoming/planned cycles (status === 'draft' or 'planned') */
  get upcomingCycles(): Cycle[] {
    return this.filteredCycles.filter((c) => c.status === 'draft' || c.status === 'planned');
  }

  /** Completed/cancelled cycles */
  get pastCycles(): Cycle[] {
    return this.filteredCycles.filter((c) => c.status === 'completed' || c.status === 'cancelled');
  }

  /** Issues grouped by state for cycle board */
  get issuesByState(): Record<IssueState, CycleIssue[]> {
    const states: IssueState[] = [
      'backlog',
      'todo',
      'in_progress',
      'in_review',
      'done',
      'cancelled',
    ];
    const grouped: Record<IssueState, CycleIssue[]> = {} as Record<IssueState, CycleIssue[]>;

    states.forEach((state) => {
      grouped[state] = Array.from(this.cycleIssues.values()).filter(
        (i) => getIssueStateKey(i.state) === state
      );
    });

    return grouped;
  }

  /** Incomplete issues (not done or cancelled) */
  get incompleteIssues(): CycleIssue[] {
    return Array.from(this.cycleIssues.values()).filter(
      (i) => i.state.group !== 'completed' && i.state.group !== 'cancelled'
    );
  }

  /** Completed issues */
  get completedIssues(): CycleIssue[] {
    return Array.from(this.cycleIssues.values()).filter((i) => i.state.group === 'completed');
  }

  // ============================================================================
  // Private Helpers
  // ============================================================================

  /** Sort cycles by current sort settings */
  private sortCycles(cycles: Cycle[]): Cycle[] {
    return [...cycles].sort((a, b) => {
      let comparison = 0;

      switch (this.sortBy) {
        case 'sequence':
          comparison = a.sequence - b.sequence;
          break;
        case 'created_at':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'start_date':
          if (!a.startDate && !b.startDate) comparison = 0;
          else if (!a.startDate) comparison = 1;
          else if (!b.startDate) comparison = -1;
          else comparison = new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
          break;
      }

      return this.sortOrder === 'asc' ? comparison : -comparison;
    });
  }

  // ============================================================================
  // Actions - UI State
  // ============================================================================

  /** Set current cycle for detail view */
  setCurrentCycle(cycleId: string | null): void {
    this.currentCycleId = cycleId;
    this.cycleIssues.clear();
    this.burndownData = null;
  }

  /** Set filters */
  setFilters(filters: Partial<CycleFilters>): void {
    this.filters = { ...this.filters, ...filters };
  }

  /** Clear all filters */
  clearFilters(): void {
    this.filters = {};
  }

  /** Set sort configuration */
  setSortBy(sortBy: SortBy): void {
    this.sortBy = sortBy;
  }

  setSortOrder(sortOrder: SortOrder): void {
    this.sortOrder = sortOrder;
  }

  // ============================================================================
  // Actions - Data Loading (delegated to cycle-store-actions.ts)
  // ============================================================================

  async loadCycles(
    workspaceId: string,
    projectId: string,
    options: { includeMetrics?: boolean; loadMore?: boolean } = {}
  ): Promise<void> {
    return actions.loadCycles(this, workspaceId, projectId, options);
  }

  async loadCycle(
    workspaceId: string,
    cycleId: string,
    includeMetrics = true
  ): Promise<Cycle | null> {
    return actions.loadCycle(this, workspaceId, cycleId, includeMetrics);
  }

  async loadActiveCycle(workspaceId: string, projectId: string): Promise<Cycle | null> {
    return actions.loadActiveCycle(this, workspaceId, projectId);
  }

  async loadCycleIssues(
    workspaceId: string,
    cycleId: string,
    includeCompleted = true
  ): Promise<void> {
    return actions.loadCycleIssues(this, workspaceId, cycleId, includeCompleted);
  }

  async loadBurndownData(workspaceId: string, cycleId: string): Promise<void> {
    await actions.loadBurndownData(this, workspaceId, cycleId);
  }

  async loadVelocityData(workspaceId: string, projectId: string, limit = 10): Promise<void> {
    await actions.loadVelocityData(this, workspaceId, projectId, limit);
  }

  // ============================================================================
  // Actions - CRUD Operations
  // ============================================================================

  async createCycle(data: CreateCycleData): Promise<Cycle | null> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const cycle = await cyclesApi.create(this.currentWorkspaceId, data);
      runInAction(() => {
        this.cycles.set(cycle.id, cycle);
        this.isSaving = false;
      });
      return cycle;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to create cycle';
        this.isSaving = false;
      });
      return null;
    }
  }

  async updateCycle(cycleId: string, data: UpdateCycleData): Promise<Cycle | null> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    // Optimistic update
    const original = this.cycles.get(cycleId);
    if (original && data.name !== undefined) {
      this.cycles.set(cycleId, { ...original, name: data.name });
    }

    try {
      const cycle = await cyclesApi.update(this.currentWorkspaceId, cycleId, data);
      runInAction(() => {
        this.cycles.set(cycle.id, cycle);
        this.isSaving = false;
      });
      return cycle;
    } catch (err) {
      runInAction(() => {
        if (original) {
          this.cycles.set(cycleId, original);
        }
        this.error = err instanceof Error ? err.message : 'Failed to update cycle';
        this.isSaving = false;
      });
      return null;
    }
  }

  async deleteCycle(cycleId: string): Promise<boolean> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return false;
    }

    const original = this.cycles.get(cycleId);
    this.cycles.delete(cycleId);

    try {
      await cyclesApi.delete(this.currentWorkspaceId, cycleId);
      runInAction(() => {
        if (this.currentCycleId === cycleId) {
          this.currentCycleId = null;
        }
      });
      return true;
    } catch (err) {
      runInAction(() => {
        if (original) {
          this.cycles.set(cycleId, original);
        }
        this.error = err instanceof Error ? err.message : 'Failed to delete cycle';
      });
      return false;
    }
  }

  async activateCycle(cycleId: string): Promise<Cycle | null> {
    return this.updateCycle(cycleId, { status: 'active' });
  }

  async completeCycle(cycleId: string): Promise<Cycle | null> {
    return this.updateCycle(cycleId, { status: 'completed' });
  }

  async cancelCycle(cycleId: string): Promise<Cycle | null> {
    return this.updateCycle(cycleId, { status: 'cancelled' });
  }

  // ============================================================================
  // Actions - Issue Management
  // ============================================================================

  async addIssueToCycle(cycleId: string, issueId: string): Promise<boolean> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return false;
    }

    try {
      await cyclesApi.addIssue(this.currentWorkspaceId, cycleId, issueId);
      await this.loadCycleIssues(this.currentWorkspaceId, cycleId);
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to add issue to cycle';
      });
      return false;
    }
  }

  async bulkAddIssuesToCycle(cycleId: string, issueIds: string[]): Promise<boolean> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return false;
    }

    try {
      await cyclesApi.bulkAddIssues(this.currentWorkspaceId, cycleId, issueIds);
      await this.loadCycleIssues(this.currentWorkspaceId, cycleId);
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to add issues to cycle';
      });
      return false;
    }
  }

  async removeIssueFromCycle(cycleId: string, issueId: string): Promise<boolean> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return false;
    }

    this.cycleIssues.delete(issueId);

    try {
      await cyclesApi.removeIssue(this.currentWorkspaceId, cycleId, issueId);
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to remove issue';
      });
      await this.loadCycleIssues(this.currentWorkspaceId, cycleId);
      return false;
    }
  }

  /**
   * Optimistic update for issue state (drag-drop)
   */
  optimisticUpdateIssueState(issueId: string, newState: string): void {
    const issue = this.cycleIssues.get(issueId);
    if (issue) {
      this.cycleIssues.set(issueId, {
        ...issue,
        state: { ...issue.state, name: newState },
      });
    }
  }

  // ============================================================================
  // Actions - Rollover
  // ============================================================================

  async rolloverCycle(
    sourceCycleId: string,
    data: RolloverCycleData
  ): Promise<RolloverCycleResult | null> {
    if (!this.currentWorkspaceId) {
      this.error = 'No workspace context';
      return null;
    }

    this.isSaving = true;
    this.error = null;

    try {
      const result = await cyclesApi.rollover(this.currentWorkspaceId, sourceCycleId, data);
      runInAction(() => {
        this.cycles.set(result.sourceCycle.id, result.sourceCycle);
        this.cycles.set(result.targetCycle.id, result.targetCycle);
        this.isSaving = false;
      });
      return result;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to rollover cycle';
        this.isSaving = false;
      });
      return null;
    }
  }

  // ============================================================================
  // Reset
  // ============================================================================

  /** Reset store to initial state */
  reset(): void {
    this.cycles.clear();
    this.currentCycleId = null;
    this.cycleIssues.clear();
    this.burndownData = null;
    this.velocityData = null;
    this.isLoading = false;
    this.isSaving = false;
    this.isLoadingIssues = false;
    this.isLoadingBurndown = false;
    this.isLoadingVelocity = false;
    this.error = null;
    this.filters = {};
    this.sortBy = 'sequence';
    this.sortOrder = 'desc';
    this.currentProjectId = null;
    this.currentWorkspaceId = null;
    this.nextCursor = null;
    this.hasMore = false;
  }
}

export const cycleStore = new CycleStore();
