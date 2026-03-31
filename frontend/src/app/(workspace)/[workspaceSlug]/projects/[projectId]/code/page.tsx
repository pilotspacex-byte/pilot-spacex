'use client';

/**
 * Code page — IDE for browsing and editing project artifacts.
 *
 * Route: /{workspaceSlug}/projects/{projectId}/code
 *
 * Renders the 3-panel EditorLayout with FileTree, Monaco editor,
 * BreadcrumbBar, TabBar, and StatusBar.
 */

import { useParams } from 'next/navigation';
import { useStore } from '@/stores';
import { useProjectArtifacts } from '@/features/artifacts/hooks';
import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';

const EditorLayout = dynamic(
  () => import('@/features/code/components/EditorLayout').then((m) => ({ default: m.EditorLayout })),
  {
    ssr: false,
    loading: () => <Skeleton className="h-full w-full" />,
  }
);

export default function CodePage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const workspaceSlug = params.workspaceSlug ?? '';
  const projectId = params.projectId ?? '';

  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  const { data: artifacts = [], isLoading } = useProjectArtifacts(workspaceId, projectId);

  if (isLoading) {
    return <Skeleton className="h-full w-full" />;
  }

  return (
    <div className="h-full w-full overflow-hidden" data-testid="code-page">
      <EditorLayout
        projectId={projectId}
        workspaceSlug={workspaceSlug}
        workspaceId={workspaceId}
        artifacts={artifacts}
      />
    </div>
  );
}
