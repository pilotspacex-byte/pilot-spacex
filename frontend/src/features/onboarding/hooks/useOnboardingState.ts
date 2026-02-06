'use client';

/**
 * useOnboardingState - TanStack Query hook for fetching onboarding state
 *
 * T019: Create useOnboardingState hook
 * Source: FR-001, FR-002, US1
 */
import { useQuery } from '@tanstack/react-query';
import { onboardingApi, type OnboardingState } from '@/services/api/onboarding';

/**
 * Query keys for onboarding data
 */
export const onboardingKeys = {
  all: ['onboarding'] as const,
  detail: (workspaceId: string) => [...onboardingKeys.all, 'detail', workspaceId] as const,
};

export interface UseOnboardingStateOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Enable query */
  enabled?: boolean;
}

/**
 * Hook for fetching onboarding state for a workspace
 *
 * FR-001: Display onboarding checklist (owner/admin only)
 * FR-002: Persist onboarding state per workspace
 */
export function useOnboardingState({ workspaceId, enabled = true }: UseOnboardingStateOptions) {
  return useQuery({
    queryKey: onboardingKeys.detail(workspaceId),
    queryFn: () => onboardingApi.getOnboardingState(workspaceId),
    enabled: enabled && !!workspaceId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 30, // 30 minutes
    retry: (failureCount, error) => {
      // Don't retry on 403 (not admin) or 404 (workspace not found)
      const status = (error as { status?: number })?.status;
      if (status === 403 || status === 404) {
        return false;
      }
      return failureCount < 3;
    },
  });
}

/**
 * Select whether all steps are completed
 */
export function selectIsComplete(data: OnboardingState | undefined): boolean {
  return data?.completionPercentage === 100;
}

/**
 * Select whether the checklist is dismissed
 */
export function selectIsDismissed(data: OnboardingState | undefined): boolean {
  if (!data) return false;
  return data.dismissedAt !== null;
}

/**
 * Select the completion percentage
 */
export function selectCompletionPercentage(data: OnboardingState | undefined): number {
  return data?.completionPercentage ?? 0;
}

/**
 * Select the next incomplete step
 */
export function selectNextIncompleteStep(
  data: OnboardingState | undefined
): 'ai_providers' | 'invite_members' | 'first_note' | null {
  if (!data) return null;

  if (!data.steps.ai_providers) return 'ai_providers';
  if (!data.steps.invite_members) return 'invite_members';
  if (!data.steps.first_note) return 'first_note';

  return null;
}
