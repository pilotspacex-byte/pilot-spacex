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

export interface WorkspaceAISettings {
  anthropic_key_set: boolean;
  openai_key_set: boolean;
  ghost_text_enabled: boolean;
  margin_annotations_enabled: boolean;
  ai_context_enabled: boolean;
  issue_extraction_enabled: boolean;
  pr_review_enabled: boolean;
  provider_status?: Array<{
    provider: 'anthropic' | 'openai' | 'google';
    key_set: boolean;
    last_validated_at?: string | null;
    status?: 'connected' | 'disconnected' | 'unknown';
  }>;
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
}

export interface ApprovalListResponse {
  requests: ApprovalRequest[];
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
   * @param settings - Partial settings update with optional API keys
   * @returns Updated workspace AI settings
   */
  updateWorkspaceSettings: (
    workspaceId: string,
    settings: Partial<WorkspaceAISettings> & {
      anthropic_api_key?: string;
      openai_api_key?: string;
    }
  ) => apiClient.put<WorkspaceAISettings>(`/workspaces/${workspaceId}/ai/settings`, settings),

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
    apiClient.get<ApprovalRequest>(`/ai/approvals/${approvalId}`),

  /**
   * Resolve approval request (approve/reject).
   * @param approvalId - Approval request UUID
   * @param resolution - Approval resolution with optional note and selected issues
   * @returns Updated approval request
   */
  resolveApproval: (approvalId: string, resolution: ApprovalResolutionRequest) =>
    apiClient.post<ApprovalRequest>(`/ai/approvals/${approvalId}/resolve`, resolution),

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
  getCostSummary: (workspaceId: string, startDate: string, endDate: string) =>
    apiClient.get<CostSummary>(`/ai/costs/summary`, {
      params: { start_date: startDate, end_date: endDate },
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
   * Approve an action request with optional modifications.
   * @param requestId - Request UUID
   * @param modifications - Optional modifications to apply
   * @returns Updated approval request
   */
  approveAction: (requestId: string, modifications?: Record<string, unknown>) =>
    apiClient.post<ApprovalRequest>(`/ai/approvals/${requestId}/approve`, { modifications }),

  /**
   * Reject an action request with a reason.
   * @param requestId - Request UUID
   * @param reason - Rejection reason
   * @returns Updated approval request
   */
  rejectAction: (requestId: string, reason: string) =>
    apiClient.post<ApprovalRequest>(`/ai/approvals/${requestId}/reject`, { reason }),

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
   * Create issues from AI extraction results.
   * User explicitly selected which issues to create — no approval needed.
   * @param workspaceId - Workspace UUID
   * @param noteId - Note UUID the issues were extracted from
   * @param issues - Selected extracted issues to create
   * @returns Created issue IDs
   */
  createExtractedIssues: (
    _workspaceId: string,
    noteId: string,
    issues: Array<{
      title: string;
      description?: string;
      priority?: string;
      type?: string;
      source_block_id?: string | null;
    }>
  ) =>
    apiClient.post<{ created_issues: string[]; created_count: number }>(
      `/notes/${noteId}/extract-issues/approve`,
      { approval_id: '', selected_issues: issues.map((_, i) => i) }
    ),

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

// Intent response types (matches IntentResponse schema from backend)
export interface IntentResponse {
  id: string;
  workspace_id: string;
  what: string;
  why?: string;
  constraints?: unknown[];
  acceptance?: unknown[];
  status: string;
  dedup_status: string;
  confidence: number;
  owner?: string;
  source_block_id?: string;
  parent_intent_id?: string;
  dedup_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface ConfirmAllResponse {
  confirmed: IntentResponse[];
  confirmed_count: number;
  remaining_count: number;
  deduplicating_count: number;
}
