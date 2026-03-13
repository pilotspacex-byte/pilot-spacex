'use client';

import { useParams } from 'next/navigation';
import { useProject } from '@/features/projects/hooks';
import { MessageSquare } from 'lucide-react';

export default function ProjectChatPage() {
  const params = useParams<{ workspaceSlug: string; projectId: string }>();
  const { data: project } = useProject({ projectId: params.projectId });

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <MessageSquare className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <p className="text-sm text-muted-foreground">Loading project...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-6 py-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Chat — {project.name}
        </h2>
        <p className="text-xs text-muted-foreground">
          AI chat scoped to this project&apos;s context
        </p>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <MessageSquare className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <h3 className="text-base font-medium mb-1">Project AI Chat</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          Chat integration with PilotSpaceAgent will be connected here. The AI will have context
          about {project.name}&apos;s issues, cycles, and members.
        </p>
      </div>
    </div>
  );
}
