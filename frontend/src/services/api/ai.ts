import { apiClient } from './client';

/**
 * AI API client with typed endpoints.
 * @see specs/004-mvp-agents-build/tasks/P16-T111-T120.md#T113
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

// Types
export interface AIContextRequest {
  issue_id: string;
}

export interface PRReviewRequest {
  pr_number: number;
  repo_id: string;
}

export interface IssueExtractionRequest {
  note_id: string;
  max_issues?: number;
}

export interface ApprovalResolutionRequest {
  approved: boolean;
  note?: string;
  selected_issues?: number[];
}

export interface WorkspaceAISettingsFeatures {
  ghostTextEnabled: boolean;
  marginAnnotationsEnabled: boolean;
  aiContextEnabled: boolean;
  issueExtractionEnabled: boolean;
  prReviewEnabled: boolean;
  autoApproveNonDestructive: boolean;
}

export interface WorkspaceAISettingsProvider {
  provider: string;
  serviceType: 'embedding' | 'llm' | 'stt';
  isConfigured: boolean;
  isValid: boolean | null;
  lastValidatedAt: string | null;
  baseUrl?: string | null;
  modelName?: string | null;
}

export interface WorkspaceAISettings {
  workspaceId: string;
  providers: WorkspaceAISettingsProvider[];
  features: WorkspaceAISettingsFeatures;
  defaultLlmProvider: string;
  defaultEmbeddingProvider: string;
  defaultSttProvider?: string;
  costLimitUsd: number | null;
}

export interface WorkspaceAISettingsUpdateResponse {
  success: boolean;
  validationResults: Array<{
    provider: string;
    isValid: boolean;
    errorMessage: string | null;
  }>;
  updatedProviders: string[];
  updatedFeatures: boolean;
}

export interface CostSummary {
  workspace_id: string;
  period_start: string;
  period_end: string;
  total_cost_usd: number;
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  by_agent: Array<{
    agent_name: string;
    total_cost_usd: number;
    request_count: number;
    input_tokens: number;
    output_tokens: number;
  }>;
  by_user: Array<{
    user_id: string;
    user_name: string;
    total_cost_usd: number;
    request_count: number;
  }>;
  by_day: Array<{ date: string; total_cost_usd: number; request_count: number }>;
  /** Cost breakdown by operation_type. Present only when group_by=operation_type is requested. */
  by_feature: Record<string, number> | null;
}

export interface ApprovalListResponse {
  requests: ApprovalRequest[];
  total: number;
  pending_count: number;
}

export interface ApprovalRequest {
  id: string;
  agent_name: string;
  action_type: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  created_at: string;
  expires_at: string;
  requested_by: string;
  context_preview: string;
  payload?: Record<string, unknown>;
}

/** Full approval detail — returned by GET /ai/approvals/{id}. */
export interface ApprovalDetailResponse extends ApprovalRequest {
  payload: Record<string, unknown>;
  context: Record<string, unknown> | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
}

/** Response shape for POST /ai/approvals/{id}/resolve. */
export interface ApprovalResolutionResponse {
  approved: boolean;
  action_result: Record<string, unknown> | null;
  action_error: string | null;
}

