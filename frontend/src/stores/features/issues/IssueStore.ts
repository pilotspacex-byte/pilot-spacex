import { makeAutoObservable, runInAction } from 'mobx';
import type {
  Issue,
  IssueState,
  IssuePriority,
  IssueType,
  CreateIssueData,
  UpdateIssueData,
  AIContext,
} from '@/types';

import { stateNameToKey } from '@/lib/issue-helpers';
import { issuesApi } from '@/services/api';

// AI Suggestion types
export interface LabelSuggestion {
  name: string;
  confidence: number;
  isExisting: boolean;
}

export interface PrioritySuggestion {
  priority: IssuePriority;
  confidence: number;
}

export interface EnhancementSuggestion {
  enhancedTitle: string;
  enhancedDescription: string | null;
  suggestedLabels: LabelSuggestion[];
  suggestedPriority: PrioritySuggestion | null;
  titleEnhanced: boolean;
  descriptionExpanded: boolean;
}

export interface DuplicateCandidate {
  issueId: string;
  identifier: string;
  title: string;
  similarity: number;
  explanation: string | null;
}

export interface DuplicateCheckResult {
  candidates: DuplicateCandidate[];
  hasLikelyDuplicate: boolean;
  highestSimilarity: number;
}

export interface AssigneeRecommendation {
  userId: string;
  name: string;
  confidence: number;
  reason: string;
}

interface IssueFilters {
  state?: IssueState | 'all';
  priority?: IssuePriority | 'all';
  type?: IssueType | 'all';
  assigneeId?: string | 'all';
  projectId?: string | 'all';
}

type GroupBy = 'state' | 'priority' | 'assignee' | 'project' | 'none';
type SortBy = 'created' | 'updated' | 'priority' | 'title';
type SortOrder = 'asc' | 'desc';

export class IssueStore {
  issues: Map<string, Issue> = new Map();
  currentIssueId: string | null = null;
  isLoading = false;
  isSaving = false;
  error: string | null = null;

  // AI Context for current issue
  aiContext: AIContext | null = null;
  isLoadingAIContext = false;

  // AI Enhancement state (T145)
  enhancementSuggestion: EnhancementSuggestion | null = null;
  isLoadingEnhancement = false;
  duplicateCheckResult: DuplicateCheckResult | null = null;
  isCheckingDuplicates = false;
  assigneeRecommendations: AssigneeRecommendation[] = [];
  isLoadingRecommendations = false;

  // Filters and sorting
  filters: IssueFilters = {};
  groupBy: GroupBy = 'state';
  sortBy: SortBy = 'updated';
  sortOrder: SortOrder = 'desc';
  searchQuery = '';

  // View state
  viewMode: 'board' | 'list' | 'table' = 'board';

  // Per-field save status for inline editing (T014)
  saveStatus: Map<string, 'idle' | 'saving' | 'saved' | 'error'> = new Map();
  /** @internal Not observable — cleanup timers only. */
  private _saveStatusTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  constructor() {
    makeAutoObservable<IssueStore, '_saveStatusTimers'>(this, {
      _saveStatusTimers: false,
    });
  }

  // Computed

  /** Aggregate save status across all fields: saving > error > saved > idle. */
  get aggregateSaveStatus(): 'idle' | 'saving' | 'saved' | 'error' {
    let hasSaved = false;
    for (const status of this.saveStatus.values()) {
      if (status === 'saving') return 'saving';
      if (status === 'error') return 'error';
      if (status === 'saved') hasSaved = true;
    }
    return hasSaved ? 'saved' : 'idle';
  }

  get currentIssue(): Issue | null {
    return this.currentIssueId ? (this.issues.get(this.currentIssueId) ?? null) : null;
  }

  get issuesList(): Issue[] {
    return Array.from(this.issues.values());
  }

