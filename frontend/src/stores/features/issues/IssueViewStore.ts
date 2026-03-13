'use client';

import { makeAutoObservable, reaction, computed, type IReactionDisposer } from 'mobx';

// ---- Types ----

export type ViewMode = 'board' | 'list' | 'table' | 'priority';

// ---- Persisted State Shape ----

interface PersistedIssueViewState {
  viewMode: ViewMode;
  cardDensity: 'comfortable' | 'compact' | 'minimal';
  collapsedColumns: string[];
  collapsedGroups: string[];
  columnWidths: Record<string, number>;
  hiddenColumns: string[];
  wipLimits: Record<string, number>;
  filterStates: string[];
  filterPriorities: string[];
  filterTypes: string[];
  filterAssigneeIds: string[];
  filterLabelIds: string[];
  filterProjectIds: string[];
  projectViewModes: Record<string, ViewMode>;
}

const STORAGE_KEY = 'pilot-space:issue-view-state';

// ---- Store ----

export class IssueViewStore {
  // View preferences (persisted)
  viewMode: ViewMode = 'board';
  projectViewModes: Map<string, ViewMode> = new Map();
  cardDensity: 'comfortable' | 'compact' | 'minimal' = 'comfortable';
  collapsedColumns: Set<string> = new Set();
  collapsedGroups: Set<string> = new Set();
  columnWidths: Map<string, number> = new Map();
  hiddenColumns: Set<string> = new Set();
  wipLimits: Map<string, number> = new Map();

  // Multi-select filters (persisted)
  filterStates: string[] = [];
  filterPriorities: string[] = [];
  filterTypes: string[] = [];
  filterAssigneeIds: string[] = [];
  filterLabelIds: string[] = [];
  filterProjectIds: string[] = [];

  // Ephemeral (NOT persisted)
  selectedIssueIds: Set<string> = new Set();

  private hydrated = false;
  private reactionDisposers: IReactionDisposer[] = [];

  constructor() {
    makeAutoObservable(this, {
      hasActiveFilters: computed,
      activeFilterCount: computed,
      selectedCount: computed,
    });

    this.setupPersistence();
  }

  // ---- Computed ----

  get hasActiveFilters(): boolean {
    return (
      this.filterStates.length > 0 ||
      this.filterPriorities.length > 0 ||
      this.filterTypes.length > 0 ||
      this.filterAssigneeIds.length > 0 ||
      this.filterLabelIds.length > 0 ||
      this.filterProjectIds.length > 0
    );
  }

  get activeFilterCount(): number {
    return (
      this.filterStates.length +
      this.filterPriorities.length +
      this.filterTypes.length +
      this.filterAssigneeIds.length +
      this.filterLabelIds.length +
      this.filterProjectIds.length
    );
  }

  get selectedCount(): number {
    return this.selectedIssueIds.size;
  }

  // ---- Hydration ----

  hydrate(): void {
    if (this.hydrated) return;
    this.loadFromStorage();
    this.hydrated = true;
  }

  // ---- View Preference Actions ----

  setViewMode(mode: ViewMode): void {
    this.viewMode = mode;
  }

  getEffectiveViewMode(projectId?: string): ViewMode {
    if (projectId) {
      return this.projectViewModes.get(projectId) ?? this.viewMode;
    }
    return this.viewMode;
  }

  setEffectiveViewMode(mode: ViewMode, projectId?: string): void {
    if (projectId) {
      this.projectViewModes.set(projectId, mode);
    } else {
      this.viewMode = mode;
    }
  }

  setCardDensity(density: 'comfortable' | 'compact' | 'minimal'): void {
    this.cardDensity = density;
  }

  toggleColumnCollapsed(columnKey: string): void {
    if (this.collapsedColumns.has(columnKey)) {
      this.collapsedColumns.delete(columnKey);
    } else {
      this.collapsedColumns.add(columnKey);
    }
  }

  toggleGroupCollapsed(groupId: string): void {
    if (this.collapsedGroups.has(groupId)) {
      this.collapsedGroups.delete(groupId);
    } else {
      this.collapsedGroups.add(groupId);
    }
  }

  setColumnWidth(columnKey: string, width: number): void {
    this.columnWidths.set(columnKey, width);
  }

  toggleHiddenColumn(columnKey: string): void {
    if (this.hiddenColumns.has(columnKey)) {
      this.hiddenColumns.delete(columnKey);
    } else {
      this.hiddenColumns.add(columnKey);
    }
  }

  setWipLimit(columnKey: string, limit: number): void {
    this.wipLimits.set(columnKey, limit);
  }

  // ---- Filter Set Actions ----

  setFilterStates(states: string[]): void {
    this.filterStates = states;
  }

  setFilterPriorities(priorities: string[]): void {
    this.filterPriorities = priorities;
  }

  setFilterTypes(types: string[]): void {
    this.filterTypes = types;
  }

  setFilterAssigneeIds(ids: string[]): void {
    this.filterAssigneeIds = ids;
  }

