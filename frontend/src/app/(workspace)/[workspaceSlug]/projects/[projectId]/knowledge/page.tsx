'use client';

import { useParams } from 'next/navigation';
import { AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useProject } from '@/features/projects/hooks';
import { ProjectKnowledgeGraph } from '@/features/projects/components/project-knowledge-graph';

export default function ProjectKnowledgePage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();

  const { data: project, isLoading, isError } = useProject({ projectId: params.projectId });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Skeleton className="h-96 w-full max-w-2xl rounded-lg" />
        </div>
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 text-center">
        <AlertCircle className="h-10 w-10 text-destructive mb-3" />
        <h3 className="text-lg font-medium">Project not found</h3>
        <p className="text-sm text-muted-foreground">
          The project may have been deleted or you don&apos;t have access.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-4 shrink-0">
        <h1 className="text-lg font-semibold">Knowledge Graph</h1>
        <span className="text-sm text-muted-foreground">{project.name}</span>
      </div>

      {/* Graph fills remaining height */}
      <div className="flex-1 min-h-0">
        <ProjectKnowledgeGraph workspaceId={project.workspaceId} projectId={params.projectId} />
      </div>
    </div>
  );
}
