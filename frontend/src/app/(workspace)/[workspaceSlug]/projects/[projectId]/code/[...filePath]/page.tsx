'use client';

/**
 * Code file page — IDE with a specific file pre-opened.
 *
 * Route: /{workspaceSlug}/projects/{projectId}/code/{...filePath}
 *
 * The catch-all [...filePath] segment is joined to form the file path,
 * which is passed as `initialFilePath` to EditorLayout for auto-open.
 *
 * Example:
 *   /my-workspace/projects/abc123/code/src/components/App.tsx
 *   → initialFilePath = "src/components/App.tsx"
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

export default function CodeFilePage() {
  const params = useParams<{
    workspaceSlug: string;
    projectId: string;
    filePath: string[];
  }>();

  const workspaceSlug = params.workspaceSlug ?? '';
  const projectId = params.projectId ?? '';
  // Join catch-all segments to reconstruct the full file path
  const initialFilePath = params.filePath ? params.filePath.join('/') : undefined;

  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';

  const { data: artifacts = [], isLoading } = useProjectArtifacts(workspaceId, projectId);

  if (isLoading) {
    return <Skeleton className="h-full w-full" />;
  }

  return (
    <div className="h-full w-full overflow-hidden" data-testid="code-file-page">
      <EditorLayout
        projectId={projectId}
        workspaceSlug={workspaceSlug}
        workspaceId={workspaceId}
        artifacts={artifacts}
        initialFilePath={initialFilePath}
      />
    </div>
  );
}
