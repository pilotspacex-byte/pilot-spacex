'use client';

/**
 * OnboardingChecklist - Onboarding modal dialog with role setup sub-flow.
 *
 * Migrated from RoleSkillStore to local React state.
 * Source: FR-001, FR-002, FR-003, FR-013, US1
 */
import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { useState, useCallback, useEffect, useMemo } from 'react';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import React from 'react';
import { Sparkles, Check } from 'lucide-react';
import {
  useOnboardingState,
  selectCompletionPercentage,
  selectNextIncompleteStep,
} from '../hooks/useOnboardingState';
import { useOnboardingActions } from '../hooks/useOnboardingActions';
import { useOnboardingStore } from '@/stores/RootStore';
import { useSkillTemplates } from '@/services/api/skill-templates';
import { ApiKeySetupStep } from './ApiKeySetupStep';
import { OnboardingStepItem } from './OnboardingStepItem';
import { OnboardingCelebration } from './OnboardingCelebration';
import { RoleSelectorStep } from './RoleSelectorStep';
import { SkillGenerationWizard } from './SkillGenerationWizard';
import { CustomRoleInput } from './CustomRoleInput';
import type { OnboardingStep } from '@/services/api/onboarding';
import type { SDLCRoleType } from '../constants/skill-wizard-constants';

export interface OnboardingChecklistProps {
  /** Workspace ID (required) */
  workspaceId: string;
  /** Workspace slug for navigation */
  workspaceSlug: string;
}

/**
 * Step configuration with UI metadata.
 */
const STEP_CONFIG: Record<
  OnboardingStep,
  {
    title: string;
    description: string;
    actionLabel: string;
    icon: 'key' | 'users' | 'note' | 'wand';
  }
> = {
  ai_providers: {
    title: 'Connect AI Services',
    description: 'Add API keys for Anthropic (LLM) and Google Gemini (Embedding)',
    actionLabel: 'Add API Keys',
    icon: 'key',
  },
  invite_members: {
    title: 'Invite Team Members',
    description: 'Collaborate with your team by inviting members',
    actionLabel: 'Invite Members',
    icon: 'users',
  },
  role_setup: {
    title: 'Set Up Your Role',
    description: 'Personalize your AI assistant for your SDLC role',
    actionLabel: 'Set Up',
    icon: 'wand',
  },
  first_note: {
    title: 'Create Your First Note',
    description: 'Start capturing ideas with our guided template',
    actionLabel: 'Create Note',
    icon: 'note',
  },
};

/** Views for the role setup sub-flow within the dialog. */
type RoleSetupView = 'checklist' | 'role_grid' | 'custom_role' | 'skill_wizard';

/** Ordered step display */
const STEP_ORDER: OnboardingStep[] = ['ai_providers', 'invite_members', 'role_setup', 'first_note'];

const MAX_ROLES = 3;

/**
 * Maps each onboarding step to its corresponding settings page path segment.
 */
const STEP_SETTINGS_PATH: Partial<Record<OnboardingStep, string>> = {
  ai_providers: 'settings/ai-providers',
  invite_members: 'settings/members',
  role_setup: 'settings/skills',
};

