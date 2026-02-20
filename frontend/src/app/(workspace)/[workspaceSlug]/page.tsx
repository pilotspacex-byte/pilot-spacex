'use client';

import { use } from 'react';
import { observer } from 'mobx-react-lite';
import { useWorkspaceStore } from '@/stores/RootStore';
import { OnboardingChecklist } from '@/features/onboarding';
import { HomepageHub } from '@/features/homepage';

interface WorkspaceHomePageProps {
  params: Promise<{ workspaceSlug: string }>;
}

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }: WorkspaceHomePageProps) {
  const { workspaceSlug } = use(params);
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  return (
    <div className="flex h-full flex-col">
      {/* Onboarding Modal (renders as Dialog, no layout space) */}
      <OnboardingChecklist workspaceId={workspaceId} workspaceSlug={workspaceSlug} />

      {/* Homepage Hub — 2-panel layout: DailyBrief + ChatView */}
      <HomepageHub workspaceSlug={workspaceSlug} />
    </div>
  );
});

export default WorkspaceHomePage;
