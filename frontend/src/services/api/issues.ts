import { apiClient, type PaginatedResponse } from './client';
import type {
  Issue,
  CreateIssueData,
  UpdateIssueData,
  IssuePriority,
  Activity,
  ActivityTimelineResponse,
} from '@/types';

interface IssueFilters {
  projectId?: string;
  state?: string;
  priority?: string;
  assigneeId?: string;
  labels?: string[];
}

// AI Enhancement types
export interface LabelSuggestion {
  name: string;
  confidence: number;
  isExisting: boolean;
}

export interface PrioritySuggestion {
  priority: IssuePriority;
  confidence: number;
}

export interface EnhancementResponse {
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

export interface DuplicateCheckResponse {
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

export interface AssigneeRecommendationsResponse {
  recommendations: AssigneeRecommendation[];
}

export const issuesApi = {
  list(
    workspaceId: string,
    filters?: IssueFilters,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<Issue>> {
    const params: Record<string, string> = {
      page: String(page),
      pageSize: String(pageSize),
    };

    if (filters?.projectId) params.projectId = filters.projectId;
    if (filters?.state) params.state = filters.state;
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.assigneeId) params.assigneeId = filters.assigneeId;
    if (filters?.labels?.length) params.labels = filters.labels.join(',');

    return apiClient.get<PaginatedResponse<Issue>>(`/workspaces/${workspaceId}/issues`, { params });
  },

  get(workspaceId: string, issueId: string): Promise<Issue> {
    return apiClient.get<Issue>(`/workspaces/${workspaceId}/issues/${issueId}`);
  },

  getByIdentifier(workspaceId: string, identifier: string): Promise<Issue> {
    return apiClient.get<Issue>(`/workspaces/${workspaceId}/issues/by-identifier/${identifier}`);
  },

  create(workspaceId: string, data: CreateIssueData): Promise<Issue> {
    return apiClient.post<Issue>(`/workspaces/${workspaceId}/issues`, data);
  },

  update(workspaceId: string, issueId: string, data: UpdateIssueData): Promise<Issue> {
    return apiClient.patch<Issue>(`/workspaces/${workspaceId}/issues/${issueId}`, data);
  },

  delete(workspaceId: string, issueId: string): Promise<void> {
    return apiClient.delete<void>(`/workspaces/${workspaceId}/issues/${issueId}`);
  },

  updateState(workspaceId: string, issueId: string, state: string): Promise<Issue> {
    return apiClient.patch<Issue>(`/workspaces/${workspaceId}/issues/${issueId}/state`, { state });
  },

  assignTo(workspaceId: string, issueId: string, assigneeId: string | null): Promise<Issue> {
    return apiClient.patch<Issue>(`/workspaces/${workspaceId}/issues/${issueId}/assign`, {
      assigneeId,
    });
  },

  addLabels(workspaceId: string, issueId: string, labelIds: string[]): Promise<Issue> {
    return apiClient.post<Issue>(`/workspaces/${workspaceId}/issues/${issueId}/labels`, {
      labelIds,
    });
  },

  removeLabel(workspaceId: string, issueId: string, labelId: string): Promise<Issue> {
    return apiClient.delete<Issue>(
      `/workspaces/${workspaceId}/issues/${issueId}/labels/${labelId}`
    );
  },

  // Activity & Comment endpoints

  listActivities(
    _workspaceId: string,
    issueId: string,
    options?: { limit?: number; offset?: number }
  ): Promise<ActivityTimelineResponse> {
    const params: Record<string, string> = {};
    if (options?.limit !== undefined) params.limit = String(options.limit);
    if (options?.offset !== undefined) params.offset = String(options.offset);

    return apiClient.get<ActivityTimelineResponse>(`/issues/${issueId}/activities`, { params });
  },

  addComment(_workspaceId: string, issueId: string, data: { content: string }): Promise<Activity> {
    return apiClient.post<Activity>(`/issues/${issueId}/comments`, data);
  },

  // AI Enhancement endpoints

  enhance(
    workspaceId: string,
    data: { title: string; description: string | null; projectId: string }
  ): Promise<EnhancementResponse> {
    return apiClient.post<EnhancementResponse>(
      `/workspaces/${workspaceId}/issues/ai/enhance`,
      data
    );
  },

  checkDuplicates(
    workspaceId: string,
    data: {
      title: string;
      description: string | null;
      projectId?: string;
      excludeIssueId?: string;
      threshold?: number;
    }
  ): Promise<DuplicateCheckResponse> {
    return apiClient.post<DuplicateCheckResponse>(
      `/workspaces/${workspaceId}/issues/ai/check-duplicates`,
      data
    );
  },

  recommendAssignee(
    workspaceId: string,
    data: {
      title: string;
      description: string | null;
      labelNames: string[];
      projectId: string;
    }
  ): Promise<AssigneeRecommendationsResponse> {
    return apiClient.post<AssigneeRecommendationsResponse>(
      `/workspaces/${workspaceId}/issues/ai/recommend-assignee`,
      data
    );
  },

  recordSuggestionDecision(
    workspaceId: string,
    issueId: string,
    data: {
      suggestionType: 'label' | 'priority' | 'assignee' | 'title' | 'description' | 'duplicate';
      accepted: boolean;
      suggestionValue?: unknown;
    }
  ): Promise<void> {
    return apiClient.post<void>(
      `/workspaces/${workspaceId}/issues/${issueId}/ai/suggestion-decision`,
      data
    );
  },
};
