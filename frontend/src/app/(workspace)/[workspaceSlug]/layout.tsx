'use client';

/**
 * Workspace-slug-scoped layout.
 *
 * Mounts the AiNotConfiguredBanner at the top of every workspace page (AIGOV-05).
 * Banner is only visible to Owners when BYOK is not configured.
 */

import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { usePathname } from 'next/navigation';
import { useWorkspace } from '@/components/workspace-guard';
import { useWorkspaceStore } from '@/stores';
import { saveLastWorkspacePath } from '@/lib/workspace-nav';
import { AiNotConfiguredBanner } from '@/components/workspace/ai-not-configured-banner';

interface WorkspaceSlugLayoutProps {
  children: ReactNode;
}

const WorkspaceSlugLayout = observer(function WorkspaceSlugLayout({
  children,
}: WorkspaceSlugLayoutProps) {
  const { workspaceSlug } = useWorkspace();
  const workspaceStore = useWorkspaceStore();
  const isOwner = workspaceStore.isOwner;
  const pathname = usePathname();

  useEffect(() => {
    saveLastWorkspacePath(workspaceSlug, pathname);
  }, [pathname, workspaceSlug]);

  return (
    <>
      <AiNotConfiguredBanner workspaceSlug={workspaceSlug} isOwner={isOwner} />
      {children}
    </>
  );
});

export default WorkspaceSlugLayout;
