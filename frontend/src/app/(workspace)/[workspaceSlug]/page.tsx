'use client';

import { use } from 'react';
import { observer } from 'mobx-react-lite';
import { useWorkspace } from '@/components/workspace-guard';
import { OnboardingChecklist } from '@/features/onboarding';
import { HomepageHub } from '@/features/homepage';

interface WorkspaceHomePageProps {
  params: Promise<{ workspaceSlug: string }>;
}

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }: WorkspaceHomePageProps) {
  const { workspaceSlug } = use(params);
  const { workspace } = useWorkspace();
  // workspace.id is always a UUID — WorkspaceGuard resolves it from the API
  // before rendering children. This avoids the BUG-01 race condition where
  // workspaceStore.currentWorkspace?.id could be null on the first render,
  // causing the slug string to be passed to OnboardingChecklist instead.

  return (
    <div className="flex h-full flex-col">
      {/* Onboarding Modal (renders as Dialog, no layout space) */}
      <OnboardingChecklist workspaceId={workspace.id} workspaceSlug={workspaceSlug} />

      {/* Homepage Hub — 2-panel layout: DailyBrief + ChatView */}
      <HomepageHub workspaceSlug={workspaceSlug} />
    </div>
  );
});

export default WorkspaceHomePage;
