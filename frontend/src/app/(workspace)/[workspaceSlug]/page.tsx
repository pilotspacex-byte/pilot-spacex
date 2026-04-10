'use client';

import { use } from 'react';
import { observer } from 'mobx-react-lite';
import { useWorkspace } from '@/components/workspace-guard';
import { useWorkspaceStore } from '@/stores';
import { OnboardingChecklist } from '@/features/onboarding';
import { HomepageHub } from '@/features/homepage';
import { ChatEmptyState } from '@/features/ai/ChatView/ChatEmptyState';

interface WorkspaceHomePageProps {
  params: Promise<{ workspaceSlug: string }>;
}

const WorkspaceHomePage = observer(function WorkspaceHomePage({ params }: WorkspaceHomePageProps) {
  const { workspaceSlug } = use(params);
  const { workspace } = useWorkspace();
  const workspaceStore = useWorkspaceStore();
  const useV2Layout = workspaceStore.isFeatureEnabled('layout_v2');

  return (
    <div className="flex h-full flex-col">
      <OnboardingChecklist workspaceId={workspace.id} workspaceSlug={workspaceSlug} />

      {useV2Layout ? (
        <ChatEmptyState />
      ) : (
        <HomepageHub workspaceSlug={workspaceSlug} />
      )}
    </div>
  );
});

export default WorkspaceHomePage;
