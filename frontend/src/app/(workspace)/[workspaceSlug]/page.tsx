'use client';

import { use } from 'react';
import { Sparkles, ChevronRight } from 'lucide-react';
import { observer } from 'mobx-react-lite';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useWorkspaceStore, useOnboardingStore } from '@/stores/RootStore';
import { OnboardingChecklist } from '@/features/onboarding';
import {
  useOnboardingState,
  selectCompletionPercentage,
} from '@/features/onboarding/hooks/useOnboardingState';
import { HomepageHub } from '@/features/homepage';

interface WorkspaceHomePageProps {
  params: Promise<{ workspaceSlug: string }>;
}

/**
 * Progress trigger shown when onboarding modal is closed but not dismissed.
 * Clicking re-opens the onboarding modal.
 */
const OnboardingTrigger = observer(function OnboardingTrigger({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const onboardingStore = useOnboardingStore();
  const { data } = useOnboardingState({ workspaceId });

  if (!data || data.dismissedAt || data.completedAt) return null;
  if (onboardingStore.isModalOpen) return null;

  const percentage = selectCompletionPercentage(data);

  return (
    <div className="mx-auto mb-6 motion-safe:animate-fade-up">
      <button
        onClick={() => onboardingStore.openModal()}
        className={cn(
          'flex items-center gap-2.5 px-4 py-2.5 rounded-lg',
          'border border-primary/20 bg-primary/5',
          'text-sm font-medium text-foreground',
          'transition-all duration-200',
          'hover:border-primary/40 hover:bg-primary/10 hover:shadow-sm'
        )}
      >
        <Sparkles className="h-4 w-4 text-primary" />
        <span>Setup: {percentage}%</span>
        <Progress value={percentage} className="h-1.5 w-16" />
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
      </button>
    </div>
  );
});

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }: WorkspaceHomePageProps) {
  const { workspaceSlug } = use(params);
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  return (
    <div className="flex h-full flex-col overflow-auto">
      {/* Onboarding Modal (renders as Dialog, no layout space) */}
      <OnboardingChecklist workspaceId={workspaceId} workspaceSlug={workspaceSlug} />

      {/* Progress trigger when modal is closed but onboarding active */}
      <div className="px-4 pt-4 sm:px-6 lg:px-8">
        <OnboardingTrigger workspaceId={workspaceId} />
      </div>

      {/* Homepage Hub — 3-zone layout (US-19) */}
      <HomepageHub workspaceSlug={workspaceSlug} />
    </div>
  );
});

export default WorkspaceHomePage;