export interface ConversationSession {
  session_id: string;
  issue_id: string;
  created_at: string;
  expires_at: string;
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

/**
 * AI API client for AI-powered features.
 * Provides both SSE streaming endpoints and REST endpoints.
 */
export const aiApi = {
  /**
   * SSE streaming endpoint URLs (return URL for SSE client).
   * These endpoints support Server-Sent Events for real-time streaming.
   */

  /**
   * Get ghost text streaming URL for note.
   * Uses new /api/v1/ai/ghost-text endpoint per T071-T074.
   * @param _noteId - Note UUID (unused, kept for API compatibility)
   * @returns SSE endpoint URL (absolute for EventSource)
   */
  getGhostTextUrl: (_noteId: string) => `${API_BASE}/ai/ghost-text`,

  /**
   * Get AI context streaming URL for issue.
   * @param issueId - Issue UUID
   * @returns SSE endpoint URL (absolute for EventSource)
   */
  getAIContextUrl: (issueId: string) => `${API_BASE}/issues/${issueId}/ai-context/stream`,

  /**
   * Get PR review streaming URL.
   * @param repoId - Repository UUID
   * @param prNumber - Pull request number
   * @returns SSE endpoint URL (absolute for EventSource)
   */
  getPRReviewUrl: (repoId: string, prNumber: number) =>
    `${API_BASE}/ai/repos/${repoId}/prs/${prNumber}/review`,

  /**
   * Get issue extraction streaming URL for note.
   * @param noteId - Note UUID
   * @returns SSE endpoint URL (absolute for EventSource)
   */
  getIssueExtractionUrl: (noteId: string) => `${API_BASE}/notes/${noteId}/extract-issues`,

  /**
   * Get margin annotations streaming URL for note.
   * @param noteId - Note UUID
   * @returns SSE endpoint URL (absolute for EventSource)
   */
  getAnnotationsUrl: (noteId: string) => `${API_BASE}/notes/${noteId}/annotations`,

  /**
   * Get conversation streaming URL for multi-turn chat.
   * @returns SSE endpoint URL
   */
  getConversationUrl: () => `/api/v1/ai/conversation`,

  /**
   * REST endpoints for AI settings and management.
   */

  /**
   * Get AI settings for workspace.
   * @param workspaceId - Workspace UUID
   * @returns Workspace AI settings
   */
  getWorkspaceSettings: (workspaceId: string) =>
    apiClient.get<WorkspaceAISettings>(`/workspaces/${workspaceId}/ai/settings`),

  /**
   * Update AI settings for workspace.
   * @param workspaceId - Workspace UUID
   * @param data - Settings update with optional API keys array and feature toggles
   * @returns Updated workspace AI settings
   */
  updateWorkspaceSettings: (
    workspaceId: string,
    data: {
      api_keys?: Array<{
        provider: string;
        service_type: 'embedding' | 'llm' | 'stt';
        api_key?: string;
        base_url?: string;
        model_name?: string;
      }>;
      features?: Partial<WorkspaceAISettingsFeatures>;
      default_llm_provider?: string;
      default_embedding_provider?: string;
    }
  ): Promise<WorkspaceAISettingsUpdateResponse> => {
    return apiClient.patch<WorkspaceAISettingsUpdateResponse>(
      `/workspaces/${workspaceId}/ai/settings`,
      data
    );
  },

  /**
   * Approval endpoints for human-in-the-loop actions.
   */

  /**
   * List approval requests with optional status filter.
   * @param status - Optional filter by status
   * @returns List of approval requests with pending count
   */
  listApprovals: (status?: 'pending' | 'approved' | 'rejected' | 'expired') =>
    apiClient.get<ApprovalListResponse>('/ai/approvals', { params: { status } }),

  /**
   * Get specific approval request by ID.
   * @param approvalId - Approval request UUID
   * @returns Approval request details
   */
  getApproval: (approvalId: string) =>
    apiClient.get<ApprovalDetailResponse>(`/ai/approvals/${approvalId}`),

  /**
   * Resolve approval request (approve/reject).
   * @param approvalId - Approval request UUID
   * @param resolution - Approval resolution with optional note and selected issues
   * @returns Resolution outcome (approved flag + optional action result/error)
   */
  resolveApproval: (approvalId: string, resolution: ApprovalResolutionRequest) =>
    apiClient.post<ApprovalResolutionResponse>(`/ai/approvals/${approvalId}/resolve`, resolution),

  /**
   * Cost tracking endpoints.
   */

  /**
   * Get cost summary for workspace AI usage.
   * @param workspaceId - Workspace UUID
   * @param startDate - Start date (YYYY-MM-DD format)
   * @param endDate - End date (YYYY-MM-DD format)
   * @returns Cost summary with breakdowns by agent, user, and day
   */
  getCostSummary: (workspaceId: string, startDate: string, endDate: string, groupBy?: string) =>
    apiClient.get<CostSummary>(`/ai/costs/summary`, {
      params: {
        start_date: startDate,
        end_date: endDate,
        ...(groupBy ? { group_by: groupBy } : {}),
      },
      headers: { 'X-Workspace-Id': workspaceId },
    }),

  /**
   * Conversation endpoints for multi-turn chat.
   */

  /**
   * Create conversation session for issue.
   * @param issueId - Issue UUID
   * @returns Conversation session
   */
  createConversationSession: (issueId: string) =>
    apiClient.post<ConversationSession>('/ai/conversation/sessions', { issue_id: issueId }),

  /**
   * Get conversation history for session.
   * @param sessionId - Session UUID
   * @returns List of conversation messages
   */
  getConversationHistory: (sessionId: string) =>
    apiClient.get<ConversationMessage[]>(`/ai/conversation/sessions/${sessionId}/messages`),

  /**
   * Approve an action request with optional note.
   * @param requestId - Request UUID
   * @param modifications - Optional modifications to apply (passed as note)
   * @returns Approval resolution result
   */
  approveAction: (requestId: string, modifications?: Record<string, unknown>) =>
    apiClient.post<{
      approved: boolean;
      action_result: Record<string, unknown> | null;
      action_error: string | null;
    }>(`/ai/approvals/${requestId}/resolve`, {
      approved: true,
      note: modifications ? JSON.stringify(modifications) : undefined,
    }),

  /**
   * Reject an action request with a reason.
   * @param requestId - Request UUID
   * @param reason - Rejection reason
   * @returns Approval resolution result
   */
  rejectAction: (requestId: string, reason: string) =>
    apiClient.post<{
      approved: boolean;
      action_result: Record<string, unknown> | null;
      action_error: string | null;
    }>(`/ai/approvals/${requestId}/resolve`, { approved: false, note: reason }),

  /**
   * List available skills from backend templates.
   * @returns Skill definitions with UI metadata
   */
  listSkills: () =>
    apiClient.get<{
      skills: Array<{
        name: string;
        description: string;
        category: string;
        icon: string;
        examples: string[];
      }>;
    }>('/skills'),

  /**
   * Create issues from AI extraction results (auto-approve, DD-003 non-destructive).
   * @param workspaceId - Workspace UUID (unused, kept for interface compatibility)
   * @param noteId - Note UUID the issues were extracted from (null for no-note extraction)
   * @param issues - Issues to create with priority as int (0=urgent…4=none)
   * @param projectId - Project to assign the issues to
   * @returns Created issue data with identifiers
   */
  createExtractedIssues: (
    _workspaceId: string,
    noteId: string | null,
    issues: Array<{
      title: string;
      description?: string | null;
      priority?: number;
      source_block_id?: string | null;
    }>,
    projectId?: string | null
  ) => {
    const issuePayload = issues.map((i) => ({
      title: i.title,
      description: i.description ?? null,
      priority: i.priority ?? 4,
      source_block_id: i.source_block_id ?? null,
    }));
    const url = noteId ? `/notes/${noteId}/extract-issues/approve` : `/extract-issues/approve`;
    return apiClient.post<{
      created_issues: Array<{ id: string; identifier: string; title: string }>;
      created_count: number;
    }>(url, {
      issues: issuePayload,
      project_id: projectId ?? null,
    });
  },

  // ============================================================
  // Feature 015: Intent API (T-014, M2)
  // ============================================================

  /**
   * Confirm a detected intent.
   * Optionally pass sessionId to signal the ConfirmationBus (T-018).
   */
  confirmIntent: (workspaceId: string, intentId: string, sessionId?: string) =>
    apiClient.post<IntentResponse>(`/workspaces/${workspaceId}/intents/${intentId}/confirm`, {
      session_id: sessionId ?? null,
    }),

  /**
   * Reject an intent.
   */
  rejectIntent: (workspaceId: string, intentId: string, sessionId?: string) =>
    apiClient.post<IntentResponse>(`/workspaces/${workspaceId}/intents/${intentId}/reject`, {
      session_id: sessionId ?? null,
    }),

  /**
   * Edit intent fields before confirmation.
   */
  editIntent: (
    workspaceId: string,
    intentId: string,
    patch: { new_what?: string; new_why?: string; new_constraints?: string[] }
  ) => apiClient.post<IntentResponse>(`/workspaces/${workspaceId}/intents/${intentId}/edit`, patch),

  /**
   * Batch confirm top-N eligible intents.
   */
  confirmAllIntents: (workspaceId: string, minConfidence = 0.7, maxCount = 10) =>
    apiClient.post<ConfirmAllResponse>(`/workspaces/${workspaceId}/intents/confirm-all`, {
      min_confidence: minConfidence,
      max_count: maxCount,
    }),

  /**
   * List intents by status.
   */
  listIntents: (workspaceId: string, status = 'detected') =>
    apiClient.get<IntentResponse[]>(`/workspaces/${workspaceId}/intents`, {
      params: { intent_status: status },
    }),

  /**
   * Approve a skill output pending approval.
   */
  approveSkillOutput: (workspaceId: string, approvalId: string) =>
    apiClient.post<void>(`/workspaces/${workspaceId}/skill-approvals/${approvalId}/approve`, {}),

  /**
   * Reject a skill output pending approval.
   */
  rejectSkillOutput: (workspaceId: string, approvalId: string, reason?: string) =>
    apiClient.post<void>(`/workspaces/${workspaceId}/skill-approvals/${approvalId}/reject`, {
      reason,
    }),
};

// Intent response types (matches IntentResponse schema from backend — EntitySchema → camelCase)
export interface IntentResponse {
  id: string;
  workspaceId: string;
  what: string;
  why?: string;
  constraints?: unknown[];
  acceptance?: unknown[];
  status: string;
  dedupStatus: string;
  confidence: number;
  owner?: string;
  sourceBlockId?: string;
  parentIntentId?: string;
  dedupHash?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ConfirmAllResponse {
  confirmed: IntentResponse[];
  confirmedCount: number;
  remainingCount: number;
  deduplicatingCount: number;
}
