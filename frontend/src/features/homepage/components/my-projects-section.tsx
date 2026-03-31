/**
 * MyProjectsSection — Displays the current user's assigned projects.
 *
 * T034 [US5]: Grid of project cards with name, identifier badge, last-activity
 * timestamp, and issue count. Empty state with "Contact your admin" guidance.
 * Uses useMyProjects TanStack Query hook (my-projects endpoint).
 */

'use client';

import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import type { MyProjectCard } from '@/services/api/project-members';
import { useMyProjects } from '@/services/api/project-members';
import { FolderKanban, Lock } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface MyProjectsSectionProps {
  workspaceId: string;
  workspaceSlug: string;
}

function ProjectCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <Skeleton className="h-4 w-16" />
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

function ProjectCard({
  project,
  onClick,
}: {
  project: MyProjectCard;
  workspaceSlug: string;
  onClick: () => void;
}) {
  const assignedDate = new Date(project.assignedAt).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  return (
    <button
      type="button"
      onClick={onClick}
      className="group text-left w-full rounded-lg border border-border bg-card p-4 space-y-2 transition-all duration-150 hover:bg-accent/50 hover:shadow-warm-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={`Open project ${project.name}`}
    >
      <div className="flex items-center justify-between gap-2">
        <Badge variant="secondary" className="font-mono text-xs shrink-0">
          {project.identifier}
        </Badge>
        {project.icon && <span className="text-base leading-none">{project.icon}</span>}
      </div>
      <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
        {project.name}
      </p>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>
          {project.issueCount} issue{project.issueCount !== 1 ? 's' : ''}
        </span>
        <span>·</span>
        <span>Joined {assignedDate}</span>
      </div>
    </button>
  );
}

export function MyProjectsSection({ workspaceId, workspaceSlug }: MyProjectsSectionProps) {
  const router = useRouter();
  const { data, isLoading } = useMyProjects(workspaceId);

  const projects = data?.items.filter((p) => !p.isArchived) ?? [];

  return (
    <section aria-label="My projects" className="space-y-3">
      <div className="flex items-center gap-2">
        <FolderKanban className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <h2 className="text-sm font-medium text-foreground">My Projects</h2>
        {!isLoading && <span className="text-xs text-muted-foreground">({projects.length})</span>}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <ProjectCardSkeleton key={i} />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border py-10 text-center">
          <Lock className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">No projects assigned</p>
            <p className="text-xs text-muted-foreground">
              Contact your workspace admin to get assigned to a project.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.projectId}
              project={project}
              workspaceSlug={workspaceSlug}
              onClick={() => router.push(`/${workspaceSlug}/projects/${project.projectId}`)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
