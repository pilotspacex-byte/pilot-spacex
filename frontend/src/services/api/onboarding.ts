/**
 * Onboarding API client.
 *
 * Typed functions for onboarding endpoints.
 * T006: Create onboarding API client
 * Source: FR-001, FR-002, FR-003, FR-005, FR-011
 */

import { apiClient } from './client';

/**
 * Onboarding step names.
 */
export type OnboardingStep = 'ai_providers' | 'invite_members' | 'role_setup' | 'first_note';

/**
 * Onboarding steps status.
 */
export interface OnboardingSteps {
  ai_providers: boolean;
  invite_members: boolean;
  role_setup: boolean;
  first_note: boolean;
}

/**
 * Onboarding state response.
 * GET /api/v1/workspaces/{id}/onboarding
 */
export interface OnboardingState {
  id: string;
  workspaceId: string;
  steps: OnboardingSteps;
  guidedNoteId: string | null;
  dismissedAt: string | null;
  completedAt: string | null;
  completionPercentage: number;
  createdAt: string;
  updatedAt: string;
}

/**
 * AI provider types for validation.
 */
export type AIProviderType = 'anthropic';

/**
 * Key validation response.
 * POST /api/v1/workspaces/{id}/ai-providers/validate
 */
export interface ValidateKeyResponse {
  provider: AIProviderType;
  valid: boolean;
  errorMessage: string | null;
  modelsAvailable: string[];
}

/**
 * Guided note creation response.
 * POST /api/v1/workspaces/{id}/onboarding/guided-note
 */
export interface GuidedNoteResponse {
  noteId: string;
  title: string;
  redirectUrl: string;
}

/**
 * Onboarding API functions.
 */
export const onboardingApi = {
  /**
   * Get onboarding state for workspace.
   * FR-001, FR-002
   *
   * @param workspaceId - Workspace ID
   * @returns Onboarding state
   */
  getOnboardingState(workspaceId: string): Promise<OnboardingState> {
    return apiClient.get<OnboardingState>(`/workspaces/${workspaceId}/onboarding`);
  },

  /**
   * Update onboarding step completion.
   * FR-002
   *
   * @param workspaceId - Workspace ID
   * @param step - Step to update
   * @param completed - Completion status
   * @returns Updated onboarding state
   */
  updateOnboardingStep(
    workspaceId: string,
    step: OnboardingStep,
    completed: boolean
  ): Promise<OnboardingState> {
    return apiClient.patch<OnboardingState>(`/workspaces/${workspaceId}/onboarding`, {
      step,
      completed,
    });
  },

  /**
   * Dismiss onboarding checklist.
   * FR-003
   *
   * @param workspaceId - Workspace ID
   * @returns Updated onboarding state
   */
  dismissOnboarding(workspaceId: string): Promise<OnboardingState> {
    return apiClient.patch<OnboardingState>(`/workspaces/${workspaceId}/onboarding`, {
      dismissed: true,
    });
  },

  /**
   * Validate AI provider API key.
   * FR-005, FR-006
   *
   * @param workspaceId - Workspace ID
   * @param provider - Provider type (anthropic)
   * @param apiKey - API key to validate
   * @returns Validation result
   */
  validateProviderKey(
    workspaceId: string,
    provider: AIProviderType,
    apiKey: string
  ): Promise<ValidateKeyResponse> {
    return apiClient.post<ValidateKeyResponse>(`/workspaces/${workspaceId}/ai-providers/validate`, {
      provider,
      apiKey,
    });
  },

  /**
   * Create guided first note.
   * FR-011
   *
   * @param workspaceId - Workspace ID
   * @returns Created note info with redirect URL
   */
  createGuidedNote(workspaceId: string): Promise<GuidedNoteResponse> {
    return apiClient.post<GuidedNoteResponse>(`/workspaces/${workspaceId}/onboarding/guided-note`);
  },
};