export const OnboardingChecklist = observer(function OnboardingChecklist({
  workspaceId,
  workspaceSlug,
}: OnboardingChecklistProps) {
  const router = useRouter();
  const onboardingStore = useOnboardingStore();
  const { data, isLoading, error } = useOnboardingState({ workspaceId });
  const {
    dismiss,
    updateStep,
    createNote,
    isLoading: isActionLoading,
  } = useOnboardingActions({
    workspaceId,
    workspaceSlug,
  });
  const { data: templates, isLoading: isLoadingTemplates } = useSkillTemplates(workspaceSlug);

  // Local state replacing RoleSkillStore
  const [selectedRoles, setSelectedRoles] = useState<SDLCRoleType[]>([]);
  const [customRoleDescription, setCustomRoleDescription] = useState('');

  const existingSkillRoleTypes = useMemo(
    () => (templates ?? []).filter(t => t.is_active).map((t) => t.role_type ?? t.name),
    [templates]
  );

  // Sub-flow state for role_setup step
  const [roleSetupView, setRoleSetupView] = useState<RoleSetupView>('checklist');
  // Track which role index we are configuring (0-based)
  const [currentWizardIndex, setCurrentWizardIndex] = useState(0);

  // Hydrate store on mount
  useEffect(() => {
    onboardingStore.hydrate();
  }, [onboardingStore]);

  // Reset sub-flow state when dialog closes
  const resetSubFlow = useCallback(() => {
    setRoleSetupView('checklist');
    setCurrentWizardIndex(0);
    setSelectedRoles([]);
    setCustomRoleDescription('');
  }, []);

  const toggleRole = useCallback((roleType: SDLCRoleType) => {
    setSelectedRoles(prev => {
      const index = prev.indexOf(roleType);
      if (index >= 0) {
        return prev.filter(r => r !== roleType);
      } else if (prev.length < MAX_ROLES) {
        return [...prev, roleType];
      }
      return prev;
    });
  }, []);

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
      resetSubFlow();
    }
  };

  const handleDismiss = () => {
    dismiss.mutate();
    resetSubFlow();
  };

  const handleStepAction = (step: OnboardingStep) => {
    onboardingStore.setActiveStep(step);

    if (step === 'role_setup') {
      // Open the role selection sub-flow WITHIN the dialog
      setSelectedRoles([]);
      setRoleSetupView('role_grid');
    } else if (step === 'first_note') {
      createNote.mutate();
    } else if (step === 'ai_providers') {
      // No navigation -- ApiKeySetupStep renders inline below the step item
    } else if (step === 'invite_members') {
      onboardingStore.setInviteDialogFromOnboarding(true);
      onboardingStore.closeModal();
      router.push(`/${workspaceSlug}/settings/members`);
    }
  };

  // Role selection flow handlers
  const handleRoleContinue = () => {
    if (selectedRoles.length === 0) return;
    setCurrentWizardIndex(0);
    setRoleSetupView('skill_wizard');
  };

  const handleRoleSkip = () => {
    resetSubFlow();
  };

  const handleCustomRole = () => {
    setRoleSetupView('custom_role');
  };

  const handleCustomRoleBack = () => {
    setRoleSetupView('role_grid');
  };

  const handleCustomRoleGenerate = () => {
    // Add 'custom' to selected roles if not already there
    if (!selectedRoles.includes('custom')) {
      toggleRole('custom');
    }
    // Advance to wizard for the custom role
    const customIndex = selectedRoles.includes('custom')
      ? selectedRoles.indexOf('custom')
      : selectedRoles.length; // will be added by toggleRole
    setCurrentWizardIndex(customIndex);
    setRoleSetupView('skill_wizard');
  };

  const handleWizardBack = () => {
    if (currentWizardIndex > 0) {
      setCurrentWizardIndex(currentWizardIndex - 1);
    } else {
      setRoleSetupView('role_grid');
    }
  };

  const handleWizardComplete = () => {
    const nextIndex = currentWizardIndex + 1;

    if (nextIndex < selectedRoles.length) {
      // More roles to configure
      setCurrentWizardIndex(nextIndex);
    } else {
      // All roles configured -- mark step complete
      updateStep.mutate({ step: 'role_setup', completed: true });
      resetSubFlow();
    }
  };

  // Find the current wizard role's template
  const currentWizardRole = selectedRoles[currentWizardIndex];
  const currentTemplate = templates?.find((t) => (t.role_type ?? t.name) === currentWizardRole);

  // Determine if we show the sub-flow or the checklist
  const showSubFlow = roleSetupView !== 'checklist';
  const needsWideModal = roleSetupView === 'skill_wizard' || roleSetupView === 'custom_role';

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        className={needsWideModal ? 'sm:max-w-4xl' : 'sm:max-w-2xl'}
        showCloseButton={!onboardingStore.showingCelebration && !showSubFlow}
      >
        {onboardingStore.showingCelebration ? (
          <OnboardingCelebration />
        ) : showSubFlow ? (
          // --- ROLE SETUP SUB-FLOW ---
          <div className="py-2">
            {roleSetupView === 'role_grid' && (
              <RoleSelectorStep
                existingSkillRoleTypes={existingSkillRoleTypes}
                selectedRoles={selectedRoles}
                onToggleRole={toggleRole}
                templates={templates}
                isLoadingTemplates={isLoadingTemplates}
                onContinue={handleRoleContinue}
                onSkip={handleRoleSkip}
                onBack={resetSubFlow}
                onCustomRole={handleCustomRole}
              />
            )}
            {roleSetupView === 'custom_role' && (
              <CustomRoleInput
                description={customRoleDescription}
                onDescriptionChange={setCustomRoleDescription}
                onBack={handleCustomRoleBack}
                onGenerate={handleCustomRoleGenerate}
              />
            )}
            {roleSetupView === 'skill_wizard' && currentWizardRole && (
              <SkillGenerationWizard
                roleType={currentWizardRole}
                template={currentTemplate}
                workspaceId={workspaceId}
                onBack={handleWizardBack}
                onComplete={handleWizardComplete}
                currentIndex={currentWizardIndex + 1}
                totalRoles={selectedRoles.length}
                isPrimary={currentWizardIndex === 0}
              />
            )}
          </div>
        ) : (
          // --- STANDARD CHECKLIST ---
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
              {STEP_ORDER.map((step) => {
                const settingsPath = STEP_SETTINGS_PATH[step];
                const settingsHref = settingsPath ? `/${workspaceSlug}/${settingsPath}` : undefined;
                return (
                  <React.Fragment key={step}>
                    <OnboardingStepItem
                      step={step}
                      config={STEP_CONFIG[step]}
                      completed={data.steps[step]}
                      isActive={onboardingStore.activeStep === step}
                      isNext={nextStep === step}
                      onAction={() => handleStepAction(step)}
                      disabled={isActionLoading}
                      settingsHref={settingsHref}
                    />
                    {step === 'ai_providers' &&
                      onboardingStore.activeStep === 'ai_providers' &&
                      !data.steps[step] && (
                        <ApiKeySetupStep
                          workspaceId={workspaceId}
                          workspaceSlug={workspaceSlug}
                          onNavigateToSettings={() => {
                            onboardingStore.closeModal();
                            router.push(`/${workspaceSlug}/settings/ai-providers`);
                          }}
                        />
                      )}
                  </React.Fragment>
                );
              })}

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
