'use client';

import { useParams } from 'next/navigation';
import { IssueViewsRoot } from '@/features/issues/components/views/IssueViewsRoot';

/**
 * Project-scoped Issues page — shows only issues for the given project.
 * Project filter is pre-applied and hidden from the filter bar.
 */
export default function ProjectIssuesPage() {
  const params = useParams();
  const workspaceSlug = params.workspaceSlug as string;
  const projectId = params.projectId as string;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-2xl font-semibold">Tasks</h1>
        <p className="text-sm text-muted-foreground">Project tasks</p>
      </div>
      <IssueViewsRoot workspaceSlug={workspaceSlug} projectId={projectId} />
    </div>
  );
}