  setFilterLabelIds(ids: string[]): void {
    this.filterLabelIds = ids;
  }

  setFilterProjectIds(ids: string[]): void {
    this.filterProjectIds = ids;
  }

  // ---- Filter Toggle Actions ----

  toggleFilterState(state: string): void {
    this.filterStates = toggleItem(this.filterStates, state);
  }

  toggleFilterPriority(priority: string): void {
    this.filterPriorities = toggleItem(this.filterPriorities, priority);
  }

  toggleFilterType(type: string): void {
    this.filterTypes = toggleItem(this.filterTypes, type);
  }

  toggleFilterAssigneeId(id: string): void {
    this.filterAssigneeIds = toggleItem(this.filterAssigneeIds, id);
  }

  toggleFilterLabelId(id: string): void {
    this.filterLabelIds = toggleItem(this.filterLabelIds, id);
  }

  toggleFilterProjectId(id: string): void {
    this.filterProjectIds = toggleItem(this.filterProjectIds, id);
  }

  clearAllFilters(): void {
    this.filterStates = [];
    this.filterPriorities = [];
    this.filterTypes = [];
    this.filterAssigneeIds = [];
    this.filterLabelIds = [];
    this.filterProjectIds = [];
  }

  // ---- Selection Actions ----

  toggleSelectedIssue(issueId: string): void {
    if (this.selectedIssueIds.has(issueId)) {
      this.selectedIssueIds.delete(issueId);
    } else {
      this.selectedIssueIds.add(issueId);
    }
  }

  selectAll(issueIds: string[]): void {
    this.selectedIssueIds = new Set(issueIds);
  }

  clearSelection(): void {
    this.selectedIssueIds.clear();
  }

  // ---- Lifecycle ----

  reset(): void {
    this.viewMode = 'board';
    this.cardDensity = 'comfortable';
    this.collapsedColumns.clear();
    this.collapsedGroups.clear();
    this.columnWidths.clear();
    this.hiddenColumns.clear();
    this.wipLimits.clear();
    this.filterStates = [];
    this.filterPriorities = [];
    this.filterTypes = [];
    this.filterAssigneeIds = [];
    this.filterLabelIds = [];
    this.filterProjectIds = [];
    this.selectedIssueIds.clear();
    this.projectViewModes.clear();
  }

  dispose(): void {
    for (const disposer of this.reactionDisposers) {
      disposer();
    }
    this.reactionDisposers = [];
  }

  // ---- Persistence (private) ----

  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const state: PersistedIssueViewState = JSON.parse(stored);
        this.viewMode = state.viewMode ?? 'board';
        this.cardDensity = state.cardDensity ?? 'comfortable';
        this.collapsedColumns = new Set(state.collapsedColumns ?? []);
        this.collapsedGroups = new Set(state.collapsedGroups ?? []);
        this.columnWidths = new Map(Object.entries(state.columnWidths ?? {}));
        this.hiddenColumns = new Set(state.hiddenColumns ?? []);
        this.wipLimits = new Map(Object.entries(state.wipLimits ?? {}));
        this.filterStates = state.filterStates ?? [];
        this.filterPriorities = state.filterPriorities ?? [];
        this.filterTypes = state.filterTypes ?? [];
        this.filterAssigneeIds = state.filterAssigneeIds ?? [];
        this.filterLabelIds = state.filterLabelIds ?? [];
        this.filterProjectIds = state.filterProjectIds ?? [];
        this.projectViewModes = new Map(Object.entries(state.projectViewModes ?? {}));
      }
    } catch {
      // Ignore parse errors
    }
  }

  private setupPersistence(): void {
    const disposer = reaction(
      () => ({
        viewMode: this.viewMode,
        cardDensity: this.cardDensity,
        collapsedColumns: Array.from(this.collapsedColumns),
        collapsedGroups: Array.from(this.collapsedGroups),
        columnWidths: Object.fromEntries(this.columnWidths),
        hiddenColumns: Array.from(this.hiddenColumns),
        wipLimits: Object.fromEntries(this.wipLimits),
        filterStates: this.filterStates.slice(),
        filterPriorities: this.filterPriorities.slice(),
        filterTypes: this.filterTypes.slice(),
        filterAssigneeIds: this.filterAssigneeIds.slice(),
        filterLabelIds: this.filterLabelIds.slice(),
        filterProjectIds: this.filterProjectIds.slice(),
        projectViewModes: Object.fromEntries(this.projectViewModes),
      }),
      (state) => {
        if (typeof window === 'undefined') return;

        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch {
          // Ignore storage errors
        }
      }
    );

    this.reactionDisposers.push(disposer);
  }
}

// ---- Helpers ----

function toggleItem(array: string[], item: string): string[] {
  const index = array.indexOf(item);
  if (index === -1) {
    return [...array, item];
  }
  return array.filter((v) => v !== item);
}

// ---- Singleton ----

export const issueViewStore = new IssueViewStore();
