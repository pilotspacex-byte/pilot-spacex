'use client';

/**
 * useOnboardingActions - Mutation hooks for onboarding actions
 *
 * T020: Create useOnboardingActions hook
 * Source: FR-002, FR-003, FR-005, FR-011, FR-013, US1
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import {
  onboardingApi,
  type OnboardingState,
  type OnboardingStep,
  type AIProviderType,
  type ValidateKeyResponse,
} from '@/services/api/onboarding';
import { ApiError } from '@/services/api/client';
import { onboardingKeys } from './useOnboardingState';
import { useOnboardingStore } from '@/stores/RootStore';

export interface UseOnboardingActionsOptions {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Workspace slug for navigation (optional) */
  workspaceSlug?: string;
}

/**
 * Hook for updating onboarding step completion
 *
 * FR-002: Persist onboarding completion state
 * FR-013: Celebration trigger when all steps complete
 */
export function useUpdateOnboardingStep({ workspaceId }: UseOnboardingActionsOptions) {
  const queryClient = useQueryClient();
  const onboardingStore = useOnboardingStore();

  return useMutation({
    mutationFn: ({ step, completed }: { step: OnboardingStep; completed: boolean }) =>
      onboardingApi.updateOnboardingStep(workspaceId, step, completed),

    onMutate: async ({ step, completed }) => {
      await queryClient.cancelQueries({
        queryKey: onboardingKeys.detail(workspaceId),
      });

      const previousState = queryClient.getQueryData<OnboardingState>(
        onboardingKeys.detail(workspaceId)
      );

      if (previousState) {
        const newSteps = { ...previousState.steps, [step]: completed };
        const completedCount = Object.values(newSteps).filter(Boolean).length;

        queryClient.setQueryData<OnboardingState>(onboardingKeys.detail(workspaceId), {
          ...previousState,
          steps: newSteps,
          completionPercentage: Math.round((completedCount / 3) * 100),
          completedAt: completedCount === 3 ? new Date().toISOString() : previousState.completedAt,
          updatedAt: new Date().toISOString(),
        });
      }

      return { previousState };
    },

    onSuccess: (data) => {
      queryClient.setQueryData(onboardingKeys.detail(workspaceId), data);

      // Trigger celebration when all steps complete (FR-013)
      if (data.completionPercentage === 100) {
        onboardingStore.triggerCelebration();
      }
    },

    onError: (error: Error, _variables, context) => {
      if (context?.previousState) {
        queryClient.setQueryData(onboardingKeys.detail(workspaceId), context.previousState);
      }

      toast.error('Failed to update onboarding', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for dismissing onboarding checklist
 *
 * FR-003: Dismiss checklist (collapse to sidebar reminder)
 */
export function useDismissOnboarding({ workspaceId }: UseOnboardingActionsOptions) {
  const queryClient = useQueryClient();
  const onboardingStore = useOnboardingStore();

  return useMutation({
    mutationFn: () => onboardingApi.dismissOnboarding(workspaceId),

    onMutate: async () => {
      await queryClient.cancelQueries({
        queryKey: onboardingKeys.detail(workspaceId),
      });

      const previousState = queryClient.getQueryData<OnboardingState>(
        onboardingKeys.detail(workspaceId)
      );

      if (previousState) {
        queryClient.setQueryData<OnboardingState>(onboardingKeys.detail(workspaceId), {
          ...previousState,
          dismissedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        });
      }

      // Close modal immediately
      onboardingStore.closeModal();

      return { previousState };
    },

    onSuccess: (data) => {
      queryClient.setQueryData(onboardingKeys.detail(workspaceId), data);
    },

    onError: (error: Error, _variables, context) => {
      if (context?.previousState) {
        queryClient.setQueryData(onboardingKeys.detail(workspaceId), context.previousState);
      }

      // Reopen modal on error
      onboardingStore.openModal();

      toast.error('Failed to dismiss onboarding', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for validating AI provider API key
 *
 * FR-005: Validate Anthropic key via separate endpoint
 * FR-006: Display Anthropic provider status
 */
export function useValidateProviderKey({ workspaceId }: UseOnboardingActionsOptions) {
  return useMutation({
    mutationFn: ({ provider, apiKey }: { provider: AIProviderType; apiKey: string }) =>
      onboardingApi.validateProviderKey(workspaceId, provider, apiKey),

    onSuccess: (data: ValidateKeyResponse) => {
      if (data.valid) {
        toast.success('API key validated', {
          description: `${data.modelsAvailable.length} models available`,
        });
      }
    },

    onError: (error: Error) => {
      toast.error('Validation failed', {
        description: error.message,
      });
    },
  });
}

/**
 * Hook for creating guided first note
 *
 * FR-011: Create guided note with template content
 */
export function useCreateGuidedNote({ workspaceId, workspaceSlug }: UseOnboardingActionsOptions) {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => onboardingApi.createGuidedNote(workspaceId),

    onSuccess: (data) => {
      // Invalidate onboarding state to reflect the new guided note
      queryClient.invalidateQueries({
        queryKey: onboardingKeys.detail(workspaceId),
      });

      toast.success('Guided note created', {
        description: 'Redirecting to your first note...',
      });

      // Navigate to the new note
      if (workspaceSlug) {
        router.push(`/${workspaceSlug}/notes/${data.noteId}`);
      } else {
        // Use the redirect URL from the response
        router.push(data.redirectUrl);
      }
    },

    onError: (error: Error) => {
      // Handle 409 Conflict (note already exists)
      if (error instanceof ApiError && error.status === 409) {
        toast.info('Guided note already exists', {
          description: 'Redirecting to your existing note...',
        });
        // The error headers contain the redirect URL, but we may not have access
        // to it here. The user can navigate manually.
        return;
      }

      toast.error('Failed to create guided note', {
        description: error.message,
      });
    },
  });
}

/**
 * Combined hook for common onboarding actions
 */
export function useOnboardingActions(options: UseOnboardingActionsOptions) {
  const updateStep = useUpdateOnboardingStep(options);
  const dismiss = useDismissOnboarding(options);
  const validateKey = useValidateProviderKey(options);
  const createNote = useCreateGuidedNote(options);

  return {
    updateStep,
    dismiss,
    validateKey,
    createNote,
    isLoading:
      updateStep.isPending || dismiss.isPending || validateKey.isPending || createNote.isPending,
  };
}
