'use client';

/**
 * OnboardingChecklist - Onboarding modal dialog
 *
 * T021: Create OnboardingChecklist component
 * Source: FR-001, FR-002, FR-003, FR-013, US1
 */
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Sparkles, Check } from 'lucide-react';
import {
  useOnboardingState,
  selectCompletionPercentage,
  selectNextIncompleteStep,
} from '../hooks/useOnboardingState';
import { useOnboardingActions } from '../hooks/useOnboardingActions';
import { useOnboardingStore } from '@/stores/RootStore';
import { useEffect } from 'react';
import { OnboardingStepItem } from './OnboardingStepItem';
import { OnboardingCelebration } from './OnboardingCelebration';
import type { OnboardingStep } from '@/services/api/onboarding';

export interface OnboardingChecklistProps {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Workspace slug for navigation */
  workspaceSlug: string;
}

/**
 * Step configuration with UI metadata
 */
const STEP_CONFIG: Record<
  OnboardingStep,
  {
    title: string;
    description: string;
    actionLabel: string;
    icon: 'key' | 'users' | 'note';
  }
> = {
  ai_providers: {
    title: 'Connect AI Provider',
    description: 'Add your Anthropic API key to enable AI features',
    actionLabel: 'Add API Key',
    icon: 'key',
  },
  invite_members: {
    title: 'Invite Team Members',
    description: 'Collaborate with your team by inviting members',
    actionLabel: 'Invite Members',
    icon: 'users',
  },
  first_note: {
    title: 'Create Your First Note',
    description: 'Start capturing ideas with our guided template',
    actionLabel: 'Create Note',
    icon: 'note',
  },
};

/**
 * OnboardingChecklist - modal dialog for 3-step onboarding
 *
 * FR-001: Display onboarding checklist (owner/admin only)
 * FR-002: Persist onboarding state per workspace
 * FR-003: Dismiss checklist via "Skip setup" or close modal
 * FR-013: Celebration trigger when all steps complete
 */
export const OnboardingChecklist = observer(function OnboardingChecklist({
  workspaceId,
  workspaceSlug,
}: OnboardingChecklistProps) {
  const router = useRouter();
  const onboardingStore = useOnboardingStore();
  const { data, isLoading, error } = useOnboardingState({ workspaceId });
  const {
    dismiss,
    createNote,
    isLoading: isActionLoading,
  } = useOnboardingActions({
    workspaceId,
    workspaceSlug,
  });

  // Hydrate store on mount
  useEffect(() => {
    onboardingStore.hydrate();
  }, [onboardingStore]);

  // Don't render if loading, error, or no data
  if (isLoading || error || !data) {
    return null;
  }

  // Don't render if dismissed or completed (server-side)
  if (data.dismissedAt || data.completedAt) {
    return null;
  }

  const completionPercentage = selectCompletionPercentage(data);
  const nextStep = selectNextIncompleteStep(data);
  const isComplete = completionPercentage === 100;
  const isOpen = onboardingStore.isModalOpen;

  const handleOpenChange = (open: boolean) => {
    if (!open && !onboardingStore.showingCelebration) {
      onboardingStore.closeModal();
    }
  };

  const handleDismiss = () => {
    dismiss.mutate();
  };

  const handleStepAction = (step: OnboardingStep) => {
    onboardingStore.setActiveStep(step);

    if (step === 'first_note') {
      createNote.mutate();
    } else if (step === 'ai_providers') {
      onboardingStore.closeModal();
      router.push(`/${workspaceSlug}/settings/ai-providers`);
    } else if (step === 'invite_members') {
      onboardingStore.setInviteDialogFromOnboarding(true);
      onboardingStore.closeModal();
      router.push(`/${workspaceSlug}/settings/members`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-xl" showCloseButton={!onboardingStore.showingCelebration}>
        {onboardingStore.showingCelebration ? (
          <OnboardingCelebration />
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Sparkles className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <DialogTitle className="text-lg">Welcome to Pilot Space</DialogTitle>
                  <DialogDescription>Complete these steps to get started</DialogDescription>
                </div>
              </div>

              <div className="mt-4">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{completionPercentage}%</span>
                </div>
                <Progress value={completionPercentage} className="h-2" />
              </div>
            </DialogHeader>

            <div className="space-y-3">
              {(['ai_providers', 'invite_members', 'first_note'] as OnboardingStep[]).map(
                (step) => (
                  <OnboardingStepItem
                    key={step}
                    step={step}
                    config={STEP_CONFIG[step]}
                    completed={data.steps[step]}
                    isActive={onboardingStore.activeStep === step}
                    isNext={nextStep === step}
                    onAction={() => handleStepAction(step)}
                    disabled={isActionLoading}
                  />
                )
              )}

              {isComplete && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/10 text-primary">
                  <Check className="h-5 w-5" />
                  <span className="font-medium">All set! You&apos;re ready to go.</span>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground"
                onClick={handleDismiss}
                disabled={dismiss.isPending}
              >
                Skip setup
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
});
