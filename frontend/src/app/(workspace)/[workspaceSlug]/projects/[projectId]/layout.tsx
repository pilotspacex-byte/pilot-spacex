'use client';

import { AccessDenied } from '@/components/access-denied';
import { ProjectSidebar } from '@/components/projects/ProjectSidebar';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useProject } from '@/features/projects/hooks';
import { ApiError } from '@/services/api/client';
import { AlertCircle } from 'lucide-react';
import { useParams } from 'next/navigation';

export default function ProjectDetailLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const {
    data: project,
    isLoading,
    isError,
    error,
    refetch,
  } = useProject({
    projectId: params.projectId,
  });

  if (isLoading) {
    return (
      <div className="flex h-full">
        <aside className="hidden md:flex md:w-56 md:flex-col md:border-r md:border-border">
          <div className="flex items-center gap-3 border-b border-border px-4 py-4">
            <Skeleton className="h-9 w-9 rounded-lg" />
            <div>
              <Skeleton className="h-4 w-24 mb-1" />
              <Skeleton className="h-3 w-12" />
            </div>
          </div>
          <div className="px-2 py-4 space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full rounded-md" />
            ))}
          </div>
        </aside>
        <main className="flex-1 overflow-auto p-6">
          <Skeleton className="h-8 w-48 mb-6" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))}
          </div>
        </main>
      </div>
    );
  }

  if (isError || !project) {
    // 403: user is not a member of this project
    if (isError && ApiError.isForbidden(error)) {
      return <AccessDenied backHref={`/${params.workspaceSlug}`} backLabel="Back to workspace" />;
    }

    return (
      <div className="flex flex-col items-center justify-center h-full py-20 text-center">
        <AlertCircle className="h-10 w-10 text-destructive mb-3" />
        <h3 className="text-lg font-medium">Project not found</h3>
        <p className="text-sm text-muted-foreground mb-4">
          The project may have been deleted or you don&apos;t have access.
        </p>
        <Button variant="outline" onClick={() => refetch()}>
          Try Again
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col md:flex-row">
      <ProjectSidebar project={project} workspaceSlug={params.workspaceSlug} />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
