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
import { usePathname, useRouter } from 'next/navigation';
import { useWorkspace } from '@/components/workspace-guard';
import { useWorkspaceStore } from '@/stores';
import { saveLastWorkspacePath } from '@/lib/workspace-nav';
import { AiNotConfiguredBanner } from '@/components/workspace/ai-not-configured-banner';
import { SmoothScrollProvider } from '@/features/editor/hooks/useLenisScroll';
import type { WorkspaceFeatureToggles } from '@/types';

/** Map first pathname segment after workspace slug to a feature toggle key. */
const ROUTE_FEATURE_MAP: Record<string, keyof WorkspaceFeatureToggles> = {
  notes: 'notes',
  issues: 'issues',
  projects: 'projects',
  members: 'members',
  docs: 'docs',
  skills: 'skills',
  costs: 'costs',
  approvals: 'approvals',
};

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
  const router = useRouter();

  useEffect(() => {
    saveLastWorkspacePath(workspaceSlug, pathname);
  }, [pathname, workspaceSlug]);

  // Route protection: redirect when navigating to a disabled feature
  useEffect(() => {
    // Wait until feature toggles are loaded
    if (!workspaceStore.featureToggles) return;

    // Extract the first path segment after /{workspaceSlug}/
    const segments = pathname.split('/').filter(Boolean);
    const routeSegment = segments[1]; // segments[0] is workspaceSlug
    if (!routeSegment) return;

    const featureKey = ROUTE_FEATURE_MAP[routeSegment];
    if (featureKey && !workspaceStore.isFeatureEnabled(featureKey)) {
      router.replace(`/${workspaceSlug}`);
    }
  }, [pathname, workspaceSlug, workspaceStore.featureToggles, router, workspaceStore]);

  return (
    <>
      <AiNotConfiguredBanner workspaceSlug={workspaceSlug} isOwner={isOwner} />
      <SmoothScrollProvider>{children}</SmoothScrollProvider>
    </>
  );
});

export default WorkspaceSlugLayout;
