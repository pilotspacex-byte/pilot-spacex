/**
 * Project members page — view and manage project member assignments (US1, FR-01).
 * Route: /[workspaceSlug]/projects/[projectId]/members
 */

'use client';

import { ProjectMembersTab } from '@/features/projects/components/project-members-tab';
import { useProject } from '@/features/projects/hooks';
import { useStore } from '@/stores';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';

export default observer(function ProjectMembersPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const { workspaceStore } = useStore();

  const workspace = workspaceStore.getWorkspaceBySlug(params.workspaceSlug);
  const workspaceId = workspace?.id ?? params.workspaceSlug;

  const { data: project } = useProject({ projectId: params.projectId });

  const isAdmin = workspaceStore.isAdmin;

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-6 py-4">
        <h1 className="text-lg font-semibold">Members</h1>
        {project && (
          <p className="text-sm text-muted-foreground mt-1">
            Manage who has access to <span className="font-medium">{project.name}</span>
          </p>
        )}
      </div>
      <div className="flex-1 overflow-auto">
        <ProjectMembersTab
          workspaceId={workspaceId}
          projectId={params.projectId}
          isAdmin={isAdmin}
        />
      </div>
    </div>
  );
});
