'use client';

import { useParams } from 'next/navigation';
import { IssueViewsRoot } from '@/features/issues/components/views/IssueViewsRoot';

export default function ProjectHubPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  return <IssueViewsRoot workspaceSlug={params.workspaceSlug} projectId={params.projectId} />;
}