  get filteredIssues(): Issue[] {
    let issues = this.issuesList;

    // Apply filters
    if (this.filters.state && this.filters.state !== 'all') {
      issues = issues.filter((i) => stateNameToKey(i.state.name) === this.filters.state);
    }
    if (this.filters.priority && this.filters.priority !== 'all') {
      issues = issues.filter((i) => i.priority === this.filters.priority);
    }
    if (this.filters.type && this.filters.type !== 'all') {
      issues = issues.filter((i) => i.type === this.filters.type);
    }
    if (this.filters.assigneeId && this.filters.assigneeId !== 'all') {
      issues = issues.filter((i) => i.assigneeId === this.filters.assigneeId);
    }
    if (this.filters.projectId && this.filters.projectId !== 'all') {
      issues = issues.filter((i) => i.projectId === this.filters.projectId);
    }

    // Apply search
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      issues = issues.filter(
        (i) =>
          (i.title ?? i.name).toLowerCase().includes(query) ||
          i.identifier.toLowerCase().includes(query) ||
          i.description?.toLowerCase().includes(query)
      );
    }

    // Apply sorting
    issues = this.sortIssues(issues);

    return issues;
  }

  get issuesByState(): Record<IssueState, Issue[]> {
    const states: IssueState[] = [
      'backlog',
      'todo',
      'in_progress',
      'in_review',
      'done',
      'cancelled',
    ];
    const grouped: Record<IssueState, Issue[]> = {} as Record<IssueState, Issue[]>;

    states.forEach((state) => {
      grouped[state] = this.filteredIssues.filter((i) => stateNameToKey(i.state.name) === state);
    });

    return grouped;
  }

  get issuesByPriority(): Record<IssuePriority, Issue[]> {
    const priorities: IssuePriority[] = ['urgent', 'high', 'medium', 'low', 'none'];
    const grouped: Record<IssuePriority, Issue[]> = {} as Record<IssuePriority, Issue[]>;

    priorities.forEach((priority) => {
      grouped[priority] = this.filteredIssues.filter((i) => i.priority === priority);
    });

    return grouped;
  }

  get backlogIssues(): Issue[] {
    return this.filteredIssues.filter((i) => i.state.group === 'backlog');
  }

  get inProgressIssues(): Issue[] {
    return this.filteredIssues.filter((i) => i.state.group === 'started');
  }

  get completedIssues(): Issue[] {
    return this.filteredIssues.filter(
      (i) => i.state.group === 'completed' || i.state.group === 'cancelled'
    );
  }

  // Helper
  private sortIssues(issues: Issue[]): Issue[] {
    const priorityOrder: Record<IssuePriority, number> = {
      urgent: 0,
      high: 1,
      medium: 2,
      low: 3,
      none: 4,
    };

    return [...issues].sort((a, b) => {
      let comparison = 0;

      switch (this.sortBy) {
        case 'created':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'updated':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
        case 'priority':
          comparison = priorityOrder[a.priority] - priorityOrder[b.priority];
          break;
        case 'title':
          comparison = (a.title ?? a.name).localeCompare(b.title ?? b.name);
          break;
      }

      return this.sortOrder === 'asc' ? comparison : -comparison;
    });
  }

  // Actions
  setCurrentIssue(issueId: string | null) {
    this.currentIssueId = issueId;
    this.aiContext = null;
  }

  setFilters(filters: Partial<IssueFilters>) {
    this.filters = { ...this.filters, ...filters };
  }

  clearFilters() {
    this.filters = {};
  }

  setGroupBy(groupBy: GroupBy) {
    this.groupBy = groupBy;
  }

  setSortBy(sortBy: SortBy) {
    this.sortBy = sortBy;
  }

  setSortOrder(sortOrder: SortOrder) {
    this.sortOrder = sortOrder;
  }

  setSearchQuery(query: string) {
    this.searchQuery = query;
  }

  setViewMode(mode: 'board' | 'list' | 'table') {
    this.viewMode = mode;
  }

  // Optimistic update for drag and drop
  optimisticUpdateState(issueId: string, newState: string) {
    const issue = this.issues.get(issueId);
    if (issue) {
      // Partial optimistic update: set state name for instant UI feedback;
      // the full StateBrief is corrected when the API response arrives.
      this.issues.set(issueId, {
        ...issue,
        state: { ...issue.state, name: newState },
      });
    }
  }

  // Async actions
  async loadIssues(workspaceId: string, projectId?: string) {
    this.isLoading = true;
    this.error = null;

    try {
      const response = await issuesApi.list(workspaceId, { projectId });
      runInAction(() => {
        this.issues.clear();
        response.items.forEach((issue) => {
          this.issues.set(issue.id, issue);
        });
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load issues';
        this.isLoading = false;
      });
    }
  }

  async loadIssue(workspaceId: string, issueId: string) {
    this.isLoading = true;
    this.error = null;

    try {
      const issue = await issuesApi.get(workspaceId, issueId);
      runInAction(() => {
        this.issues.set(issue.id, issue);
        this.currentIssueId = issue.id;
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to load issue';
        this.isLoading = false;
      });
    }
  }

  async createIssue(workspaceId: string, data: CreateIssueData) {
    this.isSaving = true;
    this.error = null;

    try {
      const issue = await issuesApi.create(workspaceId, data);
      runInAction(() => {
        this.issues.set(issue.id, issue);
        this.isSaving = false;
      });
      return issue;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to create issue';
        this.isSaving = false;
      });
      return null;
    }
  }

  async updateIssue(workspaceId: string, issueId: string, data: UpdateIssueData) {
    this.isSaving = true;
    this.error = null;

    try {
      const issue = await issuesApi.update(workspaceId, issueId, data);
      runInAction(() => {
        this.issues.set(issue.id, issue);
        this.isSaving = false;
      });
      return issue;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update issue';
        this.isSaving = false;
      });
      return null;
    }
  }

  async updateIssueState(workspaceId: string, issueId: string, state: string) {
    // Optimistic update
    this.optimisticUpdateState(issueId, state);

    try {
      const issue = await issuesApi.updateState(workspaceId, issueId, state);
      runInAction(() => {
        this.issues.set(issue.id, issue);
      });
      return issue;
    } catch (err) {
      // Rollback on error
      await this.loadIssue(workspaceId, issueId);
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to update issue state';
      });
      return null;
    }
  }

  async deleteIssue(workspaceId: string, issueId: string) {
    try {
      await issuesApi.delete(workspaceId, issueId);
      runInAction(() => {
        this.issues.delete(issueId);
        if (this.currentIssueId === issueId) {
          this.currentIssueId = null;
        }
      });
      return true;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to delete issue';
      });
      return false;
    }
  }

  async assignIssue(workspaceId: string, issueId: string, assigneeId: string | null) {
    try {
      const issue = await issuesApi.assignTo(workspaceId, issueId, assigneeId);
      runInAction(() => {
        this.issues.set(issue.id, issue);
      });
      return issue;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to assign issue';
      });
      return null;
    }
  }

  // ============================================================================
  // AI Enhancement Methods (T145)
  // ============================================================================

  /**
   * Request AI enhancement suggestions for issue content.
   */
  async getEnhancementSuggestions(
    workspaceId: string,
    title: string,
    description: string | null,
    projectId: string
  ): Promise<EnhancementSuggestion | null> {
    this.isLoadingEnhancement = true;
    this.enhancementSuggestion = null;

    try {
      const response = await issuesApi.enhance(workspaceId, {
        title,
        description,
        projectId,
      });
      runInAction(() => {
        this.enhancementSuggestion = response;
        this.isLoadingEnhancement = false;
      });
      return response;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to get enhancement suggestions';
        this.isLoadingEnhancement = false;
      });
      return null;
    }
  }

  /**
   * Check for potential duplicate issues.
   */
  async checkForDuplicates(
    workspaceId: string,
    title: string,
    description: string | null,
    projectId?: string,
    excludeIssueId?: string
  ): Promise<DuplicateCheckResult | null> {
    this.isCheckingDuplicates = true;
    this.duplicateCheckResult = null;

    try {
      const response = await issuesApi.checkDuplicates(workspaceId, {
        title,
        description,
        projectId,
        excludeIssueId,
        threshold: 0.75,
      });
      runInAction(() => {
        this.duplicateCheckResult = response;
        this.isCheckingDuplicates = false;
      });
      return response;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to check for duplicates';
        this.isCheckingDuplicates = false;
      });
      return null;
    }
  }

  /**
   * Get assignee recommendations for an issue.
   */
  async getAssigneeRecommendations(
    workspaceId: string,
    title: string,
    description: string | null,
    labelNames: string[],
    projectId: string
  ): Promise<AssigneeRecommendation[]> {
    this.isLoadingRecommendations = true;
    this.assigneeRecommendations = [];

    try {
      const response = await issuesApi.recommendAssignee(workspaceId, {
        title,
        description,
        labelNames,
        projectId,
      });
      runInAction(() => {
        this.assigneeRecommendations = response.recommendations;
        this.isLoadingRecommendations = false;
      });
      return response.recommendations;
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to get assignee recommendations';
        this.isLoadingRecommendations = false;
      });
      return [];
    }
  }

  /**
   * Record user decision on AI suggestion.
   */
  async recordSuggestionDecision(
    workspaceId: string,
    issueId: string,
    suggestionType: 'label' | 'priority' | 'assignee' | 'title' | 'description' | 'duplicate',
    accepted: boolean,
    suggestionValue?: unknown
  ): Promise<void> {
    try {
      await issuesApi.recordSuggestionDecision(workspaceId, issueId, {
        suggestionType,
        accepted,
        suggestionValue,
      });
    } catch (err) {
      console.error('Failed to record suggestion decision:', err);
    }
  }

  /**
   * Clear AI suggestion state.
   */
  clearAISuggestions() {
    this.enhancementSuggestion = null;
    this.duplicateCheckResult = null;
    this.assigneeRecommendations = [];
  }

  // ============================================================================
  // Per-field Save Status Methods (T014)
  // ============================================================================

  /**
   * Set save status for a specific field. Auto-clears to 'idle' after 2s when 'saved'.
   */
  setSaveStatus(field: string, status: 'idle' | 'saving' | 'saved' | 'error') {
    this.saveStatus.set(field, status);

    // Clear any existing auto-reset timer for this field
    const existing = this._saveStatusTimers.get(field);
    if (existing) {
      clearTimeout(existing);
      this._saveStatusTimers.delete(field);
    }

    // Auto-clear to 'idle' after 2s when status is 'saved'
    if (status === 'saved') {
      const timer = setTimeout(() => {
        runInAction(() => {
          this.saveStatus.set(field, 'idle');
        });
        this._saveStatusTimers.delete(field);
      }, 2000);
      this._saveStatusTimers.set(field, timer);
    }
  }

  /**
   * Get save status for a specific field. Defaults to 'idle' if not tracked.
   */
  getSaveStatus(field: string): 'idle' | 'saving' | 'saved' | 'error' {
    return this.saveStatus.get(field) ?? 'idle';
  }

  // Reset
  reset() {
    this.issues.clear();
    this.currentIssueId = null;
    this.isLoading = false;
    this.isSaving = false;
    this.error = null;
    this.aiContext = null;
    this.isLoadingAIContext = false;
    this.filters = {};
    this.groupBy = 'state';
    this.sortBy = 'updated';
    this.sortOrder = 'desc';
    this.searchQuery = '';
    this.viewMode = 'board';
    // AI state
    this.enhancementSuggestion = null;
    this.isLoadingEnhancement = false;
    this.duplicateCheckResult = null;
    this.isCheckingDuplicates = false;
    this.assigneeRecommendations = [];
    this.isLoadingRecommendations = false;
    // Save status (T014)
    this.saveStatus.clear();
    this._saveStatusTimers.forEach((timer) => clearTimeout(timer));
    this._saveStatusTimers.clear();
  }
}

export const issueStore = new IssueStore();
