'use client';

import { observer } from 'mobx-react-lite';
import { useEffect, useState } from 'react';
import { FolderGit2, GitBranch, Link, Plus, Download, ChevronDown } from 'lucide-react';
import { useProjectStore } from '@/stores/RootStore';
import { isTauri } from '@/lib/tauri';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CloneRepoDialog } from './clone-repo-dialog';
import { LinkRepoDialog } from './link-repo-dialog';
import { GitStatusPanel, BranchSelector, ConflictBanner } from '@/features/git';

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

export const ProjectDashboard = observer(function ProjectDashboard() {
  const projectStore = useProjectStore();
  const [cloneOpen, setCloneOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  useEffect(() => {
    if (isTauri()) {
      projectStore.loadProjects();
    }
  }, [projectStore]);

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          {projectStore.projectsDir && (
            <p className="text-muted-foreground text-sm">
              Base directory: <span className="font-mono text-xs">{projectStore.projectsDir}</span>
            </p>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="sm" onClick={() => setLinkOpen(true)}>
            <Link className="size-4" />
            Link Existing
          </Button>
          <Button size="sm" onClick={() => setCloneOpen(true)}>
            <Download className="size-4" />
            Clone Repository
          </Button>
        </div>
      </div>

      {/* Content */}
      {projectStore.isLoading ? (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-muted/40 h-20 animate-pulse rounded-lg border"
              aria-hidden="true"
            />
          ))}
        </div>
      ) : projectStore.error ? (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3">
          <p className="text-destructive text-sm font-medium">Failed to load projects</p>
          <p className="text-destructive/80 mt-1 text-xs">{projectStore.error}</p>
        </div>
      ) : projectStore.projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed py-16 text-center">
          <div className="bg-muted flex size-12 items-center justify-center rounded-full">
            <FolderGit2 className="text-muted-foreground size-6" />
          </div>
          <div className="flex flex-col gap-1">
            <p className="font-medium">No projects yet</p>
            <p className="text-muted-foreground text-sm">
              Clone a repository or link an existing local folder to get started.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setLinkOpen(true)}>
              <Link className="size-4" />
              Link Existing
            </Button>
            <Button size="sm" onClick={() => setCloneOpen(true)}>
              <Plus className="size-4" />
              Clone Repository
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {projectStore.projects.map((project) => (
            <div
              key={project.path}
              className="rounded-lg border bg-card p-4 shadow-xs transition-shadow hover:shadow-sm cursor-pointer"
              onClick={() =>
                setSelectedProject((prev) => (prev === project.path ? null : project.path))
              }
            >
              <div className="flex items-center gap-4">
                {/* Icon */}
                <div className="bg-muted flex size-10 shrink-0 items-center justify-center rounded-md">
                  <GitBranch className="text-muted-foreground size-5" />
                </div>

                {/* Details */}
                <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold">{project.name}</span>
                    <Badge variant={project.linked ? 'secondary' : 'default'} className="shrink-0">
                      {project.linked ? 'Linked' : 'Cloned'}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground truncate font-mono text-xs">{project.path}</p>
                  {project.remote_url ? (
                    <p className="text-muted-foreground truncate text-xs">{project.remote_url}</p>
                  ) : (
                    <p className="text-muted-foreground/60 text-xs italic">Local only</p>
                  )}
                </div>

                {/* Timestamp + expand indicator */}
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-muted-foreground text-right text-xs">
                    <span>Added</span>
                    <br />
                    <span>{formatDate(project.added_at)}</span>
                  </div>
                  <ChevronDown
                    className={`text-muted-foreground size-4 transition-transform ${
                      selectedProject === project.path ? 'rotate-180' : ''
                    }`}
                  />
                </div>
              </div>

              {/* Expanded git panel */}
              {selectedProject === project.path && (
                <div className="mt-3 border-t pt-3 space-y-3" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    <BranchSelector repoPath={project.path} />
                  </div>
                  <ConflictBanner />
                  <GitStatusPanel repoPath={project.path} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CloneRepoDialog open={cloneOpen} onOpenChange={setCloneOpen} />
      <LinkRepoDialog open={linkOpen} onOpenChange={setLinkOpen} />
    </div>
  );
});
